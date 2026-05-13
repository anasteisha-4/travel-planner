import uuid
from datetime import UTC

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_optional_user_id
from app.models.user_event import UserEvent
from app.schemas.events import EventsBatchRequest, EventsBatchResponse
from app.services.event_contract import CANONICAL_EVENT_VERSION, validate_event_contract

router = APIRouter(prefix="/api/v1/events", tags=["events"])

SERVICE_VERSION = "0.1.0"


@router.post("", response_model=EventsBatchResponse, status_code=202)
async def ingest_events(
    body: EventsBatchRequest,
    user_id: uuid.UUID | None = Depends(get_optional_user_id),
    x_request_id: str | None = Header(None, alias="X-Request-ID"),
    db: Session = Depends(get_db),
) -> EventsBatchResponse:
    rows = []
    warnings: list[str] = []
    event_ids = [ev.event_id for ev in body.events if ev.event_id is not None]
    existing_event_ids = set()
    if event_ids:
        existing_event_ids = set(db.query(UserEvent.event_id).filter(UserEvent.event_id.in_(event_ids)).all())

    for ev in body.events:
        if ev.event_id is not None and (ev.event_id,) in existing_event_ids:
            warnings.append(f"duplicate_event_id:{ev.event_id}")
            continue

        occurred_at = ev.occurred_at
        if occurred_at is not None and occurred_at.tzinfo is None:
            occurred_at = occurred_at.replace(tzinfo=UTC)

        client_meta = dict(ev.client_meta or {})
        client_meta.setdefault("event_version", ev.event_version or CANONICAL_EVENT_VERSION)

        result = validate_event_contract(
            event_id=ev.event_id,
            event_type=ev.event_type,
            entity_type=ev.entity_type,
            entity_id=ev.entity_id,
            context=ev.context,
            client_meta=client_meta,
            request_id=x_request_id,
            environment=getattr(settings, "ENVIRONMENT", "local"),
            service_version=SERVICE_VERSION,
        )
        warnings.extend(result.warnings)

        rows.append(
            UserEvent(
                event_id=ev.event_id,
                user_id=user_id,
                session_id=ev.session_id,
                event_type=result.event_type,
                entity_type=result.entity_type,
                entity_id=result.entity_id,
                context=result.context,
                client_meta=result.client_meta,
                **({"created_at": occurred_at} if occurred_at else {}),
            )
        )

    db.add_all(rows)
    db.commit()

    return EventsBatchResponse(accepted=len(rows), warning_count=len(warnings), warnings=warnings[:50])
