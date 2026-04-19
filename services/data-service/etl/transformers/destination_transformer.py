"""Transform REST Countries and cities supplement data into destination records."""

import logging

import pandas as pd

logger = logging.getLogger(__name__)


def transform_countries(raw: list[dict]) -> list[dict]:
    """Transform REST Countries API response into destination dicts."""
    destinations = []
    for country in raw:
        # Prefer capital-specific coordinates if available (more accurate than country centroid)
        capital_info = country.get("capitalInfo", {})
        latlng = capital_info.get("latlng") or country.get("latlng", [])
        if len(latlng) < 2:
            continue

        capital_names = country.get("capital", [])
        capital_name = (
            capital_names[0]
            if capital_names
            else country.get("name", {}).get("common", "")
        )

        if not capital_name:
            continue

        currencies_raw = country.get("currencies", {})
        currencies = {
            code: info.get("name", code) for code, info in currencies_raw.items()
        }

        destinations.append(
            {
                "name": capital_name,
                "country_code": country.get("cca2", ""),
                "lat": latlng[0],
                "lng": latlng[1],
                "region": country.get("region"),
                "subregion": country.get("subregion"),
                "capital": True,
                "population": country.get("population"),
                "currencies": currencies,
                "is_active": True,
            }
        )

    logger.info(f"Transformed {len(destinations)} country capitals.")
    return destinations


def transform_cities(df: pd.DataFrame) -> list[dict]:
    """Transform cities supplement CSV into destination dicts."""
    if df.empty:
        return []

    destinations = []
    for _, row in df.iterrows():
        destinations.append(
            {
                "name": row["name"],
                "country_code": row["country_code"],
                "lat": float(row["lat"]),
                "lng": float(row["lng"]),
                "region": row.get("region"),
                "subregion": row.get("subregion"),
                "capital": False,
                "population": int(row["population"])
                if pd.notna(row.get("population"))
                else None,
                "currencies": {},
                "is_active": True,
                "radius_m": int(row["radius_m"])
                if pd.notna(row.get("radius_m"))
                else 20000,
            }
        )

    logger.info(f"Transformed {len(destinations)} supplementary cities.")
    return destinations
