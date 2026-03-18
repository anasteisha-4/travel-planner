from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app import models, schemas
from app.exceptions import AppException


def _validate_coordinates(latitude: Decimal, longitude: Decimal) -> None:
    if not (-90 <= latitude <= 90):
        raise AppException(
            status_code=400,
            code="INVALID_COORDINATES",
            message="Latitude must be between -90 and 90",
        )
    if not (-180 <= longitude <= 180):
        raise AppException(
            status_code=400,
            code="INVALID_COORDINATES",
            message="Longitude must be between -180 and 180",
        )


def _verify_trip_ownership(db: Session, trip_id: UUID, user_id: UUID) -> models.Trip:
    trip = (
        db.query(models.Trip)
        .filter(
            models.Trip.id == trip_id,
            models.Trip.user_id == user_id,
        )
        .first()
    )
    if not trip:
        raise AppException(status_code=404, code="NOT_FOUND", message="Trip not found")
    return trip


def _verify_place_ownership(db: Session, place_id: UUID, user_id: UUID) -> models.PlaceVisit:
    place = (
        db.query(models.PlaceVisit)
        .filter(
            models.PlaceVisit.id == place_id,
            models.PlaceVisit.user_id == user_id,
        )
        .first()
    )
    if not place:
        raise AppException(status_code=404, code="NOT_FOUND", message="Place not found")
    return place


def create_place(
    db: Session,
    user_id: UUID,
    trip_id: UUID,
    data: schemas.PlaceVisitCreate,
) -> models.PlaceVisit:
    _verify_trip_ownership(db, trip_id, user_id)
    _validate_coordinates(data.latitude, data.longitude)

    place = models.PlaceVisit(
        user_id=user_id,
        trip_id=trip_id,
        name=data.name,
        visited_at=data.visited_at,
        latitude=data.latitude,
        longitude=data.longitude,
        notes=data.notes,
    )
    db.add(place)
    db.commit()
    db.refresh(place)
    return place


def get_places_by_trip(
    db: Session,
    user_id: UUID,
    trip_id: UUID,
) -> list[models.PlaceVisit]:
    _verify_trip_ownership(db, trip_id, user_id)
    return (
        db.query(models.PlaceVisit)
        .filter(
            models.PlaceVisit.trip_id == trip_id,
            models.PlaceVisit.user_id == user_id,
        )
        .order_by(models.PlaceVisit.visited_at.asc(), models.PlaceVisit.created_at.asc())
        .all()
    )


def delete_place(db: Session, user_id: UUID, place_id: UUID) -> None:
    place = _verify_place_ownership(db, place_id, user_id)
    db.delete(place)
    db.commit()
