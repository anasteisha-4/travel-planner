"""One-time migration script: copy preferences from auth-service users → trip-service user_profiles."""

import os
import sys
import uuid
from decimal import Decimal

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings

DURATION_MAP = {
    "week": "short",
    "two_weeks": "standard",
    "month": "long",
    "weekend": "weekend",
    "extended": "extended",
}

DURATION_DAYS = {
    "weekend": 2,
    "short": 5,
    "standard": 10,
    "long": 21,
    "extended": 45,
}


def run():
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()

    users = db.execute(text("SELECT id, preferences FROM users WHERE preferences IS NOT NULL")).fetchall()
    print(f"Found {len(users)} users with preferences")

    migrated = 0
    skipped = 0

    for user_id, preferences in users:
        if not preferences:
            continue

        existing = db.execute(
            text("SELECT id FROM user_profiles WHERE user_id = :uid"),
            {"uid": user_id},
        ).fetchone()
        if existing:
            skipped += 1
            continue

        travel_types = preferences.get("travel_types") or []
        currency = preferences.get("currency") or "RUB"
        budget_min = preferences.get("budget_min")
        budget_max = preferences.get("budget_max")
        trip_duration_raw = preferences.get("trip_duration")
        departure_city = preferences.get("departure_city")
        favorite_destinations = preferences.get("favorite_destinations") or ""
        additional_info = preferences.get("additional_info") or ""

        typical_duration = DURATION_MAP.get(trip_duration_raw) if trip_duration_raw else None
        typical_duration_days = DURATION_DAYS.get(typical_duration) if typical_duration else None

        free_text_parts = []
        if favorite_destinations:
            free_text_parts.append(f"Любимые направления: {favorite_destinations}")
        if additional_info:
            free_text_parts.append(additional_info)
        free_text_notes = "\n".join(free_text_parts) or None

        db.execute(
            text("""
                INSERT INTO user_profiles (
                    id, user_id,
                    vacation_preferences_ranked, preferred_currency,
                    budget_min, budget_max,
                    typical_duration, typical_duration_days,
                    origin_city_name,
                    free_text_notes,
                    onboarding_completed, onboarding_step,
                    created_at, updated_at
                ) VALUES (
                    :id, :user_id,
                    :vacation_preferences_ranked, :preferred_currency,
                    :budget_min, :budget_max,
                    :typical_duration, :typical_duration_days,
                    :origin_city_name,
                    :free_text_notes,
                    false, 0,
                    now(), now()
                )
            """),
            {
                "id": str(uuid.uuid4()),
                "user_id": str(user_id),
                "vacation_preferences_ranked": travel_types if travel_types else None,
                "preferred_currency": currency,
                "budget_min": Decimal(str(budget_min)) if budget_min is not None else None,
                "budget_max": Decimal(str(budget_max)) if budget_max is not None else None,
                "typical_duration": typical_duration,
                "typical_duration_days": typical_duration_days,
                "origin_city_name": departure_city or None,
                "free_text_notes": free_text_notes,
            },
        )
        migrated += 1

    db.commit()
    db.close()

    print(f"Done: migrated={migrated}, skipped(already exist)={skipped}")


if __name__ == "__main__":
    run()
