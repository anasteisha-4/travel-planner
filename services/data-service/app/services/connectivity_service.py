"""Dynamic connectivity score computation with hub exclusion support.

Stored connectivity_score reflects the full picture (all hubs available).
When the geopolitical situation changes (e.g. Dubai or Istanbul become
undesirable), callers pass excluded_hubs and get a recalculated score
without touching the database.

Usage in recommendation engine:
    scores = get_connectivity_scores(db, dest_ids, excluded_hubs=["dubai"])
    score = scores.get(destination_id, 0.0)

Valid hub names: "dubai", "istanbul", "yerevan", "tashkent", "tbilisi"
"""

import uuid

from sqlalchemy.orm import Session

from etl.transformers.connectivity_transformer import HUB_FIELDS, compute_score


def get_connectivity_scores(
    db: Session,
    destination_ids: list[uuid.UUID],
    excluded_hubs: list[str] | None = None,
) -> dict[uuid.UUID, float]:
    """Return connectivity scores for the given destinations.

    If excluded_hubs is empty/None — returns stored connectivity_score (fast path).
    If excluded_hubs is provided — recomputes score on the fly for each destination.

    Args:
        db: SQLAlchemy session.
        destination_ids: list of destination UUIDs to look up.
        excluded_hubs: hub names to exclude. Valid: "dubai", "istanbul",
                       "yerevan", "tashkent", "tbilisi".

    Returns:
        {destination_id: score} — missing destinations default to 0.0.
    """
    from app.models.connectivity import DestinationConnectivity

    rows = (
        db.query(DestinationConnectivity)
        .filter(DestinationConnectivity.destination_id.in_(destination_ids))
        .all()
    )

    excluded = {h.lower() for h in (excluded_hubs or [])}

    # Validate hub names early — fail loudly on typos
    unknown = excluded - set(HUB_FIELDS.keys())
    if unknown:
        raise ValueError(
            f"Unknown hub names: {unknown}. Valid hubs: {sorted(HUB_FIELDS.keys())}"
        )

    if not excluded:
        # Fast path — use pre-computed score
        return {row.destination_id: row.connectivity_score for row in rows}

    # Slow path — recompute per row
    result: dict[uuid.UUID, float] = {}
    for row in rows:
        record = {
            "direct_from_moscow": row.direct_from_moscow,
            "transit_via_dubai": row.transit_via_dubai,
            "transit_via_istanbul": row.transit_via_istanbul,
            "transit_via_yerevan": row.transit_via_yerevan,
            "transit_via_tashkent": row.transit_via_tashkent,
            "transit_via_tbilisi": row.transit_via_tbilisi,
            "train_from_moscow": row.train_from_moscow,
            "min_transit_hours": row.min_transit_hours,
        }
        result[row.destination_id] = compute_score(record, excluded_hubs=list(excluded))
    return result
