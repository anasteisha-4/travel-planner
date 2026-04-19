"""Destination recommendation engine using pre-computed feature scores."""

from sqlalchemy.orm import Session


def _percentile_rank(value: float, all_values: list[float]) -> float:
    """Return fraction of values strictly below `value` (percentile rank in [0, 1])."""
    if not all_values:
        return 0.5
    return sum(1 for v in all_values if v < value) / len(all_values)


def recommend_destinations(
    db: Session,
    citizenship_code: str,
    travel_month: int,
    budget_per_day_usd: float,
    preferred_activities: list[str],
    excluded_hubs: list[str] | None = None,
    limit: int = 10,
) -> list[dict]:
    from app.models import (
        Destination,
        DestinationActivity,
        DestinationCosts,
        DestinationPopularity,
        DestinationSafety,
        DestinationSeasonality,
        VisaRule,
    )
    from app.services.connectivity_service import get_connectivity_scores

    destinations = db.query(Destination).filter(Destination.is_active == True).all()  # noqa: E712

    # Pre-load all feature data for efficiency
    dest_ids = [d.id for d in destinations]

    safety_map = {
        r.destination_id: r.safety_score
        for r in db.query(DestinationSafety)
        .filter(DestinationSafety.destination_id.in_(dest_ids))
        .all()
    }
    costs_map = {
        r.destination_id: r
        for r in db.query(DestinationCosts)
        .filter(DestinationCosts.destination_id.in_(dest_ids))
        .all()
    }
    season_map = {
        (r.destination_id, r.month): r.season_score
        for r in db.query(DestinationSeasonality)
        .filter(
            DestinationSeasonality.destination_id.in_(dest_ids),
            DestinationSeasonality.month == travel_month,
        )
        .all()
    }
    visa_map = {
        r.destination_id: r.visa_score
        for r in db.query(VisaRule)
        .filter(
            VisaRule.destination_id.in_(dest_ids),
            VisaRule.citizenship_code == citizenship_code.upper(),
        )
        .all()
    }
    crowd_map = {
        r.destination_id: r.crowd_index
        for r in db.query(DestinationPopularity)
        .filter(
            DestinationPopularity.destination_id.in_(dest_ids),
            DestinationPopularity.month == travel_month,
        )
        .all()
    }
    connectivity_map = get_connectivity_scores(
        db, dest_ids, excluded_hubs=excluded_hubs
    )

    # Load activity scores for all destinations (for percentile normalization)
    # When preferred_activities given — use only those types; otherwise use all
    activity_rows = (
        db.query(DestinationActivity)
        .filter(
            DestinationActivity.destination_id.in_(dest_ids),
            *(
                [DestinationActivity.activity_type.in_(preferred_activities)]
                if preferred_activities
                else []
            ),
        )
        .all()
    )

    # Per-destination: average raw score across requested activity types
    raw_activity_map: dict = {}
    for r in activity_rows:
        raw_activity_map.setdefault(r.destination_id, []).append(r.score)
    avg_raw_map = {
        dest_id: sum(scores) / len(scores)
        for dest_id, scores in raw_activity_map.items()
    }

    # Build global distribution for percentile ranking (removes tanh saturation)
    global_activity_values = list(avg_raw_map.values())

    # Determine user budget index (normalize against global max cost ~ $500/day)
    GLOBAL_BUDGET_MAX = 500.0
    user_budget_index = min(budget_per_day_usd / GLOBAL_BUDGET_MAX, 1.0)

    scored = []
    for dest in destinations:
        safety = safety_map.get(dest.id, 0.5)
        season = season_map.get((dest.id, travel_month), 0.5)
        visa = visa_map.get(dest.id, 0.2)  # default: visa required
        crowd = crowd_map.get(dest.id, 0.5)
        connectivity = connectivity_map.get(dest.id, 0.0)
        costs_row = costs_map.get(dest.id)
        cost_distance = abs(
            (costs_row.cost_index if costs_row else 0.5) - user_budget_index
        )

        # Percentile rank replaces raw tanh-saturated score → full [0,1] spread
        raw_activity = avg_raw_map.get(dest.id)
        if raw_activity is not None:
            activity = _percentile_rank(raw_activity, global_activity_values)
        else:
            activity = 0.5

        composite = (
            0.22 * season
            + 0.18 * visa
            + 0.18 * safety
            + 0.16 * activity
            + 0.14 * connectivity
            + 0.08 * (1.0 - cost_distance)
            + 0.04 * (1.0 - crowd)
        )
        scored.append(
            {
                "id": str(dest.id),
                "name": dest.name,
                "country_code": dest.country_code,
                "region": dest.region,
                "score": round(composite, 4),
                "season_score": round(season, 4),
                "visa_score": round(visa, 4),
                "safety_score": round(safety, 4),
                "activity_score": round(activity, 4),
                "connectivity_score": round(connectivity, 4),
                "crowd_index": round(crowd, 4),
                "avg_daily_cost_usd": costs_row.avg_daily_cost_usd
                if costs_row
                else None,
            }
        )

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:limit]
