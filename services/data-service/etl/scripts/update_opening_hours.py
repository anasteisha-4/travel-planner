"""Incremental opening_hours enrichment from OpenStreetMap.

Fetches ONLY elements that have the opening_hours tag (targeted query),
updates POI records where opening_hours IS NULL, matches by external_id.

Key design decisions (mirroring overpass_wellness.py patterns):
- [timeout:25] — short Overpass timeout, fast fail on overloaded servers
- Server error → skip city (not marked completed), retried on next run
- Bulk DB update: one SELECT to find matching POI, then executemany UPDATE
- Rotates across 3 Overpass mirrors on consecutive attempts

State key: "opening_hours_update" — independent from main ETL state.

Usage (from container):
    python -m etl.scripts.update_opening_hours
    python -m etl.scripts.update_opening_hours --limit 10
    python -m etl.scripts.update_opening_hours --reset
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path

import httpx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

OVERPASS_SERVERS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
STATE_FILE = Path("/app/data/state/poi_progress.json")
STATE_KEY = "opening_hours_update"
SLEEP_BETWEEN_CITIES = 5.0
SLEEP_ON_RATE_LIMIT = 60.0
MAX_RETRIES = 3

# Short timeout: opening_hours-filtered query is small, fail fast if server is busy
_QUERY = """
[out:json][timeout:25];
(
  node["opening_hours"](around:{radius},{lat},{lng});
  way["opening_hours"](around:{radius},{lat},{lng});
);
out ids tags;
"""


def _load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {}


def _save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def _fetch(dest_id: str, lat: float, lng: float, radius_m: int) -> list[dict] | None:
    """Return list of elements on success, None on server error (will retry next run)."""
    query = _QUERY.format(radius=radius_m, lat=lat, lng=lng)
    for attempt in range(1, MAX_RETRIES + 1):
        server = OVERPASS_SERVERS[(attempt - 1) % len(OVERPASS_SERVERS)]
        try:
            with httpx.Client(timeout=40) as client:
                resp = client.post(server, data={"data": query})
            if resp.status_code == 429:
                wait = SLEEP_ON_RATE_LIMIT * attempt
                logger.warning(f"429 from {server} attempt {attempt}, sleep {wait}s")
                time.sleep(wait)
                continue
            if resp.status_code == 504:
                wait = 30 * attempt
                logger.warning(f"504 from {server} attempt {attempt}, sleep {wait}s")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json().get("elements", [])
        except Exception as e:
            if attempt == MAX_RETRIES:
                logger.warning(f"Overpass failed for {dest_id}: {e}")
                return None  # server error → skip, retry next run
            time.sleep(10 * attempt)
    return None


def _bulk_update(oh_map: dict[str, str]) -> int:
    """Update opening_hours for POI matched by external_id. Returns count updated."""
    from app.database import SessionLocal
    from app.models import POI

    db = SessionLocal()
    try:
        # Single SELECT to find which external_ids exist in our DB with NULL opening_hours
        ext_ids = list(oh_map.keys())
        matches = (
            db.query(POI.id, POI.external_id).filter(POI.external_id.in_(ext_ids), POI.opening_hours.is_(None)).all()
        )
        if not matches:
            return 0

        # Bulk UPDATE via executemany — one round-trip for all matched rows
        db.execute(
            POI.__table__.update().where(POI.__table__.c.id == POI.__table__.c.id),
            # SQLAlchemy Core bulk update: use direct execute with list of dicts
        )
        # Use raw execute for efficiency
        from sqlalchemy import text

        db.execute(
            text("UPDATE poi SET opening_hours = :oh WHERE id = :id AND opening_hours IS NULL"),
            [{"oh": oh_map[ext_id], "id": str(row_id)} for row_id, ext_id in matches],
        )
        db.commit()
        return len(matches)
    except Exception as e:
        db.rollback()
        logger.error(f"DB bulk update error: {e}")
        return 0
    finally:
        db.close()


def run(limit: int | None = None, reset: bool = False) -> None:
    from datetime import date

    from app.database import SessionLocal
    from app.models import Destination

    state = _load_state()
    job = state.setdefault(STATE_KEY, {"completed": [], "total_updated": 0})

    if reset:
        job["completed"] = []
        job["total_updated"] = 0
        _save_state(state)
        logger.info("State reset")

    completed_ids = set(job["completed"])

    db = SessionLocal()
    try:
        destinations = (
            db.query(Destination)
            .filter(Destination.is_active == True)  # noqa: E712
            .order_by(Destination.name)
            .all()
        )
    finally:
        db.close()

    pending = [d for d in destinations if str(d.id) not in completed_ids]
    if limit is not None:
        pending = pending[:limit]

    logger.info(f"opening_hours update: {len(pending)} pending / {len(completed_ids)} done")

    total_updated = int(job.get("total_updated", 0))

    for i, dest in enumerate(pending, 1):
        dest_id = str(dest.id)
        logger.info(f"[{i}/{len(pending)}] {dest.name} ({dest.country_code})")

        elements = _fetch(dest_id, dest.lat, dest.lng, dest.radius_m)

        if elements is None:
            # Server error — skip, will retry on next run (don't mark completed)
            logger.warning("  → skipped (server error), will retry")
            time.sleep(SLEEP_BETWEEN_CITIES)
            continue

        oh_map = {
            f"osm:{el['id']}": el["tags"]["opening_hours"] for el in elements if el.get("tags", {}).get("opening_hours")
        }

        updated = 0
        if oh_map:
            updated = _bulk_update(oh_map)
            if updated:
                logger.info(f"  → {updated} POI updated (OSM had {len(oh_map)} with opening_hours)")

        total_updated += updated
        job["completed"].append(dest_id)
        job["total_updated"] = total_updated
        job["last_run_date"] = date.today().isoformat()
        _save_state(state)

        if i < len(pending):
            time.sleep(SLEEP_BETWEEN_CITIES)

    logger.info(f"Done. Total POI updated: {total_updated}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int)
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()
    run(limit=args.limit, reset=args.reset)
