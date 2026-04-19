"""Load destination_events from events_seed.csv + optional Wikidata enrichment.

Pipeline:
  1. transform_events()     — load seed CSV (always runs, fast)
  2. enrich_with_wikidata() — fetch ~200 events from Wikidata SPARQL (optional, ~5 min)
  3. merge_events()         — combine seed + wikidata, seed takes priority on duplicates

Ramadan note: month_start/month_end in seed are approximate (shifts ~11 days/year).
The seed uses month 3 (March) as a rough average; for accurate dates use a Hijri
calendar conversion. ML model treats it as a soft signal, not exact scheduling.

Duplicate handling:
  A destination may have the same event name (e.g. "Navruz") across multiple cities —
  this is intentional. Within a single destination, duplicate (destination_id, name)
  combos are deduplicated by keeping the seed entry over Wikidata.

Wikidata matching:
  WikidataEvent has (country_code, city_name). We match:
    1. Try (city_name, country_code) → exact destination
    2. Fall back to capital/largest city in country_code if city_name is None
       or not found — skipped to avoid false positives (too many country-level events
       would all land on the capital).
  Only events with a resolvable city-level match are imported. Country-level events
  without a city match are dropped — prevents polluting capitals with every national holiday.
"""

import csv
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_SEED_PATH = Path(__file__).parents[2] / "data" / "raw" / "events_seed.csv"

_BOOL_MAP = {
    "true": True,
    "false": False,
    "1": True,
    "0": False,
    "yes": True,
    "no": False,
}

_VALID_CATEGORIES = {
    "festival",
    "holiday",
    "religious",
    "carnival",
    "sports",
    "music",
    "food",
    "arts",
}

# Events with these words in the title are likely duplicates of seed entries —
# skip them from Wikidata to avoid noise
_WIKIDATA_SKIP_KEYWORDS = frozenset(
    {
        "navruz",
        "nowruz",
        "novruz",
        "ramadan",
        "eid",
        "diwali",
        "oktoberfest",
        "white nights",
        "venice carnival",
    }
)


def _parse_bool(val: str) -> bool:
    return _BOOL_MAP.get(val.strip().lower(), True)


def _parse_int_or_none(val: str) -> int | None:
    val = val.strip()
    if not val:
        return None
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return None


def _parse_float(val: str, default: float) -> float:
    val = val.strip()
    if not val:
        return default
    try:
        return round(float(val), 4)
    except (ValueError, TypeError):
        return default


def _build_dest_index() -> dict[tuple[str, str], str]:
    """Return {(name_lower, country_code_upper): destination_id_str}."""
    from app.database import SessionLocal
    from app.models import Destination

    db = SessionLocal()
    try:
        return {
            (d.name.strip().lower(), (d.country_code or "").upper()): str(d.id)
            for d in db.query(
                Destination.id, Destination.name, Destination.country_code
            ).all()
        }
    finally:
        db.close()


def transform_events(seed_path: Path = _SEED_PATH) -> list[dict]:
    """Read events_seed.csv, resolve destination UUIDs, return records for upsert."""
    if not seed_path.exists():
        logger.error(f"events_seed.csv not found at {seed_path}")
        return []

    dest_index = _build_dest_index()

    records: list[dict] = []
    seen: set[tuple[str, str]] = set()
    skipped = 0
    unresolved = 0

    with seed_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            dest_name = row.get("destination_name", "").strip()
            country_code = row.get("country_code", "").strip().upper()

            dest_id = dest_index.get((dest_name.lower(), country_code))
            if dest_id is None:
                logger.warning(
                    f"Cannot resolve destination: '{dest_name}' ({country_code}) — skipping"
                )
                unresolved += 1
                continue

            name = row.get("name", "").strip()
            dedup_key = (dest_id, name)
            if dedup_key in seen:
                skipped += 1
                continue
            seen.add(dedup_key)

            category = row.get("category", "festival").strip().lower()
            if category not in _VALID_CATEGORIES:
                logger.warning(
                    f"Unknown category '{category}' for '{name}' — using 'festival'"
                )
                category = "festival"

            month_start = _parse_int_or_none(row.get("month_start", ""))
            month_end = _parse_int_or_none(row.get("month_end", ""))
            if month_start is None or month_end is None:
                logger.warning(f"Missing month for '{name}' at {dest_name} — skipping")
                skipped += 1
                continue

            records.append(
                {
                    "destination_id": dest_id,
                    "name": name,
                    "name_ru": row.get("name_ru", "").strip() or None,
                    "category": category,
                    "month_start": month_start,
                    "month_end": month_end,
                    "day_start": _parse_int_or_none(row.get("day_start", "")),
                    "day_end": _parse_int_or_none(row.get("day_end", "")),
                    "is_annual": _parse_bool(row.get("is_annual", "true")),
                    "crowd_impact": _parse_float(row.get("crowd_impact", ""), 0.5),
                    "price_impact": _parse_float(row.get("price_impact", ""), 0.5),
                    "traveler_relevance": _parse_float(
                        row.get("traveler_relevance", ""), 0.5
                    ),
                    "notes": row.get("notes", "").strip() or None,
                    "data_source": row.get("data_source", "seed_csv").strip(),
                }
            )

    logger.info(
        f"Seed: {len(records)} event records "
        f"(unresolved={unresolved}, duplicates_skipped={skipped})."
    )
    return records


def enrich_with_wikidata(
    seed_records: list[dict],
    country_codes: list[str] | None = None,
) -> list[dict]:
    """Fetch events from Wikidata and merge with seed records.

    Seed records take priority: any (destination_id, name) already in seed is skipped.

    Args:
        seed_records: output of transform_events()
        country_codes: which countries to query. Defaults to all active destinations'
                       country codes, prioritising high-value travel destinations.

    Returns:
        merged list: seed_records + new wikidata events (no duplicates).
    """
    from etl.extractors.wikidata_events import fetch_all_events

    dest_index = _build_dest_index()

    # Existing (destination_id, name_lower) set — seed wins on collision
    existing: set[tuple[str, str]] = {
        (r["destination_id"], r["name"].lower()) for r in seed_records
    }

    if country_codes is None:
        country_codes = _default_country_codes()

    wikidata_events = fetch_all_events(country_codes)

    added = 0
    skipped_no_city = 0
    skipped_dup = 0
    skipped_noise = 0

    wikidata_records: list[dict] = []
    for ev in wikidata_events:
        city_name = ev.get("city_name")
        country_code = ev.get("country_code", "").upper()

        if not city_name:
            skipped_no_city += 1
            continue

        dest_id = dest_index.get((city_name.lower(), country_code))
        if dest_id is None:
            skipped_no_city += 1
            continue

        name_en = ev.get("name_en", "")
        name_lower = name_en.lower()
        if any(kw in name_lower for kw in _WIKIDATA_SKIP_KEYWORDS):
            skipped_noise += 1
            continue

        dedup_key = (dest_id, name_lower)
        if dedup_key in existing:
            skipped_dup += 1
            continue
        existing.add(dedup_key)

        name_ru = ev.get("name_ru")
        wikidata_records.append(
            {
                "destination_id": dest_id,
                "name": name_en[:200],
                "name_ru": name_ru[:200] if name_ru else None,
                "category": ev.get("category", "festival"),
                "month_start": ev["month_start"],
                "month_end": ev["month_end"],
                "day_start": None,
                "day_end": None,
                "is_annual": True,
                "crowd_impact": ev.get("crowd_impact", 0.5),
                "price_impact": ev.get("price_impact", 0.4),
                "traveler_relevance": ev.get("traveler_relevance", 0.6),
                "notes": None,
                "data_source": "wikidata",
            }
        )
        added += 1

    logger.info(
        f"Wikidata enrichment: +{added} new events "
        f"(skipped: no_city={skipped_no_city}, dup={skipped_dup}, noise={skipped_noise})."
    )
    return seed_records + wikidata_records


def _default_country_codes() -> list[str]:
    """Return prioritised list of country codes to query from Wikidata.

    Order: CIS first (highest CIS audience relevance), then top travel destinations.
    Excludes very small/remote territories that are unlikely to have indexed events.
    """
    # Tier 1: CIS — highest relevance for Russian-speaking audience
    cis = ["RU", "KZ", "BY", "UZ", "KG", "TJ", "TM", "AZ", "AM", "GE", "MD", "UA"]
    # Tier 2: key outbound markets for CIS travelers
    tier2 = ["TR", "EG", "TH", "AE", "IN", "CN", "JP", "VN", "ID", "LK", "MV"]
    # Tier 3: Europe
    europe = [
        "DE",
        "IT",
        "ES",
        "FR",
        "GB",
        "CZ",
        "AT",
        "HU",
        "GR",
        "HR",
        "NL",
        "PT",
        "BE",
        "SE",
        "NO",
        "FI",
        "PL",
        "RS",
        "BA",
        "ME",
        "BG",
        "RO",
        "SK",
        "SI",
        "LT",
        "LV",
        "EE",
        "MT",
        "CY",
        "IS",
    ]
    # Tier 4: Americas + Africa + Oceania
    other = [
        "US",
        "MX",
        "BR",
        "AR",
        "PE",
        "CO",
        "MA",
        "TN",
        "KE",
        "TZ",
        "ZA",
        "AU",
        "NZ",
    ]
    return cis + tier2 + europe + other
