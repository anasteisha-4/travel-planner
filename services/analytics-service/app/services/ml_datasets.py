from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.ml_dataset_snapshot import MLDatasetSnapshot

BUILDER_VERSION = "analytics-service-ml-datasets-v1"
CONTRACT_VERSION = "1"

RANKER_EVENTS = {
    "recommendation_impression": 0,
    "recommendation_clicked": 2,
    "destination_detail_opened": 2,
    "trip_created": 3,
    "post_trip_feedback_submitted": 3,
    "post_trip_feedback_updated": 3,
}

ITINERARY_EVENTS = [
    "itinerary_candidate_generated",
    "itinerary_generated",
    "itinerary_approved",
    "itinerary_regenerated",
    "itinerary_poi_moved",
    "itinerary_poi_removed",
    "itinerary_poi_added",
    "place_visit_marked_visited",
]


def build_ml_dataset_report(db: Session, date_from: datetime | None, date_to: datetime | None) -> dict[str, Any]:
    ranker = build_ranker_report(db, date_from, date_to)
    budget = build_budget_report(db, date_from, date_to)
    itinerary = build_itinerary_report(db, date_from, date_to)
    return {
        "builder_version": BUILDER_VERSION,
        "contract_version": CONTRACT_VERSION,
        "date_from": date_from.isoformat() if date_from else None,
        "date_to": date_to.isoformat() if date_to else None,
        "ranker": ranker,
        "budget": budget,
        "itinerary": itinerary,
        "readiness": {
            "ranker_behavioral_training_ready": ranker["thresholds"]["ready"],
            "budget_real_feedback_ready": budget["coverage"]["matched_predictions"] > 0,
            "itinerary_feedback_ready": itinerary["coverage"]["generated_candidates"] > 0,
        },
    }


def build_ranker_report(db: Session, date_from: datetime | None, date_to: datetime | None) -> dict[str, Any]:
    counts = _event_counts(db, list(RANKER_EVENTS), date_from, date_to)
    positives = sum(counts[event] for event, label in RANKER_EVENTS.items() if label > 0)
    recommendation_logs = _recommendation_log_summary(db, date_from, date_to)
    thresholds = {
        "min_impressions": 5000,
        "min_positive_actions": 500,
        "impressions": counts["recommendation_impression"],
        "positive_actions": positives,
    }
    thresholds["ready"] = (
        thresholds["impressions"] >= thresholds["min_impressions"]
        and thresholds["positive_actions"] >= thresholds["min_positive_actions"]
    )
    return {
        "label_policy": {
            "impression": 0,
            "click_or_detail": 2,
            "trip_created_or_feedback": 3,
        },
        "counterfactual_guardrails": [
            "keep rank, model_version, recommendation_id and exposure timestamp in every training row",
            "do not train on behavioral data until thresholds are met",
            "evaluate by query/session split before activating a model",
        ],
        "event_counts": counts,
        "recommendation_logs": recommendation_logs,
        "row_count": counts["recommendation_impression"],
        "positive_count": positives,
        "thresholds": thresholds,
    }


def build_budget_report(db: Session, date_from: datetime | None, date_to: datetime | None) -> dict[str, Any]:
    counts = _event_counts(
        db,
        [
            "budget_prediction_served",
            "budget_monitor_served",
            "post_trip_feedback_submitted",
            "post_trip_feedback_updated",
        ],
        date_from,
        date_to,
    )
    matched = _budget_prediction_error(db, date_from, date_to)
    risk_distribution = _context_value_counts(db, "budget_monitor_served", "risk_status", date_from, date_to)
    return {
        "currency_policy": {
            "canonical_currency": "USD",
            "actual_cost_requires_usd_or_explicit_fx_snapshot": True,
            "non_usd_feedback_is_excluded_from_error_until_fx_table_exists": True,
        },
        "event_counts": counts,
        "risk_distribution": risk_distribution,
        "coverage": matched["coverage"],
        "forecast_error": matched["forecast_error"],
        "row_count": matched["coverage"]["matched_predictions"],
        "positive_count": matched["coverage"]["actual_cost_feedback"],
    }


def build_itinerary_report(db: Session, date_from: datetime | None, date_to: datetime | None) -> dict[str, Any]:
    counts = _event_counts(db, ITINERARY_EVENTS, date_from, date_to)
    generated = counts["itinerary_candidate_generated"] or counts["itinerary_generated"]
    approved = counts["itinerary_approved"]
    edited = (
        counts["itinerary_regenerated"]
        + counts["itinerary_poi_moved"]
        + counts["itinerary_poi_removed"]
        + counts["itinerary_poi_added"]
    )
    visited = counts["place_visit_marked_visited"]
    return {
        "event_counts": counts,
        "label_policy": {
            "candidate_generated": "route exposure",
            "approved": "route-level positive",
            "edited": "route-level correction signal",
            "visited": "poi-level positive",
        },
        "coverage": {
            "generated_candidates": generated,
            "approved_routes": approved,
            "edited_routes": edited,
            "visited_poi_labels": visited,
        },
        "rates": {
            "approval_rate": _safe_rate(approved, generated),
            "edit_rate": _safe_rate(edited, generated),
            "visited_rate": _safe_rate(visited, generated),
        },
        "row_count": generated,
        "positive_count": approved + visited,
    }


def create_snapshot(
    db: Session,
    dataset_type: str,
    date_from: datetime | None,
    date_to: datetime | None,
    created_by_user_id: str,
) -> MLDatasetSnapshot:
    report = build_ml_dataset_report(db, date_from, date_to)
    selected = report.get(dataset_type) if dataset_type != "all" else _all_dataset_summary(report)
    if not isinstance(selected, dict):
        raise ValueError("Unsupported dataset type")
    snapshot = MLDatasetSnapshot(
        dataset_type=dataset_type,
        date_from=date_from,
        date_to=date_to,
        contract_version=CONTRACT_VERSION,
        builder_version=BUILDER_VERSION,
        row_count=int(selected.get("row_count") or 0),
        positive_count=int(selected.get("positive_count") or 0),
        metadata_json={
            "dataset_type": dataset_type,
            "event_versions": [CONTRACT_VERSION],
            "model_versions": report["ranker"]["recommendation_logs"].get("model_versions", {}),
            "thresholds": report["ranker"]["thresholds"],
        },
        sanity_report=selected,
        created_by_user_id=created_by_user_id,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


def _all_dataset_summary(report: dict[str, Any]) -> dict[str, Any]:
    datasets = [report["ranker"], report["budget"], report["itinerary"]]
    return {
        "builder_version": report["builder_version"],
        "contract_version": report["contract_version"],
        "date_from": report["date_from"],
        "date_to": report["date_to"],
        "readiness": report["readiness"],
        "ranker": report["ranker"],
        "budget": report["budget"],
        "itinerary": report["itinerary"],
        "row_count": sum(int(dataset.get("row_count") or 0) for dataset in datasets),
        "positive_count": sum(int(dataset.get("positive_count") or 0) for dataset in datasets),
    }


def _event_counts(
    db: Session, event_types: list[str], date_from: datetime | None, date_to: datetime | None
) -> dict[str, int]:
    params: dict[str, Any] = {"event_types": event_types}
    where = ["event_type = ANY(:event_types)"]
    if date_from:
        where.append("created_at >= :date_from")
        params["date_from"] = date_from
    if date_to:
        where.append("created_at < :date_to")
        params["date_to"] = date_to
    rows = db.execute(
        text(f"SELECT event_type, COUNT(*) AS count FROM user_events WHERE {' AND '.join(where)} GROUP BY event_type"),
        params,
    ).mappings()
    counts = {event_type: 0 for event_type in event_types}
    for row in rows:
        counts[str(row["event_type"])] = int(row["count"])
    return counts


def _context_value_counts(
    db: Session, event_type: str, context_key: str, date_from: datetime | None, date_to: datetime | None
) -> dict[str, int]:
    params: dict[str, Any] = {"event_type": event_type, "context_key": context_key}
    where = ["event_type = :event_type"]
    if date_from:
        where.append("created_at >= :date_from")
        params["date_from"] = date_from
    if date_to:
        where.append("created_at < :date_to")
        params["date_to"] = date_to
    rows = db.execute(
        text(
            "SELECT COALESCE(context ->> :context_key, 'unknown') AS value, COUNT(*) AS count "
            "FROM user_events "
            f"WHERE {' AND '.join(where)} "
            "GROUP BY value"
        ),
        params,
    ).mappings()
    return {str(row["value"]): int(row["count"]) for row in rows}


def _budget_prediction_error(db: Session, date_from: datetime | None, date_to: datetime | None) -> dict[str, Any]:
    params: dict[str, Any] = {}
    where = ["e.event_type = 'budget_prediction_served'", "f.actual_total_cost IS NOT NULL"]
    if date_from:
        where.append("e.created_at >= :date_from")
        params["date_from"] = date_from
    if date_to:
        where.append("e.created_at < :date_to")
        params["date_to"] = date_to
    rows = (
        db.execute(
            text(
                "SELECT "
                "COUNT(*) AS matched_predictions, "
                "COUNT(*) FILTER (WHERE f.actual_currency IS NULL OR f.actual_currency = 'USD') AS usd_feedback, "
                "AVG(ABS((e.context ->> 'p50')::numeric - f.actual_total_cost)) "
                "FILTER (WHERE (e.context ? 'p50') AND (f.actual_currency IS NULL OR f.actual_currency = 'USD')) AS mae_p50, "
                "AVG(ABS(((e.context ->> 'p50')::numeric - f.actual_total_cost) / NULLIF(f.actual_total_cost, 0))) "
                "FILTER (WHERE (e.context ? 'p50') AND (f.actual_currency IS NULL OR f.actual_currency = 'USD')) AS mape_p50, "
                "COUNT(*) FILTER (WHERE (e.context ? 'p10') AND (e.context ? 'p90') "
                "AND f.actual_total_cost BETWEEN (e.context ->> 'p10')::numeric AND (e.context ->> 'p90')::numeric "
                "AND (f.actual_currency IS NULL OR f.actual_currency = 'USD')) AS inside_interval "
                "FROM user_events e "
                "JOIN post_trip_feedback f ON f.trip_id = e.context ->> 'trip_id' "
                f"WHERE {' AND '.join(where)}"
            ),
            params,
        )
        .mappings()
        .one()
    )
    matched = int(rows["matched_predictions"] or 0)
    usd_feedback = int(rows["usd_feedback"] or 0)
    return {
        "coverage": {
            "matched_predictions": matched,
            "actual_cost_feedback": usd_feedback,
            "excluded_non_usd_feedback": max(matched - usd_feedback, 0),
            "inside_p10_p90": int(rows["inside_interval"] or 0),
            "inside_p10_p90_rate": _safe_rate(int(rows["inside_interval"] or 0), usd_feedback),
        },
        "forecast_error": {
            "mae_p50_usd": float(rows["mae_p50"]) if rows["mae_p50"] is not None else None,
            "mape_p50": float(rows["mape_p50"]) if rows["mape_p50"] is not None else None,
        },
    }


def _recommendation_log_summary(db: Session, date_from: datetime | None, date_to: datetime | None) -> dict[str, Any]:
    if not _table_exists(db, "recommendation_logs"):
        return {"available": False, "rows": 0, "model_versions": {}, "candidate_rows": 0}
    params: dict[str, Any] = {}
    where = ["TRUE"]
    if date_from:
        where.append("created_at >= :date_from")
        params["date_from"] = date_from
    if date_to:
        where.append("created_at < :date_to")
        params["date_to"] = date_to
    rows = db.execute(
        text(
            "SELECT model_version, COUNT(*) AS count, COALESCE(SUM(jsonb_array_length(results)), 0) AS candidates "
            "FROM recommendation_logs "
            f"WHERE {' AND '.join(where)} "
            "GROUP BY model_version"
        ),
        params,
    ).mappings()
    model_versions: dict[str, int] = {}
    candidate_rows = 0
    for row in rows:
        model_versions[str(row["model_version"])] = int(row["count"])
        candidate_rows += int(row["candidates"] or 0)
    return {
        "available": True,
        "rows": sum(model_versions.values()),
        "model_versions": model_versions,
        "candidate_rows": candidate_rows,
    }


def _table_exists(db: Session, table_name: str) -> bool:
    return bool(db.execute(text("SELECT to_regclass(:table_name)"), {"table_name": table_name}).scalar())


def _safe_rate(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return round(numerator / denominator, 4)
