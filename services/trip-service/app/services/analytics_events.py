import logging
import uuid
from datetime import UTC, datetime
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


def emit_itinerary_quality_event(
    event_type: str,
    context: dict[str, Any],
    *,
    entity_type: str | None = None,
    entity_id: uuid.UUID | str | None = None,
    authorization: str | None = None,
) -> None:
    payload = {
        "events": [
            {
                "event_id": str(uuid.uuid4()),
                "session_id": "trip-service",
                "event_type": event_type,
                "event_version": 1,
                "entity_type": entity_type,
                "entity_id": str(entity_id) if entity_id is not None else None,
                "context": context,
                "occurred_at": datetime.now(UTC).isoformat(),
                "client_meta": {"platform": "server", "service": "trip-service"},
            }
        ]
    }
    headers = {"X-Request-ID": str(uuid.uuid4())}
    if authorization:
        headers["Authorization"] = authorization

    try:
        httpx.post(
            f"{settings.ANALYTICS_SERVICE_URL.rstrip('/')}/api/v1/events",
            json=payload,
            headers=headers,
            timeout=0.8,
        )
    except httpx.HTTPError as exc:
        logger.info("Itinerary quality event skipped: %s", exc)
