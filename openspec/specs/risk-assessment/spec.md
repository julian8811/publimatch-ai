# Risk Assessment Specification

## Purpose

Detect potentially predatory journals by scoring 5 behavioral indicators. Each indicator contributes to a final risk level: Low (0–2), Moderate (3–4), or High (5). The risk assessment is returned alongside each journal match result.

## Requirements

### Requirement: Predatory Indicator Scoring

The system MUST evaluate a journal against 5 predatory indicators, each scored 0 or 1.

**Acceptance Criteria**:

| # | Indicator | Scored 1 when |
|---|-----------|---------------|
| 1 | Excessive APC | APC > $2,000 AND journal is NOT indexed in Scopus or WoS |
| 2 | Unknown Publisher | Publisher name is missing, "Unknown", or a known predatory publisher |
| 3 | No DOAJ Indexation | journal.indexed_doaj is False |
| 4 | No Impact Metrics | journal has no Scopus AND no WoS indexation |
| 5 | Overly Broad Scope | Scope text < 20 chars or contains generic terms (e.g. "multidisciplinary", "all fields") |

Final score = SUM of indicators. Risk level: 0–2 = Low, 3–4 = Moderate, 5 = High.

**Dependencies**: Journal model fields, DOAJ service

#### Scenario: High-risk journal

- GIVEN a journal with APC=$3,000, no Scopus/WoS, no DOAJ, publisher="Unknown", scope="All fields"
- WHEN risk assessment is calculated
- THEN the total score is 5 and risk level is "High"

#### Scenario: Low-risk journal

- GIVEN a journal with APC=$0, indexed in Scopus and DOAJ, publisher="Elsevier", scope="Cardiology research"
- WHEN risk assessment is calculated
- THEN the total score is 0 and risk level is "Low"

### Requirement: Risk Assessment Endpoint Data

The risk assessment MUST be included in the journal match response as a nested object.

**Acceptance Criteria**:
- Response includes `risk_assessment` with fields: `score` (int 0–5), `level` (string), `indicators` (list of triggered indicator descriptions)

#### Scenario: Risk data in match response

- GIVEN a journal match result has been scored for risk
- WHEN the match response is serialized
- THEN it contains `risk_assessment` with `score`, `level`, and `indicators`
