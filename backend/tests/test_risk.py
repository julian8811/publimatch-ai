"""Unit tests for RiskAssessmentService.

All tests use pure logic with no DB or HTTP dependencies.
"""

import pytest

from app.services.risk_service import RiskAssessmentService


# Journal with no predatory signals (clean baseline)
CLEAN_JOURNAL = {
    "in_doaj": True,
    "indexed_scopus": True,
    "indexed_wos": True,
    "issn": "1234-5678",
    "publisher": "Springer",
    "average_review_weeks": 12,
    "cited_by_count": 50000,
}


class TestRiskAssessmentService:
    """Tests for RiskAssessmentService.assess_journal."""

    def setup_method(self):
        self.service = RiskAssessmentService()

    # ------------------------------------------------------------------
    # Boundary: all signals triggered → high risk
    # ------------------------------------------------------------------

    def test_all_signals_high_risk(self):
        """All predatory signals present should yield risk_score=100 and level='high'."""
        journal = {
            "in_doaj": False,
            "indexed_scopus": False,
            "indexed_wos": False,
            "issn": None,
            "publisher": None,
            # Missing optional fields → conservative trigger
        }
        result = self.service.assess_journal(journal)
        assert result["risk_score"] == 100
        assert result["risk_level"] == "high"

    # ------------------------------------------------------------------
    # Boundary: no signals → low risk
    # ------------------------------------------------------------------

    def test_no_signals_low_risk(self):
        """No predatory signals should yield risk_score=0 and level='low'."""
        result = self.service.assess_journal(CLEAN_JOURNAL)
        assert result["risk_score"] == 0
        assert result["risk_level"] == "low"

    # ------------------------------------------------------------------
    # Partial signals → medium risk
    # ------------------------------------------------------------------

    def test_partial_signals_medium_risk(self):
        """Some signals triggered should yield medium risk."""
        journal = {**CLEAN_JOURNAL,
            "in_doaj": False,          # 20 pts
            "indexed_scopus": False,    # 15 pts
        }
        result = self.service.assess_journal(journal)
        # Total = 20 + 15 = 35 → medium
        assert result["risk_score"] == 35
        assert result["risk_level"] == "medium"

    def test_boundary_low_to_medium(self):
        """Score of exactly 20 should be medium."""
        journal = {**CLEAN_JOURNAL,
            "in_doaj": False,           # 20 pts
        }
        result = self.service.assess_journal(journal)
        # Total = 20 → medium (threshold >= 20)
        assert result["risk_score"] == 20
        assert result["risk_level"] == "medium"

    def test_boundary_medium_to_high(self):
        """Score of exactly 50 should be high."""
        journal = {**CLEAN_JOURNAL,
            "in_doaj": False,           # 20 pts
            "indexed_scopus": False,    # 15 pts
            "indexed_wos": False,       # 15 pts
        }
        result = self.service.assess_journal(journal)
        # Total = 20 + 15 + 15 = 50 → high
        assert result["risk_score"] == 50
        assert result["risk_level"] == "high"

    # ------------------------------------------------------------------
    # Signals list contains only triggered ones
    # ------------------------------------------------------------------

    def test_signals_list_only_triggered(self):
        """Only triggered signals should appear in the signals list."""
        journal = {**CLEAN_JOURNAL,
            "in_doaj": False,           # triggered → not_in_doaj
        }
        result = self.service.assess_journal(journal)
        assert "not_in_doaj" in result["signals"]
        assert "not_in_scopus" not in result["signals"]
        assert "not_in_wos" not in result["signals"]
        assert "no_issn" not in result["signals"]
        assert "no_publisher" not in result["signals"]

    # ------------------------------------------------------------------
    # Edge cases
    # ------------------------------------------------------------------

    def test_no_issn_triggers_signal(self):
        """Missing ISSN should add 'no_issn' to signals."""
        journal = {**CLEAN_JOURNAL, "issn": ""}
        result = self.service.assess_journal(journal)
        assert "no_issn" in result["signals"]

    def test_unknown_publisher_triggers_signal(self):
        """Publisher value 'Unknown' should add 'no_publisher' to signals."""
        journal = {**CLEAN_JOURNAL, "publisher": "Unknown"}
        result = self.service.assess_journal(journal)
        assert "no_publisher" in result["signals"]

    def test_empty_journal_data(self):
        """Empty dict should score 100 (all signals triggered conservatively)."""
        result = self.service.assess_journal({})
        assert result["risk_score"] == 100
        assert result["risk_level"] == "high"

    def test_signal_weights_sum(self):
        """Verify that all signal weights sum to exactly 100."""
        total = sum(self.service.PREDATORY_SIGNALS.values())
        assert total == 100

    # ------------------------------------------------------------------
    # Optional data-driven signals
    # ------------------------------------------------------------------

    def test_fast_publication_triggers_with_low_weeks(self):
        """average_review_weeks < 4 should trigger fast_publication."""
        journal = {**CLEAN_JOURNAL, "average_review_weeks": 2}
        result = self.service.assess_journal(journal)
        assert "fast_publication" in result["signals"]
        assert result["risk_score"] == 10  # Only fast_publication triggers

    def test_fast_publication_not_triggered_with_normal_weeks(self):
        """average_review_weeks >= 4 should NOT trigger fast_publication."""
        journal = {**CLEAN_JOURNAL, "average_review_weeks": 8}
        result = self.service.assess_journal(journal)
        assert "fast_publication" not in result["signals"]

    def test_low_article_count_triggers_with_low_citations(self):
        """cited_by_count < 10 should trigger low_article_count."""
        journal = {**CLEAN_JOURNAL, "cited_by_count": 0}
        result = self.service.assess_journal(journal)
        assert "low_article_count" in result["signals"]
        assert result["risk_score"] == 10  # Only low_article_count triggers
