from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.deps import get_internal_db, verify_internal_secret

router = APIRouter(prefix="", tags=["internal"], dependencies=[Depends(verify_internal_secret)])


@router.get("/destinations")
def list_destinations_internal(
    country_code: str | None = None,
    db: Session = Depends(get_internal_db),
):
    from app.models import Destination, DestinationCosts, DestinationSafety

    q = db.query(Destination).filter(Destination.is_active == True)  # noqa: E712
    if country_code:
        q = q.filter(Destination.country_code == country_code.upper())
    destinations = q.all()

    result = []
    for d in destinations:
        costs = db.query(DestinationCosts).filter(DestinationCosts.destination_id == d.id).first()
        safety = db.query(DestinationSafety).filter(DestinationSafety.destination_id == d.id).first()
        result.append(
            {
                "id": str(d.id),
                "name": d.name,
                "country_code": d.country_code,
                "lat": d.lat,
                "lng": d.lng,
                "region": d.region,
                "avg_daily_cost_usd": costs.avg_daily_cost_usd if costs else None,
                "cost_index": costs.cost_index if costs else None,
                "safety_score": safety.safety_score if safety else None,
            }
        )
    return result


@router.get("/airports/resolve-iata")
def resolve_airport_iata(
    city_name: str | None = None,
    lat: float | None = None,
    lng: float | None = None,
    country_code: str | None = None,
    db: Session = Depends(get_internal_db),
):
    from app.services.airport_service import resolve_iata

    return {
        "iata_code": resolve_iata(
            db,
            city_name,
            lat=lat,
            lng=lng,
            country_code=country_code,
        )
    }


@router.post("/recommendations")
def get_recommendations(
    citizenship_code: str,
    travel_month: int,
    budget_per_day_usd: float,
    preferred_activities: list[str],
    limit: int = 10,
    db: Session = Depends(get_internal_db),
):
    from app.services.recommendation_service import recommend_destinations

    return recommend_destinations(
        db=db,
        citizenship_code=citizenship_code,
        travel_month=travel_month,
        budget_per_day_usd=budget_per_day_usd,
        preferred_activities=preferred_activities,
        limit=limit,
    )


@router.post("/budget/predict")
def predict_budget(
    destination_id: str,
    duration_days: int,
    people_count: int,
    db: Session = Depends(get_internal_db),
):
    from app.services.budget_service import predict_trip_budget

    return predict_trip_budget(
        db=db,
        destination_id=destination_id,
        duration_days=duration_days,
        people_count=people_count,
    )


@router.get("/validation")
def validate_trip(
    destination_id: str,
    citizenship_code: str,
    travel_month: int,
    db: Session = Depends(get_internal_db),
):
    from app.services.validation_service import validate_trip_params

    return validate_trip_params(
        db=db,
        destination_id=destination_id,
        citizenship_code=citizenship_code,
        travel_month=travel_month,
    )


@router.post("/itinerary")
def generate_itinerary(
    destination_id: str,
    duration_days: int,
    preferred_activities: list[str] = Query(default_factory=list),
    start_date: str | None = None,
    variant_count: int = 1,
    variant_seed: int | None = None,
    pace: str = "standard",
    day_start_time: str = "09:30",
    day_end_time: str = "19:00",
    rest_days_count: int = 0,
    exclude_signature: str | None = None,
    trip_budget: float | None = None,
    people_count: int = 1,
    db: Session = Depends(get_internal_db),
):
    import contextlib
    from datetime import datetime as dt_class
    from datetime import time as time_class

    from app.services.itinerary_service import generate_itinerary

    parsed_start_date = None
    if start_date:
        with contextlib.suppress(ValueError):
            parsed_start_date = dt_class.fromisoformat(start_date)
    parsed_start_time = time_class.fromisoformat(day_start_time)
    parsed_end_time = time_class.fromisoformat(day_end_time)

    return generate_itinerary(
        db=db,
        destination_id=destination_id,
        duration_days=duration_days,
        preferred_activities=preferred_activities,
        start_date=parsed_start_date,
        variant_count=variant_count,
        variant_seed=variant_seed,
        pace=pace,
        day_start_time=parsed_start_time,
        day_end_time=parsed_end_time,
        rest_days_count=rest_days_count,
        exclude_signature=exclude_signature,
        trip_budget=trip_budget,
        people_count=people_count,
    )


@router.post("/osm/itinerary")
async def ingest_osm_and_generate_itinerary(
    destination_name: str,
    lat: float,
    lng: float,
    radius_m: int = 12000,
    duration_days: int = 1,
    preferred_activities: list[str] = Query(default_factory=list),
    start_date: str | None = None,
    variant_count: int = 1,
    variant_seed: int | None = None,
    pace: str = "standard",
    day_start_time: str = "09:30",
    day_end_time: str = "19:00",
    rest_days_count: int = 0,
    exclude_signature: str | None = None,
    trip_budget: float | None = None,
    people_count: int = 1,
    db: Session = Depends(get_internal_db),
):
    import contextlib
    from datetime import datetime as dt_class
    from datetime import time as time_class

    from app.services.osm_ingestion_service import ingest_osm_poi_and_generate_itinerary

    parsed_start_date = None
    if start_date:
        with contextlib.suppress(ValueError):
            parsed_start_date = dt_class.fromisoformat(start_date)
    return await ingest_osm_poi_and_generate_itinerary(
        db=db,
        destination_name=destination_name,
        lat=lat,
        lng=lng,
        radius_m=radius_m,
        duration_days=duration_days,
        preferred_activities=preferred_activities,
        start_date=parsed_start_date,
        variant_count=variant_count,
        variant_seed=variant_seed,
        pace=pace,
        day_start_time=time_class.fromisoformat(day_start_time),
        day_end_time=time_class.fromisoformat(day_end_time),
        rest_days_count=rest_days_count,
        exclude_signature=exclude_signature,
        trip_budget=trip_budget,
        people_count=people_count,
    )


@router.get("/admin/destination-ingestion-requests")
def list_destination_ingestion_requests(
    status: str = "pending",
    db: Session = Depends(get_internal_db),
):
    from app.services.osm_ingestion_service import list_destination_ingestion_requests

    return list_destination_ingestion_requests(db, status=status)


@router.post("/admin/destination-ingestion-requests/{request_id}/approve")
def approve_destination_ingestion_request(
    request_id: str,
    db: Session = Depends(get_internal_db),
):
    import uuid

    from fastapi import HTTPException

    from app.services.osm_ingestion_service import approve_destination_ingestion_request

    result = approve_destination_ingestion_request(db, uuid.UUID(request_id))
    if result is None:
        raise HTTPException(status_code=404, detail="Destination ingestion request not found")
    return result
