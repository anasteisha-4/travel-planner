"""Destination feature matrix builder.

Assembles a denormalized 40-dimension feature vector per destination from all
ML tables in the data-service schema. Used both for content scoring (serving)
and LightGBM training (offline).

Feature dimensions (48 total):
  Activities (10): beach, culture, active, nature, food, shopping, nightlife,
                   family, romance, business
  Safety (1):      safety_score
  Cost (3):        cost_index, avg_daily_cost_usd, cost_tier
  Seasonality (12):season_scores[1..12]
  Connectivity (2):connectivity_score, mir_card_accepted
  Language (3):    russian_speaking_score, english_speaking_score, script_difficulty
  Attributes (4):  is_coastal, has_ski, has_thermal, has_mountains
  Popularity (2):  crowd_index_avg, log_avg_pageviews
  Infrastructure (2): infrastructure_score, has_metro
  POI structure (9): total/category counts, diversity, compactness, quality
"""

import logging
import math
import uuid
from datetime import UTC, datetime
from typing import Any

import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

ACTIVITY_TYPES = [
    "beach",
    "culture",
    "active",
    "nature",
    "food",
    "shopping",
    "nightlife",
    "family",
    "romance",
    "business",
]

SCRIPT_DIFFICULTY_MAP = {"easy": 0.0, "medium": 0.5, "hard": 1.0}

POI_STRUCTURAL_FEATURES = [
    "poi_total_count",
    "poi_category_diversity",
    "poi_top_category_share",
    "poi_food_count",
    "poi_culture_count",
    "poi_nature_count",
    "poi_transport_count",
    "route_compactness_score",
    "avg_poi_rating_or_popularity",
]


def build_destination_feature_matrix(db: Session) -> pd.DataFrame:
    """Build full destination × feature matrix from DB. Returns DataFrame."""
    dests = _load_destinations(db)
    if not dests:
        raise RuntimeError("No active destinations found")

    dest_ids = [d["id"] for d in dests]

    safety = _load_safety(db, dest_ids)
    costs = _load_costs(db, dest_ids)
    seasonality = _load_seasonality(db, dest_ids)
    activities = _load_activities(db, dest_ids)
    visa_ru = _load_visa_ru(db, dest_ids)
    popularity = _load_popularity(db, dest_ids)
    connectivity = _load_connectivity(db, dest_ids)
    attributes = _load_attributes(db, dest_ids)
    language = _load_language(db, dest_ids)
    infrastructure = _load_infrastructure(db, dest_ids)
    poi_structural = _load_poi_structural(db, dest_ids)

    rows = []
    for d in dests:
        did = d["id"]
        row = _build_row(
            dest=d,
            safety=safety.get(did, {}),
            costs=costs.get(did, {}),
            seasonality=seasonality.get(did, {}),
            activities=activities.get(did, {}),
            visa_ru=visa_ru.get(did, 0.5),
            popularity=popularity.get(did, {}),
            connectivity=connectivity.get(did, {}),
            attributes=attributes.get(did, {}),
            language=language.get(did, {}),
            infrastructure=infrastructure.get(did, {}),
            poi_structural=poi_structural.get(did, {}),
        )
        rows.append(row)

    df = pd.DataFrame(rows)
    logger.info("Feature matrix built: %d destinations × %d features", len(df), len(df.columns))
    return df


def get_feature_columns() -> list[str]:
    """Return ordered list of feature column names (excludes destination_id, name, etc.)."""
    cols = []
    for act in ACTIVITY_TYPES:
        cols.append(f"act_{act}")
    cols += [
        "safety_score",
        "cost_index",
        "avg_daily_cost_usd",
        "cost_tier",
    ]
    for m in range(1, 13):
        cols.append(f"season_{m:02d}")
    cols += [
        "connectivity_score",
        "mir_card_accepted",
        "russian_speaking_score",
        "english_speaking_score",
        "script_difficulty",
        "is_coastal",
        "has_ski",
        "has_thermal",
        "has_mountains",
        "crowd_index_avg",
        "log_avg_pageviews",
        "infrastructure_score",
        "has_metro",
    ]
    cols += POI_STRUCTURAL_FEATURES
    return cols


def _build_row(
    dest: dict,
    safety: dict,
    costs: dict,
    seasonality: dict,
    activities: dict,
    visa_ru: float,
    popularity: dict,
    connectivity: dict,
    attributes: dict,
    language: dict,
    infrastructure: dict,
    poi_structural: dict,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "destination_id": str(dest["id"]),
        "name": dest.get("name", ""),
        "country_code": dest.get("country_code", ""),
        "region": dest.get("region", ""),
        "subregion": dest.get("subregion", ""),
        "lat": float(dest["lat"]) if dest.get("lat") is not None else 0.0,
        "lng": float(dest["lng"]) if dest.get("lng") is not None else 0.0,
    }

    for act in ACTIVITY_TYPES:
        row[f"act_{act}"] = float(activities.get(act, 0.0))

    row["safety_score"] = float(safety.get("safety_score", 0.5))

    cost_index = float(costs.get("cost_index", 0.5))
    avg_daily = float(costs.get("avg_daily_cost_usd", 80.0))
    row["cost_index"] = cost_index
    row["avg_daily_cost_usd"] = avg_daily
    row["cost_tier"] = _cost_tier(avg_daily)

    for m in range(1, 13):
        row[f"season_{m:02d}"] = float(seasonality.get(m, 0.5))

    row["connectivity_score"] = float(connectivity.get("connectivity_score", 0.3))
    row["mir_card_accepted"] = 1.0 if connectivity.get("mir_card_accepted") else 0.0

    row["russian_speaking_score"] = float(language.get("russian_speaking_score", 0.1))
    row["english_speaking_score"] = float(language.get("english_speaking_score", 0.5))
    row["script_difficulty"] = SCRIPT_DIFFICULTY_MAP.get(str(language.get("script_difficulty", "easy")).lower(), 0.0)

    row["is_coastal"] = 1.0 if attributes.get("is_coastal") else 0.0
    row["has_ski"] = 1.0 if attributes.get("has_ski") else 0.0
    row["has_thermal"] = 1.0 if attributes.get("has_thermal") else 0.0
    row["has_mountains"] = 1.0 if attributes.get("has_mountains") else 0.0

    crowd_months = popularity.get("crowd_by_month", {})
    crowd_avg = sum(crowd_months.values()) / len(crowd_months) if crowd_months else 0.5
    avg_pv = float(popularity.get("avg_pageviews", 1.0))
    row["crowd_index_avg"] = float(crowd_avg)
    row["log_avg_pageviews"] = float(math.log1p(avg_pv))

    hc = float(infrastructure.get("healthcare_score", 0.5))
    internet = float(infrastructure.get("avg_internet_mbps", 50.0))
    row["infrastructure_score"] = round((hc + min(1.0, internet / 200.0)) / 2, 4)
    row["has_metro"] = 1.0 if infrastructure.get("has_metro") else 0.0

    row["visa_score_ru"] = visa_ru

    for col in POI_STRUCTURAL_FEATURES:
        default = 0.0 if col != "route_compactness_score" else 0.5
        row[col] = float(poi_structural.get(col, default))

    return row


def _cost_tier(avg_daily_usd: float) -> int:
    if avg_daily_usd < 40:
        return 1
    if avg_daily_usd < 80:
        return 2
    if avg_daily_usd < 150:
        return 3
    return 4


def _load_destinations(db: Session) -> list[dict]:
    rows = db.execute(
        text("SELECT id, name, country_code, lat, lng, region, subregion FROM destinations WHERE is_active = true")
    )
    return [dict(r._mapping) for r in rows]


def _load_safety(db: Session, ids: list) -> dict:
    rows = db.execute(
        text("SELECT destination_id, safety_score FROM destination_safety WHERE destination_id = ANY(:ids)"),
        {"ids": ids},
    )
    return {r.destination_id: {"safety_score": float(r.safety_score)} for r in rows}


def _load_costs(db: Session, ids: list) -> dict:
    rows = db.execute(
        text(
            "SELECT destination_id, cost_index, avg_daily_cost_usd "
            "FROM destination_costs WHERE destination_id = ANY(:ids)"
        ),
        {"ids": ids},
    )
    result = {}
    for r in rows:
        result[r.destination_id] = {
            "cost_index": float(r.cost_index),
            "avg_daily_cost_usd": float(r.avg_daily_cost_usd) if r.avg_daily_cost_usd else 80.0,
        }
    return result


def _load_seasonality(db: Session, ids: list) -> dict:
    rows = db.execute(
        text(
            "SELECT destination_id, month, season_score FROM destination_seasonality WHERE destination_id = ANY(:ids)"
        ),
        {"ids": ids},
    )
    result: dict = {}
    for r in rows:
        result.setdefault(r.destination_id, {})[int(r.month)] = float(r.season_score)
    return result


def _load_activities(db: Session, ids: list) -> dict:
    rows = db.execute(
        text(
            "SELECT destination_id, activity_type, score FROM destination_activities WHERE destination_id = ANY(:ids)"
        ),
        {"ids": ids},
    )
    result: dict = {}
    for r in rows:
        result.setdefault(r.destination_id, {})[r.activity_type] = float(r.score)
    return result


def _load_visa_ru(db: Session, ids: list) -> dict:
    rows = db.execute(
        text(
            "SELECT destination_id, visa_score FROM visa_rules "
            "WHERE citizenship_code = 'RU' AND destination_id = ANY(:ids)"
        ),
        {"ids": ids},
    )
    return {r.destination_id: float(r.visa_score) for r in rows}


def _load_popularity(db: Session, ids: list) -> dict:
    rows = db.execute(
        text(
            "SELECT destination_id, month, crowd_index, avg_pageviews "
            "FROM destination_popularity WHERE destination_id = ANY(:ids)"
        ),
        {"ids": ids},
    )
    result: dict = {}
    for r in rows:
        d = result.setdefault(r.destination_id, {"crowd_by_month": {}, "avg_pageviews": 0.0})
        d["crowd_by_month"][int(r.month)] = float(r.crowd_index)
        if r.avg_pageviews:
            d["avg_pageviews"] = float(r.avg_pageviews)
    return result


def _load_connectivity(db: Session, ids: list) -> dict:
    rows = db.execute(
        text(
            "SELECT destination_id, connectivity_score, mir_card_accepted "
            "FROM destination_connectivity WHERE destination_id = ANY(:ids)"
        ),
        {"ids": ids},
    )
    return {
        r.destination_id: {
            "connectivity_score": float(r.connectivity_score),
            "mir_card_accepted": bool(r.mir_card_accepted),
        }
        for r in rows
    }


def _load_attributes(db: Session, ids: list) -> dict:
    rows = db.execute(
        text(
            "SELECT destination_id, is_coastal, has_ski, has_thermal, altitude_m, landscape "
            "FROM destination_attributes WHERE destination_id = ANY(:ids)"
        ),
        {"ids": ids},
    )
    result = {}
    for r in rows:
        landscape = r.landscape or []
        if not isinstance(landscape, list):
            landscape = []
        has_mountains = (r.altitude_m is not None and int(r.altitude_m) >= 800) or any(
            lbl in ("mountain", "mountains", "highland", "alps") for lbl in landscape
        )
        result[r.destination_id] = {
            "is_coastal": bool(r.is_coastal),
            "has_ski": bool(r.has_ski),
            "has_thermal": bool(r.has_thermal),
            "has_mountains": has_mountains,
        }
    return result


def _load_language(db: Session, ids: list) -> dict:
    rows = db.execute(
        text(
            "SELECT destination_id, russian_speaking_score, english_speaking_score, script_difficulty "
            "FROM destination_language_accessibility WHERE destination_id = ANY(:ids)"
        ),
        {"ids": ids},
    )
    return {
        r.destination_id: {
            "russian_speaking_score": float(r.russian_speaking_score),
            "english_speaking_score": float(r.english_speaking_score),
            "script_difficulty": str(r.script_difficulty),
        }
        for r in rows
    }


def _load_infrastructure(db: Session, ids: list) -> dict:
    rows = db.execute(
        text(
            "SELECT destination_id, has_metro, avg_internet_mbps, healthcare_score "
            "FROM destination_infrastructure WHERE destination_id = ANY(:ids)"
        ),
        {"ids": ids},
    )
    return {
        r.destination_id: {
            "has_metro": bool(r.has_metro),
            "avg_internet_mbps": float(r.avg_internet_mbps) if r.avg_internet_mbps else 50.0,
            "healthcare_score": float(r.healthcare_score) if r.healthcare_score else 0.5,
        }
        for r in rows
    }


def _load_poi_structural(db: Session, ids: list) -> dict:
    """Load POI-derived structural destination features.

    The features are aggregate-only, so the query stays bounded even for the
    2.1M-row POI table. Test DBs that do not create the data-service POI table
    receive neutral defaults through the caller.
    """
    if not db.execute(text("SELECT to_regclass('poi')")).scalar():
        return {}

    rows = db.execute(
        text(
            """
            WITH base AS (
                SELECT
                    destination_id,
                    lower(category) AS category,
                    lat,
                    lng,
                    COALESCE(rating, popularity_score) AS quality
                FROM poi
                WHERE destination_id = ANY(:ids)
            ),
            category_counts AS (
                SELECT destination_id, category, COUNT(*) AS cnt
                FROM base
                GROUP BY destination_id, category
            ),
            top_category AS (
                SELECT destination_id, MAX(cnt) AS top_cnt
                FROM category_counts
                GROUP BY destination_id
            ),
            stats AS (
                SELECT
                    destination_id,
                    COUNT(*) AS total_count,
                    COUNT(DISTINCT category) AS category_count,
                    SUM(CASE WHEN category LIKE ANY(ARRAY['%food%', '%restaurant%', '%cafe%', '%bar%']) THEN 1 ELSE 0 END) AS food_count,
                    SUM(CASE WHEN category LIKE ANY(ARRAY['%culture%', '%museum%', '%art%', '%historic%', '%heritage%']) THEN 1 ELSE 0 END) AS culture_count,
                    SUM(CASE WHEN category LIKE ANY(ARRAY['%nature%', '%park%', '%beach%', '%mountain%', '%viewpoint%']) THEN 1 ELSE 0 END) AS nature_count,
                    SUM(CASE WHEN category LIKE ANY(ARRAY['%transport%', '%airport%', '%station%', '%metro%', '%bus%']) THEN 1 ELSE 0 END) AS transport_count,
                    AVG(quality) AS avg_quality,
                    STDDEV_POP(lat) AS std_lat,
                    STDDEV_POP(lng) AS std_lng
                FROM base
                GROUP BY destination_id
            )
            SELECT
                stats.destination_id,
                stats.total_count,
                stats.category_count,
                top_category.top_cnt,
                stats.food_count,
                stats.culture_count,
                stats.nature_count,
                stats.transport_count,
                stats.avg_quality,
                stats.std_lat,
                stats.std_lng
            FROM stats
            JOIN top_category ON top_category.destination_id = stats.destination_id
            """
        ),
        {"ids": ids},
    )

    result = {}
    for r in rows:
        total = int(r.total_count or 0)
        std_lat = float(r.std_lat or 0.0)
        std_lng = float(r.std_lng or 0.0)
        spread_km = math.sqrt((std_lat * 111.0) ** 2 + (std_lng * 111.0) ** 2)
        compactness = 1.0 / (1.0 + spread_km / 25.0)
        result[r.destination_id] = {
            "poi_total_count": float(total),
            "poi_category_diversity": min(1.0, float(r.category_count or 0) / 10.0),
            "poi_top_category_share": float(r.top_cnt or 0) / total if total else 0.0,
            "poi_food_count": float(r.food_count or 0),
            "poi_culture_count": float(r.culture_count or 0),
            "poi_nature_count": float(r.nature_count or 0),
            "poi_transport_count": float(r.transport_count or 0),
            "route_compactness_score": round(float(compactness), 4),
            "avg_poi_rating_or_popularity": float(r.avg_quality or 0.0),
        }
    return result


def save_feature_snapshot(
    db: Session,
    feature_version: int,
    rows_count: int,
    purpose: str,
    storage_path: str | None = None,
) -> str:
    """Record snapshot metadata in feature_snapshots table. Returns snapshot id."""
    snap_id = str(uuid.uuid4())
    db.execute(
        text(
            "INSERT INTO feature_snapshots "
            "(id, snapshot_type, feature_version, created_at, rows_count, purpose, storage_path) "
            "VALUES (:id, 'destination', :ver, :now, :rows, :purpose, :path)"
        ),
        {
            "id": snap_id,
            "ver": feature_version,
            "now": datetime.now(UTC),
            "rows": rows_count,
            "purpose": purpose,
            "path": storage_path,
        },
    )
    db.commit()
    return snap_id
