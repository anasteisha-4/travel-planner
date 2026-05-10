import uuid
from datetime import UTC, datetime
from io import BytesIO

import joblib
from fastapi.testclient import TestClient
from pytest import approx
from sqlalchemy import text


class _ConstantResidualModel:
    def __init__(self, value: float) -> None:
        self.value = value

    def predict(self, X):
        return [self.value for _ in range(len(X))]


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


def test_budget_monitor_uses_active_in_trip_model(client: TestClient, db):
    artifact = {
        "model_p10": _ConstantResidualModel(-10),
        "model_p50": _ConstantResidualModel(0),
        "model_p90": _ConstantResidualModel(10),
        "feature_names": [],
        "version": "in-trip-budget-v1",
    }
    buf = BytesIO()
    joblib.dump(artifact, buf)
    model_id = str(uuid.uuid4())
    db.execute(
        text(
            "INSERT INTO model_registry "
            "(id, name, version, model_type, is_active, metrics, model_blob, trained_at) "
            "VALUES (:id, 'in_trip_budget', 'in-trip-budget-v1', 'in_trip_budget', true, "
            "'{}'::jsonb, :blob, :trained_at)"
        ),
        {"id": model_id, "blob": buf.getvalue(), "trained_at": datetime.now(UTC)},
    )
    db.commit()

    resp = client.post("/api/v1/budget/monitor", json=_payload())

    assert resp.status_code == 200
    data = resp.json()
    assert data["used_ml_model"] is True
    assert data["model_version"] == "in-trip-budget-v1"
    assert data["assumptions"]["model_available"] is True


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


def test_budget_monitor_treats_expense_outside_trip_dates_as_planning_once(client: TestClient):
    resp = client.post(
        "/api/v1/budget/monitor",
        json=_payload(
            expenses=[
                {
                    "amount": 500,
                    "currency": "USD",
                    "category": "transport",
                    "description": "Авиабилеты Москва - Стамбул",
                    "expense_date": "2026-05-10",
                }
            ],
        ),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["current_spent"] == 500
    assert data["planning_spent"] == 500
    assert data["recurring_spent"] == 0
    assert data["assumptions"]["expense_classification"]["planning_once"] == 500
    assert data["projected_final_mid"] < 1600


def test_budget_monitor_treats_flight_description_inside_trip_as_once(client: TestClient):
    resp = client.post(
        "/api/v1/budget/monitor",
        json=_payload(
            expenses=[
                {
                    "amount": 500,
                    "currency": "USD",
                    "category": "transport",
                    "description": "flight tickets",
                    "expense_date": "2026-06-02",
                }
            ],
        ),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["planning_spent"] == 0
    assert data["locked_fixed_costs"] == 500
    assert data["recurring_spent"] == 0


def test_budget_monitor_does_not_scale_forecast_to_user_budget_limit(client: TestClient):
    resp = client.post(
        "/api/v1/budget/monitor",
        json=_payload(
            as_of_date="2026-05-20",
            trip_budget=100,
            expenses=[],
        ),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["current_spent"] == 0
    assert data["projected_final_mid"] > 1000
    assert data["risk_status"] == "risk"


def test_budget_monitor_small_forecast_overage_is_on_track_not_over_budget(client: TestClient):
    resp = client.post(
        "/api/v1/budget/monitor",
        json=_payload(
            trip_budget=1700,
            expenses=[
                {
                    "amount": 800,
                    "currency": "USD",
                    "category": "transport",
                    "description": "Авиабилеты",
                    "expense_date": "2026-05-15",
                }
            ],
            pre_trip_prediction={
                "total_min": 1200,
                "total_mid": 1580,
                "total_max": 1900,
                "breakdown": {
                    "accommodation": 700,
                    "meals": 300,
                    "transport": 260,
                    "activities": 180,
                    "travel_to_destination": 650,
                },
                "model_version": "budget-v1",
            },
        ),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["current_spent"] == 800
    assert data["projected_final_mid"] > data["budget_limit"]
    assert data["budget_usage_projected_pct"] < 1.10
    assert data["risk_status"] == "on_track"


def test_budget_monitor_large_planning_transport_closes_destination_travel(client: TestClient):
    with_ticket = client.post(
        "/api/v1/budget/monitor",
        json=_payload(
            expenses=[
                {
                    "amount": 800,
                    "currency": "USD",
                    "category": "transport",
                    "description": "Авиабилеты",
                    "expense_date": "2026-05-15",
                }
            ],
            pre_trip_prediction={
                "total_min": 1200,
                "total_mid": 1580,
                "total_max": 1900,
                "breakdown": {
                    "accommodation": 700,
                    "meals": 300,
                    "transport": 260,
                    "activities": 180,
                    "travel_to_destination": 650,
                },
                "model_version": "budget-v1",
            },
        ),
    )
    with_taxi = client.post(
        "/api/v1/budget/monitor",
        json=_payload(
            expenses=[
                {
                    "amount": 30,
                    "currency": "USD",
                    "category": "transport",
                    "description": "taxi",
                    "expense_date": "2026-06-02",
                }
            ],
            pre_trip_prediction={
                "total_min": 1200,
                "total_mid": 1580,
                "total_max": 1900,
                "breakdown": {
                    "accommodation": 700,
                    "meals": 300,
                    "transport": 260,
                    "activities": 180,
                    "travel_to_destination": 650,
                },
                "model_version": "budget-v1",
            },
        ),
    )

    assert with_ticket.status_code == 200
    assert with_taxi.status_code == 200
    ticket_data = with_ticket.json()
    taxi_data = with_taxi.json()
    ticket_transport_remaining = next(
        item["remaining_mid"] for item in ticket_data["category_contributions"] if item["category"] == "transport"
    )
    taxi_transport_remaining = next(
        item["remaining_mid"] for item in taxi_data["category_contributions"] if item["category"] == "transport"
    )
    assert ticket_data["assumptions"]["destination_transport_paid_usd"] == 800
    assert taxi_data["assumptions"]["destination_transport_paid_usd"] == 0
    assert taxi_transport_remaining > ticket_transport_remaining + 400


def test_budget_monitor_without_pretrip_prediction_ignores_user_budget_as_cost_estimate(client: TestClient):
    cheap_limit = client.post(
        "/api/v1/budget/monitor",
        json=_payload(
            as_of_date="2026-05-20",
            trip_budget=100,
            expenses=[],
            pre_trip_prediction=None,
        ),
    )
    unlimited = client.post(
        "/api/v1/budget/monitor",
        json=_payload(
            as_of_date="2026-05-20",
            trip_budget=None,
            expenses=[],
            pre_trip_prediction=None,
        ),
    )

    assert cheap_limit.status_code == 200
    assert unlimited.status_code == 200
    cheap_data = cheap_limit.json()
    unlimited_data = unlimited.json()
    assert cheap_data["projected_final_mid"] == unlimited_data["projected_final_mid"]
    assert cheap_data["projected_final_mid"] > 100
    assert cheap_data["risk_status"] == "risk"
    assert unlimited_data["risk_status"] == "forecast_only"
