"""
ETL Pipeline Orchestrator

Usage:
    python -m etl.pipeline --seed                      # Full initial seed (all steps)
    python -m etl.pipeline --jobs seasonality          # Run specific jobs
    python -m etl.pipeline --jobs poi_opentripmap      # OpenTripMap POI (with state tracking)
    python -m etl.pipeline --jobs poi_opentripmap --limit 250  # Process up to 250 destinations
    python -m etl.pipeline --jobs poi_osm              # OSM Overpass POI (all destinations)
    python -m etl.pipeline --jobs poi_osm --limit 100  # OSM, up to 100 destinations
    python -m etl.pipeline --jobs poi_protected_areas  # OSM national parks / protected areas
    python -m etl.pipeline --jobs poi_unesco           # UNESCO World Heritage Sites
    python -m etl.pipeline --jobs poi_beaches          # supplementary beach POI (Phase 3.1)
    python -m etl.pipeline --jobs popularity           # Wikipedia pageviews crowd index
"""

import argparse
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

ALL_JOBS = [
    "destinations",
    "safety",
    "costs",
    "visa",
    "seasonality",
    "poi_opentripmap",
    "poi_osm",
    "poi_protected_areas",
    "poi_unesco",
    "poi_wellness",
    "poi_beaches",
    "activities",
    "trajectories",
    "popularity",
    "attributes",
    "language",
    "connectivity",
    "events",
    "infrastructure",
]

# Jobs included in --seed (poi_osm runs separately, no daily limit but slow)
SEED_JOBS = [
    "destinations",
    "safety",
    "costs",
    "visa",
    "seasonality",
    "poi_opentripmap",
    "activities",
    "trajectories",
]


def run_destinations():
    from etl.extractors.rest_countries import extract_countries
    from etl.extractors.numbeo_csv import (
        extract_cities_supplement,
        extract_russia_cities_phase2,
        extract_cis_cities_phase2b,
        extract_turkey_resorts_phase2c,
        extract_north_africa_phase2d,
        extract_global_cities_phase2e,
        extract_sea_cities_phase2f,
        extract_china_cities_phase2g,
        extract_japan_cities_phase2h,
        extract_middle_east_cities_phase2i,
        extract_japan_extra_phase2h,
        extract_middle_east_extra_phase2i,
        extract_south_asia_phase2j,
        extract_latin_america_phase2k,
        extract_north_america_phase2l,
        extract_europe_phase2m,
        extract_oceania_phase2n,
        extract_africa_phase2o,
    )
    from etl.transformers.destination_transformer import (
        transform_countries,
        transform_cities,
    )
    from etl.loaders.postgres_loader import upsert_destinations

    logger.info("Loading destinations from REST Countries API...")
    raw_countries = extract_countries()
    destinations = transform_countries(raw_countries)
    upsert_destinations(destinations)
    logger.info(f"Upserted {len(destinations)} country capitals.")

    logger.info("Loading cities supplement...")
    raw_cities = extract_cities_supplement()
    cities = transform_cities(raw_cities)
    upsert_destinations(cities)
    logger.info(f"Upserted {len(cities)} supplementary cities.")

    logger.info("Loading Russian cities Phase 2...")
    raw_russia = extract_russia_cities_phase2()
    if not raw_russia.empty:
        russia_cities = transform_cities(raw_russia)
        upsert_destinations(russia_cities)
        logger.info(f"Upserted {len(russia_cities)} Russian Phase 2 cities.")

    logger.info("Loading CIS cities Phase 2B...")
    raw_cis = extract_cis_cities_phase2b()
    if not raw_cis.empty:
        cis_cities = transform_cities(raw_cis)
        upsert_destinations(cis_cities)
        logger.info(f"Upserted {len(cis_cities)} CIS Phase 2B cities.")

    logger.info("Loading Turkey resorts Phase 2C...")
    raw_turkey = extract_turkey_resorts_phase2c()
    if not raw_turkey.empty:
        turkey_cities = transform_cities(raw_turkey)
        upsert_destinations(turkey_cities)
        logger.info(f"Upserted {len(turkey_cities)} Turkey Phase 2C resorts.")

    logger.info("Loading North Africa cities Phase 2D...")
    raw_north_africa = extract_north_africa_phase2d()
    if not raw_north_africa.empty:
        north_africa_cities = transform_cities(raw_north_africa)
        upsert_destinations(north_africa_cities)
        logger.info(
            f"Upserted {len(north_africa_cities)} North Africa Phase 2D cities."
        )

    logger.info("Loading global top cities Phase 2E (GeoNames)...")
    raw_global = extract_global_cities_phase2e()
    if not raw_global.empty:
        global_cities = transform_cities(raw_global)
        upsert_destinations(global_cities)
        logger.info(f"Upserted {len(global_cities)} global Phase 2E cities.")

    logger.info("Loading SEA / Indian Ocean cities Phase 2F...")
    raw_sea = extract_sea_cities_phase2f()
    if not raw_sea.empty:
        sea_cities = transform_cities(raw_sea)
        upsert_destinations(sea_cities)
        logger.info(f"Upserted {len(sea_cities)} SEA Phase 2F cities.")

    logger.info("Loading China tourist cities Phase 2G...")
    raw_china = extract_china_cities_phase2g()
    if not raw_china.empty:
        china_cities = transform_cities(raw_china)
        upsert_destinations(china_cities)
        logger.info(f"Upserted {len(china_cities)} China Phase 2G cities.")

    logger.info("Loading Japan tourist cities Phase 2H...")
    raw_japan = extract_japan_cities_phase2h()
    if not raw_japan.empty:
        japan_cities = transform_cities(raw_japan)
        upsert_destinations(japan_cities)
        logger.info(f"Upserted {len(japan_cities)} Japan Phase 2H cities.")

    logger.info("Loading Middle East cities Phase 2I...")
    raw_middle_east = extract_middle_east_cities_phase2i()
    if not raw_middle_east.empty:
        middle_east_cities = transform_cities(raw_middle_east)
        upsert_destinations(middle_east_cities)
        logger.info(f"Upserted {len(middle_east_cities)} Middle East Phase 2I cities.")

    logger.info("Loading extra Japan tourist destinations Phase 2H...")
    raw_japan_extra = extract_japan_extra_phase2h()
    if not raw_japan_extra.empty:
        japan_extra_cities = transform_cities(raw_japan_extra)
        upsert_destinations(japan_extra_cities)
        logger.info(f"Upserted {len(japan_extra_cities)} extra Japan Phase 2H cities.")

    logger.info("Loading extra Middle East tourist destinations Phase 2I...")
    raw_middle_east_extra = extract_middle_east_extra_phase2i()
    if not raw_middle_east_extra.empty:
        middle_east_extra_cities = transform_cities(raw_middle_east_extra)
        upsert_destinations(middle_east_extra_cities)
        logger.info(
            f"Upserted {len(middle_east_extra_cities)} extra Middle East Phase 2I cities."
        )

    logger.info("Loading South Asia tourist cities Phase 2J...")
    raw_south_asia = extract_south_asia_phase2j()
    if not raw_south_asia.empty:
        south_asia_cities = transform_cities(raw_south_asia)
        upsert_destinations(south_asia_cities)
        logger.info(f"Upserted {len(south_asia_cities)} South Asia Phase 2J cities.")

    logger.info("Loading Latin America tourist cities Phase 2K...")
    raw_latin_america = extract_latin_america_phase2k()
    if not raw_latin_america.empty:
        latin_america_cities = transform_cities(raw_latin_america)
        upsert_destinations(latin_america_cities)
        logger.info(
            f"Upserted {len(latin_america_cities)} Latin America Phase 2K cities."
        )

    logger.info("Loading North America cities Phase 2L...")
    raw_north_america = extract_north_america_phase2l()
    if not raw_north_america.empty:
        north_america_cities = transform_cities(raw_north_america)
        upsert_destinations(north_america_cities)
        logger.info(
            f"Upserted {len(north_america_cities)} North America Phase 2L cities."
        )

    logger.info("Loading Europe missing segments Phase 2M...")
    raw_europe = extract_europe_phase2m()
    if not raw_europe.empty:
        europe_cities = transform_cities(raw_europe)
        upsert_destinations(europe_cities)
        logger.info(f"Upserted {len(europe_cities)} Europe Phase 2M cities.")

    logger.info("Loading Oceania cities Phase 2N...")
    raw_oceania = extract_oceania_phase2n()
    if not raw_oceania.empty:
        oceania_cities = transform_cities(raw_oceania)
        upsert_destinations(oceania_cities)
        logger.info(f"Upserted {len(oceania_cities)} Oceania Phase 2N cities.")

    logger.info("Loading Africa expansion Phase 2O...")
    raw_africa = extract_africa_phase2o()
    if not raw_africa.empty:
        africa_cities = transform_cities(raw_africa)
        upsert_destinations(africa_cities)
        logger.info(f"Upserted {len(africa_cities)} Africa Phase 2O cities.")


def run_safety(skip_existing: bool = True):
    from etl.extractors.gpi_csv import extract_gpi
    from etl.transformers.safety_transformer import transform_safety
    from etl.loaders.postgres_loader import upsert_safety

    logger.info("Loading GPI safety scores...")
    raw = extract_gpi()
    records = transform_safety(raw, skip_existing=skip_existing)
    upsert_safety(records)
    logger.info(f"Upserted {len(records)} safety records.")


def run_costs(skip_existing: bool = True):
    from etl.extractors.numbeo_csv import extract_costs
    from etl.transformers.costs_transformer import transform_costs
    from etl.loaders.postgres_loader import upsert_costs

    logger.info("Loading Numbeo cost data...")
    raw = extract_costs()
    records = transform_costs(raw, skip_existing=skip_existing)
    upsert_costs(records)
    logger.info(f"Upserted {len(records)} cost records.")


def run_visa():
    from etl.extractors.passport_index_csv import extract_passport_index
    from etl.transformers.visa_transformer import transform_visa
    from etl.loaders.postgres_loader import upsert_visa_rules

    logger.info("Loading Passport Index (ilyankou/passport-index-dataset)...")
    raw = extract_passport_index()
    records = transform_visa(raw)
    upsert_visa_rules(records)
    logger.info(f"Upserted {len(records)} visa rule records.")


def run_seasonality():
    from etl.extractors.open_meteo import extract_weather_for_all_destinations
    from etl.transformers.seasonality_transformer import transform_seasonality
    from etl.loaders.postgres_loader import upsert_seasonality

    logger.info("Fetching historical weather data...")
    raw = extract_weather_for_all_destinations()
    records = transform_seasonality(raw)
    upsert_seasonality(records)
    logger.info(f"Upserted {len(records)} seasonality records.")


def run_poi_opentripmap(limit: int | None = None):
    from etl.extractors.opentripmap import extract_poi_opentripmap
    from etl.transformers.poi_transformer import transform_poi
    from etl.loaders.postgres_loader import upsert_poi

    logger.info("Fetching POI from OpenTripMap...")
    raw = extract_poi_opentripmap(limit=limit)
    records = transform_poi(raw, source="opentripmap")
    upsert_poi(records)
    logger.info(f"Upserted {len(records)} OpenTripMap POI.")


def run_poi_osm(limit: int | None = None):
    from etl.extractors.overpass_osm import iter_poi_overpass
    from etl.transformers.poi_transformer import transform_poi
    from etl.loaders.postgres_loader import upsert_poi

    logger.info("Fetching POI from OSM Overpass (streaming per-destination)...")
    total = 0
    for dest_name, raw in iter_poi_overpass(limit=limit):
        if not raw:
            continue
        records = transform_poi(raw, source="overpass_osm")
        upsert_poi(records)
        total += len(records)
        logger.info(
            f"Upserted {len(records)} OSM POI for {dest_name} (total so far: {total})"
        )
    logger.info(f"OSM Overpass complete. Total upserted: {total}")


def run_poi_beaches(limit: int | None = None):
    from etl.extractors.overpass_beaches import iter_beaches_overpass
    from etl.loaders.postgres_loader import upsert_poi

    logger.info("Fetching beach POI (natural=beach, leisure=beach, beach_resort)...")
    total = 0
    for dest_name, raw in iter_beaches_overpass(limit=limit):
        if not raw:
            logger.info(f"  {dest_name}: no beaches found")
            continue
        upsert_poi(raw)
        total += len(raw)
        logger.info(f"  {dest_name}: {len(raw)} beach POI (total: {total})")
    logger.info(f"Beach supplement complete. Total upserted: {total}")


def run_poi_wellness(limit: int | None = None):
    from etl.extractors.overpass_wellness import iter_wellness_overpass
    from etl.loaders.postgres_loader import upsert_poi

    logger.info(
        "Fetching wellness POI v2 (public_bath, sauna, spa, mineral_spring, massage)..."
    )
    total = 0
    for dest_name, raw in iter_wellness_overpass(limit=limit):
        if not raw:
            continue
        upsert_poi(raw)
        total += len(raw)
        logger.info(f"  {dest_name}: {len(raw)} wellness POI (total: {total})")
    logger.info(f"Wellness supplement complete. Total upserted: {total}")


def run_poi_protected_areas(limit: int | None = None):
    from etl.extractors.overpass_protected_areas import iter_protected_areas
    from etl.loaders.postgres_loader import upsert_poi

    logger.info("Fetching OSM protected areas (national parks, nature reserves)...")
    total = 0
    for dest_name, raw in iter_protected_areas(limit=limit):
        if not raw:
            logger.info(f"  {dest_name}: no protected areas found")
            continue
        upsert_poi(raw)
        total += len(raw)
        logger.info(f"  {dest_name}: {len(raw)} protected areas (total: {total})")
    logger.info(f"Protected areas complete. Total upserted: {total}")


def run_poi_unesco():
    from app.database import SessionLocal
    from app.models import Destination
    from etl.extractors.unesco_csv import extract_unesco
    from etl.loaders.postgres_loader import upsert_poi

    db = SessionLocal()
    try:
        destinations = [
            {"id": str(d.id), "name": d.name, "lat": d.lat, "lng": d.lng}
            for d in db.query(Destination).filter(Destination.is_active == True).all()  # noqa: E712
        ]
    finally:
        db.close()

    logger.info(f"Mapping UNESCO sites to {len(destinations)} destinations...")
    records = extract_unesco(destinations)
    upsert_poi(records)
    logger.info(f"Upserted {len(records)} UNESCO heritage POI.")


def run_activities():
    from etl.transformers.activity_transformer import compute_activity_scores
    from etl.loaders.postgres_loader import upsert_activities

    logger.info("Computing activity scores...")
    records = compute_activity_scores()
    upsert_activities(records)
    logger.info(f"Upserted {len(records)} activity score records.")


def run_trajectories():
    from etl.loaders.postgres_loader import generate_trajectories

    logger.info("Generating trajectory templates...")
    count = generate_trajectories()
    logger.info(f"Generated {count} trajectory templates.")


def run_popularity():
    from etl.extractors.wikipedia_pageviews import (
        extract_pageviews_missing_destinations as extract_pageviews_all_destinations,
    )
    from etl.transformers.popularity_transformer import transform_popularity
    from etl.loaders.postgres_loader import upsert_popularity

    logger.info("Fetching Wikipedia pageviews for crowd index...")
    raw = extract_pageviews_all_destinations()
    records = transform_popularity(raw)
    upsert_popularity(records)
    logger.info(f"Upserted {len(records)} popularity records.")


def run_attributes(skip_existing: bool = True, use_overpass: bool = True):
    from etl.transformers.attributes_transformer import transform_attributes
    from etl.loaders.postgres_loader import upsert_attributes

    mode = "Overpass API" if use_overpass else "country-code heuristics (fast)"
    logger.info(f"Computing destination attributes ({mode})...")
    records = transform_attributes(
        use_overpass=use_overpass, skip_existing=skip_existing
    )
    upsert_attributes(records)
    logger.info(f"Upserted {len(records)} destination_attributes records.")


def run_language(skip_existing: bool = True):
    from etl.extractors.rest_countries import extract_country_languages
    from etl.transformers.language_transformer import transform_language_accessibility
    from etl.loaders.postgres_loader import upsert_language_accessibility

    logger.info(
        "Building language accessibility scores (rule-based by country_code)..."
    )
    country_languages = extract_country_languages()
    records = transform_language_accessibility(
        country_languages, skip_existing=skip_existing
    )
    upsert_language_accessibility(records)
    logger.info(f"Upserted {len(records)} language_accessibility records.")


def run_connectivity(skip_existing: bool = True):
    from etl.extractors.openflights import load_overrides
    from etl.transformers.connectivity_transformer import transform_connectivity
    from etl.loaders.postgres_loader import upsert_connectivity

    logger.info("Building connectivity scores (rule-based + manual overrides)...")
    overrides = load_overrides()
    records = transform_connectivity(overrides, skip_existing=skip_existing)
    upsert_connectivity(records)
    logger.info(f"Upserted {len(records)} connectivity records.")


def run_infrastructure(
    use_overpass: bool = False,
    use_wikidata_metro: bool = False,
    skip_existing: bool = True,
):
    from etl.transformers.infrastructure_transformer import transform_infrastructure
    from etl.loaders.postgres_loader import upsert_infrastructure

    logger.info("Building infrastructure scores (CSV metro index + real data)...")
    records = transform_infrastructure(
        use_overpass=use_overpass,
        use_wikidata_metro=use_wikidata_metro,
        skip_existing=skip_existing,
    )
    upsert_infrastructure(records)
    logger.info(f"Upserted {len(records)} infrastructure records.")


def run_events(use_wikidata: bool = False):
    from etl.transformers.events_transformer import (
        transform_events,
        enrich_with_wikidata,
    )
    from etl.loaders.postgres_loader import upsert_events

    logger.info("Loading destination events from seed CSV...")
    records = transform_events()
    if use_wikidata:
        logger.info("Enriching with Wikidata SPARQL (~5 min)...")
        records = enrich_with_wikidata(records)
    upsert_events(records)
    logger.info(f"Upserted {len(records)} destination event records.")


JOB_RUNNERS: dict = {
    "destinations": run_destinations,
    "safety": run_safety,
    "costs": run_costs,
    "visa": run_visa,
    "seasonality": run_seasonality,
    "poi_opentripmap": run_poi_opentripmap,
    "poi_osm": run_poi_osm,
    "poi_protected_areas": run_poi_protected_areas,
    "poi_unesco": run_poi_unesco,
    "poi_wellness": run_poi_wellness,
    "poi_beaches": run_poi_beaches,
    "activities": run_activities,
    "trajectories": run_trajectories,
    "popularity": run_popularity,
    "attributes": run_attributes,
    "language": run_language,
    "connectivity": run_connectivity,
    "events": run_events,
    "infrastructure": run_infrastructure,
}

LIMIT_JOBS = {"poi_opentripmap", "poi_osm", "poi_protected_areas", "poi_wellness"}


def main():
    parser = argparse.ArgumentParser(description="Triply Data ETL Pipeline")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--seed", action="store_true", help="Run full initial seed")
    group.add_argument("--jobs", type=str, help="Comma-separated list of jobs to run")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max destinations to process (for poi_opentripmap and poi_osm jobs)",
    )
    parser.add_argument(
        "--wikidata",
        action="store_true",
        default=False,
        help="For 'events' job: enrich seed with Wikidata SPARQL (~5 min, ~200 extra events)",
    )
    parser.add_argument(
        "--overpass",
        action="store_true",
        default=False,
        help="For 'infrastructure' job: use Overpass API for metro detection (~37 min)",
    )
    parser.add_argument(
        "--wikidata-metro",
        action="store_true",
        default=False,
        help="For 'infrastructure' job: enrich metro index from Wikidata SPARQL and save to CSV",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        default=True,
        help="For 'attributes' job: skip destinations already in destination_attributes",
    )
    parser.add_argument(
        "--no-overpass",
        action="store_true",
        default=False,
        help="For 'attributes' job: use country-code heuristics instead of Overpass API (fast, ~30s)",
    )
    args = parser.parse_args()

    if args.seed:
        jobs = SEED_JOBS
    else:
        jobs = [j.strip() for j in args.jobs.split(",")]
        unknown = set(jobs) - set(ALL_JOBS)
        if unknown:
            raise ValueError(f"Unknown jobs: {unknown}. Available: {ALL_JOBS}")

    logger.info(f"Running ETL jobs: {jobs}")
    for job in jobs:
        try:
            runner = JOB_RUNNERS[job]
            if job in LIMIT_JOBS:
                runner(limit=args.limit)
            elif job == "events":
                runner(use_wikidata=args.wikidata)
            elif job == "infrastructure":
                runner(
                    use_overpass=args.overpass,
                    use_wikidata_metro=getattr(args, "wikidata_metro", False),
                    skip_existing=args.skip_existing,
                )
            elif job == "attributes":
                runner(
                    skip_existing=args.skip_existing, use_overpass=not args.no_overpass
                )
            elif job in ("safety", "costs", "language", "connectivity"):
                runner(skip_existing=args.skip_existing)
            else:
                runner()
        except Exception as e:
            logger.error(f"Job '{job}' failed: {e}", exc_info=True)
            raise

    logger.info("ETL pipeline complete.")


if __name__ == "__main__":
    main()
