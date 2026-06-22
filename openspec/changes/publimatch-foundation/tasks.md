# Tasks: PubliMatch Foundation

## Dependency Diagram

```
A (Fixes) ──┬── B (Auth) ──┬── C (Tests) ──┐
             │              │                ├── F (Risk & DOAJ)
             │              └── D (DB & Scoring) ──┤
             │                                     │
             └── E (Celery) ──────────────────────-┘
                                                    │
                                                    ├── G (Frontend)
                                                    │
                                             [Review & Merge]
```

**Key**: Arrow A → B means B depends on A. Parallel batches (B, C, E) can proceed concurrently after A completes. F depends on D + B. G is independent of backend auth.

---

## Batch A: Foundation Fixes (~55 lines)

### A-01: Fix Base declaration conflict — ✅ DONE
- **Description**: Remove the duplicate `Base = declarative_base()` from `database.py` and import from `models.base` instead. This fixes the Alembic autogenerate conflict where two Base instances cause `Target database is not up to date` errors.
- **Files to modify**:
  - `backend/app/db/database.py` — remove `Base = declarative_base()`, import `Base` from `app.models.base`
- **Dependencies**: None
- **Estimated lines**: ~5
- **Acceptance criteria**:
  - [x] `database.py` no longer defines its own `Base`
  - [x] `from app.models.base import Base` is the single import
  - [x] Alembic `env.py` uses `from app.models import Base` (already correct, no change needed there)
  - [x] `app/main.py` and all routers continue to import only `get_db` from `database.py` (no Base import)

### A-02: Fix dashboard broken ternary — ✅ DONE
- **Description**: Line 34 of `dashboard/page.tsx` has `const manuData = await manuRes.ok ? await manuRes.json() : null;` inside `if (manuRes.ok)` — the `manuRes.ok` check is redundant (always true inside the block). Simplify to direct `await manuRes.json()`.
- **Files to modify**:
  - `frontend/src/app/dashboard/page.tsx` — line 34
- **Dependencies**: None
- **Estimated lines**: ~2
- **Acceptance criteria**:
  - [x] No redundant `manuRes.ok` check in the ternary
  - [x] Code compiles without TypeScript errors
  - [x] No functional change to dashboard behavior

### A-03: Add .env to gitignore — ✅ DONE
- **Description**: There is no root-level `.gitignore`. The `backend/.env` file containing `GROQ_API_KEY` is not gitignored. Create a root `.gitignore` that ignores `backend/.env` and `frontend/.env.local`. Verify the key hasn't been committed by checking git history.
- **Files to modify/create**:
  - `.gitignore` (create at project root: `/home/julian/Revistas/publimatch-ai/.gitignore`)
- **Dependencies**: None
- **Estimated lines**: ~5
- **Acceptance criteria**:
  - [x] `.gitignore` exists at project root with `backend/.env` and `.env*` entries
  - [x] `git check-ignore backend/.env` returns the file path
  - [x] Verify with `git log --all -- backend/.env` that no commit contains the GROQ_API_KEY value

### A-04: Add healthcheck endpoint — ✅ DONE
- **Description**: Create `GET /api/health` that returns service status without auth. Checks database connectivity, Redis availability (optional), and Gemini API config presence. Returns `{"status": "ok" | "degraded", "timestamp": "..."}` with sub-statuses.
- **Files to modify/create**:
  - `backend/app/api/endpoints/health.py` — create with health router
  - `backend/app/main.py` — include health router at `/api/health`
- **Dependencies**: A-01 (Base fix ensures clean DB import)
- **Estimated lines**: ~35
- **Acceptance criteria**:
  - [x] `GET /api/health` returns 200 without any auth header
  - [x] Response includes `status`, `timestamp`, `database`, `gemini` fields
  - [x] `database` is `"connected"` when DB is reachable
  - [x] `gemini` shows API key presence (not the actual key)
  - [x] When DB is unreachable, `status` is `"degraded"` and `database` is `"disconnected"`
  - [x] Response is JSON with ISO 8601 timestamp

### A-05: Add logging configuration — ✅ DONE
- **Description**: Add structured logging configuration to the backend. Configure Python logging with a JSON-friendly format, set log levels via env var, and add request-id middleware placeholder.
- **Files to modify/create**:
  - `backend/app/core/logging.py` — create logging config module
  - `backend/app/main.py` — call logging setup on startup
- **Dependencies**: A-01
- **Estimated lines**: ~20
- **Acceptance criteria**:
  - [x] Logging is configured at app startup with timestamp, level, module
  - [x] Log level is configurable via `LOG_LEVEL` env var (default: `INFO`)
  - [x] `print()` calls in services are replaced with `logger.info/warning/error`
  - [x] LLM error logs include traceback

---

## Batch B: Auth System (~250 lines)

### B-01: Add auth dependencies to requirements.txt — ✅ DONE
- **Description**: Add `PyJWT>=2.8`, `passlib[bcrypt]>=1.7.4`, `bcrypt>=4.0` to requirements.
- **Files to modify**:
  - `backend/requirements.txt`
- **Dependencies**: A-01
- **Estimated lines**: ~3
- **Acceptance criteria**:
  - [x] `pip install -r requirements.txt` succeeds
  - [x] `from passlib.context import CryptContext` imports without error
  - [x] `import jwt` imports PyJWT successfully

### B-02: Add JWT and service settings to config — ✅ DONE
- **Description**: Extend `Settings` with `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `JWT_EXPIRATION_HOURS`, `GEMINI_API_KEY`, `REDIS_URL`, `DOAJ_API_BASE`. Set sensible defaults. Add `LOG_LEVEL`.
- **Files to modify**:
  - `backend/app/core/config.py`
- **Dependencies**: B-01
- **Estimated lines**: ~25
- **Acceptance criteria**:
  - [x] All new settings are typed and have defaults (except `JWT_SECRET_KEY` which must be set)
  - [x] `JWT_ALGORITHM` defaults to `"HS256"`
  - [x] `JWT_EXPIRATION_HOURS` defaults to `24`
  - [x] `REDIS_URL` defaults to `"redis://localhost:6380/0"`
  - [x] `DOAJ_API_BASE` defaults to `"https://doaj.org/api/v2/"`
  - [x] Config is loadable without errors

### B-03: Create security.py (auth utilities + DI dependency) — ✅ DONE
- **Description**: Create `app/core/security.py` with:
  - `hash_password(password)` — bcrypt via passlib
  - `verify_password(plain, hashed)` — bcrypt verify
  - `create_access_token(data)` — PyJWT encode with exp
  - `decode_access_token(token)` — PyJWT decode, raises on expired/invalid
  - `get_current_user(token = Depends(oauth2_scheme), db)` — FastAPI dependency that returns `User` model or raises 401
- **Files to modify/create**:
  - `backend/app/core/security.py` (create)
- **Dependencies**: B-01, B-02
- **Estimated lines**: ~65
- **Acceptance criteria**:
  - [x] `hash_password("secret123")` returns a bcrypt hash string starting with `$2b$`
  - [x] `verify_password("secret123", hash)` returns `True` for matching hashes
  - [x] `verify_password("wrong", hash)` returns `False`
  - [x] `create_access_token({"sub": user_id})` returns a valid JWT string
  - [x] `decode_access_token(valid_token)` returns the original payload
  - [x] `decode_access_token(expired_token)` raises `HTTPException(401)`
  - [x] `decode_access_token("invalid")` raises `HTTPException(401)`
  - [x] `get_current_user` with valid token returns a `User` instance
  - [x] `get_current_user` without token raises `HTTPException(401)`

### B-04: Create auth endpoints (register, login, me) — ✅ DONE
- **Description**: Create `app/api/endpoints/auth.py` with:
  - `POST /api/auth/register` — creates user, returns UserResponse + TokenResponse
  - `POST /api/auth/login` — verifies credentials, returns TokenResponse with user profile
  - `GET /api/auth/me` — returns current user from JWT (protected)
- **Files to modify/create**:
  - `backend/app/api/endpoints/auth.py` (create)
  - `backend/app/schemas.py` — add `UserCreate`, `UserResponse`, `TokenResponse`, `LoginRequest` schemas
  - `backend/app/main.py` — include auth router at `/api/auth`
- **Dependencies**: B-02, B-03
- **Estimated lines**: ~90
- **Acceptance criteria**:
  - [x] `POST /api/auth/register` with valid data returns 201 + user profile + access_token
  - [x] Password is stored as bcrypt hash (not plaintext)
  - [x] Duplicate email returns 409 Conflict
  - [x] Password < 8 chars returns 422
  - [x] `POST /api/auth/login` with valid credentials returns 200 + token
  - [x] Invalid credentials return 401
  - [x] `GET /api/auth/me` with valid token returns user profile
  - [x] `GET /api/auth/me` without token returns 401
  - [x] Token expiry is respected (use a short exp for testing)

### B-05: Protect manuscripts endpoints — ✅ DONE
- **Description**: Add `Depends(get_current_user)` to `POST /api/manuscripts/upload` and `GET /api/manuscripts/{id}`. For upload, verify user owns the target project. For GET, verify user owns the manuscript.
- **Files to modify**:
  - `backend/app/api/endpoints/manuscripts.py`
- **Dependencies**: B-03, B-04
- **Estimated lines**: ~30
- **Acceptance criteria**:
  - [x] Unauthenticated requests return 401
  - [x] Upload to own project returns 201
  - [x] Upload to another user's project returns 403
  - [x] GET own manuscript returns 200
  - [x] GET another user's manuscript returns 403

### B-06: Protect matches endpoint — ✅ DONE
- **Description**: Add `Depends(get_current_user)` to `GET /api/matches/{id}`. Verify user owns the manuscript.
- **Files to modify**:
  - `backend/app/api/endpoints/matches.py`
- **Dependencies**: B-03, B-04
- **Estimated lines**: ~15
- **Acceptance criteria**:
  - [x] Unauthenticated requests return 401
  - [x] GET matches for own manuscript returns 200
  - [x] GET matches for another user's manuscript returns 403

### B-07: Protect projects endpoints — ✅ DONE
- **Description**: Add `Depends(get_current_user)` to `POST /api/projects/` and `GET /api/projects/`. For POST, auto-assign `user_id` from token. For GET, filter projects by the authenticated user.
- **Files to modify**:
  - `backend/app/api/endpoints/projects.py`
- **Dependencies**: B-03, B-04
- **Estimated lines**: ~20
- **Acceptance criteria**:
  - [x] Unauthenticated requests return 401
  - [x] POST creates project with `user_id` set from token
  - [x] GET returns only the authenticated user's projects

---

## Batch C: Testing Infrastructure (~280 lines)

### C-01: Add test dependencies to requirements.txt — ✅ DONE
- **Description**: Add `pytest>=8.0`, `pytest-asyncio>=0.23`, `httpx>=0.27`, `respx>=0.21`, `pytest-cov>=4.1` to requirements.
- **Files to modify**:
  - `backend/requirements.txt`
- **Dependencies**: A-01, B-01
- **Estimated lines**: ~5
- **Acceptance criteria**:
  - [x] All packages install cleanly
  - [x] `pytest --version` shows 8.x

### C-02: Create conftest.py with shared fixtures — ✅ DONE
- **Description**: Create `backend/tests/conftest.py` with:
  - Function-scoped SQLite in-memory engine + session (all tables created/dropped per test)
  - `test_client` fixture: FastAPI TestClient with DB override
  - `auth_headers` fixture: registers a user, returns `{"Authorization": "Bearer {token}"}`
  - `sample_manuscript` fixture: creates Manuscript in test DB
  - `sample_journal` fixture: creates Journal in test DB
  - `override_get_db` to inject test session into endpoints
- **Files to create**:
  - `backend/tests/__init__.py` (empty)
  - `backend/tests/conftest.py`
- **Dependencies**: C-01, B-02, B-03
- **Estimated lines**: ~120
- **Acceptance criteria**:
  - [x] `pytest` discovers and imports conftest without errors
  - [x] `test_client` fixture creates an isolated test DB per function
  - [x] `auth_headers` fixture produces valid Bearer tokens
  - [x] Test DB uses SQLite (no postgres dependency for test execution)
  - [x] Tables are cleaned up after each test function
  - [x] Auth dependency is properly overridden in test context

### C-03: Write test_auth.py — ✅ DONE
- **Description**: Test register → login → me flow. Cover happy paths, duplicate email, wrong password, expired token, malformed token.
- **Files to create**:
  - `backend/tests/test_auth.py`
- **Dependencies**: C-02, B-04
- **Estimated lines**: ~90
- **Acceptance criteria**:
  - [x] Test registration with valid data returns 201
  - [x] Test duplicate email returns 409
  - [x] Test weak password returns 422
  - [x] Test login with correct credentials returns 200 + token
  - [x] Test login with wrong password returns 401
  - [x] Test `/me` with valid token returns 200
  - [x] Test `/me` without token returns 401
  - [x] Test `/me` with expired token returns 401
  - [x] All tests pass with `pytest`

### C-04: Write test_health.py
- **Description**: Test healthcheck endpoint — healthy state, DB disconnected, Gemini missing. Use monkeypatch/env override for Gemini key.
- **Files to create**:
  - `backend/tests/test_health.py`
- **Dependencies**: C-02, A-04
- **Estimated lines**: ~35
- **Acceptance criteria**:
  - [ ] Test health returns 200 with `status: "ok"`
  - [ ] Test `database` field is present
  - [ ] All tests pass with `pytest`

### C-05: Write test_scoring.py
- **Description**: Test the ScoringService with real JMS algorithm. Test individual sub-scores (semantic, impact, OA, indexation, language, APC, review_speed) and the weighted composite. Test missing data fallbacks.
- **Files to create**:
  - `backend/tests/test_scoring.py`
- **Dependencies**: C-02, D-05, D-06
- **Estimated lines**: ~80
- **Acceptance criteria**:
  - [ ] Each sub-score component returns values in 0.0–1.0 range
  - [ ] Weighted composite returns values in 0–100 range
  - [ ] Missing embedding falls back to 0 for semantic score
  - [ ] All tests pass with `pytest`

### C-06: Write test_manuscripts.py
- **Description**: Test manuscript upload flow with auth — happy path (authenticated upload returns pending status), unauthenticated returns 401, unauthorized project returns 403. Also test Celery dispatch with `task_always_eager`.
- **Files to create**:
  - `backend/tests/test_manuscripts.py`
- **Dependencies**: C-02, B-05, E-02, E-03
- **Estimated lines**: ~75
- **Acceptance criteria**:
  - [ ] Authenticated upload returns 201 with `status: "pending_profile"`
  - [ ] Unauthenticated upload returns 401
  - [ ] Upload to wrong user's project returns 403
  - [ ] All tests pass with `pytest`

### C-07: Write test_matches.py
- **Description**: Test the full match pipeline with mocked OpenAlex, DOAJ, and Gemini. Test auth gating, real scoring output, risk assessment presence, empty results, and no-keywords error.
- **Files to create**:
  - `backend/tests/test_matches.py`
- **Dependencies**: C-02, B-06, D-08, F-03
- **Estimated lines**: ~100
- **Acceptance criteria**:
  - [ ] Unauthenticated match request returns 401
  - [ ] Authenticated match returns 200 with scored results
  - [ ] Results include `risk_assessment` on each journal
  - [ ] Results sorted by `final_score` descending
  - [ ] Manuscript without keywords returns 400
  - [ ] No journals found returns 200 with empty list
  - [ ] All tests pass with `pytest`

### C-08: Write test_risk.py
- **Description**: Test RiskService with boundary conditions — all 5 indicators triggered (high risk), no indicators (low risk), and partial indicators (moderate). Also test DOAJService verify endpoint with mocked HTTP.
- **Files to create**:
  - `backend/tests/test_risk.py`
- **Dependencies**: C-02, F-01, F-02
- **Estimated lines**: ~70
- **Acceptance criteria**:
  - [ ] All 5 indicators triggered returns `risk_level: "high"`, `score: 5`
  - [ ] 0 indicators triggered returns `risk_level: "low"`, `score: 0`
  - [ ] DOAJ verify returns `is_oa: True` for found journals
  - [ ] DOAJ verify returns `is_oa: False` when API is unreachable
  - [ ] All tests pass with `pytest`

### C-09: Add pytest config and coverage setup
- **Description**: Create `backend/pyproject.toml` (or `backend/setup.cfg`) with pytest config: `testpaths = tests`, `asyncio_mode = auto`, and add `pytest.ini` if needed. Set up coverage configuration with `--cov=app --cov-report=term --cov-fail-under=70`.
- **Files to create/modify**:
  - `backend/pyproject.toml` (create)
- **Dependencies**: C-01
- **Estimated lines**: ~15
- **Acceptance criteria**:
  - [ ] `pytest` discovers all tests in `tests/`
  - [ ] Async tests run without `@pytest.mark.asyncio` (auto-mode)
  - [ ] `pytest --cov=app` produces coverage report

---

## Batch D: Database & Scoring Engine (~350 lines)

### D-01: Create MatchResult model
- **Description**: Create `app/models/match_result.py` with SQLAlchemy model for the `match_results` table. Fields: id (UUID PK), manuscript_id (FK), journal_id (FK), final_score (Numeric(5,2)), semantic_score, impact_score, oa_score, indexation_score, language_score, apc_score, review_speed_score, created_at.
- **Files to create/modify**:
  - `backend/app/models/match_result.py` (create)
  - `backend/app/models/__init__.py` — import MatchResult
- **Dependencies**: A-01 (clean Base)
- **Estimated lines**: ~35
- **Acceptance criteria**:
  - [ ] Model has all specified fields with correct types
  - [ ] Foreign keys reference `manuscripts.id` and `journals.id` with CASCADE delete
  - [ ] Model is importable from `app.models`
  - [ ] Alembic autogenerate detects the new table

### D-02: Create RiskAssessment model
- **Description**: Create `app/models/risk_assessment.py` with SQLAlchemy model for the `risk_assessments` table. Fields: id (UUID PK), journal_id (FK), risk_level (String(10)), risk_score (Numeric(5,2)), signals (JSONB default `[]`), assessed_at.
- **Files to create/modify**:
  - `backend/app/models/risk_assessment.py` (create)
  - `backend/app/models/__init__.py` — import RiskAssessment
- **Dependencies**: A-01
- **Estimated lines**: ~30
- **Acceptance criteria**:
  - [ ] Model has all specified fields with correct types
  - [ ] Foreign key references `journals.id` with CASCADE delete
  - [ ] Alembic autogenerate detects the new table

### D-03: Add manuscript_embedding column to Manuscript model
- **Description**: Add `manuscript_embedding` column to `Manuscript` model as `Vector(768)` nullable. This stores the Gemini-generated embedding for cosine similarity scoring.
- **Files to modify**:
  - `backend/app/models/manuscript.py` — add `manuscript_embedding = Column(Vector(768))`
  - `backend/app/models/manuscript.py` — add `from pgvector.sqlalchemy import Vector` import
- **Dependencies**: A-01
- **Estimated lines**: ~5
- **Acceptance criteria**:
  - [ ] Manuscript model has `manuscript_embedding` column of type `Vector(768)`
  - [ ] Column is nullable for backward compatibility

### D-04: Create Alembic migration for new tables and columns
- **Description**: Generate Alembic migration revision that:
  - Creates `match_results` table
  - Creates `risk_assessments` table
  - Adds `manuscript_embedding` column to `manuscripts` (Vector(768), nullable)
  - Creates `idx_match_results_manuscript` index
  - Creates `idx_risk_assessments_journal` index
  - Adds pgvector ivfflat index on `journals.scope_embedding` if not exists
  - Each step has a `downgrade()` counterpart
- **Files to create**:
  - `backend/alembic/versions/xxxx_publimatch_foundation.py` (create migration)
- **Dependencies**: D-01, D-02, D-03, A-01
- **Estimated lines**: ~55
- **Acceptance criteria**:
  - [ ] `alembic upgrade head` applies all changes without errors
  - [ ] `match_results` table exists with correct schema
  - [ ] `risk_assessments` table exists with correct schema
  - [ ] `manuscripts` has `manuscript_embedding` column (Vector, nullable)
  - [ ] `alembic downgrade -1` reverses the migration cleanly
  - [ ] `downgrade` drops all created tables and columns

### D-05: Refactor ScoringService with real weighted JMS
- **Description**: Rewrite `ScoringService` with the weighted JMS algorithm:
  - `WEIGHTS` dict: semantic=30%, impact=20%, oa=15%, indexation=15%, language=10%, apc=5%, review_speed=5%
  - `calculate_journal_match_score(manuscript, journal, db)` — main entry point
  - `_semantic_score` — pgvector cosine similarity via `<->` operator
  - `_impact_score` — normalized `cited_by_count` (0–1)
  - `_oa_score` — boolean: 1.0 if OA, 0.0 if not
  - `_indexation_score` — count of (scopus, wos, doaj, latindex) / 4
  - `_language_score` — language match between manuscript and journal
  - `_apc_penalty` — sigmoid decay: higher APC = lower score
  - `_review_speed_score` — inverse of `average_review_weeks`
  - Final = SUM(component * weight) rounded to 1 decimal, scaled to 0–100
- **Files to modify**:
  - `backend/app/services/scoring_service.py`
- **Dependencies**: D-03 (manuscript_embedding), D-04 (migration applied), B-02 (settings)
- **Estimated lines**: ~120
- **Acceptance criteria**:
  - [ ] Service uses 7 weighted components matching spec weights
  - [ ] Each sub-score returns 0.0–1.0
  - [ ] Final score returns 0–100
  - [ ] Missing journal embedding results in semantic=0
  - [ ] Missing manuscript embedding falls back to 0
  - [ ] `_semantic_score` queries pgvector via `<->` distance
  - [ ] OA journal returns higher oa_score than non-OA
  - [ ] Higher APC returns lower apc_score
  - [ ] Serves as synchronous calculation (for use in tests without Celery)

### D-06: Add embedding generation to LLMService
- **Description**: Add `generate_embedding(text)` method to `LLMService` using the Google Gemini `text-embedding-004` model (768-dim). Falls back to returning `None` on failure (logged).
- **Files to modify**:
  - `backend/app/services/llm_service.py`
- **Dependencies**: B-02 (GEMINI_API_KEY)
- **Estimated lines**: ~35
- **Acceptance criteria**:
  - [ ] `generate_embedding("test text")` returns a list of 768 floats
  - [ ] Missing `GEMINI_API_KEY` returns `None` with logged warning
  - [ ] API timeout returns `None` (graceful degradation)
  - [ ] Integrates with Google `google-genai` SDK

### D-07: Refactor OpenAlexService with backoff and metadata fetch
- **Description**: Add exponential backoff to `fetch_journals_by_concept`. Add `fetch_journal_metadata(openalex_id)` method for on-demand enrichment (used by Celery tasks). Add typing and docstrings.
- **Files to modify**:
  - `backend/app/services/openalex_service.py`
- **Dependencies**: B-02 (config)
- **Estimated lines**: ~40
- **Acceptance criteria**:
  - [ ] `fetch_journals_by_concept` retries on 429/5xx with exponential backoff (max 3)
  - [ ] `fetch_journal_metadata(openalex_id)` returns enriched journal data
  - [ ] Service handles timeouts gracefully (returns empty list)

### D-08: Wire real scoring into matches endpoint
- **Description**: Update `GET /api/matches/{id}` to use the new `ScoringService.calculate_journal_match_score()` with real pgvector scores. The endpoint now queries the database for journals instead of relying solely on OpenAlex. Creates `MatchResult` records in the database. Returns the enhanced `JournalMatchResponse` with all score components.
- **Files to modify**:
  - `backend/app/api/endpoints/matches.py`
  - `backend/app/schemas.py` — update `MatchScore` and `JournalMatchResponse` with new fields
- **Dependencies**: D-05, D-06, D-07, B-06
- **Estimated lines**: ~45
- **Acceptance criteria**:
  - [ ] Matches endpoint returns real scores (not placeholder)
  - [ ] `MatchScore` includes all sub-scores: semantic, impact, oa, indexation, language, apc, review_speed
  - [ ] `JournalMatchResponse` includes `scores` with the extended schema
  - [ ] Match results are sorted by `final_score` descending
  - [ ] A `MatchResult` record is created in the database per match

---

## Batch E: Celery Workers (~190 lines)

### E-01: Add REDIS_URL setting to config
- **Description**: Already part of B-02. No separate task needed — reused from B-02.

### E-02: Create celery_app.py
- **Description**: Create Celery application instance with Redis broker/backend. Configure serializer, `task_acks_late`, `worker_prefetch_multiplier`. Must be importable as `from app.core.celery_app import celery_app`. Graceful fallback when Redis is unavailable (log warning, don't crash).
- **Files to create**:
  - `backend/app/core/celery_app.py`
- **Dependencies**: B-02 (REDIS_URL)
- **Estimated lines**: ~30
- **Acceptance criteria**:
  - [x] `celery_app` is importable without connecting to Redis
  - [x] Broker URL reads from settings
  - [x] `task_acks_late` is True
  - [x] Importing when Redis is down logs warning but doesn't raise

### E-03: Create async_tasks.py + task status endpoint
- **Description**: Create `app/services/async_tasks.py` with `process_manuscript_matches` task that fetches a manuscript from DB, scores against all DB journals via ScoringService, and saves MatchResult rows. Also add `GET /api/tasks/{task_id}` endpoint for checking Celery task status.
- **Files to create**:
  - `backend/app/services/async_tasks.py`
  - `backend/app/api/endpoints/tasks.py`
- **Dependencies**: E-02, D-05, D-06
- **Estimated lines**: ~90
- **Acceptance criteria**:
  - [x] `process_manuscript_matches` fetches manuscript from DB
  - [x] Calls ScoringService for each DB journal
  - [x] Saves MatchResult to DB
  - [x] `GET /api/tasks/{task_id}` returns task status
  - [x] Handles missing manuscript gracefully
  - [x] Tasks handle DB session correctly (create their own session, don't reuse request session)

### E-04: Create journal_tasks.py
- **Description**: Create tasks:
  - `generate_journal_embeddings()` — batch-process all journals with NULL `scope_embedding`. Calls Gemini to generate embedding from journal.scope text. Updates each journal. Reports count of processed journals.
  - `fetch_journal_metadata(openalex_id)` — pulls missing fields from OpenAlex, updates Journal row.
- **Files to create**:
  - `backend/app/tasks/journal_tasks.py`
- **Dependencies**: E-02, D-06, D-07
- **Estimated lines**: ~55
- **Acceptance criteria**:
  - [ ] `generate_journal_embeddings()` processes all journals without embeddings
  - [ ] Task handles journals with empty scope gracefully (skip, don't crash)
  - [ ] `fetch_journal_metadata(openalex_id)` updates journal fields from OpenAlex
  - [ ] Tasks log progress and errors

### E-05: Update upload endpoint to dispatch Celery tasks
- **Description**: Modify `POST /api/manuscripts/upload` to:
  1. Extract text synchronously (as before)
  2. Create Manuscript with `status="pending_profile"`
  3. Commit immediately so Celery sees the record
  4. Dispatch `profile_manuscript(manuscript_id)` via `dispatch_profiling()`
  5. Return ManuscriptResponse with `status="pending_profile"`
- **Files to modify**:
  - `backend/app/api/endpoints/manuscripts.py`
- **Dependencies**: E-03, B-05
- **Estimated lines**: ~35
- **Acceptance criteria**:
  - [ ] Upload returns immediately (doesn't wait for LLM)
  - [ ] Response has `status: "pending_profile"`
  - [ ] Celery task is dispatched to `manuscripts` queue
  - [ ] When Celery completes, manuscript record is updated with profile + `status: "processed"`
  - [ ] If Redis/Celery is down, upload still creates the record with `status: "pending_profile"` (degraded mode)

---

## Batch F: Risk Assessment & DOAJ (~220 lines)

### F-01: Create DOAJService
- **Description**: Create `app/services/doaj_service.py` with:
  - `verify_journal(issn)` — calls `GET https://doaj.org/api/v3/search/articles/issn:XXXX-XXXX`
  - Returns `{"in_doaj": bool, "total_results": int}`
  - On timeout/non-200/401, returns `{"in_doaj": False, "total_results": 0}` (conservative default, no exception)
  - Uses `httpx.AsyncClient`
- **Files to create**:
  - `backend/app/services/doaj_service.py`
- **Dependencies**: B-02 (DOAJ_API_BASE)
- **Estimated lines**: ~65
- **Acceptance criteria**:
  - [x] `verify_journal("1932-6203")` returns `in_doaj: True`
  - [x] `verify_journal("0000-0000")` returns `in_doaj: False`
  - [x] API timeout returns safe defaults `in_doaj: False`, no exception
  - [x] API 401 returns safe defaults (graceful degradation)
  - [x] Empty ISSN returns `in_doaj: False` immediately

### F-02: Create RiskService
- **Description**: Create `app/services/risk_service.py` with 7 weighted predatory signals (0–100 scale):
  - `no_doaj` (20pts), `no_scopus` (15pts), `no_wos` (15pts), `no_issn` (25pts)
  - `fast_publication` (10pts), `low_article_count` (10pts), `no_publisher_info` (5pts)
  - Score = weighted sum (capped at 100), level: >=50 = high, >=20 = medium, <20 = low
  - Missing optional data triggers signals conservatively
  - `assess_journal(journal_data)` returns `{"risk_score": int, "risk_level": str, "signals": list[str]}`
- **Files to create**:
  - `backend/app/services/risk_service.py`
- **Dependencies**: None (pure logic, no external deps)
- **Estimated lines**: ~75
- **Acceptance criteria**:
  - [x] All signals triggered returns `risk_score: 100`, `risk_level: "high"`
  - [x] 0 signals triggered returns `risk_score: 0`, `risk_level: "low"`
  - [x] 35 points returns `risk_level: "medium"`
  - [x] `signals` array contains only triggered signal names
  - [x] Conservative defaults for missing data (triggers on None)

### F-03: Wire risk assessment into matches endpoint
- **Description**: Update `GET /api/matches/{id}` to run `DOAJService.verify_journal()` and `RiskService.assess_journal()` for each matched journal. Add `risk_assessment` to `JournalMatchResponse` schema.
- **Files to modify**:
  - `backend/app/api/endpoints/matches.py`
  - `backend/app/schemas.py` — add `RiskAssessmentResponse` schema, extend `JournalMatchResponse`
- **Dependencies**: F-01, F-02, D-08
- **Estimated lines**: ~35
- **Acceptance criteria**:
  - [x] Each match in response includes `risk_assessment: { risk_score, risk_level, signals }`
  - [x] DOAJ verification runs before risk assessment
  - [x] DOAJ API failure doesn't break matches (conservative defaults)
  - [x] Response is backward-compatible (new field, no removed fields)

### F-04: Add risk assessment schemas
- **Description**: Add Pydantic models for risk: `RiskAssessmentResponse(risk_score, risk_level, signals)` and update `JournalMatchResponse` to include optional `risk_assessment`.
- **Files to modify**:
  - `backend/app/schemas.py`
- **Dependencies**: F-03 can include this
- **Estimated lines**: ~10
- **Acceptance criteria**:
  - [x] `RiskAssessmentResponse` has `risk_score: int`, `risk_level: str`, `signals: list[str]`
  - [x] `JournalMatchResponse` has optional `risk_assessment`

### F-05: Write test_risk.py
- **Description**: Already listed as C-08. Moved to Testing batch for organizational purposes.

### F-06: Write test_matches.py (with risk assertions)
- **Description**: Already listed as C-07. Moved to Testing batch.

---

## Batch G: Frontend Fixes (~150 lines)

### G-01: Add API_BASE_URL env var support ✅
- **Description**: Created `frontend/.env.local` with `NEXT_PUBLIC_API_URL=http://localhost:8000/api`. Created `frontend/src/lib/config.ts` exporting `config.apiUrl`. Updated `Dropzone.tsx` and `dashboard/page.tsx` to import `config` and replace all hardcoded `http://127.0.0.1:8003` references with `${config.apiUrl}`.
- **Files modified/created**:
  - `frontend/.env.local` (created)
  - `frontend/src/lib/config.ts` (created)
  - `frontend/src/components/Dropzone.tsx` — replaced all hardcoded URLs
  - `frontend/src/app/dashboard/page.tsx` — replaced all hardcoded URLs
- **Dependencies**: None
- **Estimated lines**: ~15
- **Acceptance criteria**:
  - [x] `frontend/.env.local` contains `NEXT_PUBLIC_API_URL`
  - [x] All hardcoded `http://127.0.0.1:8003` references use the env var via config
  - [x] Fallback to `http://localhost:8000/api` works when env var is not set
  - [x] Frontend compiles without errors (tsc --noEmit passes)

### G-02: Fix error handling in Dropzone ✅
- **Description**: Added user-facing error handling to Dropzone — `error` state, validation (file size/type), network error detection, API error messages with status codes, dismiss button, and 401 session expiry handling. All existing dropzone UI preserved.
- **Files modified**:
  - `frontend/src/components/Dropzone.tsx` — added error state, validation, try/catch, dismiss
- **Dependencies**: G-01
- **Estimated lines**: ~40
- **Acceptance criteria**:
  - [x] Network error shows user-visible error message (not just console.error)
  - [x] API error (non-2xx) shows user-visible error with status code or server detail
  - [x] Error state has a dismiss/clear option
  - [x] Dropzone remains usable after error (can select different file, clears error on file select/drop)

### G-03: Fix dashboard data fetching ✅
- **Description**: Updated dashboard to use `config.apiUrl` instead of hardcoded URLs. Added proper error state with user-facing error display page with "Back to Upload" link. Added 401 handling. Empty matches already handled (showed "No matches found" message).
- **Files modified**:
  - `frontend/src/app/dashboard/page.tsx` — added error state, error UI, config import, 401 handling
- **Dependencies**: G-01, A-02
- **Estimated lines**: ~20
- **Acceptance criteria**:
  - [x] Dashboard fetches from configurable API URL
  - [x] Error in fetching doesn't break the page (shows error message + back link)
  - [x] Empty matches shows "No matches found" message (already existed)

### G-04: Add client-side auth token handling ✅
- **Description**: Created `frontend/src/lib/auth.ts` with `getToken`, `setToken`, `clearToken`, `isAuthenticated`, and `authHeaders` functions. Updated `Dropzone.tsx` and `dashboard/page.tsx` to import and use `authHeaders()` and `clearToken()` on 401 responses.
- **Files created/modified**:
  - `frontend/src/lib/auth.ts` (created) — token storage + auth helpers
  - `frontend/src/components/Dropzone.tsx` — includes Bearer token in API calls, clears on 401
  - `frontend/src/app/dashboard/page.tsx` — includes Bearer token in API calls, clears on 401
- **Dependencies**: G-01, B-04
- **Estimated lines**: ~55
- **Acceptance criteria**:
  - [x] API calls include Bearer token from localStorage when available
  - [x] 401 response clears stored token with user-facing message
  - [x] Login/register can use `setToken()` to store token
  - [x] Frontend compiles without TypeScript errors

### G-05: Wire up new match response format with risk assessment ✅
- **Description**: Updated JournalCard with corrected SCORE_LABELS keys matching backend (`indexation_score`, `apc_score`, `review_speed_score`). Added risk assessment badge with color-coded indicator (low=green, medium/moderate=amber, high=red). Shows risk signals as small tags. Handles missing `risk_assessment` and missing `ai_analysis` gracefully.
- **Files modified**:
  - `frontend/src/components/JournalCard.tsx` — fixed score labels, added RISK_COLORS, added risk badge
- **Dependencies**: G-03, G-04, F-03
- **Estimated lines**: ~30
- **Acceptance criteria**:
  - [x] JournalCard displays all new score components (7 keys matching backend)
  - [x] Risk assessment badge shows with correct color per level (green/amber/red)
  - [x] Missing `ai_analysis` doesn't break rendering (null check already existed)
  - [x] TypeScript compiles with updated response type (any, pass-through)

---

## Decision Needed Before Apply

1. **Embedding dimension mismatch**: The existing `journals.scope_embedding` column is `Vector(1536)` (from `text-embedding-003` era). The design proposes using Gemini `text-embedding-004` which outputs 768-dim. This affects D-03, D-04, D-05, E-04.
   - **Options**: (a) Recreate `scope_embedding` as `Vector(768)` with a migration (loses existing embeddings), (b) Keep 1536-dim and use a different embedding model, (c) Support both dimensions with a version field.
   - **Recommendation**: Option (a) — the existing embeddings are likely all NULL or unused, and a fresh batch generate (E-04) will repopulate them.

2. **Scoring weight schema mismatch**: The spec (`journal-scoring/spec.md`) and design (`design.md`) define different weight sets and component names:
   - **Spec**: semantic(30%), impact(20%), oa(15%), indexation(15%), language(10%), apc(5%), review_speed(5%)
   - **Design**: semantic(35%), methodology(15%), language(10%), indexation(10%), cost(5%), review_times(5%), recent_articles(20% deferred)
   - **Decision needed**: Which weight set to implement? The spec was written first, the design may have diverged.

3. **Gemini vs Groq**: The existing codebase uses GROQ API (`llama3-70b-8192`) for manuscript profiling. The design adds Gemini for embeddings. Should manuscript profiling migrate to Gemini as well, or keep Groq for LLM + Gemini for embeddings only?

4. **Auth endpoint path prefix**: The design specifies `/api/auth/register`, `/api/auth/login`, `/api/auth/me`. Confirm this matches the frontend expectations.

---

## Estimated Totals by Batch

| Batch | Description | Est. Lines | Est. Files |
|-------|-------------|-----------|------------|
| A | Foundation Fixes | ~55 | 6 |
| B | Auth System | ~250 | 8 |
| C | Testing Infrastructure | ~280 | 10 |
| D | Database & Scoring Engine | ~350 | 9 |
| E | Celery Workers | ~190 | 6 |
| F | Risk Assessment & DOAJ | ~220 | 6 |
| G | Frontend Fixes | ~150 | 7 |
| **Total** | | **~1,495** | **~52** |

---

## Review Workload Forecast

- **Chained PRs recommended: Yes**
- **400-line budget risk: High**
- **Estimated total changed lines**: ~1,500
- **Decision needed before apply: Yes**

### Recommended Chained PR Structure

| PR | Batches | Est. Lines | Rationale |
|----|---------|-----------|-----------|
| PR 1 | **A + B** | ~305 lines | Foundation fixes + auth are tightly coupled; auth adds security before any other change |
| PR 2 | **C** | ~280 lines | Testing infra + first test suite; independent review |
| PR 3 | **D** | ~350 lines | Core scoring engine + DB migration; complex logic needs focused review |
| PR 4 | **E + F** | ~410 lines | Celery + Risk are connected through the matches endpoint; risk near budget limit |
| PR 5 | **G** | ~150 lines | Frontend changes; independent of backend internals |

**Alternative**: Merge PR 4 into two separate PRs if 400-line budget is strict:
- PR 4a: E (Celery Workers, ~190 lines)
- PR 4b: F (Risk & DOAJ, ~220 lines)

This keeps every PR under ~350 lines for safer reviewing.

### Decisions to resolve before apply:
1. Embedding dimension (1536 vs 768) — affects D-03, D-04, D-05
2. Scoring weights (spec vs design) — affects D-05
3. Gemini vs Groq for profiling — affects E-03, D-06
4. Auth prefix confirmation — affects B-04, G-04
