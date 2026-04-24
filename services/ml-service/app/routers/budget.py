import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user_id
from app.exceptions import AppException
from app.schemas.budget import BudgetPredictRequest, BudgetPredictResponse

router = APIRouter()

PEOPLE_FACTOR = {1: 1.0, 2: 1.7, 3: 2.3, 4: 2.8}

ACCOMMODATION_MULTIPLIERS = {
    "hostel": 0.3,
    "budget": 0.6,
    "mid": 1.0,
    "luxury": 2.5,
}

# Approximate USD→other currency mid rates (fallback — real FX in Phase 6 ML model)
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


def _predict_budget_formula(
    costs: dict,
    duration_days: int,
    people_count: int,
    travel_month: int,
    accommodation_tier: str,
) -> dict:
    factor = (
        PEOPLE_FACTOR[people_count]
        if people_count in PEOPLE_FACTOR
        else 2.8 + (people_count - 4) * 0.5
    )

    acc_mult = ACCOMMODATION_MULTIPLIERS.get(accommodation_tier, 1.0)

    seasonal = 1.0
    sm = costs.get("seasonal_multiplier")
    if sm and travel_month is not None:
        seasonal = float(sm.get(str(travel_month), 1.0))

    hotel_tier_usd = costs.get(f"{accommodation_tier}_usd") or (
        float(costs["avg_hotel_cost_usd"]) * acc_mult
    )

    meals = float(costs["avg_meal_cost_usd"]) * 2.5 * factor
    transport = float(costs["avg_transport_cost_usd"]) * factor
    hotel = float(hotel_tier_usd)
    daily = (meals + transport + hotel) * seasonal
    total = daily * duration_days

    return {
        "daily_usd": daily,
        "total_usd": total,
        "range_low_usd": total * 0.75,
        "range_high_usd": total * 1.35,
        "breakdown_usd": {
            "meals": meals * duration_days * seasonal,
            "transport": transport * duration_days * seasonal,
            "accommodation": hotel * duration_days * seasonal,
        },
        "seasonal_multiplier": seasonal,
    }


@router.post("/budget/predict", response_model=BudgetPredictResponse)
def predict_budget(
    request: BudgetPredictRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> BudgetPredictResponse:
    dest_id = request.destination_id

    row = db.execute(
        text(
            "SELECT avg_meal_cost_usd, avg_transport_cost_usd, avg_hotel_cost_usd, "
            "avg_daily_cost_usd, hostel_usd, budget_usd, mid_usd, luxury_usd, "
            "seasonal_multiplier "
            "FROM destination_costs WHERE destination_id = :did"
        ),
        {"did": str(dest_id)},
    ).fetchone()

    if row is None:
        raise AppException(
            status_code=404,
            code="DESTINATION_NOT_FOUND",
            message=f"No cost data for destination {dest_id}",
        )

    costs = dict(row._mapping)
    result = _predict_budget_formula(
        costs=costs,
        duration_days=request.duration_days,
        people_count=request.people_count,
        travel_month=request.travel_month,
        accommodation_tier=request.accommodation_tier,
    )

    currency = request.currency.upper()
    fx = CURRENCY_RATES.get(currency, 1.0)

    def _convert(v: float) -> float:
        return round(v * fx, 2)

    return BudgetPredictResponse(
        destination_id=dest_id,
        duration_days=request.duration_days,
        people_count=request.people_count,
        currency=currency,
        total_min=_convert(result["range_low_usd"]),
        total_mid=_convert(result["total_usd"]),
        total_max=_convert(result["range_high_usd"]),
        daily_cost_usd=round(float(costs["avg_daily_cost_usd"]), 2),
        breakdown={k: _convert(v) for k, v in result["breakdown_usd"].items()},
        model_version="formula-v1",
    )
