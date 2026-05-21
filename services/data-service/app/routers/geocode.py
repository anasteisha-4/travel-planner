import os
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Query, Request, Response

from app.config import settings

router = APIRouter(prefix="/geocode", tags=["geocode"])

YANDEX_GEOCODER_URL = "https://geocode-maps.yandex.ru/1.x"
YANDEX_GEOSUGGEST_URL = "https://suggest-maps.yandex.ru/v1/suggest"
GEOAPIFY_URL = "https://api.geoapify.com/v1/geocode"
YANDEX_EXCLUDED_KINDS = {"street", "district"}
GEOSUGGEST_EXCLUDED_TAGS = {"street", "district", "province", "country", "other"}
GEOAPIFY_EXCLUDED_TYPES = {"street", "suburb", "district", "county", "state"}


async def _proxy_json_request(
    url: str,
    request: Request,
    api_key_name: str,
    legacy_api_key_name: str,
    api_key_param: str,
) -> Response:
    api_key = _env_value(api_key_name, legacy_api_key_name)
    if not api_key:
        raise HTTPException(status_code=503, detail="Geocoding provider is not configured")
    params = dict(request.query_params)
    params[api_key_param] = api_key
    async with httpx.AsyncClient(timeout=7.0) as client:
        upstream = await client.get(url, params=params)
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        media_type=upstream.headers.get("content-type", "application/json"),
    )


def _env_value(name: str, legacy_name: str) -> str:
    value = getattr(settings, name, "") or os.getenv(name, "")
    return value or os.getenv(legacy_name, "")


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


async def _search_yandex(
    query: str, results: int, lon: float | None, lat: float | None
) -> list[dict[str, float | str]]:
    api_key = _env_value("YANDEX_MAPS_API_TOKEN", "VITE_YANDEX_MAPS_API_TOKEN")
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
        response = await client.get(YANDEX_GEOCODER_URL, params=params)
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
    return parsed


async def _search_yandex_geosuggest(
    query: str, results: int, lon: float | None, lat: float | None
) -> list[dict[str, float | str]]:
    api_key = _env_value("YANDEX_GEOSUGGEST_API_KEY", "VITE_YANDEX_GEOSUGGEST_API_KEY")
    if not api_key:
        return []
    params = {
        "apikey": api_key,
        "text": query,
        "lang": "ru_RU",
        "results": str(results),
        "types": "biz,house,locality,metro",
        "print_address": "1",
    }
    if lon is not None and lat is not None:
        params["ll"] = f"{lon},{lat}"
        params["spn"] = "5,5"
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.get(YANDEX_GEOSUGGEST_URL, params=params)
    if not response.is_success:
        return []
    items = [
        item
        for item in response.json().get("results", [])
        if not any(tag in GEOSUGGEST_EXCLUDED_TAGS for tag in item.get("tags", []))
    ]
    resolved: list[dict[str, float | str]] = []
    for item in items:
        address = item.get("address", {}).get("formatted_address")
        if not address:
            continue
        yandex_matches = await _search_yandex(address, 1, lon, lat)
        if yandex_matches:
            yandex_matches[0]["name"] = item.get("title", {}).get("text") or yandex_matches[0]["name"]
            resolved.append(yandex_matches[0])
    return resolved


async def _search_geoapify(
    query: str, results: int, lon: float | None, lat: float | None
) -> list[dict[str, float | str]]:
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
    return parsed


async def _reverse_yandex(lat: float, lon: float) -> str | None:
    matches = await _search_yandex(f"{lon},{lat}", 1, lon, lat)
    return str(matches[0]["name"]) if matches else None


async def _reverse_geoapify(lat: float, lon: float) -> str | None:
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
    return props.get("name") or props.get("address_line1")


@router.get("/search")
async def search_geocode(
    q: str = Query(..., min_length=2, max_length=200),
    results: int = Query(5, ge=1, le=10),
    bias_lon: float | None = Query(None, ge=-180, le=180),
    bias_lat: float | None = Query(None, ge=-90, le=90),
) -> list[dict[str, float | str]]:
    use_yandex = bias_lon is not None and bias_lat is not None and _is_russia_or_cis(bias_lon, bias_lat)
    if use_yandex:
        yandex = await _search_yandex_geosuggest(q, results, bias_lon, bias_lat)
        if yandex:
            return yandex[:results]
        yandex = await _search_yandex(q, results, bias_lon, bias_lat)
        if yandex:
            return yandex[:results]
    geoapify = await _search_geoapify(q, results, bias_lon, bias_lat)
    if geoapify:
        return geoapify[:results]
    return (await _search_yandex(q, results, bias_lon, bias_lat))[:results]


@router.get("/reverse")
async def reverse_geocode(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
) -> dict[str, str | None]:
    if _is_russia_or_cis(lon, lat):
        return {"name": await _reverse_yandex(lat, lon)}
    return {"name": await _reverse_geoapify(lat, lon) or await _reverse_yandex(lat, lon)}


@router.get("/yandex/1.x")
async def proxy_yandex_geocoder(request: Request) -> Response:
    return await _proxy_json_request(
        YANDEX_GEOCODER_URL,
        request,
        "YANDEX_MAPS_API_TOKEN",
        "VITE_YANDEX_MAPS_API_TOKEN",
        "apikey",
    )


@router.get("/yandex/suggest")
async def proxy_yandex_geosuggest(request: Request) -> Response:
    return await _proxy_json_request(
        YANDEX_GEOSUGGEST_URL,
        request,
        "YANDEX_GEOSUGGEST_API_KEY",
        "VITE_YANDEX_GEOSUGGEST_API_KEY",
        "apikey",
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
