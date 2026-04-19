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

from sqlalchemy import create_engine, select
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

ACCOMMODATION_TIER_SHARE = {
    "hostel": 0.20,
    "budget": 0.35,
    "mid": 0.50,
    "luxury": 0.75,
}


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
    n: int = 100_000,
) -> None:
    logger.info("Generating %d trip budget actuals...", n)
    inserted = 0
    batch: list[dict[str, Any]] = []

    for _ in range(n):
        dest_id = random.choice(destination_ids)
        avg_daily = costs_by_dest.get(dest_id, 80.0)

        duration = random.randint(3, 21)
        people = random.randint(1, 6)
        travel_month = random.randint(1, 12)
        acc_tier = random.choice(ACCOMMODATION_TIERS)
        budget_tier = random.choice(BUDGET_TIERS)

        tier_mult = BUDGET_TIER_MULTIPLIERS[budget_tier]
        acc_share = ACCOMMODATION_TIER_SHARE[acc_tier]

        # Base daily spend for 1 person
        daily_per_person = _jitter(avg_daily * tier_mult)

        total = round(daily_per_person * duration * people, 2)

        # Split proportions with noise
        meals_share = _jitter(0.30, 0.15)
        acc_daily_share = _jitter(acc_share, 0.15)
        transport_share = _jitter(0.15, 0.20)
        activities_share = _jitter(0.10, 0.30)

        denom = meals_share + acc_daily_share + transport_share + activities_share
        meals_usd = round(total * meals_share / denom, 2)
        accommodation_usd = round(total * acc_daily_share / denom, 2)
        transport_usd = round(total * transport_share / denom, 2)
        activities_usd = round(total * activities_share / denom, 2)

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
        destination_ids: list[uuid.UUID] = [
            row[0] for row in session.execute(select(Destination.id)).all()
        ]
        if not destination_ids:
            logger.error("No destinations found — run ETL first.")
            return
        logger.info("  %d destinations loaded.", len(destination_ids))

        logger.info("Loading cost index per destination...")
        costs_by_dest: dict[uuid.UUID, float] = {
            row[0]: float(row[1])
            for row in session.execute(
                select(
                    DestinationCosts.destination_id, DestinationCosts.avg_daily_cost_usd
                )
            ).all()
        }
        logger.info("  %d cost records loaded.", len(costs_by_dest))

        logger.info("Loading safety scores per destination...")
        safety_by_dest: dict[uuid.UUID, float] = {
            row[0]: float(row[1])
            for row in session.execute(
                select(DestinationSafety.destination_id, DestinationSafety.safety_score)
            ).all()
        }
        logger.info("  %d safety records loaded.", len(safety_by_dest))

        logger.info("Loading trajectory IDs...")
        trajectory_ids: list[uuid.UUID] = [
            row[0] for row in session.execute(select(Trajectory.id)).all()
        ]
        logger.info("  %d trajectories loaded.", len(trajectory_ids))

        if table is None or table == "preferences":
            generate_preferences(session, destination_ids, safety_by_dest)

        if table is None or table == "budgets":
            generate_budgets(session, destination_ids, costs_by_dest)

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
