# Testing Infrastructure Specification

## Purpose

Establish a repeatable test framework with pytest, async fixtures, database setup/teardown, and mock services. Tests run against a separate test database or in-memory SQLite.

## Requirements

### Requirement: Test Runner Configuration

The system MUST provide a pytest configuration that discovers tests in `backend/tests/`.

**Acceptance Criteria**:
- All files named `test_*.py` under `backend/tests/` MUST be discovered
- Async tests MUST be supported (pytest-asyncio)
- Test database MUST be isolated from development/production data

**Dependencies**: pytest>=7.4, pytest-asyncio, httpx

#### Scenario: Running the test suite

- GIVEN the test environment is configured
- WHEN `pytest` is executed from the `backend/` directory
- THEN all discovered tests run and pass

### Requirement: Conftest Fixtures

The project MUST provide shared fixtures in `backend/tests/conftest.py`.

**Acceptance Criteria**:

| Fixture | Scope | Purpose |
|---------|-------|---------|
| `test_db` | function | Creates tables, yields session, drops tables |
| `client` | function | FastAPI TestClient with test_db override |
| `auth_headers` | function | Registers a user, returns {"Authorization": "Bearer {token}"} |
| `sample_manuscript` | function | Creates a Manuscript record in test_db |
| `sample_journal` | function | Creates a Journal record with test data |
| `mock_openalex` | function | Mocks OpenAlexService.fetch_journals_by_concept |
| `mock_gemini` | function | Mocks Gemini embedding generation |

#### Scenario: Auth fixture works

- GIVEN the `auth_headers` fixture
- WHEN a test makes an authenticated request
- THEN the request includes a valid Bearer token for a registered test user

### Requirement: Test Coverage Threshold

The system SHOULD achieve at least 70% code coverage on the `backend/app/` directory.

**Acceptance Criteria**:
- Coverage is measured by pytest-cov
- Coverage report excludes `tests/` and `venv/`

#### Scenario: Coverage check

- GIVEN the test suite has been executed with `pytest --cov=app --cov-report=term`
- WHEN coverage is below 70%
- THEN pytest-cov reports the shortfall (non-blocking for CI)
