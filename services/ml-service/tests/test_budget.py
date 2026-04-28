import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

DEST_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


@pytest.fixture(autouse=True)
def seed_costs(db: Session):
    db.execute(
        text("""
            CREATE TABLE IF NOT EXISTS destinations (
                id UUID PRIMARY KEY,
                name TEXT,
                country_code TEXT,
                lat NUMERIC,
                lng NUMERIC,
                region TEXT,
                subregion TEXT,
                is_active BOOLEAN DEFAULT TRUE
            )
        """)
    )
    db.execute(
        text("""
            CREATE TABLE IF NOT EXISTS destination_costs (
                destination_id UUID PRIMARY KEY,
                avg_meal_cost_usd NUMERIC,
                avg_transport_cost_usd NUMERIC,
                avg_hotel_cost_usd NUMERIC,
                avg_daily_cost_usd NUMERIC,
                hostel_usd NUMERIC,
                budget_usd NUMERIC,
                mid_usd NUMERIC,
                luxury_usd NUMERIC,
                cost_index NUMERIC,
                seasonal_multiplier JSONB
            )
        """)
    )
    db.execute(
        text("""
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id UUID PRIMARY KEY,
                onboarding_completed BOOLEAN DEFAULT FALSE,
                origin_lat NUMERIC,
                origin_lng NUMERIC
            )
        """)
    )
    db.execute(text("DELETE FROM destination_costs WHERE destination_id = :did"), {"did": str(DEST_ID)})
    db.execute(text("DELETE FROM destinations WHERE id = :did"), {"did": str(DEST_ID)})
    db.execute(
        text("INSERT INTO destinations (id, name, country_code, lat, lng) VALUES (:did, 'TestCity', 'XX', 48.0, 16.0)"),
        {"did": str(DEST_ID)},
    )
    db.execute(
        text("""
            INSERT INTO destination_costs (
                destination_id, avg_meal_cost_usd, avg_transport_cost_usd,
                avg_hotel_cost_usd, avg_daily_cost_usd,
                hostel_usd, budget_usd, mid_usd, luxury_usd, cost_index, seasonal_multiplier
            ) VALUES (
                :did, 20, 10, 80, 110, 25, 50, 80, 200, 0.4,
                '{"6": 1.3, "12": 0.8}'
            )
        """),
        {"did": str(DEST_ID)},
    )
    db.commit()
    yield
    db.execute(text("DELETE FROM destination_costs WHERE destination_id = :did"), {"did": str(DEST_ID)})
    db.execute(text("DELETE FROM destinations WHERE id = :did"), {"did": str(DEST_ID)})
    db.commit()


def _payload(**overrides) -> dict:
    base = {
        "destination_id": str(DEST_ID),
        "duration_days": 7,
        "people_count": 1,
        "travel_month": 6,
        "accommodation_tier": "mid",
        "currency": "USD",
    }
    base.update(overrides)
    return base


def test_budget_predict_basic(client: TestClient):
    resp = client.post("/api/v1/budget/predict", json=_payload())
    assert resp.status_code == 200
    data = resp.json()
    assert data["destination_id"] == str(DEST_ID)
    assert data["duration_days"] == 7
    assert data["currency"] == "USD"
    assert data["total_mid"] > 0
    assert data["total_min"] < data["total_mid"] < data["total_max"]
    assert "meals" in data["breakdown"]
    assert "transport" in data["breakdown"]
    assert "accommodation" in data["breakdown"]
    assert "travel_to_destination" in data["breakdown"]
    assert data["model_version"] == "formula-v1"


def test_budget_predict_seasonal_multiplier_applied(client: TestClient):
    resp_peak = client.post("/api/v1/budget/predict", json=_payload(travel_month=6))
    resp_off = client.post("/api/v1/budget/predict", json=_payload(travel_month=12))
    assert resp_peak.status_code == 200
    assert resp_off.status_code == 200
    # June has multiplier 1.3, December 0.8 → peak should be more expensive
    assert resp_peak.json()["total_mid"] > resp_off.json()["total_mid"]


def test_budget_predict_currency_conversion(client: TestClient):
    resp_usd = client.post("/api/v1/budget/predict", json=_payload(currency="USD"))
    resp_rub = client.post("/api/v1/budget/predict", json=_payload(currency="RUB"))
    assert resp_usd.status_code == 200
    assert resp_rub.status_code == 200
    usd_total = resp_usd.json()["total_mid"]
    rub_total = resp_rub.json()["total_mid"]
    assert rub_total == pytest.approx(usd_total * 90.0, rel=0.01)


def test_budget_predict_more_people_costs_more(client: TestClient):
    resp_1 = client.post("/api/v1/budget/predict", json=_payload(people_count=1))
    resp_2 = client.post("/api/v1/budget/predict", json=_payload(people_count=2))
    assert resp_1.json()["total_mid"] < resp_2.json()["total_mid"]


def test_budget_predict_accommodation_tiers(client: TestClient):
    resp_hostel = client.post("/api/v1/budget/predict", json=_payload(accommodation_tier="hostel"))
    resp_luxury = client.post("/api/v1/budget/predict", json=_payload(accommodation_tier="luxury"))
    assert resp_hostel.json()["total_mid"] < resp_luxury.json()["total_mid"]


def test_budget_predict_longer_trip_costs_more(client: TestClient):
    resp_short = client.post("/api/v1/budget/predict", json=_payload(duration_days=3))
    resp_long = client.post("/api/v1/budget/predict", json=_payload(duration_days=14))
    assert resp_short.json()["total_mid"] < resp_long.json()["total_mid"]


def test_budget_predict_unknown_destination(client: TestClient):
    resp = client.post("/api/v1/budget/predict", json=_payload(destination_id=str(uuid.uuid4())))
    assert resp.status_code == 404
