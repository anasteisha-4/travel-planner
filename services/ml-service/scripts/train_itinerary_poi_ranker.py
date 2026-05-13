"""Register itinerary POI ranker metadata.

This is the v1 training entrypoint for the post-defense itinerary engine. The
served engine currently uses the same feature contract with a heuristic scorer
fallback; this script registers the model version so deployment, observability,
and future real-feedback training have a stable model registry slot.
"""

import json
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings

MODEL_NAME = "itinerary"
MODEL_VERSION = "itinerary-poi-ranker-v1"


def main() -> None:
    engine = create_engine(settings.DATABASE_URL)
    metrics = {
        "model_family": "heuristic_ltr_bootstrap",
        "feature_groups": [
            "user_preferences",
            "trip_context",
            "poi_quality",
            "opening_hours",
            "route_context",
        ],
        "feedback_labels": [
            "approved_item",
            "pinned_item",
            "manual_add",
            "visited_item",
            "removed_item",
            "skipped_item",
        ],
        "registered_at": datetime.now(UTC).isoformat(),
    }
    with Session(engine) as session:
        session.execute(
            text("UPDATE model_registry SET is_active = false WHERE name = :name"),
            {"name": MODEL_NAME},
        )
        existing = session.execute(
            text("SELECT id FROM model_registry WHERE name = :name AND version = :version"),
            {"name": MODEL_NAME, "version": MODEL_VERSION},
        ).first()
        if existing:
            session.execute(
                text(
                    """
                    UPDATE model_registry
                    SET is_active = true, metrics = CAST(:metrics AS JSONB), trained_at = :trained_at
                    WHERE id = :id
                    """
                ),
                {"id": existing.id, "metrics": json.dumps(metrics), "trained_at": datetime.now(UTC)},
            )
        else:
            session.execute(
                text(
                    """
                    INSERT INTO model_registry (id, name, version, model_type, is_active, metrics, trained_at)
                    VALUES (:id, :name, :version, 'itinerary_poi_ranker', true, CAST(:metrics AS JSONB), :trained_at)
                    """
                ),
                {
                    "name": MODEL_NAME,
                    "id": uuid.uuid4(),
                    "version": MODEL_VERSION,
                    "metrics": json.dumps(metrics),
                    "trained_at": datetime.now(UTC),
                },
            )
        session.commit()


if __name__ == "__main__":
    main()
