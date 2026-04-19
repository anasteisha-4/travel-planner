"""Extract UNESCO World Heritage Sites from local CSV.

Source: https://whc.unesco.org/en/list/xml/
Saved to: data/raw/unesco_heritage.csv
Columns: id, name, category, country_iso, lat, lng, year_inscribed

UNESCO categories:
  Cultural  → activity_type = culture
  Natural   → activity_type = nature
  Mixed     → adds both culture + nature entries
"""

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

DATA_FILE = Path("/app/data/raw/unesco_heritage.csv")

# Popularity score for UNESCO sites — top-tier heritage significance
CULTURAL_SCORE = 0.95
NATURAL_SCORE = 0.95
MIXED_SCORE = 0.95

_CATEGORY_MAP = {
    "Cultural": ["culture"],
    "Natural": ["nature"],
    "Mixed": ["culture", "nature"],
}


def extract_unesco(
    destinations: list[dict],
    radius_km: float = 100.0,
) -> list[dict]:
    """Map UNESCO sites to destinations by proximity, return POI records.

    Args:
        destinations: list of dicts with keys: id, name, lat, lng
        radius_km: max distance from destination center to associate a UNESCO site
    """
    if not DATA_FILE.exists():
        logger.error(
            f"UNESCO CSV not found: {DATA_FILE}. Download from https://whc.unesco.org/en/list/xml/"
        )
        return []

    df = pd.read_csv(DATA_FILE, keep_default_na=False)
    df = df.dropna(subset=["lat", "lng"])
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lng"] = pd.to_numeric(df["lng"], errors="coerce")
    df = df.dropna(subset=["lat", "lng"])

    logger.info(f"UNESCO: {len(df)} sites loaded")

    records = []

    for dest in destinations:
        dest_lat = dest["lat"]
        dest_lng = dest["lng"]

        # Approximate distance filter (1 deg lat ≈ 111km)
        lat_delta = radius_km / 111.0
        lng_delta = radius_km / (111.0 * max(0.1, abs(float(f"{dest_lat:.4f}"))))

        nearby = df[
            (abs(df["lat"] - dest_lat) <= lat_delta)
            & (abs(df["lng"] - dest_lng) <= lng_delta)
        ]

        for _, row in nearby.iterrows():
            categories = _CATEGORY_MAP.get(
                str(row.get("category", "Cultural")).strip(), ["culture"]
            )
            for cat in categories:
                records.append(
                    {
                        "destination_id": dest["id"],
                        "name": str(row["name"]),
                        "lat": float(row["lat"]),
                        "lng": float(row["lng"]),
                        "category": cat,
                        "source": "heritage",
                        "external_id": f"unesco:{row['id']}:{cat}",
                        "rating": None,
                        "popularity_score": MIXED_SCORE,
                        "address": None,
                        "description": str(row.get("category", ""))
                        + f" ({row.get('year_inscribed', '')})",
                        "tags": [
                            "heritage=UNESCO",
                            f"category={cat}",
                            f"inscribed={row.get('year_inscribed', '')}",
                        ],
                    }
                )

    logger.info(f"UNESCO: mapped {len(records)} site-destination pairs")
    return records
