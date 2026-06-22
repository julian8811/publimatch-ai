# Health Monitoring Specification

## Purpose

Provide a lightweight health-check endpoint that confirms the API, database, and optional service dependencies are operational. Used by monitoring tools and load balancers.

## Requirements

### Requirement: Health Check Endpoint

The system MUST expose a GET /health endpoint returning service status.

**Acceptance Criteria**:
- Endpoint MUST NOT require authentication
- Response MUST include `status: "ok"` at minimum
- Response MUST include `timestamp` in ISO 8601 format
- Response SHOULD include optional `database`, `redis`, and `gemini` sub-statuses

**Dependencies**: None (no-auth endpoint)

#### Scenario: All services healthy

- GIVEN the database is reachable and Redis is connected
- WHEN GET /health is called
- THEN a 200 response is returned with `{"status": "ok", "database": "connected", "redis": "connected", "timestamp": "..."}`

#### Scenario: Database unreachable

- GIVEN the database connection fails
- WHEN GET /health is called
- THEN a 200 response is returned with `{"status": "degraded", "database": "disconnected", "timestamp": "..."}`

#### Scenario: Redis unreachable

- GIVEN Redis is not running
- WHEN GET /health is called
- THEN a 200 response is returned with `{"status": "degraded", "redis": "disconnected", "timestamp": "..."}`
