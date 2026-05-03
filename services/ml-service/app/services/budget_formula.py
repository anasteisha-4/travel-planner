"""Shared formula baseline for budget prediction.

Single source of truth for formula constants and baseline computation.
Used by budget_scorer.py (inference), train_budget_model.py (training),
and generate_synthetic_data.py (synthetic data generation).

If any constant changes here, training and inference stay in sync automatically.
"""

import json
import math

# Accommodation cost as fraction of avg_daily_cost_usd per room per night.
ACCOMMODATION_DAILY_FRACTION: dict[str, float] = {
    "hostel": 0.18,
    "budget": 0.35,
    "mid": 0.65,
    "luxury": 1.60,
}

# Meals fraction of avg_daily per person per day (by tier).
MEALS_DAILY_FRACTION: dict[str, float] = {
    "hostel": 0.25,
    "budget": 0.30,
    "mid": 0.38,
    "luxury": 0.55,
}

# Transport and activities fractions — fixed across tiers.
TRANSPORT_DAILY_FRACTION: float = 0.12
ACTIVITIES_DAILY_FRACTION: float = 0.08

ACC_TIER_ENCODING: dict[str, int] = {"hostel": 0, "budget": 1, "mid": 2, "luxury": 3}

# Round-trip economy fare calibrated to 2024-2025 averages (USD per person).
_TRAVEL_COST_BRACKETS: list[tuple[float, float]] = [
    (80, 0),
    (250, 25),
    (500, 60),
    (1500, 160),
    (3000, 290),
    (6000, 470),
    (10000, 700),
    (float("inf"), 980),
]

_TRAVEL_SEASON_MULT: dict[int, float] = {6: 1.15, 7: 1.30, 8: 1.30, 12: 1.40, 1: 1.20}

_EARTH_RADIUS_KM = 6371.0


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km between two lat/lon points."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * _EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def estimate_travel_cost(
    origin_lat: float | None,
    origin_lng: float | None,
    dest_lat: float,
    dest_lng: float,
    people_count: int,
    travel_month: int,
) -> float:
    """Estimate round-trip travel cost to destination in USD.

    Returns 0.0 when origin is unknown so callers can still compute a valid
    baseline without the travel component.
    """
    if origin_lat is None or origin_lng is None:
        return 0.0

    distance_km = haversine(origin_lat, origin_lng, dest_lat, dest_lng)

    per_person = _TRAVEL_COST_BRACKETS[-1][1]
    for threshold, cost in _TRAVEL_COST_BRACKETS:
        if distance_km < threshold:
            per_person = cost
            break

    season_mult = _TRAVEL_SEASON_MULT.get(travel_month, 1.0)
    return round(per_person * people_count * season_mult, 2)


def formula_baseline(
    avg_daily_cost: float,
    hostel_usd: float | None,
    budget_usd: float | None,
    mid_usd: float | None,
    luxury_usd: float | None,
    seasonal_mult: float,
    duration_days: int,
    people_count: int,
    accommodation_tier: str,
    travel_to_destination: float = 0.0,
) -> float:
    """Compute formula baseline trip cost in USD.

    Uses avg_daily_cost_usd as anchor (same basis as synthetic training data).
    Pre-computed tier costs (hostel_usd etc.) take priority if stored in DB.
    travel_to_destination is a one-time cost added on top of per-day costs.
    """
    tier = accommodation_tier if accommodation_tier in ACCOMMODATION_DAILY_FRACTION else "mid"
    tier_cost_map: dict[str, float | None] = {
        "hostel": hostel_usd,
        "budget": budget_usd,
        "mid": mid_usd,
        "luxury": luxury_usd,
    }
    hotel_tier_nightly = tier_cost_map.get(tier) or (avg_daily_cost * ACCOMMODATION_DAILY_FRACTION[tier])
    rooms = max(1, math.ceil(people_count / 2))
    accommodation_per_day = float(hotel_tier_nightly) * rooms * seasonal_mult

    meals_per_day = avg_daily_cost * MEALS_DAILY_FRACTION[tier] * people_count * seasonal_mult
    transport_per_day = avg_daily_cost * TRANSPORT_DAILY_FRACTION * people_count
    activities_per_day = avg_daily_cost * ACTIVITIES_DAILY_FRACTION * people_count

    daily = accommodation_per_day + meals_per_day + transport_per_day + activities_per_day
    return daily * duration_days + travel_to_destination


def seasonal_mult_from_json(seasonal_multiplier: object, travel_month: int) -> float:
    """Extract seasonal multiplier for a given month from DB jsonb value."""
    sm = seasonal_multiplier
    if sm is None or (isinstance(sm, float) and sm != sm):
        return 1.0
    if isinstance(sm, str):
        try:
            sm = json.loads(sm)
        except Exception:
            return 1.0
    if isinstance(sm, dict):
        return float(sm.get(str(travel_month), 1.0))
    return 1.0
