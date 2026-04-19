"""Transform raw POI data: deduplicate, normalize popularity_score."""

import logging

logger = logging.getLogger(__name__)

MAX_OPENTRIPMAP_RATING = 10.0


def transform_poi(raw: list[dict], source: str) -> list[dict]:
    """Normalize POI records from a given source."""
    max_rating = MAX_OPENTRIPMAP_RATING
    seen_external_ids = set()
    records = []

    for item in raw:
        external_id = str(item.get("external_id", "")).strip()
        name = str(item.get("name", "")).strip()

        if not external_id or not name:
            continue

        # Deduplicate within this batch
        key = (source, external_id)
        if key in seen_external_ids:
            continue
        seen_external_ids.add(key)

        rating = item.get("rating")
        precomputed_score = item.get("popularity_score")
        if rating is not None:
            try:
                rating = float(rating)
                popularity_score = round(max(0.0, min(rating / max_rating, 1.0)), 4)
            except (ValueError, TypeError):
                rating = None
                popularity_score = precomputed_score
        else:
            popularity_score = precomputed_score

        records.append(
            {
                "destination_id": item["destination_id"],
                "name": name[:300],
                "lat": float(item.get("lat", 0)),
                "lng": float(item.get("lng", 0)),
                "category": item.get("category", "urban"),
                "source": source,
                "external_id": external_id[:200],
                "rating": rating,
                "popularity_score": popularity_score,
                "address": item.get("address"),
                "description": item.get("description"),
                "tags": item.get("tags", []),
            }
        )

    logger.info(f"Transformed {len(records)} {source} POI records.")
    return records
