import os
from datetime import datetime, timedelta
from uuid import uuid4

import fakeredis
import psycopg2
import pytest
from fastapi.testclient import TestClient
from jose import jwt
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import deps
from app.config import settings
from app.database import Base, get_db
from app.main import app


def ensure_test_database_exists():
    db_host = os.environ.get("POSTGRES_HOST", "postgres")
    conn = psycopg2.connect(host=db_host, port=5432, user="postgres", password="postgres", database="postgres")
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()

    cursor.execute("SELECT 1 FROM pg_database WHERE datname = 'travel_planner_trips_test'")
    if not cursor.fetchone():
        cursor.execute("CREATE DATABASE travel_planner_trips_test")

    cursor.close()
    conn.close()


ensure_test_database_exists()

db_host = os.environ.get("POSTGRES_HOST", "postgres")
os.environ.setdefault("DATABASE_URL", f"postgresql://postgres:postgres@{db_host}:5432/travel_planner_trips_test")
os.environ.setdefault("REDIS_URL", f"redis://{os.environ.get('REDIS_HOST', 'redis')}:6379/0")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-testing-only")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")

TEST_DATABASE_URL = os.environ["DATABASE_URL"]
test_engine = create_engine(TEST_DATABASE_URL)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_test_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "type": "access",
        "jti": str(uuid4()),
        "exp": datetime.utcnow() + timedelta(minutes=30),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


@pytest.fixture(scope="function")
def fake_redis():
    return fakeredis.FakeRedis(decode_responses=True)


@pytest.fixture(scope="function")
def client(fake_redis):
    Base.metadata.create_all(bind=test_engine)

    app.dependency_overrides[get_db] = override_get_db
    original_get_redis = deps.get_redis
    deps.get_redis = lambda: fake_redis

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    deps.get_redis = original_get_redis
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def user_id():
    return str(uuid4())


@pytest.fixture
def auth_headers(user_id):
    token = create_test_token(user_id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def other_user_headers():
    token = create_test_token(str(uuid4()))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def trip_data():
    return {
        "title": "Отпуск в Турции",
        "destination": "Стамбул",
        "start_date": "2026-06-01",
        "end_date": "2026-06-14",
        "budget": 150000,
        "currency": "RUB",
        "people_count": 2,
        "notes": "Запланировать экскурсии",
    }
