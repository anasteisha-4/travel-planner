"""Upsert helpers using SQLAlchemy Core for ETL loading."""

import logging
import uuid

from sqlalchemy.dialects.postgresql import insert

logger = logging.getLogger(__name__)


def _get_db():
    from app.database import SessionLocal

    return SessionLocal()


def upsert_destinations(records: list[dict]) -> None:
    from app.models import Destination

    if not records:
        return
    db = _get_db()
    try:
        for record in records:
            stmt = insert(Destination).values(id=uuid.uuid4(), **record)
            stmt = stmt.on_conflict_do_update(
                constraint="uq_destination_name_country",
                set_={
                    "lat": stmt.excluded.lat,
                    "lng": stmt.excluded.lng,
                    "region": stmt.excluded.region,
                    "subregion": stmt.excluded.subregion,
                    "population": stmt.excluded.population,
                    "currencies": stmt.excluded.currencies,
                    "is_active": stmt.excluded.is_active,
                    "radius_m": stmt.excluded.radius_m,
                },
            )
            db.execute(stmt)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def upsert_safety(records: list[dict]) -> None:
    from app.models import DestinationSafety

    if not records:
        return
    db = _get_db()
    try:
        for record in records:
            stmt = insert(DestinationSafety).values(id=uuid.uuid4(), **record)
            stmt = stmt.on_conflict_do_update(
                index_elements=["destination_id"],
                set_={
                    "safety_score": stmt.excluded.safety_score,
                    "gpi_score": stmt.excluded.gpi_score,
                    "gpi_rank": stmt.excluded.gpi_rank,
                    "gpi_year": stmt.excluded.gpi_year,
                    "safety_data_source": stmt.excluded.safety_data_source,
                    "city_adjustment_factor": stmt.excluded.city_adjustment_factor,
                },
            )
            db.execute(stmt)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def upsert_costs(records: list[dict]) -> None:
    from app.models import DestinationCosts

    if not records:
        return
    db = _get_db()
    try:
        for record in records:
            stmt = insert(DestinationCosts).values(id=uuid.uuid4(), **record)
            stmt = stmt.on_conflict_do_update(
                index_elements=["destination_id"],
                set_={
                    "avg_meal_cost_usd": stmt.excluded.avg_meal_cost_usd,
                    "avg_transport_cost_usd": stmt.excluded.avg_transport_cost_usd,
                    "avg_hotel_cost_usd": stmt.excluded.avg_hotel_cost_usd,
                    "avg_daily_cost_usd": stmt.excluded.avg_daily_cost_usd,
                    "cost_index": stmt.excluded.cost_index,
                    "data_source": stmt.excluded.data_source,
                    "data_quality_score": stmt.excluded.data_quality_score,
                },
            )
            db.execute(stmt)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def upsert_seasonality(records: list[dict]) -> None:
    from app.models import DestinationSeasonality

    if not records:
        return
    db = _get_db()
    try:
        for record in records:
            stmt = insert(DestinationSeasonality).values(id=uuid.uuid4(), **record)
            stmt = stmt.on_conflict_do_update(
                constraint="uq_seasonality_dest_month",
                set_={
                    "avg_temp_c": stmt.excluded.avg_temp_c,
                    "avg_precipitation_mm": stmt.excluded.avg_precipitation_mm,
                    "avg_humidity_pct": stmt.excluded.avg_humidity_pct,
                    "season_score": stmt.excluded.season_score,
                },
            )
            db.execute(stmt)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def upsert_visa_rules(records: list[dict]) -> None:
    from app.models import VisaRule

    if not records:
        return
    db = _get_db()
    try:
        for record in records:
            stmt = insert(VisaRule).values(id=uuid.uuid4(), **record)
            stmt = stmt.on_conflict_do_update(
                constraint="uq_visa_citizenship_dest",
                set_={
                    "visa_type": stmt.excluded.visa_type,
                    "visa_score": stmt.excluded.visa_score,
                    "max_stay_days": stmt.excluded.max_stay_days,
                    "data_year": stmt.excluded.data_year,
                },
            )
            db.execute(stmt)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def upsert_poi(records: list[dict]) -> None:
    from app.models import POI

    if not records:
        return
    db = _get_db()
    try:
        for record in records:
            stmt = insert(POI).values(id=uuid.uuid4(), **record)
            stmt = stmt.on_conflict_do_update(
                constraint="uq_poi_source_external",
                set_={
                    "name": stmt.excluded.name,
                    "lat": stmt.excluded.lat,
                    "lng": stmt.excluded.lng,
                    "category": stmt.excluded.category,
                    "rating": stmt.excluded.rating,
                    "popularity_score": stmt.excluded.popularity_score,
                    "address": stmt.excluded.address,
                    "tags": stmt.excluded.tags,
                    "opening_hours": stmt.excluded.opening_hours,
                },
            )
            db.execute(stmt)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def upsert_activities(records: list[dict]) -> None:
    from app.models import DestinationActivity

    if not records:
        return
    db = _get_db()
    try:
        # Full replace: delete all existing records, then re-insert from fresh computation.
        # ON CONFLICT UPDATE would leave stale records for destinations that lost all POI.
        db.query(DestinationActivity).delete()
        for record in records:
            db.execute(insert(DestinationActivity).values(id=uuid.uuid4(), **record))
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def upsert_language_accessibility(records: list[dict]) -> None:
    from app.models.language import DestinationLanguageAccessibility

    if not records:
        return
    db = _get_db()
    try:
        for record in records:
            stmt = insert(DestinationLanguageAccessibility).values(id=uuid.uuid4(), **record)
            stmt = stmt.on_conflict_do_update(
                index_elements=["destination_id"],
                set_={
                    "local_languages": stmt.excluded.local_languages,
                    "russian_speaking_score": stmt.excluded.russian_speaking_score,
                    "english_speaking_score": stmt.excluded.english_speaking_score,
                    "has_cyrillic_signs": stmt.excluded.has_cyrillic_signs,
                    "script_difficulty": stmt.excluded.script_difficulty,
                    "data_source": stmt.excluded.data_source,
                    "updated_at": stmt.excluded.updated_at,
                },
            )
            db.execute(stmt)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def upsert_attributes(records: list[dict]) -> None:
    from app.models.attributes import DestinationAttributes

    if not records:
        return
    db = _get_db()
    try:
        for i, record in enumerate(records, 1):
            stmt = insert(DestinationAttributes).values(id=uuid.uuid4(), **record)
            stmt = stmt.on_conflict_do_update(
                index_elements=["destination_id"],
                set_={
                    "dest_type": stmt.excluded.dest_type,
                    "vibe": stmt.excluded.vibe,
                    "best_for": stmt.excluded.best_for,
                    "landscape": stmt.excluded.landscape,
                    "beach_type": stmt.excluded.beach_type,
                    "has_ski": stmt.excluded.has_ski,
                    "has_thermal": stmt.excluded.has_thermal,
                    "is_coastal": stmt.excluded.is_coastal,
                    "altitude_m": stmt.excluded.altitude_m,
                    "summer_temp_class": stmt.excluded.summer_temp_class,
                    "winter_temp_class": stmt.excluded.winter_temp_class,
                    "data_source": stmt.excluded.data_source,
                    "updated_at": stmt.excluded.updated_at,
                },
            )
            db.execute(stmt)
            db.commit()  # per-record commit: progress survives crashes/interrupts
            if i % 10 == 0 or i == len(records):
                logger.info(f"Upserted {i}/{len(records)} destination_attributes records.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def upsert_popularity(records: list[dict]) -> None:
    from app.models import DestinationPopularity

    if not records:
        return
    db = _get_db()
    try:
        for record in records:
            stmt = insert(DestinationPopularity).values(id=uuid.uuid4(), **record)
            stmt = stmt.on_conflict_do_update(
                constraint="uq_popularity_dest_month",
                set_={
                    "avg_pageviews": stmt.excluded.avg_pageviews,
                    "crowd_index": stmt.excluded.crowd_index,
                    "wikipedia_article": stmt.excluded.wikipedia_article,
                    "data_year": stmt.excluded.data_year,
                },
            )
            db.execute(stmt)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def upsert_connectivity(records: list[dict]) -> None:
    from app.models.connectivity import DestinationConnectivity

    if not records:
        return
    db = _get_db()
    try:
        for record in records:
            stmt = insert(DestinationConnectivity).values(id=uuid.uuid4(), **record)
            stmt = stmt.on_conflict_do_update(
                index_elements=["destination_id"],
                set_={
                    "direct_from_moscow": stmt.excluded.direct_from_moscow,
                    "direct_from_spb": stmt.excluded.direct_from_spb,
                    "direct_from_ekb": stmt.excluded.direct_from_ekb,
                    "direct_from_novosibirsk": stmt.excluded.direct_from_novosibirsk,
                    "transit_via_dubai": stmt.excluded.transit_via_dubai,
                    "transit_via_istanbul": stmt.excluded.transit_via_istanbul,
                    "transit_via_yerevan": stmt.excluded.transit_via_yerevan,
                    "transit_via_tashkent": stmt.excluded.transit_via_tashkent,
                    "transit_via_tbilisi": stmt.excluded.transit_via_tbilisi,
                    "train_from_moscow": stmt.excluded.train_from_moscow,
                    "train_hours_from_moscow": stmt.excluded.train_hours_from_moscow,
                    "flight_hours_from_moscow": stmt.excluded.flight_hours_from_moscow,
                    "min_transit_hours": stmt.excluded.min_transit_hours,
                    "connectivity_score": stmt.excluded.connectivity_score,
                    "mir_card_accepted": stmt.excluded.mir_card_accepted,
                    "data_source": stmt.excluded.data_source,
                    "data_year": stmt.excluded.data_year,
                    "updated_at": stmt.excluded.updated_at,
                },
            )
            db.execute(stmt)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def upsert_infrastructure(records: list[dict]) -> None:
    from app.models.infrastructure import DestinationInfrastructure

    if not records:
        return
    db = _get_db()
    try:
        for record in records:
            stmt = insert(DestinationInfrastructure).values(id=uuid.uuid4(), **record)
            stmt = stmt.on_conflict_do_update(
                index_elements=["destination_id"],
                set_={
                    "has_metro": stmt.excluded.has_metro,
                    "taxi_app_available": stmt.excluded.taxi_app_available,
                    "road_quality_score": stmt.excluded.road_quality_score,
                    "avg_internet_mbps": stmt.excluded.avg_internet_mbps,
                    "healthcare_score": stmt.excluded.healthcare_score,
                    "atm_density_score": stmt.excluded.atm_density_score,
                    "cash_economy": stmt.excluded.cash_economy,
                    "data_source": stmt.excluded.data_source,
                    "data_source_details": stmt.excluded.data_source_details,
                    "updated_at": stmt.excluded.updated_at,
                },
            )
            db.execute(stmt)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def upsert_events(records: list[dict]) -> None:
    """Full replace strategy: delete all existing events and re-insert from seed.

    Events are sourced from a static seed CSV, so a full replace is safe and ensures
    removed events don't linger. Runs fast (<1s for ~100 seed rows).
    """
    from app.models.events import DestinationEvent

    if not records:
        return
    db = _get_db()
    try:
        db.query(DestinationEvent).delete()
        for record in records:
            db.execute(insert(DestinationEvent).values(id=uuid.uuid4(), **record))
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


_THEME_CATEGORIES = {
    "morning": {"culture", "historic", "heritage", "museum"},
    "afternoon": {"nature", "beach", "adventure", "outdoor"},
    "evening": {"food", "nightlife", "wellness", "shopping"},
}

_THEME_FALLBACK = ["urban", "culture", "nature", "food"]

# Category → visit_duration_minutes defaults (used for itinerary time budgeting)
_DURATION_MAP = {
    "museum": 120,
    "culture": 90,
    "historic": 90,
    "heritage": 90,
    "castle": 90,
    "nature": 120,
    "adventure": 120,
    "outdoor": 120,
    "beach": 180,
    "park": 90,
    "viewpoint": 30,
    "food": 60,
    "restaurant": 60,
    "nightlife": 120,
    "shopping": 60,
    "wellness": 60,
    "urban": 45,
}


def _geo_sort(poi_list: list) -> list:
    """Greedy nearest-neighbour sort to minimise travel distance within a day."""
    if len(poi_list) <= 2:
        return poi_list
    remaining = list(poi_list)
    # Start from westernmost POI (reduces zig-zags)
    current = min(remaining, key=lambda p: p.lng)
    remaining.remove(current)
    ordered = [current]
    while remaining:
        nearest = min(
            remaining,
            key=lambda p: (p.lat - current.lat) ** 2 + (p.lng - current.lng) ** 2,
        )
        remaining.remove(nearest)
        ordered.append(nearest)
        current = nearest
    return ordered


def _pick_by_theme(poi_list: list, theme: str, n: int, used_ids: set) -> list:
    """Pick up to n POI matching theme categories, falling back to any unused POI."""
    preferred_cats = _THEME_CATEGORIES.get(theme, set())
    preferred = [p for p in poi_list if p.category in preferred_cats and str(p.id) not in used_ids]
    others = [p for p in poi_list if p.category not in preferred_cats and str(p.id) not in used_ids]
    selected = (preferred + others)[:n]
    return selected


def generate_trajectories() -> int:
    """Generate day-by-day trajectory templates from POI clusters.

    Improvements vs v1:
    - Thematic day structure: morning=culture/historic, afternoon=nature/beach, evening=food/nightlife
    - Geo-sort POI within each day (greedy nearest-neighbour) to reduce travel zig-zags
    - activity_tags reflect all categories present in the template
    """
    from app.database import SessionLocal
    from app.models import POI, Destination, Trajectory

    db = SessionLocal()
    try:
        destinations = db.query(Destination).filter(Destination.is_active == True).all()  # noqa: E712
        count = 0
        for dest in destinations:
            poi_list = (
                db.query(POI)
                .filter(POI.destination_id == dest.id)
                .order_by(POI.popularity_score.desc().nullslast())
                .limit(80)  # larger pool for thematic selection
                .all()
            )
            if len(poi_list) < 5:
                continue

            for duration_days in [3, 5, 7]:
                poi_per_day = min(4, len(poi_list) // duration_days)
                if poi_per_day < 1:
                    continue

                # Day themes cycle: morning → afternoon → evening → morning …
                day_themes = ["morning", "afternoon", "evening"]

                sequence = []
                activity_tags: set[str] = set()
                used_ids: set[str] = set()

                for day in range(1, duration_days + 1):
                    theme = day_themes[(day - 1) % len(day_themes)]
                    day_poi = _pick_by_theme(poi_list, theme, poi_per_day, used_ids)
                    if not day_poi:
                        break

                    day_poi = _geo_sort(day_poi)
                    poi_ids = [str(p.id) for p in day_poi]
                    used_ids.update(poi_ids)
                    categories = list({p.category for p in day_poi})
                    activity_tags.update(categories)

                    sequence.append(
                        {
                            "day": day,
                            "poi_ids": poi_ids,
                            "theme": theme,
                            "categories": categories,
                        }
                    )

                if not sequence:
                    continue

                existing = (
                    db.query(Trajectory)
                    .filter(
                        Trajectory.destination_id == dest.id,
                        Trajectory.duration_days == duration_days,
                        Trajectory.source == "generated",
                    )
                    .first()
                )
                if existing:
                    existing.sequence_of_poi = sequence
                    existing.activity_tags = list(activity_tags)
                else:
                    db.add(
                        Trajectory(
                            destination_id=dest.id,
                            duration_days=duration_days,
                            sequence_of_poi=sequence,
                            source="generated",
                            activity_tags=list(activity_tags),
                        )
                    )
                count += 1

        db.commit()
        return count
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
