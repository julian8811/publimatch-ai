"""Test configuration.

NOTE: pysqlite3-binary is used to replace the system sqlite3 module
which has an incompatible library linkage on this machine.
"""

import os
import sys

# Replace sqlite3 with pysqlite3 BEFORE any other imports (including stdlib).
import pysqlite3  # noqa: E402

sys.modules["sqlite3"] = pysqlite3

import tempfile  # noqa: E402
from typing import Generator  # noqa: E402

# Set test environment variables BEFORE any app imports.
# If we don't do this, settings like JWT_SECRET_KEY will be empty.
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-testing-do-not-use-in-prod")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("JWT_EXPIRATION_HOURS", "24")
os.environ.setdefault("LOG_LEVEL", "CRITICAL")

import pytest  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, event  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.db.database import get_db  # noqa: E402
from app.main import app as _app  # noqa: E402
from app.models.base import Base  # noqa: E402
from app.models.user import User  # noqa: E402
from app.models.project import Project  # noqa: E402
from app.core.security import hash_password, create_access_token  # noqa: E402

# Use file-based SQLite to avoid in-memory per-connection isolation
_db_fd, _db_path = tempfile.mkstemp(suffix=".test.db")

engine = create_engine(
    f"sqlite:///{_db_path}",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# Enable foreign keys in SQLite
@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


# Create tables that work with SQLite (no PG-specific types like ARRAY, Vector).
User.__table__.create(bind=engine, checkfirst=True)
Project.__table__.create(bind=engine, checkfirst=True)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db() -> Generator[Session, None, None]:
    db_session = TestingSessionLocal()
    try:
        yield db_session
    finally:
        db_session.close()


@pytest.fixture(autouse=True)
def cleanup_db():
    """Delete all data between tests instead of dropping/recreating."""
    yield
    session = TestingSessionLocal()
    # Delete in reverse FK order (projects references users)
    session.execute(Project.__table__.delete())
    session.execute(User.__table__.delete())
    session.commit()
    session.close()


@pytest.fixture
def db() -> Generator[Session, None, None]:
    """Provide a test database session."""
    db_session = TestingSessionLocal()
    try:
        yield db_session
    finally:
        db_session.close()


@pytest.fixture
def app() -> FastAPI:
    """Return the FastAPI app with overridden DB dependency."""
    _app.dependency_overrides[get_db] = override_get_db
    return _app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Provide a TestClient with DB dependency overridden."""
    return TestClient(app)


@pytest.fixture
def test_user_data() -> dict:
    """Default test user registration data."""
    return {
        "email": "test@example.com",
        "password": "testpass123",
        "full_name": "Test User",
        "institution": "Test University",
    }


@pytest.fixture
def test_user(db: Session, test_user_data: dict) -> User:
    """Create a test user directly in the database."""
    user = User(
        email=test_user_data["email"],
        hashed_password=hash_password(test_user_data["password"]),
        full_name=test_user_data["full_name"],
        institution=test_user_data["institution"],
        role="researcher",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user: User) -> dict:
    """Return Authorization headers with a valid token for the test user."""
    token = create_access_token(data={"sub": str(test_user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session", autouse=True)
def cleanup():
    """Clean up the temporary test database after all tests."""
    yield
    os.close(_db_fd)
    os.unlink(_db_path)
