# DOAJ Verification Specification

## Purpose

Integrate with the DOAJ (Directory of Open Access Journals) API to verify a journal's open access status and indexation. The result feeds the risk assessment indicator #3 and confirms `indexed_doaj`.

## Requirements

### Requirement: DOAJ API Lookup

The system MUST look up a journal by ISSN on the DOAJ API and return its open access status.

**Acceptance Criteria**:
- Lookup MUST use the DOAJ public API endpoint: `https://doaj.org/api/v2/search/journals`
- Query MUST search by ISSN (print or online)
- Response MUST return `is_oa: bool` and `doaj_url: str | None`
- API failure (timeout, non-200) MUST return a safe default (not OA, None)

**Dependencies**: httpx, DOAJ public API (no auth key needed for search)

#### Scenario: Journal found in DOAJ

- GIVEN a journal with ISSN "1932-6203" (PLOS ONE)
- WHEN the DOAJ service is called
- THEN it returns `is_oa: True` and a valid `doaj_url`

#### Scenario: Journal not in DOAJ

- GIVEN a journal with ISSN not registered in DOAJ
- WHEN the DOAJ service is called
- THEN it returns `is_oa: False` and `doaj_url: None`

#### Scenario: DOAJ API is unreachable

- GIVEN the DOAJ API is down or returns a non-200 status
- WHEN the DOAJ service is called
- THEN it returns `is_oa: False` and `doaj_url: None` WITHOUT raising an exception

### Requirement: DOAJ Flag Persistence

When a verified DOAJ status is obtained, the system MUST update the journal's `indexed_doaj` flag in the database.

**Acceptance Criteria**:
- `indexed_doaj` MUST be set to True when DOAJ confirms the journal
- `indexed_doaj` MUST be set to False when DOAJ does not find the journal
- The update MUST be persisted to the database

#### Scenario: DOAJ verification updates database

- GIVEN a journal record with `indexed_doaj = None`
- WHEN DOAJ verification returns is_oa=True
- THEN the journal's `indexed_doaj` column is set to True
