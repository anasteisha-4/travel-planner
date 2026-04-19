"""Compute destination_attributes from multiple sources.

Data sources (in priority order):
  1. Override CSV — manual annotations for top destinations (highest priority)
  2. Open-Meteo Elevation API — altitude_m (batch 100 coords per request, free)
  3. Overpass API — is_coastal (natural=coastline) + has_ski (piste:type=downhill)
  4. Existing DB data:
       - POI table → has_thermal (hot_spring / public_bath / mineral_spring)
       - destination_activities → dest_type / vibe heuristics
       - destination_seasonality → summer_temp_class / winter_temp_class
  5. Destination fields — is_coastal fallback via population/region, landscape inferences

Overpass queries are one per destination (coastline + ski combined).
With 5s sleep and ~440 dests ≈ 37 min total.  Acceptable for a one-time ETL.

Usage:
    from etl.transformers.attributes_transformer import transform_attributes
    records = transform_attributes()   # runs all sources
    records = transform_attributes(use_overpass=False)  # skip slow Overpass (uses heuristics only)
"""

import csv
import logging
import time
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OPEN_METEO_ELEVATION_URL = "https://api.open-meteo.com/v1/elevation"
OVERRIDE_CSV = Path("/app/data/raw/destination_attributes_override.csv")

_OVERPASS_QUERY = """
[out:json][timeout:20];
(
  way["natural"="coastline"](around:{radius},{lat},{lng});
  node["piste:type"="downhill"](around:{radius},{lat},{lng});
  way["piste:type"="downhill"](around:{radius},{lat},{lng});
  way["landuse"="winter_sports"](around:{radius},{lat},{lng});
  area["landuse"="winter_sports"](around:{radius},{lat},{lng});
);
out tags;
"""

_SLEEP_BETWEEN = 10.0
_SLEEP_RATE_LIMIT = 60.0
_MAX_RETRIES = 3
_SLEEP_504_BASE = 60.0  # 60/120/180s backoff on 504

# POI tags that indicate thermal/spa features
_THERMAL_TAGS = frozenset(
    {
        "natural=hot_spring",
        "natural=mineral_spring",
        "amenity=public_bath",
        "natural=spring",
    }
)

# Countries where Russian-speaking tourists get direct access — used for connectivity hints
_COASTAL_COUNTRIES = frozenset(
    {
        "PT",
        "ES",
        "FR",
        "IT",
        "HR",
        "GR",
        "TR",
        "ME",
        "AL",
        "SI",
        "MK",
        "BA",
        "RS",
        "BG",
        "RO",
        "UA",
        "RU",
        "GE",
        "AZ",
        "TM",
        "KZ",
        "AM",
        "IL",
        "LB",
        "JO",
        "EG",
        "LY",
        "TN",
        "DZ",
        "MA",
        "SN",
        "GH",
        "NG",
        "MZ",
        "TZ",
        "KE",
        "SO",
        "MG",
        "ZA",
        "NA",
        "AO",
        "CM",
        "GA",
        "CI",
        "MR",
        "GM",
        "GN",
        "SL",
        "AE",
        "OM",
        "YE",
        "SA",
        "KW",
        "BH",
        "QA",
        "IQ",
        "IR",
        "IN",
        "PK",
        "MM",
        "TH",
        "MY",
        "SG",
        "ID",
        "PH",
        "VN",
        "CN",
        "KR",
        "JP",
        "AU",
        "NZ",
        "FJ",
        "VU",
        "WS",
        "TO",
        "PF",
        "MV",
        "LK",
        "BD",
        "NL",
        "BE",
        "DE",
        "DK",
        "SE",
        "NO",
        "FI",
        "EE",
        "LV",
        "LT",
        "PL",
        "GB",
        "IE",
        "IS",
        "US",
        "MX",
        "CU",
        "JM",
        "HT",
        "DO",
        "PR",
        "TT",
        "BB",
        "LC",
        "VC",
        "GD",
        "AG",
        "KN",
        "DM",
        "BS",
        "BZ",
        "GT",
        "HN",
        "SV",
        "NI",
        "CR",
        "PA",
        "CO",
        "VE",
        "GY",
        "SR",
        "BR",
        "UY",
        "AR",
        "CL",
        "PE",
        "EC",
        "CV",
        "ST",
        "KM",
        "SC",
        "MU",
        "CY",
        "MT",
    }
)

_DESERT_COUNTRIES = frozenset(
    {
        "AE",
        "SA",
        "OM",
        "YE",
        "KW",
        "BH",
        "QA",
        "IQ",
        "JO",
        "IL",
        "EG",
        "LY",
        "TN",
        "DZ",
        "MA",
        "MR",
        "ML",
        "NE",
        "TD",
        "SD",
        "SO",
        "DJ",
        "ER",
        "ET",
    }
)

_STEPPE_COUNTRIES = frozenset({"KZ", "MN", "UZ", "TM", "KG", "TJ"})

# Island/archipelago country codes and overseas territories where ANY city
# is by definition coastal.  Used as the ONLY fallback when Overpass returns None.
#
# Rule: include a code only when the entire territory is an island or archipelago
# so that every city within it is necessarily coastal.  Large continental countries
# (PL, BE, IN, RU, BR …) must NOT be here even if they have a coastline — their
# inland cities would be falsely flagged.  Use Overpass for those.
_ISLAND_COUNTRY_CODES = frozenset(
    {
        # Micronesia / Pacific
        "GU",
        "MP",
        "PW",
        "FM",
        "MH",
        "KI",
        "NR",
        "TV",
        "WS",
        "TO",
        "VU",
        "SB",
        "FJ",
        "PF",
        "NC",
        "WF",
        "CK",
        "NU",
        "TK",
        "AS",
        # Caribbean territories
        "VG",
        "VI",
        "AI",
        "MS",
        "KY",
        "TC",
        "BM",
        "AW",
        "CW",
        "BQ",
        "SX",
        "MF",
        "GP",
        "MQ",
        "BL",
        "PR",
        # Atlantic / Indian Ocean territories
        "YT",
        "RE",
        "PM",
        "FK",
        "SH",
        "AC",
        "TA",
        "IO",  # British Indian Ocean Territory (Diego Garcia atoll)
        # Sovereign island micro-states
        "MC",
        "MV",
        "SG",
        "BH",
        "MT",
        "CY",
        "GI",  # Gibraltar (peninsula, but functionally coastal for all of it)
        "IM",  # Isle of Man
        "JE",
        "GG",  # Jersey, Guernsey
        "AX",  # Åland Islands
        # Caribbean sovereign nations
        "BB",
        "LC",
        "VC",
        "GD",
        "AG",
        "KN",
        "DM",
        "BS",
        "TT",
        "JM",
        # Pacific / Indian Ocean sovereign nations
        "SC",
        "MU",
        "CV",
        "ST",
        "KM",
        # HK and Macau: primarily island/peninsula geography, every district coastal-adjacent
        "HK",
        "MO",
    }
)

_MOUNTAIN_COUNTRIES = frozenset(
    {
        "CH",
        "AT",
        "NO",
        "IS",
        "NP",
        "BT",
        "AF",
        "TJ",
        "KG",
        "AM",
        "GE",
        "AZ",
        "PE",
        "BO",
        "EC",
        "CO",
    }
)

_PILGRIMAGE_CITIES = frozenset(
    {
        ("Mecca", "SA"),
        ("Medina", "SA"),
        ("Jerusalem", "IL"),
        ("Nazareth", "IL"),
        ("Bethlehem", "PS"),
        ("Vatican City", "VA"),
        ("Lourdes", "FR"),
        ("Santiago de Compostela", "ES"),
        ("Varanasi", "IN"),
        ("Amritsar", "IN"),
        ("Bodh Gaya", "IN"),
        ("Shirdi", "IN"),
        ("Tirupati", "IN"),
        ("Puri", "IN"),
        ("Kathmandu", "NP"),
        ("Lhasa", "CN"),
        ("Karbala", "IQ"),
        ("Najaf", "IQ"),
        ("Mashhad", "IR"),
        ("Qom", "IR"),
        ("Kyoto", "JP"),
        ("Nara", "JP"),
    }
)


# ---------------------------------------------------------------------------
# Altitude fetching (Open-Meteo Elevation API, batch 100)
# ---------------------------------------------------------------------------


def _fetch_altitudes_batch(coords: list[tuple[str, float, float]]) -> dict[str, int]:
    """Fetch elevation for up to 100 (dest_id, lat, lng) at once.

    Returns dict: destination_id → altitude_m.
    """
    if not coords:
        return {}

    lats = ",".join(str(round(c[1], 6)) for c in coords)
    lngs = ",".join(str(round(c[2], 6)) for c in coords)

    try:
        with httpx.Client(timeout=30) as client:
            resp = client.get(
                OPEN_METEO_ELEVATION_URL,
                params={"latitude": lats, "longitude": lngs},
            )
            resp.raise_for_status()
            elevations = resp.json().get("elevation", [])
    except Exception as e:
        logger.warning(f"Open-Meteo elevation API failed: {e}")
        return {}

    result = {}
    for i, (dest_id, _, _) in enumerate(coords):
        if i < len(elevations) and elevations[i] is not None:
            result[dest_id] = int(float(elevations[i]))
    return result


def fetch_all_altitudes(destinations: list) -> dict[str, int]:
    """Batch-fetch altitude_m for all destinations (50 per request)."""
    batch_size = 50
    coords = [(str(d.id), d.lat, d.lng) for d in destinations]
    result: dict[str, int] = {}

    for i in range(0, len(coords), batch_size):
        batch = coords[i : i + batch_size]
        partial = _fetch_altitudes_batch(batch)
        result.update(partial)
        if i + batch_size < len(coords):
            time.sleep(0.5)  # gentle rate limit

    logger.info(
        f"Fetched altitudes for {len(result)}/{len(destinations)} destinations."
    )
    return result


# ---------------------------------------------------------------------------
# Overpass: coastline + ski detection per destination
# ---------------------------------------------------------------------------


def _fetch_overpass_attributes(
    dest_id: str, lat: float, lng: float, radius_m: int
) -> dict:
    """Return {'is_coastal': bool, 'has_ski': bool} for one destination."""
    query = _OVERPASS_QUERY.format(radius=radius_m, lat=lat, lng=lng)

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            with httpx.Client(timeout=45) as client:
                resp = client.post(OVERPASS_URL, data={"data": query})
                if resp.status_code == 429:
                    wait = _SLEEP_RATE_LIMIT * attempt
                    logger.warning(
                        f"Overpass 429 (attempt {attempt}), sleeping {wait}s"
                    )
                    time.sleep(wait)
                    continue
                if resp.status_code == 504:
                    wait = _SLEEP_504_BASE * attempt
                    logger.warning(
                        f"Overpass 504 (attempt {attempt}), sleeping {wait}s"
                    )
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                elements = resp.json().get("elements", [])
                break
        except Exception as e:
            if attempt == _MAX_RETRIES:
                logger.warning(f"Overpass failed for {dest_id}: {e}")
                return {"is_coastal": None, "has_ski": None}
            time.sleep(10 * attempt)
    else:
        return {"is_coastal": None, "has_ski": None}

    is_coastal = False
    has_ski = False
    for el in elements:
        tags = el.get("tags", {})
        if tags.get("natural") == "coastline":
            is_coastal = True
        if (
            tags.get("piste:type") == "downhill"
            or tags.get("landuse") == "winter_sports"
        ):
            has_ski = True
        if is_coastal and has_ski:
            break

    return {"is_coastal": is_coastal, "has_ski": has_ski}


# ---------------------------------------------------------------------------
# Override CSV loader
# ---------------------------------------------------------------------------


def _load_override_csv() -> dict[tuple[str, str], dict]:
    """Load destination_attributes_override.csv.

    Key: (name_lower, country_code_upper)
    Value: dict of non-empty fields to override.
    """
    if not OVERRIDE_CSV.exists():
        logger.info("Override CSV not found, skipping.")
        return {}

    overrides: dict[tuple[str, str], dict] = {}
    with OVERRIDE_CSV.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("name", "").strip()
            cc = row.get("country_code", "").strip().upper()
            if not name or not cc:
                continue

            override: dict = {}
            for jsonb_field in ("dest_type", "vibe", "best_for", "landscape"):
                val = row.get(jsonb_field, "").strip()
                if val:
                    override[jsonb_field] = [
                        v.strip() for v in val.split("|") if v.strip()
                    ]

            for str_field in (
                "beach_type",
                "summer_temp_class",
                "winter_temp_class",
                "data_source",
            ):
                val = row.get(str_field, "").strip()
                if val:
                    override[str_field] = val

            for bool_field in ("has_ski", "has_thermal", "is_coastal"):
                val = row.get(bool_field, "").strip().lower()
                if val in ("true", "false"):
                    override[bool_field] = val == "true"

            for int_field in ("altitude_m",):
                val = row.get(int_field, "").strip()
                if val:
                    try:
                        override[int_field] = int(float(val))
                    except ValueError:
                        pass

            if override:
                overrides[(name.lower(), cc)] = override

    logger.info(f"Loaded {len(overrides)} override records from CSV.")
    return overrides


# ---------------------------------------------------------------------------
# Heuristic classifiers
# ---------------------------------------------------------------------------


def _classify_temp(avg_temp: float | None) -> str | None:
    if avg_temp is None:
        return None
    if avg_temp > 28:
        return "hot"
    if avg_temp >= 18:
        return "warm"
    if avg_temp >= 8:
        return "mild"
    return "cold"


def _build_dest_type(
    activity_scores: dict[str, float],
    has_ski: bool,
    has_thermal: bool,
    population: int,
    capital: bool,
    name: str,
    country_code: str,
    altitude_m: int | None,
) -> list[str]:
    types = []
    beach_score = activity_scores.get("beach", 0.0)
    culture_score = activity_scores.get("culture", 0.0)
    nature_score = activity_scores.get("nature", 0.0)

    if beach_score > 0.35:
        types.append("beach")
    if culture_score > 0.55:
        types.append("cultural")
    if has_ski:
        types.append("ski_resort")
    if has_thermal:
        types.append("spa_resort")
    if nature_score > 0.5 and population < 50_000:
        types.append("nature")
    if (name, country_code) in _PILGRIMAGE_CITIES:
        types.append("pilgrimage")

    # Island detection: small population in island nations
    _ISLAND_NATIONS = frozenset(
        {
            "MV",
            "PF",
            "MH",
            "FM",
            "PW",
            "KI",
            "TV",
            "NR",
            "WS",
            "TO",
            "VU",
            "SB",
            "FJ",
            "SG",
            "SC",
            "MU",
            "CV",
            "KM",
            "ST",
            "BB",
            "LC",
            "VC",
            "GD",
            "AG",
            "KN",
            "DM",
            "BS",
            "TT",
            "CY",
            "MT",
            "BH",
            "CW",
            "AW",
            "MQ",
            "GP",
            "RE",
            "YT",
            "PM",
        }
    )
    if country_code in _ISLAND_NATIONS:
        types.append("island")

    # Default classification
    if not types:
        if population > 500_000 or capital:
            types.append("city")
        elif altitude_m is not None and altitude_m > 1000:
            types.append("mountain")
        elif population < 20_000:
            types.append("rural")
        else:
            types.append("city")

    return types


def _build_vibe(
    activity_scores: dict[str, float],
    dest_type: list[str],
    has_thermal: bool,
    country_code: str,
) -> list[str]:
    vibes = []
    beach_s = activity_scores.get("beach", 0.0)
    culture_s = activity_scores.get("culture", 0.0)
    nightlife_s = activity_scores.get("nightlife", 0.0)
    adventure_s = activity_scores.get("adventure", 0.0)
    wellness_s = activity_scores.get("wellness", 0.0)

    if nightlife_s > 0.4:
        vibes.append("party")
    if beach_s > 0.35 or "beach" in dest_type or "island" in dest_type:
        vibes.append("relaxation")
    if adventure_s > 0.4 or "ski_resort" in dest_type:
        vibes.append("adventure")
    if culture_s > 0.5 or "cultural" in dest_type:
        vibes.append("cultural")
    if has_thermal or wellness_s > 0.3:
        vibes.append("relaxation")
    if "pilgrimage" in dest_type:
        vibes.append("spiritual")
    if "luxury" not in vibes and country_code in frozenset(
        {"AE", "QA", "MC", "LI", "CH"}
    ):
        vibes.append("luxury")

    # deduplicate preserving order
    seen: set[str] = set()
    deduped = []
    for v in vibes:
        if v not in seen:
            seen.add(v)
            deduped.append(v)

    if not deduped:
        deduped.append("cultural")
    return deduped


def _build_best_for(
    activity_scores: dict[str, float],
    dest_type: list[str],
    vibe: list[str],
) -> list[str]:
    best: list[str] = []
    family_s = activity_scores.get("family", 0.0)
    nightlife_s = activity_scores.get("nightlife", 0.0)
    culture_s = activity_scores.get("culture", 0.0)

    if family_s > 0.3 or "beach" in dest_type:
        best.append("families")
    if nightlife_s > 0.35 or "party" in vibe:
        best.append("groups")
    if culture_s > 0.4 or "relaxation" in vibe:
        best.append("couples")
    if culture_s > 0.5 or "off_beaten" in vibe:
        best.append("solo")

    seen: set[str] = set()
    deduped = []
    for b in best:
        if b not in seen:
            seen.add(b)
            deduped.append(b)
    if not deduped:
        deduped = ["couples", "solo"]
    return deduped


def _build_landscape(
    is_coastal: bool,
    altitude_m: int | None,
    country_code: str,
    dest_type: list[str],
    activity_scores: dict[str, float],
) -> list[str]:
    landscape = []
    if is_coastal or "beach" in dest_type or "island" in dest_type:
        landscape.append("sea")
    if altitude_m is not None and altitude_m > 800:
        landscape.append("mountains")
    if country_code in _DESERT_COUNTRIES:
        landscape.append("desert")
    elif country_code in _STEPPE_COUNTRIES:
        landscape.append("steppe")
    elif (
        activity_scores.get("nature", 0.0) > 0.4
        and "sea" not in landscape
        and "mountains" not in landscape
    ):
        landscape.append("forest")

    if not landscape:
        landscape.append(
            "urban"
        ) if altitude_m is not None and altitude_m < 200 else landscape.append("forest")

    return landscape


# ---------------------------------------------------------------------------
# Main transformer
# ---------------------------------------------------------------------------


def transform_attributes(
    use_overpass: bool = True, skip_existing: bool = True
) -> list[dict]:
    """Build destination_attributes records for all active destinations.

    Args:
        use_overpass: If True, query Overpass for is_coastal + has_ski.
                      Set to False for fast runs (uses country-code heuristics instead).
        skip_existing: If True, skip destinations that already have a record in
                       destination_attributes. Useful for incremental runs after
                       adding new destinations.

    Returns list[dict] ready for upsert into destination_attributes.
    """
    from app.database import SessionLocal
    from app.models import Destination, DestinationSeasonality
    from app.models.activities import DestinationActivity
    from app.models.attributes import DestinationAttributes
    from app.models.poi import POI

    db = SessionLocal()
    try:
        destinations = (
            db.query(Destination)
            .filter(Destination.is_active == True)  # noqa: E712
            .all()
        )

        if skip_existing:
            # Skip only destinations that were successfully processed (data_source != 'overpass_failed').
            # Destinations that previously failed Overpass are re-queued for retry.
            existing = db.query(
                DestinationAttributes.destination_id,
                DestinationAttributes.data_source,
            ).all()
            skip_ids = {str(r[0]) for r in existing if r[1] != "overpass_failed"}
            before = len(destinations)
            destinations = [d for d in destinations if str(d.id) not in skip_ids]
            retry_count = sum(1 for r in existing if r[1] == "overpass_failed")
            logger.info(
                f"skip_existing=True: skipping {before - len(destinations) - retry_count} "
                f"already processed, retrying {retry_count} overpass_failed, "
                f"{len(destinations)} total to process."
            )

        # Activity scores per destination: {dest_id: {activity_type: score}}
        activity_rows = db.query(
            DestinationActivity.destination_id,
            DestinationActivity.activity_type,
            DestinationActivity.score,
        ).all()
        activity_map: dict[str, dict[str, float]] = {}
        for dest_id, act_type, score in activity_rows:
            key = str(dest_id)
            if key not in activity_map:
                activity_map[key] = {}
            activity_map[key][
                str(act_type.value) if hasattr(act_type, "value") else str(act_type)
            ] = float(score)

        # Seasonality: monthly avg_temp per destination
        seasonality_rows = db.query(
            DestinationSeasonality.destination_id,
            DestinationSeasonality.month,
            DestinationSeasonality.avg_temp_c,
        ).all()
        seasonality_map: dict[str, dict[int, float]] = {}
        for dest_id, month, avg_temp in seasonality_rows:
            key = str(dest_id)
            if key not in seasonality_map:
                seasonality_map[key] = {}
            if avg_temp is not None:
                seasonality_map[key][int(month)] = float(avg_temp)

        # Thermal POI: destinations that have hot_spring / public_bath / mineral_spring
        thermal_dest_ids: set[str] = set()
        thermal_poi = (
            db.query(POI.destination_id, POI.tags)
            .filter(POI.category.in_(["wellness", "nature"]))
            .all()
        )
        for dest_id, tags in thermal_poi:
            if not tags:
                continue
            for tag in tags:
                if any(
                    t in str(tag)
                    for t in (
                        "hot_spring",
                        "mineral_spring",
                        "public_bath",
                        "natural=spring",
                    )
                ):
                    thermal_dest_ids.add(str(dest_id))
                    break
    finally:
        db.close()

    # Altitude batch fetch
    altitudes = fetch_all_altitudes(destinations)

    # Override CSV
    overrides = _load_override_csv()

    records = []

    for i, dest in enumerate(destinations, 1):
        dest_id = str(dest.id)
        act_scores = activity_map.get(dest_id, {})
        temps = seasonality_map.get(dest_id, {})
        altitude_m = altitudes.get(dest_id)

        # Temperature classification
        summer_temps = [temps[m] for m in (6, 7, 8) if m in temps]
        winter_temps = [temps[m] for m in (12, 1, 2) if m in temps]
        summer_avg = sum(summer_temps) / len(summer_temps) if summer_temps else None
        winter_avg = sum(winter_temps) / len(winter_temps) if winter_temps else None
        summer_temp_class = _classify_temp(summer_avg)
        winter_temp_class = _classify_temp(winter_avg)

        # Thermal from POI
        has_thermal_db = dest_id in thermal_dest_ids

        # Coastline / ski from Overpass or heuristic.
        # Priority: Override CSV (applied later) > Overpass result > island heuristic > False
        #
        # _COASTAL_COUNTRIES is intentionally NOT used as a fallback here: it is a
        # country-level list, so continental countries (RU, IN, BR, PL, …) would cause
        # every inland city to be falsely marked coastal.  Only _ISLAND_COUNTRY_CODES
        # (territories where all cities are by definition coastal) is safe as a fallback.
        def _is_coastal_heuristic(cc: str) -> bool:
            """True only for island/micro-territory country codes."""
            return cc in _ISLAND_COUNTRY_CODES

        overpass_failed = False
        if use_overpass:
            ov = _fetch_overpass_attributes(dest_id, dest.lat, dest.lng, dest.radius_m)
            if ov["is_coastal"] is not None:
                is_coastal = ov["is_coastal"]
            else:
                # Overpass returned None (timeout/error) — island heuristic only
                is_coastal = _is_coastal_heuristic(dest.country_code)
                overpass_failed = True
            has_ski = ov["has_ski"] if ov["has_ski"] is not None else False
            time.sleep(_SLEEP_BETWEEN)
        else:
            is_coastal = _is_coastal_heuristic(dest.country_code)
            has_ski = False  # conservative default without Overpass

        has_thermal = has_thermal_db

        # Heuristic classification
        dest_type = _build_dest_type(
            act_scores,
            has_ski,
            has_thermal,
            int(dest.population) if dest.population else 0,
            bool(dest.capital),
            dest.name,
            dest.country_code,
            altitude_m,
        )
        vibe = _build_vibe(act_scores, dest_type, has_thermal, dest.country_code)
        best_for = _build_best_for(act_scores, dest_type, vibe)
        landscape = _build_landscape(
            is_coastal, altitude_m, dest.country_code, dest_type, act_scores
        )

        beach_type: str | None = None
        if "beach" in dest_type or "island" in dest_type:
            beach_type = "sea"

        record: dict = {
            "destination_id": dest_id,
            "dest_type": dest_type,
            "vibe": vibe,
            "best_for": best_for,
            "landscape": landscape,
            "beach_type": beach_type,
            "has_ski": has_ski,
            "has_thermal": has_thermal,
            "is_coastal": is_coastal,
            "altitude_m": altitude_m,
            "summer_temp_class": summer_temp_class,
            "winter_temp_class": winter_temp_class,
            "data_source": "overpass_failed" if overpass_failed else "osm_inferred",
        }

        # Apply override CSV — always takes priority, including over overpass_failed
        override_key = (dest.name.lower(), dest.country_code.upper())
        override = overrides.get(override_key)
        if override:
            record.update(override)
            if "data_source" not in override:
                record["data_source"] = "manual"

        records.append(record)
        if i % 20 == 0 or i == len(destinations):
            logger.info(f"Parsed {i}/{len(destinations)} destinations for attributes.")

    logger.info(f"Built {len(records)} destination_attributes records.")
    return records
