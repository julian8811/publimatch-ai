# User Authentication Specification

## Purpose

Provide JWT-based user registration, login, and profile retrieval. The auth layer protects all endpoints that require authenticated access using FastAPI dependency injection.

## Requirements

### Requirement: User Registration

The system MUST allow a new user to register with email, password, full name, and institution.

**Acceptance Criteria**:
- Password MUST be hashed with bcrypt before storage
- Email MUST be unique (case-insensitive)
- Response MUST return user profile (excluding password hash)
- Duplicate email MUST return 409 Conflict

**Dependencies**: `users` table (exists), bcrypt library

#### Scenario: Happy path registration

- GIVEN the user provides a valid email, password ≥8 chars, full name, and institution
- WHEN POST /api/auth/register is called
- THEN a 201 response is returned with the user profile (id, email, full_name, institution, role, created_at)
- AND the password is stored as a bcrypt hash

#### Scenario: Duplicate email

- GIVEN a user with email "test@example.com" already exists
- WHEN POST /api/auth/register is called with the same email
- THEN a 409 Conflict response is returned with a descriptive error

#### Scenario: Weak password

- GIVEN the password is shorter than 8 characters
- WHEN POST /api/auth/register is called
- THEN a 422 Unprocessable Entity response is returned

### Requirement: User Login

The system MUST authenticate a user by email and password, returning a JWT access token.

**Acceptance Criteria**:
- Token MUST encode user_id and exp in the payload
- Token expiry MUST be configurable (default 24 hours)
- Invalid credentials MUST return 401 Unauthorized
- Response MUST include token and token_type

**Dependencies**: JWT secret key in settings

#### Scenario: Successful login

- GIVEN a registered user with email "user@example.com" and correct password
- WHEN POST /api/auth/login is called with valid credentials
- THEN a 200 response is returned with `access_token`, `token_type: "bearer"`, and user profile

#### Scenario: Invalid password

- GIVEN a registered user
- WHEN POST /api/auth/login is called with the wrong password
- THEN a 401 Unauthorized response is returned

### Requirement: Get Current User Profile

The system MUST return the authenticated user's profile given a valid JWT.

**Acceptance Criteria**:
- Valid token MUST return user profile
- Expired or malformed token MUST return 401
- Response MUST exclude password_hash

**Dependencies**: Auth middleware dependency, JWT verification

#### Scenario: Valid token

- GIVEN a registered user with a valid JWT access token
- WHEN GET /api/auth/me is called with Authorization: Bearer {token}
- THEN a 200 response is returned with the user profile

#### Scenario: Expired token

- GIVEN an expired JWT token
- WHEN GET /api/auth/me is called
- THEN a 401 Unauthorized response is returned

### Requirement: Auth Dependency for Protected Routes

The system MUST provide a FastAPI `Depends` callable that extracts and validates the current user, which can be injected into any protected route.

**Acceptance Criteria**:
- Routes that include the dependency MUST reject unauthenticated requests with 401
- The dependency MUST inject the `User` model instance into the route handler

#### Scenario: Protected route with valid token

- GIVEN a valid JWT token and a route protected by the auth dependency
- WHEN the route is called with the token
- THEN the route executes and returns data

#### Scenario: Protected route without token

- GIVEN a protected route
- WHEN the route is called without an Authorization header
- THEN a 401 Unauthorized response is returned
