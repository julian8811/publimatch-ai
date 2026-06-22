# Async Worker Specification

## Purpose

Offload heavyweight operations (manuscript profiling, embedding generation) from the request path to Celery background tasks. This keeps API responses fast and allows independent retry/scaling of processing tasks.

## Requirements

### Requirement: Celery Application Configuration

The system MUST bootstrap a Celery application with Redis as the message broker and result backend.

**Acceptance Criteria**:
- Celery app MUST read Redis URL from settings
- Celery app MUST be importable as `from app.celery_app import celery_app`
- Broker connection failure MUST log a warning, not crash the app

**Dependencies**: Redis service (add to docker-compose), celery>=5.3.6

#### Scenario: Celery app initializes

- GIVEN Redis is available at the configured URL
- WHEN the celery_app module is imported
- THEN a Celery application instance is created and connected to the broker

#### Scenario: Redis unavailable at startup

- GIVEN Redis is not running
- WHEN the app starts
- THEN a warning is logged but the FastAPI app continues running (endpoints that sync-call tasks may fail)

### Requirement: Manuscript Profiling Task

The system MUST provide a Celery task that takes a manuscript_id, generates the manuscript profile via LLM, and updates the database.

**Acceptance Criteria**:
- Task MUST be named `profile_manuscript`
- Task MUST receive manuscript_id as argument
- Task MUST update manuscript.title, .abstract, .keywords, .article_type, .language
- Task MUST set manuscript.status to "processed" on success or "error" on failure
- Failure MUST not raise unhandled exceptions (caught and logged)

#### Scenario: Profiling succeeds

- GIVEN a manuscript record with extracted_text and status="pending_profile"
- WHEN the `profile_manuscript` task runs
- THEN the manuscript is updated with LLM-extracted fields and status="processed"

#### Scenario: LLM call fails

- GIVEN the LLM service returns an error
- WHEN `profile_manuscript` runs
- THEN the manuscript status is set to "error" and the error is logged

### Requirement: Embedding Generation Task

The system MUST provide a Celery task that generates a manuscript embedding via Gemini.

**Acceptance Criteria**:
- Task MUST be named `generate_manuscript_embedding`
- Task MUST receive manuscript_id as argument
- Task MUST store the embedding vector in `manuscripts.manuscript_embedding`

#### Scenario: Embedding generation succeeds

- GIVEN a manuscript with abstract text
- WHEN the `generate_manuscript_embedding` task runs
- THEN the manuscript's `manuscript_embedding` column is populated with a 768-dim vector

### Requirement: Async Task Dispatch Helpers

The system MUST provide helper functions to dispatch tasks with standard error handling.

- `dispatch_profiling(manuscript_id)` — dispatches `profile_manuscript` asynchronously
- `dispatch_embedding(manuscript_id)` — dispatches `generate_manuscript_embedding`

Both MUST return the Celery AsyncResult ID.
