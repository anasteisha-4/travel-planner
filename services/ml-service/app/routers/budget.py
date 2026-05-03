import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user_id
from app.exceptions import AppException
from app.schemas.budget import BudgetAssumptions, BudgetPredictRequest, BudgetPredictResponse
from app.services.budget_formula import estimate_travel_cost, haversine
from app.services.budget_scorer import get_budget_scorer
from app.services.data_loader import get_destination_features
from app.services.profile_client import _get_profile_sync
from app.services.travelpayouts_service import get_cached_fare_usd

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


def _as_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return None if parsed != parsed else parsed


def _resolve_origin(request: BudgetPredictRequest, profile: dict) -> tuple[float | None, float | None, str | None, str]:
    request_origin_lat = _as_float(request.origin_lat)
    request_origin_lng = _as_float(request.origin_lng)
    if request_origin_lat is not None and request_origin_lng is not None:
        return request_origin_lat, request_origin_lng, request.origin_city_name, "request"

    if request.origin_city_name and request.origin_city_name.strip():
        return None, None, request.origin_city_name.strip(), "request_name"

    profile_origin_lat = _as_float(profile.get("origin_lat"))
    profile_origin_lng = _as_float(profile.get("origin_lng"))
    if profile_origin_lat is not None and profile_origin_lng is not None:
        return profile_origin_lat, profile_origin_lng, profile.get("origin_city_name"), "profile"

    return None, None, request.origin_city_name or profile.get("origin_city_name"), "unknown"


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


def _load_destination_info(db: Session, dest_id: uuid.UUID) -> dict:
    row = db.execute(
        text("SELECT name, country_code, lat, lng FROM destinations WHERE id = :did"),
        {"did": str(dest_id)},
    ).fetchone()
    return dict(row._mapping) if row else {}


def _formula_breakdown(
    costs: dict,
    duration_days: int,
    people_count: int,
    travel_month: int,
    accommodation_tier: str,
    origin_lat: float | None,
    origin_lng: float | None,
    dest_lat: float,
    dest_lng: float,
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
    travel_total = estimate_travel_cost(origin_lat, origin_lng, dest_lat, dest_lng, people_count, travel_month)

    return {
        "accommodation": round(accommodation_total, 2),
        "meals": round(meals_total, 2),
        "transport": round(transport_total, 2),
        "activities": round(activities_total, 2),
        "travel_to_destination": round(travel_total, 2),
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

    dest_info = _load_destination_info(db, dest_id)
    dest_features = get_destination_features(db, [dest_id]).get(dest_id, {})
    dest_lat = float(dest_features.get("lat") or dest_info.get("lat") or 0.0)
    dest_lng = float(dest_features.get("lng") or dest_info.get("lng") or 0.0)

    profile = _get_profile_sync(db, user_id)
    origin_lat, origin_lng, origin_city_name, origin_source = _resolve_origin(request, profile)
    travel_distance_km = (
        round(haversine(origin_lat, origin_lng, dest_lat, dest_lng), 1)
        if origin_lat is not None and origin_lng is not None
        else None
    )

    scorer = get_budget_scorer(db)
    if scorer is not None:
        result = scorer.predict(
            costs=costs,
            dest_features=dest_features,
            duration_days=request.duration_days,
            people_count=request.people_count,
            travel_month=request.travel_month,
            accommodation_tier=request.accommodation_tier,
            origin_lat=origin_lat,
            origin_lng=origin_lng,
        )
    else:
        from app.services.budget_scorer import _formula_baseline

        baseline = _formula_baseline(
            costs,
            request.duration_days,
            request.people_count,
            request.travel_month,
            request.accommodation_tier,
            origin_lat,
            origin_lng,
            dest_lat,
            dest_lng,
        )
        travel_cost = estimate_travel_cost(
            origin_lat, origin_lng, dest_lat, dest_lng, request.people_count, request.travel_month
        )
        result = {
            "total_min": round(baseline * 0.75, 2),
            "total_mid": round(baseline, 2),
            "total_max": round(baseline * 1.35, 2),
            "model_version": "formula-v1",
            "baseline": round(baseline, 2),
            "travel_to_destination": round(travel_cost, 2),
        }

    currency = request.currency.upper()
    fx = CURRENCY_RATES.get(currency, 1.0)

    breakdown_usd = _formula_breakdown(
        costs,
        request.duration_days,
        request.people_count,
        request.travel_month,
        request.accommodation_tier,
        origin_lat,
        origin_lng,
        dest_lat,
        dest_lng,
    )
    fallback_travel_usd = breakdown_usd["travel_to_destination"]
    fare = get_cached_fare_usd(
        origin_city_name=origin_city_name,
        origin_lat=origin_lat,
        origin_lng=origin_lng,
        destination_name=dest_info.get("name"),
        destination_lat=dest_lat,
        destination_lng=dest_lng,
        destination_country_code=dest_info.get("country_code"),
        travel_month=request.travel_month,
        duration_days=request.duration_days,
        accommodation_tier=request.accommodation_tier,
    )
    travel_cost_source = "distance_fallback" if fallback_travel_usd > 0 else "none"
    origin_iata = None
    destination_iata = None
    fare_found_at = None
    fare_expires_at = None
    fare_strategy = None
    fare_trip_class = None
    fare_delta_usd = 0.0
    if fare is not None and fare.price_usd > 0:
        fare_delta_usd = fare.price_usd - fallback_travel_usd
        breakdown_usd["travel_to_destination"] = fare.price_usd
        travel_cost_source = fare.source
        origin_iata = fare.origin_iata
        destination_iata = fare.destination_iata
        fare_found_at = fare.found_at
        fare_expires_at = fare.expires_at
        fare_strategy = fare.fare_strategy
        fare_trip_class = fare.trip_class

    return BudgetPredictResponse(
        destination_id=dest_id,
        duration_days=request.duration_days,
        people_count=request.people_count,
        currency=currency,
        total_min=round(max(1.0, float(result["total_min"]) + fare_delta_usd) * fx, 2),
        total_mid=round(max(1.0, float(result["total_mid"]) + fare_delta_usd) * fx, 2),
        total_max=round(max(1.0, float(result["total_max"]) + fare_delta_usd) * fx, 2),
        daily_cost_usd=round(float(costs.get("avg_daily_cost_usd") or 80.0), 2),
        breakdown={k: round(v * fx, 2) for k, v in breakdown_usd.items()},
        assumptions=BudgetAssumptions(
            duration_days=request.duration_days,
            people_count=request.people_count,
            accommodation_tier=request.accommodation_tier,
            travel_month=request.travel_month,
            currency=currency,
            origin_city_name=origin_city_name,
            origin_lat=origin_lat,
            origin_lng=origin_lng,
            origin_source=origin_source,
            travel_distance_km=travel_distance_km,
            travel_cost_source=travel_cost_source,
            origin_iata=origin_iata,
            destination_iata=destination_iata,
            flight_fare_strategy=fare_strategy,
            flight_trip_class=fare_trip_class,
            flight_fare_found_at=fare_found_at,
            flight_fare_expires_at=fare_expires_at,
        ),
        model_version=str(result["model_version"]),
    )
