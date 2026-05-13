from uuid import UUID

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app import schemas
from app.database import get_db
from app.deps import get_current_user_id
from app.services import itinerary_service
from app.services.analytics_events import emit_itinerary_quality_event

router = APIRouter()


@router.get("/{trip_id}/itinerary", response_model=schemas.ItineraryStateResponse)
def get_itinerary_state(
    trip_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return itinerary_service.get_itinerary_state(db, user_id, trip_id)


@router.post("/{trip_id}/itinerary/generate", response_model=list[schemas.ItineraryResponse], status_code=201)
def generate_itinerary(
    trip_id: UUID,
    data: schemas.ItineraryGenerateRequest,
    authorization: str | None = Header(default=None),
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    itineraries = itinerary_service.generate_itineraries(db, user_id, trip_id, data, authorization)
    responses = [itinerary_service.to_response(db, item) for item in itineraries]
    for item in responses:
        emit_itinerary_quality_event(
            "itinerary_candidate_generated",
            {
                "trip_id": str(trip_id),
                "itinerary_id": str(item.id),
                "template_version": item.model_version,
                "ranker_version": item.model_version,
                "days": len(item.days),
                "places": sum(len(day.items) for day in item.days),
                "route_signature": item.route_signature,
                "variant_index": item.variant_index,
            },
            entity_type="itinerary",
            entity_id=item.id,
            authorization=authorization,
        )
    return responses


@router.post("/{trip_id}/itinerary/regenerate", response_model=list[schemas.ItineraryResponse], status_code=201)
def regenerate_itinerary(
    trip_id: UUID,
    data: schemas.ItineraryRegenerateRequest,
    authorization: str | None = Header(default=None),
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    itineraries = itinerary_service.generate_itineraries(db, user_id, trip_id, data, authorization)
    responses = [itinerary_service.to_response(db, item) for item in itineraries]
    for item in responses:
        emit_itinerary_quality_event(
            "itinerary_candidate_generated",
            {
                "trip_id": str(trip_id),
                "itinerary_id": str(item.id),
                "template_version": item.model_version,
                "ranker_version": item.model_version,
                "days": len(item.days),
                "places": sum(len(day.items) for day in item.days),
                "route_signature": item.route_signature,
                "variant_index": item.variant_index,
                "regenerated": True,
            },
            entity_type="itinerary",
            entity_id=item.id,
            authorization=authorization,
        )
    return responses


@router.post("/{trip_id}/itinerary/{itinerary_id}/approve", response_model=schemas.ItineraryResponse)
def approve_itinerary(
    trip_id: UUID,
    itinerary_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    itinerary = itinerary_service.approve_itinerary(db, user_id, trip_id, itinerary_id)
    return itinerary_service.to_response(db, itinerary)


@router.post("/{trip_id}/itinerary/items", response_model=schemas.ItineraryItemResponse, status_code=201)
def add_manual_item(
    trip_id: UUID,
    data: schemas.ItineraryManualItemCreate,
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    item = itinerary_service.add_manual_item(db, user_id, trip_id, data)
    return itinerary_service._item_response(item)


@router.patch("/{trip_id}/itinerary/items/{item_id}", response_model=schemas.ItineraryItemResponse)
def update_item(
    trip_id: UUID,
    item_id: UUID,
    data: schemas.ItineraryItemUpdate,
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    item = itinerary_service.update_item(db, user_id, trip_id, item_id, data)
    return itinerary_service._item_response(item)


@router.post("/{trip_id}/itinerary/items/{item_id}/swap", response_model=schemas.ItineraryResponse)
def swap_items(
    trip_id: UUID,
    item_id: UUID,
    data: schemas.ItineraryItemSwapRequest,
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    itinerary = itinerary_service.swap_items(db, user_id, trip_id, item_id, data)
    return itinerary_service.to_response(db, itinerary)


@router.post("/{trip_id}/itinerary/items/{item_id}/move", response_model=schemas.ItineraryResponse)
def move_item(
    trip_id: UUID,
    item_id: UUID,
    data: schemas.ItineraryItemMoveRequest,
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    itinerary = itinerary_service.move_item(db, user_id, trip_id, item_id, data)
    return itinerary_service.to_response(db, itinerary)


@router.delete("/{trip_id}/itinerary/items/{item_id}", status_code=204)
def remove_item(
    trip_id: UUID,
    item_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    itinerary_service.remove_item(db, user_id, trip_id, item_id)


@router.post("/{trip_id}/itinerary/items/{item_id}/visit", response_model=schemas.ItineraryItemResponse)
def mark_item_visited(
    trip_id: UUID,
    item_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    item = itinerary_service.mark_item_visited(db, user_id, trip_id, item_id)
    return itinerary_service._item_response(item)


@router.delete("/{trip_id}/itinerary/items/{item_id}/visit", response_model=schemas.ItineraryItemResponse)
def unmark_item_visited(
    trip_id: UUID,
    item_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    item = itinerary_service.unmark_item_visited(db, user_id, trip_id, item_id)
    return itinerary_service._item_response(item)
