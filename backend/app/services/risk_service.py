"""Journal risk assessment service.

Evaluates potential predatory signals for a journal and produces a
0–100 risk score with a corresponding level (low / medium / high) and
a list of triggered signals.
"""

import logging

logger = logging.getLogger(__name__)


class RiskAssessmentService:
    """Assess journal predatory risk based on multiple behavioural signals.

    Each signal contributes a weight to the total score (capped at 100).
    The risk level is derived from the cumulative score.

    Signal weights (sum = 100 when all triggered):
        no_doaj:           20  — not indexed in DOAJ
        no_scopus:         15  — not indexed in Scopus
        no_wos:            15  — not indexed in Web of Science
        no_issn:           25  — missing ISSN
        fast_publication:  10  — very fast review turnaround (< 4 weeks)
        low_article_count: 10  — very few published articles
        no_publisher_info:  5  — missing or unknown publisher

    Missing data for optional signals is treated conservatively (assumes
    the worst) — if we can't confirm good standing, the signal triggers.
    """

    PREDATORY_SIGNALS = {
        "no_doaj": 20,
        "no_scopus": 15,
        "no_wos": 15,
        "no_issn": 25,
        "fast_publication": 10,
        "low_article_count": 10,
        "no_publisher_info": 5,
    }

    # Thresholds for optional data-driven signals
    FAST_REVIEW_WEEKS = 4  # Fewer weeks than this → potentially predatory
    LOW_CITATION_COUNT = 10  # Cited-by count below this → suspicious

    def assess_journal(self, journal_data: dict) -> dict:
        """Evaluate predatory risk on a 0–100 scale.

        Args:
            journal_data: Dictionary with keys used for signal detection:
                - ``in_doaj`` (bool) — result of DOAJ verification.
                - ``indexed_scopus`` (bool) — Scopus indexation flag.
                - ``indexed_wos`` (bool) — Web of Science indexation flag.
                - ``issn`` (str, optional) — ISSN string.
                - ``publisher`` (str, optional) — publisher name.
                - ``average_review_weeks`` (int, optional) — weeks.
                - ``cited_by_count`` (int, optional) — citation count.

        Returns:
            dict with keys:
                ``risk_score`` (int) — 0–100 cumulative score.
                ``risk_level`` (str) — ``"high"`` (>=50), ``"medium"`` (>=20),
                                       or ``"low"``.
                ``signals`` (list[str]) — names of triggered signals.
        """
        score = 0
        signals_found = []

        # Check DOAJ indexation
        if not journal_data.get("in_doaj"):
            score += self.PREDATORY_SIGNALS["no_doaj"]
            signals_found.append("not_in_doaj")

        # Check Scopus indexation
        if not journal_data.get("indexed_scopus"):
            score += self.PREDATORY_SIGNALS["no_scopus"]
            signals_found.append("not_in_scopus")

        # Check Web of Science indexation
        if not journal_data.get("indexed_wos"):
            score += self.PREDATORY_SIGNALS["no_wos"]
            signals_found.append("not_in_wos")

        # Check ISSN presence
        if not journal_data.get("issn"):
            score += self.PREDATORY_SIGNALS["no_issn"]
            signals_found.append("no_issn")

        # Check fast publication: trigger on missing data OR very short turnaround
        review_weeks = journal_data.get("average_review_weeks")
        if review_weeks is None or (
            isinstance(review_weeks, (int, float))
            and review_weeks < self.FAST_REVIEW_WEEKS
        ):
            score += self.PREDATORY_SIGNALS["fast_publication"]
            signals_found.append("fast_publication")

        # Check low article count / citations: trigger on missing data OR very low
        cited_by = journal_data.get("cited_by_count")
        if cited_by is None or (
            isinstance(cited_by, (int, float)) and cited_by < self.LOW_CITATION_COUNT
        ):
            score += self.PREDATORY_SIGNALS["low_article_count"]
            signals_found.append("low_article_count")

        # Check publisher info
        publisher = journal_data.get("publisher")
        if not publisher or str(publisher).strip().lower() in (
            "unknown",
            "",
            "n/a",
        ):
            score += self.PREDATORY_SIGNALS["no_publisher_info"]
            signals_found.append("no_publisher")

        return {
            "risk_score": min(score, 100),
            "risk_level": "high" if score >= 50 else "medium" if score >= 20 else "low",
            "signals": signals_found,
        }
