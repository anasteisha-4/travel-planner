import json
import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

import httpx
import redis

from app.config import settings
from app.deps import get_redis
from app.services.iata_resolver import resolve_iata

logger = logging.getLogger(__name__)

_PRICES_FOR_DATES_URL = "https://api.travelpayouts.com/aviasales/v3/prices_for_dates"
_NEAREST_PLACES_URL = "https://api.travelpayouts.com/v2/prices/nearest-places-matrix"
_PRICES_FOR_DATES_RATE_LIMIT_PER_MIN = 500
_NEAREST_PLACES_RATE_LIMIT_PER_MIN = 50


@dataclass(frozen=True)
class FareEstimate:
    price_usd: float
    source: str
    origin_iata: str
    destination_iata: str | None
    fare_strategy: str
    trip_class: int
    found_at: str | None = None
    expires_at: str | None = None


def _fare_strategy(accommodation_tier: str) -> tuple[str, int]:
    if accommodation_tier == "luxury":
        return "business_comfort", 1
    if accommodation_tier == "mid":
        return "typical_economy", 0
    return "cheapest_economy", 0


def _month_start(year: int, month: int) -> date:
    return date(year, month, 1)


def _date_window(travel_month: int, duration_days: int) -> tuple[str, str]:
    today = date.today()
    year = today.year + (1 if travel_month < today.month else 0)
    depart = _month_start(year, travel_month)
    if depart < today:
        depart = today + timedelta(days=7)
    return_at = depart + timedelta(days=max(1, duration_days))
    return depart.isoformat(), return_at.isoformat()


def _cache_get(cache_key: str) -> FareEstimate | None:
    try:
        raw = get_redis().get(cache_key)
    except redis.RedisError:
        return None
    if not raw:
        return None
    try:
        data = json.loads(raw)
        return FareEstimate(**data)
    except (TypeError, ValueError):
        return None


def _cache_set(cache_key: str, fare: FareEstimate) -> None:
    try:
        get_redis().setex(cache_key, settings.TRAVELPAYOUTS_CACHE_TTL_SECONDS, json.dumps(fare.__dict__))
    except redis.RedisError:
        return


def _rate_limit_allows(method_key: str, limit_per_minute: int) -> bool:
    try:
        r = get_redis()
        key = f"travelpayouts:rate:{method_key}:{datetime.utcnow().strftime('%Y%m%d%H%M')}"
        count = r.incr(key)
        if count == 1:
            r.expire(key, 60)
        return int(count) <= limit_per_minute
    except redis.RedisError:
        logger.info("Travelpayouts fare lookup skipped: Redis rate guard unavailable")
        return False


def _adjust_fare_for_strategy(price: float, strategy: str) -> float:
    if strategy == "business_comfort":
        return price
    if strategy == "typical_economy":
        return price * 1.18
    return price


def _extract_prices_for_dates(
    data: dict[str, Any],
    origin_iata: str,
    destination_iata: str,
    fare_strategy: str,
    trip_class: int,
) -> FareEstimate | None:
    if not data.get("success"):
        return None
    rows = data.get("data")
    if not isinstance(rows, list) or not rows:
        return None
    priced_rows = sorted((row for row in rows if row.get("price")), key=lambda row: float(row["price"]))
    if not priced_rows:
        return None
    if fare_strategy == "typical_economy" and len(priced_rows) >= 3:
        selected = priced_rows[min(len(priced_rows) // 2, len(priced_rows) - 1)]
    else:
        selected = priced_rows[0]
    return FareEstimate(
        price_usd=round(_adjust_fare_for_strategy(float(selected["price"]), fare_strategy), 2),
        source="travelpayouts_prices_for_dates",
        origin_iata=str(selected.get("origin") or origin_iata),
        destination_iata=str(selected.get("destination") or destination_iata),
        fare_strategy=fare_strategy,
        trip_class=int(selected.get("trip_class") if selected.get("trip_class") is not None else trip_class),
        found_at=selected.get("found_at"),
        expires_at=selected.get("expires_at"),
    )


def _extract_nearest_places(
    data: dict[str, Any],
    origin_iata: str,
    destination_hint: str,
    fare_strategy: str,
    trip_class: int,
) -> FareEstimate | None:
    rows = data.get("prices")
    if not isinstance(rows, list) or not rows:
        return None
    cheapest = min((row for row in rows if row.get("value")), key=lambda row: float(row["value"]), default=None)
    if not cheapest:
        return None
    return FareEstimate(
        price_usd=round(_adjust_fare_for_strategy(float(cheapest["value"]), fare_strategy), 2),
        source="travelpayouts_nearest_places",
        origin_iata=str(cheapest.get("origin") or origin_iata),
        destination_iata=str(cheapest.get("destination") or destination_hint),
        fare_strategy=fare_strategy,
        trip_class=int(cheapest.get("trip_class") if cheapest.get("trip_class") is not None else trip_class),
        found_at=cheapest.get("found_at"),
        expires_at=None,
    )


def get_cached_fare_usd(
    *,
    origin_city_name: str | None,
    origin_lat: float | None = None,
    origin_lng: float | None = None,
    destination_name: str | None,
    destination_lat: float | None = None,
    destination_lng: float | None = None,
    destination_country_code: str | None,
    travel_month: int,
    duration_days: int,
    accommodation_tier: str,
) -> FareEstimate | None:
    token = settings.TRAVELPAYOUTS_API_TOKEN.strip()
    if not token:
        return None

    fare_strategy, trip_class = _fare_strategy(accommodation_tier)
    origin_iata = resolve_iata(origin_city_name, lat=origin_lat, lng=origin_lng)
    if not origin_iata:
        return None

    destination_iata = resolve_iata(
        destination_name,
        lat=destination_lat,
        lng=destination_lng,
        country_code=destination_country_code,
    )
    destination_hint = destination_iata or (destination_country_code or "").upper()
    if len(destination_hint) not in (2, 3):
        return None

    depart_at, return_at = _date_window(travel_month, duration_days)
    cache_key = (
        "travelpayouts:fare:v1:"
        f"{origin_iata}:{destination_hint}:{depart_at[:7]}:{return_at[:7]}:{duration_days}:usd:{fare_strategy}:{trip_class}"
    )
    cached = _cache_get(cache_key)
    if cached:
        return cached

    headers = {"Accept-Encoding": "gzip, deflate", "X-Access-Token": token}
    try:
        with httpx.Client(timeout=settings.TRAVELPAYOUTS_TIMEOUT_SECONDS, headers=headers) as client:
            fare = None
            if destination_iata and _rate_limit_allows("prices_for_dates", _PRICES_FOR_DATES_RATE_LIMIT_PER_MIN):
                resp = client.get(
                    _PRICES_FOR_DATES_URL,
                    params={
                        "origin": origin_iata,
                        "destination": destination_iata,
                        "departure_at": depart_at,
                        "return_at": return_at,
                        "one_way": "false",
                        "direct": "false",
                        "sorting": "price",
                        "currency": "usd",
                        "market": "ru",
                        "limit": 30,
                        "page": 1,
                        "trip_class": trip_class,
                    },
                )
                resp.raise_for_status()
                fare = _extract_prices_for_dates(resp.json(), origin_iata, destination_iata, fare_strategy, trip_class)

            if fare is None and _rate_limit_allows("nearest_places_matrix", _NEAREST_PLACES_RATE_LIMIT_PER_MIN):
                resp = client.get(
                    _NEAREST_PLACES_URL,
                    params={
                        "origin": origin_iata,
                        "destination": destination_hint,
                        "depart_date": depart_at[:7],
                        "return_date": return_at[:7],
                        "currency": "usd",
                        "market": "ru",
                        "show_to_affiliates": "true",
                        "limit": 5,
                        "distance": 1000,
                        "trip_class": trip_class,
                    },
                )
                resp.raise_for_status()
                fare = _extract_nearest_places(resp.json(), origin_iata, destination_hint, fare_strategy, trip_class)

            if fare_strategy == "business_comfort":
                economy_fare = get_cached_fare_usd(
                    origin_city_name=origin_city_name,
                    origin_lat=origin_lat,
                    origin_lng=origin_lng,
                    destination_name=destination_name,
                    destination_lat=destination_lat,
                    destination_lng=destination_lng,
                    destination_country_code=destination_country_code,
                    travel_month=travel_month,
                    duration_days=duration_days,
                    accommodation_tier="mid",
                )
                business_floor = round(economy_fare.price_usd * 3.2, 2) if economy_fare is not None else None
                if economy_fare is not None and (fare is None or fare.price_usd < business_floor):
                    fare = FareEstimate(
                        price_usd=business_floor,
                        source="travelpayouts_business_fallback",
                        origin_iata=economy_fare.origin_iata,
                        destination_iata=economy_fare.destination_iata,
                        fare_strategy=fare_strategy,
                        trip_class=trip_class,
                        found_at=economy_fare.found_at,
                        expires_at=economy_fare.expires_at,
                    )
    except (httpx.HTTPError, ValueError) as exc:
        logger.info("Travelpayouts fare lookup skipped: %s", exc)
        return None

    if fare is None:
        return None

    _cache_set(cache_key, fare)
    return fare
