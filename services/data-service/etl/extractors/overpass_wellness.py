"""Supplementary wellness POI extractor via Overpass API.

v2 expands tag coverage beyond the original set:

Original (v1):
  amenity=public_bath  → hammams (Istanbul, Marrakech), onsens (Japan), thermal baths (Budapest)
  leisure=sauna        → Finnish saunas, Russian banyas (Reykjavik, Helsinki, Tallinn)
  tourism=spa_resort   → dedicated spa resorts (Bali, Chiang Mai, Baden-Baden)
  shop=massage         → Thai massage centres (Chiang Mai), Ayurvedic (Bali)
  amenity=massage      → massage clinics

Added (v2):
  amenity=sauna        → alternative sauna tagging (some mappers use amenity instead of leisure)
  healthcare=spa       → medical spa / balneology centres (Karlovy Vary, Bad Kissingen)
  historic=spa         → heritage spa towns (Bath, UK; Spa, Belgium — sometimes tagged historic)
  building=spa         → spa buildings without specific amenity tag (named only)
  natural=mineral_spring → mineral springs standalone nodes (Kislovodsk, Essentuki, CIS resorts)
  natural=spring[mineral=yes] → generic spring explicitly tagged as mineral
  tourism=spa          → spa tourism object (distinct from spa_resort)

All results go to category='wellness', source='overpass_osm'.
Deduplication is handled by the (source, external_id) unique constraint on upsert.

State versioning:
  v1 used key 'wellness_supplement'  (925 destinations completed as of 2026-04-09)
  v2 uses key 'wellness_supplement_v2' — full re-run of all destinations with expanded tags
"""

import json
import logging
import time
from datetime import date
from pathlib import Path
from typing import Generator

import httpx

logger = logging.getLogger(__name__)

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
STATE_FILE = Path("/app/data/state/poi_progress.json")
SLEEP_BETWEEN_CITIES = 5.0  # polite delay; 1s caused 429s under server load
SLEEP_ON_RATE_LIMIT = 60.0  # 429: full minute backoff
MAX_RETRIES = 3

# v2 expanded query — adds mineral springs and additional spa tags.
# natural=spring with mineral=yes uses a compound Overpass filter.
# building=spa is a structural tag so we accept unnamed nodes/ways (handled by _UNNAMED_FRIENDLY).
_QUERY = """
[out:json][timeout:25];
(
  node["amenity"="public_bath"](around:{radius},{lat},{lng});
  way["amenity"="public_bath"](around:{radius},{lat},{lng});
  node["leisure"="sauna"](around:{radius},{lat},{lng});
  way["leisure"="sauna"](around:{radius},{lat},{lng});
  node["amenity"="sauna"](around:{radius},{lat},{lng});
  way["amenity"="sauna"](around:{radius},{lat},{lng});
  node["tourism"="spa_resort"](around:{radius},{lat},{lng});
  way["tourism"="spa_resort"](around:{radius},{lat},{lng});
  node["tourism"="spa"](around:{radius},{lat},{lng});
  way["tourism"="spa"](around:{radius},{lat},{lng});
  node["shop"="massage"](around:{radius},{lat},{lng});
  node["amenity"="massage"](around:{radius},{lat},{lng});
  node["healthcare"="spa"](around:{radius},{lat},{lng});
  way["healthcare"="spa"](around:{radius},{lat},{lng});
  node["historic"="spa"](around:{radius},{lat},{lng});
  way["historic"="spa"](around:{radius},{lat},{lng});
  node["building"="spa"](around:{radius},{lat},{lng});
  way["building"="spa"](around:{radius},{lat},{lng});
  node["natural"="mineral_spring"](around:{radius},{lat},{lng});
  node["natural"="spring"]["mineral"="yes"](around:{radius},{lat},{lng});
);
out center tags;
"""

# Tags whose key appears as primary classifier — used to build the tags list for the POI record.
_CLASSIFIER_KEYS = frozenset(
    {
        "amenity",
        "leisure",
        "tourism",
        "shop",
        "healthcare",
        "historic",
        "building",
        "natural",
    }
)

# Human-readable fallback names for unnamed objects.
# building=spa, tourism=spa(_resort), healthcare=spa get fallbacks because they represent
# real tourist-facing facilities even without explicit naming.
# Conversely: unnamed public_bath/sauna/massage are residential amenities with no tourist value
# (1500+ residential saunas in Helsinki inflate scores).
_UNNAMED_FRIENDLY: dict[str, str] = {
    "tourism:spa_resort": "Spa Resort",
    "tourism:spa": "Spa",
    "building:spa": "Spa Building",
    "healthcare:spa": "Medical Spa",
    "historic:spa": "Historic Spa",
    "natural:mineral_spring": "Mineral Spring",
    "natural:spring": "Mineral Spring",  # only reached when mineral=yes filter matched
}


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
    if "stars" in tags or "rating" in tags:
        score += 0.05
    return min(round(score, 4), 1.0)


def _resolve_unnamed(tags: dict) -> str | None:
    """Return a generated name for unnamed wellness objects, or None to skip."""
    checks = [
        ("tourism", "spa_resort"),
        ("tourism", "spa"),
        ("building", "spa"),
        ("healthcare", "spa"),
        ("historic", "spa"),
        ("natural", "mineral_spring"),
        ("natural", "spring"),
        ("amenity", "public_bath"),
        ("leisure", "sauna"),
        ("amenity", "sauna"),
        ("shop", "massage"),
        ("amenity", "massage"),
    ]
    for key, val in checks:
        if tags.get(key) == val:
            return _UNNAMED_FRIENDLY.get(f"{key}:{val}")
    return None


def fetch_wellness_for_destination(
    destination_id: str,
    lat: float,
    lng: float,
    radius_m: int = 20000,
) -> list[dict] | None:
    """Return list of POI on success (empty list = no results), None on server error."""
    query = _QUERY.format(radius=radius_m, lat=lat, lng=lng)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with httpx.Client(timeout=60) as client:
                response = client.post(OVERPASS_URL, data={"data": query})
                if response.status_code == 429:
                    wait = SLEEP_ON_RATE_LIMIT * attempt  # 60s, 120s, 180s
                    logger.warning(
                        f"Overpass 429 (attempt {attempt}), sleeping {wait}s"
                    )
                    time.sleep(wait)
                    continue
                if response.status_code == 504:
                    wait = 30 * attempt  # 30s, 60s, 90s
                    logger.warning(
                        f"Overpass 504 (attempt {attempt}), sleeping {wait}s"
                    )
                    time.sleep(wait)
                    continue
                response.raise_for_status()
                elements = response.json().get("elements", [])
                break
        except Exception as e:
            if attempt == MAX_RETRIES:
                logger.warning(f"Wellness fetch failed for {destination_id}: {e}")
                return None  # None = server error, not "genuinely empty"
            time.sleep(10 * attempt)
    else:
        return None  # exhausted retries

    results = []
    seen_ids: set[str] = set()  # guard against duplicate element IDs in response

    for el in elements:
        external_id = f"osm:{el['id']}"
        if external_id in seen_ids:
            continue
        seen_ids.add(external_id)

        tags = el.get("tags", {})
        name = tags.get("name") or tags.get("name:en") or tags.get("name:ru", "")

        if not name:
            name = _resolve_unnamed(tags)
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
                "category": "wellness",
                "source": "overpass_osm",
                "external_id": external_id,
                "rating": None,
                "popularity_score": _popularity_score(tags),
                "address": tags.get("addr:full") or tags.get("addr:street"),
                "description": tags.get("description"),
                "tags": [f"{k}={v}" for k, v in tags.items() if k in _CLASSIFIER_KEYS],
            }
        )

    return results


def iter_wellness_overpass(
    limit: int | None = None,
) -> Generator[tuple[str, list[dict]], None, None]:
    """Yield (dest_name, poi_list) per destination. Resumable via state file.

    Uses state key 'wellness_supplement_v2' (full re-run with expanded tags).
    Legacy key 'wellness_supplement' is preserved in the state file but not used.
    """
    from app.database import SessionLocal
    from app.models import Destination

    state = _load_state()
    ws_state = state.setdefault(
        "wellness_supplement_v2",
        {"completed": [], "last_run_date": None, "total_completed": 0},
    )
    completed_ids = set(ws_state["completed"])

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

    logger.info(
        f"Wellness supplement v2: {len(completed_ids)} done, {len(pending)} pending "
        f"(total active: {len(destinations)})"
    )

    for dest in pending:
        poi = fetch_wellness_for_destination(
            str(dest.id), dest.lat, dest.lng, radius_m=dest.radius_m
        )

        if poi is None:
            # Server error — skip this city for now, retry on next run
            logger.warning(f"Skipping {dest.name} (server error), will retry next run")
            time.sleep(SLEEP_BETWEEN_CITIES)
            continue

        yield dest.name, poi

        # Only mark completed when Overpass actually responded (even if 0 results)
        ws_state["completed"].append(str(dest.id))
        ws_state["total_completed"] = len(ws_state["completed"])
        ws_state["last_run_date"] = date.today().isoformat()
        _save_state(state)

        time.sleep(SLEEP_BETWEEN_CITIES)
