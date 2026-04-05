"""Shared pytest fixtures for all backend tests.

Provides:
- db_url: sync PostgreSQL URL pointing at the test database
- test_engine: SQLAlchemy engine scoped to the test session
- mock_db_session: AsyncMock database session that is wired into app.dependency_overrides
  so that API router tests can run without a real database connection.
"""
import os
import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy import create_engine, text


# Use TEST_DATABASE_URL env var if set, otherwise fall back to default
# (allows CI to override without code changes)
TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://citydata:citydata@localhost:5432/citydata",
).replace("+asyncpg", "")


@pytest.fixture(scope="session")
def db_url() -> str:
    """Return the sync database URL for use in tests."""
    return TEST_DB_URL


@pytest.fixture(scope="session")
def db_engine(db_url):
    """SQLAlchemy engine connected to test database."""
    engine = create_engine(db_url)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def db_conn(db_engine):
    """A single database connection reused across the test session."""
    with db_engine.connect() as conn:
        yield conn


def _make_mock_session() -> AsyncMock:
    """Build an AsyncMock that mimics an AsyncSession with empty query results."""
    session = AsyncMock()
    # result.mappings().all() → empty list
    result_mock = MagicMock()
    result_mock.mappings.return_value.all.return_value = []
    session.execute.return_value = result_mock
    return session


@pytest.fixture(autouse=True)
def override_get_db(request):
    """Override app.db.get_db for all tests that import app.main.

    This prevents any test from accidentally hitting a real database via
    the FastAPI dependency injection path. Tests that need a real DB connection
    should use the db_conn fixture directly.

    Skip the override if the test is marked with @pytest.mark.uses_real_db.
    """
    if request.node.get_closest_marker("uses_real_db"):
        yield
        return

    # Only apply to tests that load the FastAPI app
    try:
        from app.main import app
        from app.db import get_db
    except ImportError:
        yield
        return

    async def _mock_get_db():
        yield _make_mock_session()

    app.dependency_overrides[get_db] = _mock_get_db
    yield
    # Clean up only our override, leave others (like get_current_town) intact
    app.dependency_overrides.pop(get_db, None)
