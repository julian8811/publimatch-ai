# Design: PubliMatch Foundation

## Technical Approach

Refactor from a single-threaded prototype into an async MVP with auth, real scoring, background workers, and risk assessment. Celery offloads LLM/embedding work from the request path; a weighted scoring pipeline replaces the hardcoded placeholder; JWT auth wraps protected endpoints via FastAPI `Depends()`; Alembic migrations add `match_results` and `risk_assessments` tables alongside pgvector indexes.

The strategy is additive — every new system can be disabled independently. No existing endpoint is removed, only augmented.

## Architecture Decisions

| Decision | Choice | Alternatives | Rationale |
|----------|--------|-------------|-----------|
| Auth library | PyJWT (`PyJWT>=2.8`) | python-jose (unmaintained since 2022) | Actively maintained, same API surface |
| Password hashing | passlib[bcrypt] | hashlib, argon2 | passlib is the standard; bcrypt fast enough for MVP |
| Async worker | Celery + Redis | FastAPI BackgroundTasks, RQ, Arq | Celery has the largest ecosystem; Redis already in docker-compose; RQ doesn't support task routing, Arq too young |
| Embedding service | google-genai SDK | OpenAI, sentence-transformers | Gemini API key already configured; google-genai supports embedding models across projects |
| Test DB | SQLite in-memory | testcontainers-postgres, pytest-postgresql | Zero setup, fast for CI; existing models are compatible with SQLite (no postgres-specific types outside pgvector) |
| Scoring formula | Weighted composite | ML regression, LLM ranking | MVP needs explainability; weights match JMS spec (J. Med. Syst.) |
| Risk engine | Rule-based signals | LLM classification | Deterministic, auditable, no API cost per call |
| Base declaration | Single source in `models/base.py` | Keep both, remove from database.py | Alembic metadata must be a single `Base.metadata`; the duplicate prevents autogenerate |

## Data Flow

### Manuscript Upload (with Celery)

```
Client POST /api/manuscripts/upload
  │
  ├─ 1. Extract text from PDF/DOCX (synchronous)
  ├─ 2. Insert Manuscript row (status="pending")
  ├─ 3. Enqueue profile_manuscript(manuscript_id) → Celery
  └─ 4. Return ManuscriptResponse (status="pending")
         │
         ▼
  Celery Worker picks up task
  ├─ 5. Call Gemini to extract profile (title, abstract, keywords, type)
  ├─ 6. Update Manuscript row (status="processed" | "error")
  └─ 7. Done
```

### Match Request (scoring pipeline)

```
Client GET /api/matches/{id}
  │
  ├─ 1. Load Manuscript (must be "processed")
  ├─ 2. OpenAlex fetch_journals_by_concept(keywords) → 10 results
  ├─ 3. For each journal:
  │     ├─ Semantic (35%): Cosim(manuscript_embedding, journal.scope_embedding) via pgvector
  │     ├─ Methodology (15%): LLM-extracted type vs journal profile
  │     ├─ Language (10%): langdetect match
  │     ├─ Indexation (10%): scopus OR wos OR doaj OR latindex
  │     ├─ Cost (5%): APC penalty (lower is better)
  │     └─ ReviewTime (5%): based on average_review_weeks
  ├─ 4. Sort by weighted score, return top N
  └─ 5. For each returned match, risk_service.assess(journal_id) joins inline
```

### Auth Flow

```
Client                               Server
  │                                     │
  ├─ POST /api/auth/register ──────────→ validate + hash → INSERT users
  ├─ POST /api/auth/login ─────────────→ verify hash → sign JWT → return token
  ├─ GET /api/auth/me (Authorization) ─→ verify JWT → Depends(get_current_user) → return user
  └─ GET /api/matches/{id} (Authorization) → same Depends() guards protected endpoints
```

## Component Design

### Auth System

**Files**: `app/api/endpoints/auth.py` (new), `app/core/security.py` (new), `app/schemas.py` (extend)

```
app/core/security.py
├── hash_password(password: str) → str          # passlib bcrypt
├── verify_password(plain: str, hashed: str) → bool
├── create_access_token(data: dict) → str       # PyJWT, exp=timedelta(hours=24)
├── decode_access_token(token: str) → dict      # raises on expired/invalid
└── get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) → User
```

The `oauth2_scheme` is `OAuth2PasswordBearer(tokenUrl="/api/auth/login")`. Every protected endpoint uses `Depends(get_current_user)`. No `refresh_tokens` table for MVP — single 24h token with frontend re-login on 401.

**Table impact**: `users` table already exists. No migration needed for auth — only new rows.

### Scoring Engine (refactor `scoring_service.py`)

```python
class ScoringService:
    WEIGHTS = {
        "semantic": 0.35,
        "recent_articles": 0.20,   # deferred — returns 0
        "methodology": 0.15,
        "language": 0.10,
        "indexation": 0.10,
        "cost": 0.05,
        "review_times": 0.05,
    }

    async def calculate(self, manuscript: Manuscript, journal: Journal) -> ScoreResult:
        semantic     = await self._semantic_score(manuscript, journal)          # pgvector cosine
        methodology  = await self._methodology_score(manuscript, journal)       # LLM match
        language     = self._language_score(manuscript, journal)                # langdetect
        indexation   = self._indexation_score(journal)                          # boolean combo
        cost         = self._cost_penalty(journal)                              # APC curve
        review_times = self._review_time_score(journal)                         # weeks→score

        weighted = (
            semantic * self.WEIGHTS["semantic"] +
            methodology * self.WEIGHTS["methodology"] +
            language * self.WEIGHTS["language"] +
            indexation * self.WEIGHTS["indexation"] +
            cost * self.WEIGHTS["cost"] +
            review_times * self.WEIGHTS["review_times"]
        )  # recent_articles = 0 for now

        return ScoreResult(
            final_score=round(weighted * 100, 1),
            semantic_score=semantic,
            methodology_score=methodology,
            language_score=language,
            indexation_score=indexation,
            cost_score=cost,
            review_times_score=review_times,
        )
```

Each sub-score is a private method returning 0.0–1.0. The `_semantic_score` method generates an embedding for the manuscript abstract via Gemini (`text-embedding-004`) and queries `journals` with `<->` (cosine distance) ordered by similarity. The embedding is cached on the manuscript row.

### Celery Integration

**Files**: `app/celery_app.py` (new), `app/tasks/manuscript_tasks.py` (new), `app/tasks/journal_tasks.py` (new)

```python
# celery_app.py
from celery import Celery
from app.core.config import settings

celery_app = Celery("publimatch")
celery_app.config_from_object({
    "broker_url": settings.REDIS_URL,         # redis://localhost:6380/0
    "result_backend": settings.REDIS_URL,
    "task_serializer": "json",
    "accept_content": ["json"],
    "task_routes": {
        "app.tasks.manuscript_tasks.*": {"queue": "manuscripts"},
        "app.tasks.journal_tasks.*": {"queue": "journals"},
    },
    "task_acks_late": True,
    "worker_prefetch_multiplier": 1,
})
```

**Tasks**:

| Task | Queue | Trigger | What it does |
|------|-------|---------|-------------|
| `profile_manuscript(manuscript_id)` | manuscripts | Upload endpoint | Calls Gemini for profile extraction; updates Manuscript row |
| `generate_journal_embeddings()` | journals | Cron (manual) | Batch-processes all journals with NULL `scope_embedding` |
| `fetch_journal_metadata(openalex_id)` | journals | On-demand | Pulls missing fields from OpenAlex, updates Journal row |

**Redis config**: Docker already has `redis:7-alpine` on port 6380. Add `REDIS_URL=redis://localhost:6380/0` to `.env`.

### Risk Assessment Module

**File**: `app/services/risk_service.py` (new)

```python
class RiskService:
    INDICATORS = [
        ("no_doaj", 20),        # Not in DOAJ
        ("high_apc", 25),       # APC > $2000 USD without OA
        ("low_homepage", 15),   # Missing or minimal website
        ("young_journal", 20),  # No citations or recent (<3yr)
        ("broad_scope", 20),    # Scope is suspiciously broad
    ]

    def assess(self, journal: Journal) -> RiskAssessment:
        score = 0
        signals = []
        for name, weight in self.INDICATORS:
            if self._check(journal, name):
                score += weight
                signals.append(name)
        risk_level = "low" if score < 20 else "medium" if score < 50 else "high"
        return RiskAssessment(risk_level=risk_level, risk_score=score, signals=signals)
```

Integrates via `GET /api/matches/{id}` — after computing scores, each journal gets a risk assessment joined to the response.

### DOAJ Service

**File**: `app/services/doaj_service.py` (new)

```python
class DOAJService:
    BASE_URL = "https://doaj.org/api/v3/"

    async def verify(self, issn: str) -> dict:
        # GET /api/v3/search/journals?issn=XXXX-XXXX
        # Returns {"indexed": bool, "doaj_seal": bool, ...}
        # Caches result in journals.indexed_doaj
```

Cache strategy: on first lookup, set `journal.indexed_doaj`. Periodic refresh via Celery task.

## Interfaces / Contracts

### New Schemas (in `app/schemas.py`)

```python
# --- Auth ---
class UserCreate(BaseModel):
    email: str
    password: str
    full_name: Optional[str] = None
    institution: Optional[str] = None

class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: Optional[str]
    institution: Optional[str]
    role: str
    model_config = {"from_attributes": True}

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

# --- Scoring ---
class MatchScore(BaseModel):  # Extended
    final_score: float
    semantic_score: float = 0
    methodology_score: float = 0
    language_score: float = 0
    indexation_score: float = 0
    cost_score: float = 0
    review_times_score: float = 0

# --- Risk ---
class RiskAssessment(BaseModel):
    risk_level: str          # low | medium | high
    risk_score: float
    signals: list[str]

class JournalMatchResponse(BaseModel):  # Extended
    # ... existing fields ...
    risk_assessment: Optional[RiskAssessment] = None
```

### New API Endpoints

| Method | Path | Auth | What |
|--------|------|------|------|
| POST | `/api/auth/register` | No | Create user, return JWT |
| POST | `/api/auth/login` | No | Verify credentials, return JWT |
| GET | `/api/auth/me` | Yes | Current user profile |
| GET | `/api/health` | No | DB + Redis + Gemini connectivity |

### Modified Endpoints

| Method | Path | Change |
|--------|------|--------|
| POST | `/api/manuscripts/upload` | Add `Depends(get_current_user)`; return immediately with `status="pending"`; enqueue Celery task |
| GET | `/api/matches/{id}` | Add `Depends(get_current_user)`; return real scores instead of placeholder; include `risk_assessment` per journal |
| POST | `/api/projects/` | Add `Depends(get_current_user)`; auto-assign `user_id` from token |

## Database Schema Changes

### New Table: `match_results`

```sql
CREATE TABLE match_results (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    manuscript_id   UUID NOT NULL REFERENCES manuscripts(id) ON DELETE CASCADE,
    journal_id      UUID NOT NULL REFERENCES journals(id) ON DELETE CASCADE,
    final_score     NUMERIC(5,2) NOT NULL,
    semantic_score  NUMERIC(5,2),
    methodology_score NUMERIC(5,2),
    language_score  NUMERIC(5,2),
    indexation_score NUMERIC(5,2),
    cost_score      NUMERIC(5,2),
    review_times_score NUMERIC(5,2),
    created_at      TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_match_results_manuscript ON match_results(manuscript_id);
```

### New Table: `risk_assessments`

```sql
CREATE TABLE risk_assessments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    journal_id      UUID NOT NULL REFERENCES journals(id) ON DELETE CASCADE,
    risk_level      VARCHAR(10) NOT NULL,
    risk_score      NUMERIC(5,2) NOT NULL,
    signals         JSONB DEFAULT '[]',
    assessed_at     TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_risk_assessments_journal ON risk_assessments(journal_id);
```

### pgvector Index

The `journals.scope_embedding` column already exists (dim=1536). Add:

```sql
CREATE INDEX idx_journals_scope_embedding ON journals
  USING ivfflat (scope_embedding vector_cosine_ops) WITH (lists = 100);
```

### Migration Strategy

New Alembic revision (`a8e12734ff1f` → `xxxx_publimatch_foundation`):
- Create `match_results` table
- Create `risk_assessments` table
- Create `idx_journals_scope_embedding` index
- Add `abstract_embedding` column to `manuscripts` (Vector(1536), nullable)

Each migration step has a `downgrade()` counterpart.

## Testing Strategy

| Layer | What | How |
|-------|------|-----|
| Unit | Auth (hash/verify, token create/decode) | pytest, no DB |
| Unit | Scoring formulas | Pure math, no IO |
| Unit | Risk assessment logic | Mock journal data |
| Integration | Auth endpoints (register → login → me) | httpx async client with SQLite |
| Integration | Manuscript upload → Celery offload | Mock Celery via `task_always_eager=True` |
| Integration | Match endpoint with mocked OpenAlex | respx mock router |
| Integration | DOAJ service | respx for HTTP calls |
| Fixtures | Test DB | `sqlalchemy.create_engine("sqlite://")` with `Base.metadata.create_all` |
| Fixtures | Auth headers | `create_access_token` helper |

**Files**:
```
tests/
├── conftest.py              # session-scoped engine, function-scoped session
├── test_auth.py             # register → login → me → 401 on expired
├── test_scoring.py          # each sub-score component + weighted composite
├── test_risk.py             # risk signals, boundary cases
├── test_matches.py          # full match pipeline with mocked OpenAlex
├── test_health.py           # healthcheck endpoint
└── test_manuscripts.py      # upload flow, status transitions
```

**Mocks**: `respx` mocks OpenAlex API, DOAJ API, and Gemini API. Celery tasks are tested synchronously with `task_always_eager = True` in test config.

## Error Handling Strategy

| Failure | Behavior | Recovery |
|---------|----------|----------|
| Gemini API timeout on profiling | Manuscript stays `status="pending"`; retry via Celery (max 3, exponential backoff) | Admin can re-trigger via endpoint |
| Gemini embedding failure | Falls back to keyword-based semantic (TF-IDF cosine) | Logged; Celery retries |
| OpenAlex API timeout | Returns empty journal list (graded degradation) | Journals can be enriched later |
| DOAJ API timeout | Risk service treats as "no_doaj = True" (conservative) | Retry on next match request |
| Auth token expired | 401 with `WWW-Authenticate` header | Frontend redirects to login |
| Redis down | Celery tasks fail synchronously (raise immediately) | Deployment check: `/api/health` returns `redis: "unavailable"` |
| pgvector query fails | Falls back to sequential scan | Logged; degraded but functional |

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/db/database.py` | Modify | Remove duplicate `Base`, import `Base` from `app.models.base` |
| `app/models/__init__.py` | Modify | Import `MatchResult`, `RiskAssessment` |
| `app/models/match_result.py` | Create | MatchResults SQLAlchemy model |
| `app/models/risk_assessment.py` | Create | RiskAssessment SQLAlchemy model |
| `app/schemas.py` | Modify | Add auth + risk schemas; extend MatchScore + JournalMatchResponse |
| `app/core/config.py` | Modify | Add `GEMINI_API_KEY`, `REDIS_URL`, `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `JWT_EXPIRATION_HOURS`, `DOAJ_API_BASE` |
| `app/core/security.py` | Create | `hash_password`, `verify_password`, `create_access_token`, `decode_access_token`, `get_current_user` |
| `app/main.py` | Modify | Include `auth.router`; add `/api/health`; add `lifespan` event for startup |
| `app/api/endpoints/auth.py` | Create | `register`, `login`, `me` endpoints |
| `app/api/endpoints/manuscripts.py` | Modify | Add auth `Depends`; enqueue Celery task; return pending status |
| `app/api/endpoints/matches.py` | Modify | Add auth `Depends`; integrate real ScoringService + RiskService |
| `app/api/endpoints/projects.py` | Modify | Add auth `Depends` |
| `app/services/scoring_service.py` | Modify | Full rewrite with weighted components + pgvector |
| `app/services/risk_service.py` | Create | Predatory indicator engine |
| `app/services/doaj_service.py` | Create | DOAJ API client |
| `app/services/llm_service.py` | Modify | Add Gemini embedding method; extract profile returns structured model |
| `app/services/openalex_service.py` | Modify | Add exponential backoff; add metadata fetch method |
| `app/celery_app.py` | Create | Celery application instance with Redis config |
| `app/tasks/__init__.py` | Create | Empty |
| `app/tasks/manuscript_tasks.py` | Create | `profile_manuscript` task |
| `app/tasks/journal_tasks.py` | Create | `generate_journal_embeddings`, `fetch_journal_metadata` |
| `alembic/versions/xxxx_publimatch_foundation.py` | Create | Migration: match_results, risk_assessments, pgvector index, abstract_embedding |
| `requirements.txt` | Modify | Add `PyJWT>=2.8`, `passlib[bcrypt]>=1.7.4`, `bcrypt>=4.0`, `pytest>=8.0`, `pytest-asyncio>=0.23`, `httpx>=0.27`, `respx>=0.21` |
| `tests/` | Create | Full test directory |
| `frontend/src/app/dashboard/page.tsx` | Modify | Replace hardcoded `127.0.0.1:8003` with `process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8003'` |
| `frontend/src/components/Dropzone.tsx` | Modify | Same API_BASE_URL treatment; add error toast on upload failure |
| `frontend/.env.local` | Create | `NEXT_PUBLIC_API_BASE_URL=http://localhost:8003` |
| `.gitignore` | Modify | Add `backend/.env`, `frontend/.env.local` (if missing) |

## Migration Plan

### Order of Operations

1. **Bug fixes** (no new code, 3 changes):
   - Remove duplicate `Base` from `database.py`, import from `models.base`
   - Fix dashboard ternary (`manuRes.ok ? await manuRes.json() : null`)
   - Add `.env` to `.gitignore`, verify GROQ_API_KEY not in committed files

2. **Foundation** (tests, config, DB):
   - Add new deps to `requirements.txt`
   - Create test directory + `conftest.py` with SQLite fixtures
   - Generate Alembic migration for new tables + pgvector index + abstract_embedding
   - Run migration against dev DB (test downgrade)

3. **Auth layer**:
   - `security.py` (hash, tokens, Depends)
   - `auth.py` endpoints (register, login, me)
   - Add `Depends(get_current_user)` to all existing endpoints
   - Write `test_auth.py`

4. **Scoring engine**:
   - Refactor `ScoringService` with weighted components
   - Add Gemini embedding method to `LLMService`
   - pgvector similarity search
   - Wire into `matches.py`
   - Write `test_scoring.py`

5. **Celery workers**:
   - `celery_app.py` + task files
   - Move manuscript profiling to `profile_manuscript` task
   - Update upload endpoint to enqueue instead of blocking
   - Write `test_manuscripts.py`

6. **DOAJ + Risk**:
   - `doaj_service.py` (API client + cache)
   - `risk_service.py` (5-indicator engine)
   - Integrate risk into matches response
   - Write `test_risk.py` + `test_matches.py`

7. **Frontend**:
   - Environment variable for API URL
   - Error handling in Dropzone
   - Auth token storage (simple `localStorage` for MVP)

8. **Health endpoint + wiring**:
   - `GET /api/health` with DB, Redis, Gemini probes
   - Verify everything end-to-end
   - Run full test suite

### Backward Compatibility

- **Auth is additive**: unprotected endpoints continue working until `Depends()` is added (step 3). Old clients won't break mid-transition.
- **Scoring response enriched, not replaced**: `MatchScore` gains new fields but keeps `final_score`. Existing frontend JSON parsing continues to work.
- **Upload returns immediately**: Frontend polls status or receives via redirect — the `status="pending"` transition is the only observable change.
- **Celery optional**: If Redis/Celery aren't running, the upload endpoint completes synchronously (degraded mode). Detection via `REDIS_URL` config presence.

## Open Questions

- [ ] Should `abstract_embedding` be persisted on the manuscript row, or computed ephemerally per match request? Persisting trades storage for speed — the design assumes persist.
- [ ] What Gemini embedding model to use? `text-embedding-004` outputs 768-dim, but existing journal vectors are 1536-dim from `text-embedding-003`. Need to align dimensions.
- [ ] Celery concurrency: eventlet vs gevent vs prefork for the async worker? Prefork with `--concurrency=4` is simplest for MVP.
