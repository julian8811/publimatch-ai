# Journal Scoring Specification

## Purpose

Replace the placeholder scoring logic with a real Journal Match Score (JMS) algorithm. The score combines 7 weighted components: semantic relevance (via Gemini embeddings), journal impact, open access, indexation, language match, APC reasonableness, and review speed. Embeddings are stored in pgvector for cosine-similarity queries.

## Requirements

### Requirement: Embedding Generation for Manuscripts

The system MUST generate a 768-dimension embedding for each manuscript abstract using the Gemini embedding model.

**Acceptance Criteria**:
- Embedding MUST be generated asynchronously via Celery worker
- Embedding MUST be stored in a new `manuscript_embedding` column on the `manuscripts` table
- Missing API key MUST raise a clear error

**Dependencies**: Google Generative AI SDK, Celery worker

#### Scenario: Embedding generated successfully

- GIVEN a manuscript with an abstract
- WHEN the Celery task `generate_embedding` runs
- THEN a 768-dimension vector is stored in `manuscripts.manuscript_embedding`

#### Scenario: API key missing

- GIVEN no Gemini API key is configured
- WHEN embedding generation is attempted
- THEN the task fails with a logged error and the manuscript status is set to "error"

### Requirement: Journal Embedding from Scope

The system MUST generate and store a 768-dimension embedding for each journal's scope text when the journal is first created.

**Acceptance Criteria**:
- The existing `journals.scope_embedding` (dim=1536) MUST be replaced or supplemented with a 768-dimension embedding
- Embedding MUST be computed from the journal's scope field

#### Scenario: New journal with scope

- GIVEN a journal with a non-empty scope field and no existing embedding
- WHEN the scoring service accesses the journal
- THEN a 768-dimension scope_embedding is generated and persisted

### Requirement: Weighted JMS Calculation

The system MUST compute a 0–100 final score from 7 weighted components, each normalized 0–100.

**Acceptance Criteria**:

| Component | Weight | Data Source |
|-----------|--------|-------------|
| Semantic Relevance | 30% | Cosine similarity (manuscript_embedding × scope_embedding) |
| Journal Impact | 20% | OpenAlex cited_by_count normalized |
| Open Access | 15% | Boolean flag |
| Indexation | 15% | Count of indexed databases (Scopus, WoS, DOAJ, Latindex) |
| Language Match | 10% | Match between manuscript language and journal languages |
| APC Reasonableness | 5% | APC amount relative to journal type (OA vs subscription) |
| Review Speed | 5% | Inverse of average_review_weeks |

Final score = SUM(component_score × weight) rounded to 1 decimal.

#### Scenario: Complete scoring with all data

- GIVEN a manuscript with embedding and a journal with embedding, indexation data, language, APC, and review speed
- WHEN `calculate_journal_match_score` is called
- THEN a dict with `final_score`, `semantic_score`, `impact_score`, `oa_score`, `indexation_score`, `language_score`, `apc_score`, and `review_speed_score` is returned

#### Scenario: Missing journal embedding

- GIVEN a journal without a scope_embedding
- WHEN scoring is calculated
- THEN the semantic relevance component is scored as 0 and calculation continues with remaining components
