import uuid

from psycopg2.extras import register_uuid
from sqlalchemy import text
from sqlalchemy.orm import Session

register_uuid()


def get_all_destinations(db: Session) -> list[dict]:
    result = db.execute(
        text("SELECT id, name, country_code, lat, lng, region, subregion FROM destinations WHERE is_active = true")
    )
    return [dict(row._mapping) for row in result]


def get_destination_features(
    db: Session, dest_ids: list[uuid.UUID], citizenship_code: str = "RU"
) -> dict[uuid.UUID, dict]:
    if not dest_ids:
        return {}

    id_param = dest_ids  # passed as uuid[] via psycopg2 after register_uuid()

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

    features: dict[uuid.UUID, dict] = {d: {} for d in dest_ids}

    def _key(raw) -> uuid.UUID:
        return uuid.UUID(str(raw))

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

    return features
