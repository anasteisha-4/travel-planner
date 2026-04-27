"""Re-fetch beach POI for Bali from Overpass with expanded radius (50km).

Bali's main beaches (Kuta, Seminyak, Nusa Dua, Sanur, Canggu) are distributed
across the whole island — the default 20km radius only captures the northern tip (Lovina).
This script fetches with radius=50000m, upserts into poi table, then recomputes
the beach activity score for Bali.

Run inside the data-service container:
  docker compose run --rm data-service python scripts/fix_bali_beaches.py
"""

import logging
import sys
from pathlib import Path

# Allow imports from service root
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BALI_LAT = -8.2271303
BALI_LNG = 115.1919203
BALI_RADIUS = 50_000  # 50km — covers entire island


def main() -> None:
    from app.database import SessionLocal
    from app.models import POI, Destination
    from etl.extractors.overpass_beaches import fetch_beaches_for_destination

    db = SessionLocal()
    try:
        bali = db.query(Destination).filter(Destination.name == "Bali").first()
        if not bali:
            logger.error("Bali not found in destinations table")
            return
        dest_id = str(bali.id)
        logger.info(f"Bali destination_id={dest_id}")

        logger.info(f"Fetching beach POI from Overpass (radius={BALI_RADIUS}m)...")
        poi_list = fetch_beaches_for_destination(dest_id, BALI_LAT, BALI_LNG, radius_m=BALI_RADIUS)

        if poi_list is None:
            logger.error("Overpass request failed — try again later")
            return

        logger.info(f"Fetched {len(poi_list)} beach POI from Overpass")

        # Show what we got
        names_summary: dict[str, int] = {}
        for p in poi_list:
            names_summary[p["name"]] = names_summary.get(p["name"], 0) + 1
        for name, cnt in sorted(names_summary.items(), key=lambda x: -x[1])[:20]:
            logger.info(f"  {cnt:3d}x  {name}")

        # Upsert: use external_id as dedup key

        existing_ext_ids = {
            row[0]
            for row in db.query(POI.external_id)
            .filter(
                POI.destination_id == bali.id,
                POI.category == "beach",
            )
            .all()
            if row[0]
        }
        logger.info(f"Existing beach POI in DB: {len(existing_ext_ids)}")

        new_count = 0
        updated_count = 0
        for p in poi_list:
            ext_id = p.get("external_id")
            existing = db.query(POI).filter(POI.external_id == ext_id).first() if ext_id else None
            if existing:
                # Update popularity_score if changed
                if existing.popularity_score != p["popularity_score"]:
                    existing.popularity_score = p["popularity_score"]
                    updated_count += 1
            else:
                poi_obj = POI(
                    destination_id=bali.id,
                    name=p["name"],
                    lat=p["lat"],
                    lng=p["lng"],
                    category=p["category"],
                    source=p["source"],
                    external_id=ext_id,
                    popularity_score=p["popularity_score"],
                    address=p.get("address"),
                    description=p.get("description"),
                    tags=p.get("tags"),
                )
                db.add(poi_obj)
                new_count += 1

        db.commit()
        logger.info(f"Upserted: {new_count} new, {updated_count} updated beach POI")

        # Verify new count
        total = (
            db.query(POI)
            .filter(
                POI.destination_id == bali.id,
                POI.category == "beach",
            )
            .count()
        )
        logger.info(f"Total beach POI for Bali now: {total}")

    finally:
        db.close()

    # Recompute activity scores for Bali
    logger.info("Recomputing beach activity score for Bali...")
    _recompute_bali_beach_score(dest_id)


def _recompute_bali_beach_score(dest_id: str) -> None:
    import math

    from app.database import SessionLocal
    from app.models import POI, DestinationAttributes
    from app.models.activities import DestinationActivity

    db = SessionLocal()
    try:
        # Load all beach POI for Bali
        poi_rows = (
            db.query(POI.name, POI.popularity_score, POI.source)
            .filter(
                POI.destination_id == dest_id,
                POI.category == "beach",
            )
            .all()
        )

        is_coastal = (
            db.query(DestinationAttributes.is_coastal).filter(DestinationAttributes.destination_id == dest_id).scalar()
        ) or False

        _GENERIC_NAMES = frozenset({"Beach", "Sandy Beach", "Pebble Beach"})
        _BEACH_COASTAL_WEIGHT = 2.0
        _BEACH_NAMED_WEIGHT = 1.0
        DIVISOR = 20.0

        eff_count = 0.0
        scores = []
        for name, pop_score, _source in poi_rows:
            weight = _BEACH_COASTAL_WEIGHT if name in _GENERIC_NAMES and is_coastal else _BEACH_NAMED_WEIGHT
            eff_count += weight
            if pop_score is not None:
                scores.append(float(pop_score))

        avg_pop = sum(scores) / len(scores) if scores else 0.5
        count_score = math.tanh(eff_count / DIVISOR)
        new_score = round(0.7 * count_score + 0.3 * avg_pop, 4)

        poi_count = len(poi_rows)
        logger.info(
            f"Bali beach: {poi_count} POI, eff_count={eff_count:.1f}, avg_pop={avg_pop:.3f}, new_score={new_score:.4f}"
        )

        # Upsert activity record
        existing = (
            db.query(DestinationActivity)
            .filter(
                DestinationActivity.destination_id == dest_id,
                DestinationActivity.activity_type == "beach",
            )
            .first()
        )
        if existing:
            old_score = existing.score
            existing.score = new_score
            existing.poi_count = poi_count
            logger.info(f"Updated Bali beach score: {old_score:.4f} → {new_score:.4f}")
        else:
            db.add(
                DestinationActivity(
                    destination_id=dest_id,
                    activity_type="beach",
                    score=new_score,
                    poi_count=poi_count,
                )
            )
            logger.info(f"Created Bali beach activity record: score={new_score:.4f}")

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    main()
