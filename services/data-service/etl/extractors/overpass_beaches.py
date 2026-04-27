"""Supplementary beach POI extractor via Overpass API.

Collects beach features NOT reliably covered by the main OSM scrape:
  natural=beach    → coastal/river beaches (nodes AND ways)
  leisure=beach    → managed/leisure beaches
  amenity=beach_resort → resort beaches with facilities

Additional tags captured for richer data:
  surface (sand, gravel, shingle), access (yes/private/permissive),
  area (m²), fee (yes/no), lifeguard (yes/no/seasonal)

All results go to category='beach', source='overpass_osm'.
Deduplication handled by (source, external_id) unique constraint on upsert.

Why a separate extractor:
  The main overpass_osm.py fetches beach nodes and ways, but unnamed beaches
  all collapse to name="Beach" which gets _GENERIC_WEIGHT=0.25 in the transformer.
  This extractor adds way-geometry beaches (which are large coastline polygons) that
  the main scrape may miss, and enriches existing beach POI with surface/access data.
"""

import json
import logging
import time
from collections.abc import Generator
from datetime import date
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
STATE_FILE = Path("/app/data/state/poi_progress.json")
SLEEP_BETWEEN_CITIES = 5.0
SLEEP_ON_RATE_LIMIT = 60.0
MAX_RETRIES = 3

_QUERY = """
[out:json][timeout:30];
(
  node["natural"="beach"](around:{radius},{lat},{lng});
  way["natural"="beach"](around:{radius},{lat},{lng});
  relation["natural"="beach"](around:{radius},{lat},{lng});
  node["leisure"="beach_resort"](around:{radius},{lat},{lng});
  way["leisure"="beach_resort"](around:{radius},{lat},{lng});
  node["leisure"="beach"](around:{radius},{lat},{lng});
  way["leisure"="beach"](around:{radius},{lat},{lng});
  node["amenity"="beach_resort"](around:{radius},{lat},{lng});
  way["amenity"="beach_resort"](around:{radius},{lat},{lng});
);
out center tags;
"""


def _build_name(tags: dict) -> str | None:
    """Return best available name for the beach element."""
    name = tags.get("name") or tags.get("name:en") or tags.get("name:ru")
    if name:
        return name
    # Unnamed beach — generate descriptive name from surface tag
    surface = tags.get("surface")
    if surface in ("sand", "sandy"):
        return "Sandy Beach"
    if surface in ("gravel", "shingle", "pebbles", "pebble"):
        return "Pebble Beach"
    # Generic fallback — still valid coastline feature
    return "Beach"


def _popularity_score(tags: dict) -> float:
    """Score based on tag richness and known quality signals."""
    score = 0.5
    if "wikipedia" in tags:
        score += 0.2
    if "wikidata" in tags:
        score += 0.1
    if tags.get("tourism") == "attraction":
        score += 0.15
    if tags.get("fee") == "no" and tags.get("access") in ("yes", "public", None):
        score += 0.03  # free public beach is a mild positive signal
    if tags.get("lifeguard") in ("yes", "seasonal"):
        score += 0.03
    return min(round(score, 4), 1.0)


def _build_tags_list(tags: dict) -> list[str]:
    relevant = (
        "natural",
        "leisure",
        "amenity",
        "surface",
        "access",
        "fee",
        "lifeguard",
        "sport",
    )
    return [f"{k}={v}" for k, v in tags.items() if k in relevant]


def fetch_beaches_for_destination(
    destination_id: str,
    lat: float,
    lng: float,
    radius_m: int = 20000,
) -> list[dict] | None:
    """Return list of beach POI on success (empty = no beaches), None on server error."""
    query = _QUERY.format(radius=radius_m, lat=lat, lng=lng)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with httpx.Client(timeout=45) as client:
                response = client.post(OVERPASS_URL, data={"data": query})
                if response.status_code == 429:
                    wait = SLEEP_ON_RATE_LIMIT * attempt
                    logger.warning(f"Overpass 429 (attempt {attempt}), sleeping {wait}s")
                    time.sleep(wait)
                    continue
                if response.status_code == 504:
                    wait = 30 * attempt
                    logger.warning(f"Overpass 504 (attempt {attempt}), sleeping {wait}s")
                    time.sleep(wait)
                    continue
                response.raise_for_status()
                elements = response.json().get("elements", [])
                break
        except Exception as e:
            if attempt == MAX_RETRIES:
                logger.warning(f"Beach fetch failed for {destination_id}: {e}")
                return None
            time.sleep(10 * attempt)
    else:
        return None

    results = []
    for el in elements:
        tags = el.get("tags", {})
        name = _build_name(tags)
        if not name:
            continue

        center = el.get("center", {})
        el_lat = float(center.get("lat", el.get("lat", lat)))
        el_lng = float(center.get("lon", el.get("lon", lng)))

        results.append(
            {
                "destination_id": destination_id,
                "name": name,
                "lat": el_lat,
                "lng": el_lng,
                "category": "beach",
                "source": "overpass_osm",
                "external_id": f"osm:{el['id']}",
                "rating": None,
                "popularity_score": _popularity_score(tags),
                "address": tags.get("addr:full") or tags.get("addr:street"),
                "description": tags.get("description"),
                "tags": _build_tags_list(tags),
            }
        )

    return results


def iter_beaches_overpass(
    limit: int | None = None,
) -> Generator[tuple[str, list[dict]], None, None]:
    """Yield (dest_name, poi_list) per destination. Resumable via state file."""
    from app.database import SessionLocal
    from app.models import Destination

    state = _load_state()
    beaches_state = state.setdefault(
        "beaches_supplement",
        {"completed": [], "last_run_date": None, "total_completed": 0},
    )
    completed_ids = set(beaches_state["completed"])

    db = SessionLocal()
    try:
        destinations = (
            db.query(Destination)
            .filter(Destination.is_active == True)  # noqa: E712
            .all()
        )
    finally:
        db.close()

    pending = [d for d in destinations if str(d.id) not in completed_ids]
    if limit is not None:
        pending = pending[:limit]

    logger.info(f"Beach supplement: {len(completed_ids)} done, {len(pending)} pending")

    for dest in pending:
        poi = fetch_beaches_for_destination(str(dest.id), dest.lat, dest.lng, radius_m=dest.radius_m)

        if poi is None:
            logger.warning(f"Skipping {dest.name} (server error), will retry next run")
            time.sleep(SLEEP_BETWEEN_CITIES)
            continue

        yield dest.name, poi

        beaches_state["completed"].append(str(dest.id))
        beaches_state["total_completed"] = len(beaches_state["completed"])
        beaches_state["last_run_date"] = date.today().isoformat()
        _save_state(state)

        time.sleep(SLEEP_BETWEEN_CITIES)


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
