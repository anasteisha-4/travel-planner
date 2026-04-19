"""Compute destination_infrastructure from real data sources + rule-based fallbacks.

Data sources (priority order):
  1. Real CSV data (World Bank / Ookla / Speedtest):
     - avg_internet_mbps: data/raw/internet_speeds_country.csv (Speedtest 2024)
     - healthcare_score:  data/raw/healthcare_life_expectancy.csv (WB SP.DYN.LE00.IN)
     - road_quality_score: data/raw/road_quality_wef.csv (WB LP.LPI.INFR.XQ)
     - atm_density_score: data/raw/atm_banking_access.csv (WB FB.ATM.TOTL.P5)
     - cash_economy: data/raw/cash_economy_findex.csv (WB FX.OWN.TOTL.ZS, <50% → cash)
     - has_metro: data/raw/metro_systems.csv (curated ~170 systems) + optional Wikidata

  2. Regional fallbacks (if CSV missing or country not covered)

  3. Rule-based fallback (taxi_app_available)

Post-2022 context:
- Yandex.Taxi available across CIS countries
- Uber suspended in Russia but active in most other markets
"""

import csv
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "raw"

# Countries where metro systems exist (major cities only — Overpass will refine per-city)
_METRO_COUNTRIES = frozenset(
    [
        "RU",
        "UA",
        "BY",
        "KZ",
        "UZ",
        "AZ",
        "GE",
        "AM",  # CIS
        "CN",
        "JP",
        "KR",
        "IN",
        "SG",
        "TH",
        "TR",
        "AE",  # Asia
        "DE",
        "FR",
        "GB",
        "ES",
        "IT",
        "NL",
        "AT",
        "BE",  # EU core
        "SE",
        "NO",
        "DK",
        "FI",
        "PL",
        "CZ",
        "HU",
        "RO",  # EU east/north
        "US",
        "CA",
        "MX",
        "BR",
        "AR",  # Americas
        "EG",
        "ZA",
        "MA",  # Africa
    ]
)

# Countries where Yandex.Taxi operates (CIS + some neighbors)
_YANDEX_TAXI_COUNTRIES = frozenset(
    [
        "RU",
        "BY",
        "KZ",
        "KG",
        "TJ",
        "UZ",
        "TM",
        "AZ",
        "AM",
        "GE",
        "MD",
        "IL",
        "RS",
        "FI",  # Yandex expanded markets
    ]
)

# Countries where taxis/ride-hailing are very limited or not available
_NO_TAXI_APP_COUNTRIES = frozenset(
    [
        "KP",
        "CU",
        "ER",
        "SS",
        "CF",
        "SO",  # isolated/conflict states
    ]
)

# ATM density regional fallback (0–1) — used only if CSV missing
_ATM_DENSITY_BY_REGION = {
    "Europe": 0.85,
    "Northern America": 0.90,
    "Australia and New Zealand": 0.88,
    "Eastern Asia": 0.80,
    "Western Asia": 0.75,
    "South-eastern Asia": 0.65,
    "Central Asia": 0.55,
    "Southern Asia": 0.50,
    "South America": 0.65,
    "Caribbean": 0.60,
    "Central America": 0.55,
    "Northern Africa": 0.60,
    "Sub-Saharan Africa": 0.35,
    "Melanesia": 0.30,
    "Micronesia": 0.25,
    "Polynesia": 0.25,
}
_ATM_DENSITY_DEFAULT = 0.5

# Internet speed regional fallback (Mbps) — used only if CSV missing
_INTERNET_FALLBACK_BY_REGION = {
    "Europe": 80.0,
    "Northern America": 120.0,
    "Australia and New Zealand": 75.0,
    "Eastern Asia": 100.0,
    "Western Asia": 40.0,
    "South-eastern Asia": 35.0,
    "Central Asia": 20.0,
    "Southern Asia": 18.0,
    "South America": 30.0,
    "Caribbean": 20.0,
    "Central America": 18.0,
    "Northern Africa": 15.0,
    "Sub-Saharan Africa": 10.0,
    "Melanesia": 8.0,
    "Micronesia": 6.0,
    "Polynesia": 5.0,
}
_INTERNET_FALLBACK_DEFAULT = 20.0

# Healthcare score regional fallback — used only if CSV missing
_HEALTHCARE_BY_REGION = {
    "Europe": 0.80,
    "Northern America": 0.82,
    "Australia and New Zealand": 0.85,
    "Eastern Asia": 0.78,
    "Western Asia": 0.65,
    "South-eastern Asia": 0.55,
    "Central Asia": 0.55,
    "Southern Asia": 0.45,
    "South America": 0.60,
    "Caribbean": 0.55,
    "Central America": 0.50,
    "Northern Africa": 0.55,
    "Sub-Saharan Africa": 0.35,
    "Melanesia": 0.30,
    "Micronesia": 0.35,
    "Polynesia": 0.40,
}
_HEALTHCARE_DEFAULT = 0.5

# Road quality regional fallback — used only if CSV missing
_ROAD_QUALITY_BY_REGION = {
    "Europe": 0.82,
    "Northern America": 0.80,
    "Australia and New Zealand": 0.85,
    "Eastern Asia": 0.75,
    "Western Asia": 0.65,
    "South-eastern Asia": 0.55,
    "Central Asia": 0.45,
    "Southern Asia": 0.42,
    "South America": 0.52,
    "Caribbean": 0.48,
    "Central America": 0.48,
    "Northern Africa": 0.55,
    "Sub-Saharan Africa": 0.30,
    "Melanesia": 0.25,
    "Micronesia": 0.28,
    "Polynesia": 0.35,
}
_ROAD_QUALITY_DEFAULT = 0.5

# Cash-dominant countries hardcoded fallback (used if Findex CSV missing)
_CASH_ECONOMY_COUNTRIES_FALLBACK = frozenset(
    [
        "MM",
        "KH",
        "LA",
        "PG",
        "BD",
        "NP",
        "AF",
        "YE",
        "LY",
        "SD",
        "TD",
        "ML",
        "NE",
        "BF",
        "GN",
        "SL",
        "LR",
        "TG",
    ]
)


def _load_csv_by_country(csv_path: Path, value_field: str) -> dict[str, float]:
    """Load a CSV with country_code + numeric field → {country_code: float}."""
    if not csv_path.exists():
        logger.warning(f"CSV not found: {csv_path}, using regional fallbacks.")
        return {}
    result: dict[str, float] = {}
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            cc = (row.get("country_code") or "").upper().strip()
            raw = row.get(value_field) or ""
            if cc and raw:
                try:
                    result[cc] = float(raw)
                except ValueError:
                    pass
    logger.info(f"Loaded {len(result)} rows from {csv_path.name} ({value_field})")
    return result


def _load_cash_economy(csv_path: Path) -> set[str]:
    """Load cash_economy_findex.csv → set of cash-dominant country codes."""
    if not csv_path.exists():
        logger.warning(
            f"Cash economy CSV not found: {csv_path}, using hardcoded fallback."
        )
        return set(_CASH_ECONOMY_COUNTRIES_FALLBACK)
    result: set[str] = set()
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            cc = (row.get("country_code") or "").upper().strip()
            is_cash = str(row.get("is_cash_economy") or "").lower()
            if cc and is_cash in ("true", "1", "yes"):
                result.add(cc)
    # Always include known cash-dominant countries not covered by Findex
    result.update(_CASH_ECONOMY_COUNTRIES_FALLBACK)
    logger.info(f"Cash economy countries: {len(result)}")
    return result


def _check_metro_overpass(lat: float, lng: float, radius_m: int) -> bool:
    """Query Overpass for subway routes within destination radius."""
    import time
    import requests

    query = f"""
[out:json][timeout:15];
(
  relation["route"="subway"]({lat - radius_m / 111000:.4f},{lng - radius_m / 111000:.4f},{lat + radius_m / 111000:.4f},{lng + radius_m / 111000:.4f});
);
out count;
"""
    mirrors = [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
    ]
    for mirror in mirrors:
        try:
            resp = requests.post(mirror, data={"data": query}, timeout=20)
            if resp.status_code == 200:
                data = resp.json()
                count = data.get("elements", [{}])[0].get("tags", {}).get("total", 0)
                time.sleep(0.5)
                return int(count) > 0
        except Exception:
            time.sleep(1)
            continue
    return False


def transform_infrastructure(
    use_overpass: bool = False,
    use_wikidata_metro: bool = False,
    skip_existing: bool = False,
) -> list[dict]:
    """Build infrastructure records for all active destinations.

    Args:
        use_overpass: if True, query Overpass API for metro detection (~37 min for 1000+ dests).
                      Rarely needed — metro_systems.csv covers ~170 systems.
        use_wikidata_metro: if True, enrich metro index from Wikidata SPARQL (requires connectivity).
        skip_existing: If True, skip destinations that already have an infrastructure record.

    Returns list[dict] ready for upsert into destination_infrastructure.
    """
    from app.database import SessionLocal
    from app.models import Destination
    from app.models.infrastructure import DestinationInfrastructure

    # Load real data CSVs
    internet_by_cc = _load_csv_by_country(
        DATA_DIR / "internet_speeds_country.csv", "avg_download_mbps"
    )
    healthcare_by_cc = _load_csv_by_country(
        DATA_DIR / "healthcare_life_expectancy.csv", "healthcare_score"
    )
    road_by_cc = _load_csv_by_country(
        DATA_DIR / "road_quality_wef.csv", "road_quality_score"
    )
    atm_by_cc = _load_csv_by_country(
        DATA_DIR / "atm_banking_access.csv", "atm_density_proxy"
    )
    cash_countries = _load_cash_economy(DATA_DIR / "cash_economy_findex.csv")

    # Load metro index: CSV + optional Wikidata enrichment
    from etl.extractors.wikidata_metro import build_metro_index

    metro_index = build_metro_index(use_wikidata=use_wikidata_metro)

    # Load year metadata for data_source_details
    def _load_years(csv_path: Path) -> dict[str, str]:
        if not csv_path.exists():
            return {}
        result: dict[str, str] = {}
        with open(csv_path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                cc = (row.get("country_code") or "").upper().strip()
                year = row.get("data_year") or ""
                if cc and year:
                    result[cc] = year
        return result

    healthcare_years = _load_years(DATA_DIR / "healthcare_life_expectancy.csv")
    road_years = _load_years(DATA_DIR / "road_quality_wef.csv")
    atm_years = _load_years(DATA_DIR / "atm_banking_access.csv")

    db = SessionLocal()
    try:
        destinations = (
            db.query(Destination)
            .filter(Destination.is_active == True)  # noqa: E712
            .all()
        )
        if skip_existing:
            existing = db.query(DestinationInfrastructure.destination_id).all()
            existing_ids = {str(r[0]) for r in existing}
            before = len(destinations)
            destinations = [d for d in destinations if str(d.id) not in existing_ids]
            logger.info(
                f"skip_existing=True: skipping {before - len(destinations)}, {len(destinations)} remaining."
            )
    finally:
        db.close()

    records = []
    stats = {
        "metro_yes": 0,
        "metro_overpass": 0,
        "taxi_yes": 0,
        "cash_economy": 0,
        "internet_real": 0,
        "internet_fallback": 0,
        "healthcare_real": 0,
        "healthcare_fallback": 0,
        "road_real": 0,
        "road_fallback": 0,
        "atm_real": 0,
        "atm_fallback": 0,
    }

    for dest in destinations:
        cc = (dest.country_code or "").upper()
        region = dest.region or ""
        subregion = dest.subregion or ""
        radius_m = int(dest.radius_m) if dest.radius_m else 20000

        # Metro detection: name-based matching against metro_index
        import unicodedata

        def _norm_metro_name(s: str) -> str:
            # Lowercase, strip accents, remove punctuation
            s = (
                unicodedata.normalize("NFKD", s)
                .encode("ascii", "ignore")
                .decode("ascii")
            )
            return s.lower().replace(",", "").replace(".", "").replace("-", " ").strip()

        dest_name_lower = (dest.name or "").lower().strip()
        dest_name_ascii = _norm_metro_name(dest.name or "")
        cc_metros = metro_index.get(cc, set())
        cc_metros_ascii = {_norm_metro_name(m) for m in cc_metros}
        has_metro = dest_name_lower in cc_metros or dest_name_ascii in cc_metros_ascii
        # Also check if any metro entry is a prefix of the destination name
        # (handles "washington" matching "washington, d.c.")
        if not has_metro:
            for metro_ascii in cc_metros_ascii:
                if dest_name_ascii.startswith(
                    metro_ascii + " "
                ) or metro_ascii.startswith(dest_name_ascii + " "):
                    has_metro = True
                    break

        # Fallback: Overpass for countries with metro but destination not in index
        if not has_metro and use_overpass and cc in _METRO_COUNTRIES:
            has_metro = _check_metro_overpass(
                float(dest.lat), float(dest.lng), radius_m
            )
            if has_metro:
                stats["metro_overpass"] += 1

        if has_metro:
            stats["metro_yes"] += 1

        # Taxi app availability
        taxi_app_available = cc not in _NO_TAXI_APP_COUNTRIES
        if taxi_app_available:
            stats["taxi_yes"] += 1

        # Internet speed
        if cc in internet_by_cc:
            avg_internet_mbps = internet_by_cc[cc]
            stats["internet_real"] += 1
        else:
            avg_internet_mbps = _INTERNET_FALLBACK_BY_REGION.get(
                subregion,
                _INTERNET_FALLBACK_BY_REGION.get(region, _INTERNET_FALLBACK_DEFAULT),
            )
            stats["internet_fallback"] += 1

        # Healthcare score
        if cc in healthcare_by_cc:
            healthcare_score = healthcare_by_cc[cc]
            stats["healthcare_real"] += 1
        else:
            healthcare_score = _HEALTHCARE_BY_REGION.get(
                subregion, _HEALTHCARE_BY_REGION.get(region, _HEALTHCARE_DEFAULT)
            )
            stats["healthcare_fallback"] += 1

        # Road quality score
        if cc in road_by_cc:
            road_quality_score = road_by_cc[cc]
            stats["road_real"] += 1
        else:
            road_quality_score = _ROAD_QUALITY_BY_REGION.get(
                subregion, _ROAD_QUALITY_BY_REGION.get(region, _ROAD_QUALITY_DEFAULT)
            )
            stats["road_fallback"] += 1

        # ATM density
        if cc in atm_by_cc:
            atm_density_score = atm_by_cc[cc]
            stats["atm_real"] += 1
        else:
            atm_density_score = _ATM_DENSITY_BY_REGION.get(
                subregion, _ATM_DENSITY_BY_REGION.get(region, _ATM_DENSITY_DEFAULT)
            )
            stats["atm_fallback"] += 1

        # Cash economy
        cash_economy = cc in cash_countries
        if cash_economy:
            stats["cash_economy"] += 1

        # data_source_details
        source_details = {
            "internet_mbps": "speedtest_2024"
            if cc in internet_by_cc
            else "regional_fallback",
            "healthcare": f"wb_life_expectancy_{healthcare_years.get(cc, 'unknown')}"
            if cc in healthcare_by_cc
            else "regional_fallback",
            "road_quality": f"wb_lpi_{road_years.get(cc, 'unknown')}"
            if cc in road_by_cc
            else "regional_fallback",
            "atm_density": f"wb_findex_{atm_years.get(cc, 'unknown')}"
            if cc in atm_by_cc
            else "regional_fallback",
        }

        # data_source summary
        real_count = sum(
            [
                cc in internet_by_cc,
                cc in healthcare_by_cc,
                cc in road_by_cc,
                cc in atm_by_cc,
            ]
        )
        if real_count == 4:
            data_source = "real_data"
        elif real_count > 0:
            data_source = "mixed_real_fallback"
        else:
            data_source = "rule_based"

        records.append(
            {
                "destination_id": str(dest.id),
                "has_metro": has_metro,
                "taxi_app_available": taxi_app_available,
                "road_quality_score": round(road_quality_score, 4),
                "avg_internet_mbps": round(float(avg_internet_mbps), 1),
                "healthcare_score": round(healthcare_score, 4),
                "atm_density_score": round(atm_density_score, 4),
                "cash_economy": cash_economy,
                "data_source": data_source,
                "data_source_details": source_details,
            }
        )

    logger.info(
        f"Transformed {len(records)} infrastructure records. "
        f"has_metro={stats['metro_yes']} (overpass={stats['metro_overpass']}), "
        f"taxi={stats['taxi_yes']}, cash={stats['cash_economy']}. "
        f"Real data: internet={stats['internet_real']}/{len(records)}, "
        f"healthcare={stats['healthcare_real']}/{len(records)}, "
        f"road={stats['road_real']}/{len(records)}, "
        f"atm={stats['atm_real']}/{len(records)}"
    )
    return records
