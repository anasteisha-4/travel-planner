"""Extract OSM protected areas (national parks, nature reserves) via Overpass API.

Queries relation/way objects with boundary=protected_area and IUCN protect_class 1-5.
These are large-area features (national parks, wilderness areas) that point-based
OSM queries miss entirely — critical for correct nature scoring.

IUCN classes fetched:
  1a/1b — Strict Nature Reserve / Wilderness Area
  2     — National Park (Yellowstone, Fiordland, Kruger, Banff…)
  3     — Natural Monument
  4     — Habitat/Species Management Area
  5     — Protected Landscape / Seascape
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
SLEEP_BETWEEN_CITIES = 3.0
SLEEP_ON_RATE_LIMIT = 60.0
MAX_RETRIES = 3

# popularity_score by protect class: stricter protection = higher significance
_CLASS_SCORE: dict[str, float] = {
    "1": 0.95,
    "1a": 0.95,
    "1b": 0.95,
    "2": 0.95,  # National Parks — top significance
    "3": 0.90,
    "4": 0.85,
    "5": 0.80,
    "6": 0.75,
}
_DEFAULT_SCORE = 0.80

_QUERY = """
[out:json][timeout:45];
(
  relation["boundary"="protected_area"]["protect_class"~"^(1|1a|1b|2|3|4|5|6)$"](around:{radius},{lat},{lng});
  way["boundary"="protected_area"]["protect_class"~"^(1|1a|1b|2|3|4|5|6)$"](around:{radius},{lat},{lng});
  relation["boundary"="national_park"](around:{radius},{lat},{lng});
  way["boundary"="national_park"](around:{radius},{lat},{lng});
);
out center tags;
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


def fetch_protected_areas_for_destination(
    destination_id: str,
    lat: float,
    lng: float,
    radius_m: int = 50000,  # 50km — parks extend well beyond city center
) -> list[dict]:
    query = _QUERY.format(radius=radius_m, lat=lat, lng=lng)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with httpx.Client(timeout=60) as client:
                response = client.post(OVERPASS_URL, data={"data": query})
                if response.status_code == 429:
                    logger.warning(f"Overpass 429 (attempt {attempt}), sleeping {SLEEP_ON_RATE_LIMIT}s")
                    time.sleep(SLEEP_ON_RATE_LIMIT)
                    continue
                if response.status_code == 504:
                    logger.warning(f"Overpass 504 (attempt {attempt}), sleeping 30s")
                    time.sleep(30)
                    continue
                response.raise_for_status()
                elements = response.json().get("elements", [])
                break
        except Exception as e:
            if attempt == MAX_RETRIES:
                logger.warning(f"Protected areas fetch failed for {destination_id}: {e}")
                return []
            time.sleep(10 * attempt)
    else:
        return []

    results = []
    seen_names: set[str] = set()

    for el in elements:
        tags = el.get("tags", {})
        name = tags.get("name:en") or tags.get("name") or tags.get("official_name")
        if not name:
            continue

        # Deduplicate by name within same destination (same park can appear as way + relation)
        if name in seen_names:
            continue
        seen_names.add(name)

        center = el.get("center", {})
        el_lat = float(center.get("lat", lat))
        el_lng = float(center.get("lon", lng))

        protect_class = tags.get("protect_class", "")
        score = _CLASS_SCORE.get(protect_class, _DEFAULT_SCORE)

        # Determine category: national_park / wilderness → nature; landscape → nature
        el_tags = []
        if tags.get("boundary") == "national_park" or protect_class in (
            "1",
            "1a",
            "1b",
            "2",
        ):
            category = "nature"
            el_tags.append("boundary=national_park")
        elif protect_class in ("3",):
            category = "nature"
            el_tags.append("boundary=protected_area")
        else:
            category = "nature"
            el_tags.append("boundary=protected_area")

        if protect_class:
            el_tags.append(f"protect_class={protect_class}")
        if tags.get("wikidata"):
            el_tags.append(f"wikidata={tags['wikidata']}")

        results.append(
            {
                "destination_id": destination_id,
                "name": name,
                "lat": el_lat,
                "lng": el_lng,
                "category": category,
                "source": "heritage",
                "external_id": f"osm_pa:{el['type']}:{el['id']}",
                "rating": None,
                "popularity_score": score,
                "address": None,
                "description": tags.get("description"),
                "tags": el_tags,
            }
        )

    return results


def iter_protected_areas(
    limit: int | None = None,
) -> Generator[tuple[str, list[dict]], None, None]:
    """Yield (dest_name, poi_list) per destination for protected areas. Resumable."""
    from app.database import SessionLocal
    from app.models import Destination

    state = _load_state()
    pa_state = state.setdefault(
        "protected_areas",
        {"completed": [], "last_run_date": None, "total_completed": 0},
    )
    completed_ids = set(pa_state["completed"])

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

    logger.info(f"Protected areas: {len(completed_ids)} done, {len(pending)} pending")

    for dest in pending:
        poi = fetch_protected_areas_for_destination(
            str(dest.id), dest.lat, dest.lng, radius_m=max(dest.radius_m, 50000)
        )
        yield dest.name, poi

        pa_state["completed"].append(str(dest.id))
        pa_state["total_completed"] = len(pa_state["completed"])
        pa_state["last_run_date"] = date.today().isoformat()
        _save_state(state)

        time.sleep(SLEEP_BETWEEN_CITIES)
