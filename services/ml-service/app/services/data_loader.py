import math
import uuid

from psycopg2.extras import register_uuid
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.lib.russian_names import resolve_destination_display_name

register_uuid()


def _destination_query(db: Session) -> str:
    exists = db.execute(text("SELECT to_regclass('name_translations')")).scalar()
    if not exists:
        return (
            "SELECT d.id, d.name AS name, d.name AS name_original, NULL AS name_ru, "
            "d.name AS display_name, d.country_code, d.lat, d.lng, d.region, d.subregion "
            "FROM destinations d WHERE d.is_active = true"
        )
    return (
        "SELECT d.id, d.name AS name, d.name AS name_original, "
        "nt.translated_name AS name_ru, nt.translated_name AS display_name, nt.provider AS name_translation_provider, "
        "d.country_code, d.lat, d.lng, d.region, d.subregion "
        "FROM destinations d "
        "LEFT JOIN name_translations nt ON nt.entity_type = 'destination' "
        "AND nt.entity_id = d.id AND nt.locale = 'ru' "
        "WHERE d.is_active = true"
    )


def get_all_destinations(db: Session) -> list[dict]:
    result = db.execute(text(_destination_query(db)))
    destinations = [dict(row._mapping) for row in result]
    for destination in destinations:
        display_name = resolve_destination_display_name(
            str(destination["name_original"]),
            destination.get("name_ru"),
            destination.get("name_translation_provider"),
        )
        destination["name"] = display_name
        destination["name_ru"] = display_name
        destination["display_name"] = display_name
        destination.pop("name_translation_provider", None)
    return destinations


def get_destination_features(
    db: Session, dest_ids: list[uuid.UUID], citizenship_code: str = "RU"
) -> dict[uuid.UUID, dict]:
    if not dest_ids:
        return {}

    id_param = dest_ids  # passed as uuid[] via psycopg2 after register_uuid()

    coord_rows = db.execute(
        text("SELECT id, lat, lng, subregion FROM destinations WHERE id = ANY(:ids)"),
        {"ids": id_param},
    )
    safety_rows = db.execute(
        text("SELECT destination_id, safety_score FROM destination_safety WHERE destination_id = ANY(:ids)"),
        {"ids": id_param},
    )
    costs_rows = db.execute(
        text(
            "SELECT destination_id, cost_index, avg_daily_cost_usd FROM destination_costs "
            "WHERE destination_id = ANY(:ids)"
        ),
        {"ids": id_param},
    )
    season_rows = db.execute(
        text(
            "SELECT destination_id, month, season_score FROM destination_seasonality WHERE destination_id = ANY(:ids)"
        ),
        {"ids": id_param},
    )
    activity_rows = db.execute(
        text(
            "SELECT destination_id, activity_type, score FROM destination_activities WHERE destination_id = ANY(:ids)"
        ),
        {"ids": id_param},
    )
    visa_rows = db.execute(
        text(
            "SELECT destination_id, visa_score FROM visa_rules "
            "WHERE citizenship_code = :cc AND destination_id = ANY(:ids)"
        ),
        {"cc": citizenship_code.upper(), "ids": id_param},
    )
    popularity_rows = db.execute(
        text(
            "SELECT destination_id, month, crowd_index, avg_pageviews "
            "FROM destination_popularity "
            "WHERE destination_id = ANY(:ids)"
        ),
        {"ids": id_param},
    )
    connectivity_rows = db.execute(
        text(
            "SELECT destination_id, connectivity_score, mir_card_accepted "
            "FROM destination_connectivity "
            "WHERE destination_id = ANY(:ids)"
        ),
        {"ids": id_param},
    )
    attribute_rows = db.execute(
        text(
            "SELECT destination_id, is_coastal, has_ski, has_thermal, "
            "landscape, altitude_m "
            "FROM destination_attributes "
            "WHERE destination_id = ANY(:ids)"
        ),
        {"ids": id_param},
    )
    language_rows = db.execute(
        text(
            "SELECT destination_id, russian_speaking_score, english_speaking_score, "
            "script_difficulty "
            "FROM destination_language_accessibility "
            "WHERE destination_id = ANY(:ids)"
        ),
        {"ids": id_param},
    )
    infrastructure_rows = db.execute(
        text(
            "SELECT destination_id, has_metro, healthcare_score, avg_internet_mbps "
            "FROM destination_infrastructure "
            "WHERE destination_id = ANY(:ids)"
        ),
        {"ids": id_param},
    )
    poi_rows = _load_poi_structural_rows(db, id_param)

    features: dict[uuid.UUID, dict] = {d: {} for d in dest_ids}

    def _key(raw) -> uuid.UUID:
        return uuid.UUID(str(raw))

    for row in coord_rows:
        k = _key(row.id)
        if k in features:
            features[k]["lat"] = float(row.lat)
            features[k]["lng"] = float(row.lng)
            features[k]["subregion"] = row.subregion

    for row in safety_rows:
        k = _key(row.destination_id)
        if k in features:
            features[k]["safety_score"] = float(row.safety_score)

    for row in costs_rows:
        k = _key(row.destination_id)
        if k in features:
            features[k]["cost_index"] = float(row.cost_index)
            features[k]["avg_daily_cost_usd"] = (
                float(row.avg_daily_cost_usd) if row.avg_daily_cost_usd is not None else None
            )

    season_map: dict[uuid.UUID, dict[int, float]] = {}
    for row in season_rows:
        k = _key(row.destination_id)
        if k in features:
            season_map.setdefault(k, {})[int(row.month)] = float(row.season_score)
    for k, months in season_map.items():
        features[k]["seasonality"] = months

    activity_map: dict[uuid.UUID, dict[str, float]] = {}
    for row in activity_rows:
        k = _key(row.destination_id)
        if k in features:
            activity_map.setdefault(k, {})[row.activity_type] = float(row.score)
    for k, acts in activity_map.items():
        features[k]["activities"] = acts

    for row in visa_rows:
        k = _key(row.destination_id)
        if k in features:
            features[k]["visa_score"] = float(row.visa_score)

    popularity_map: dict[uuid.UUID, dict[int, float]] = {}
    pageviews_map: dict[uuid.UUID, float] = {}
    for row in popularity_rows:
        k = _key(row.destination_id)
        if k in features:
            popularity_map.setdefault(k, {})[int(row.month)] = float(row.crowd_index)
            if row.avg_pageviews is not None:
                pageviews_map[k] = float(row.avg_pageviews)
    for k, months in popularity_map.items():
        features[k]["crowd_by_month"] = months
    for k, pv in pageviews_map.items():
        features[k]["avg_pageviews"] = pv

    for row in connectivity_rows:
        k = _key(row.destination_id)
        if k in features:
            features[k]["connectivity_score"] = float(row.connectivity_score)
            features[k]["mir_card_accepted"] = bool(row.mir_card_accepted)

    for row in attribute_rows:
        k = _key(row.destination_id)
        if k in features:
            features[k]["is_coastal"] = bool(row.is_coastal)
            features[k]["has_ski"] = bool(row.has_ski)
            features[k]["has_thermal"] = bool(row.has_thermal)
            altitude = row.altitude_m
            landscape = row.landscape or []
            features[k]["has_mountains"] = (altitude is not None and int(altitude) >= 800) or any(
                lbl in ("mountain", "mountains", "highland", "alps")
                for lbl in (landscape if isinstance(landscape, list) else [])
            )

    SCRIPT_DIFFICULTY_MAP = {"easy": 0.0, "medium": 0.5, "hard": 1.0}
    for row in language_rows:
        k = _key(row.destination_id)
        if k in features:
            features[k]["russian_speaking_score"] = float(row.russian_speaking_score)
            features[k]["english_speaking_score"] = float(row.english_speaking_score)
            features[k]["script_difficulty"] = SCRIPT_DIFFICULTY_MAP.get(str(row.script_difficulty).lower(), 0.0)

    for row in infrastructure_rows:
        k = _key(row.destination_id)
        if k in features:
            features[k]["has_metro"] = bool(row.has_metro)
            hc = row.healthcare_score
            internet = row.avg_internet_mbps
            # Derive a composite infrastructure_score from available fields
            hc_norm = float(hc) if hc is not None else 0.5
            internet_norm = min(1.0, float(internet) / 200.0) if internet is not None else 0.5
            features[k]["infrastructure_score"] = round((hc_norm + internet_norm) / 2, 4)

    for row in poi_rows:
        k = _key(row.destination_id)
        if k not in features:
            continue
        total = int(row.total_count or 0)
        std_lat = float(row.std_lat or 0.0)
        std_lng = float(row.std_lng or 0.0)
        spread_km = math.sqrt((std_lat * 111.0) ** 2 + (std_lng * 111.0) ** 2)
        compactness = 1.0 / (1.0 + spread_km / 25.0)
        features[k].update(
            {
                "poi_total_count": float(total),
                "poi_category_diversity": min(1.0, float(row.category_count or 0) / 10.0),
                "poi_top_category_share": float(row.top_cnt or 0) / total if total else 0.0,
                "poi_food_count": float(row.food_count or 0),
                "poi_culture_count": float(row.culture_count or 0),
                "poi_nature_count": float(row.nature_count or 0),
                "poi_transport_count": float(row.transport_count or 0),
                "route_compactness_score": round(float(compactness), 4),
                "avg_poi_rating_or_popularity": float(row.avg_quality or 0.0),
            }
        )

    return features


def _load_poi_structural_rows(db: Session, ids: list[uuid.UUID]):
    if not db.execute(text("SELECT to_regclass('poi')")).scalar():
        return []

    return db.execute(
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
    ).fetchall()
