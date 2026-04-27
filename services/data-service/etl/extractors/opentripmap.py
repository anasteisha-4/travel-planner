"""Extract POI data from OpenTripMap API.

Uses 4 batched category requests per destination instead of 16 individual ones,
reducing daily API usage from 16× to 4× per destination (~250 destinations/day).

State tracking via data/state/poi_progress.json allows resumable multi-day runs.
"""

import json
import logging
import time
from datetime import date
from pathlib import Path

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

BASE_URL = "https://api.opentripmap.com/0.1/en/places"
STATE_FILE = Path("/app/data/state/poi_progress.json")
DAILY_REQUEST_LIMIT = 950  # safe margin below 1000/day

# 4 batched category groups (16 individual → 4 requests per destination)
# Validated kinds against OTM API — "parks" and "spa" return 400
CATEGORY_BATCHES: dict[str, tuple[str, str]] = {
    "cultural": ("historic,cultural,architecture,religion,museums", "culture"),
    "nature": ("beaches,natural,natural_springs", "nature"),
    "leisure": ("sport,amusements,foods,restaurants,cafes", "food"),
    "urban": ("shops,adult,accomodations", "shopping"),
}


def _load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {
        "opentripmap": {
            "completed": [],
            "last_run_date": None,
            "total_completed": 0,
            "requests_today": 0,
        }
    }


def _save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def fetch_poi_for_destination(
    destination_id: str, lat: float, lng: float, radius_m: int = 20000
) -> tuple[list[dict], int]:
    """Fetch POI for one destination using 4 batched requests.

    Returns (poi_list, requests_used).
    """
    if not settings.OPENTRIPMAP_API_KEY:
        logger.warning("OPENTRIPMAP_API_KEY not set, skipping OpenTripMap extraction.")
        return [], 0

    results = []
    requests_used = 0

    for batch_name, (kinds, activity_type) in CATEGORY_BATCHES.items():
        try:
            params = {
                "radius": radius_m,
                "lon": lng,
                "lat": lat,
                "kinds": kinds,
                "apikey": settings.OPENTRIPMAP_API_KEY,
                "limit": 100,
                "format": "json",
            }
            with httpx.Client(timeout=20) as client:
                response = client.get(f"{BASE_URL}/radius", params=params)
                response.raise_for_status()
                features = response.json()
            requests_used += 1

            for feature in features:
                point = feature.get("point", {})
                results.append(
                    {
                        "destination_id": destination_id,
                        "name": feature.get("name", ""),
                        "lat": point.get("lat", 0),
                        "lng": point.get("lon", 0),
                        "category": activity_type,
                        "external_id": str(feature.get("xid", "")),
                        "rating": feature.get("rate", 0),
                        "tags": [kinds],
                    }
                )
            time.sleep(0.2)
        except Exception as e:
            logger.warning(f"OpenTripMap fetch failed for batch={batch_name}: {e}")

    return results, requests_used


def extract_poi_opentripmap(limit: int | None = None) -> list[dict]:
    """Fetch POI for active destinations with state tracking and daily limit enforcement.

    Args:
        limit: Max destinations to process in this run. None = all pending.
    """
    from app.database import SessionLocal
    from app.models import Destination

    state = _load_state()
    otm_state = state.setdefault(
        "opentripmap",
        {
            "completed": [],
            "last_run_date": None,
            "total_completed": 0,
            "requests_today": 0,
        },
    )

    today = date.today().isoformat()
    if otm_state.get("last_run_date") != today:
        otm_state["requests_today"] = 0
        logger.info("New day — daily request counter reset.")

    completed_ids = set(otm_state["completed"])
    requests_today = int(otm_state["requests_today"])

    db = SessionLocal()
    try:
        destinations = (
            db.query(Destination)
            .filter(Destination.is_active == True)  # noqa: E712
            .order_by(Destination.population.desc().nullslast())
            .all()
        )
    finally:
        db.close()

    pending = [d for d in destinations if str(d.id) not in completed_ids]
    if limit is not None:
        pending = pending[:limit]

    logger.info(f"OpenTripMap: {len(completed_ids)} completed, {len(pending)} pending, {requests_today} requests today")

    all_poi: list[dict] = []
    for dest in pending:
        if requests_today >= DAILY_REQUEST_LIMIT:
            logger.info(
                f"Daily limit reached ({requests_today}/{DAILY_REQUEST_LIMIT}). Resume tomorrow: make fetch-poi-otm"
            )
            break

        poi, used = fetch_poi_for_destination(str(dest.id), dest.lat, dest.lng)
        all_poi.extend(poi)
        requests_today += used

        otm_state["completed"].append(str(dest.id))
        otm_state["last_run_date"] = today
        otm_state["total_completed"] = len(otm_state["completed"])
        otm_state["requests_today"] = requests_today
        _save_state(state)

        logger.info(f"Fetched {len(poi)} POI for {dest.name} (running total: {requests_today}/{DAILY_REQUEST_LIMIT})")

    return all_poi
