import math
import re
import uuid
from datetime import datetime, time
from typing import Any

import pycountry
from sqlalchemy.orm import Session

from app.models import POI, Destination, DestinationIngestionRequest, DestinationIngestionStatus, POISource
from app.routers.geocode import _search_osm_overpass_poi
from app.services.itinerary_service import generate_itinerary

_COUNTRY_ALIASES = {
    "spain": "ES",
    "испания": "ES",
    "españa": "ES",
    "thailand": "TH",
    "таиланд": "TH",
    "turkey": "TR",
    "турция": "TR",
    "france": "FR",
    "франция": "FR",
    "italy": "IT",
    "италия": "IT",
}


async def ingest_osm_poi_and_generate_itinerary(
    *,
    db: Session,
    destination_name: str,
    lat: float,
    lng: float,
    radius_m: int,
    duration_days: int,
    preferred_activities: list[str],
    start_date: datetime | None,
    variant_count: int,
    variant_seed: int | None,
    pace: str,
    day_start_time: time,
    day_end_time: time,
    rest_days_count: int,
    exclude_signature: str | None,
    trip_budget: float | None,
    people_count: int,
) -> dict[str, Any]:
    country_code = _country_code_from_destination_text(destination_name)
    destination, created_destination = _get_or_create_destination(
        db,
        destination_name=destination_name,
        country_code=country_code,
        lat=lat,
        lng=lng,
        radius_m=radius_m,
    )
    raw_poi = await _search_osm_overpass_poi(lat, lng, radius_m, results=80)
    saved_count = _save_osm_poi(db, destination, raw_poi)
    if created_destination:
        _ensure_ingestion_request(
            db,
            destination=destination,
            destination_name=destination_name,
            country_code=country_code,
            poi_count=saved_count,
        )
    db.commit()

    itinerary = generate_itinerary(
        db=db,
        destination_id=str(destination.id),
        duration_days=duration_days,
        preferred_activities=preferred_activities,
        start_date=start_date,
        variant_count=variant_count,
        variant_seed=variant_seed,
        pace=pace,
        day_start_time=day_start_time,
        day_end_time=day_end_time,
        rest_days_count=rest_days_count,
        exclude_signature=exclude_signature,
        trip_budget=trip_budget,
        people_count=people_count,
        poi_sources=[POISource.overpass_osm.value],
    )
    summary = dict(itinerary.get("score_summary") or {})
    summary.update(
        {
            "osm_ingestion_used": True,
            "osm_saved_poi_count": saved_count,
            "destination_created_for_admin_review": created_destination,
            "destination_active": bool(destination.is_active),
        }
    )
    itinerary["score_summary"] = summary
    itinerary["source"] = "osm-ingested-heuristic"
    itinerary["model_version"] = f"{itinerary.get('model_version', 'orienteering-heuristic-v2')}:osm-ingested"
    itinerary["destination_id"] = str(destination.id)
    for variant in itinerary.get("variants", []):
        variant_summary = dict(variant.get("score_summary") or {})
        variant_summary.update(summary)
        variant["score_summary"] = variant_summary
        variant["source"] = "osm-ingested-heuristic"
        variant["model_version"] = f"{variant.get('model_version', 'orienteering-heuristic-v2')}:osm-ingested"
        variant["destination_id"] = str(destination.id)
    return itinerary


def approve_destination_ingestion_request(db: Session, request_id: uuid.UUID) -> dict[str, Any] | None:
    request = db.query(DestinationIngestionRequest).filter(DestinationIngestionRequest.id == request_id).first()
    if request is None:
        return None
    destination = db.query(Destination).filter(Destination.id == request.destination_id).first()
    if destination is None:
        return None
    destination.is_active = True
    request.status = DestinationIngestionStatus.approved
    db.commit()
    db.refresh(request)
    return _request_payload(request, destination)


def list_destination_ingestion_requests(db: Session, status: str = "pending") -> list[dict[str, Any]]:
    query = db.query(DestinationIngestionRequest).order_by(DestinationIngestionRequest.created_at.desc())
    if status:
        query = query.filter(DestinationIngestionRequest.status == status)
    requests = query.limit(100).all()
    destinations = {
        destination.id: destination
        for destination in db.query(Destination)
        .filter(Destination.id.in_([request.destination_id for request in requests]))
        .all()
    }
    return [_request_payload(request, destinations.get(request.destination_id)) for request in requests]


def _get_or_create_destination(
    db: Session,
    *,
    destination_name: str,
    country_code: str,
    lat: float,
    lng: float,
    radius_m: int,
) -> tuple[Destination, bool]:
    base_name = _destination_base_name(destination_name)
    exact = (
        db.query(Destination)
        .filter(Destination.name.ilike(base_name), Destination.country_code == country_code)
        .first()
    )
    if exact:
        return exact, False

    nearby = [
        destination
        for destination in db.query(Destination).filter(Destination.country_code == country_code).all()
        if _destination_names_match(base_name, destination.name)
        and _haversine_km(lat, lng, float(destination.lat), float(destination.lng)) <= 8.0
    ]
    if nearby:
        nearby.sort(key=lambda item: _haversine_km(lat, lng, float(item.lat), float(item.lng)))
        return nearby[0], False

    destination = Destination(
        name=base_name,
        country_code=country_code,
        lat=lat,
        lng=lng,
        region=None,
        subregion=None,
        capital=False,
        population=None,
        currencies={},
        is_active=False,
        radius_m=radius_m,
    )
    db.add(destination)
    db.flush()
    return destination, True


def _save_osm_poi(db: Session, destination: Destination, raw_poi: list[dict[str, Any]]) -> int:
    saved = 0
    for item in raw_poi:
        external_id = str(item.get("external_id") or "")
        if not external_id:
            external_id = "osm:auto:" + str(uuid.uuid5(uuid.NAMESPACE_URL, compact_poi_key(item)))
        name = str(item.get("name") or "").strip()
        lat = _float_or_none(item.get("lat"))
        lng = _float_or_none(item.get("lon") or item.get("lng"))
        if not name or lat is None or lng is None:
            continue
        existing = db.query(POI).filter(POI.source == POISource.overpass_osm, POI.external_id == external_id).first()
        if existing:
            _refresh_osm_poi(existing, destination, item, name, lat, lng)
            _repair_similar_catalog_poi(db, destination, item, name, lat, lng)
            saved += 1
            continue
        _repair_similar_catalog_poi(db, destination, item, name, lat, lng)
        db.add(
            POI(
                name=name[:300],
                lat=lat,
                lng=lng,
                category=str(item.get("category") or "place")[:100],
                destination_id=destination.id,
                source=POISource.overpass_osm,
                external_id=external_id[:200],
                rating=None,
                popularity_score=max(0.1, min(1.0, float(item.get("score") or 1.0) / 3.0)),
                address=item.get("fullAddress") or item.get("address"),
                description=None,
                tags=_tags_payload(item.get("tags")),
                visit_duration_minutes=_duration_for_category(str(item.get("category") or "")),
                opening_hours=None,
                price_tier=None,
                entrance_fee_usd=None,
                fee_notes=None,
            )
        )
        saved += 1
    return saved


def _refresh_osm_poi(
    poi: POI,
    destination: Destination,
    item: dict[str, Any],
    name: str,
    lat: float,
    lng: float,
) -> None:
    poi.destination_id = destination.id
    poi.name = name[:300]
    poi.lat = lat
    poi.lng = lng
    poi.category = str(item.get("category") or poi.category or "place")[:100]
    poi.address = item.get("fullAddress") or item.get("address") or poi.address
    poi.tags = _tags_payload(item.get("tags")) or poi.tags
    poi.visit_duration_minutes = poi.visit_duration_minutes or _duration_for_category(poi.category)
    poi.popularity_score = max(
        float(poi.popularity_score or 0.0), max(0.1, min(1.0, float(item.get("score") or 1.0) / 3.0))
    )


def _repair_similar_catalog_poi(
    db: Session,
    destination: Destination,
    item: dict[str, Any],
    name: str,
    lat: float,
    lng: float,
) -> None:
    normalized_name = _normalize_poi_name(name)
    if not normalized_name:
        return
    candidates = (
        db.query(POI)
        .filter(POI.destination_id == destination.id, POI.source != POISource.overpass_osm)
        .limit(200)
        .all()
    )
    destination_lat = float(destination.lat)
    destination_lng = float(destination.lng)
    for candidate in candidates:
        if not _poi_names_match(normalized_name, _normalize_poi_name(candidate.name)):
            continue
        old_distance = _haversine_km(destination_lat, destination_lng, float(candidate.lat), float(candidate.lng))
        new_distance = _haversine_km(destination_lat, destination_lng, lat, lng)
        old_to_new_distance = _haversine_km(float(candidate.lat), float(candidate.lng), lat, lng)
        if old_to_new_distance < 0.2:
            continue
        if old_distance <= new_distance + 1.0 and old_distance <= max(float(destination.radius_m) / 1000.0, 3.0):
            continue
        candidate.lat = lat
        candidate.lng = lng
        candidate.category = str(item.get("category") or candidate.category or "place")[:100]
        candidate.address = item.get("fullAddress") or item.get("address") or candidate.address
        candidate.tags = sorted(
            {*list(candidate.tags or []), *_tags_payload(item.get("tags")), "coordinate_repaired_from:overpass_osm"}
        )[:40]
        candidate.visit_duration_minutes = candidate.visit_duration_minutes or _duration_for_category(
            candidate.category
        )
        candidate.popularity_score = max(
            float(candidate.popularity_score or 0.0),
            max(0.1, min(1.0, float(item.get("score") or 1.0) / 3.0)),
        )
        return


def _ensure_ingestion_request(
    db: Session,
    *,
    destination: Destination,
    destination_name: str,
    country_code: str,
    poi_count: int,
) -> None:
    existing = (
        db.query(DestinationIngestionRequest)
        .filter(
            DestinationIngestionRequest.destination_id == destination.id,
            DestinationIngestionRequest.source == "osm_external_route",
            DestinationIngestionRequest.status == DestinationIngestionStatus.pending,
        )
        .first()
    )
    if existing:
        metadata = dict(existing.request_metadata or {})
        metadata["poi_count"] = max(int(metadata.get("poi_count") or 0), poi_count)
        metadata["lat"] = destination.lat
        metadata["lng"] = destination.lng
        metadata["radius_m"] = destination.radius_m
        existing.request_metadata = metadata
        return
    db.add(
        DestinationIngestionRequest(
            destination_id=destination.id,
            requested_name=destination_name[:200],
            requested_country_code=country_code,
            status=DestinationIngestionStatus.pending,
            source="osm_external_route",
            reason="Destination was created from a successful live OSM route ingestion and needs admin approval.",
            request_metadata={
                "poi_count": poi_count,
                "lat": destination.lat,
                "lng": destination.lng,
                "radius_m": destination.radius_m,
            },
        )
    )


def _request_payload(
    request: DestinationIngestionRequest,
    destination: Destination | None,
) -> dict[str, Any]:
    return {
        "id": str(request.id),
        "destination_id": str(request.destination_id),
        "requested_name": request.requested_name,
        "requested_country_code": request.requested_country_code,
        "status": request.status,
        "source": request.source,
        "reason": request.reason,
        "request_metadata": request.request_metadata,
        "destination": {
            "name": destination.name,
            "country_code": destination.country_code,
            "lat": destination.lat,
            "lng": destination.lng,
            "is_active": destination.is_active,
        }
        if destination
        else None,
        "created_at": request.created_at.isoformat() if request.created_at else None,
        "updated_at": request.updated_at.isoformat() if request.updated_at else None,
    }


def _destination_base_name(destination_name: str) -> str:
    return destination_name.split(",", 1)[0].strip()[:200] or "Unknown destination"


def _destination_names_match(left: str, right: str) -> bool:
    left_normalized = _normalize_poi_name(left)
    right_normalized = _normalize_poi_name(right)
    if not left_normalized or not right_normalized:
        return False
    if left_normalized == right_normalized:
        return True
    return left_normalized in right_normalized or right_normalized in left_normalized


def _country_code_from_destination_text(destination_name: str) -> str:
    normalized = destination_name.casefold()
    for alias, code in _COUNTRY_ALIASES.items():
        if alias in normalized:
            return code
    parts = [part.strip() for part in re.split(r",|\\(|\\)", destination_name) if part.strip()]
    for part in reversed(parts):
        country = pycountry.countries.get(name=part)
        if country:
            return str(country.alpha_2)
    return "XX"


def _tags_payload(tags: Any) -> list[str]:
    if not isinstance(tags, dict):
        return []
    return [f"{key}:{value}"[:120] for key, value in sorted(tags.items()) if isinstance(value, str)][:30]


def _duration_for_category(category: str) -> int:
    normalized = category.casefold()
    if normalized in {"museum", "theme_park", "family"}:
        return 150
    if normalized in {"beach", "park", "marina"}:
        return 120
    return 75


def _normalize_poi_name(value: str) -> str:
    normalized = value.casefold().replace("&", " and ")
    normalized = normalized.replace("portaventura", "port aventura")
    normalized = re.sub(r"[^a-zа-яё0-9]+", " ", normalized)
    stop_words = {"world", "park", "parque", "theme", "the", "de", "la", "el"}
    tokens = [token for token in normalized.split() if token not in stop_words]
    return " ".join(tokens)


def _poi_names_match(left: str, right: str) -> bool:
    if not left or not right:
        return False
    if left == right:
        return True
    left_tokens = set(left.split())
    right_tokens = set(right.split())
    if not left_tokens or not right_tokens:
        return False
    overlap = len(left_tokens & right_tokens)
    return overlap >= min(len(left_tokens), len(right_tokens), 2)


def compact_poi_key(item: dict[str, Any]) -> str:
    return f"{item.get('name')}|{item.get('lat')}|{item.get('lon') or item.get('lng')}"


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    radius_km = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lng2 - lng1)
    value = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    return 2 * radius_km * math.atan2(math.sqrt(value), math.sqrt(1 - value))
