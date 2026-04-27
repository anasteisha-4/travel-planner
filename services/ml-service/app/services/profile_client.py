import uuid

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings


class ProfileNotFoundError(Exception):
    pass


class OnboardingIncompleteError(Exception):
    pass


def _get_profile_sync(db: Session, user_id: uuid.UUID) -> dict:
    """Read user profile directly from trip-service tables (same shared DB)."""
    row = db.execute(
        text("SELECT * FROM user_profiles WHERE user_id = :uid"),
        {"uid": str(user_id)},
    ).fetchone()

    if row is None:
        return {
            "onboarding_completed": False,
            "vacation_preferences_ranked": [],
            "budget_min_usd": None,
            "budget_max_usd": None,
            "typical_duration_days": 10,
            "typical_duration": None,
            "risk_tolerance": None,
            "visa_tolerance": "any_visa",
            "language_comfort": ["any"],
            "crowd_preference": None,
            "climate_preferences": [],
            "liked_destination_ids": [],
            "origin_lat": None,
            "origin_lng": None,
        }

    m = dict(row._mapping)
    _enum_to_days = {"weekend": 2, "short": 5, "standard": 10, "long": 21, "extended": 45}
    typical_duration_days = m.get("typical_duration_days")
    if typical_duration_days is None:
        typical_duration_days = _enum_to_days.get(m.get("typical_duration") or "standard", 10)
    else:
        typical_duration_days = int(float(typical_duration_days))
    return {
        "onboarding_completed": bool(m.get("onboarding_completed", False)),
        "vacation_preferences_ranked": m.get("vacation_preferences_ranked") or [],
        "budget_min_usd": float(m["budget_min_usd"]) if m.get("budget_min_usd") else None,
        "budget_max_usd": float(m["budget_max_usd"]) if m.get("budget_max_usd") else None,
        "typical_duration_days": typical_duration_days,
        "typical_duration": m.get("typical_duration"),
        "risk_tolerance": m.get("risk_tolerance"),
        "visa_tolerance": m.get("visa_tolerance") or "any_visa",
        "language_comfort": m.get("language_comfort") or ["any"],
        "crowd_preference": m.get("crowd_preference"),
        "climate_preferences": m.get("climate_preferences") or [],
        "liked_destination_ids": m.get("liked_destination_ids") or [],
        "origin_lat": float(m["origin_lat"]) if m.get("origin_lat") else None,
        "origin_lng": float(m["origin_lng"]) if m.get("origin_lng") else None,
    }


async def get_user_profile(user_id: uuid.UUID, auth_header: str) -> dict:
    url = f"{settings.TRIP_SERVICE_URL}/api/profile"
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.get(url, headers={"Authorization": auth_header})
        if response.status_code == 404:
            raise ProfileNotFoundError(f"Profile not found for user {user_id}")
        response.raise_for_status()
        return response.json()


async def get_user_profile_checked(user_id: uuid.UUID, auth_header: str) -> dict:
    """Fetch profile and raise OnboardingIncompleteError if onboarding not done."""
    profile = await get_user_profile(user_id, auth_header)
    if not profile.get("onboarding_completed", False):
        raise OnboardingIncompleteError("User has not completed onboarding")
    return profile
