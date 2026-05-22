import json
import logging
import os
import tempfile
from uuid import UUID

from sqlalchemy.orm import Session

from app import models, schemas
from app.config import settings

logger = logging.getLogger(__name__)


def get_vapid_public_key() -> str:
    return settings.VAPID_PUBLIC_KEY


def upsert_subscription(
    db: Session,
    user_id: UUID,
    data: schemas.PushSubscriptionCreate,
) -> models.PushSubscription:
    subscription = db.query(models.PushSubscription).filter(models.PushSubscription.endpoint == data.endpoint).first()
    if subscription is None:
        subscription = models.PushSubscription(
            user_id=user_id,
            endpoint=data.endpoint,
            p256dh=data.keys.p256dh,
            auth=data.keys.auth,
            user_agent=data.user_agent,
        )
        db.add(subscription)
    else:
        subscription.user_id = user_id
        subscription.p256dh = data.keys.p256dh
        subscription.auth = data.keys.auth
        subscription.user_agent = data.user_agent
    db.commit()
    db.refresh(subscription)
    return subscription


def delete_subscription(db: Session, user_id: UUID, endpoint: str) -> None:
    db.query(models.PushSubscription).filter(
        models.PushSubscription.user_id == user_id,
        models.PushSubscription.endpoint == endpoint,
    ).delete(synchronize_session=False)
    db.commit()


def send_push_to_user(
    db: Session,
    user_id: UUID,
    payload: dict,
) -> None:
    if not settings.VAPID_PUBLIC_KEY or not settings.VAPID_PRIVATE_KEY:
        logger.info("Push notification skipped: VAPID keys are not configured")
        return

    try:
        from pywebpush import WebPushException, webpush
    except ImportError:
        logger.warning("Push notification skipped: pywebpush is not installed")
        return

    subscriptions = db.query(models.PushSubscription).filter(models.PushSubscription.user_id == user_id).all()
    private_key_file: str | None = None
    private_key = settings.VAPID_PRIVATE_KEY.replace("\\n", "\n")
    if "-----BEGIN" in private_key:
        with tempfile.NamedTemporaryFile("w", delete=False) as temp:
            temp.write(private_key)
            private_key_file = temp.name
        private_key = private_key_file
    try:
        for subscription in subscriptions:
            subscription_info = {
                "endpoint": subscription.endpoint,
                "keys": {
                    "p256dh": subscription.p256dh,
                    "auth": subscription.auth,
                },
            }
            try:
                webpush(
                    subscription_info=subscription_info,
                    data=json.dumps(payload),
                    vapid_private_key=private_key,
                    vapid_claims={"sub": settings.VAPID_SUBJECT},
                )
            except WebPushException as exc:
                status_code = getattr(getattr(exc, "response", None), "status_code", None)
                if status_code in {404, 410}:
                    db.delete(subscription)
                    db.commit()
                else:
                    logger.info("Push notification failed: %s", exc)
    finally:
        if private_key_file:
            os.unlink(private_key_file)
