"""Extract POI data from OpenStreetMap via Overpass API.

Processes destinations one at a time and yields results so the pipeline can
upsert incrementally — avoids OOM on large runs. State is saved after each
city so the run is fully resumable after a crash.
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
SLEEP_BETWEEN_CITIES = 5.0  # polite delay; Overpass asks for ≥ a few seconds
SLEEP_ON_RATE_LIMIT = 60.0  # back off when 429
MAX_RETRIES = 3

# Tags where unnamed objects are still valid POI — generate descriptive name from tag value
UNNAMED_FRIENDLY: dict[str, str] = {
    "natural:beach": "Beach",
    "leisure:beach": "Beach",
    "natural:peak": "Peak",
    "natural:waterfall": "Waterfall",
    "natural:hot_spring": "Hot Spring",
    "natural:cave_entrance": "Cave",
    "amenity:spa": "Spa",
    "leisure:park": "Park",
    "leisure:garden": "Garden",
    "tourism:viewpoint": "Viewpoint",
}

# Overpass tag → activity_type mapping
OSM_TAG_TO_ACTIVITY: dict[str, str] = {
    "tourism:museum": "culture",
    "tourism:attraction": "culture",
    "tourism:gallery": "culture",
    "tourism:artwork": "culture",
    "tourism:viewpoint": "culture",
    "tourism:theme_park": "family",
    "tourism:zoo": "family",
    "tourism:aquarium": "family",
    "amenity:restaurant": "food",
    "amenity:cafe": "food",
    "amenity:bar": "nightlife",
    "amenity:nightclub": "nightlife",
    "amenity:spa": "wellness",
    "amenity:theatre": "culture",
    "leisure:beach": "beach",
    "leisure:park": "nature",
    "leisure:garden": "nature",
    "leisure:sports_centre": "adventure",
    "leisure:water_park": "family",
    "natural:beach": "beach",
    "natural:peak": "nature",
    "natural:waterfall": "nature",
    "natural:hot_spring": "nature",  # geothermal features, not wellness facilities
    "natural:cave_entrance": "nature",
    "historic:monument": "culture",
    "historic:castle": "culture",
    "historic:ruins": "culture",
    "historic:archaeological_site": "culture",
    "historic:memorial": "culture",
    "shop:mall": "shopping",
    "shop:department_store": "shopping",
    "shop:market": "shopping",
}

_OVERPASS_QUERY = """
[out:json][timeout:30];
(
  node["tourism"~"attraction|museum|gallery|artwork|viewpoint|theme_park|zoo|aquarium"](around:{radius},{lat},{lng});
  node["amenity"~"restaurant|cafe|bar|nightclub|spa|theatre"](around:{radius},{lat},{lng});
  node["leisure"~"beach|park|garden|sports_centre|water_park"](around:{radius},{lat},{lng});
  node["natural"~"beach|peak|hot_spring|waterfall|cave_entrance"](around:{radius},{lat},{lng});
  node["historic"~"monument|ruins|castle|archaeological_site|memorial"](around:{radius},{lat},{lng});
  node["shop"~"mall|department_store|market"](around:{radius},{lat},{lng});
  way["natural"~"beach"](around:{radius},{lat},{lng});
  way["leisure"~"beach|park|garden|water_park"](around:{radius},{lat},{lng});
  way["natural"~"waterfall|hot_spring|cave_entrance"](around:{radius},{lat},{lng});
  way["amenity"~"spa"](around:{radius},{lat},{lng});
);
out center;
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


def _popularity_score(tags: dict) -> float:
    score = 0.5
    if "wikipedia" in tags:
        score += 0.2
    if "wikidata" in tags:
        score += 0.1
    if "tourism" in tags:
        score += 0.15
    if "historic" in tags:
        score += 0.05
    return min(round(score, 4), 1.0)


def _activity_type(tags: dict) -> str:
    for key in ("tourism", "amenity", "leisure", "natural", "historic", "shop"):
        val = tags.get(key)
        if val:
            mapped = OSM_TAG_TO_ACTIVITY.get(f"{key}:{val}")
            if mapped:
                return mapped
    return "culture"


def fetch_poi_for_destination(
    destination_id: str,
    lat: float,
    lng: float,
    radius_m: int = 20000,
) -> list[dict]:
    """Fetch all POI from Overpass for one destination. Retries on 429/504."""
    query = _OVERPASS_QUERY.format(radius=radius_m, lat=lat, lng=lng)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with httpx.Client(timeout=45) as client:
                response = client.post(OVERPASS_URL, data={"data": query})
                if response.status_code == 429:
                    logger.warning(
                        f"Overpass 429 for {destination_id} (attempt {attempt}/{MAX_RETRIES}), "
                        f"sleeping {SLEEP_ON_RATE_LIMIT}s"
                    )
                    time.sleep(SLEEP_ON_RATE_LIMIT)
                    continue
                if response.status_code == 504:
                    logger.warning(f"Overpass 504 for {destination_id} (attempt {attempt}/{MAX_RETRIES}), sleeping 30s")
                    time.sleep(30)
                    continue
                response.raise_for_status()
                elements = response.json().get("elements", [])
                break
        except Exception as e:
            if attempt == MAX_RETRIES:
                logger.warning(f"Overpass fetch failed for {destination_id} after {MAX_RETRIES} attempts: {e}")
                return []
            time.sleep(10 * attempt)
    else:
        return []

    results = []
    for el in elements:
        tags = el.get("tags", {})
        name = tags.get("name") or tags.get("name:en", "")

        if not name:
            # For natural/beach/wellness features: generate descriptive name from tag
            generated = None
            for key in ("natural", "leisure", "amenity", "tourism"):
                val = tags.get(key)
                if val:
                    generated = UNNAMED_FRIENDLY.get(f"{key}:{val}")
                    if generated:
                        # Append elevation for peaks, making them distinguishable
                        if key == "natural" and val == "peak" and tags.get("ele"):
                            generated = f"Peak {tags['ele']}m"
                        break
            if not generated:
                continue
            name = generated

        # way elements return center coords, node elements return lat/lon directly
        center = el.get("center", {})
        el_lat = float(center.get("lat", el.get("lat", lat)))
        el_lng = float(center.get("lon", el.get("lon", lng)))

        results.append(
            {
                "destination_id": destination_id,
                "name": name,
                "lat": el_lat,
                "lng": el_lng,
                "category": _activity_type(tags),
                "external_id": f"osm:{el['id']}",
                "rating": None,
                "popularity_score": _popularity_score(tags),
                "address": tags.get("addr:full") or tags.get("addr:street"),
                "description": tags.get("description"),
                "tags": [
                    f"{k}={v}"
                    for k, v in tags.items()
                    if k in ("tourism", "amenity", "leisure", "natural", "historic", "shop")
                ],
                "opening_hours": tags.get("opening_hours"),
            }
        )
    return results


def iter_poi_overpass(
    limit: int | None = None,
) -> Generator[tuple[str, list[dict]], None, None]:
    """Yield (dest_name, poi_list) per destination, saving state after each.

    The pipeline calls this and upserts immediately — no memory accumulation.
    Skips already-completed destinations so the run is fully resumable.
    """
    from app.database import SessionLocal
    from app.models import Destination

    state = _load_state()
    osm_state = state.setdefault(
        "overpass_osm",
        {"completed": [], "last_run_date": None, "total_completed": 0},
    )
    completed_ids = set(osm_state["completed"])

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

    logger.info(f"OSM Overpass: {len(completed_ids)} already done, {len(pending)} pending")

    for dest in pending:
        poi = fetch_poi_for_destination(str(dest.id), dest.lat, dest.lng, radius_m=dest.radius_m)
        yield dest.name, poi

        osm_state["completed"].append(str(dest.id))
        osm_state["total_completed"] = len(osm_state["completed"])
        osm_state["last_run_date"] = date.today().isoformat()
        _save_state(state)

        time.sleep(SLEEP_BETWEEN_CITIES)
