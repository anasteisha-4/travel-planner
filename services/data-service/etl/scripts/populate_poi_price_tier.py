"""Populate price_tier for POI based on OSM tags and category rules.

Rules:
- fee=no, free_entry=yes → free
- natural=beach, natural=water, natural=peak, natural=cave → free
- tourism=museum, tourism=gallery, tourism=monument → mid
- tourism=hostel, tourism=hotel → mid
- amenity=restaurant, amenity=cafe → budget
- amenity=bar, amenity=pub, amenity=nightclub → budget
- historic=castle, historic=monument → mid
- leisure=park, leisure=garden → free
- Default for unknown → null (to be determined by user)

entrance_fee_usd:
- For 'free' → 0
- For others → extracted from fee_usd tag, or null
"""

import logging

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.poi import POI


logger = logging.getLogger(__name__)


def extract_price_tier_from_tags(tags: list | None) -> tuple[str | None, float | None]:
    """
    Extract price_tier and entrance_fee_usd from OSM tags.

    Tags format: ["key=value", "key2=value2"]

    Returns:
        (price_tier, entrance_fee_usd)
    """
    if not tags or not isinstance(tags, list):
        return None, None

    # Parse tags into a dict
    tag_dict = {}
    for tag in tags:
        if isinstance(tag, str) and "=" in tag:
            key, value = tag.split("=", 1)
            tag_dict[key] = value

    # Free entries
    if tag_dict.get("fee") == "no" or tag_dict.get("free_entry") == "yes":
        return "free", 0.0

    fee_usd = None
    fee_value = tag_dict.get("fee_usd")
    if fee_value:
        try:
            fee_usd = float(fee_value)
        except (ValueError, TypeError):
            fee_usd = None

    # Natural features - free
    natural = tag_dict.get("natural")
    if natural in ("beach", "water", "peak", "cave", "waterfall"):
        return "free", 0.0

    # Parks and gardens - free
    leisure = tag_dict.get("leisure")
    if leisure in ("park", "garden", "playground"):
        return "free", 0.0

    # Tourism attractions - mid-tier by default
    tourism = tag_dict.get("tourism")
    if tourism in ("museum", "gallery", "monument", "historical"):
        price_tier = "mid"
        return price_tier, fee_usd

    if tourism in ("hostel", "hotel"):
        price_tier = "mid"
        return price_tier, fee_usd

    # Historic features - mid-tier
    historic = tag_dict.get("historic")
    if historic in ("castle", "monument", "ruins", "memorials"):
        return "mid", fee_usd

    # Food & Drink - budget
    amenity = tag_dict.get("amenity")
    if amenity in ("restaurant", "cafe", "fast_food"):
        return "budget", fee_usd

    if amenity in ("bar", "pub", "nightclub"):
        return "budget", fee_usd

    # Sport - budget
    if amenity in ("sports_centre", "swimming_pool", "gym"):
        return "budget", fee_usd

    # No explicit rule - return None
    return None, fee_usd


def populate_price_tier(db: Session) -> None:
    """Populate price_tier and entrance_fee_usd for all POI."""
    try:
        pois = db.execute(select(POI)).scalars().all()
        logger.info(f"Processing {len(pois)} POI records...")

        updated_count = 0
        for poi in pois:
            price_tier, entrance_fee_usd = extract_price_tier_from_tags(poi.tags)

            # Only update if price_tier is not already set
            if poi.price_tier is None and price_tier is not None:
                poi.price_tier = price_tier
                if entrance_fee_usd is not None:
                    poi.entrance_fee_usd = entrance_fee_usd
                updated_count += 1

                if updated_count % 10000 == 0:
                    db.commit()
                    logger.info(f"Committed {updated_count} records...")

        db.commit()
        logger.info(f"Successfully updated {updated_count} POI records with price_tier")

    except Exception as e:
        logger.error(f"Error populating price_tier: {e}", exc_info=True)
        db.rollback()
        raise


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    engine = create_engine(settings.DATABASE_URL)

    with Session(engine) as db:
        populate_price_tier(db)
