import uuid
from datetime import UTC, datetime
from io import BytesIO

import joblib
from fastapi.testclient import TestClient
from pytest import approx
from sqlalchemy import text

from app.schemas.budget import BudgetMonitorRequest
from app.services.in_trip_budget_scorer import compute_baseline


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
                "is_one_time": True,
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
            "remaining_evidence_backed_entrance_fees": 40,
            "evidence_backed_price_count": 2,
            "candidate_poi_price_count": 1,
            "price_estimation_used": True,
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
    assert data["assumptions"]["itinerary_evidence_fee_remaining_usd"] == 40
    assert data["assumptions"]["itinerary_evidence_backed_price_count"] == 2
    assert data["assumptions"]["itinerary_candidate_poi_price_count"] == 1
    assert data["assumptions"]["itinerary_price_estimation_used"] is True


def test_budget_monitor_uses_bounded_in_trip_residual_model(client: TestClient, db):
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
    assert data["assumptions"]["ml_residual_allowed"] is True


def test_budget_monitor_without_budget_returns_forecast_only(client: TestClient):
    resp = client.post("/api/v1/budget/monitor", json=_payload(trip_budget=None))
    assert resp.status_code == 200
    data = resp.json()
    assert data["risk_status"] == "forecast_only"
    assert data["budget_limit"] is None
    assert data["budget_usage_projected_pct"] is None


def test_budget_monitor_starts_from_pretrip_prediction_without_expenses(client: TestClient):
    resp = client.post(
        "/api/v1/budget/monitor",
        json=_payload(
            as_of_date="2026-06-01",
            expenses=[],
            itinerary_summary={
                "generated_days_count": 7,
                "remaining_days_count": 7,
                "remaining_poi_count": 20,
                "remaining_food_poi_count": 6,
                "remaining_paid_poi_count": 8,
                "remaining_estimated_entrance_fees": 500,
                "remaining_evidence_backed_entrance_fees": 500,
                "evidence_backed_price_count": 8,
                "candidate_poi_price_count": 0,
                "price_estimation_used": False,
                "avg_visit_duration_minutes": 90,
            },
        ),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["current_spent"] == 0
    assert data["remaining_mid"] == 1500
    assert data["projected_final_mid"] == 1500
    assert data["assumptions"]["elapsed_days"] == 0
    assert data["assumptions"]["remaining_days"] == 7
    assert data["assumptions"]["pretrip_anchor_applied"] is True


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


def test_budget_monitor_description_does_not_make_expense_one_time(client: TestClient):
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
    assert data["locked_fixed_costs"] == 0
    assert data["recurring_spent"] == 500
    assert data["assumptions"]["recurring_projected_total_by_category_usd"]["transport"] == 3500


def test_budget_monitor_regular_transport_projects_across_trip_duration(client: TestClient):
    resp = client.post(
        "/api/v1/budget/monitor",
        json=_payload(
            as_of_date="2026-06-01",
            expenses=[
                {
                    "amount": 500,
                    "currency": "USD",
                    "category": "transport",
                    "description": "transport",
                    "expense_date": "2026-06-01",
                }
            ],
            pre_trip_prediction={
                "total_min": 1200,
                "total_mid": 1500,
                "total_max": 1900,
                "breakdown": {
                    "accommodation": 500,
                    "meals": 250,
                    "transport": 150,
                    "activities": 100,
                    "travel_to_destination": 500,
                },
                "model_version": "budget-v1",
            },
        ),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["current_spent"] == 500
    assert data["locked_fixed_costs"] == 0
    assert data["recurring_spent"] == 500
    assert data["assumptions"]["destination_transport_paid_usd"] == 0
    assert data["assumptions"]["recurring_trimmed_mean_by_category_usd"]["transport"] == 500
    assert data["assumptions"]["recurring_projected_total_by_category_usd"]["transport"] == 3500
    assert data["projected_final_mid"] > 4000
    transport_remaining = next(
        item["remaining_mid"] for item in data["category_contributions"] if item["category"] == "transport"
    )
    assert transport_remaining == 3000


def test_budget_monitor_skips_ml_residual_for_early_one_time_transport(client: TestClient, db):
    artifact = {
        "model_p10": _ConstantResidualModel(1000),
        "model_p50": _ConstantResidualModel(1000),
        "model_p90": _ConstantResidualModel(1000),
        "feature_names": [],
        "version": "in-trip-budget-v1",
    }
    buf = BytesIO()
    joblib.dump(artifact, buf)
    db.execute(
        text(
            "INSERT INTO model_registry "
            "(id, name, version, model_type, is_active, metrics, model_blob, trained_at) "
            "VALUES (:id, 'in_trip_budget', 'in-trip-budget-v1', 'in_trip_budget', true, "
            "'{}'::jsonb, :blob, :trained_at)"
        ),
        {"id": str(uuid.uuid4()), "blob": buf.getvalue(), "trained_at": datetime.now(UTC)},
    )
    db.commit()

    resp = client.post(
        "/api/v1/budget/monitor",
        json=_payload(
            as_of_date="2026-06-01",
            expenses=[
                {
                    "amount": 500,
                    "currency": "USD",
                    "category": "transport",
                    "description": "transport",
                    "expense_date": "2026-06-01",
                    "is_one_time": True,
                }
            ],
            pre_trip_prediction={
                "total_min": 1200,
                "total_mid": 1500,
                "total_max": 1900,
                "breakdown": {
                    "accommodation": 500,
                    "meals": 250,
                    "transport": 150,
                    "activities": 100,
                    "travel_to_destination": 500,
                },
                "model_version": "budget-v1",
            },
        ),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["used_ml_model"] is False
    assert data["assumptions"]["model_available"] is True
    assert data["assumptions"]["ml_residual_allowed"] is False
    assert data["projected_final_mid"] == 1582.5


def test_budget_monitor_caps_large_ml_residual(client: TestClient, db):
    artifact = {
        "model_p10": _ConstantResidualModel(1000),
        "model_p50": _ConstantResidualModel(1000),
        "model_p90": _ConstantResidualModel(1000),
        "feature_names": [],
        "version": "in-trip-budget-v1",
    }
    buf = BytesIO()
    joblib.dump(artifact, buf)
    db.execute(
        text(
            "INSERT INTO model_registry "
            "(id, name, version, model_type, is_active, metrics, model_blob, trained_at) "
            "VALUES (:id, 'in_trip_budget', 'in-trip-budget-v1', 'in_trip_budget', true, "
            "'{}'::jsonb, :blob, :trained_at)"
        ),
        {"id": str(uuid.uuid4()), "blob": buf.getvalue(), "trained_at": datetime.now(UTC)},
    )
    db.commit()

    payload = _payload()
    baseline_remaining = compute_baseline(BudgetMonitorRequest.model_validate(payload)).remaining_mid_usd
    cap = max(baseline_remaining * 0.20, 100)
    with_model = client.post("/api/v1/budget/monitor", json=payload).json()

    assert with_model["used_ml_model"] is True
    assert with_model["remaining_mid"] - baseline_remaining == approx(cap, abs=0.01)


def test_budget_monitor_projects_small_recurring_sample_with_trimmed_mean_rule(client: TestClient):
    resp = client.post(
        "/api/v1/budget/monitor",
        json=_payload(
            as_of_date="2026-06-02",
            expenses=[
                {
                    "amount": 10,
                    "currency": "USD",
                    "category": "food",
                    "description": "breakfast",
                    "expense_date": "2026-06-01",
                },
                {
                    "amount": 20,
                    "currency": "USD",
                    "category": "food",
                    "description": "dinner",
                    "expense_date": "2026-06-02",
                },
            ],
        ),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["current_spent"] == 30
    assert data["assumptions"]["recurring_trimmed_mean_by_category_usd"]["food"] == 15
    assert data["assumptions"]["recurring_projected_total_by_category_usd"]["food"] == 105
    food_remaining = next(
        item["remaining_mid"] for item in data["category_contributions"] if item["category"] == "food"
    )
    assert food_remaining == 75


def test_budget_monitor_trims_extreme_recurring_expense_outliers(client: TestClient):
    resp = client.post(
        "/api/v1/budget/monitor",
        json=_payload(
            as_of_date="2026-06-05",
            end_date="2026-06-30",
            expenses=[
                {
                    "amount": 1,
                    "currency": "USD",
                    "category": "food",
                    "description": "low outlier",
                    "expense_date": "2026-06-01",
                },
                {
                    "amount": 10,
                    "currency": "USD",
                    "category": "food",
                    "description": "meal",
                    "expense_date": "2026-06-02",
                },
                {
                    "amount": 12,
                    "currency": "USD",
                    "category": "food",
                    "description": "meal",
                    "expense_date": "2026-06-03",
                },
                {
                    "amount": 14,
                    "currency": "USD",
                    "category": "food",
                    "description": "meal",
                    "expense_date": "2026-06-04",
                },
                {
                    "amount": 100,
                    "currency": "USD",
                    "category": "food",
                    "description": "high outlier",
                    "expense_date": "2026-06-05",
                },
            ],
        ),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["assumptions"]["recurring_trim_fraction"] == 0.2
    assert data["assumptions"]["recurring_trimmed_mean_by_category_usd"]["food"] == 12
    assert data["assumptions"]["recurring_projected_total_by_category_usd"]["food"] == 360


def test_budget_monitor_lowers_forecast_for_slow_spend_in_second_half(client: TestClient):
    resp = client.post(
        "/api/v1/budget/monitor",
        json=_payload(
            as_of_date="2026-06-05",
            expenses=[
                {
                    "amount": 100,
                    "currency": "USD",
                    "category": "transport",
                    "description": "flight tickets",
                    "expense_date": "2026-06-01",
                },
                {
                    "amount": 20,
                    "currency": "USD",
                    "category": "food",
                    "description": "meals",
                    "expense_date": "2026-06-02",
                },
                {
                    "amount": 20,
                    "currency": "USD",
                    "category": "transport",
                    "description": "metro",
                    "expense_date": "2026-06-03",
                },
            ],
            itinerary_summary={
                "generated_days_count": 7,
                "remaining_days_count": 2,
                "remaining_poi_count": 4,
                "remaining_food_poi_count": 1,
                "remaining_paid_poi_count": 1,
                "remaining_estimated_entrance_fees": 0,
                "remaining_evidence_backed_entrance_fees": 0,
                "evidence_backed_price_count": 0,
                "candidate_poi_price_count": 0,
                "price_estimation_used": False,
                "avg_visit_duration_minutes": 90,
            },
        ),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["current_spent"] == 140
    assert data["projected_final_mid"] < 1500
    assert data["assumptions"]["recurring_projection_method"] == "trimmed_mean_per_expense_times_trip_duration"


def test_budget_monitor_raises_forecast_for_fast_spend(client: TestClient):
    resp = client.post(
        "/api/v1/budget/monitor",
        json=_payload(
            as_of_date="2026-06-05",
            expenses=[
                {
                    "amount": 800,
                    "currency": "USD",
                    "category": "transport",
                    "description": "flight tickets",
                    "expense_date": "2026-06-01",
                },
                {
                    "amount": 500,
                    "currency": "USD",
                    "category": "housing",
                    "description": "hotel",
                    "expense_date": "2026-06-01",
                },
                {
                    "amount": 500,
                    "currency": "USD",
                    "category": "food",
                    "description": "meals",
                    "expense_date": "2026-06-02",
                },
                {
                    "amount": 200,
                    "currency": "USD",
                    "category": "entertainment",
                    "description": "museum tickets",
                    "expense_date": "2026-06-03",
                },
            ],
            itinerary_summary={
                "generated_days_count": 7,
                "remaining_days_count": 2,
                "remaining_poi_count": 4,
                "remaining_food_poi_count": 1,
                "remaining_paid_poi_count": 1,
                "remaining_estimated_entrance_fees": 0,
                "remaining_evidence_backed_entrance_fees": 0,
                "evidence_backed_price_count": 0,
                "candidate_poi_price_count": 0,
                "price_estimation_used": False,
                "avg_visit_duration_minutes": 90,
            },
        ),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["current_spent"] == 2000
    assert data["projected_final_mid"] > 2000
    assert data["projected_final_mid"] > 1500


def test_budget_monitor_converges_to_spent_when_trip_is_over(client: TestClient):
    resp = client.post(
        "/api/v1/budget/monitor",
        json=_payload(
            as_of_date="2026-06-07",
            expenses=[
                {
                    "amount": 100,
                    "currency": "USD",
                    "category": "transport",
                    "description": "flight tickets",
                    "expense_date": "2026-06-01",
                },
                {
                    "amount": 40,
                    "currency": "USD",
                    "category": "food",
                    "description": "meals",
                    "expense_date": "2026-06-02",
                },
            ],
            itinerary_summary={
                "generated_days_count": 7,
                "remaining_days_count": 0,
                "remaining_poi_count": 0,
                "remaining_food_poi_count": 0,
                "remaining_paid_poi_count": 0,
                "remaining_estimated_entrance_fees": 0,
                "remaining_evidence_backed_entrance_fees": 0,
                "evidence_backed_price_count": 0,
                "candidate_poi_price_count": 0,
                "price_estimation_used": False,
                "avg_visit_duration_minutes": 90,
            },
        ),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["current_spent"] == 140
    assert data["remaining_mid"] == 840
    assert data["projected_final_mid"] == 980


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
    assert data["projected_final_mid"] <= data["budget_limit"]
    assert data["budget_usage_projected_pct"] < 1.0
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
    assert taxi_transport_remaining > ticket_transport_remaining + 100


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
