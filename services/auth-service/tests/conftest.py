"""
Test fixtures for auth-service tests
Uses test PostgreSQL database and fakeredis
"""
import os
import pytest
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


def ensure_test_database_exists():
    """Create test database if it doesn't exist"""
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        user="postgres",
        password="postgres",
        database="postgres"
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    
    cursor.execute("SELECT 1 FROM pg_database WHERE datname = 'travel_planner_test'")
    if not cursor.fetchone():
        cursor.execute("CREATE DATABASE travel_planner_test")
        print("Created test database: travel_planner_test")
    
    cursor.close()
    conn.close()


ensure_test_database_exists()

os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/travel_planner_test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-testing-only")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import fakeredis

from app.main import app
from app.database import Base, get_db
from app import redis_client


TEST_DATABASE_URL = os.environ["DATABASE_URL"]
test_engine = create_engine(TEST_DATABASE_URL)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def fake_redis():
    fake = fakeredis.FakeRedis(decode_responses=True)
    return fake


@pytest.fixture(scope="function")
def client(fake_redis):
    Base.metadata.create_all(bind=test_engine)

    app.dependency_overrides[get_db] = override_get_db

    original_get_redis = redis_client.get_redis
    redis_client.get_redis = lambda: fake_redis

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    redis_client.get_redis = original_get_redis
    
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def test_user_data():
    return {
        "email": "test@example.com",
        "login": "testuser",
        "password": "SecurePass123!",
        "first_name": "Test",
        "last_name": "User"
    }


@pytest.fixture
def test_user(client, test_user_data):
    response = client.post("/api/auth/register", json=test_user_data)
    assert response.status_code == 200
    data = response.json()
    return {
        **test_user_data,
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"]
    }


@pytest.fixture
def auth_headers(test_user):
    return {"Authorization": f"Bearer {test_user['access_token']}"}


@pytest.fixture
def second_user_data():
    return {
        "email": "second@example.com",
        "login": "seconduser",
        "password": "AnotherPass456!",
        "first_name": "Second",
        "last_name": "User"
    }
