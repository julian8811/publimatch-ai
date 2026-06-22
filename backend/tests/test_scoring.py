"""Unit tests for ScoringService with the real weighted JMS algorithm.

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

    def test_max_citations_gives_high_impact(self):
        """Very high cited_by_count should cap impact at 20 contribution."""
        journal = {
            "cited_by_count": 999_999_999,
            "open_access": True,
        }
        result = self.service.calculate_journal_match_score(["keyword"], journal)
        # impact_raw = 1.0, impact_contribution = 1.0 * 0.20 * 100 = 20
        # oa_raw = 1.0, oa_contribution = 1.0 * 0.20 * 100 = 20
        # semantic (keyword in name): keyword not in name, so 0
        # final minimum: 0 + 20 + 20 + 0 + 10 + 5 = 55
        assert result["final_score"] > 50
        assert result["impact_score"] == pytest.approx(100.0, abs=1)

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
        # oa=0.25*100*0.20=5, language=1.0*100*0.10=10, cost=1.0*100*0.05=5
        # semantic=0, impact=0, indexing=0
        # final = 0 + 0 + 5 + 0 + 10 + 5 = 20
        assert pytest.approx(result["final_score"], abs=1) == 20.0
        assert result["impact_score"] == 0.0

    def test_empty_keywords(self):
        """Empty keywords should still produce a valid score (semantic = 0)."""
        journal = {
            "cited_by_count": 1000,
            "open_access": True,
        }
        result = self.service.calculate_journal_match_score([], journal)
        # impact_raw = 0.01, oa_raw = 1.0
        assert 0 <= result["final_score"] <= 100
        assert result["semantic_score"] == 0.0

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
        assert result_oa["oa_score"] == 100.0
        assert result_closed["oa_score"] == 25.0

    # ------------------------------------------------------------------
    # Sub-score value ranges
    # ------------------------------------------------------------------

    def test_semantic_score_with_matching_keyword(self):
        """Keyword matching should produce a semantic > 0 when keyword is in journal name."""
        journal = {"name": "Journal of Keyword Research"}
        result = self.service.calculate_journal_match_score(
            ["keyword", "research"], journal
        )
        # "keyword" is not in the name, but "research" is → 1/2 = 0.5 raw
        # 0.5 * 100 = 50 for semantic_score
        assert result["semantic_score"] > 0

    def test_semantic_score_with_no_match(self):
        """No keyword match should give 0 semantic score."""
        journal = {"name": "Alpha Beta Gamma"}
        result = self.service.calculate_journal_match_score(
            ["xyz", "zzz"], journal
        )
        assert result["semantic_score"] == 0.0

    def test_cost_score_zero_apc(self):
        """Zero APC should give full cost_score."""
        result = self.service._cost_score({"apc_usd": 0})
        assert result == 1.0

    def test_cost_score_high_apc(self):
        """Very high APC should give zero cost_score."""
        result = self.service._cost_score({"apc_usd": 5000})
        assert result == 0.0

    def test_cost_score_mid_apc(self):
        """APC at $1500 (half of max) should give 0.5 raw score."""
        result = self.service._cost_score({"apc_usd": 1500})
        assert result == pytest.approx(0.5, abs=0.01)

    def test_indexing_score_all_true(self):
        """All 4 indexed fields true = 1.0 raw."""
        journal = {
            "indexed_scopus": True,
            "indexed_wos": True,
            "indexed_doaj": True,
            "indexed_latindex": True,
        }
        assert self.service._indexing_score(journal) == 1.0

    def test_indexing_score_none_true(self):
        """No indexed fields = 0.0 raw."""
        journal = {
            "indexed_scopus": False,
            "indexed_wos": False,
            "indexed_doaj": False,
            "indexed_latindex": False,
        }
        assert self.service._indexing_score(journal) == 0.0

    def test_indexing_score_missing_keys(self):
        """Missing indexed_* keys should be treated as False."""
        journal = {}
        assert self.service._indexing_score(journal) == 0.0

    # ------------------------------------------------------------------
    # Score component structure
    # ------------------------------------------------------------------

    def test_returns_all_score_components(self):
        """Result dict should contain all expected keys for the new JMS."""
        journal = {
            "cited_by_count": 5000,
            "open_access": True,
        }
        result = self.service.calculate_journal_match_score(["test"], journal)

        assert "final_score" in result
        assert "semantic_score" in result
        assert "impact_score" in result
        assert "oa_score" in result
        assert "indexing_score" in result
        assert "language_score" in result
        assert "cost_score" in result
        assert isinstance(result["final_score"], float)

    def test_old_keys_not_present(self):
        """Old key names (relevance_score) should not be in the result."""
        journal = {
            "cited_by_count": 5000,
            "open_access": True,
        }
        result = self.service.calculate_journal_match_score(["test"], journal)
        assert "relevance_score" not in result

    def test_high_score_scenario(self):
        """A journal with max citations, OA, indexed, matching keywords should score high."""
        journal = {
            "cited_by_count": 200_000,
            "open_access": True,
            "name": "Journal of Keyword and Research Studies",
            "indexed_scopus": True,
            "indexed_wos": True,
            "indexed_doaj": True,
            "indexed_latindex": True,
        }
        result = self.service.calculate_journal_match_score(
            ["keyword", "research"], journal
        )
        # Both "keyword" and "research" appear in the name → 2/2 = 1.0 raw semantic
        # semantic: 1.0 → 1.0*0.35*100 = 35 pts
        # impact: min(200000/100000, 1) = 1.0 → 1.0*0.20*100 = 20 pts
        # oa: 1.0 → 1.0*0.20*100 = 20 pts
        # indexing: 4/4 = 1.0 → 1.0*0.10*100 = 10 pts
        # language: default match → 1.0 → 1.0*0.10*100 = 10 pts
        # cost: no apc data → 1.0 → 1.0*0.05*100 = 5 pts
        # total = 35 + 20 + 20 + 10 + 10 + 5 = 100
        assert result["final_score"] == 100.0
        assert result["final_score"] > 80
