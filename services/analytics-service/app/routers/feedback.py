import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user_id
from app.exceptions import AppException
from app.models.post_trip_feedback import PostTripFeedback
from app.schemas.feedback import (
    PendingFeedbackItem,
    PostTripFeedbackCreate,
    PostTripFeedbackResponse,
    PostTripFeedbackUpdate,
)

router = APIRouter(prefix="/api/v1/feedback", tags=["feedback"])


@router.post("/post-trip", response_model=PostTripFeedbackResponse, status_code=201)
def submit_post_trip_feedback(
    body: PostTripFeedbackCreate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> PostTripFeedback:
    existing = db.query(PostTripFeedback).filter(PostTripFeedback.trip_id == body.trip_id).first()
    if existing:
        raise AppException(status_code=409, code="FEEDBACK_EXISTS", message="Feedback already submitted for this trip")

    feedback = PostTripFeedback(
        id=uuid.uuid4(),
        user_id=user_id,
        trip_id=body.trip_id,
        destination=body.destination,
        overall_rating=body.overall_rating,
        destination_rating=body.destination_rating,
        value_rating=body.value_rating,
        actual_total_cost=body.actual_total_cost,
        actual_currency=body.actual_currency,
        would_revisit=body.would_revisit,
        free_text=body.free_text,
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return feedback


@router.get("/post-trip/{trip_id}", response_model=PostTripFeedbackResponse)
def get_post_trip_feedback(
    trip_id: str,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> PostTripFeedback:
    feedback = (
        db.query(PostTripFeedback)
        .filter(PostTripFeedback.trip_id == trip_id, PostTripFeedback.user_id == user_id)
        .first()
    )
    if not feedback:
        raise AppException(status_code=404, code="FEEDBACK_NOT_FOUND", message="No feedback for this trip")
    return feedback


@router.put("/post-trip/{trip_id}", response_model=PostTripFeedbackResponse)
def update_post_trip_feedback(
    trip_id: str,
    body: PostTripFeedbackUpdate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> PostTripFeedback:
    feedback = (
        db.query(PostTripFeedback)
        .filter(PostTripFeedback.trip_id == trip_id, PostTripFeedback.user_id == user_id)
        .first()
    )
    if not feedback:
        raise AppException(status_code=404, code="FEEDBACK_NOT_FOUND", message="No feedback for this trip")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(feedback, field, value)

    db.commit()
    db.refresh(feedback)
    return feedback


@router.delete("/post-trip/{trip_id}", status_code=204)
def delete_post_trip_feedback(
    trip_id: str,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> None:
    feedback = (
        db.query(PostTripFeedback)
        .filter(PostTripFeedback.trip_id == trip_id, PostTripFeedback.user_id == user_id)
        .first()
    )
    if feedback:
        db.delete(feedback)
        db.commit()


@router.get("/pending", response_model=list[PendingFeedbackItem])
def get_pending_feedback(
    trip_ids: list[str] = Query(..., alias="trip_id"),
    destinations: list[str] = Query(..., alias="destination"),
    completed_ats: list[str | None] = Query([], alias="completed_at"),
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> list[PendingFeedbackItem]:
    if not trip_ids:
        return []

    submitted_ids = {
        row.trip_id
        for row in db.query(PostTripFeedback.trip_id)
        .filter(
            PostTripFeedback.user_id == user_id,
            PostTripFeedback.trip_id.in_(trip_ids),
        )
        .all()
    }

    result = []
    for i, trip_id in enumerate(trip_ids):
        if trip_id not in submitted_ids:
            result.append(
                PendingFeedbackItem(
                    trip_id=trip_id,
                    destination=destinations[i] if i < len(destinations) else "",
                    completed_at=completed_ats[i] if i < len(completed_ats) else None,
                )
            )

    return result
