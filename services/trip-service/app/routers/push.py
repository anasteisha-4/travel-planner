from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import schemas
from app.database import get_db
from app.deps import get_current_user_id
from app.services import push_service

router = APIRouter()


@router.get("/vapid-public-key", response_model=schemas.VapidPublicKeyResponse)
def get_vapid_public_key():
    return schemas.VapidPublicKeyResponse(public_key=push_service.get_vapid_public_key())


@router.post("/subscriptions", response_model=schemas.PushSubscriptionResponse, status_code=201)
def save_subscription(
    data: schemas.PushSubscriptionCreate,
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return push_service.upsert_subscription(db, user_id, data)


@router.delete("/subscriptions", status_code=204)
def remove_subscription(
    data: schemas.PushSubscriptionCreate,
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    push_service.delete_subscription(db, user_id, data.endpoint)
