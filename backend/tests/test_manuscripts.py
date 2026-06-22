"""Tests for the manuscripts endpoints.

The Manuscript model uses ARRAY(String) for keywords, which SQLite can't
render. We use create_table_safe to create the table with Text columns
instead.  When creating manuscripts via the ORM we avoid passing Python
lists to columns that became Text in the DB.
"""

import io
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.manuscript import Manuscript
from app.models.project import Project
from app.models.user import User
from tests.conftest import engine as test_engine
from tests.helpers import create_table_safe


# Ensure the manuscripts table exists with SQLite-compatible types.
@pytest.fixture(scope="module", autouse=True)
def setup_manuscripts_table():
    """Create the manuscripts table (once per module) with adapted types."""
    create_table_safe(Manuscript, test_engine)


class TestManuscripts:
    """Integration tests for /api/manuscripts/."""

    def _dummy_pdf(self) -> io.BytesIO:
        """Create a minimal valid PDF for upload testing."""
        return io.BytesIO(
            b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
            b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\n"
            b"xref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n"
            b"0000000058 00000 n \n0000000115 00000 n \n"
            b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n190\n%%EOF"
        )

    # ------------------------------------------------------------------
    # Upload — authenticated
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_upload_authenticated(
        self, client: TestClient, db: Session, auth_headers: dict
    ):
        """Authenticated upload returns manuscript data."""
        user = db.query(User).first()
        assert user is not None

        project = Project(name="Test Upload", user_id=user.id)
        db.add(project)
        db.commit()
        db.refresh(project)

        dummy_pdf = self._dummy_pdf()
        response = client.post(
            "/api/manuscripts/upload",
            files={"file": ("test.pdf", dummy_pdf, "application/pdf")},
            data={"project_id": str(project.id)},
            headers=auth_headers,
        )
        assert response.status_code in (201, 200), f"Got {response.status_code}: {response.text}"
        data = response.json()
        assert data["project_id"] == str(project.id)
        assert "id" in data

    # ------------------------------------------------------------------
    # Upload — unauthenticated (401)
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_upload_without_auth_returns_401(self, client: TestClient, db: Session):
        """Upload without auth should return 401."""
        project = Project(name="No Auth")
        db.add(project)
        db.commit()
        db.refresh(project)

        dummy_pdf = self._dummy_pdf()
        response = client.post(
            "/api/manuscripts/upload",
            files={"file": ("test.pdf", dummy_pdf, "application/pdf")},
            data={"project_id": str(project.id)},
        )
        assert response.status_code == 401

    # ------------------------------------------------------------------
    # GET manuscript — authenticated
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_get_manuscript(
        self, client: TestClient, db: Session, auth_headers: dict
    ):
        """GET /api/manuscripts/{id} returns manuscript data."""
        user = db.query(User).first()
        assert user is not None

        project = Project(name="Get Test", user_id=user.id)
        db.add(project)
        db.commit()
        db.refresh(project)

        # Create manuscript via ORM — but skip keywords (ARRAY in model,
        # Text in SQLite; passing a list would crash).
        manuscript = Manuscript(
            project_id=project.id,
            title="Test Manuscript",
            status="processed",
        )
        db.add(manuscript)
        db.commit()
        db.refresh(manuscript)

        response = client.get(
            f"/api/manuscripts/{manuscript.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(manuscript.id)
        assert data["status"] == "processed"

    # ------------------------------------------------------------------
    # GET manuscript — unauthenticated (401)
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_get_manuscript_without_auth_returns_401(
        self, client: TestClient, db: Session
    ):
        """GET /api/manuscripts/{id} without auth returns 401."""
        project = Project(name="Auth Get Test")
        db.add(project)
        db.commit()
        db.refresh(project)

        manuscript = Manuscript(
            project_id=project.id,
            title="Secret",
            status="draft",
        )
        db.add(manuscript)
        db.commit()
        db.refresh(manuscript)

        response = client.get(f"/api/manuscripts/{manuscript.id}")
        assert response.status_code == 401

    # ------------------------------------------------------------------
    # Upload to another user's project (403)
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_upload_to_other_users_project_returns_403(
        self, client: TestClient, db: Session, auth_headers: dict
    ):
        """Uploading to another user's project returns 403."""
        from app.core.security import hash_password

        # Create a second user that exists in the DB (so FK is satisfied).
        other_user = User(
            email="other@manuscripts-test.com",
            hashed_password=hash_password("otherpass123"),
            full_name="Other User",
        )
        db.add(other_user)
        db.commit()
        db.refresh(other_user)

        other_project = Project(name="Other's Project", user_id=other_user.id)
        db.add(other_project)
        db.commit()
        db.refresh(other_project)

        dummy_pdf = self._dummy_pdf()
        response = client.post(
            "/api/manuscripts/upload",
            files={"file": ("test.pdf", dummy_pdf, "application/pdf")},
            data={"project_id": str(other_project.id)},
            headers=auth_headers,
        )
        assert response.status_code == 403
