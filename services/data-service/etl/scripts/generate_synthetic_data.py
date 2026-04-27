"""Generate synthetic ML training data for Phase 1.7.

Produces:
- 10 000 user_preference_profiles  (recommendation training)
- 100 000 trip_budget_actuals      (budget prediction training)
- 50 000 trajectory_feedback       (route quality training)

Usage:
    docker compose run --rm data-service python -m etl.scripts.generate_synthetic_data
    docker compose run --rm data-service python -m etl.scripts.generate_synthetic_data --table preferences
    docker compose run --rm data-service python -m etl.scripts.generate_synthetic_data --table budgets
    docker compose run --rm data-service python -m etl.scripts.generate_synthetic_data --table feedback
"""

import argparse
import logging
import random
import uuid
from typing import Any

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.config import settings
from app.models.costs import DestinationCosts
from app.models.destination import Destination
from app.models.safety import DestinationSafety
from app.models.trajectory import Trajectory
from app.models.trajectory_feedback import TrajectoryFeedback
from app.models.trip_budget_actual import TripBudgetActual
from app.models.user_preference_profile import UserPreferenceProfile

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BATCH_SIZE = 1000

CITIZENSHIP_CODES = [
    "RU",
    "US",
    "DE",
    "FR",
    "GB",
    "CN",
    "IN",
    "BR",
    "TR",
    "IT",
    "ES",
    "PL",
    "NL",
    "KZ",
    "UA",
    "BY",
    "UZ",
    "AZ",
    "GE",
    "AM",
    "TH",
    "JP",
    "KR",
    "AU",
    "CA",
    "MX",
    "AR",
    "ZA",
    "EG",
    "AE",
]

ACTIVITY_TYPES = [
    "beach",
    "culture",
    "nature",
    "adventure",
    "food",
    "nightlife",
    "wellness",
    "shopping",
    "family",
    "urban",
]

TRIP_TYPES = ["solo", "couple", "family", "group"]

BUDGET_TIERS = ["budget", "mid", "premium", "luxury"]

PROFILE_TYPES = [
    "backpacker",
    "budget",
    "mid",
    "premium",
    "luxury",
    "business",
    "family",
]

ACCOMMODATION_TIERS = ["hostel", "budget", "mid", "luxury"]

BUDGET_TIER_MULTIPLIERS = {
    "budget": 0.6,
    "mid": 1.0,
    "premium": 1.6,
    "luxury": 2.8,
}

# IMPORTANT: These constants MUST match services/ml-service/app/services/budget_formula.py exactly.
# Both services are deployed separately, so they cannot share a module. If you change values here,
# update budget_formula.py too — mismatches cause formula MAPE inflation at training time.
ACCOMMODATION_COST_FRACTION = {
    "hostel": 0.18,
    "budget": 0.35,
    "mid": 0.65,
    "luxury": 1.60,
}

MEALS_COST_FRACTION = {
    "hostel": 0.25,
    "budget": 0.30,
    "mid": 0.38,
    "luxury": 0.55,
}

TRANSPORT_COST_FRACTION = 0.12
ACTIVITIES_COST_FRACTION = 0.08


def _jitter(value: float, pct: float = 0.30) -> float:
    """Apply ±pct random noise to a value, keep positive."""
    noise = random.uniform(1.0 - pct, 1.0 + pct)
    return max(0.01, round(value * noise, 2))


def _pick_activities(n_min: int = 1, n_max: int = 4) -> list[str]:
    k = random.randint(n_min, n_max)
    return random.sample(ACTIVITY_TYPES, k)


def generate_preferences(
    session: Session,
    destination_ids: list[uuid.UUID],
    safety_by_dest: dict[uuid.UUID, float],
    n: int = 10_000,
) -> None:
    logger.info("Generating %d user preference profiles...", n)
    inserted = 0
    batch: list[dict[str, Any]] = []

    for _ in range(n):
        budget_tier = random.choice(BUDGET_TIERS)
        profile_type = random.choice(PROFILE_TYPES)
        trip_type = random.choice(TRIP_TYPES)

        # Safety threshold: backpackers tolerate more risk, luxury less
        if profile_type in ("luxury", "business"):
            min_safety = round(random.uniform(0.45, 0.75), 2)
        elif profile_type == "backpacker":
            min_safety = round(random.uniform(0.0, 0.35), 2)
        else:
            min_safety = round(random.uniform(0.15, 0.55), 2)

        label_dest_id = random.choice(destination_ids)
        dest_safety = safety_by_dest.get(label_dest_id, 0.5)
        # Label score: inversion of low-safety for risk-averse profiles + noise
        base_score = dest_safety if min_safety > 0.4 else (1.0 - dest_safety * 0.3)
        label_score = round(min(1.0, max(0.0, _jitter(base_score, 0.25))), 4)

        batch.append(
            {
                "id": uuid.uuid4(),
                "citizenship_code": random.choice(CITIZENSHIP_CODES),
                "travel_month": random.randint(1, 12),
                "budget_tier": budget_tier,
                "preferred_activities": _pick_activities(),
                "trip_type": trip_type,
                "min_safety_threshold": min_safety,
                "profile_type": profile_type,
                "label_destination_id": label_dest_id,
                "label_score": label_score,
                "source": "synthetic",
            }
        )

        if len(batch) >= BATCH_SIZE:
            session.bulk_insert_mappings(UserPreferenceProfile, batch)
            session.commit()
            inserted += len(batch)
            batch.clear()
            logger.info("  preferences: %d / %d", inserted, n)

    if batch:
        session.bulk_insert_mappings(UserPreferenceProfile, batch)
        session.commit()
        inserted += len(batch)

    logger.info("Inserted %d user_preference_profiles.", inserted)


def generate_budgets(
    session: Session,
    destination_ids: list[uuid.UUID],
    costs_by_dest: dict[uuid.UUID, float],
    seasonality_by_dest: dict[uuid.UUID, dict[int, float]],
    n: int = 100_000,
) -> None:
    logger.info("Generating %d trip budget actuals...", n)
    inserted = 0
    batch: list[dict[str, Any]] = []

    # Per-destination persistent bias: fixed ±12% systematic deviation.
    # Simulates real-world patterns: Tokyo systematically more expensive than
    # Bangkok even at the same cost_index tier. Seed=2024 for reproducibility.
    rng = random.Random(2024)
    dest_bias: dict[uuid.UUID, float] = {dest_id: rng.gauss(1.0, 0.12) for dest_id in destination_ids}

    # Realistic people-count weights: solo/couple most common
    people_weights = [20, 35, 20, 12, 8, 5]

    for _ in range(n):
        dest_id = random.choice(destination_ids)
        avg_daily = costs_by_dest.get(dest_id, 80.0)

        duration = random.randint(3, 28)
        people = random.choices(range(1, 7), weights=people_weights)[0]
        travel_month = random.randint(1, 12)
        acc_tier = random.choice(ACCOMMODATION_TIERS)

        # Seasonal multiplier from destination seasonality [0.7, 1.35]
        season_score = seasonality_by_dest.get(dest_id, {}).get(travel_month, 0.65)
        # High season (season_score < 0.5 means bad weather → fewer tourists, lower prices)
        # Peak season has higher prices: score 0.9 → ~1.20×, score 0.5 → ~1.0×, score 0.3 → ~0.85×
        seasonal_mult = round(0.70 + season_score * 0.65, 3)

        # --- Build cost from components (each per person per day) ---
        acc_frac = ACCOMMODATION_COST_FRACTION[acc_tier]
        meals_frac = MEALS_COST_FRACTION[acc_tier]
        transport_frac = TRANSPORT_COST_FRACTION

        # Apply per-destination systematic bias (fixed per dest_id, seed=2024).
        # Jitter reduced from ±30% to ±15%: real signal comes from dest_bias,
        # not pure noise — so budget ML can learn destination-specific patterns.
        bias = dest_bias[dest_id]
        effective_daily = avg_daily * bias

        # Accommodation is per room (split among people, but min 1 room)
        rooms = max(1, (people + 1) // 2) if acc_tier == "hostel" else max(1, (people + 1) // 2)
        acc_nightly_per_room = _jitter(effective_daily * acc_frac, 0.15) * seasonal_mult
        accommodation_usd = round(acc_nightly_per_room * rooms * duration, 2)

        meals_daily_per_person = _jitter(effective_daily * meals_frac, 0.15) * seasonal_mult
        meals_usd = round(meals_daily_per_person * people * duration, 2)

        transport_daily = _jitter(effective_daily * transport_frac, 0.15)
        transport_usd = round(transport_daily * people * duration, 2)

        activities_daily = _jitter(effective_daily * ACTIVITIES_COST_FRACTION, 0.15)
        activities_usd = round(activities_daily * people * duration, 2)

        total = round(accommodation_usd + meals_usd + transport_usd + activities_usd, 2)

        batch.append(
            {
                "id": uuid.uuid4(),
                "trip_id": None,
                "destination_id": dest_id,
                "duration_days": duration,
                "people_count": people,
                "travel_month": travel_month,
                "total_actual_usd": total,
                "meals_usd": meals_usd,
                "accommodation_usd": accommodation_usd,
                "transport_usd": transport_usd,
                "activities_usd": activities_usd,
                "accommodation_tier": acc_tier,
                "data_source": "synthetic",
            }
        )

        if len(batch) >= BATCH_SIZE:
            session.bulk_insert_mappings(TripBudgetActual, batch)
            session.commit()
            inserted += len(batch)
            batch.clear()
            logger.info("  budgets: %d / %d", inserted, n)

    if batch:
        session.bulk_insert_mappings(TripBudgetActual, batch)
        session.commit()
        inserted += len(batch)

    logger.info("Inserted %d trip_budget_actuals.", inserted)


def generate_feedback(
    session: Session,
    trajectory_ids: list[uuid.UUID],
    n: int = 50_000,
) -> None:
    logger.info("Generating %d trajectory feedback records...", n)

    if not trajectory_ids:
        logger.warning("No trajectories found — skipping feedback generation.")
        return

    inserted = 0
    batch: list[dict[str, Any]] = []
    top_20_cutoff = int(len(trajectory_ids) * 0.20)
    top_trajectories = set(trajectory_ids[:top_20_cutoff])

    for _ in range(n):
        traj_id = random.choice(trajectory_ids)
        is_top = traj_id in top_trajectories

        # Top 20% trajectories get higher ratings (positive bias)
        if is_top:
            rating = random.choices([3, 4, 5], weights=[10, 35, 55])[0]
            was_completed = random.random() > 0.10
        else:
            rating = random.choices([1, 2, 3, 4, 5], weights=[10, 20, 35, 25, 10])[0]
            was_completed = random.random() > 0.25

        duration = random.randint(3, 14)
        people = random.randint(1, 6)

        batch.append(
            {
                "id": uuid.uuid4(),
                "trajectory_id": traj_id,
                "user_id": None,
                "rating": rating,
                "was_completed": was_completed,
                "people_count": people,
                "trip_duration_days": duration,
                "source": "synthetic",
            }
        )

        if len(batch) >= BATCH_SIZE:
            session.bulk_insert_mappings(TrajectoryFeedback, batch)
            session.commit()
            inserted += len(batch)
            batch.clear()
            logger.info("  feedback: %d / %d", inserted, n)

    if batch:
        session.bulk_insert_mappings(TrajectoryFeedback, batch)
        session.commit()
        inserted += len(batch)

    logger.info("Inserted %d trajectory_feedback records.", inserted)


def main(table: str | None = None) -> None:
    engine = create_engine(settings.DATABASE_URL)

    with Session(engine) as session:
        logger.info("Loading destination IDs...")
        destination_ids: list[uuid.UUID] = [row[0] for row in session.execute(select(Destination.id)).all()]
        if not destination_ids:
            logger.error("No destinations found — run ETL first.")
            return
        logger.info("  %d destinations loaded.", len(destination_ids))

        logger.info("Loading cost index per destination...")
        costs_by_dest: dict[uuid.UUID, float] = {
            row[0]: float(row[1])
            for row in session.execute(
                select(DestinationCosts.destination_id, DestinationCosts.avg_daily_cost_usd)
            ).all()
        }
        logger.info("  %d cost records loaded.", len(costs_by_dest))

        logger.info("Loading safety scores per destination...")
        safety_by_dest: dict[uuid.UUID, float] = {
            row[0]: float(row[1])
            for row in session.execute(select(DestinationSafety.destination_id, DestinationSafety.safety_score)).all()
        }
        logger.info("  %d safety records loaded.", len(safety_by_dest))

        logger.info("Loading seasonality per destination...")
        seasonality_by_dest: dict[uuid.UUID, dict[int, float]] = {}
        for row in session.execute(text("SELECT destination_id, month, season_score FROM destination_seasonality")):
            did = row[0]
            seasonality_by_dest.setdefault(did, {})[int(row[1])] = float(row[2])
        logger.info("  %d destinations with seasonality.", len(seasonality_by_dest))

        logger.info("Loading trajectory IDs...")
        trajectory_ids: list[uuid.UUID] = [row[0] for row in session.execute(select(Trajectory.id)).all()]
        logger.info("  %d trajectories loaded.", len(trajectory_ids))

        if table is None or table == "preferences":
            generate_preferences(session, destination_ids, safety_by_dest)

        if table is None or table == "budgets":
            generate_budgets(session, destination_ids, costs_by_dest, seasonality_by_dest)

        if table is None or table == "feedback":
            generate_feedback(session, trajectory_ids)

    logger.info("Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic ML training data")
    parser.add_argument(
        "--table",
        choices=["preferences", "budgets", "feedback"],
        default=None,
        help="Which table to populate (default: all)",
    )
    args = parser.parse_args()
    main(table=args.table)
