import uuid

from fastapi.testclient import TestClient
from pytest import approx


def _payload(**overrides) -> dict:
    base = {
        "trip_id": str(uuid.uuid4()),
        "destination_id": str(uuid.uuid4()),
        "start_date": "2026-06-01",
        "end_date": "2026-06-07",
        "as_of_date": "2026-06-03",
        "people_count": 2,
        "currency": "USD",
        "trip_budget": 1600,
        "expenses": [
            {
                "amount": 500,
                "currency": "USD",
                "category": "housing",
                "description": "Hotel prepaid",
                "expense_date": "2026-06-01",
            },
            {
                "amount": 120,
                "currency": "USD",
                "category": "food",
                "description": "Meals",
                "expense_date": "2026-06-02",
            },
        ],
        "pre_trip_prediction": {
            "total_min": 1200,
            "total_mid": 1500,
            "total_max": 1900,
            "breakdown": {
                "accommodation": 700,
                "meals": 420,
                "transport": 180,
                "activities": 140,
                "travel_to_destination": 0,
            },
            "model_version": "budget-v1",
        },
        "itinerary_summary": {
            "generated_days_count": 7,
            "remaining_days_count": 4,
            "remaining_poi_count": 12,
            "remaining_food_poi_count": 4,
            "remaining_paid_poi_count": 3,
            "remaining_estimated_entrance_fees": 60,
            "avg_visit_duration_minutes": 95,
        },
    }
    base.update(overrides)
    return base


def test_budget_monitor_formula_fallback(client: TestClient):
    resp = client.post("/api/v1/budget/monitor", json=_payload())
    assert resp.status_code == 200
    data = resp.json()
    assert data["currency"] == "USD"
    assert data["current_spent"] == 620
    assert data["locked_fixed_costs"] == 500
    assert data["recurring_spent"] == 120
    assert data["remaining_mid"] > 0
    assert data["projected_final_mid"] == approx(data["current_spent"] + data["remaining_mid"])
    assert data["model_version"] == "in-trip-formula-v1"
    assert data["used_ml_model"] is False
    categories = {item["category"] for item in data["category_contributions"]}
    assert {"housing", "food", "entertainment"}.issubset(categories)


def test_budget_monitor_without_budget_returns_forecast_only(client: TestClient):
    resp = client.post("/api/v1/budget/monitor", json=_payload(trip_budget=None))
    assert resp.status_code == 200
    data = resp.json()
    assert data["risk_status"] == "forecast_only"
    assert data["budget_limit"] is None
    assert data["budget_usage_projected_pct"] is None


def test_budget_monitor_converts_target_currency(client: TestClient):
    resp = client.post(
        "/api/v1/budget/monitor",
        json=_payload(
            currency="RUB",
            trip_budget=144000,
            expenses=[
                {
                    "amount": 45000,
                    "currency": "RUB",
                    "category": "housing",
                    "description": "Отель",
                    "expense_date": "2026-06-01",
                }
            ],
        ),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["currency"] == "RUB"
    assert data["current_spent"] == 45000
    assert data["remaining_mid"] > 0
