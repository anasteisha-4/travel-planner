"""Transform Numbeo cost data: match to destinations, normalize cost_index."""

import logging
import re

import numpy as np
import pandas as pd
from rapidfuzz import fuzz

logger = logging.getLogger(__name__)

# Russia is too large to use a single country_average — daily costs vary 3–5x.
# We group cities into cost clusters based on geographic/economic proximity
# to Numbeo-covered cities. Data quality = 0.5 (PPP-corrected regional proxy).
#
# Clusters derived from Numbeo RU data (2024):
#   Moscow:         ~$195/day
#   Saint Petersburg: ~$118/day
#   Major cities (Ekaterinburg, Tyumen, Kazan, Vladivostok, Nizhny Novgorod): ~$90–130/day
#   Mid cities (Krasnodar, Chelyabinsk, Novosibirsk, Samara, Ufa, Rostov, Kaliningrad): ~$80–95/day
#   Smaller cities (Perm, Krasnoyarsk, Tomsk): ~$70–80/day
#
_RU_CITY_CLUSTERS: dict[str, float] = {
    # Moscow cluster
    "Moscow": 194.51,
    "Khimki": 160.0,
    "Mytishchi": 155.0,
    "Kolomna": 120.0,
    "Sergiev Posad": 110.0,
    "Suzdal": 110.0,
    "Vladimir": 95.0,
    "Tula": 90.0,
    "Ryazan": 88.0,
    "Yaroslavl": 92.0,
    "Kostroma": 85.0,
    "Ivanovo": 82.0,
    "Tver": 88.0,
    "Smolensk": 82.0,
    "Bryansk": 80.0,
    "Kursk": 80.0,
    "Belgorod": 83.0,
    "Lipetsk": 80.0,
    "Voronezh": 85.0,
    "Oryol": 78.0,
    "Pereslavl-Zalessky": 95.0,
    # Saint Petersburg cluster
    "Saint Petersburg": 118.0,
    "Pskov": 85.0,
    "Vologda": 82.0,
    "Petrozavodsk": 88.0,
    "Murmansk": 92.0,
    "Arkhangelsk": 88.0,
    "Kaliningrad": 82.73,
    "Veliky Novgorod": 85.0,
    # Volga cluster (Kazan/Nizhny Novgorod/Samara/Ufa level)
    "Kazan": 98.0,
    "Nizhny Novgorod": 100.62,
    "Nizhniy Novgorod": 100.62,
    "Samara": 93.0,
    "Ufa": 89.0,
    "Saratov": 83.0,
    "Volgograd": 82.0,
    "Astrakhan": 82.0,
    "Penza": 80.0,
    "Ulyanovsk": 80.0,
    "Cheboksary": 78.0,
    "Naberezhnye Chelny": 82.0,
    "Izhevsk": 82.0,
    "Kirov": 78.0,
    "Tolyatti": 80.0,
    # Ural cluster
    "Yekaterinburg": 122.0,
    "Chelyabinsk": 89.8,
    "Tyumen": 107.0,
    "Perm": 83.39,
    "Orenburg": 80.0,
    "Magnitogorsk": 78.0,
    # Krasnodar/South cluster
    "Krasnodar": 94.67,
    "Rostov-on-Don": 88.0,
    "Sochi": 130.0,
    "Anapa": 105.0,
    "Gelendzhik": 108.0,
    "Novorossiysk": 88.0,
    "Makhachkala": 78.0,
    "Stavropol": 78.0,
    "Derbent": 75.0,
    "Kislovodsk": 95.0,
    "Pyatigorsk": 88.0,
    # Siberia cluster
    "Novosibirsk": 89.4,
    "Krasnoyarsk": 80.52,
    "Omsk": 82.0,
    "Tomsk": 80.0,
    "Barnaul": 78.0,
    "Kemerovo": 76.0,
    "Novokuznetsk": 75.0,
    "Tyumenskaya": 85.0,
    "Gorno-Altaysk": 80.0,
    "Chemal": 90.0,
    "Artybash": 85.0,
    "Kosh-Agach": 75.0,
    "Biysk": 74.0,
    "Abakan": 76.0,
    # Far East cluster
    "Vladivostok": 105.0,
    "Khabarovsk": 98.0,
    "Khabarovsk Vtoroy": 98.0,
    "Blagoveshchensk": 85.0,
    "Yuzhno-Sakhalinsk": 108.0,
    "Petropavlovsk-Kamchatsky": 120.0,
    "Magadan": 130.0,
    "Yakutsk": 115.0,
    # Nature/remote cluster (higher due to remoteness/tourism)
    "Ruskeala": 90.0,  # RU park near Finnish border — subregion wrongly classified as Northern Europe
    "Irkutsk": 88.0,
    "Listvyanka": 100.0,
    "Olkhon": 95.0,
    "Ulan-Ude": 80.0,
    "Kizhi": 110.0,
    "Curonian Spit": 90.0,
    "Dombay": 105.0,
    "Feodosia": 88.0,
    "Valley of Geysers": 120.0,
}


def _numbeo_variants(city_name: str) -> list[str]:
    """Generate name candidates from Numbeo city names with parentheticals.

    "Kiev (Kyiv)" → ["Kiev (Kyiv)", "Kiev", "Kyiv"]
    "Krakow (Cracow)" → ["Krakow (Cracow)", "Krakow", "Cracow"]
    """
    variants = [city_name]
    before = re.sub(r"\s*\(.*?\)", "", city_name).strip()
    if before and before != city_name:
        variants.append(before)
    inside = re.findall(r"\(([^)]+)\)", city_name)
    variants.extend(inside)
    return variants


def _get_destination_lookup(skip_existing: bool = False) -> dict[str, dict]:
    from app.database import SessionLocal
    from app.models import Destination
    from app.models.costs import DestinationCosts

    db = SessionLocal()
    try:
        destinations = db.query(Destination).filter(Destination.is_active == True).all()  # noqa: E712
        if skip_existing:
            existing = db.query(DestinationCosts.destination_id).all()
            existing_ids = {str(r[0]) for r in existing}
            before = len(destinations)
            destinations = [d for d in destinations if str(d.id) not in existing_ids]
            logger.info(
                f"skip_existing=True: {before - len(destinations)} already covered, {len(destinations)} remaining."
            )
        return {
            str(dest.id): {
                "name": dest.name,
                "country_code": dest.country_code,
                "subregion": dest.subregion or "",
                "region": dest.region or "",
            }
            for dest in destinations
        }
    finally:
        db.close()


def _match_destination(city_name: str, country_code: str, lookup: dict) -> str | None:
    """Fuzzy match with parenthetical variant extraction. Threshold 80 to avoid false city matches."""
    candidates = [
        (dest_id, info)
        for dest_id, info in lookup.items()
        if info["country_code"].upper() == country_code.upper()
    ]
    if not candidates:
        return None

    best_id, best_score = None, 0
    for dest_id, info in candidates:
        for variant in _numbeo_variants(city_name):
            score = fuzz.token_sort_ratio(variant.lower(), info["name"].lower())
            if score > best_score:
                best_score = score
                best_id = dest_id

    # Use 80 threshold to avoid matching different cities in same country (e.g. Bruges→Brussels)
    return str(best_id) if best_score >= 80 else None


def transform_costs(df: pd.DataFrame, skip_existing: bool = False) -> list[dict]:
    """Match Numbeo data to destinations and compute normalized cost_index."""
    lookup = _get_destination_lookup(skip_existing=skip_existing)

    rows = []
    matched_ids: set[str] = set()
    for _, row in df.iterrows():
        dest_id = _match_destination(
            str(row.get("city_name", "")),
            str(row.get("country_code", "")),
            lookup,
        )
        if not dest_id:
            logger.debug(
                f"No destination match for {row.get('city_name')}, {row.get('country_code')}"
            )
            continue

        # Skip duplicate matches (e.g. Nizhny Novgorod matched twice via name variants)
        if dest_id in matched_ids:
            logger.debug(
                f"Duplicate Numbeo match skipped: {row.get('city_name')} → {dest_id}"
            )
            continue
        matched_ids.add(dest_id)

        meal = float(row.get("meal_mid_usd", 0) or 0)
        transport = float(row.get("transport_day_usd", 0) or 0)
        hotel = float(row.get("hotel_3star_usd", 0) or 0)

        # Treat rows where both meal and hotel are 0 as incomplete data — only transport present
        # (e.g. Khabarovsk in Numbeo CSV: meal=0.0, hotel=0.0, transport_only=1.42)
        daily = meal * 2.5 + transport + hotel
        if meal == 0.0 and hotel == 0.0:
            logger.warning(
                f"Numbeo row for {row.get('city_name')} has no meal/hotel data (daily={daily:.2f}) "
                f"— skipping, will use city cluster or country_average fallback."
            )
            matched_ids.discard(dest_id)
            continue

        rows.append(
            {
                "destination_id": dest_id,
                "avg_meal_cost_usd": round(meal, 2),
                "avg_transport_cost_usd": round(transport, 2),
                "avg_hotel_cost_usd": round(hotel, 2),
                "avg_daily_cost_usd": round(daily, 2),
                "data_source": "numbeo",
            }
        )

    if not rows:
        return []

    rows = _normalize_and_fill_defaults(rows, lookup)
    logger.info(f"Transformed {len(rows)} cost records (including regional defaults).")
    return rows


_DATA_QUALITY_BY_SOURCE: dict[str, float] = {
    "numbeo": 1.0,
    "ru_city_cluster": 0.5,
    "country_average": 0.7,
    "subregion_average": 0.3,
    "region_average": 0.3,
    "global_average": 0.1,
}


def _normalize_and_fill_defaults(rows: list[dict], lookup: dict) -> list[dict]:
    """Normalize cost_index and add regional-average defaults for uncovered destinations."""
    # Step 1: normalize existing Numbeo records
    daily_costs = np.array([r["avg_daily_cost_usd"] for r in rows])
    p5, p95 = (
        float(np.percentile(daily_costs, 5)),
        float(np.percentile(daily_costs, 95)),
    )
    rng = p95 - p5 if p95 > p5 else 1.0

    covered_ids = set()
    for row in rows:
        clipped = max(p5, min(p95, row["avg_daily_cost_usd"]))
        row["cost_index"] = round((clipped - p5) / rng, 4)
        row.setdefault("data_source", "numbeo")
        row["data_quality_score"] = _DATA_QUALITY_BY_SOURCE.get(row["data_source"], 0.5)
        covered_ids.add(row["destination_id"])

    # Step 2: build country / subregion / region averages from Numbeo data
    dest_meta = {did: info for did, info in lookup.items()}
    country_costs: dict[str, list[float]] = {}
    subregion_costs: dict[str, list[float]] = {}
    region_costs: dict[str, list[float]] = {}

    for row in rows:
        meta = dest_meta.get(row["destination_id"], {})
        cc = meta.get("country_code", "")
        sub = meta.get("subregion", "")
        reg = meta.get("region", "")
        daily = row["avg_daily_cost_usd"]
        if cc:
            country_costs.setdefault(cc, []).append(daily)
        if sub:
            subregion_costs.setdefault(sub, []).append(daily)
        if reg:
            region_costs.setdefault(reg, []).append(daily)

    global_avg_daily = float(np.mean(daily_costs))

    # Step 3: for each uncovered destination, infer daily cost and compute cost_index
    for dest_id, info in lookup.items():
        if dest_id in covered_ids:
            continue

        cc = info.get("country_code", "")
        sub = info.get("subregion", "")
        reg = info.get("region", "")
        name = info.get("name", "")

        # Russia: use city-level cluster data instead of country_average —
        # costs vary 3–5x across regions (Moscow ~$195/day vs Siberia ~$75/day)
        if cc == "RU" and name in _RU_CITY_CLUSTERS:
            inferred_daily = _RU_CITY_CLUSTERS[name]
            source = "ru_city_cluster"
        elif cc and cc in country_costs and cc != "RU":
            inferred_daily = float(np.mean(country_costs[cc]))
            source = "country_average"
        elif sub and sub in subregion_costs:
            inferred_daily = float(np.mean(subregion_costs[sub]))
            source = "subregion_average"
        elif reg and reg in region_costs:
            inferred_daily = float(np.mean(region_costs[reg]))
            source = "region_average"
        else:
            inferred_daily = global_avg_daily
            source = "global_average"

        clipped = max(p5, min(p95, inferred_daily))
        cost_index = round((clipped - p5) / rng, 4)

        rows.append(
            {
                "destination_id": dest_id,
                "avg_meal_cost_usd": round(
                    inferred_daily / 4.5, 2
                ),  # inverse of meal*2.5+transport+hotel
                "avg_transport_cost_usd": round(inferred_daily * 0.05, 2),
                "avg_hotel_cost_usd": round(inferred_daily * 0.6, 2),
                "avg_daily_cost_usd": round(inferred_daily, 2),
                "cost_index": cost_index,
                "data_source": source,
                "data_quality_score": _DATA_QUALITY_BY_SOURCE.get(source, 0.5),
            }
        )

    return rows
