import uuid
from datetime import UTC

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_optional_user_id
from app.models.user_event import UserEvent
from app.schemas.events import EventsBatchRequest, EventsBatchResponse

router = APIRouter(prefix="/api/v1/events", tags=["events"])


@router.post("", response_model=EventsBatchResponse, status_code=202)
async def ingest_events(
    body: EventsBatchRequest,
    user_id: uuid.UUID | None = Depends(get_optional_user_id),
    db: Session = Depends(get_db),
) -> EventsBatchResponse:
    rows = []
    for ev in body.events:
        occurred_at = ev.occurred_at
        if occurred_at is not None and occurred_at.tzinfo is None:
            occurred_at = occurred_at.replace(tzinfo=UTC)

        rows.append(
            UserEvent(
                user_id=user_id,
                session_id=ev.session_id,
                event_type=ev.event_type,
                entity_type=ev.entity_type,
                entity_id=ev.entity_id,
                context=ev.context,
                client_meta=ev.client_meta,
                **({"created_at": occurred_at} if occurred_at else {}),
            )
        )

    db.add_all(rows)
    db.commit()

    return EventsBatchResponse(accepted=len(rows))
