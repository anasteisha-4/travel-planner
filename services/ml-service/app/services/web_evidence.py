from app.schemas.itinerary import ItineraryGenerateResponse


def apply_paid_poi_price_evidence(
    itinerary: ItineraryGenerateResponse,
    *,
    destination: dict | None = None,
) -> ItineraryGenerateResponse:
    del destination
    return itinerary
