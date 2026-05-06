"""Backfill Russian display names into name_translations overlay.

The script does not modify destinations.name or poi.name. It stores authoritative
Russian labels when external sources expose them and leaves unresolved rows
untouched so the UI can safely fall back to original names.

Examples:
  python scripts/backfill_name_translations.py destinations --limit 50
  python scripts/backfill_name_translations.py poi --limit 1000 --batch-size 100 --missing-only
  python scripts/backfill_name_translations.py poi --source opentripmap --missing-only --destination-limit 25
  python scripts/backfill_name_translations.py poi --destination-limit 25 --missing-only --use-osm-fallback
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import re
import sys
import time
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, TypeVar

import httpx
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert

sys.path.insert(0, "/app")

from app.config import settings
from app.database import SessionLocal
from app.lib.russian_names import translate_destination_name
from app.models import (
    POI,
    Destination,
    NameTranslation,
    NameTranslationEntity,
    NameTranslationQuality,
    POISource,
)

WIKIDATA_SPARQL_URL = "https://query.wikidata.org/sparql"
WIKIDATA_ENTITY_URL = "https://www.wikidata.org/w/api.php"
OPENTRIPMAP_DETAILS_URL = "https://api.opentripmap.com/0.1/ru/places/xid/{xid}"
OVERPASS_SERVERS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
NOMINATIM_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"
HEADERS = {"User-Agent": "TriplyDiploma/1.0 (name translation backfill)"}
STATE_FILE = Path("/app/data/state/name_translation_progress.json")
POI_STATE_KEY = "poi_name_translations_v2"
MAX_RETRIES = 3
SLEEP_ON_RATE_LIMIT = 60.0
OPENTRIPMAP_DAILY_REQUEST_LIMIT = 950

CYRILLIC_RE = re.compile("[А-Яа-яЁё]")
WIKIDATA_RE = re.compile(r"Q\d+")
GENERIC_POI_NAMES = {
    "attraction",
    "beach",
    "cafe",
    "café",
    "castle",
    "cave",
    "church",
    "garden",
    "hot spring",
    "mall",
    "market",
    "memorial",
    "monument",
    "museum",
    "park",
    "peak",
    "restaurant",
    "ruins",
    "spa",
    "theatre",
    "viewpoint",
    "waterfall",
}
T = TypeVar("T")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
logger = logging.getLogger(__name__)


@dataclass
class TranslationCandidate:
    entity_id: uuid.UUID
    original_name: str
    translated_name: str
    provider: str
    provider_ref: str | None
    quality: NameTranslationQuality
    confidence: float
    metadata: dict[str, Any]


class TransientProviderError(RuntimeError):
    """External provider failed in a way that should be retried in a later run."""


def has_cyrillic(value: str | None) -> bool:
    return bool(value and CYRILLIC_RE.search(value))


def _load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            logger.warning("Could not parse %s; starting with empty state", STATE_FILE)
    return {}


def _save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def chunks(items: list[T], size: int) -> Iterable[list[T]]:
    for index in range(0, len(items), size):
        yield items[index : index + size]


def _normalize_name(value: str) -> str:
    value = value.lower().replace("&", "and")
    return re.sub(r"[^a-zа-яё0-9]+", "", value)


def _distance_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    radius_km = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    return radius_km * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _request_with_retry(
    client: httpx.Client,
    method: str,
    url: str,
    *,
    timeout: float,
    retry_429: bool = True,
    retry_504: bool = True,
    **kwargs: Any,
) -> httpx.Response:
    last_error: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.request(method, url, timeout=timeout, **kwargs)
            if response.status_code == 429 and retry_429:
                wait = SLEEP_ON_RATE_LIMIT * attempt
                logger.warning("429 from %s attempt %s/%s; sleep %.1fs", url, attempt, MAX_RETRIES, wait)
                time.sleep(wait)
                continue
            if response.status_code == 504 and retry_504:
                wait = 30.0 * attempt
                logger.warning("504 from %s attempt %s/%s; sleep %.1fs", url, attempt, MAX_RETRIES, wait)
                time.sleep(wait)
                continue
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as exc:
            if 400 <= exc.response.status_code < 500:
                raise
            last_error = exc
            if attempt == MAX_RETRIES:
                break
            time.sleep(10.0 * attempt)
        except httpx.HTTPError as exc:
            last_error = exc
            if attempt == MAX_RETRIES:
                break
            time.sleep(10.0 * attempt)
    raise TransientProviderError(str(last_error or "provider request failed"))


def upsert_translations(entity_type: NameTranslationEntity, rows: list[TranslationCandidate]) -> int:
    if not rows:
        return 0

    payload = [
        {
            "id": uuid.uuid4(),
            "entity_type": entity_type,
            "entity_id": row.entity_id,
            "locale": "ru",
            "original_name": row.original_name,
            "translated_name": row.translated_name,
            "provider": row.provider,
            "provider_ref": row.provider_ref,
            "quality": row.quality,
            "confidence": row.confidence,
            "translation_metadata": row.metadata,
        }
        for row in rows
        if row.translated_name and (row.translated_name != row.original_name or row.provider == "source_cyrillic")
    ]
    if not payload:
        return 0

    with SessionLocal() as db:
        stmt = insert(NameTranslation).values(payload)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_name_translation_entity_locale",
            set_={
                "original_name": stmt.excluded.original_name,
                "translated_name": stmt.excluded.translated_name,
                "provider": stmt.excluded.provider,
                "provider_ref": stmt.excluded.provider_ref,
                "quality": stmt.excluded.quality,
                "confidence": stmt.excluded.confidence,
                "translation_metadata": stmt.excluded.translation_metadata,
                "updated_at": text("now()"),
            },
        )
        db.execute(stmt)
        db.commit()
    return len(payload)


def wikidata_destination_label(client: httpx.Client, name: str, country_code: str | None) -> tuple[str, str] | None:
    escaped_name = json.dumps(name)
    country_filter = ""
    if country_code:
        country_filter = f'?country wdt:P297 "{country_code.upper()}" .'
    query = f"""
    SELECT ?item ?itemLabelRu WHERE {{
      ?item rdfs:label {escaped_name}@en .
      OPTIONAL {{ ?item wdt:P17 ?country . }}
      {country_filter}
      ?item rdfs:label ?itemLabelRu FILTER(LANG(?itemLabelRu) = "ru") .
    }}
    LIMIT 1
    """
    response = client.get(
        WIKIDATA_SPARQL_URL,
        params={"query": query, "format": "json"},
        headers=HEADERS,
        timeout=20,
    )
    response.raise_for_status()
    bindings = response.json().get("results", {}).get("bindings", [])
    if not bindings:
        return None
    item = bindings[0]["item"]["value"].rsplit("/", 1)[-1]
    label = bindings[0]["itemLabelRu"]["value"]
    return label, item


def nominatim_destination_label(client: httpx.Client, lat: float, lng: float) -> str | None:
    response = client.get(
        NOMINATIM_REVERSE_URL,
        params={
            "format": "jsonv2",
            "lat": lat,
            "lon": lng,
            "zoom": 10,
            "accept-language": "ru",
        },
        headers=HEADERS,
        timeout=20,
    )
    response.raise_for_status()
    data = response.json()
    address = data.get("address") or {}
    for key in ("city", "town", "village", "municipality", "island", "tourism", "county", "state"):
        value = address.get(key)
        if value and has_cyrillic(value):
            return str(value)
    display_name = data.get("display_name")
    if display_name and has_cyrillic(display_name):
        return str(display_name).split(",", 1)[0].strip()
    return None


def backfill_destinations(limit: int | None, sleep_seconds: float, missing_only: bool) -> None:
    with SessionLocal() as db:
        q = db.query(Destination).filter(Destination.is_active == True)  # noqa: E712
        if missing_only:
            q = q.filter(
                ~db.query(NameTranslation.id)
                .filter(
                    NameTranslation.entity_type == NameTranslationEntity.destination,
                    NameTranslation.locale == "ru",
                    NameTranslation.entity_id == Destination.id,
                )
                .exists()
            )
        q = q.order_by(Destination.name)
        if limit:
            q = q.limit(limit)
        destinations = q.all()

    saved = 0
    unresolved = 0
    with httpx.Client() as client:
        for destination in destinations:
            if has_cyrillic(destination.name):
                candidate = TranslationCandidate(
                    entity_id=destination.id,
                    original_name=destination.name,
                    translated_name=destination.name,
                    provider="source_cyrillic",
                    provider_ref=None,
                    quality=NameTranslationQuality.authoritative,
                    confidence=1.0,
                    metadata={},
                )
                saved += upsert_translations(NameTranslationEntity.destination, [candidate])
                continue

            try:
                resolved = wikidata_destination_label(client, destination.name, destination.country_code)
            except Exception as exc:
                print(f"[dest] error {destination.name}: {exc}")
                unresolved += 1
                time.sleep(sleep_seconds)
                continue

            if resolved and has_cyrillic(resolved[0]) and resolved[0] != destination.name:
                label, wikidata_id = resolved
                candidate = TranslationCandidate(
                    entity_id=destination.id,
                    original_name=destination.name,
                    translated_name=label,
                    provider="wikidata_ru_label",
                    provider_ref=wikidata_id,
                    quality=NameTranslationQuality.authoritative,
                    confidence=0.98,
                    metadata={"country_code": destination.country_code},
                )
                saved += upsert_translations(NameTranslationEntity.destination, [candidate])
            else:
                local_name = translate_destination_name(destination.name)
                if local_name and local_name != destination.name:
                    candidate = TranslationCandidate(
                        entity_id=destination.id,
                        original_name=destination.name,
                        translated_name=local_name,
                        provider="local_curated",
                        provider_ref=None,
                        quality=NameTranslationQuality.manual,
                        confidence=0.9,
                        metadata={"country_code": destination.country_code},
                    )
                    saved += upsert_translations(NameTranslationEntity.destination, [candidate])
                else:
                    try:
                        nominatim_name = nominatim_destination_label(client, destination.lat, destination.lng)
                    except Exception:
                        nominatim_name = None
                    if nominatim_name and nominatim_name != destination.name:
                        candidate = TranslationCandidate(
                            entity_id=destination.id,
                            original_name=destination.name,
                            translated_name=nominatim_name,
                            provider="nominatim_reverse_ru",
                            provider_ref=None,
                            quality=NameTranslationQuality.authoritative,
                            confidence=0.86,
                            metadata={
                                "country_code": destination.country_code,
                                "lat": destination.lat,
                                "lng": destination.lng,
                            },
                        )
                        saved += upsert_translations(NameTranslationEntity.destination, [candidate])
                    else:
                        unresolved += 1
                        print(f"[dest] unresolved {destination.name} ({destination.country_code})")
            time.sleep(sleep_seconds)

    print(f"destinations saved={saved} unresolved={unresolved} total={len(destinations)}")


def _osm_type_from_external_id(external_id: str, source: POISource) -> tuple[str | None, str | None]:
    value = external_id.strip()
    if source == POISource.opentripmap and len(value) > 1:
        prefix = value[0].upper()
        osm_type = {"N": "node", "W": "way", "R": "relation"}.get(prefix)
        if osm_type and value[1:].isdigit():
            return osm_type, value[1:]
    if source == POISource.overpass_osm and value.startswith("osm:") and value[4:].isdigit():
        return None, value[4:]
    return None, None


def _overpass_query(ids_by_type: dict[str, list[str]], ambiguous_ids: list[str]) -> str:
    parts: list[str] = []
    for osm_type, ids in ids_by_type.items():
        if ids:
            parts.append(f"{osm_type}(id:{','.join(ids)});")
    if ambiguous_ids:
        joined = ",".join(ambiguous_ids)
        parts.extend([f"node(id:{joined});", f"way(id:{joined});", f"relation(id:{joined});"])
    return f"[out:json][timeout:60];({''.join(parts)});out tags;"


def _wikidata_labels(client: httpx.Client, ids: list[str]) -> dict[str, str]:
    labels: dict[str, str] = {}
    for batch in chunks(sorted(set(ids)), 50):
        response = _request_with_retry(
            client,
            "GET",
            WIKIDATA_ENTITY_URL,
            params={
                "action": "wbgetentities",
                "ids": "|".join(batch),
                "props": "labels",
                "languages": "ru",
                "format": "json",
            },
            headers=HEADERS,
            timeout=20,
        )
        response.raise_for_status()
        entities = response.json().get("entities", {})
        for qid, entity in entities.items():
            label = entity.get("labels", {}).get("ru", {}).get("value")
            if label:
                labels[qid] = label
    return labels


def _wikidata_poi_candidates(client: httpx.Client, pois: list[POI]) -> list[TranslationCandidate]:
    candidates: list[TranslationCandidate] = []
    for poi in pois:
        original_norm = _normalize_name(poi.name)
        if len(original_norm) < 4 or poi.name.strip().lower() in GENERIC_POI_NAMES:
            continue

        response = _request_with_retry(
            client,
            "GET",
            WIKIDATA_ENTITY_URL,
            params={
                "action": "wbsearchentities",
                "search": poi.name,
                "language": "en",
                "uselang": "ru",
                "limit": 5,
                "format": "json",
            },
            headers=HEADERS,
            timeout=20,
        )
        search_results = response.json().get("search", [])
        qids = [item.get("id") for item in search_results if item.get("id")]
        if not qids:
            continue

        entities_response = _request_with_retry(
            client,
            "GET",
            WIKIDATA_ENTITY_URL,
            params={
                "action": "wbgetentities",
                "ids": "|".join(qids),
                "props": "labels|aliases|claims",
                "languages": "ru|en",
                "format": "json",
            },
            headers=HEADERS,
            timeout=20,
        )
        entities = entities_response.json().get("entities", {})
        for qid in qids:
            entity = entities.get(qid) or {}
            labels = entity.get("labels", {})
            ru_label = labels.get("ru", {}).get("value")
            en_label = labels.get("en", {}).get("value")
            if not ru_label or not has_cyrillic(ru_label):
                continue

            aliases = entity.get("aliases", {}).get("en", [])
            en_names = [en_label, *[alias.get("value") for alias in aliases]]
            if original_norm not in {_normalize_name(name) for name in en_names if name}:
                continue

            coordinate_claims = entity.get("claims", {}).get("P625", [])
            distance_km: float | None = None
            if coordinate_claims:
                value = coordinate_claims[0].get("mainsnak", {}).get("datavalue", {}).get("value", {})
                if value.get("latitude") is not None and value.get("longitude") is not None:
                    distance_km = _distance_km(poi.lat, poi.lng, float(value["latitude"]), float(value["longitude"]))
                    if distance_km > 75:
                        continue

            candidates.append(
                TranslationCandidate(
                    entity_id=poi.id,
                    original_name=poi.name,
                    translated_name=ru_label,
                    provider="wikidata_search_ru_label",
                    provider_ref=qid,
                    quality=NameTranslationQuality.authoritative,
                    confidence=0.95 if distance_km is not None else 0.88,
                    metadata={
                        "source": poi.source.value,
                        "category": poi.category,
                        "distance_km": round(distance_km, 2) if distance_km is not None else None,
                    },
                )
            )
            break
    return candidates


def _opentripmap_poi_candidates(
    client: httpx.Client,
    pois: list[POI],
    requests_remaining: int,
) -> tuple[list[TranslationCandidate], int]:
    if not settings.OPENTRIPMAP_API_KEY or requests_remaining <= 0:
        return [], 0

    candidates: list[TranslationCandidate] = []
    requests_used = 0
    for poi in pois:
        if requests_used >= requests_remaining:
            break
        if poi.source != POISource.opentripmap or not poi.external_id:
            continue
        try:
            response = _request_with_retry(
                client,
                "GET",
                OPENTRIPMAP_DETAILS_URL.format(xid=poi.external_id),
                params={"apikey": settings.OPENTRIPMAP_API_KEY},
                headers=HEADERS,
                timeout=20,
                retry_504=False,
            )
        except TransientProviderError:
            raise
        except Exception:
            continue

        requests_used += 1
        data = response.json()
        label = data.get("name")
        if not label or not has_cyrillic(label) or label == poi.name:
            continue

        candidates.append(
            TranslationCandidate(
                entity_id=poi.id,
                original_name=poi.name,
                translated_name=str(label),
                provider="opentripmap_ru_details",
                provider_ref=poi.external_id,
                quality=NameTranslationQuality.authoritative,
                confidence=0.92,
                metadata={"source": poi.source.value, "category": poi.category},
            )
        )
    return candidates, requests_used


def _poi_candidates_from_overpass(client: httpx.Client, pois: list[POI]) -> list[TranslationCandidate]:
    ids_by_type: dict[str, list[str]] = {"node": [], "way": [], "relation": []}
    ambiguous_ids: list[str] = []
    poi_by_osm_id: dict[str, list[POI]] = {}
    for poi in pois:
        osm_type, osm_id = _osm_type_from_external_id(poi.external_id, poi.source)
        if not osm_id:
            continue
        poi_by_osm_id.setdefault(osm_id, []).append(poi)
        if osm_type:
            ids_by_type[osm_type].append(osm_id)
        else:
            ambiguous_ids.append(osm_id)

    if not any(ids_by_type.values()) and not ambiguous_ids:
        return []

    query = _overpass_query(ids_by_type, ambiguous_ids)
    last_error: Exception | None = None
    elements: list[dict[str, Any]] = []
    for attempt in range(1, MAX_RETRIES + 1):
        server = OVERPASS_SERVERS[(attempt - 1) % len(OVERPASS_SERVERS)]
        try:
            response = _request_with_retry(
                client,
                "POST",
                server,
                data={"data": query},
                headers=HEADERS,
                timeout=90,
            )
            elements = response.json().get("elements", [])
            break
        except TransientProviderError as exc:
            last_error = exc
            logger.warning("Overpass failed on %s attempt %s/%s: %s", server, attempt, MAX_RETRIES, exc)
    else:
        raise TransientProviderError(f"Overpass unavailable: {last_error}")

    qids: list[str] = []
    resolved: list[tuple[POI, str, str, str | None, dict[str, Any]]] = []
    for element in elements:
        osm_id = str(element.get("id"))
        tags = element.get("tags") or {}
        label = tags.get("name:ru")
        wikidata = tags.get("wikidata")
        if wikidata and WIKIDATA_RE.fullmatch(wikidata):
            qids.append(wikidata)
        if not label and tags.get("wikipedia", "").startswith("ru:"):
            label = tags["wikipedia"].split(":", 1)[1].replace("_", " ")
        for poi in poi_by_osm_id.get(osm_id, []):
            if label:
                resolved.append((poi, label, "osm_name_ru", osm_id, {"osm_type": element.get("type")}))
            elif wikidata:
                resolved.append((poi, wikidata, "wikidata_pending", wikidata, {"osm_type": element.get("type")}))

    wikidata_labels = _wikidata_labels(client, qids) if qids else {}
    candidates: list[TranslationCandidate] = []
    for poi, value, provider, provider_ref, metadata in resolved:
        label = wikidata_labels.get(value, value) if provider == "wikidata_pending" else value
        if provider == "wikidata_pending" and label == value:
            continue
        candidates.append(
            TranslationCandidate(
                entity_id=poi.id,
                original_name=poi.name,
                translated_name=label,
                provider="wikidata_ru_label" if provider == "wikidata_pending" else provider,
                provider_ref=provider_ref,
                quality=NameTranslationQuality.authoritative,
                confidence=0.98,
                metadata=metadata,
            )
        )
    return candidates


def _poi_query(db, destination_id: uuid.UUID, source: str | None, missing_only: bool, after_id: uuid.UUID | None):
    q = db.query(POI).filter(POI.destination_id == destination_id)
    if after_id is not None:
        q = q.filter(POI.id > after_id)
    if source:
        q = q.filter(POI.source == POISource(source))
    if missing_only:
        q = q.filter(
            ~db.query(NameTranslation.id)
            .filter(
                NameTranslation.entity_type == NameTranslationEntity.poi,
                NameTranslation.locale == "ru",
                NameTranslation.entity_id == POI.id,
            )
            .exists()
        )
    return q.order_by(POI.id)


def _process_poi_batch(
    client: httpx.Client,
    batch: list[POI],
    use_opentripmap: bool,
    opentripmap_requests_remaining: int,
    use_osm_fallback: bool,
) -> tuple[int, int]:
    local_candidates = [
        TranslationCandidate(
            entity_id=poi.id,
            original_name=poi.name,
            translated_name=poi.name,
            provider="source_cyrillic",
            provider_ref=poi.external_id,
            quality=NameTranslationQuality.authoritative,
            confidence=1.0,
            metadata={"source": poi.source.value},
        )
        for poi in batch
        if has_cyrillic(poi.name)
    ]
    unresolved = [poi for poi in batch if not has_cyrillic(poi.name)]
    opentripmap_candidates: list[TranslationCandidate] = []
    opentripmap_requests_used = 0
    if use_opentripmap:
        opentripmap_candidates, opentripmap_requests_used = _opentripmap_poi_candidates(
            client,
            unresolved,
            opentripmap_requests_remaining,
        )
    resolved_ids = {candidate.entity_id for candidate in opentripmap_candidates}

    wikidata_candidates = _wikidata_poi_candidates(client, [poi for poi in unresolved if poi.id not in resolved_ids])
    resolved_ids.update(candidate.entity_id for candidate in wikidata_candidates)

    osm_candidates: list[TranslationCandidate] = []
    if use_osm_fallback:
        osm_candidates = _poi_candidates_from_overpass(
            client,
            [poi for poi in unresolved if poi.id not in resolved_ids],
        )

    saved = upsert_translations(
        NameTranslationEntity.poi,
        local_candidates + opentripmap_candidates + wikidata_candidates + osm_candidates,
    )
    return saved, opentripmap_requests_used


def backfill_poi(
    limit: int | None,
    batch_size: int,
    sleep_seconds: float,
    source: str | None,
    missing_only: bool,
    use_osm_fallback: bool,
    use_opentripmap: bool,
    skip_completed: bool,
    reset_state: bool,
    destination_limit: int | None,
) -> None:
    state = _load_state()
    job = state.setdefault(
        POI_STATE_KEY,
        {
            "completed_destinations": [],
            "failed_destinations": {},
            "total_saved": 0,
            "total_scanned": 0,
            "opentripmap_requests_today": 0,
            "last_run_date": None,
        },
    )
    today = date.today().isoformat()
    if job.get("last_run_date") != today:
        job["opentripmap_requests_today"] = 0
    if reset_state:
        job["completed_destinations"] = []
        job["failed_destinations"] = {}
        job["total_saved"] = 0
        job["total_scanned"] = 0
        job["opentripmap_requests_today"] = 0
        _save_state(state)
        logger.info("POI translation state reset")

    completed_ids = set(job.get("completed_destinations", [])) if skip_completed else set()

    with SessionLocal() as db:
        destinations = (
            db.query(Destination)
            .filter(Destination.is_active == True)  # noqa: E712
            .order_by(Destination.name)
            .all()
        )

    pending_destinations = [destination for destination in destinations if str(destination.id) not in completed_ids]
    if destination_limit is not None:
        pending_destinations = pending_destinations[:destination_limit]

    saved = 0
    scanned = 0
    errors = 0
    logger.info(
        "POI translations: %s destinations pending / %s completed, providers=source_cyrillic%s,wikidata%s",
        len(pending_destinations),
        len(completed_ids),
        ",opentripmap" if use_opentripmap and settings.OPENTRIPMAP_API_KEY else "",
        ",overpass_fallback" if use_osm_fallback else "",
    )

    with httpx.Client() as client:
        for index, destination in enumerate(pending_destinations, 1):
            if limit is not None and scanned >= limit:
                break

            dest_id = str(destination.id)
            logger.info("[%s/%s] %s (%s)", index, len(pending_destinations), destination.name, destination.country_code)
            destination_failed = False
            destination_scanned = 0
            destination_saved = 0
            cursor_id: uuid.UUID | None = None
            stopped_by_limit = False

            while True:
                remaining = None if limit is None else max(limit - scanned, 0)
                if remaining == 0:
                    stopped_by_limit = True
                    break
                current_batch_size = min(batch_size, remaining) if remaining is not None else batch_size
                with SessionLocal() as db:
                    batch = (
                        _poi_query(db, destination.id, source, missing_only, cursor_id).limit(current_batch_size).all()
                    )
                if not batch:
                    break
                cursor_id = batch[-1].id

                try:
                    otm_remaining = max(
                        OPENTRIPMAP_DAILY_REQUEST_LIMIT - int(job.get("opentripmap_requests_today", 0)),
                        0,
                    )
                    saved_now, otm_used = _process_poi_batch(
                        client,
                        batch,
                        use_opentripmap,
                        otm_remaining,
                        use_osm_fallback,
                    )
                    job["opentripmap_requests_today"] = int(job.get("opentripmap_requests_today", 0)) + otm_used
                    saved += saved_now
                    destination_saved += saved_now
                    scanned += len(batch)
                    destination_scanned += len(batch)
                    logger.info("  batch scanned=%s saved=%s otm_requests=%s", len(batch), saved_now, otm_used)
                    job["last_run_date"] = today
                    _save_state(state)
                except TransientProviderError as exc:
                    errors += 1
                    destination_failed = True
                    job.setdefault("failed_destinations", {})[dest_id] = {
                        "name": destination.name,
                        "error": str(exc),
                        "last_failed_at": date.today().isoformat(),
                    }
                    _save_state(state)
                    logger.warning("  provider error; destination will be retried next run: %s", exc)
                    break
                except Exception as exc:
                    errors += 1
                    destination_failed = True
                    job.setdefault("failed_destinations", {})[dest_id] = {
                        "name": destination.name,
                        "error": str(exc),
                        "last_failed_at": date.today().isoformat(),
                    }
                    _save_state(state)
                    logger.exception("  unexpected batch error; destination will be retried next run")
                    break

                time.sleep(sleep_seconds)

            if destination_failed:
                time.sleep(sleep_seconds)
                continue
            if stopped_by_limit:
                job["total_saved"] = int(job.get("total_saved", 0)) + destination_saved
                job["total_scanned"] = int(job.get("total_scanned", 0)) + destination_scanned
                job["last_run_date"] = today
                _save_state(state)
                logger.info("  stopped by run limit; destination is not marked completed")
                break

            job.setdefault("failed_destinations", {}).pop(dest_id, None)
            if dest_id not in job["completed_destinations"]:
                job["completed_destinations"].append(dest_id)
            job["total_saved"] = int(job.get("total_saved", 0)) + destination_saved
            job["total_scanned"] = int(job.get("total_scanned", 0)) + destination_scanned
            job["last_run_date"] = today
            _save_state(state)
            logger.info("  completed destination; scanned=%s", destination_scanned)

    print(f"poi saved={saved} errors={errors} scanned={scanned} destinations={len(pending_destinations)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="mode", required=True)

    dest_parser = sub.add_parser("destinations")
    dest_parser.add_argument("--limit", type=int)
    dest_parser.add_argument("--sleep", type=float, default=0.2)
    dest_parser.add_argument("--missing-only", action="store_true")

    poi_parser = sub.add_parser("poi")
    poi_parser.add_argument("--limit", type=int)
    poi_parser.add_argument("--batch-size", type=int, default=100)
    poi_parser.add_argument("--sleep", type=float, default=1.0)
    poi_parser.add_argument("--source", choices=[item.value for item in POISource])
    poi_parser.add_argument("--missing-only", action="store_true")
    poi_parser.add_argument("--destination-limit", type=int)
    poi_parser.add_argument("--no-opentripmap", action="store_true")
    poi_parser.add_argument("--use-osm-fallback", action="store_true")
    poi_parser.add_argument("--no-skip-completed", action="store_true")
    poi_parser.add_argument("--reset-state", action="store_true")

    args = parser.parse_args()
    if args.mode == "destinations":
        backfill_destinations(args.limit, args.sleep, args.missing_only)
    else:
        backfill_poi(
            args.limit,
            args.batch_size,
            args.sleep,
            args.source,
            args.missing_only,
            args.use_osm_fallback,
            not args.no_opentripmap,
            not args.no_skip_completed,
            args.reset_state,
            args.destination_limit,
        )


if __name__ == "__main__":
    main()
