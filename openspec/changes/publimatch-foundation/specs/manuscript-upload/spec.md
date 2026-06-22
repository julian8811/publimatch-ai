# Delta for Manuscript Upload

## MODIFIED Requirements

### Requirement: Upload Manuscript with Auth and Async Processing

The system MUST allow an authenticated user to upload a manuscript file (PDF or text) to a project they own. The upload dispatches Celery tasks for profiling and embedding, then returns immediately with the manuscript record and status.

(Previously: Upload accepted a project_id without authentication, performed LLM profiling inline on the request path.)

**Acceptance Criteria**:
- Endpoint MUST be protected by the auth dependency (requires valid JWT)
- The requesting user MUST own the target project (or be an admin)
- Upload MUST dispatch Celery task `profile_manuscript` instead of calling LLM inline
- Upload MUST dispatch Celery task `generate_manuscript_embedding` after profiling
- Response MUST include `status` field indicating "pending_profile"
- File content extraction (PDF/text) remains synchronous

**Dependencies**: Auth dependency, Celery dispatcher, `profile_manuscript` task, `generate_manuscript_embedding` task

#### Scenario: Authenticated user uploads to own project

- GIVEN a registered user owns "Project A" and has a valid JWT
- WHEN POST /api/manuscripts/upload is called with the JWT, project_id, and a PDF file
- THEN a 201 response is returned with manuscript data (id, status="pending_profile")
- AND the file content is extracted synchronously
- AND `profile_manuscript` is dispatched to Celery
- AND `generate_manuscript_embedding` is dispatched after profiling

#### Scenario: Unauthenticated upload

- GIVEN no Authorization header is provided
- WHEN POST /api/manuscripts/upload is called
- THEN a 401 Unauthorized response is returned

#### Scenario: User does not own the project

- GIVEN a registered user with a valid JWT who does NOT own project_id "X"
- WHEN POST /api/manuscripts/upload is called with project_id "X"
- THEN a 403 Forbidden response is returned

#### Scenario: Upload non-PDF file

- GIVEN an authenticated user with a valid token
- WHEN POST /api/manuscripts/upload is called with a .docx file
- THEN a 201 response is returned with status="pending_profile"
- AND the text is extracted via python-docx

### Requirement: Get Manuscript with Auth

The system MUST allow an authenticated user to retrieve a manuscript they own.

(Previously: No auth check on GET /api/manuscripts/{id}.)

#### Scenario: Get own manuscript

- GIVEN a manuscript owned by the authenticated user
- WHEN GET /api/manuscripts/{manuscript_id} is called with a valid JWT
- THEN a 200 response is returned with the manuscript data including current status

#### Scenario: Get another user's manuscript

- GIVEN a manuscript owned by a different user
- WHEN GET /api/manuscripts/{manuscript_id} is called
- THEN a 403 Forbidden response is returned
