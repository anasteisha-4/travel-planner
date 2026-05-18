import os
import uuid
from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
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
    settings.LLM_QUALITY_ENABLED = False
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


_ML_FEATURE_TABLES = [
    "destination_safety",
    "destination_costs",
    "destination_seasonality",
    "destination_activities",
    "visa_rules",
    "destination_popularity",
    "destination_connectivity",
    "destination_attributes",
    "destination_language_accessibility",
    "destination_infrastructure",
]


@pytest.fixture(scope="session", autouse=True)
def create_ml_feature_tables(create_test_schema):
    """Drop and recreate stub ML feature tables used by get_destination_features / budget router."""
    with engine.connect() as conn:
        for tbl in reversed(_ML_FEATURE_TABLES):
            conn.execute(text(f"DROP TABLE IF EXISTS {tbl} CASCADE"))
        conn.execute(
            text("""
            CREATE TABLE destination_safety (
                destination_id UUID PRIMARY KEY,
                safety_score NUMERIC
            )
        """)
        )
        conn.execute(
            text("""
            CREATE TABLE destination_costs (
                destination_id UUID PRIMARY KEY,
                cost_index NUMERIC,
                avg_daily_cost_usd NUMERIC,
                avg_meal_cost_usd NUMERIC,
                avg_transport_cost_usd NUMERIC,
                avg_hotel_cost_usd NUMERIC,
                hostel_usd NUMERIC,
                budget_usd NUMERIC,
                mid_usd NUMERIC,
                luxury_usd NUMERIC,
                seasonal_multiplier JSONB
            )
        """)
        )
        conn.execute(
            text("""
            CREATE TABLE destination_seasonality (
                destination_id UUID,
                month INTEGER,
                season_score NUMERIC,
                avg_temp_c NUMERIC,
                avg_precipitation_mm NUMERIC,
                avg_humidity_pct NUMERIC,
                PRIMARY KEY (destination_id, month)
            )
        """)
        )
        conn.execute(
            text("""
            CREATE TABLE destination_activities (
                destination_id UUID,
                activity_type TEXT,
                score NUMERIC,
                PRIMARY KEY (destination_id, activity_type)
            )
        """)
        )
        conn.execute(
            text("""
            CREATE TABLE visa_rules (
                citizenship_code TEXT,
                destination_id UUID,
                visa_type TEXT,
                visa_score NUMERIC,
                max_stay_days INTEGER,
                PRIMARY KEY (citizenship_code, destination_id)
            )
        """)
        )
        conn.execute(
            text("""
            CREATE TABLE destination_popularity (
                destination_id UUID,
                month INTEGER,
                crowd_index NUMERIC,
                avg_pageviews NUMERIC,
                PRIMARY KEY (destination_id, month)
            )
        """)
        )
        conn.execute(
            text("""
            CREATE TABLE destination_connectivity (
                destination_id UUID PRIMARY KEY,
                connectivity_score NUMERIC,
                mir_card_accepted BOOLEAN
            )
        """)
        )
        conn.execute(
            text("""
            CREATE TABLE destination_attributes (
                destination_id UUID PRIMARY KEY,
                is_coastal BOOLEAN,
                has_ski BOOLEAN,
                has_thermal BOOLEAN,
                landscape TEXT,
                altitude_m NUMERIC
            )
        """)
        )
        conn.execute(
            text("""
            CREATE TABLE destination_language_accessibility (
                destination_id UUID PRIMARY KEY,
                russian_speaking_score NUMERIC,
                english_speaking_score NUMERIC,
                script_difficulty TEXT
            )
        """)
        )
        conn.execute(
            text("""
            CREATE TABLE destination_infrastructure (
                destination_id UUID PRIMARY KEY,
                has_metro BOOLEAN,
                healthcare_score NUMERIC,
                avg_internet_mbps NUMERIC
            )
        """)
        )
        conn.commit()
