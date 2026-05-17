import uuid
from dataclasses import dataclass, field

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

    for adjustment in review.suggested_adjustments:
        if adjustment.action == LLMReviewAction.remove and adjustment.target_id:
            adjusted, did_apply = _remove_item(adjusted, adjustment.target_id)
            _record(applied, ignored, did_apply, "remove", adjustment.target_id)
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


def _remove_item(itinerary: ItineraryGenerateResponse, target_id: uuid.UUID) -> tuple[ItineraryGenerateResponse, bool]:
    days = []
    did_apply = False
    for day in itinerary.days:
        places = [place for place in day.places if place.id != target_id]
        did_apply = did_apply or len(places) != len(day.places)
        days.append(day.model_copy(update={"places": places, "items": places}))
    return itinerary.model_copy(update={"days": days}), did_apply


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
            places.insert(insert_at, place)
            did_apply = True
        days.append(day.model_copy(update={"places": places, "items": places}))
    candidate_poi = [*itinerary.candidate_poi, candidate] if did_apply else itinerary.candidate_poi
    return itinerary.model_copy(update={"days": days, "candidate_poi": candidate_poi}), did_apply


def _record(
    applied: list[dict], ignored: list[dict], did_apply: bool, action: str, target_id: uuid.UUID | None
) -> None:
    payload = {"action": action, "target_id": str(target_id) if target_id else None}
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
