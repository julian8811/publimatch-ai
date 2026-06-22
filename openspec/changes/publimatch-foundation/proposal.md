# Proposal: PubliMatch Foundation

## Intent

Close critical MVP gaps blocking deployment: auth, real scoring, async processing, tests, risk assessment, and bug fixes. Bring the project from ~60% to 100% MVP.

## Scope

### In Scope
1. Fix 3 critical bugs: Base declaration conflict, dashboard broken ternary, GROQ_API_KEY leakage
2. Testing infra: pytest + async fixtures, 5 test files, healthcheck endpoint, structured logging
3. JWT auth: register/login/me endpoints, bcrypt hashing, DI-protected routes
4. Database: match_results + risk_assessments tables, Alembic migration
5. Real scoring engine: weighted Gemini embeddings + impact/OA/indexation/language/cost scores
6. Celery async workers for journal fetching + manuscript profiling
7. DOAJ verification + risk assessment service (predatory indicators)
8. Frontend: API_BASE_URL env var, error handling in Dropzone

### Out of Scope
- Cover letter generator
- PDF export
- CI/CD pipelines
- Dockerfiles
- Articles table & recent-articles scoring
- i18n / multi-language
- S3 storage
- Rate limiting

## Capabilities

### New Capabilities
- `auth`: JWT-based user registration, login, and profile
- `risk-assessment`: Predatory journal detection with scored signals
- `doaj-verification`: DOAJ membership check for journals
- `async-worker`: Celery-based offload for heavy processing

### Modified Capabilities
- `scoring`: Real weighted embedding scoring replaces placeholder
- `journal-matching`: Returns risk assessment alongside match results

## Approach

1. Fix bugs first (no new code)
2. Add DB tables + Alembic migration
3. Add JWT auth layer (models → endpoints → middleware)
4. Add testing infra, write tests alongside features
5. Refactor scoring to use real embeddings + weights
6. Add Celery workers, move LLM off request path
7. Add DOAJ + risk services
8. Wire everything into matches endpoint

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/app/db/database.py` | Modified | Remove duplicate Base, import from models |
| `backend/app/models/` | Modified | Add match_result.py, risk_assessment.py |
| `backend/app/schemas.py` | Modified | Add auth + risk schemas |
| `backend/app/core/config.py` | Modified | Add JWT + DOAJ settings |
| `backend/app/main.py` | Modified | Add auth router + healthcheck |
| `backend/app/api/endpoints/auth.py` | New | Auth endpoints |
| `backend/app/services/scoring_service.py` | Modified | Real embedding scoring |
| `backend/app/services/risk_service.py` | New | Predatory indicator scoring |
| `backend/app/services/doaj_service.py` | New | DOAJ verification |
| `backend/app/celery_app.py` | New | Celery config |
| `backend/app/worker.py` | New | Async tasks |
| `backend/tests/` | New | Full test directory |
| `backend/requirements.txt` | Modified | Add test + celery deps |
| `frontend/src/app/dashboard/page.tsx` | Modified | Fix ternary, use env var |
| `frontend/src/components/Dropzone.tsx` | Modified | Error handling, env var |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Tests need user context | High | Mock auth dependency |
| Gemini embeddings slow | Med | Celery offload + retry |
| OpenAlex rate limits | Med | Exponential backoff |
| Existing DB migration | Med | Add downgrade, test on copy |

## Rollback Plan

Each DB migration is reversible (downgrade). Auth is additive — old endpoints work without token until protected. Celery can be disabled by not running the worker. Each change is independently revertible.

## Dependencies

- Google Gemini API key (already configured)
- Existing PostgreSQL with pgvector extension
- Redis (for Celery broker) — add to docker-compose

## Success Criteria

- [ ] `pytest` passes with >70% coverage on backend
- [ ] User can register, login, get JWT
- [ ] Manuscript upload returns real matches with scores
- [ ] Risk assessment returns with each match
- [ ] Celery worker processes manuscript profiling async
- [ ] Dashboard works without `127.0.0.1:8003` hardcoded
- [ ] API key not committable (gitignored .env)
- [ ] All existing functionality still works
