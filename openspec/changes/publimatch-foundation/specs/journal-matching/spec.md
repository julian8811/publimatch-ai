# Delta for Journal Matching

## MODIFIED Requirements

### Requirement: Get Matches with Auth, Real Scoring, and Risk Assessment

The system MUST return journal matches for an authenticated user's manuscript. Each match includes real weighted scores (JMS algorithm) and a risk assessment.

(Previously: No auth required, used placeholder scoring, no risk assessment.)

**Acceptance Criteria**:
- Endpoint MUST be protected by the auth dependency
- The manuscript MUST belong to the authenticated user
- Scoring MUST use the real JMS algorithm (embedding-based, 7 components)
- Each match MUST include a `risk_assessment` object with `score`, `level`, and `indicators`
- DOAJ verification MUST be attempted before risk assessment
- LLM compatibility analysis (ai_analysis) remains optional and may be async

**Dependencies**: Auth dependency, scoring_service (JMS), risk_service, doaj_service

#### Scenario: Authenticated user gets matches for own manuscript

- GIVEN a registered user with a manuscript that has keywords and embeddings
- WHEN GET /api/matches/{manuscript_id} is called with a valid JWT
- THEN a 200 response is returned with up to 10 journal matches
- AND each match includes real JMS scores (7 components)
- AND each match includes risk_assessment with score, level, and indicators
- AND results are sorted by final_score descending

#### Scenario: Unauthenticated request

- GIVEN no Authorization header
- WHEN GET /api/matches/{manuscript_id} is called
- THEN a 401 Unauthorized response is returned

#### Scenario: Manuscript belongs to another user

- GIVEN a valid JWT for User A but manuscript_id belongs to User B
- WHEN GET /api/matches/{manuscript_id} is called
- THEN a 403 Forbidden response is returned

#### Scenario: Manuscript has no keywords

- GIVEN a manuscript with null or empty keywords
- WHEN GET /api/matches/{manuscript_id} is called
- THEN a 400 Bad Request response is returned with a descriptive error

#### Scenario: No journals found

- GIVEN a manuscript with valid keywords but no matching journals from OpenAlex
- WHEN GET /api/matches/{manuscript_id} is called
- THEN a 200 response is returned with an empty results array

### Requirement: JournalMatchResponse Includes Risk Assessment

The schemas MUST include a `RiskAssessment` object in the match response.

(Previously: Only scores and ai_analysis were returned. Risk is now a first-class field.)

#### Scenario: Risk assessment in response

- GIVEN a journal match
- WHEN the response is serialized
- THEN the response includes `risk_assessment: { score: int, level: str, indicators: list[str] }`
