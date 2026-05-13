from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.deps import get_current_user_id
from app.exceptions import AppException

router = APIRouter()


def trip_to_response(trip: models.Trip) -> schemas.TripResponse:
    return schemas.TripResponse(
        id=trip.id,
        user_id=trip.user_id,
        destination=trip.destination,
        destination_id=trip.destination_id,
        start_date=trip.start_date,
        end_date=trip.end_date,
        budget=trip.budget,
        currency=trip.currency,
        people_count=trip.people_count,
        rest_days_count=trip.rest_days_count,
        status=schemas.TripStatus(trip.status),
        trip_type=trip.trip_type,
        season=trip.season,
        departure_city=trip.departure_city,
        notes=trip.notes,
        created_at=trip.created_at.isoformat() if trip.created_at else "",
        updated_at=trip.updated_at.isoformat() if trip.updated_at else None,
    )


def _trip_duration_days(start_date, end_date) -> int:
    return max(1, (end_date - start_date).days + 1)


def _validate_rest_days(start_date, end_date, rest_days_count: int) -> None:
    if rest_days_count > _trip_duration_days(start_date, end_date):
        raise AppException(
            status_code=400,
            code="INVALID_REST_DAYS",
            message="Rest days count cannot exceed trip duration.",
        )


def _should_reset_itinerary(trip: models.Trip, update_fields: dict) -> bool:
    reset_fields = {"destination", "destination_id", "start_date", "end_date", "rest_days_count"}
    return any(getattr(trip, field) != update_fields[field] for field in reset_fields & update_fields.keys())


def _archive_active_itineraries(db: Session, trip_id: UUID, user_id: UUID) -> None:
    db.query(models.TripItinerary).filter(
        models.TripItinerary.trip_id == trip_id,
        models.TripItinerary.user_id == user_id,
        models.TripItinerary.status.in_(["draft", "approved"]),
    ).update({"status": "archived"}, synchronize_session=False)


@router.get("/", response_model=list[schemas.TripResponse])
def list_trips(
    status: schemas.TripStatus | None = Query(None),
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    query = db.query(models.Trip).filter(models.Trip.user_id == user_id)
    if status:
        query = query.filter(models.Trip.status == status.value)
    trips = query.order_by(models.Trip.created_at.desc()).all()
    return [trip_to_response(t) for t in trips]


@router.post("/", response_model=schemas.TripResponse, status_code=201)
def create_trip(
    trip_data: schemas.TripCreate,
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    _validate_rest_days(trip_data.start_date, trip_data.end_date, trip_data.rest_days_count)
    trip = models.Trip(
        user_id=user_id,
        destination=trip_data.destination,
        destination_id=trip_data.destination_id,
        start_date=trip_data.start_date,
        end_date=trip_data.end_date,
        budget=trip_data.budget,
        currency=trip_data.currency,
        people_count=trip_data.people_count,
        rest_days_count=trip_data.rest_days_count,
        trip_type=trip_data.trip_type,
        season=trip_data.season,
        departure_city=trip_data.departure_city,
        notes=trip_data.notes,
    )
    db.add(trip)
    db.commit()
    db.refresh(trip)
    return trip_to_response(trip)


@router.get("/{trip_id}", response_model=schemas.TripResponse)
def get_trip(
    trip_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    trip = db.query(models.Trip).filter(models.Trip.id == trip_id, models.Trip.user_id == user_id).first()
    if not trip:
        raise AppException(status_code=404, code="NOT_FOUND", message="Trip not found")
    return trip_to_response(trip)


@router.put("/{trip_id}", response_model=schemas.TripResponse)
def update_trip(
    trip_id: UUID,
    trip_data: schemas.TripUpdate,
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    trip = db.query(models.Trip).filter(models.Trip.id == trip_id, models.Trip.user_id == user_id).first()
    if not trip:
        raise AppException(status_code=404, code="NOT_FOUND", message="Trip not found")

    update_fields = trip_data.model_dump(exclude_unset=True)
    next_start = update_fields.get("start_date", trip.start_date)
    next_end = update_fields.get("end_date", trip.end_date)
    next_rest_days = update_fields.get("rest_days_count", trip.rest_days_count)
    _validate_rest_days(next_start, next_end, next_rest_days)
    should_reset_itinerary = _should_reset_itinerary(trip, update_fields)
    for field, value in update_fields.items():
        if field == "status" and value is not None:
            setattr(trip, field, value.value if isinstance(value, schemas.TripStatus) else value)
        else:
            setattr(trip, field, value)
    if should_reset_itinerary:
        _archive_active_itineraries(db, trip_id, user_id)

    db.commit()
    db.refresh(trip)
    return trip_to_response(trip)


@router.delete("/{trip_id}", status_code=204)
def delete_trip(
    trip_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    trip = db.query(models.Trip).filter(models.Trip.id == trip_id, models.Trip.user_id == user_id).first()
    if not trip:
        raise AppException(status_code=404, code="NOT_FOUND", message="Trip not found")
    db.delete(trip)
    db.commit()
