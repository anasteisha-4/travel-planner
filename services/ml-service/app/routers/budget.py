import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user_id
from app.exceptions import AppException
from app.schemas.budget import BudgetPredictRequest, BudgetPredictResponse
from app.services.budget_scorer import get_budget_scorer
from app.services.data_loader import get_destination_features

router = APIRouter()

CURRENCY_RATES: dict[str, float] = {
    "USD": 1.0,
    "EUR": 0.93,
    "RUB": 90.0,
    "GBP": 0.79,
    "AED": 3.67,
    "TRY": 32.0,
    "THB": 36.0,
    "CNY": 7.2,
    "JPY": 150.0,
    "KZT": 450.0,
    "GEL": 2.65,
    "AMD": 395.0,
}

ACCOMMODATION_DAILY_FRACTION = {"hostel": 0.18, "budget": 0.35, "mid": 0.65, "luxury": 1.60}
MEALS_DAILY_FRACTION = {"hostel": 0.25, "budget": 0.30, "mid": 0.38, "luxury": 0.55}
TRANSPORT_DAILY_FRACTION = 0.12
ACTIVITIES_DAILY_FRACTION = 0.08


def _load_costs(db: Session, dest_id: uuid.UUID) -> dict:
    row = db.execute(
        text(
            "SELECT avg_meal_cost_usd, avg_transport_cost_usd, avg_hotel_cost_usd, "
            "avg_daily_cost_usd, hostel_usd, budget_usd, mid_usd, luxury_usd, "
            "cost_index, seasonal_multiplier "
            "FROM destination_costs WHERE destination_id = :did"
        ),
        {"did": str(dest_id)},
    ).fetchone()
    if row is None:
        return {}
    return dict(row._mapping)


def _formula_breakdown(
    costs: dict,
    duration_days: int,
    people_count: int,
    travel_month: int,
    accommodation_tier: str,
) -> dict:
    """Compute per-category breakdown in USD. Mirrors budget_scorer._formula_baseline."""
    import json
    import math

    sm = costs.get("seasonal_multiplier") or {}
    if isinstance(sm, str):
        sm = json.loads(sm)
    seasonal = float(sm.get(str(travel_month), 1.0)) if sm else 1.0

    avg_daily = float(costs.get("avg_daily_cost_usd") or 80.0)
    tier = accommodation_tier if accommodation_tier in ACCOMMODATION_DAILY_FRACTION else "mid"

    hotel_tier_nightly = costs.get(f"{tier}_usd") or (avg_daily * ACCOMMODATION_DAILY_FRACTION[tier])
    rooms = max(1, math.ceil(people_count / 2))
    accommodation_total = float(hotel_tier_nightly) * rooms * seasonal * duration_days

    meals_total = avg_daily * MEALS_DAILY_FRACTION[tier] * people_count * seasonal * duration_days
    transport_total = avg_daily * TRANSPORT_DAILY_FRACTION * people_count * duration_days
    activities_total = avg_daily * ACTIVITIES_DAILY_FRACTION * people_count * duration_days

    return {
        "meals": round(meals_total, 2),
        "transport": round(transport_total, 2),
        "accommodation": round(accommodation_total, 2),
        "activities": round(activities_total, 2),
    }


@router.post("/budget/predict", response_model=BudgetPredictResponse)
def predict_budget(
    request: BudgetPredictRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> BudgetPredictResponse:
    dest_id = request.destination_id

    costs = _load_costs(db, dest_id)
    if not costs:
        raise AppException(
            status_code=404,
            code="DESTINATION_NOT_FOUND",
            message=f"No cost data for destination {dest_id}",
        )

    dest_features = get_destination_features(db, [dest_id]).get(dest_id, {})

    scorer = get_budget_scorer(db)
    if scorer is not None:
        result = scorer.predict(
            costs=costs,
            dest_features=dest_features,
            duration_days=request.duration_days,
            people_count=request.people_count,
            travel_month=request.travel_month,
            accommodation_tier=request.accommodation_tier,
        )
    else:
        # No trained model yet — use formula directly
        import json

        from app.services.budget_scorer import _formula_baseline

        sm = costs.get("seasonal_multiplier") or {}
        if isinstance(sm, str):
            sm = json.loads(sm)
        baseline = _formula_baseline(
            costs,
            request.duration_days,
            request.people_count,
            request.travel_month,
            request.accommodation_tier,
        )
        result = {
            "total_min": round(baseline * 0.75, 2),
            "total_mid": round(baseline, 2),
            "total_max": round(baseline * 1.35, 2),
            "model_version": "formula-v1",
            "baseline": round(baseline, 2),
        }

    currency = request.currency.upper()
    fx = CURRENCY_RATES.get(currency, 1.0)

    breakdown_usd = _formula_breakdown(
        costs,
        request.duration_days,
        request.people_count,
        request.travel_month,
        request.accommodation_tier,
    )

    return BudgetPredictResponse(
        destination_id=dest_id,
        duration_days=request.duration_days,
        people_count=request.people_count,
        currency=currency,
        total_min=round(float(result["total_min"]) * fx, 2),
        total_mid=round(float(result["total_mid"]) * fx, 2),
        total_max=round(float(result["total_max"]) * fx, 2),
        daily_cost_usd=round(float(costs.get("avg_daily_cost_usd") or 80.0), 2),
        breakdown={k: round(v * fx, 2) for k, v in breakdown_usd.items()},
        model_version=str(result["model_version"]),
    )
