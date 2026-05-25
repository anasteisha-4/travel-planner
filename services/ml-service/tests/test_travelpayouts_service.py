import fnmatch
import json
from datetime import date

from app.services import travelpayouts_service as fares
from app.services.iata_resolver import resolve_iata
from app.services.travelpayouts_service import _extract_nearest_places, _extract_prices_for_dates


def test_resolve_iata_supports_demo_origins():
    assert resolve_iata("Москва") == "MOW"
    assert resolve_iata("Saint Petersburg") == "LED"
    assert resolve_iata("Ереван") == "EVN"


def test_resolve_iata_prefers_local_overrides(monkeypatch):
    def fail_data_service(*_args, **_kwargs):
        raise AssertionError("data-service should not be called for local overrides")

    monkeypatch.setattr("app.services.iata_resolver._resolve_iata_from_data_service", fail_data_service)

    assert resolve_iata("Moscow") == "MOW"


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


def test_comfort_rest_level_uses_typical_economy_strategy():
    assert fares._fare_strategy("comfort") == ("typical_economy", 0)


def test_multi_date_fares_use_representative_month_price():
    candidates = [
        fares.FareEstimate(
            price_usd=600,
            source="travelpayouts_prices_for_dates",
            origin_iata="MOW",
            destination_iata="BCN",
            fare_strategy="typical_economy",
            trip_class=0,
        ),
        fares.FareEstimate(
            price_usd=400,
            source="travelpayouts_prices_for_dates",
            origin_iata="MOW",
            destination_iata="BCN",
            fare_strategy="typical_economy",
            trip_class=0,
        ),
        fares.FareEstimate(
            price_usd=500,
            source="travelpayouts_prices_for_dates",
            origin_iata="MOW",
            destination_iata="BCN",
            fare_strategy="typical_economy",
            trip_class=0,
        ),
        fares.FareEstimate(
            price_usd=300,
            source="travelpayouts_prices_for_dates",
            origin_iata="MOW",
            destination_iata="BCN",
            fare_strategy="typical_economy",
            trip_class=0,
        ),
    ]

    fare = fares._select_representative_fare(candidates, "typical_economy")

    assert fare is not None
    assert fare.price_usd == 500
    assert fare.source == "travelpayouts_prices_for_dates_multi_date"


class FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self.store.get(key)

    def setex(self, key: str, _ttl: int, value: str) -> None:
        self.store[key] = value

    def scan_iter(self, pattern: str):
        for key in self.store:
            if fnmatch.fnmatch(key, pattern):
                yield key

    def incr(self, key: str) -> int:
        value = int(self.store.get(key, "0")) + 1
        self.store[key] = str(value)
        return value

    def expire(self, _key: str, _ttl: int) -> None:
        return None


class FakeResponse:
    def __init__(self, data: dict) -> None:
        self._data = data

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._data


class FakeTravelpayoutsClient:
    requests: list[dict] = []

    def __init__(self, *_args, **_kwargs) -> None:
        return None

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def get(self, _url: str, params: dict):
        self.requests.append(params)
        day = int(params["departure_at"][-2:])
        price_by_day = {1: 600, 5: 400, 10: 500, 15: 300, 22: 450, 28: 800}
        return FakeResponse(
            {
                "success": True,
                "data": [
                    {
                        "origin": params["origin"],
                        "destination": params["destination"],
                        "price": price_by_day.get(day, 700),
                        "trip_class": params["trip_class"],
                    }
                ],
            }
        )


def _fare(price: float = 250.0) -> fares.FareEstimate:
    return fares.FareEstimate(
        price_usd=price,
        source="travelpayouts_prices_for_dates",
        origin_iata="MOW",
        destination_iata="IST",
        fare_strategy="typical_economy",
        trip_class=0,
    )


def test_route_month_cache_survives_duration_change(monkeypatch):
    fake_redis = FakeRedis()
    monkeypatch.setattr(fares, "get_redis", lambda: fake_redis)

    fare = _fare()
    exact_key = fares._exact_cache_key("MOW", "IST", "2026-06-01", "2026-06-11", 10, "typical_economy", 0)
    route_key = fares._route_month_cache_key("MOW", "IST", "2026-06-01", "typical_economy", 0)
    fares._cache_set_many([exact_key, route_key], fare)

    cached = fares._cache_get_fare("MOW", "IST", "2026-06-01", "2026-06-22", 21, "typical_economy", 0)

    assert cached == fare


def test_nearest_duration_cache_fallback_for_old_exact_keys(monkeypatch):
    fake_redis = FakeRedis()
    monkeypatch.setattr(fares, "get_redis", lambda: fake_redis)

    closer = _fare(300.0)
    farther = _fare(500.0)
    fake_redis.store[fares._exact_cache_key("MOW", "IST", "2026-06-01", "2026-06-11", 10, "typical_economy", 0)] = (
        json.dumps(farther.__dict__)
    )
    fake_redis.store[fares._exact_cache_key("MOW", "IST", "2026-06-01", "2026-06-15", 14, "typical_economy", 0)] = (
        json.dumps(closer.__dict__)
    )

    cached = fares._cache_get_fare("MOW", "IST", "2026-06-01", "2026-06-17", 16, "typical_economy", 0)

    assert cached == closer


def test_get_cached_fare_uses_multiple_real_fare_dates(monkeypatch):
    fake_redis = FakeRedis()
    FakeTravelpayoutsClient.requests = []
    next_month = date.today().month % 12 + 1
    monkeypatch.setattr(fares, "get_redis", lambda: fake_redis)
    monkeypatch.setattr(fares.settings, "TRAVELPAYOUTS_API_TOKEN", "token")
    monkeypatch.setattr(fares.httpx, "Client", FakeTravelpayoutsClient)

    fare = fares.get_cached_fare_usd(
        origin_city_name="Москва",
        destination_name="Барселона",
        destination_country_code="ES",
        travel_month=next_month,
        duration_days=7,
        accommodation_tier="comfort",
    )

    assert fare is not None
    assert len(FakeTravelpayoutsClient.requests) >= 3
    assert fare.source == "travelpayouts_prices_for_dates_multi_date"
    assert fare.fare_strategy == "typical_economy"
    assert fare.price_usd in {531.0, 590.0}
