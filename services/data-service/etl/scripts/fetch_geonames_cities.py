"""
Fetch top global cities from GeoNames API and generate Phase 2E CSV.

GeoNames cities1000 dataset: cities with population >= 1000, sorted by population.
Free API: https://www.geonames.org/export/web-services.html

Usage:
    docker compose run --rm data-service python -m etl.scripts.fetch_geonames_cities
    # or with options:
    docker compose run --rm data-service python -m etl.scripts.fetch_geonames_cities \
        --max-cities 300 --output data/raw/global_cities_phase2e.csv

The script:
1. Fetches top cities by population from GeoNames API
2. Filters out cities already in the destinations table
3. Filters out capitals (already covered by REST Countries ETL)
4. Outputs a CSV ready for Phase 2E ETL
"""

import argparse
import logging
import time
from pathlib import Path

import httpx
import pandas as pd

from app.database import SessionLocal

logger = logging.getLogger(__name__)

# GeoNames username — free demo account (limited to 1000 req/hour)
# Register at https://www.geonames.org/login to get a username
GEONAMES_USERNAME = "demo"

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"

# GeoNames feature codes for populated places
FEATURE_CODES = ["PPLC", "PPLA", "PPLA2", "PPLA3", "PPL", "PPLX"]

# Region/subregion mapping by country continentCode
CONTINENT_REGION: dict[str, str] = {
    "EU": "Europe",
    "AS": "Asia",
    "AF": "Africa",
    "NA": "Americas",
    "SA": "Americas",
    "OC": "Oceania",
    "AN": "Antarctica",
}

# GeoNames adminCode1 subregion mapping (simplified)
CONTINENT_SUBREGION_FALLBACK: dict[str, str] = {
    "EU": "Europe",
    "AS": "Asia",
    "AF": "Africa",
    "NA": "Northern America",
    "SA": "South America",
    "OC": "Oceania",
}

# Subregion by country_code (for important cases)
COUNTRY_SUBREGION: dict[str, str] = {
    "RU": "Eastern Europe",
    "TR": "Western Asia",
    "CY": "Western Asia",
    "GE": "Western Asia",
    "AM": "Western Asia",
    "AZ": "Western Asia",
    "KZ": "Central Asia",
    "UZ": "Central Asia",
    "KG": "Central Asia",
    "TJ": "Central Asia",
    "TM": "Central Asia",
    "MN": "Eastern Asia",
    "CN": "Eastern Asia",
    "JP": "Eastern Asia",
    "KR": "Eastern Asia",
    "TW": "Eastern Asia",
    "HK": "Eastern Asia",
    "MO": "Eastern Asia",
    "IN": "Southern Asia",
    "PK": "Southern Asia",
    "BD": "Southern Asia",
    "NP": "Southern Asia",
    "LK": "Southern Asia",
    "MV": "Southern Asia",
    "TH": "South-Eastern Asia",
    "VN": "South-Eastern Asia",
    "ID": "South-Eastern Asia",
    "PH": "South-Eastern Asia",
    "MY": "South-Eastern Asia",
    "SG": "South-Eastern Asia",
    "KH": "South-Eastern Asia",
    "LA": "South-Eastern Asia",
    "MM": "South-Eastern Asia",
    "BN": "South-Eastern Asia",
    "TL": "South-Eastern Asia",
    "SA": "Western Asia",
    "AE": "Western Asia",
    "QA": "Western Asia",
    "KW": "Western Asia",
    "BH": "Western Asia",
    "OM": "Western Asia",
    "YE": "Western Asia",
    "IQ": "Western Asia",
    "IR": "Western Asia",
    "SY": "Western Asia",
    "LB": "Western Asia",
    "JO": "Western Asia",
    "IL": "Western Asia",
    "PS": "Western Asia",
    "AU": "Australia and New Zealand",
    "NZ": "Australia and New Zealand",
    "FJ": "Melanesia",
    "PG": "Melanesia",
    "SB": "Melanesia",
    "VU": "Melanesia",
    "NC": "Melanesia",
    "PF": "Polynesia",
    "WS": "Polynesia",
    "TO": "Polynesia",
    "CK": "Polynesia",
    "US": "Northern America",
    "CA": "Northern America",
    "MX": "Central America",
    "GT": "Central America",
    "BZ": "Central America",
    "HN": "Central America",
    "SV": "Central America",
    "NI": "Central America",
    "CR": "Central America",
    "PA": "Central America",
    "CU": "Caribbean",
    "DO": "Caribbean",
    "HT": "Caribbean",
    "JM": "Caribbean",
    "PR": "Caribbean",
    "TT": "Caribbean",
    "BB": "Caribbean",
    "LC": "Caribbean",
    "VC": "Caribbean",
    "GD": "Caribbean",
    "BS": "Caribbean",
    "TC": "Caribbean",
    "KY": "Caribbean",
    "VI": "Caribbean",
    "BR": "South America",
    "AR": "South America",
    "CL": "South America",
    "PE": "South America",
    "CO": "South America",
    "VE": "South America",
    "EC": "South America",
    "BO": "South America",
    "PY": "South America",
    "UY": "South America",
    "GY": "South America",
    "SR": "South America",
    "EG": "Northern Africa",
    "LY": "Northern Africa",
    "TN": "Northern Africa",
    "DZ": "Northern Africa",
    "MA": "Northern Africa",
    "SD": "Northern Africa",
    "NG": "Western Africa",
    "GH": "Western Africa",
    "SN": "Western Africa",
    "CI": "Western Africa",
    "CM": "Western Africa",
    "ML": "Western Africa",
    "BF": "Western Africa",
    "NE": "Western Africa",
    "TG": "Western Africa",
    "BJ": "Western Africa",
    "GN": "Western Africa",
    "SL": "Western Africa",
    "LR": "Western Africa",
    "GM": "Western Africa",
    "MR": "Western Africa",
    "ZA": "Southern Africa",
    "ZW": "Southern Africa",
    "ZM": "Southern Africa",
    "BW": "Southern Africa",
    "NA": "Southern Africa",
    "LS": "Southern Africa",
    "SZ": "Southern Africa",
    "MZ": "Eastern Africa",
    "TZ": "Eastern Africa",
    "KE": "Eastern Africa",
    "UG": "Eastern Africa",
    "RW": "Eastern Africa",
    "BI": "Eastern Africa",
    "ET": "Eastern Africa",
    "SO": "Eastern Africa",
    "DJ": "Eastern Africa",
    "ER": "Eastern Africa",
    "MG": "Eastern Africa",
    "MU": "Eastern Africa",
    "SC": "Eastern Africa",
    "KM": "Eastern Africa",
    "CD": "Middle Africa",
    "CG": "Middle Africa",
    "GA": "Middle Africa",
    "CF": "Middle Africa",
    "TD": "Middle Africa",
    "AO": "Middle Africa",
}


# Default radius_m by population
def get_radius_m(population: int) -> int:
    if population >= 3_000_000:
        return 25000
    elif population >= 1_000_000:
        return 20000
    elif population >= 200_000:
        return 15000
    elif population >= 50_000:
        return 12000
    else:
        return 10000


def fetch_top_cities_geonames(
    max_rows: int = 1000,
    username: str = GEONAMES_USERNAME,
    min_population: int = 100_000,
) -> list[dict]:
    """Fetch top cities by population from GeoNames API."""
    url = "http://api.geonames.org/searchJSON"
    cities = []
    start_row = 0
    batch_size = 100  # GeoNames max per request

    logger.info(f"Fetching up to {max_rows} cities from GeoNames (min_pop={min_population})...")

    with httpx.Client(timeout=30) as client:
        while start_row < max_rows:
            rows_left = min(batch_size, max_rows - start_row)
            params = {
                "featureClass": "P",
                "featureCode": ["PPLC", "PPLA", "PPLA2", "PPL"],
                "orderby": "population",
                "maxRows": rows_left,
                "startRow": start_row,
                "username": username,
                "style": "MEDIUM",
            }
            try:
                resp = client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                logger.error(f"GeoNames API error at row {start_row}: {e}")
                break

            batch = data.get("geonames", [])
            if not batch:
                break

            # Filter by min population
            batch = [c for c in batch if c.get("population", 0) >= min_population]
            cities.extend(batch)
            logger.info(f"  fetched {len(batch)} cities (total: {len(cities)}, start_row={start_row})")

            if len(data.get("geonames", [])) < rows_left:
                break

            start_row += batch_size
            time.sleep(0.3)  # respect rate limit

    logger.info(f"Total fetched from GeoNames: {len(cities)}")
    return cities


def get_existing_destinations() -> set[tuple[str, str]]:
    """Return set of (name_lower, country_code) already in destinations table."""
    from sqlalchemy import text

    db = SessionLocal()
    try:
        result = db.execute(text("SELECT LOWER(name), country_code FROM destinations"))
        return {(row[0], row[1]) for row in result}
    finally:
        db.close()


def geonames_to_csv_row(city: dict) -> dict | None:
    """Convert GeoNames city dict to CSV row dict."""
    name = city.get("name", "").strip()
    country_code = city.get("countryCode", "").strip().upper()
    lat_str = city.get("lat")
    lng_str = city.get("lng")
    population = city.get("population", 0)
    continent_code = city.get("continentCode", "")

    if not name or not country_code or not lat_str or not lng_str:
        return None

    try:
        lat = float(lat_str)
        lng = float(lng_str)
    except (ValueError, TypeError):
        return None

    region = CONTINENT_REGION.get(continent_code, "Other")
    subregion = COUNTRY_SUBREGION.get(country_code, CONTINENT_SUBREGION_FALLBACK.get(continent_code, "Other"))
    radius_m = get_radius_m(int(population))

    return {
        "name": name,
        "country_code": country_code,
        "lat": round(lat, 7),
        "lng": round(lng, 7),
        "region": region,
        "subregion": subregion,
        "population": int(population),
        "radius_m": radius_m,
    }


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(description="Fetch top global cities from GeoNames")
    parser.add_argument("--max-cities", type=int, default=500, help="Max cities to fetch from API")
    parser.add_argument("--min-population", type=int, default=200_000, help="Min population filter")
    parser.add_argument("--output", type=str, default=str(DATA_DIR / "global_cities_phase2e.csv"))
    parser.add_argument("--username", type=str, default=GEONAMES_USERNAME)
    parser.add_argument("--no-db-filter", action="store_true", help="Skip DB deduplication")
    args = parser.parse_args()

    # Fetch from GeoNames
    raw_cities = fetch_top_cities_geonames(
        max_rows=args.max_cities,
        username=args.username,
        min_population=args.min_population,
    )

    if not raw_cities:
        logger.error("No cities fetched — check GeoNames username or network")
        return

    # Convert to rows
    rows = []
    for city in raw_cities:
        row = geonames_to_csv_row(city)
        if row:
            rows.append(row)

    logger.info(f"Converted {len(rows)} cities to CSV format")

    # Deduplicate against existing DB destinations
    if not args.no_db_filter:
        try:
            existing = get_existing_destinations()
            logger.info(f"Found {len(existing)} existing destinations in DB")
            before = len(rows)
            rows = [r for r in rows if (r["name"].lower(), r["country_code"]) not in existing]
            logger.info(f"Filtered {before - len(rows)} duplicates → {len(rows)} new cities")
        except Exception as e:
            logger.warning(f"Could not filter against DB (proceeding without): {e}")

    # Deduplicate within batch
    seen: set[tuple[str, str]] = set()
    unique_rows = []
    for r in rows:
        key = (r["name"].lower(), r["country_code"])
        if key not in seen:
            seen.add(key)
            unique_rows.append(r)
    rows = unique_rows
    logger.info(f"After dedup within batch: {len(rows)} cities")

    if not rows:
        logger.info("No new cities to add — all already in database")
        return

    df = pd.DataFrame(
        rows,
        columns=[
            "name",
            "country_code",
            "lat",
            "lng",
            "region",
            "subregion",
            "population",
            "radius_m",
        ],
    )
    output_path = Path(args.output)
    df.to_csv(output_path, index=False)
    logger.info(f"Saved {len(df)} cities to {output_path}")

    # Summary stats
    print("\n=== Phase 2E Cities Summary ===")
    print(f"Total new cities: {len(df)}")
    print("\nBy region:")
    print(df.groupby("region").size().to_string())
    print("\nBy country (top 15):")
    print(df.groupby("country_code").size().sort_values(ascending=False).head(15).to_string())


if __name__ == "__main__":
    main()
