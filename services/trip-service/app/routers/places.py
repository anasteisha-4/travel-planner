from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import schemas
from app.database import get_db
from app.deps import get_current_user_id
from app.services import place_service

router = APIRouter()


def _place_to_response(place) -> schemas.PlaceVisitResponse:
    return schemas.PlaceVisitResponse(
        id=place.id,
        trip_id=place.trip_id,
        user_id=place.user_id,
        name=place.name,
        visited_at=place.visited_at,
        latitude=place.latitude,
        longitude=place.longitude,
        notes=place.notes,
        created_at=place.created_at.isoformat() if place.created_at else "",
        updated_at=place.updated_at.isoformat() if place.updated_at else None,
    )


@router.post("/trips/{trip_id}/places", response_model=schemas.PlaceVisitResponse, status_code=201)
def create_place(
    trip_id: UUID,
    data: schemas.PlaceVisitCreate,
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    place = place_service.create_place(db, user_id, trip_id, data)
    return _place_to_response(place)


@router.get("/trips/{trip_id}/places", response_model=list[schemas.PlaceVisitResponse])
def get_places(
    trip_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    places = place_service.get_places_by_trip(db, user_id, trip_id)
    return [_place_to_response(p) for p in places]


@router.delete("/places/{place_id}", status_code=204)
def delete_place(
    place_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    place_service.delete_place(db, user_id, place_id)
