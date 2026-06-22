# Publimatch Foundation — Specifications Summary

**Change**: publimatch-foundation  
**Scope**: Auth, real scoring, async processing, risk assessment, DOAJ verification, health monitoring, testing infra, plus modifications to manuscript upload and journal matching.

## Specs Created

| Domain | Type | File |
|--------|------|------|
| `user-auth` | New | `openspec/specs/user-auth/spec.md` |
| `journal-scoring` | New | `openspec/specs/journal-scoring/spec.md` |
| `async-worker` | New | `openspec/specs/async-worker/spec.md` |
| `risk-assessment` | New | `openspec/specs/risk-assessment/spec.md` |
| `doaj-verification` | New | `openspec/specs/doaj-verification/spec.md` |
| `health-monitoring` | New | `openspec/specs/health-monitoring/spec.md` |
| `testing-infrastructure` | New | `openspec/specs/testing-infrastructure/spec.md` |
| `manuscript-upload` | Delta | `openspec/changes/publimatch-foundation/specs/manuscript-upload/spec.md` |
| `journal-matching` | Delta | `openspec/changes/publimatch-foundation/specs/journal-matching/spec.md` |

## Coverage

- **Happy paths**: All domains covered
- **Edge cases**: Auth (duplicate email, weak password, expired token), Scoring (missing embeddings, empty keywords), Worker (broker down, task failure), Risk (no DOAJ data, unknown journal), Upload (non-PDF, processing error), Matches (no keywords, empty results)
- **Error states**: 401/403 for unauthenticated requests, 404 for missing resources, 503 for worker unavailability, 422 for validation errors

## Dependencies

- Google Gemini API key (existing)
- PostgreSQL with pgvector (existing)
- Redis for Celery broker (add to docker-compose)
- FastAPI Depends for auth middleware
- pytest + httpx + pytest-asyncio for testing

## Next Step

Ready for design (`sdd-design`).
