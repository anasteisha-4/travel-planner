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
) -> float:
    """Compute formula baseline trip cost in USD.

    Uses avg_daily_cost_usd as anchor (same basis as synthetic training data).
    Pre-computed tier costs (hostel_usd etc.) take priority if stored in DB.
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
    return daily * duration_days


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
