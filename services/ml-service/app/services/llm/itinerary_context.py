from app.config import settings
from app.schemas.itinerary import ItineraryGenerateRequest, ItineraryGenerateResponse
from app.services.llm.sanitizer import sanitize_note


def build_itinerary_context(
    *,
    profile: dict,
    request: ItineraryGenerateRequest,
    itinerary: ItineraryGenerateResponse,
    destination_info: dict | None,
) -> dict:
    notes = sanitize_note(request.trip_notes, max_chars=settings.LLM_NOTES_MAX_CHARS)
    profile_notes = sanitize_note(profile.get("free_text_notes"), max_chars=settings.LLM_NOTES_MAX_CHARS)
    total_visit_minutes = sum(
        int(place.visit_duration_minutes or place.duration_minutes or 0)
        for day in itinerary.days
        for place in day.places
    )
    return {
        "destination": destination_info or {"destination_id": str(itinerary.destination_id)},
        "trip": {
            "duration_days": request.duration_days,
            "start_date": request.start_date.isoformat(),
            "pace": request.pace,
            "trip_notes": notes.__dict__,
        },
        "user_profile": {
            "vacation_preferences_ranked": profile.get("vacation_preferences_ranked"),
            "risk_tolerance": profile.get("risk_tolerance"),
            "free_text_notes": profile_notes.__dict__,
        },
        "variant": {
            "variant_index": itinerary.variant_index,
            "route_signature": itinerary.route_signature,
            "derived_metrics": {"total_visit_minutes": total_visit_minutes},
            "days": [
                {
                    "day": day.day_number or day.day,
                    "theme": day.theme,
                    "places": [
                        {
                            "id": str(place.id),
                            "name": place.name,
                            "category": place.category,
                            "opening_status": place.opening_status,
                            "arrival_time": place.arrival_time,
                            "departure_time": place.departure_time,
                            "visit_duration_minutes": place.visit_duration_minutes,
                        }
                        for place in day.places
                    ],
                }
                for day in itinerary.days
            ],
        },
    }
