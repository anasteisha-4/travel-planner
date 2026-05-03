from fastapi import APIRouter, Depends
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
    preferred_activities: list[str],
    start_date: str | None = None,
    db: Session = Depends(get_internal_db),
):
    import contextlib
    from datetime import datetime as dt_class

    from app.services.itinerary_service import generate_itinerary

    parsed_start_date = None
    if start_date:
        with contextlib.suppress(ValueError):
            parsed_start_date = dt_class.fromisoformat(start_date)

    return generate_itinerary(
        db=db,
        destination_id=destination_id,
        duration_days=duration_days,
        preferred_activities=preferred_activities,
        start_date=parsed_start_date,
    )
