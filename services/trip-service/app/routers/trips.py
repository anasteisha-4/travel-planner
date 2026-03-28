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
        start_date=trip.start_date,
        end_date=trip.end_date,
        budget=trip.budget,
        currency=trip.currency,
        people_count=trip.people_count,
        status=schemas.TripStatus(trip.status),
        trip_type=trip.trip_type,
        season=trip.season,
        departure_city=trip.departure_city,
        notes=trip.notes,
        created_at=trip.created_at.isoformat() if trip.created_at else "",
        updated_at=trip.updated_at.isoformat() if trip.updated_at else None,
    )


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
    trip = models.Trip(
        user_id=user_id,
        destination=trip_data.destination,
        start_date=trip_data.start_date,
        end_date=trip_data.end_date,
        budget=trip_data.budget,
        currency=trip_data.currency,
        people_count=trip_data.people_count,
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
    for field, value in update_fields.items():
        if field == "status" and value is not None:
            setattr(trip, field, value.value if isinstance(value, schemas.TripStatus) else value)
        else:
            setattr(trip, field, value)

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
