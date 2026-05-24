import os
import time
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Query, Request, Response

from app.config import settings

router = APIRouter(prefix="/geocode", tags=["geocode"])

YANDEX_GEOCODER_URL = "https://geocode-maps.yandex.ru/v1"
YANDEX_GEOSUGGEST_URL = "https://suggest-maps.yandex.ru/v1/suggest"
GEOAPIFY_URL = "https://api.geoapify.com/v1/geocode"
OSM_NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OSM_OVERPASS_URL = "https://overpass-api.de/api/interpreter"
YANDEX_PROXY_REFERER = "https://www.triply-ai.ru/"
YANDEX_EXCLUDED_KINDS = {"street", "district"}
GEOSUGGEST_EXCLUDED_TAGS = {"street", "district", "province", "country", "other"}
GEOAPIFY_EXCLUDED_TYPES = {"street", "suburb", "district", "county", "state"}
OSM_EXCLUDED_TYPES = {"administrative", "postcode", "road", "residential", "suburb"}
GEOCODE_CACHE_TTL_SECONDS = 24 * 60 * 60
GEOCODE_CACHE_MAX_SIZE = 1024
GEOCODE_CACHE_PRECISION = 5

_geocode_cache: dict[str, tuple[float, Any]] = {}


def _cache_get(key: str) -> Any | None:
    cached = _geocode_cache.get(key)
    if not cached:
        return None
    expires_at, value = cached
    if expires_at <= time.monotonic():
        _geocode_cache.pop(key, None)
        return None
    return value


def _cache_set(key: str, value: Any) -> Any:
    if len(_geocode_cache) >= GEOCODE_CACHE_MAX_SIZE:
        oldest_key = next(iter(_geocode_cache))
        _geocode_cache.pop(oldest_key, None)
    _geocode_cache[key] = (time.monotonic() + GEOCODE_CACHE_TTL_SECONDS, value)
    return value


def _rounded_coord(value: float | None) -> str:
    return "" if value is None else f"{value:.{GEOCODE_CACHE_PRECISION}f}"


def _cache_key(provider: str, *parts: object) -> str:
    normalized = [str(part).strip().lower() if isinstance(part, str) else str(part) for part in parts]
    return f"{provider}:" + "|".join(normalized)


async def _proxy_json_request(
    url: str,
    request: Request,
    api_key_name: str,
    legacy_api_key_name: str,
    api_key_param: str,
    upstream_headers: dict[str, str] | None = None,
) -> Response:
    api_key = _env_value(api_key_name, legacy_api_key_name)
    if not api_key:
        raise HTTPException(status_code=503, detail="Geocoding provider is not configured")
    params = dict(request.query_params)
    params[api_key_param] = api_key
    async with httpx.AsyncClient(timeout=7.0) as client:
        upstream = await client.get(url, params=params, headers=upstream_headers)
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        media_type=upstream.headers.get("content-type", "application/json"),
    )


def _env_value(name: str, legacy_name: str) -> str:
    value = getattr(settings, name, "") or os.getenv(name, "")
    return value or os.getenv(legacy_name, "")


def _yandex_geocoder_api_key() -> str:
    return (
        _env_value("YANDEX_GEOCODER_API_KEY", "YANDEX_MAPS_API_TOKEN")
        or os.getenv("VITE_YANDEX_GEOCODER_API_KEY", "")
        or os.getenv("VITE_YANDEX_MAPS_API_TOKEN", "")
    )


def _yandex_referer_headers() -> dict[str, str]:
    return {
        "Referer": YANDEX_PROXY_REFERER,
        "Origin": YANDEX_PROXY_REFERER.rstrip("/"),
    }


def _is_russia_or_cis(lon: float, lat: float) -> bool:
    return 19 <= lon <= 180 and 41 <= lat <= 82


def _parse_yandex(obj: dict[str, Any]) -> dict[str, float | str] | None:
    point = obj.get("Point", {}).get("pos", "")
    try:
        lon_raw, lat_raw = point.split(" ")
        lon = float(lon_raw)
        lat = float(lat_raw)
    except ValueError:
        return None
    meta = obj.get("metaDataProperty", {}).get("GeocoderMetaData", {})
    return {
        "name": obj.get("name") or meta.get("text") or "",
        "fullAddress": meta.get("text") or "",
        "lat": lat,
        "lon": lon,
    }


def _parse_geoapify(feature: dict[str, Any]) -> dict[str, float | str] | None:
    coordinates = feature.get("geometry", {}).get("coordinates") or []
    if len(coordinates) < 2:
        return None
    props = feature.get("properties", {})
    return {
        "name": props.get("name") or props.get("address_line1") or "",
        "fullAddress": props.get("formatted") or "",
        "lat": float(coordinates[1]),
        "lon": float(coordinates[0]),
    }


def _parse_osm(item: dict[str, Any]) -> dict[str, float | str] | None:
    try:
        lat = float(item.get("lat"))
        lon = float(item.get("lon"))
    except (TypeError, ValueError):
        return None
    namedetails = item.get("namedetails") if isinstance(item.get("namedetails"), dict) else {}
    name = (
        item.get("name")
        or namedetails.get("name")
        or namedetails.get("name:en")
        or namedetails.get("name:ru")
        or str(item.get("display_name") or "").split(",", 1)[0]
    )
    return {
        "name": str(name or ""),
        "fullAddress": item.get("display_name") or "",
        "lat": lat,
        "lon": lon,
    }


async def _search_yandex(
    query: str, results: int, lon: float | None, lat: float | None
) -> list[dict[str, float | str]]:
    cache_key = _cache_key("yandex-search", query, results, _rounded_coord(lon), _rounded_coord(lat))
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    api_key = _yandex_geocoder_api_key()
    if not api_key:
        return []
    params = {
        "apikey": api_key,
        "format": "json",
        "lang": "ru-RU",
        "geocode": query,
        "results": str(results),
    }
    if lon is not None and lat is not None:
        params["ll"] = f"{lon},{lat}"
        params["spn"] = "5,5"
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.get(YANDEX_GEOCODER_URL, params=params, headers=_yandex_referer_headers())
    if not response.is_success:
        return []
    data = response.json()
    members = data.get("response", {}).get("GeoObjectCollection", {}).get("featureMember", [])
    parsed: list[dict[str, float | str]] = []
    for member in members:
        obj = member.get("GeoObject", {})
        kind = obj.get("metaDataProperty", {}).get("GeocoderMetaData", {}).get("kind")
        if kind in YANDEX_EXCLUDED_KINDS:
            continue
        item = _parse_yandex(obj)
        if item:
            parsed.append(item)
    return _cache_set(cache_key, parsed)


async def _search_yandex_geosuggest(
    query: str, results: int, lon: float | None, lat: float | None
) -> list[dict[str, float | str]]:
    max_resolved_results = min(results, 3)
    cache_key = _cache_key("yandex-geosuggest", query, max_resolved_results, _rounded_coord(lon), _rounded_coord(lat))
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    api_key = _env_value("YANDEX_GEOSUGGEST_API_KEY", "VITE_YANDEX_GEOSUGGEST_API_KEY")
    if not api_key:
        return []
    params = {
        "apikey": api_key,
        "text": query,
        "lang": "ru_RU",
        "results": str(max_resolved_results),
        "types": "biz,house,locality,metro",
        "print_address": "1",
    }
    if lon is not None and lat is not None:
        params["ll"] = f"{lon},{lat}"
        params["spn"] = "5,5"
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.get(YANDEX_GEOSUGGEST_URL, params=params, headers=_yandex_referer_headers())
    if not response.is_success:
        return []
    items = [
        item
        for item in response.json().get("results", [])
        if not any(tag in GEOSUGGEST_EXCLUDED_TAGS for tag in item.get("tags", []))
    ]
    resolved: list[dict[str, float | str]] = []
    for item in items[:max_resolved_results]:
        address = item.get("address", {}).get("formatted_address")
        if not address:
            continue
        yandex_matches = await _search_yandex(address, 1, lon, lat)
        if yandex_matches:
            yandex_matches[0]["name"] = item.get("title", {}).get("text") or yandex_matches[0]["name"]
            resolved.append(yandex_matches[0])
    return _cache_set(cache_key, resolved)


async def _search_geoapify(
    query: str, results: int, lon: float | None, lat: float | None
) -> list[dict[str, float | str]]:
    cache_key = _cache_key("geoapify-search", query, results, _rounded_coord(lon), _rounded_coord(lat))
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    api_key = _env_value("GEOAPIFY_API_KEY", "VITE_GEOAPIFY_API_KEY")
    if not api_key:
        return []
    params = {"text": query, "limit": str(results), "lang": "ru", "apiKey": api_key}
    if lon is not None and lat is not None:
        params["bias"] = f"proximity:{lon},{lat}"
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.get(f"{GEOAPIFY_URL}/autocomplete", params=params)
    if not response.is_success:
        return []
    parsed: list[dict[str, float | str]] = []
    for feature in response.json().get("features", []):
        if feature.get("properties", {}).get("result_type") in GEOAPIFY_EXCLUDED_TYPES:
            continue
        item = _parse_geoapify(feature)
        if item and item["name"]:
            parsed.append(item)
    return _cache_set(cache_key, parsed)


async def _search_osm_nominatim(
    query: str, results: int, lon: float | None, lat: float | None
) -> list[dict[str, float | str]]:
    cache_key = _cache_key("osm-nominatim-search", query, results, _rounded_coord(lon), _rounded_coord(lat))
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    params = {
        "q": query,
        "format": "jsonv2",
        "limit": str(results),
        "addressdetails": "1",
        "namedetails": "1",
        "extratags": "1",
        "accept-language": "ru,en",
    }
    if lon is not None and lat is not None:
        params["viewbox"] = f"{lon - 0.25},{lat + 0.25},{lon + 0.25},{lat - 0.25}"
        params["bounded"] = "0"
    headers = {"User-Agent": "Triply/1.0 (https://www.triply-ai.ru; geocoding@triply-ai.ru)"}
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.get(OSM_NOMINATIM_URL, params=params, headers=headers)
    if not response.is_success:
        return []
    parsed: list[dict[str, float | str]] = []
    for item in response.json():
        if str(item.get("type") or "").lower() in OSM_EXCLUDED_TYPES:
            continue
        parsed_item = _parse_osm(item)
        if parsed_item and parsed_item["name"]:
            parsed.append(parsed_item)
    return _cache_set(cache_key, parsed)


def _overpass_query(lat: float, lon: float, radius_m: int, limit: int) -> str:
    selectors = [
        '["tourism"~"^(attraction|museum|gallery|theme_park|viewpoint|zoo|aquarium)$"]["name"]',
        '["historic"]["name"]',
        '["leisure"~"^(park|theme_park|water_park|marina|beach_resort)$"]["name"]',
        '["amenity"~"^(theatre|arts_centre|place_of_worship|marketplace)$"]["name"]',
        '["natural"~"^(beach|cape|peak|spring|wood)$"]["name"]',
    ]
    blocks = [f"nwr(around:{radius_m},{lat},{lon}){selector};" for selector in selectors]
    return "[out:json][timeout:8];(" + "".join(blocks) + f");out center tags qt {limit};"


def _parse_overpass_element(element: dict[str, Any], center_lat: float, center_lon: float) -> dict[str, Any] | None:
    tags = element.get("tags") if isinstance(element.get("tags"), dict) else {}
    name = tags.get("name") or tags.get("name:en") or tags.get("name:ru")
    if not name:
        return None
    lat = element.get("lat") or (element.get("center") or {}).get("lat")
    lon = element.get("lon") or (element.get("center") or {}).get("lon")
    try:
        lat_float = float(lat)
        lon_float = float(lon)
    except (TypeError, ValueError):
        return None
    category = _osm_category(tags)
    return {
        "external_id": f"osm:{element.get('type', 'element')}:{element.get('id')}",
        "name": str(name),
        "fullAddress": tags.get("addr:full") or tags.get("addr:street") or "",
        "lat": lat_float,
        "lon": lon_float,
        "category": category,
        "source": "osm_overpass",
        "score": _osm_poi_score(tags, category, lat_float, lon_float, center_lat, center_lon),
        "tags": tags,
    }


def _osm_category(tags: dict[str, Any]) -> str:
    if tags.get("leisure") in {"theme_park", "water_park"}:
        return "family"
    if tags.get("tourism") in {"museum", "gallery", "attraction", "theme_park", "viewpoint"}:
        return str(tags["tourism"])
    if tags.get("historic"):
        return "historic"
    if tags.get("natural") == "beach":
        return "beach"
    if tags.get("leisure") in {"park", "marina", "beach_resort"}:
        return str(tags["leisure"])
    if tags.get("amenity"):
        return str(tags["amenity"])
    return "place"


def _osm_poi_score(
    tags: dict[str, Any],
    category: str,
    lat: float,
    lon: float,
    center_lat: float,
    center_lon: float,
) -> float:
    score = 1.0
    if tags.get("wikidata") or tags.get("wikipedia"):
        score += 1.2
    if tags.get("tourism") in {"attraction", "theme_park", "museum", "viewpoint"}:
        score += 1.0
    if category in {"family", "beach", "historic", "park", "marina"}:
        score += 0.6
    score -= min(1.2, (((lat - center_lat) ** 2 + (lon - center_lon) ** 2) ** 0.5) * 12)
    return round(score, 4)


async def _search_osm_overpass_poi(lat: float, lon: float, radius_m: int, results: int) -> list[dict[str, Any]]:
    radius_m = max(500, min(radius_m, 30000))
    cache_key = _cache_key("osm-overpass-poi", _rounded_coord(lon), _rounded_coord(lat), radius_m, results)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    headers = {"User-Agent": "Triply/1.0 (https://www.triply-ai.ru; geocoding@triply-ai.ru)"}
    try:
        async with httpx.AsyncClient(timeout=18.0) as client:
            response = await client.post(
                OSM_OVERPASS_URL,
                data={"data": _overpass_query(lat, lon, radius_m, results)},
                headers=headers,
            )
    except httpx.HTTPError:
        return []
    if not response.is_success:
        return []
    items = [
        parsed
        for element in response.json().get("elements", [])
        if (parsed := _parse_overpass_element(element, lat, lon)) is not None
    ]
    items.sort(key=lambda item: float(item.get("score") or 0), reverse=True)
    return _cache_set(cache_key, _dedupe_geocode_matches(items)[:results])


async def _reverse_yandex(lat: float, lon: float) -> str | None:
    matches = await _search_yandex(f"{lon},{lat}", 1, lon, lat)
    return str(matches[0]["name"]) if matches else None


async def _reverse_geoapify(lat: float, lon: float) -> str | None:
    cache_key = _cache_key("geoapify-reverse", _rounded_coord(lon), _rounded_coord(lat))
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    api_key = _env_value("GEOAPIFY_API_KEY", "VITE_GEOAPIFY_API_KEY")
    if not api_key:
        return None
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.get(
            f"{GEOAPIFY_URL}/reverse",
            params={"lat": str(lat), "lon": str(lon), "lang": "ru", "apiKey": api_key, "type": "amenity"},
        )
        if response.is_success:
            feature = (response.json().get("features") or [None])[0]
            name = feature and feature.get("properties", {}).get("name")
            if name:
                return str(name)
        response = await client.get(
            f"{GEOAPIFY_URL}/reverse",
            params={"lat": str(lat), "lon": str(lon), "lang": "ru", "apiKey": api_key},
        )
    if not response.is_success:
        return None
    feature = (response.json().get("features") or [None])[0]
    if not feature:
        return None
    props = feature.get("properties", {})
    return _cache_set(cache_key, props.get("name") or props.get("address_line1"))


@router.get("/search")
async def search_geocode(
    q: str = Query(..., min_length=2, max_length=200),
    results: int = Query(5, ge=1, le=10),
    bias_lon: float | None = Query(None, ge=-180, le=180),
    bias_lat: float | None = Query(None, ge=-90, le=90),
    mode: str = Query("default", pattern="^(default|poi)$"),
) -> list[dict[str, float | str]]:
    if mode == "poi":
        matches: list[dict[str, float | str]] = []
        for provider_matches in [
            await _search_geoapify(q, results, bias_lon, bias_lat),
            await _search_yandex(q, results, bias_lon, bias_lat),
            await _search_osm_nominatim(q, results, bias_lon, bias_lat),
        ]:
            matches.extend(provider_matches)
        return _dedupe_geocode_matches(matches)[:results]

    geoapify = await _search_geoapify(q, results, bias_lon, bias_lat)
    if geoapify:
        return geoapify[:results]
    yandex = await _search_yandex(q, results, bias_lon, bias_lat)
    if yandex:
        return yandex[:results]
    if bias_lon is not None and bias_lat is not None and _is_russia_or_cis(bias_lon, bias_lat):
        yandex_suggest = await _search_yandex_geosuggest(q, results, bias_lon, bias_lat)
        if yandex_suggest:
            return yandex_suggest[:results]
    return []


def _dedupe_geocode_matches(matches: list[dict[str, float | str]]) -> list[dict[str, float | str]]:
    seen: set[tuple[str, str, str]] = set()
    deduped: list[dict[str, float | str]] = []
    for item in matches:
        lat = item.get("lat")
        lon = item.get("lon")
        key = (
            str(item.get("name") or "").casefold(),
            f"{float(lat):.5f}" if isinstance(lat, int | float) else str(lat),
            f"{float(lon):.5f}" if isinstance(lon, int | float) else str(lon),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


@router.get("/reverse")
async def reverse_geocode(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
) -> dict[str, str | None]:
    return {"name": await _reverse_geoapify(lat, lon) or await _reverse_yandex(lat, lon)}


@router.get("/poi")
async def search_poi(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    radius_m: int = Query(12000, ge=500, le=30000),
    results: int = Query(40, ge=1, le=80),
) -> list[dict[str, Any]]:
    return await _search_osm_overpass_poi(lat, lon, radius_m, results)


@router.get("/yandex/1.x")
async def proxy_yandex_geocoder(request: Request) -> Response:
    return await _proxy_json_request(
        YANDEX_GEOCODER_URL,
        request,
        "YANDEX_GEOCODER_API_KEY",
        "YANDEX_MAPS_API_TOKEN",
        "apikey",
        _yandex_referer_headers(),
    )


@router.get("/yandex/suggest")
async def proxy_yandex_geosuggest(request: Request) -> Response:
    return await _proxy_json_request(
        YANDEX_GEOSUGGEST_URL,
        request,
        "YANDEX_GEOSUGGEST_API_KEY",
        "VITE_YANDEX_GEOSUGGEST_API_KEY",
        "apikey",
        _yandex_referer_headers(),
    )


@router.get("/geoapify/autocomplete")
async def proxy_geoapify_autocomplete(request: Request) -> Response:
    return await _proxy_json_request(
        f"{GEOAPIFY_URL}/autocomplete",
        request,
        "GEOAPIFY_API_KEY",
        "VITE_GEOAPIFY_API_KEY",
        "apiKey",
    )


@router.get("/geoapify/reverse")
async def proxy_geoapify_reverse(request: Request) -> Response:
    return await _proxy_json_request(
        f"{GEOAPIFY_URL}/reverse",
        request,
        "GEOAPIFY_API_KEY",
        "VITE_GEOAPIFY_API_KEY",
        "apiKey",
    )
