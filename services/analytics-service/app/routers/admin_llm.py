import json
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_admin_user_id
from app.exceptions import AppException

router = APIRouter(prefix="/api/v1/admin/llm", tags=["admin-llm"])


class CandidatePOIApprovePayload(BaseModel):
    comment: str | None = None
    name: str | None = None
    name_ru: str | None = None
    category: str | None = None
    lat: float | None = None
    lng: float | None = None
    address: str | None = None
    source_url: str | None = None
    official_url: str | None = None
    suggested_visit_duration_minutes: int | None = None
    opening_hours: str | None = None
    estimated_price: float | None = None
    estimated_price_currency: str | None = None
    price_source_url: str | None = None


class CandidateDestinationApprovePayload(BaseModel):
    comment: str | None = None
    name_ru: str | None = None
    region: str | None = None


@router.get("/candidate-poi")
def candidate_poi(
    status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    user_id=Depends(get_admin_user_id),
    db: Session = Depends(get_db),
):
    del user_id
    if not _table_exists(db, "llm_candidate_poi"):
        return {"items": []}
    where = "WHERE status = :status" if status else ""
    rows = db.execute(
        text(
            "SELECT id::text, destination_id::text, trip_id::text, itinerary_id, review_log_id::text, "
            "name, category, lat, lng, address, payload, status, approved_poi_id::text, "
            "reviewed_by_user_id, review_comment, NULL AS created_at, NULL AS updated_at "
            f"FROM llm_candidate_poi {where} "
            "ORDER BY id DESC "
            "LIMIT :limit"
        ),
        {"status": status, "limit": limit},
    ).mappings()
    return {"items": [_candidate_poi_to_dict(row) for row in rows]}


@router.get("/candidate-destination")
def candidate_destinations(
    status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    user_id=Depends(get_admin_user_id),
    db: Session = Depends(get_db),
):
    del user_id
    if not _table_exists(db, "llm_candidate_destinations"):
        return {"items": []}
    where = "WHERE status = :status" if status else ""
    rows = db.execute(
        text(
            "SELECT id::text, user_id::text, trip_id::text, review_log_id::text, name, country_code, "
            "country_name, region, lat, lng, payload, status, reviewed_by_user_id, review_comment, "
            "NULL AS created_at, NULL AS updated_at "
            f"FROM llm_candidate_destinations {where} "
            "ORDER BY id DESC "
            "LIMIT :limit"
        ),
        {"status": status, "limit": limit},
    ).mappings()
    return {"items": [_candidate_destination_to_dict(row) for row in rows]}


@router.get("/review-logs")
def review_logs(
    status: str | None = Query(default=None),
    entity_type: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    user_id=Depends(get_admin_user_id),
    db: Session = Depends(get_db),
):
    del user_id
    if not _table_exists(db, "llm_review_logs"):
        return {"items": []}

    filters: list[str] = []
    params: dict[str, Any] = {"limit": limit}
    if status:
        filters.append("status = :status")
        params["status"] = status
    if entity_type:
        filters.append("entity_type = :entity_type")
        params["entity_type"] = entity_type
    where = f"WHERE {' AND '.join(filters)}" if filters else ""
    rows = db.execute(
        text(
            "SELECT id::text, user_id::text, entity_type, entity_id, provider, model, prompt_version, "
            "status, latency_ms, issue_codes, cache_hit, error_code, NULL AS created_at "
            f"FROM llm_review_logs {where} "
            "ORDER BY id DESC "
            "LIMIT :limit"
        ),
        params,
    ).mappings()
    return {"items": [_review_log_to_dict(row) for row in rows]}


@router.post("/candidate-poi/{candidate_id}/approve")
def approve_candidate_poi(
    candidate_id: str,
    payload: CandidatePOIApprovePayload | None = None,
    user_id=Depends(get_admin_user_id),
    db: Session = Depends(get_db),
):
    candidate = _get_candidate_poi(db, candidate_id)
    approve_payload = payload or CandidatePOIApprovePayload()
    poi_id = candidate["approved_poi_id"]

    if not poi_id:
        poi_id = str(uuid.uuid4())
        name = _clean_text(approve_payload.name) or candidate["name"]
        category = _clean_text(approve_payload.category) or candidate["category"] or "attraction"
        lat = approve_payload.lat if approve_payload.lat is not None else candidate["lat"]
        lng = approve_payload.lng if approve_payload.lng is not None else candidate["lng"]
        destination_id = candidate["destination_id"]
        if not destination_id or lat is None or lng is None:
            raise AppException(
                status_code=400,
                code="CANDIDATE_POI_INCOMPLETE",
                message="Candidate needs destination_id, lat and lng before approval",
            )
        db.execute(
            text(
                "INSERT INTO poi (id, name, lat, lng, category, destination_id, source, external_id, "
                "rating, popularity_score, address, description, tags, visit_duration_minutes, opening_hours, "
                "price_tier, entrance_fee_usd, fee_notes, created_at, updated_at) "
                "VALUES (:id, :name, :lat, :lng, :category, :destination_id, 'llm_admin_approved', "
                ":external_id, NULL, 0.5, :address, :description, CAST(:tags AS jsonb), :visit_duration_minutes, "
                ":opening_hours, NULL, :entrance_fee_usd, :fee_notes, now(), now()) "
                "ON CONFLICT (source, external_id) DO UPDATE SET "
                "name = EXCLUDED.name, lat = EXCLUDED.lat, lng = EXCLUDED.lng, category = EXCLUDED.category, "
                "address = EXCLUDED.address, description = EXCLUDED.description, tags = EXCLUDED.tags, "
                "visit_duration_minutes = EXCLUDED.visit_duration_minutes, opening_hours = EXCLUDED.opening_hours, "
                "entrance_fee_usd = EXCLUDED.entrance_fee_usd, fee_notes = EXCLUDED.fee_notes, updated_at = now() "
                "RETURNING id::text"
            ),
            {
                "id": poi_id,
                "name": name,
                "lat": lat,
                "lng": lng,
                "category": category,
                "destination_id": destination_id,
                "external_id": f"llm:{candidate_id}",
                "address": _clean_text(approve_payload.address) or candidate["address"],
                "description": _clean_text(approve_payload.official_url)
                or _clean_text(approve_payload.source_url)
                or _clean_text((candidate["payload"] or {}).get("reason")),
                "tags": json.dumps(_poi_tags(candidate, approve_payload)),
                "visit_duration_minutes": approve_payload.suggested_visit_duration_minutes,
                "opening_hours": _clean_text(approve_payload.opening_hours),
                "entrance_fee_usd": approve_payload.estimated_price,
                "fee_notes": _fee_notes(approve_payload),
            },
        ).scalar_one()
        if approve_payload.name_ru and _table_exists(db, "name_translations"):
            _upsert_poi_translation(db, poi_id, name, approve_payload.name_ru, candidate_id)

    updated = _update_candidate_status(
        db,
        "llm_candidate_poi",
        candidate_id,
        "approved",
        str(user_id),
        approve_payload.comment,
        approved_poi_id=poi_id,
    )
    db.commit()
    return _candidate_poi_to_dict(updated)


@router.post("/candidate-poi/{candidate_id}/reject")
def reject_candidate_poi(
    candidate_id: str,
    user_id=Depends(get_admin_user_id),
    db: Session = Depends(get_db),
):
    updated = _update_candidate_status(db, "llm_candidate_poi", candidate_id, "rejected", str(user_id), None)
    db.commit()
    return _candidate_poi_to_dict(updated)


@router.post("/candidate-poi/{candidate_id}/needs-more-data")
def candidate_poi_needs_data(
    candidate_id: str,
    user_id=Depends(get_admin_user_id),
    db: Session = Depends(get_db),
):
    updated = _update_candidate_status(db, "llm_candidate_poi", candidate_id, "needs_data", str(user_id), None)
    db.commit()
    return _candidate_poi_to_dict(updated)


@router.post("/candidate-destination/{candidate_id}/approve")
def approve_candidate_destination(
    candidate_id: str,
    payload: CandidateDestinationApprovePayload | None = None,
    user_id=Depends(get_admin_user_id),
    db: Session = Depends(get_db),
):
    approve_payload = payload or CandidateDestinationApprovePayload()
    _get_candidate_destination(db, candidate_id)
    updated = _update_candidate_status(
        db,
        "llm_candidate_destinations",
        candidate_id,
        "approved",
        str(user_id),
        approve_payload.comment,
        extra_payload={"name_ru": approve_payload.name_ru, "region": approve_payload.region},
    )
    db.commit()
    return _candidate_destination_to_dict(updated)


@router.post("/candidate-destination/{candidate_id}/reject")
def reject_candidate_destination(
    candidate_id: str,
    user_id=Depends(get_admin_user_id),
    db: Session = Depends(get_db),
):
    updated = _update_candidate_status(db, "llm_candidate_destinations", candidate_id, "rejected", str(user_id), None)
    db.commit()
    return _candidate_destination_to_dict(updated)


@router.post("/candidate-destination/{candidate_id}/needs-more-data")
def candidate_destination_needs_data(
    candidate_id: str,
    user_id=Depends(get_admin_user_id),
    db: Session = Depends(get_db),
):
    updated = _update_candidate_status(db, "llm_candidate_destinations", candidate_id, "needs_data", str(user_id), None)
    db.commit()
    return _candidate_destination_to_dict(updated)


def _get_candidate_poi(db: Session, candidate_id: str):
    row = (
        db.execute(
            text(
                "SELECT id::text, destination_id::text, trip_id::text, itinerary_id, review_log_id::text, "
                "name, category, lat, lng, address, payload, status, approved_poi_id::text, "
                "reviewed_by_user_id, review_comment, NULL AS created_at, NULL AS updated_at "
                "FROM llm_candidate_poi WHERE id::text = :candidate_id"
            ),
            {"candidate_id": candidate_id},
        )
        .mappings()
        .one_or_none()
    )
    if not row:
        raise AppException(status_code=404, code="CANDIDATE_NOT_FOUND", message="LLM POI candidate not found")
    return row


def _get_candidate_destination(db: Session, candidate_id: str):
    row = (
        db.execute(
            text(
                "SELECT id::text, user_id::text, trip_id::text, review_log_id::text, name, country_code, "
                "country_name, region, lat, lng, payload, status, reviewed_by_user_id, review_comment, "
                "NULL AS created_at, NULL AS updated_at "
                "FROM llm_candidate_destinations WHERE id::text = :candidate_id"
            ),
            {"candidate_id": candidate_id},
        )
        .mappings()
        .one_or_none()
    )
    if not row:
        raise AppException(status_code=404, code="CANDIDATE_NOT_FOUND", message="LLM destination candidate not found")
    return row


def _update_candidate_status(
    db: Session,
    table_name: str,
    candidate_id: str,
    status: str,
    user_id: str,
    comment: str | None,
    approved_poi_id: str | None = None,
    extra_payload: dict[str, Any] | None = None,
):
    if table_name not in {"llm_candidate_poi", "llm_candidate_destinations"}:
        raise ValueError("Unsupported candidate table")
    payload_sql = ""
    params: dict[str, Any] = {
        "candidate_id": candidate_id,
        "status": status,
        "user_id": user_id,
        "comment": comment,
    }
    if approved_poi_id is not None:
        payload_sql += ", approved_poi_id = :approved_poi_id"
        params["approved_poi_id"] = approved_poi_id
    if extra_payload:
        payload_sql += ", payload = COALESCE(payload, '{}'::jsonb) || CAST(:extra_payload AS jsonb)"
        params["extra_payload"] = json.dumps({key: value for key, value in extra_payload.items() if value is not None})
    updated_id = db.execute(
        text(
            f"UPDATE {table_name} SET status = :status, reviewed_by_user_id = :user_id, "
            f"review_comment = COALESCE(:comment, review_comment) {payload_sql} "
            "WHERE id::text = :candidate_id "
            "RETURNING id::text"
        ),
        params,
    ).scalar_one_or_none()
    if not updated_id:
        raise AppException(status_code=404, code="CANDIDATE_NOT_FOUND", message="LLM candidate not found")
    return (
        _get_candidate_poi(db, updated_id)
        if table_name == "llm_candidate_poi"
        else _get_candidate_destination(db, updated_id)
    )


def _upsert_poi_translation(
    db: Session, poi_id: str, original_name: str, translated_name: str, candidate_id: str
) -> None:
    db.execute(
        text(
            "INSERT INTO name_translations (id, entity_type, entity_id, locale, original_name, translated_name, "
            "provider, provider_ref, quality, confidence, translation_metadata, created_at, updated_at) "
            "VALUES (:id, 'poi', :entity_id, 'ru', :original_name, :translated_name, 'llm_admin_review', "
            ":provider_ref, 'manual', 1.0, CAST(:metadata AS jsonb), now(), now()) "
            "ON CONFLICT (entity_type, entity_id, locale) DO UPDATE SET "
            "translated_name = EXCLUDED.translated_name, provider = EXCLUDED.provider, "
            "provider_ref = EXCLUDED.provider_ref, quality = EXCLUDED.quality, confidence = EXCLUDED.confidence, "
            "translation_metadata = EXCLUDED.translation_metadata, updated_at = now()"
        ),
        {
            "id": str(uuid.uuid4()),
            "entity_id": poi_id,
            "original_name": original_name,
            "translated_name": translated_name.strip(),
            "provider_ref": candidate_id,
            "metadata": json.dumps({"source": "admin_llm_candidate_poi"}),
        },
    )


def _poi_tags(candidate, payload: CandidatePOIApprovePayload) -> list[dict]:
    source_payload = candidate["payload"] or {}
    tags: list[dict] = [{"llm_admin_approved": True}]
    for key in ["source_url", "official_url", "price_source_url"]:
        value = getattr(payload, key, None) or source_payload.get(key)
        if value:
            tags.append({key: value})
    return tags


def _fee_notes(payload: CandidatePOIApprovePayload) -> str | None:
    parts = []
    if payload.estimated_price_currency:
        parts.append(f"currency={payload.estimated_price_currency}")
    if payload.price_source_url:
        parts.append(f"source={payload.price_source_url}")
    return "; ".join(parts) or None


def _candidate_poi_to_dict(row) -> dict:
    return {
        "id": row["id"],
        "destination_id": row["destination_id"],
        "trip_id": row["trip_id"],
        "itinerary_id": row["itinerary_id"],
        "review_log_id": row["review_log_id"],
        "name": row["name"],
        "category": row["category"],
        "lat": row["lat"],
        "lng": row["lng"],
        "address": row["address"],
        "payload": row["payload"] or {},
        "status": row["status"],
        "approved_poi_id": row["approved_poi_id"],
        "reviewed_by_user_id": row["reviewed_by_user_id"],
        "review_comment": row["review_comment"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
    }


def _candidate_destination_to_dict(row) -> dict:
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "trip_id": row["trip_id"],
        "review_log_id": row["review_log_id"],
        "name": row["name"],
        "country_code": row["country_code"],
        "country_name": row["country_name"],
        "region": row["region"],
        "lat": row["lat"],
        "lng": row["lng"],
        "payload": row["payload"] or {},
        "status": row["status"],
        "reviewed_by_user_id": row["reviewed_by_user_id"],
        "review_comment": row["review_comment"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
    }


def _review_log_to_dict(row) -> dict:
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "entity_type": row["entity_type"],
        "entity_id": row["entity_id"],
        "provider": row["provider"],
        "model": row["model"],
        "prompt_version": row["prompt_version"],
        "status": row["status"],
        "latency_ms": row["latency_ms"],
        "issue_codes": row["issue_codes"] or [],
        "cache_hit": bool(row["cache_hit"]),
        "error_code": row["error_code"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
    }


def _table_exists(db: Session, table_name: str) -> bool:
    return bool(db.execute(text("SELECT to_regclass(:table_name)"), {"table_name": table_name}).scalar())


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None
