"""Budget prediction service."""

from sqlalchemy.orm import Session

PEOPLE_FACTOR = {1: 1.0, 2: 1.7, 3: 2.3, 4: 2.8}

ACCOMMODATION_MULTIPLIERS = {
    "hostel": 0.3,
    "budget": 0.6,
    "mid": 1.0,
    "luxury": 2.5,
}


def predict_trip_budget(
    db: Session,
    destination_id: str,
    duration_days: int,
    people_count: int,
    travel_month: int | None = None,
    accommodation_tier: str = "mid",
) -> dict:
    if duration_days < 1:
        return {"error": "duration_days must be at least 1."}
    if people_count < 1:
        return {"error": "people_count must be at least 1."}
    if accommodation_tier not in ACCOMMODATION_MULTIPLIERS:
        accommodation_tier = "mid"

    from app.models import DestinationCosts

    costs = db.query(DestinationCosts).filter(DestinationCosts.destination_id == destination_id).first()
    if not costs:
        return {"error": "No cost data available for this destination."}

    factor = PEOPLE_FACTOR[people_count] if people_count in PEOPLE_FACTOR else 2.8 + (people_count - 4) * 0.5

    # Seasonal multiplier: crowd_index-derived per-month scalar [0.7, 1.4]
    seasonal = 1.0
    if travel_month is not None and costs.seasonal_multiplier:
        seasonal = float(costs.seasonal_multiplier.get(str(travel_month), 1.0))

    # Accommodation cost for the chosen tier
    hotel_tier_usd = getattr(costs, f"{accommodation_tier}_usd", None) or (
        costs.avg_hotel_cost_usd * ACCOMMODATION_MULTIPLIERS[accommodation_tier]
    )

    predicted_daily = (
        costs.avg_meal_cost_usd * 2.5 * factor + costs.avg_transport_cost_usd * factor + hotel_tier_usd
    ) * seasonal
    predicted_total = predicted_daily * duration_days

    return {
        "destination_id": destination_id,
        "duration_days": duration_days,
        "people_count": people_count,
        "travel_month": travel_month,
        "accommodation_tier": accommodation_tier,
        "seasonal_multiplier": round(seasonal, 3),
        "predicted_total_usd": round(predicted_total, 2),
        "predicted_daily_usd": round(predicted_daily, 2),
        "range_low_usd": round(predicted_total * 0.75, 2),
        "range_high_usd": round(predicted_total * 1.35, 2),
        "breakdown": {
            "meals_usd": round(costs.avg_meal_cost_usd * 2.5 * factor * duration_days * seasonal, 2),
            "transport_usd": round(costs.avg_transport_cost_usd * factor * duration_days * seasonal, 2),
            "accommodation_usd": round(hotel_tier_usd * duration_days * seasonal, 2),
        },
    }
