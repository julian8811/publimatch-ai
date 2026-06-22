"""Tests for the matches endpoints.

The manuscripts table uses ARRAY(String) for keywords (adapted to Text on
SQLite). We mock the external services (OpenAlex, Scoring, LLM) at the
endpoint module level to get deterministic test data.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.manuscript import Manuscript
from app.models.project import Project
from app.models.user import User
from tests.conftest import engine as test_engine
from tests.helpers import create_table_safe


# Ensure tables exist
@pytest.fixture(scope="module", autouse=True)
def setup_tables():
    create_table_safe(Manuscript, test_engine)


# Sample journals returned by the mocked OpenAlex service
MOCK_JOURNALS = [
    {
        "openalex_id": "https://openalex.org/S123",
        "name": "Journal of Alpha Research",
        "issn_print": "1234-5678",
        "publisher": "Alpha Publishing",
        "country": "US",
        "open_access": True,
        "apc_usd": 1500.0,
        "homepage_url": "https://alpha-research.example.com",
        "cited_by_count": 50000,
    },
    {
        "openalex_id": "https://openalex.org/S456",
        "name": "Beta Science Quarterly",
        "issn_print": "9876-5432",
        "publisher": "Beta Press",
        "country": "GB",
        "open_access": False,
        "apc_usd": 0.0,
        "homepage_url": "https://beta-science.example.com",
        "cited_by_count": 2000,
    },
    {
        "openalex_id": "https://openalex.org/S789",
        "name": "Gamma Letters",
        "issn_print": "1111-2222",
        "publisher": "Gamma Inc",
        "country": "DE",
        "open_access": True,
        "apc_usd": 2500.0,
        "homepage_url": "https://gamma.example.com",
        "cited_by_count": 100,
    },
]

# Scores returned by the mocked ScoringService
MOCK_SCORES = {
    "final_score": 85.5,
    "semantic_score": 35.0,
    "impact_score": 25.0,
    "oa_score": 20.0,
    "indexing_score": 10.0,
    "language_score": 5.0,
    "cost_score": 3.0,
}


class TestMatches:
    """Integration tests for GET /api/matches/{id}."""

    def _create_manuscript(self, db: Session, user: User, keywords_str: str = "") -> uuid.UUID:
        """Create a project + manuscript owned by *user* and return the manuscript id."""
        project = Project(name="Matches Test", user_id=user.id)
        db.add(project)
        db.commit()
        db.refresh(project)

        # Raw INSERT via text() to avoid ARRAY–SQLite bind issues.
        from sqlalchemy import text as sa_text

        manuscript_id = uuid.uuid4()
        db.execute(
            sa_text(
                "INSERT INTO manuscripts "
                "(id, project_id, title, abstract, status, keywords) "
                "VALUES (:id, :pid, :title, :abstract, :status, :kw)"
            ),
            {
                "id": manuscript_id.hex,
                "pid": project.id.hex,
                "title": "Test Manuscript",
                "abstract": "A test abstract about alpha and beta research.",
                "status": "processed",
                "kw": keywords_str or None,
            },
        )
        db.commit()
        return manuscript_id

    # ------------------------------------------------------------------
    # Without auth → 401
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_matches_without_auth_returns_401(self, client: TestClient, db: Session):
        """GET /api/matches/{id} without auth should return 401."""
        user = db.query(User).first()
        if not user:
            from app.core.security import hash_password
            user = User(email="nobody@test.com", hashed_password=hash_password("x"))
            db.add(user)
            db.commit()
            db.refresh(user)

        manuscript_id = self._create_manuscript(db, user)
        response = client.get(f"/api/matches/{manuscript_id}")
        assert response.status_code == 401

    # ------------------------------------------------------------------
    # Authenticated — no keywords → 400
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_matches_no_keywords_returns_400(
        self, client: TestClient, db: Session, auth_headers: dict
    ):
        """Manuscript without extracted keywords should return 400."""
        user = db.query(User).first()
        assert user is not None
        manuscript_id = self._create_manuscript(db, user, keywords_str="")

        response = client.get(
            f"/api/matches/{manuscript_id}",
            headers=auth_headers,
        )
        assert response.status_code == 400

    # ------------------------------------------------------------------
    # Authenticated — full match pipeline
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_matches_authenticated_with_mocked_services(
        self, client: TestClient, db: Session, auth_headers: dict, monkeypatch
    ):
        """Authenticated match request returns scored results sorted descending."""
        user = db.query(User).first()
        assert user is not None
        manuscript_id = self._create_manuscript(
            db, user, keywords_str='["alpha", "beta", "research"]'
        )

        # Mock the three services at the endpoint module level
        import app.api.endpoints.matches as matches_mod

        async def mock_fetch(*args, **kwargs):
            return MOCK_JOURNALS

        def mock_score(keywords, journal_data, **kwargs):
            return dict(MOCK_SCORES)

        async def mock_analysis(*args, **kwargs):
            return {
                "compatibility_reason": "Good fit.",
                "predatory_risk": "Low",
                "submission_strategy": "Submit directly.",
            }

        monkeypatch.setattr(
            matches_mod.openalex_service, "fetch_journals_by_concept", mock_fetch
        )
        monkeypatch.setattr(
            matches_mod.scoring_service, "calculate_journal_match_score", mock_score
        )
        monkeypatch.setattr(
            matches_mod.llm_service, "analyze_journal_compatibility", mock_analysis
        )

        response = client.get(
            f"/api/matches/{manuscript_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 3

        # Check structure
        for item in data:
            assert "openalex_id" in item
            assert "name" in item
            assert "scores" in item
            assert "final_score" in item["scores"]

        # Verify sorted by final_score descending
        scores = [j["scores"]["final_score"] for j in data]
        assert scores == sorted(scores, reverse=True)
