"""Extract monthly Wikipedia pageview data as a proxy for tourist interest.

Strategy: probe article names directly via the Pageviews API (no search API needed).
The Pageviews REST API returns 404 for unknown articles — we use that as a probe.
Candidates are tried in order: city name → "City, Country" variant → common aliases.
"""

import logging
import time
import unicodedata
import urllib.parse
from datetime import date

import httpx
import pycountry

logger = logging.getLogger(__name__)

PAGEVIEWS_URL = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article"
HEADERS = {"User-Agent": "Triply/1.0 (travel-planner; contact: admin@triply.app)"}
SLEEP_BETWEEN_REQUESTS = 0.5  # conservative — Wikimedia pageviews allows ~100 req/s but we share with search

# Known aliases where city name ≠ Wikipedia article title
ARTICLE_ALIASES: dict[str, str] = {
    "Malé": "Malé",
    "Ciudad de la Paz": "Malabo",  # GQ capital is actually Malabo
    "El Aaiún": "Laayoune",
    "Sana'a": "Sanaa",
    "N'Djamena": "N'Djamena",
    "Ngerulmud": "Ngerulmud",
    "Funafuti": "Funafuti",
    "Yaren": "Yaren District",
    "Road Town": "Road Town",
    "Adamstown": "Adamstown, Pitcairn Islands",
    "Flying Fish Cove": "Flying Fish Cove",
    "Jamestown": "Jamestown, Saint Helena",
    "Edinburgh of the Seven Seas": "Edinburgh of the Seven Seas",
}


def _country_name(country_code: str) -> str:
    try:
        return pycountry.countries.get(alpha_2=country_code).name
    except Exception:
        return country_code


def _ascii_name(name: str) -> str:
    """Normalize accented characters to ASCII for article name fallback."""
    return unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")


def _probe_article(name: str, year: int) -> bool:
    """Return True if this article name has pageview data for the given year."""
    encoded = urllib.parse.quote(name.replace(" ", "_"), safe="")
    url = f"{PAGEVIEWS_URL}/en.wikipedia/all-access/all-agents/{encoded}/monthly/{year}010100/{year}123100"
    try:
        with httpx.Client(timeout=10, headers=HEADERS) as client:
            r = client.get(url)
            return r.status_code == 200
    except Exception:
        return False


def _find_article_name(city_name: str, country_code: str) -> str | None:
    """Probe candidate article names without using the search API."""
    if city_name in ARTICLE_ALIASES:
        return ARTICLE_ALIASES[city_name]

    country = _country_name(country_code)
    probe_year = date.today().year - 1

    candidates = [
        city_name,
        _ascii_name(city_name),
        f"{city_name}, {country}",
        f"{_ascii_name(city_name)}, {country}",
        f"{city_name} City",
    ]

    for candidate in candidates:
        if not candidate.strip():
            continue
        time.sleep(SLEEP_BETWEEN_REQUESTS)
        if _probe_article(candidate, probe_year):
            return candidate

    return None


def _fetch_monthly_pageviews(article: str, year: int) -> dict[int, int]:
    """Fetch monthly pageview counts for a Wikipedia article in a given year."""
    encoded = urllib.parse.quote(article.replace(" ", "_"), safe="")
    url = f"{PAGEVIEWS_URL}/en.wikipedia/all-access/all-agents/{encoded}/monthly/{year}010100/{year}123100"
    try:
        with httpx.Client(timeout=15, headers=HEADERS) as client:
            r = client.get(url)
            if r.status_code in (404, 429):
                return {}
            r.raise_for_status()
            items = r.json().get("items", [])
        return {int(item["timestamp"][4:6]): item["views"] for item in items if "timestamp" in item and "views" in item}
    except Exception as e:
        logger.debug(f"Pageview fetch failed for {article}: {e}")
        return {}


def fetch_pageviews_for_destination(
    destination_id: str,
    name: str,
    country_code: str,
) -> dict:
    """Return monthly pageview data for one destination."""
    ref_years = [date.today().year - 2, date.today().year - 1]

    article = _find_article_name(name, country_code)
    if not article:
        return {"destination_id": destination_id, "article": None, "monthly_views": {}}

    combined: dict[int, list[int]] = {}
    for year in ref_years:
        monthly = _fetch_monthly_pageviews(article, year)
        time.sleep(SLEEP_BETWEEN_REQUESTS)
        for month, views in monthly.items():
            combined.setdefault(month, []).append(views)

    avg_monthly = {month: int(sum(views) / len(views)) for month, views in combined.items()}

    return {
        "destination_id": destination_id,
        "article": article,
        "monthly_views": avg_monthly,
    }


def extract_pageviews_missing_destinations() -> list[dict]:
    """Fetch Wikipedia pageviews only for destinations not yet in destination_popularity."""
    from sqlalchemy import text

    from app.database import SessionLocal
    from app.models import Destination

    db = SessionLocal()
    try:
        destinations = db.query(Destination).filter(Destination.is_active == True).all()  # noqa: E712
        covered_ids: set[str] = {
            row[0]
            for row in db.execute(text("SELECT DISTINCT destination_id::text FROM destination_popularity")).fetchall()
        }
    finally:
        db.close()

    missing = [d for d in destinations if str(d.id) not in covered_ids]
    logger.info(
        f"Fetching pageviews for {len(missing)} remaining destinations (skipping {len(covered_ids)} already done)"
    )

    results = []
    for i, dest in enumerate(missing, 1):
        data = fetch_pageviews_for_destination(str(dest.id), dest.name, dest.country_code)
        results.append(data)
        found = "✓" if data["article"] else "✗"
        logger.info(
            f"[{i}/{len(missing)}] {found} {dest.name} → {data.get('article')} ({len(data['monthly_views'])} months)"
        )

    return results


def extract_pageviews_all_destinations() -> list[dict]:
    """Fetch Wikipedia pageviews for all active destinations."""
    from app.database import SessionLocal
    from app.models import Destination

    db = SessionLocal()
    try:
        destinations = db.query(Destination).filter(Destination.is_active == True).all()  # noqa: E712
    finally:
        db.close()

    results = []
    for i, dest in enumerate(destinations, 1):
        data = fetch_pageviews_for_destination(str(dest.id), dest.name, dest.country_code)
        results.append(data)
        found = "✓" if data["article"] else "✗"
        logger.info(
            f"[{i}/{len(destinations)}] {found} {dest.name} → {data.get('article')} ({len(data['monthly_views'])} months)"
        )

    return results
