"""Extract recurring annual events from Wikidata via SPARQL endpoint.

Strategy (2-phase):
  Phase 1: Batch-resolve ISO-2 country codes → Wikidata QIDs (one query, fast).
  Phase 2: For each country QID, query city-level events (P276→city→P17→country).
           Uses hardcoded QIDs — avoids slow P297 join inside event queries.

Category mapping (Wikidata P31 QID → EventCategory):
  Q132241  festival               → festival
  Q188928  carnival               → carnival
  Q27968055 sports event          → sports
  Q2726537  music festival        → music
  Q1786389  music event           → music
  Q2761147  art exhibition        → arts
  Q200538   cultural event        → festival
  Q105791828 food festival        → food
  Q1191566  religious event       → religious
  Q4504495  annual sporting event → sports
  Q15275719 recurring event       → festival (fallback)
  Q638544   beer festival         → festival
  Q7216866  performing arts fest  → festival
  Q27686    public holiday        → holiday
  Q1069949  national holiday      → holiday

Rate limiting: sleep 0.8s between country queries, 30s timeout, 1 retry.
"""

import logging
import math
import time

import httpx

logger = logging.getLogger(__name__)

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
HEADERS = {
    "User-Agent": "Triply/1.0 (travel-planner; contact: admin@triply.app)",
    "Accept": "application/sparql-results+json",
}
REQUEST_TIMEOUT = 30.0
SLEEP_BETWEEN_COUNTRIES = 0.8

_INSTANCE_OF_CATEGORY: dict[str, str] = {
    "Q132241": "festival",
    "Q188928": "carnival",
    "Q27968055": "sports",
    "Q2726537": "music",
    "Q1786389": "music",
    "Q2761147": "arts",
    "Q200538": "festival",
    "Q105791828": "food",
    "Q1191566": "religious",
    "Q4504495": "sports",
    "Q15275719": "festival",
    "Q638544": "festival",
    "Q7216866": "festival",
    "Q27686": "holiday",
    "Q1069949": "holiday",
    "Q5398426": "festival",
}

_CATEGORY_DEFAULTS: dict[str, tuple[float, float, float]] = {
    "festival": (0.60, 0.40, 0.70),
    "carnival": (0.75, 0.55, 0.80),
    "holiday": (0.65, 0.45, 0.75),
    "religious": (0.45, 0.30, 0.60),
    "sports": (0.70, 0.65, 0.65),
    "music": (0.65, 0.50, 0.70),
    "arts": (0.55, 0.40, 0.65),
    "food": (0.55, 0.35, 0.65),
}

_INSTANCE_VALUES = """
    wd:Q132241 wd:Q188928 wd:Q27968055 wd:Q2726537 wd:Q1786389
    wd:Q2761147 wd:Q200538 wd:Q105791828 wd:Q1191566 wd:Q4504495
    wd:Q15275719 wd:Q638544 wd:Q7216866 wd:Q27686 wd:Q1069949
    wd:Q5398426
"""


def _sparql(query: str, retries: int = 1) -> list[dict]:
    for attempt in range(retries + 1):
        try:
            r = httpx.get(
                SPARQL_ENDPOINT,
                params={"query": query, "format": "json"},
                headers=HEADERS,
                timeout=REQUEST_TIMEOUT,
            )
            if r.status_code == 429:
                logger.warning("SPARQL rate limited — sleeping 15s")
                time.sleep(15.0)
                continue
            r.raise_for_status()
            return r.json().get("results", {}).get("bindings", [])
        except httpx.TimeoutException:
            logger.warning(f"SPARQL timeout (attempt {attempt + 1}/{retries + 1})")
            if attempt < retries:
                time.sleep(5.0)
        except Exception as e:
            logger.warning(f"SPARQL error: {e}")
            break
    return []


def _val(b: dict, key: str) -> str | None:
    node = b.get(key)
    return node.get("value") if node else None


def _month_from_date(date_str: str | None) -> int | None:
    if not date_str:
        return None
    try:
        clean = date_str.lstrip("+")
        parts = clean.split("T")[0].split("-")
        if len(parts) >= 2:
            m = int(parts[1])
            if 1 <= m <= 12:
                return m
    except (ValueError, IndexError):
        pass
    return None


def _map_category(uri: str | None) -> str:
    if not uri:
        return "festival"
    return _INSTANCE_OF_CATEGORY.get(uri.rsplit("/", 1)[-1], "festival")


def _impacts(att_raw: str | None, category: str) -> tuple[float, float, float]:
    crowd, price, relevance = _CATEGORY_DEFAULTS.get(category, (0.55, 0.40, 0.65))
    if att_raw:
        try:
            att = int(float(att_raw))
            if att > 0:
                crowd = min(0.95, max(0.2, round(0.15 * math.log10(att), 2)))
        except (ValueError, TypeError):
            pass
    return crowd, price, relevance


def resolve_country_qids(country_codes: list[str]) -> dict[str, str]:
    """Return {country_code: wikidata_QID} for given ISO-2 codes.

    Uses P297 (ISO 3166-1 alpha-2) + P31=Q3624078 (sovereign state) filter
    to avoid disambiguation items.
    """
    cc_values = " ".join(f'"{cc}"' for cc in country_codes)
    query = f"""
SELECT ?country ?countryCode WHERE {{
  VALUES ?countryCode {{ {cc_values} }}
  ?country wdt:P297 ?countryCode .
  ?country wdt:P31 wd:Q3624078 .
}}
"""
    bindings = _sparql(query)
    result: dict[str, str] = {}
    for b in bindings:
        cc = _val(b, "countryCode") or ""
        qid = (_val(b, "country") or "").rsplit("/", 1)[-1]
        if cc and qid:
            result[cc.upper()] = qid
    logger.info(f"Resolved {len(result)}/{len(country_codes)} country QIDs")
    return result


def fetch_events_for_country_qid(
    country_qid: str,
    country_code: str,
    limit: int = 200,
) -> list[dict]:
    """Fetch city-level events for one country using its Wikidata QID.

    Queries events with explicit city location (P276→city→P17→country_qid).
    Returns at most `limit` events.
    """
    query = f"""
SELECT DISTINCT ?event ?eventLabel ?eventLabelRu ?instanceOf
       ?cityLabel ?startDate ?attendance WHERE {{
  ?event wdt:P31 ?instanceOf .
  VALUES ?instanceOf {{ {_INSTANCE_VALUES} }}
  ?event wdt:P276 ?city .
  ?city wdt:P17 wd:{country_qid} .
  OPTIONAL {{ ?event wdt:P580 ?d1 . }}
  OPTIONAL {{ ?event wdt:P585 ?d2 . }}
  BIND(COALESCE(?d1, ?d2) AS ?startDate)
  FILTER(BOUND(?startDate))
  ?event rdfs:label ?eventLabel . FILTER(LANG(?eventLabel) = "en")
  OPTIONAL {{ ?event rdfs:label ?eventLabelRu . FILTER(LANG(?eventLabelRu) = "ru") }}
  ?city rdfs:label ?cityLabel . FILTER(LANG(?cityLabel) = "en")
  OPTIONAL {{ ?event wdt:P1120 ?attendance . }}
}}
LIMIT {limit}
"""
    bindings = _sparql(query)
    results: list[dict] = []
    seen: set[str] = set()

    for b in bindings:
        uri = _val(b, "event") or ""
        wid = uri.rsplit("/", 1)[-1]
        if wid in seen:
            continue
        seen.add(wid)

        name_en = _val(b, "eventLabel") or ""
        if not name_en or name_en.startswith("Q"):
            continue

        month = _month_from_date(_val(b, "startDate"))
        if month is None:
            continue

        category = _map_category(_val(b, "instanceOf"))
        crowd, price, relevance = _impacts(_val(b, "attendance"), category)

        results.append(
            {
                "wikidata_id": wid,
                "name_en": name_en,
                "name_ru": _val(b, "eventLabelRu"),
                "country_code": country_code,
                "city_name": _val(b, "cityLabel"),
                "month_start": month,
                "month_end": month,
                "category": category,
                "crowd_impact": crowd,
                "price_impact": price,
                "traveler_relevance": relevance,
            }
        )

    logger.info(
        f"  {country_code} ({country_qid}): {len(bindings)} raw → {len(results)} valid events"
    )
    return results


def fetch_all_events(
    country_codes: list[str],
    batch_size: int = 20,
) -> list[dict]:
    """Fetch events for all country codes.

    Phase 1: resolve ISO codes → QIDs in batches of 20 (fast, ~0.5s per batch).
    Phase 2: query events per country QID (one request per country, ~2s each).

    Args:
        country_codes: ISO-2 codes to query
        batch_size: codes per QID-resolution request

    Returns:
        globally deduplicated list of event dicts.
    """
    # Phase 1: resolve QIDs
    qid_map: dict[str, str] = {}
    for i in range(0, len(country_codes), batch_size):
        batch = country_codes[i : i + batch_size]
        resolved = resolve_country_qids(batch)
        qid_map.update(resolved)
        if i + batch_size < len(country_codes):
            time.sleep(0.5)

    logger.info(
        f"Phase 2: fetching events for {len(qid_map)} countries with resolved QIDs..."
    )

    all_events: list[dict] = []
    seen_global: set[str] = set()

    for idx, (cc, qid) in enumerate(qid_map.items()):
        events = fetch_events_for_country_qid(qid, cc)
        for ev in events:
            wid = ev["wikidata_id"]
            if wid not in seen_global:
                seen_global.add(wid)
                all_events.append(ev)
        if idx < len(qid_map) - 1:
            time.sleep(SLEEP_BETWEEN_COUNTRIES)

    logger.info(
        f"Wikidata total: {len(all_events)} unique events from {len(qid_map)} countries."
    )
    return all_events
