"""Weighted Journal Match Score (JMS) engine.

Computes a 0–100 composite score from 6 weighted components:

    Semantic Relevance (35%) — cosine similarity via embeddings, fallback to keyword
    Journal Impact    (20%) — normalized OpenAlex cited_by_count
    Open Access       (20%) — binary boost
    Indexation        (10%) — Scopus / WoS / DOAJ / Latindex coverage
    Language Match    (10%) — manuscript language vs journal languages
    APC Cost          ( 5%) — inverse APC penalty

Each sub-score is normalized to 0–1 before weighting.
Final score = SUM(component × weight) × 100, capped at 100.
"""

import logging
import math

logger = logging.getLogger(__name__)


class ScoringService:
    """Journal Match Score calculator with weighted components.

    Designed to work with either OpenAlex journal dicts (for the initial
    async match) or full Journal ORM models (for DB-based re-scoring).
    """

    # Weights sum to 100% — these are the "JMS weights from the spec"
    JMS_WEIGHTS = {
        "semantic": 0.35,
        "impact": 0.20,
        "oa": 0.20,
        "indexing": 0.10,
        "language": 0.10,
        "cost": 0.05,
    }

    # Maximum APC in USD above which the cost score is 0
    APC_MAX_USD = 3000.0

    # Number of indexed databases considered
    INDEXED_DB_COUNT = 4  # scopus, wos, doaj, latindex

    def calculate_journal_match_score(
        self,
        manuscript_keywords: list[str],
        journal_data: dict,
        manuscript=None,
    ) -> dict:
        """Calculate the full weighted JMS for a single journal.

        Args:
            manuscript_keywords: Keywords extracted from the manuscript.
            journal_data: Flat dict from OpenAlex OR (eventually) a Journal
                          ORM model converted to dict with ``__dict__``.
            manuscript: Optional Manuscript ORM model for embedding access.
                        Currently unused; semantic falls back to keyword
                        similarity when embeddings are absent.

        Returns:
            dict with keys: final_score, semantic_score, impact_score,
                            oa_score, indexing_score, language_score,
                            cost_score — all as 0–100 floats.
        """
        # Compute raw sub-scores (0–1 normalized)
        semantic = self._semantic_score(manuscript_keywords, journal_data, manuscript)
        impact = self._impact_score(journal_data)
        oa = self._oa_score(journal_data)
        indexing = self._indexing_score(journal_data)
        language = self._language_score(journal_data)
        cost = self._cost_score(journal_data)

        # Weighted sum → 0–100
        weighted = (
            semantic * self.JMS_WEIGHTS["semantic"]
            + impact * self.JMS_WEIGHTS["impact"]
            + oa * self.JMS_WEIGHTS["oa"]
            + indexing * self.JMS_WEIGHTS["indexing"]
            + language * self.JMS_WEIGHTS["language"]
            + cost * self.JMS_WEIGHTS["cost"]
        )
        final_score = min(round(weighted * 100, 1), 100.0)

        return {
            "final_score": final_score,
            "semantic_score": round(semantic * 100, 1),
            "impact_score": round(impact * 100, 1),
            "oa_score": round(oa * 100, 1),
            "indexing_score": round(indexing * 100, 1),
            "language_score": round(language * 100, 1),
            "cost_score": round(cost * 100, 1),
        }

    # ------------------------------------------------------------------
    # Sub-score methods (each returns 0.0–1.0)
    # ------------------------------------------------------------------

    def _semantic_score(
        self,
        keywords: list[str],
        journal_data: dict,
        manuscript=None,
    ) -> float:
        """Semantic relevance via keyword overlap Jaccard similarity.

        When DB embeddings are available (future), this method will use
        pgvector cosine similarity between manuscript_embedding and
        journal.scope_embedding.  For now, falls back to Jaccard on
        keyword overlap with the journal name / scope text.
        """
        # Attempt embedding-based scoring if both embeddings exist
        if manuscript is not None and hasattr(manuscript, "manuscript_embedding"):
            ms_emb = manuscript.manuscript_embedding
            journal_emb = journal_data.get("scope_embedding")
            if ms_emb is not None and journal_emb is not None:
                from app.services.embedding_service import EmbeddingService

                sim = EmbeddingService.compute_cosine_similarity(ms_emb, journal_emb)
                if sim > 0:
                    return min(sim, 1.0)

        # Fallback: Jaccard similarity between keywords and journal name
        journal_name = (journal_data.get("name") or "").lower()
        scope_text = (journal_data.get("scope") or "").lower()
        combined_text = f"{journal_name} {scope_text}"

        if not keywords or not combined_text.strip():
            return 0.0

        keyword_set = {kw.lower().strip() for kw in keywords if kw.strip()}
        if not keyword_set:
            return 0.0

        # Count how many keywords appear in the journal name/scope
        matches = sum(1 for kw in keyword_set if kw in combined_text)
        return matches / len(keyword_set)

    def _impact_score(self, journal_data: dict) -> float:
        """Normalized journal impact from cited_by_count.

        Formula: min(cited_by_count / 100_000, 1.0)
        A journal with 100k+ citations gets a full 1.0 raw impact.
        """
        citations = float(journal_data.get("cited_by_count") or 0)
        return min(citations / 100_000.0, 1.0)

    def _oa_score(self, journal_data: dict) -> float:
        """Open Access boost.

        OA journal → 1.0.  Non-OA → 0.25 (still has some discoverability).
        """
        return 1.0 if journal_data.get("open_access", False) else 0.25

    def _indexing_score(self, journal_data: dict) -> float:
        """Indexation coverage across Scopus, WoS, DOAJ, Latindex.

        Counts True-ish values for indexed_* fields and divides by 4.
        Works with both OpenAlex dicts (where these may be absent → 0)
        and DB Journal objects (where they're proper booleans).
        """
        count = 0
        for field in ("indexed_scopus", "indexed_wos", "indexed_doaj", "indexed_latindex"):
            if journal_data.get(field):
                count += 1
        return count / self.INDEXED_DB_COUNT

    def _language_score(self, journal_data: dict) -> float:
        """Language match between manuscript and journal.

        If the journal has no language restriction (languages is None/empty),
        assume a match → 1.0.
        Otherwise, check if the manuscript language (in journal_data) overlaps.
        For OpenAlex dicts, language info is rarely available → default match.
        """
        journal_languages = journal_data.get("languages")
        manuscript_lang = journal_data.get("manuscript_language")

        # No language data available → assume match
        if not journal_languages or not manuscript_lang:
            return 1.0

        if isinstance(journal_languages, list):
            return 1.0 if manuscript_lang in journal_languages else 0.0

        # Single language string
        return 1.0 if manuscript_lang == str(journal_languages) else 0.0

    def _cost_score(self, journal_data: dict) -> float:
        """Inverse APC cost penalty.

        $0 APC → 1.0 (max score)
        Linear decay to $APC_MAX_USD → 0.0
        Above $APC_MAX_USD → 0.0
        """
        apc = float(journal_data.get("apc_usd") or 0)
        if apc <= 0:
            return 1.0
        if apc >= self.APC_MAX_USD:
            return 0.0
        return 1.0 - (apc / self.APC_MAX_USD)
