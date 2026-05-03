from app.services.iata_resolver import resolve_iata
from app.services.travelpayouts_service import _extract_nearest_places, _extract_prices_for_dates


def test_resolve_iata_supports_demo_origins():
    assert resolve_iata("Москва") == "MOW"
    assert resolve_iata("Saint Petersburg") == "LED"
    assert resolve_iata("Ереван") == "EVN"


def test_resolve_iata_supports_demo_destinations():
    assert resolve_iata("Istanbul") == "IST"
    assert resolve_iata("Бангкок") == "BKK"
    assert resolve_iata("Пхукет") == "HKT"


def test_resolve_iata_uses_nearest_airport_from_coordinates():
    assert resolve_iata(None, lat=48.2082, lng=16.3738, country_code="AT") == "VIE"
    assert resolve_iata("Unknown beach", lat=7.8804, lng=98.3923, country_code="TH") == "HKT"


def test_extract_prices_for_dates_picks_cheapest():
    fare = _extract_prices_for_dates(
        {
            "success": True,
            "data": [
                {"origin": "MOW", "destination": "IST", "price": 300, "found_at": "2026-01-01T00:00:00Z"},
                {"origin": "MOW", "destination": "IST", "price": 220, "expires_at": "2026-01-08T00:00:00Z"},
            ],
        },
        "MOW",
        "IST",
        "cheapest_economy",
        0,
    )
    assert fare is not None
    assert fare.price_usd == 220
    assert fare.source == "travelpayouts_prices_for_dates"
    assert fare.origin_iata == "MOW"
    assert fare.destination_iata == "IST"
    assert fare.fare_strategy == "cheapest_economy"
    assert fare.trip_class == 0


def test_extract_prices_for_dates_uses_median_for_typical_economy():
    fare = _extract_prices_for_dates(
        {
            "success": True,
            "data": [
                {"origin": "MOW", "destination": "IST", "price": 100},
                {"origin": "MOW", "destination": "IST", "price": 300},
                {"origin": "MOW", "destination": "IST", "price": 200},
            ],
        },
        "MOW",
        "IST",
        "typical_economy",
        0,
    )
    assert fare is not None
    assert fare.price_usd == 236
    assert fare.fare_strategy == "typical_economy"


def test_extract_nearest_places_picks_cheapest():
    fare = _extract_nearest_places(
        {
            "prices": [
                {"origin": "MOW", "destination": "BKK", "value": 700},
                {"origin": "MOW", "destination": "HKT", "value": 640},
            ]
        },
        "MOW",
        "TH",
        "business_comfort",
        1,
    )
    assert fare is not None
    assert fare.price_usd == 640
    assert fare.source == "travelpayouts_nearest_places"
    assert fare.destination_iata == "HKT"
    assert fare.fare_strategy == "business_comfort"
    assert fare.trip_class == 1
