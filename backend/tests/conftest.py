"""Shared pytest fixtures for all backend tests.

Provides:
- db_url: sync PostgreSQL URL pointing at the test database
- test_engine: SQLAlchemy engine scoped to the test session
"""
import os
import pytest
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
