import os
import uuid
from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base, get_db
from app.deps import get_current_user_id
from app.main import app

_base_url = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/travel_planner",
)
TEST_SCHEMA = "ml_test"
SQLALCHEMY_TEST_URL = f"{_base_url}?options=-csearch_path%3D{TEST_SCHEMA}"

engine = create_engine(SQLALCHEMY_TEST_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

TEST_USER_ID = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-111111111111")


def override_get_db() -> Generator[Session, None, None]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def override_get_current_user_id() -> uuid.UUID:
    return TEST_USER_ID


@pytest.fixture(scope="session", autouse=True)
def create_test_schema():
    base_engine = create_engine(_base_url)
    with base_engine.connect() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {TEST_SCHEMA}"))
        conn.commit()
    base_engine.dispose()

    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

    base_engine = create_engine(_base_url)
    with base_engine.connect() as conn:
        conn.execute(text(f"DROP SCHEMA IF EXISTS {TEST_SCHEMA} CASCADE"))
        conn.commit()
    base_engine.dispose()
    engine.dispose()


@pytest.fixture(autouse=True)
def clean_tables():
    yield
    db = TestingSessionLocal()
    try:
        for table in reversed(Base.metadata.sorted_tables):
            db.execute(table.delete())
        db.commit()
    finally:
        db.close()


@pytest.fixture
def db() -> Generator[Session, None, None]:
    yield from override_get_db()


@pytest.fixture(scope="session")
def _setup_overrides():
    fake_redis = MagicMock()
    fake_redis.exists.return_value = 0

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user_id] = override_get_current_user_id

    with patch("app.deps.get_redis", return_value=fake_redis):
        yield

    app.dependency_overrides.clear()


@pytest.fixture
def client(_setup_overrides) -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c
