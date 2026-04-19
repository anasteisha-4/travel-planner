"""Extract historical weather data from Open-Meteo Archive API."""

import logging
import time
from datetime import date

import httpx

logger = logging.getLogger(__name__)

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"


def extract_weather(lat: float, lng: float, year: int | None = None) -> dict:
    """Fetch daily mean temperature and precipitation for a full year."""
    if year is None:
        year = date.today().year - 1  # previous full year

    params = {
        "latitude": lat,
        "longitude": lng,
        "start_date": f"{year}-01-01",
        "end_date": f"{year}-12-31",
        "daily": "temperature_2m_mean,precipitation_sum,relative_humidity_2m_mean",
        "timezone": "UTC",
    }
    with httpx.Client(timeout=30) as client:
        response = client.get(ARCHIVE_URL, params=params)
        response.raise_for_status()
    return response.json()


def extract_weather_for_all_destinations(skip_existing: bool = True) -> list[dict]:
    """Fetch weather for every active destination. Batched to avoid rate limits.

    Args:
        skip_existing: If True (default), skip destinations that already have 12
                       seasonality records. Safe to re-run after adding new destinations.
    """
    from app.database import SessionLocal
    from app.models import Destination
    from app.models.destination import DestinationSeasonality
    from sqlalchemy import func

    db = SessionLocal()
    try:
        destinations = db.query(Destination).filter(Destination.is_active == True).all()  # noqa: E712

        if skip_existing:
            covered = (
                db.query(DestinationSeasonality.destination_id)
                .group_by(DestinationSeasonality.destination_id)
                .having(func.count() >= 12)
                .all()
            )
            covered_ids = {str(r[0]) for r in covered}
            before = len(destinations)
            destinations = [d for d in destinations if str(d.id) not in covered_ids]
            logger.info(
                f"skip_existing=True: skipping {before - len(destinations)} covered, {len(destinations)} remaining."
            )
    finally:
        db.close()

    results = []
    for dest in destinations:
        try:
            weather = extract_weather(dest.lat, dest.lng)
            results.append({"destination_id": str(dest.id), "weather": weather})
        except Exception as e:
            logger.warning(f"Failed to fetch weather for {dest.name}: {e}")
        finally:
            time.sleep(0.1)  # rate limit: always pause, even after failures

    return results
