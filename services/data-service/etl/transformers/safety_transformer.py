"""Transform GPI scores into safety_score 0-1 per destination."""

import logging
import os

import pandas as pd

logger = logging.getLogger(__name__)

GPI_MIN = 1.0
GPI_MAX = 5.0
GPI_RANGE = GPI_MAX - GPI_MIN

_OVERRIDES_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "raw", "safety_city_overrides.csv")


def _load_city_overrides() -> dict[tuple[str, str], float]:
    """Load city-level safety adjustments from CSV.

    Returns {(name_lower, country_code_upper): adjustment_float}.
    """
    path = os.path.normpath(_OVERRIDES_PATH)
    if not os.path.exists(path):
        logger.warning(f"City overrides file not found: {path}")
        return {}

    df = pd.read_csv(path, keep_default_na=False)
    result: dict[tuple[str, str], float] = {}
    for _, row in df.iterrows():
        name = str(row.get("name", "")).strip().lower()
        cc = str(row.get("country_code", "")).strip().upper()
        raw_adj = str(row.get("adjustment", "0")).strip().replace("+", "")
        try:
            adjustment = float(raw_adj)
        except ValueError:
            logger.warning(f"Invalid adjustment value for {name}/{cc}: {raw_adj!r}")
            continue
        if name and cc:
            result[(name, cc)] = adjustment
    logger.info(f"Loaded {len(result)} city safety overrides.")
    return result


def _get_country_destinations(
    skip_existing: bool = False,
) -> dict[str, list[tuple[str, str]]]:
    """Return {country_code: [(destination_id, destination_name), ...]}.

    Args:
        skip_existing: If True, exclude destinations that already have a safety record.
    """
    from app.database import SessionLocal
    from app.models import Destination
    from app.models.safety import DestinationSafety

    db = SessionLocal()
    try:
        destinations = db.query(Destination).all()
        if skip_existing:
            existing = db.query(DestinationSafety.destination_id).all()
            existing_ids = {str(r[0]) for r in existing}
            destinations = [d for d in destinations if str(d.id) not in existing_ids]
            logger.info(f"skip_existing=True: {len(existing_ids)} already covered, {len(destinations)} remaining.")
        result: dict[str, list[tuple[str, str]]] = {}
        for d in destinations:
            if d.country_code:
                result.setdefault(d.country_code.upper(), []).append((str(d.id), d.name))
        return result
    finally:
        db.close()


DEFAULT_SAFETY_SCORE = 0.5  # used for destinations not covered by GPI


def transform_safety(df: pd.DataFrame, skip_existing: bool = False) -> list[dict]:
    """Map GPI scores to safety_score and fan out to all destinations in that country.

    City-level overrides from safety_city_overrides.csv are applied on top of the
    country GPI score. The adjustment is additive and clamped to [0, 1].

    Destinations whose country is not in GPI receive a neutral default score of 0.5
    so they are not penalised in recommendations simply due to data absence.
    """
    country_map = _get_country_destinations(skip_existing=skip_existing)
    city_overrides = _load_city_overrides()
    records = []
    covered_countries: set[str] = set()

    for _, row in df.iterrows():
        country_code = str(row.get("country_iso2", "")).upper().strip()
        gpi_score = float(row.get("gpi_score", 0) or 0)
        gpi_rank = int(row.get("gpi_rank")) if pd.notna(row.get("gpi_rank")) else None
        gpi_year = int(row.get("year")) if pd.notna(row.get("year")) else None

        if not country_code or gpi_score <= 0:
            continue

        base_safety_score = round(1.0 - (gpi_score - GPI_MIN) / GPI_RANGE, 4)
        base_safety_score = max(0.0, min(1.0, base_safety_score))

        dest_list = country_map.get(country_code, [])
        for dest_id, dest_name in dest_list:
            override_key = (dest_name.lower(), country_code)
            adjustment = city_overrides.get(override_key)

            if adjustment is not None:
                final_score = round(max(0.0, min(1.0, base_safety_score + adjustment)), 4)
                data_source = "gpi_city_adjusted"
            else:
                final_score = base_safety_score
                data_source = "gpi_country"

            records.append(
                {
                    "destination_id": dest_id,
                    "safety_score": final_score,
                    "gpi_score": gpi_score,
                    "gpi_rank": gpi_rank,
                    "gpi_year": gpi_year,
                    "safety_data_source": data_source,
                    "city_adjustment_factor": adjustment,
                }
            )
        if dest_list:
            covered_countries.add(country_code)

    # Insert neutral default for every destination whose country has no GPI entry
    default_count = 0
    for country_code, dest_list in country_map.items():
        if country_code in covered_countries:
            continue
        for dest_id, _dest_name in dest_list:
            records.append(
                {
                    "destination_id": dest_id,
                    "safety_score": DEFAULT_SAFETY_SCORE,
                    "gpi_score": None,
                    "gpi_rank": None,
                    "gpi_year": None,
                    "safety_data_source": "default",
                    "city_adjustment_factor": None,
                }
            )
            default_count += 1

    adjusted_count = sum(1 for r in records if r["safety_data_source"] == "gpi_city_adjusted")
    logger.info(
        f"Transformed {len(records)} safety records "
        f"({len(records) - default_count} real GPI, {default_count} defaults, "
        f"{adjusted_count} city-adjusted)."
    )
    return records
