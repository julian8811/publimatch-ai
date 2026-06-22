"""Unit tests for ScoringService.

The service is pure logic — no DB, no HTTP — so these tests do not need
any fixtures from conftest.
"""

import pytest

from app.services.scoring_service import ScoringService


class TestScoringService:
    """Tests for ScoringService.calculate_journal_match_score."""

    def setup_method(self):
        self.service = ScoringService()

    # ------------------------------------------------------------------
    # Basic score boundaries
    # ------------------------------------------------------------------

    def test_final_score_in_0_100_range(self):
        """Final score should always be between 0 and 100."""
        journal = {
            "cited_by_count": 0,
            "open_access": False,
        }
        result = self.service.calculate_journal_match_score(["keyword"], journal)
        assert 0 <= result["final_score"] <= 100

    def test_top_citations_gives_high_score(self):
        """Very high cited_by_count should cap at 40 for the impact component."""
        journal = {
            "cited_by_count": 999_999_999,
            "open_access": True,
        }
        result = self.service.calculate_journal_match_score(["keyword"], journal)
        # impact = min(999999999 / 100000 * 40, 40) = 40
        # oa = 20
        # relevance = 40
        # final = 40 + 20 + 40 = 100
        assert result["final_score"] == 100.0

    # ------------------------------------------------------------------
    # Edge cases
    # ------------------------------------------------------------------

    def test_zero_citations(self):
        """Zero citations should produce low-ish but non-zero score."""
        journal = {
            "cited_by_count": 0,
            "open_access": False,
        }
        result = self.service.calculate_journal_match_score(["keyword"], journal)
        # impact = 0, oa = 5, relevance = 40 → 45
        assert result["final_score"] == 45.0
        assert result["impact_score"] == 0.0

    def test_empty_keywords(self):
        """Empty keywords should still produce a valid score."""
        journal = {
            "cited_by_count": 1000,
            "open_access": True,
        }
        result = self.service.calculate_journal_match_score([], journal)
        # impact = 1000/100000*40=0.4, oa=20, relevance=40 → 60.4
        assert 0 <= result["final_score"] <= 100
        assert result["relevance_score"] == 40.0  # always 40 in current impl

    # ------------------------------------------------------------------
    # OA vs closed access
    # ------------------------------------------------------------------

    def test_open_access_higher_than_closed(self):
        """OA journal should have higher oa_score than closed-access one."""
        journal_oa = {
            "cited_by_count": 1000,
            "open_access": True,
        }
        journal_closed = {
            "cited_by_count": 1000,
            "open_access": False,
        }
        result_oa = self.service.calculate_journal_match_score(["kw"], journal_oa)
        result_closed = self.service.calculate_journal_match_score(["kw"], journal_closed)

        assert result_oa["oa_score"] > result_closed["oa_score"]
        assert result_oa["oa_score"] == 20.0
        assert result_closed["oa_score"] == 5.0

    # ------------------------------------------------------------------
    # Score component structure
    # ------------------------------------------------------------------

    def test_returns_all_score_components(self):
        """Result dict should contain all expected keys."""
        journal = {
            "cited_by_count": 5000,
            "open_access": True,
        }
        result = self.service.calculate_journal_match_score(["test"], journal)

        assert "final_score" in result
        assert "relevance_score" in result
        assert "impact_score" in result
        assert "oa_score" in result
        assert isinstance(result["final_score"], float)
