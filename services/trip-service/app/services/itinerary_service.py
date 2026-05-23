import hashlib
import math
import random
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from uuid import UUID

import httpx
from sqlalchemy import nulls_last
from sqlalchemy.orm import Session

from app import models, schemas
from app.config import settings
from app.database import SessionLocal
from app.exceptions import AppException
from app.services.analytics_events import emit_itinerary_quality_event
from app.services.place_service import _validate_coordinates
from app.services.push_service import send_push_to_user

MAX_ITINERARY_DAYS = 31


def _verify_trip_ownership(db: Session, trip_id: UUID, user_id: UUID) -> models.Trip:
    trip = db.query(models.Trip).filter(models.Trip.id == trip_id, models.Trip.user_id == user_id).first()
    if not trip:
        raise AppException(status_code=404, code="NOT_FOUND", message="Trip not found")
    return trip


def _verify_itinerary_ownership(db: Session, itinerary_id: UUID, user_id: UUID) -> models.TripItinerary:
    itinerary = (
        db.query(models.TripItinerary)
        .filter(models.TripItinerary.id == itinerary_id, models.TripItinerary.user_id == user_id)
        .first()
    )
    if not itinerary:
        raise AppException(status_code=404, code="NOT_FOUND", message="Itinerary not found")
    return itinerary


def _verify_item_ownership(db: Session, item_id: UUID, user_id: UUID) -> models.TripItineraryItem:
    item = (
        db.query(models.TripItineraryItem)
        .filter(models.TripItineraryItem.id == item_id, models.TripItineraryItem.user_id == user_id)
        .first()
    )
    if not item:
        raise AppException(status_code=404, code="NOT_FOUND", message="Itinerary item not found")
    return item


def _duration_days(trip: models.Trip) -> int:
    return max(1, (trip.end_date - trip.start_date).days + 1)


def _validate_generation_duration(trip: models.Trip) -> None:
    if _duration_days(trip) > MAX_ITINERARY_DAYS:
        raise AppException(
            status_code=422,
            code="ITINERARY_DURATION_TOO_LONG",
            message="Itinerary generation supports trips up to 31 days.",
        )


def _rest_days_count(trip: models.Trip, requested: int | None = None) -> int:
    value = trip.rest_days_count if requested is None else requested
    return max(0, min(int(value or 0), _duration_days(trip)))


def _time_from_iso(value: str | None) -> time | None:
    if not value:
        return None
    return time.fromisoformat(value[:5])


def _time_to_minutes(value: time) -> int:
    return value.hour * 60 + value.minute


def _time_with_delta(value: time, delta_minutes: int) -> time:
    minutes = _time_to_minutes(value) + delta_minutes
    if minutes < 0 or minutes >= 24 * 60:
        raise AppException(
            status_code=400, code="INVALID_TIME_WINDOW", message="Itinerary item time is out of day bounds"
        )
    return time(hour=minutes // 60, minute=minutes % 60)


def _time_from_minutes(minutes: int) -> time:
    if minutes < 0 or minutes >= 24 * 60:
        raise AppException(
            status_code=400, code="INVALID_TIME_WINDOW", message="Itinerary item time is out of day bounds"
        )
    return time(hour=minutes // 60, minute=minutes % 60)


def _haversine_km(lat1: Decimal, lng1: Decimal, lat2: Decimal, lng2: Decimal) -> float:
    radius_km = 6371.0
    phi1 = math.radians(float(lat1))
    phi2 = math.radians(float(lat2))
    d_phi = math.radians(float(lat2) - float(lat1))
    d_lambda = math.radians(float(lng2) - float(lng1))
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return radius_km * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _estimate_travel_minutes(
    previous: models.TripItineraryItem | None,
    current: models.TripItineraryItem,
) -> int:
    if previous is None:
        return 0
    if previous.latitude is None or previous.longitude is None or current.latitude is None or current.longitude is None:
        return max(0, int(current.travel_from_previous_minutes or 20))
    distance = _haversine_km(previous.latitude, previous.longitude, current.latitude, current.longitude)
    return max(5, min(75, int(distance / 20 * 60) + 5))


def _decimal(value: object) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


def _signature(days: list[dict]) -> str:
    poi_ids = [
        str(item.get("poi_id") or item.get("id") or "")
        for day in days
        for item in day.get("items", day.get("places", []))
        if item.get("poi_id") or item.get("id")
    ]
    return hashlib.sha1("|".join(poi_ids).encode("utf-8")).hexdigest()[:24]


def _route_score_summary(variant: dict, days_payload: list[dict]) -> dict:
    summary = dict(variant.get("score_summary") or variant.get("stats") or {})
    items = [item for day in days_payload for item in day.get("items", day.get("places", []))]
    summary.setdefault("total_pois", len(items))
    summary.setdefault(
        "travel_overhead_minutes",
        sum(max(0, int(item.get("travel_from_previous_minutes") or 0)) for item in items),
    )
    return summary


def _normalized_days_for_trip(trip: models.Trip, days_payload: list[dict], constraints: dict) -> list[dict]:
    by_day: dict[int, dict] = {}
    for index, payload in enumerate(days_payload):
        day_number = int(payload.get("day_number") or payload.get("day") or index + 1)
        if 1 <= day_number <= _duration_days(trip) and day_number not in by_day:
            by_day[day_number] = payload

    return [
        by_day.get(
            day_number,
            {
                "day": day_number,
                "day_number": day_number,
                "theme": "free",
                "start_time": constraints.get("day_start_time"),
                "end_time": constraints.get("day_end_time"),
                "items": [],
            },
        )
        for day_number in range(1, _duration_days(trip) + 1)
    ]


def get_itinerary_state(db: Session, user_id: UUID, trip_id: UUID) -> schemas.ItineraryStateResponse:
    _verify_trip_ownership(db, trip_id, user_id)
    itineraries = (
        db.query(models.TripItinerary)
        .filter(models.TripItinerary.trip_id == trip_id, models.TripItinerary.user_id == user_id)
        .order_by(models.TripItinerary.created_at.desc())
        .all()
    )
    approved = next((item for item in itineraries if item.status == "approved"), None)
    drafts = [item for item in itineraries if item.status == "draft"][:3]
    latest_generation_job = (
        db.query(models.ItineraryGenerationJob)
        .filter(
            models.ItineraryGenerationJob.trip_id == trip_id,
            models.ItineraryGenerationJob.user_id == user_id,
        )
        .order_by(models.ItineraryGenerationJob.created_at.desc())
        .first()
    )
    generation_job = (
        latest_generation_job
        if latest_generation_job and latest_generation_job.status in {"queued", "running", "failed"}
        else None
    )
    return schemas.ItineraryStateResponse(
        approved=to_response(db, approved) if approved else None,
        drafts=[to_response(db, draft) for draft in drafts],
        generation_job=generation_job,
    )


def enqueue_itinerary_generation(
    db: Session,
    user_id: UUID,
    trip_id: UUID,
    data: schemas.ItineraryGenerateRequest | schemas.ItineraryRegenerateRequest,
    mode: str,
) -> models.ItineraryGenerationJob:
    trip = _verify_trip_ownership(db, trip_id, user_id)
    _validate_generation_duration(trip)
    active_job = (
        db.query(models.ItineraryGenerationJob)
        .filter(
            models.ItineraryGenerationJob.trip_id == trip_id,
            models.ItineraryGenerationJob.user_id == user_id,
            models.ItineraryGenerationJob.status.in_(("queued", "running")),
        )
        .order_by(models.ItineraryGenerationJob.created_at.desc())
        .first()
    )
    if active_job:
        return active_job

    job = models.ItineraryGenerationJob(
        trip_id=trip_id,
        user_id=user_id,
        status="queued",
        mode=mode,
        request_payload=data.model_dump(mode="json"),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def run_itinerary_generation_job(job_id: UUID, authorization: str | None) -> None:
    db = SessionLocal()
    try:
        job = db.query(models.ItineraryGenerationJob).filter(models.ItineraryGenerationJob.id == job_id).first()
        if not job or job.status not in {"queued", "running"}:
            return
        job.status = "running"
        job.started_at = datetime.now(UTC)
        db.commit()

        if job.mode == "regenerate":
            request = schemas.ItineraryRegenerateRequest.model_validate(job.request_payload)
        else:
            request = schemas.ItineraryGenerateRequest.model_validate(job.request_payload)

        itineraries = generate_itineraries(db, job.user_id, job.trip_id, request, authorization)
        responses = [to_response(db, item) for item in itineraries]
        for item in responses:
            emit_itinerary_quality_event(
                "itinerary_candidate_generated",
                {
                    "trip_id": str(job.trip_id),
                    "itinerary_id": str(item.id),
                    "template_version": item.model_version,
                    "ranker_version": item.model_version,
                    "days": len(item.days),
                    "places": sum(len(day.items) for day in item.days),
                    "route_signature": item.route_signature,
                    "variant_index": item.variant_index,
                    "regenerated": job.mode == "regenerate",
                },
                entity_type="itinerary",
                entity_id=item.id,
                authorization=authorization,
            )

        job.status = "completed"
        job.result_itinerary_ids = [str(item.id) for item in itineraries]
        job.completed_at = datetime.now(UTC)
        db.commit()
        send_push_to_user(
            db,
            job.user_id,
            {
                "title": "Маршрут готов",
                "body": "Мы собрали маршрут поездки. Можно посмотреть варианты и утвердить подходящий.",
                "url": f"/trips/{job.trip_id}/itinerary",
                "tag": f"itinerary-{job.trip_id}",
            },
        )
    except AppException as exc:
        job = db.query(models.ItineraryGenerationJob).filter(models.ItineraryGenerationJob.id == job_id).first()
        if job:
            job.status = "failed"
            job.error_code = exc.code
            job.error_message = exc.message
            job.completed_at = datetime.now(UTC)
            db.commit()
            send_push_to_user(
                db,
                job.user_id,
                {
                    "title": "Маршрут не собрался",
                    "body": "Поменяйте параметры или направление поездки и попробуйте ещё раз.",
                    "url": f"/trips/{job.trip_id}/itinerary",
                    "tag": f"itinerary-{job.trip_id}",
                },
            )
    except Exception as exc:
        job = db.query(models.ItineraryGenerationJob).filter(models.ItineraryGenerationJob.id == job_id).first()
        if job:
            job.status = "failed"
            job.error_code = "ITINERARY_UNAVAILABLE"
            job.error_message = "Itinerary generation failed"
            job.completed_at = datetime.now(UTC)
            db.commit()
        raise exc
    finally:
        db.close()


def generate_itineraries(
    db: Session,
    user_id: UUID,
    trip_id: UUID,
    data: schemas.ItineraryGenerateRequest | schemas.ItineraryRegenerateRequest,
    authorization: str | None,
) -> list[models.TripItinerary]:
    trip = _verify_trip_ownership(db, trip_id, user_id)
    _validate_generation_duration(trip)

    seed_base = random.randint(10_000, 9_999_999)
    has_approved_itinerary = (
        isinstance(data, schemas.ItineraryRegenerateRequest)
        and db.query(models.TripItinerary.id)
        .filter(
            models.TripItinerary.trip_id == trip_id,
            models.TripItinerary.user_id == user_id,
            models.TripItinerary.status == "approved",
        )
        .first()
        is not None
    )
    effective_variant_count = 1 if not trip.destination_id or has_approved_itinerary else data.variant_count
    payload = {
        "trip_id": str(trip.id),
        "destination_id": str(trip.destination_id) if trip.destination_id else None,
        "destination_text": trip.destination if not trip.destination_id else None,
        "duration_days": _duration_days(trip),
        "rest_days_count": _rest_days_count(trip, data.rest_days_count),
        "start_date": trip.start_date.isoformat(),
        "preferred_activities": data.preferred_activities,
        "variant_count": effective_variant_count,
        "variant_seed": seed_base,
        "pace": data.pace,
        "day_start_time": data.day_start_time.isoformat(timespec="minutes"),
        "day_end_time": data.day_end_time.isoformat(timespec="minutes"),
        "trip_budget": trip.budget,
        "currency": trip.currency,
        "people_count": trip.people_count,
        "trip_notes": trip.notes,
        "origin_city_name": trip.departure_city,
        "allow_external_route": data.allow_external_route or not trip.destination_id,
    }
    if isinstance(data, schemas.ItineraryRegenerateRequest):
        payload["exclude_signature"] = data.exclude_signature

    headers = {"Authorization": authorization} if authorization else {}
    try:
        response = httpx.post(
            f"{settings.ML_SERVICE_URL}/api/v1/itinerary",
            json=payload,
            headers=headers,
            timeout=settings.ML_SERVICE_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code
        try:
            error_payload = exc.response.json()
        except ValueError:
            error_payload = {}
        code = str(error_payload.get("error") or "ITINERARY_UNAVAILABLE")
        message = str(error_payload.get("message") or "Itinerary generation failed")
        raise AppException(status_code=status_code, code=code, message=message) from exc
    except httpx.HTTPError as exc:
        raise AppException(
            status_code=503, code="ITINERARY_UNAVAILABLE", message="Itinerary generation failed"
        ) from exc

    body = response.json()
    variants = body.get("variants") or [body]
    variants = [
        variant for variant in variants if _variant_has_required_active_days(trip, variant, payload["rest_days_count"])
    ]
    if _contains_external_llm_route(body, variants):
        effective_variant_count = 1
    if not variants:
        raise AppException(
            status_code=422,
            code="ITINERARY_NO_FEASIBLE_ROUTE",
            message="Could not build a route for the selected trip parameters.",
        )
    db.query(models.TripItinerary).filter(
        models.TripItinerary.trip_id == trip_id,
        models.TripItinerary.user_id == user_id,
        models.TripItinerary.status == "draft",
    ).update({"status": "archived"}, synchronize_session=False)

    created: list[models.TripItinerary] = []
    for index, variant in enumerate(variants[:effective_variant_count]):
        created.append(_persist_variant(db, user_id, trip, variant, index, seed_base + index, payload))
    if has_approved_itinerary and created:
        db.query(models.TripItinerary).filter(
            models.TripItinerary.trip_id == trip_id,
            models.TripItinerary.user_id == user_id,
            models.TripItinerary.status == "approved",
        ).update({"status": "archived"}, synchronize_session=False)
        created[0].status = "approved"
    db.commit()
    for item in created:
        db.refresh(item)
    return created


def _contains_external_llm_route(body: dict, variants: list[dict]) -> bool:
    candidates = [body, *variants]
    for variant in candidates:
        if not isinstance(variant, dict):
            continue
        score_summary = variant.get("score_summary") or {}
        if variant.get("source") == "llm-external-draft":
            return True
        if str(variant.get("model_version") or "").startswith("llm-external-route:"):
            return True
        if isinstance(score_summary, dict) and score_summary.get("external_route_used") is True:
            return True
    return False


def _variant_has_required_active_days(trip: models.Trip, variant: dict, rest_days_count: int) -> bool:
    days = variant.get("days") or []
    rest_days = {
        int(day.get("day_number") or day.get("day") or index + 1)
        for index, day in enumerate(days)
        if str(day.get("theme") or "").lower() == "rest"
    }
    if len(rest_days) != rest_days_count:
        return False

    required_day_numbers = set(range(1, _duration_days(trip) + 1)) - rest_days
    active_days_with_items = {
        int(day.get("day_number") or day.get("day") or index + 1)
        for index, day in enumerate(days)
        if int(day.get("day_number") or day.get("day") or index + 1) in required_day_numbers
        and len(day.get("items", day.get("places", []))) > 0
    }
    return active_days_with_items == required_day_numbers


def _persist_variant(
    db: Session,
    user_id: UUID,
    trip: models.Trip,
    variant: dict,
    index: int,
    seed: int,
    constraints: dict,
) -> models.TripItinerary:
    days_payload = _normalized_days_for_trip(trip, variant.get("days", []), constraints)
    itinerary = models.TripItinerary(
        trip_id=trip.id,
        user_id=user_id,
        status="draft",
        variant_index=index,
        generation_seed=int(variant.get("variant_seed") or seed),
        model_version=str(variant.get("model_version") or "heuristic-itinerary-v2"),
        route_signature=str(variant.get("route_signature") or _signature(days_payload)),
        constraints=constraints,
        score_summary=_route_score_summary(variant, days_payload),
    )
    db.add(itinerary)
    db.flush()

    for day_index, day_payload in enumerate(days_payload):
        day_number = int(day_payload.get("day_number") or day_payload.get("day") or day_index + 1)
        day = models.TripItineraryDay(
            itinerary_id=itinerary.id,
            date=trip.start_date + timedelta(days=day_number - 1),
            day_number=day_number,
            theme=day_payload.get("theme"),
            start_time=_time_from_iso(day_payload.get("start_time") or constraints.get("day_start_time")),
            end_time=_time_from_iso(day_payload.get("end_time") or constraints.get("day_end_time")),
        )
        db.add(day)
        db.flush()
        items = day_payload.get("items", day_payload.get("places", []))
        for order, item_payload in enumerate(items):
            is_external_candidate = bool(item_payload.get("external_candidate_source"))
            db.add(
                models.TripItineraryItem(
                    day_id=day.id,
                    user_id=user_id,
                    trip_id=trip.id,
                    poi_id=None
                    if is_external_candidate
                    else UUID(str(item_payload.get("poi_id") or item_payload.get("id"))),
                    name=str(item_payload.get("name") or item_payload.get("display_name") or "Place"),
                    category=item_payload.get("category"),
                    latitude=_decimal(item_payload.get("lat")),
                    longitude=_decimal(item_payload.get("lng")),
                    arrival_time=_time_from_iso(item_payload.get("arrival_time")),
                    departure_time=_time_from_iso(item_payload.get("departure_time")),
                    duration_minutes=item_payload.get("visit_duration_minutes") or item_payload.get("duration_minutes"),
                    travel_from_previous_minutes=int(item_payload.get("travel_from_previous_minutes") or 0),
                    source="external_candidate" if is_external_candidate else "generated",
                    opening_status=item_payload.get("opening_status"),
                    price_tier=item_payload.get("price_tier"),
                    entrance_fee_usd=item_payload.get("entrance_fee_usd"),
                    relevance_score=item_payload.get("score") or item_payload.get("relevance_score"),
                    order=order,
                )
            )
    return itinerary


def approve_itinerary(db: Session, user_id: UUID, trip_id: UUID, itinerary_id: UUID) -> models.TripItinerary:
    _verify_trip_ownership(db, trip_id, user_id)
    itinerary = _verify_itinerary_ownership(db, itinerary_id, user_id)
    if itinerary.trip_id != trip_id:
        raise AppException(status_code=404, code="NOT_FOUND", message="Itinerary not found")
    db.query(models.TripItinerary).filter(
        models.TripItinerary.trip_id == trip_id,
        models.TripItinerary.user_id == user_id,
        models.TripItinerary.status == "approved",
    ).update({"status": "archived"}, synchronize_session=False)
    itinerary.status = "approved"
    db.commit()
    db.refresh(itinerary)
    return itinerary


def update_item(db: Session, user_id: UUID, trip_id: UUID, item_id: UUID, data: schemas.ItineraryItemUpdate):
    _verify_trip_ownership(db, trip_id, user_id)
    item = _verify_item_ownership(db, item_id, user_id)
    if item.trip_id != trip_id:
        raise AppException(status_code=404, code="NOT_FOUND", message="Itinerary item not found")
    values = data.model_dump(exclude_unset=True)
    original_day_id = item.day_id
    original_arrival = item.arrival_time
    original_departure = item.departure_time
    original_duration = item.duration_minutes
    if data.day_id is not None:
        target_day = (
            db.query(models.TripItineraryDay)
            .join(models.TripItinerary)
            .filter(
                models.TripItineraryDay.id == data.day_id,
                models.TripItinerary.trip_id == trip_id,
                models.TripItinerary.user_id == user_id,
            )
            .first()
        )
        if not target_day:
            raise AppException(status_code=404, code="NOT_FOUND", message="Itinerary day not found")
    for field, value in values.items():
        setattr(item, field, value)
    if {"arrival_time", "departure_time", "duration_minutes", "day_id"} & values.keys():
        _normalize_item_time_change(
            db,
            item,
            values,
            original_day_id,
            original_arrival,
            original_departure,
            original_duration,
        )
    elif "order" in values:
        _recalculate_day_route(db, item.day_id)
    db.commit()
    db.refresh(item)
    return item


def swap_items(
    db: Session,
    user_id: UUID,
    trip_id: UUID,
    item_id: UUID,
    data: schemas.ItineraryItemSwapRequest,
) -> models.TripItinerary:
    _verify_trip_ownership(db, trip_id, user_id)
    source = _verify_item_ownership(db, item_id, user_id)
    target = _verify_item_ownership(db, data.target_item_id, user_id)
    if source.trip_id != trip_id or target.trip_id != trip_id or source.is_removed or target.is_removed:
        raise AppException(status_code=404, code="NOT_FOUND", message="Itinerary item not found")
    if source.id == target.id:
        return _itinerary_for_day(db, source.day_id, user_id)

    source_itinerary = _itinerary_for_day(db, source.day_id, user_id)
    target_itinerary = _itinerary_for_day(db, target.day_id, user_id)
    if source_itinerary.id != target_itinerary.id:
        raise AppException(status_code=400, code="ITINERARY_MISMATCH", message="Items belong to different itineraries")

    source_day_id = source.day_id
    target_day_id = target.day_id
    source_order = source.order
    target_order = target.order

    source.day_id = target_day_id
    source.order = target_order
    target.day_id = source_day_id
    target.order = source_order

    db.flush()
    _recalculate_day_route(db, source_day_id)
    if target_day_id != source_day_id:
        _recalculate_day_route(db, target_day_id)

    db.commit()
    db.refresh(source_itinerary)
    return source_itinerary


def move_item(
    db: Session,
    user_id: UUID,
    trip_id: UUID,
    item_id: UUID,
    data: schemas.ItineraryItemMoveRequest,
) -> models.TripItinerary:
    _verify_trip_ownership(db, trip_id, user_id)
    item = _verify_item_ownership(db, item_id, user_id)
    if item.trip_id != trip_id or item.is_removed:
        raise AppException(status_code=404, code="NOT_FOUND", message="Itinerary item not found")

    source_itinerary = _itinerary_for_day(db, item.day_id, user_id)
    target_itinerary = _itinerary_for_day(db, data.target_day_id, user_id)
    if source_itinerary.id != target_itinerary.id:
        raise AppException(status_code=400, code="ITINERARY_MISMATCH", message="Items belong to different itineraries")

    source_day_id = item.day_id
    target_day_id = data.target_day_id
    target_items = _ordered_active_day_items(db, target_day_id, exclude_item_id=item.id)
    insert_at = min(data.target_order, len(target_items))

    item.day_id = target_day_id
    target_items.insert(insert_at, item)
    for order, target_item in enumerate(target_items):
        target_item.day_id = target_day_id
        target_item.order = order

    if source_day_id != target_day_id:
        source_items = _ordered_active_day_items(db, source_day_id, exclude_item_id=item.id)
        for order, source_item in enumerate(source_items):
            source_item.order = order

    db.flush()
    _recalculate_day_route(db, source_day_id)
    if source_day_id != target_day_id:
        _recalculate_day_route(db, target_day_id)

    db.commit()
    db.refresh(source_itinerary)
    return source_itinerary


def _itinerary_for_day(db: Session, day_id: UUID, user_id: UUID) -> models.TripItinerary:
    itinerary = (
        db.query(models.TripItinerary)
        .join(models.TripItineraryDay, models.TripItineraryDay.itinerary_id == models.TripItinerary.id)
        .filter(models.TripItineraryDay.id == day_id, models.TripItinerary.user_id == user_id)
        .first()
    )
    if not itinerary:
        raise AppException(status_code=404, code="NOT_FOUND", message="Itinerary not found")
    return itinerary


def _ordered_active_day_items(
    db: Session,
    day_id: UUID,
    exclude_item_id: UUID | None = None,
) -> list[models.TripItineraryItem]:
    query = db.query(models.TripItineraryItem).filter(
        models.TripItineraryItem.day_id == day_id,
        models.TripItineraryItem.is_removed.is_(False),
    )
    if exclude_item_id is not None:
        query = query.filter(models.TripItineraryItem.id != exclude_item_id)
    return query.order_by(models.TripItineraryItem.order.asc(), models.TripItineraryItem.created_at.asc()).all()


def _normalize_item_time_change(
    db: Session,
    item: models.TripItineraryItem,
    values: dict,
    original_day_id: UUID,
    old_arrival: time | None,
    old_departure: time | None,
    old_duration: int | None,
) -> None:
    if item.day_id != original_day_id:
        _recalculate_day_from_order(db, original_day_id, None)
        _recalculate_day_from_order(db, item.day_id, item)
        return

    if old_arrival is None and item.arrival_time is None:
        return

    if "arrival_time" in values and "departure_time" not in values and old_arrival and old_departure:
        delta = _time_to_minutes(item.arrival_time) - _time_to_minutes(old_arrival)
        item.departure_time = _time_with_delta(old_departure, delta)
        item.duration_minutes = old_duration
    elif "duration_minutes" in values and item.arrival_time and item.duration_minutes:
        item.departure_time = _time_with_delta(item.arrival_time, item.duration_minutes)
    elif (
        "departure_time" in values
        and item.arrival_time
        and item.departure_time
        or item.arrival_time
        and item.departure_time
    ):
        item.duration_minutes = _time_to_minutes(item.departure_time) - _time_to_minutes(item.arrival_time)

    if (
        item.arrival_time
        and item.departure_time
        and _time_to_minutes(item.departure_time) <= _time_to_minutes(item.arrival_time)
    ):
        raise AppException(
            status_code=400, code="INVALID_TIME_WINDOW", message="Departure time must be after arrival time"
        )
    if item.duration_minutes is not None and item.duration_minutes <= 0:
        raise AppException(status_code=400, code="INVALID_TIME_WINDOW", message="Visit duration must be positive")

    if old_departure and item.departure_time:
        delta = _time_to_minutes(item.departure_time) - _time_to_minutes(old_departure)
        if delta:
            _shift_following_items(db, item, delta)


def _shift_following_items(db: Session, item: models.TripItineraryItem, delta_minutes: int) -> None:
    following_items = (
        db.query(models.TripItineraryItem)
        .filter(
            models.TripItineraryItem.day_id == item.day_id,
            models.TripItineraryItem.order > item.order,
            models.TripItineraryItem.is_removed.is_(False),
        )
        .order_by(models.TripItineraryItem.order.asc(), models.TripItineraryItem.created_at.asc())
        .all()
    )
    for following in following_items:
        if following.arrival_time:
            following.arrival_time = _time_with_delta(following.arrival_time, delta_minutes)
        if following.departure_time:
            following.departure_time = _time_with_delta(following.departure_time, delta_minutes)


def _recalculate_day_from_order(
    db: Session,
    day_id: UUID,
    anchor_item: models.TripItineraryItem | None,
) -> None:
    items = (
        db.query(models.TripItineraryItem)
        .filter(models.TripItineraryItem.day_id == day_id, models.TripItineraryItem.is_removed.is_(False))
        .order_by(models.TripItineraryItem.order.asc(), models.TripItineraryItem.created_at.asc())
        .all()
    )
    if not items:
        return

    previous_departure: time | None = None
    for current in items:
        if current is anchor_item:
            if current.arrival_time and current.duration_minutes and not current.departure_time:
                current.departure_time = _time_with_delta(current.arrival_time, current.duration_minutes)
        elif previous_departure and current.arrival_time and current.duration_minutes:
            current.arrival_time = _time_with_delta(previous_departure, current.travel_from_previous_minutes)
            current.departure_time = _time_with_delta(current.arrival_time, current.duration_minutes)
        elif current.arrival_time and current.duration_minutes and not current.departure_time:
            current.departure_time = _time_with_delta(current.arrival_time, current.duration_minutes)
        previous_departure = current.departure_time


def _recalculate_day_route(db: Session, day_id: UUID) -> None:
    day = db.query(models.TripItineraryDay).filter(models.TripItineraryDay.id == day_id).first()
    if not day:
        return
    items = (
        db.query(models.TripItineraryItem)
        .filter(models.TripItineraryItem.day_id == day_id, models.TripItineraryItem.is_removed.is_(False))
        .order_by(models.TripItineraryItem.order.asc(), models.TripItineraryItem.created_at.asc())
        .all()
    )
    if not items:
        return

    previous: models.TripItineraryItem | None = None
    previous_departure = day.start_time or items[0].arrival_time or time(9, 30)
    for order, current in enumerate(items):
        current.order = order
        travel_minutes = _estimate_travel_minutes(previous, current)
        current.travel_from_previous_minutes = travel_minutes
        current.arrival_time = (
            previous_departure if previous is None else _time_with_delta(previous_departure, travel_minutes)
        )
        current.duration_minutes = current.duration_minutes or 90
        current.departure_time = _time_with_delta(current.arrival_time, current.duration_minutes)
        previous = current
        previous_departure = current.departure_time


def add_manual_item(db: Session, user_id: UUID, trip_id: UUID, data: schemas.ItineraryManualItemCreate):
    _verify_trip_ownership(db, trip_id, user_id)
    if data.latitude is not None and data.longitude is not None:
        _validate_coordinates(data.latitude, data.longitude)
    day = (
        db.query(models.TripItineraryDay)
        .join(models.TripItinerary)
        .filter(
            models.TripItineraryDay.id == data.day_id,
            models.TripItinerary.trip_id == trip_id,
            models.TripItinerary.user_id == user_id,
        )
        .first()
    )
    if not day:
        raise AppException(status_code=404, code="NOT_FOUND", message="Itinerary day not found")
    max_order = (
        db.query(models.TripItineraryItem)
        .filter(models.TripItineraryItem.day_id == data.day_id)
        .order_by(models.TripItineraryItem.order.desc())
        .first()
    )
    item = models.TripItineraryItem(
        day_id=data.day_id,
        user_id=user_id,
        trip_id=trip_id,
        poi_id=data.poi_id,
        name=data.name,
        category=data.category,
        latitude=data.latitude,
        longitude=data.longitude,
        arrival_time=data.arrival_time,
        departure_time=data.departure_time,
        duration_minutes=data.duration_minutes,
        travel_from_previous_minutes=0,
        source="manual",
        order=(max_order.order + 1 if max_order else 0),
        is_pinned=True,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def remove_item(db: Session, user_id: UUID, trip_id: UUID, item_id: UUID) -> None:
    item = update_item(db, user_id, trip_id, item_id, schemas.ItineraryItemUpdate(is_removed=True))
    item.is_pinned = False
    db.commit()


def mark_item_visited(db: Session, user_id: UUID, trip_id: UUID, item_id: UUID) -> models.TripItineraryItem:
    trip = _verify_trip_ownership(db, trip_id, user_id)
    item = _verify_item_ownership(db, item_id, user_id)
    if item.trip_id != trip_id:
        raise AppException(status_code=404, code="NOT_FOUND", message="Itinerary item not found")
    if item.source == "external_candidate":
        raise AppException(
            status_code=400,
            code="CANDIDATE_POI_NOT_APPROVED",
            message="Candidate POI must be approved before marking it visited",
        )
    if item.visited_place_id:
        return item
    if item.latitude is None or item.longitude is None:
        raise AppException(status_code=400, code="INVALID_COORDINATES", message="Item has no coordinates")
    visit = models.PlaceVisit(
        user_id=user_id,
        trip_id=trip_id,
        name=item.name,
        visited_at=next_day_date(db, item) or trip.start_date,
        latitude=item.latitude,
        longitude=item.longitude,
        notes="Добавлено из маршрута Triply",
    )
    db.add(visit)
    db.flush()
    item.visited_place_id = visit.id
    db.commit()
    db.refresh(item)
    return item


def unmark_item_visited(db: Session, user_id: UUID, trip_id: UUID, item_id: UUID) -> models.TripItineraryItem:
    _verify_trip_ownership(db, trip_id, user_id)
    item = _verify_item_ownership(db, item_id, user_id)
    if item.trip_id != trip_id:
        raise AppException(status_code=404, code="NOT_FOUND", message="Itinerary item not found")
    if not item.visited_place_id:
        return item
    visit = (
        db.query(models.PlaceVisit)
        .filter(models.PlaceVisit.id == item.visited_place_id, models.PlaceVisit.user_id == user_id)
        .first()
    )
    item.visited_place_id = None
    if visit and (visit.notes is None or visit.notes == "Добавлено из маршрута Triply"):
        db.delete(visit)
    db.commit()
    db.refresh(item)
    return item


def next_day_date(db: Session, item: models.TripItineraryItem):
    day = db.query(models.TripItineraryDay).filter(models.TripItineraryDay.id == item.day_id).first()
    return day.date if day else None


def to_response(db: Session, itinerary: models.TripItinerary) -> schemas.ItineraryResponse:
    days = (
        db.query(models.TripItineraryDay)
        .filter(models.TripItineraryDay.itinerary_id == itinerary.id)
        .order_by(models.TripItineraryDay.day_number.asc())
        .all()
    )
    item_rows = (
        db.query(models.TripItineraryItem)
        .filter(models.TripItineraryItem.day_id.in_([day.id for day in days]))
        .order_by(nulls_last(models.TripItineraryItem.order.asc()), models.TripItineraryItem.created_at.asc())
        .all()
        if days
        else []
    )
    items_by_day: dict[UUID, list[models.TripItineraryItem]] = {}
    for item in item_rows:
        items_by_day.setdefault(item.day_id, []).append(item)
    score_summary = itinerary.score_summary or {}
    return schemas.ItineraryResponse(
        id=itinerary.id,
        trip_id=itinerary.trip_id,
        user_id=itinerary.user_id,
        status=itinerary.status,
        variant_index=itinerary.variant_index,
        generation_seed=itinerary.generation_seed,
        model_version=itinerary.model_version,
        route_signature=itinerary.route_signature,
        constraints=itinerary.constraints,
        score_summary=_public_score_summary(score_summary),
        quality_model_version=score_summary.get("llm_quality_model_version"),
        quality_review=None,
        candidate_poi=[],
        days=[_day_response(day, items_by_day.get(day.id, [])) for day in days],
        created_at=itinerary.created_at.isoformat() if itinerary.created_at else "",
        updated_at=itinerary.updated_at.isoformat() if itinerary.updated_at else None,
    )


def _day_response(
    day: models.TripItineraryDay,
    items: list[models.TripItineraryItem],
) -> schemas.ItineraryDayResponse:
    return schemas.ItineraryDayResponse(
        id=day.id,
        date=day.date,
        day_number=day.day_number,
        theme=day.theme,
        start_time=day.start_time,
        end_time=day.end_time,
        quality_review=None,
        items=[_item_response(item) for item in items],
    )


def _item_response(item: models.TripItineraryItem, item_reviews: dict | None = None) -> schemas.ItineraryItemResponse:
    return schemas.ItineraryItemResponse(
        id=item.id,
        day_id=item.day_id,
        poi_id=item.poi_id,
        name=item.name,
        category=item.category,
        latitude=item.latitude,
        longitude=item.longitude,
        arrival_time=item.arrival_time,
        departure_time=item.departure_time,
        duration_minutes=item.duration_minutes,
        travel_from_previous_minutes=item.travel_from_previous_minutes,
        source=item.source,
        opening_status=item.opening_status,
        price_tier=item.price_tier,
        entrance_fee_usd=item.entrance_fee_usd,
        relevance_score=item.relevance_score,
        order=item.order,
        is_pinned=item.is_pinned,
        is_removed=item.is_removed,
        visited_place_id=item.visited_place_id,
        quality_review=None,
        external_candidate_source=None,
        created_at=item.created_at.isoformat() if item.created_at else "",
        updated_at=item.updated_at.isoformat() if item.updated_at else None,
    )


def _public_score_summary(score_summary: dict) -> dict:
    return {
        key: value
        for key, value in score_summary.items()
        if not str(key).startswith("llm_quality")
        and key
        not in {
            "llm_candidate_poi",
            "llm_external_route_model",
            "external_route_prompt_version",
            "catalog_mutation_allowed",
        }
    }
