def filter_destinations_by_travel_advisory(
    *,
    destinations: list[dict],
    citizenship_code: str,
) -> tuple[list[dict], list[dict]]:
    del citizenship_code
    return destinations, []
