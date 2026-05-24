import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas.itinerary import ItineraryGenerateResponse, ItineraryPlace
from app.schemas.llm_quality import LLMCandidatePOI, LLMQualityReview, LLMReviewAction
from app.services.llm.candidate_poi_validation import CandidatePOIValidationResult, validate_candidate_poi


@dataclass
class ItineraryAdjustmentResult:
    itinerary: ItineraryGenerateResponse
    applied_adjustments: list[dict] = field(default_factory=list)
    ignored_adjustments: list[dict] = field(default_factory=list)
    candidate_results: list[CandidatePOIValidationResult] = field(default_factory=list)


def apply_itinerary_quality_review(
    itinerary: ItineraryGenerateResponse,
    review: LLMQualityReview,
    *,
    db: Session,
) -> ItineraryAdjustmentResult:
    adjusted = itinerary
    applied: list[dict] = []
    ignored: list[dict] = []
    candidate_results: list[CandidatePOIValidationResult] = []
    removed_targets: set[uuid.UUID] = set()

    for issue in review.issues:
        target_id = issue.item_id or issue.target_id
        if issue.severity.value in {"critical", "warning"} and target_id:
            adjusted, did_apply = _remove_item(adjusted, target_id, min_active_day_places=0)
            _record(applied, ignored, did_apply, "remove", target_id, reason=f"{issue.severity.value}_issue")
            if did_apply:
                removed_targets.add(target_id)

    for adjustment in review.suggested_adjustments:
        if adjustment.target_id in removed_targets:
            continue
        if adjustment.action == LLMReviewAction.remove and adjustment.target_id:
            adjusted, did_apply = _remove_item(adjusted, adjustment.target_id)
            _record(applied, ignored, did_apply, "remove", adjustment.target_id)
            if did_apply:
                removed_targets.add(adjustment.target_id)
        elif (
            adjustment.action == LLMReviewAction.replace_item and adjustment.target_id and not adjustment.candidate_poi
        ):
            adjusted, did_apply = _remove_item(adjusted, adjustment.target_id)
            _record(applied, ignored, did_apply, "replace_item", adjustment.target_id)
            if did_apply:
                removed_targets.add(adjustment.target_id)
        elif adjustment.action == LLMReviewAction.swap and adjustment.target_id and adjustment.replacement_id:
            adjusted, did_apply = _swap_items(adjusted, adjustment.target_id, adjustment.replacement_id)
            _record(
                applied,
                ignored,
                did_apply,
                "swap",
                adjustment.target_id,
                replacement_id=adjustment.replacement_id,
            )
        elif adjustment.action == LLMReviewAction.add_candidate_poi and adjustment.candidate_poi:
            result = validate_candidate_poi(
                adjustment.candidate_poi,
                duplicate_warnings=_candidate_duplicate_warnings(
                    db=db,
                    itinerary=adjusted,
                    candidate=adjustment.candidate_poi,
                ),
            )
            candidate_results.append(result)
            if result.display_allowed:
                adjusted, did_apply = _add_candidate(
                    adjusted, adjustment.target_day or 1, adjustment.target_order, result
                )
                _record(applied, ignored, did_apply, "add_candidate_poi", None)
            else:
                reason = (
                    "duplicate_candidate"
                    if "catalog_duplicate" in result.rejection_reasons or "route_duplicate" in result.rejection_reasons
                    else "candidate_needs_data"
                )
                ignored.append({"action": "add_candidate_poi", "reason": reason})
        else:
            ignored.append({"action": adjustment.action.value, "reason": "unsupported_or_missing_target"})

    return ItineraryAdjustmentResult(
        itinerary=adjusted,
        applied_adjustments=applied,
        ignored_adjustments=ignored,
        candidate_results=candidate_results,
    )


def _remove_item(
    itinerary: ItineraryGenerateResponse,
    target_id: uuid.UUID,
    *,
    min_active_day_places: int = 2,
) -> tuple[ItineraryGenerateResponse, bool]:
    days = []
    did_apply = False
    kept_first_match = False
    total_matches = sum(1 for day in itinerary.days for place in day.places if place.id == target_id)
    for day in itinerary.days:
        places = []
        removed_from_day = False
        is_active_day = str(day.theme or "").lower() != "rest"
        matching_count = sum(1 for place in day.places if place.id == target_id)
        for place in day.places:
            if place.id != target_id:
                places.append(place)
                continue
            if total_matches > 1 and not kept_first_match:
                places.append(place)
                kept_first_match = True
                continue
            if is_active_day and len(day.places) - matching_count < min_active_day_places:
                places.append(place)
                continue
            removed_from_day = True
        did_apply = did_apply or removed_from_day
        days.append(day.model_copy(update={"places": places, "items": places}))
    return itinerary.model_copy(update={"days": days}), did_apply


def _swap_items(
    itinerary: ItineraryGenerateResponse,
    target_id: uuid.UUID,
    replacement_id: uuid.UUID,
) -> tuple[ItineraryGenerateResponse, bool]:
    positions: dict[uuid.UUID, tuple[int, int, ItineraryPlace]] = {}
    for day_index, day in enumerate(itinerary.days):
        for place_index, place in enumerate(day.places):
            if place.id in {target_id, replacement_id}:
                positions[place.id] = (day_index, place_index, place)
    if target_id not in positions or replacement_id not in positions:
        return itinerary, False

    first_day_index, first_place_index, first_place = positions[target_id]
    second_day_index, second_place_index, second_place = positions[replacement_id]
    days = [day.model_copy(update={"places": list(day.places), "items": list(day.places)}) for day in itinerary.days]
    days[first_day_index].places[first_place_index] = _place_in_time_slot(
        second_place,
        arrival_time=first_place.arrival_time,
        departure_time=first_place.departure_time,
        travel_from_previous_minutes=first_place.travel_from_previous_minutes,
    )
    days[second_day_index].places[second_place_index] = _place_in_time_slot(
        first_place,
        arrival_time=second_place.arrival_time,
        departure_time=second_place.departure_time,
        travel_from_previous_minutes=second_place.travel_from_previous_minutes,
    )
    return itinerary.model_copy(update={"days": [day.model_copy(update={"items": day.places}) for day in days]}), True


def _place_in_time_slot(
    place: ItineraryPlace,
    *,
    arrival_time: str | None,
    departure_time: str | None,
    travel_from_previous_minutes: int,
) -> ItineraryPlace:
    return place.model_copy(
        update={
            "arrival_time": arrival_time,
            "departure_time": departure_time,
            "travel_from_previous_minutes": travel_from_previous_minutes,
        }
    )


def _add_candidate(
    itinerary: ItineraryGenerateResponse,
    target_day: int,
    target_order: int | None,
    result: CandidatePOIValidationResult,
) -> tuple[ItineraryGenerateResponse, bool]:
    candidate = result.candidate
    place = ItineraryPlace(
        id=uuid.uuid4(),
        name=candidate.name,
        category=candidate.category or "place",
        lat=candidate.lat,
        lng=candidate.lng,
        address=candidate.address,
        opening_hours=candidate.opening_hours,
        visit_duration_minutes=candidate.suggested_visit_duration_minutes,
        duration_minutes=candidate.suggested_visit_duration_minutes,
        external_candidate_source="llm_candidate_poi",
    )
    days = []
    did_apply = False
    for day in itinerary.days:
        places = list(day.places)
        if (day.day_number or day.day) == target_day:
            insert_at = len(places) if target_order is None else max(0, min(len(places), target_order))
            place = _candidate_in_time_slot(day.places, insert_at, place)
            places.insert(insert_at, place)
            places = _shift_places_after_insert(places, insert_at)
            did_apply = True
        days.append(day.model_copy(update={"places": places, "items": places}))
    candidate_poi = [*itinerary.candidate_poi, candidate] if did_apply else itinerary.candidate_poi
    return itinerary.model_copy(update={"days": days, "candidate_poi": candidate_poi}), did_apply


def _candidate_in_time_slot(
    places: list[ItineraryPlace],
    insert_at: int,
    candidate: ItineraryPlace,
) -> ItineraryPlace:
    duration = int(candidate.visit_duration_minutes or candidate.duration_minutes or 60)
    previous = places[insert_at - 1] if insert_at > 0 and insert_at - 1 < len(places) else None
    next_place = places[insert_at] if insert_at < len(places) else None
    arrival = _add_minutes(previous.departure_time, 20) if previous and previous.departure_time else None
    if arrival is None and next_place and next_place.arrival_time:
        arrival = next_place.arrival_time
    if arrival is None:
        arrival = "09:30"
    departure = _add_minutes(arrival, duration)
    return candidate.model_copy(
        update={
            "arrival_time": arrival,
            "departure_time": departure,
            "travel_from_previous_minutes": 20 if previous else 0,
            "visit_duration_minutes": duration,
            "duration_minutes": duration,
        }
    )


def _shift_places_after_insert(places: list[ItineraryPlace], inserted_at: int) -> list[ItineraryPlace]:
    shifted = list(places)
    previous = shifted[inserted_at]
    for index in range(inserted_at + 1, len(shifted)):
        current = shifted[index]
        duration = int(current.visit_duration_minutes or current.duration_minutes or 60)
        arrival = _add_minutes(previous.departure_time, current.travel_from_previous_minutes or 20)
        if arrival is None:
            previous = current
            continue
        departure = _add_minutes(arrival, duration)
        shifted[index] = current.model_copy(update={"arrival_time": arrival, "departure_time": departure})
        previous = shifted[index]
    return shifted


def _add_minutes(value: str | None, minutes: int) -> str | None:
    if not value:
        return None
    try:
        parsed = datetime.strptime(value, "%H:%M")
    except ValueError:
        return None
    return (parsed + timedelta(minutes=minutes)).strftime("%H:%M")


def _record(
    applied: list[dict],
    ignored: list[dict],
    did_apply: bool,
    action: str,
    target_id: uuid.UUID | None,
    replacement_id: uuid.UUID | None = None,
    reason: str | None = None,
) -> None:
    payload = {"action": action, "target_id": str(target_id) if target_id else None}
    if replacement_id:
        payload["replacement_id"] = str(replacement_id)
    if reason:
        payload["reason"] = reason
    if did_apply:
        applied.append(payload)
    else:
        ignored.append({**payload, "reason": "unknown_item_id" if action == "remove" else "not_applied"})


def _candidate_duplicate_warnings(
    *,
    db: Session,
    itinerary: ItineraryGenerateResponse,
    candidate: LLMCandidatePOI,
) -> list[str]:
    warnings: list[str] = []
    normalized_name = _normalize_name(candidate.name)
    if not normalized_name:
        return warnings
    if any(_normalize_name(place.name) == normalized_name for day in itinerary.days for place in day.places):
        warnings.append("route_duplicate")
    try:
        exists = db.execute(
            text(
                """
                SELECT 1
                FROM poi
                WHERE destination_id = :destination_id
                  AND lower(trim(name)) = :name
                LIMIT 1
                """
            ),
            {"destination_id": str(itinerary.destination_id), "name": normalized_name},
        ).scalar()
    except Exception:
        exists = None
    if exists:
        warnings.append("catalog_duplicate")
    return warnings


def _normalize_name(value: str | None) -> str:
    return " ".join(str(value or "").casefold().split())
