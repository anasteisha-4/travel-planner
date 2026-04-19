"""Compute destination activity scores from POI data."""

import logging
import math
from collections import defaultdict

logger = logging.getLogger(__name__)

# Generic OSM names generated for unnamed objects — treated as reduced weight in count.
# These are real features (parks, gardens) but represent low-value OSM tagging:
# 32K "Park" + 31K "Garden" entries were inflating nature scores for non-nature cities
# (Ghent 94% generic → same score as Queenstown with real mountains/fjords).
#
# Beach special-casing:
#   Most real sea beaches are unnamed in OSM and collapse to name="Beach".
#   For coastal destinations these are legitimate sea-beach POI → high weight + fast saturation.
#   For inland destinations (rivers, lakes) the same tag appears but shouldn't dominate —
#   Warsaw's Vistula sandbanks ≠ Ibiza beach destination.
#
#   "Sandy Beach" (413 destinations) and "Pebble Beach" (109 destinations) are OSM generic
#   templates — not unique named beaches — and are treated as generic names.
#
#   Weight rules per (is_coastal, name_type) for beach category:
#     is_coastal=True,  generic name  → weight=2.0  (real sea-beach feature)
#     is_coastal=True,  named POI     → weight=1.0  (standard)
#     is_coastal=False, generic name  → weight=0.1  (river/lake sandbank, minimal credit)
#     is_coastal=False, named POI     → weight=0.3  (real inland beach, but penalised vs coast)
#
#   Divisor for beach category:
#     coastal → 20 (fast saturation, genuine beach destinations)
#     inland  → 60 (very slow saturation; London/Berlin with 100+ lake POI still < 0.35)
#
_GENERIC_NAMES: frozenset[str] = frozenset(
    {
        "Park",
        "Garden",
        "Viewpoint",
        "Beach",
        "Sandy Beach",
        "Pebble Beach",
        "Hot Spring",
        "Peak",
        "Cave",
        "Waterfall",
        "Spa",
    }
)
_GENERIC_WEIGHT = 0.25  # parks, gardens — low-value unnamed OSM objects
_BEACH_COASTAL_WEIGHT = 2.0  # generic beach in coastal destination — real sea feature
_BEACH_INLAND_WEIGHT = (
    0.1  # generic beach in inland destination — river/lake, minimal credit
)
_BEACH_NAMED_INLAND_WEIGHT = (
    0.3  # named (unique) beach in inland destination — penalised vs coast
)
_HERITAGE_WEIGHT = 10.0  # UNESCO / national park = equivalent to 10 regular POI

_DEFAULT_TANH_DIVISOR = 20.0  # standard saturation point for all categories
_BEACH_INLAND_TANH_DIVISOR = (
    60.0  # inland beach saturates 3× slower (vs 20 for coastal)
)


def _load_coastal_destinations() -> set[str]:
    """Return set of destination_ids where is_coastal=True in destination_attributes."""
    from app.database import SessionLocal
    from app.models import DestinationAttributes

    db = SessionLocal()
    try:
        rows = (
            db.query(DestinationAttributes.destination_id)
            .filter(
                DestinationAttributes.is_coastal == True  # noqa: E712
            )
            .all()
        )
        return {str(r.destination_id) for r in rows}
    finally:
        db.close()


def compute_activity_scores() -> list[dict]:
    """Aggregate POI → destination_activities scores.

    Formula: 0.7 * tanh(eff_count / divisor) + 0.3 * avg_popularity

    Weight and divisor rules per (destination, category) group:
      - heritage source                          → weight=10.0
      - generic name, beach cat, coastal dest    → weight=2.0
      - generic name, beach cat, inland dest     → weight=0.1
      - generic name, other cat                  → weight=0.25
      - named beach POI, coastal dest            → weight=1.0
      - named beach POI, inland dest             → weight=0.3  (penalised: lake/river beach)
      - named POI, other category                → weight=1.0

      divisor for beach category:
        coastal destination  → 20  (standard)
        inland destination   → 60  (3× slower: London/Berlin with 100+ lake POI stay < 0.35)

    Coastal flag comes from destination_attributes.is_coastal.
    Destinations without an attributes row default to inland behaviour.
    """
    from app.database import SessionLocal
    from app.models import POI, POISource

    coastal_ids = _load_coastal_destinations()
    logger.info(
        f"Loaded {len(coastal_ids)} coastal destinations for beach weight adjustment."
    )

    db = SessionLocal()
    try:
        from app.models import Destination

        poi_rows = (
            db.query(
                POI.destination_id,
                POI.category,
                POI.name,
                POI.popularity_score,
                POI.source,
            )
            .join(Destination, POI.destination_id == Destination.id)
            .filter(Destination.is_active)
            .all()
        )
    finally:
        db.close()

    # Group by (destination_id, category)
    groups: dict[tuple, dict] = defaultdict(
        lambda: {"scores": [], "count": 0, "eff_count": 0.0}
    )

    for dest_id, category, name, pop_score, source in poi_rows:
        dest_id_str = str(dest_id)
        key = (dest_id_str, category)
        is_coastal = dest_id_str in coastal_ids

        if source == POISource.heritage:
            weight = _HERITAGE_WEIGHT
        elif name in _GENERIC_NAMES and category == "beach":
            weight = _BEACH_COASTAL_WEIGHT if is_coastal else _BEACH_INLAND_WEIGHT
        elif name in _GENERIC_NAMES:
            weight = _GENERIC_WEIGHT
        elif category == "beach" and not is_coastal:
            weight = _BEACH_NAMED_INLAND_WEIGHT
        else:
            weight = 1.0

        groups[key]["count"] += 1
        groups[key]["eff_count"] += weight
        if pop_score is not None:
            groups[key]["scores"].append(pop_score)

    records = []
    for (dest_id, activity_type), data in groups.items():
        count = data["count"]
        eff_count = data["eff_count"]
        avg_pop = sum(data["scores"]) / len(data["scores"]) if data["scores"] else 0.5

        # Divisor rules for beach category:
        #   coastal destination → 20 (standard, fast saturation for real sea beaches)
        #   inland destination  → 60 (3× slower: London/Berlin 100+ lake POI stay < 0.35)
        # Sintra/Bariloche: marked is_coastal=True in override CSV → gets divisor=20 correctly.
        is_coastal = dest_id in coastal_ids
        if activity_type == "beach" and not is_coastal:
            divisor = _BEACH_INLAND_TANH_DIVISOR  # 40 for all inland
        else:
            divisor = _DEFAULT_TANH_DIVISOR  # 20 for coastal or non-beach activities

        count_score = math.tanh(eff_count / divisor)
        score = round(0.7 * count_score + 0.3 * avg_pop, 4)
        score = max(0.0, min(1.0, score))

        records.append(
            {
                "destination_id": dest_id,
                "activity_type": activity_type,
                "score": score,
                "poi_count": count,
            }
        )

    logger.info(f"Computed {len(records)} activity score records.")
    return records
