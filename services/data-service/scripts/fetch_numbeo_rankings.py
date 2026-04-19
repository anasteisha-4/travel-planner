"""Scrape Numbeo Cost of Living Index rankings and update destination_costs.

Numbeo rankings page (no API key needed):
  https://www.numbeo.com/cost-of-living/rankings_current.jsp

Returns 500+ cities with Cost of Living Index (New York = 100).
We use this index directly to compute cost_index [0,1] via p5/p95 normalization,
same approach as the existing transformer.

Strategy:
  1. Scrape all cities from Numbeo rankings → {city_name_raw: col_index}
  2. Parse "City, Country" → (city, country_name) → map country_name → ISO2
  3. Fuzzy-match to our destinations (same rapidfuzz logic as costs_transformer)
  4. For matched destinations: convert CoL index → daily_usd estimate, recompute cost_index
  5. Upsert into destination_costs with data_source='numbeo'

After this script, run the ETL upsert (or insert directly via SQL).

Run inside container:
  docker compose run --rm data-service python scripts/fetch_numbeo_rankings.py
"""

import logging
import re
import sys
from pathlib import Path

import httpx
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

NUMBEO_URL = "https://www.numbeo.com/cost-of-living/rankings_current.jsp"
# New York CoL index = 100.0; multiply by this factor to get approximate daily USD
# Based on: NYC avg daily ~$250 → 250/100 = 2.5 USD per index point
COL_INDEX_TO_DAILY_USD = 2.5

# Country name → ISO2 mapping for Numbeo's display names
_COUNTRY_NAME_TO_ISO2: dict[str, str] = {
    "Afghanistan": "AF",
    "Albania": "AL",
    "Algeria": "DZ",
    "Andorra": "AD",
    "Angola": "AO",
    "Argentina": "AR",
    "Armenia": "AM",
    "Australia": "AU",
    "Austria": "AT",
    "Azerbaijan": "AZ",
    "Bahrain": "BH",
    "Bangladesh": "BD",
    "Belarus": "BY",
    "Belgium": "BE",
    "Bolivia": "BO",
    "Bosnia And Herzegovina": "BA",
    "Botswana": "BW",
    "Brazil": "BR",
    "Bulgaria": "BG",
    "Cambodia": "KH",
    "Cameroon": "CM",
    "Canada": "CA",
    "Chile": "CL",
    "China": "CN",
    "Hong Kong (China)": "HK",
    "Colombia": "CO",
    "Costa Rica": "CR",
    "Croatia": "HR",
    "Cuba": "CU",
    "Cyprus": "CY",
    "Czech Republic": "CZ",
    "Czechia": "CZ",
    "Denmark": "DK",
    "Dominican Republic": "DO",
    "Ecuador": "EC",
    "Egypt": "EG",
    "El Salvador": "SV",
    "Estonia": "EE",
    "Ethiopia": "ET",
    "Finland": "FI",
    "France": "FR",
    "Georgia": "GE",
    "Germany": "DE",
    "Ghana": "GH",
    "Greece": "GR",
    "Guatemala": "GT",
    "Honduras": "HN",
    "Hungary": "HU",
    "Iceland": "IS",
    "India": "IN",
    "Indonesia": "ID",
    "Iran": "IR",
    "Iraq": "IQ",
    "Ireland": "IE",
    "Israel": "IL",
    "Italy": "IT",
    "Jamaica": "JM",
    "Japan": "JP",
    "Jordan": "JO",
    "Kazakhstan": "KZ",
    "Kenya": "KE",
    "Kosovo": "XK",
    "Kuwait": "KW",
    "Kyrgyzstan": "KG",
    "Latvia": "LV",
    "Lebanon": "LB",
    "Libya": "LY",
    "Lithuania": "LT",
    "Luxembourg": "LU",
    "Macao": "MO",
    "Malaysia": "MY",
    "Malta": "MT",
    "Mauritius": "MU",
    "Mexico": "MX",
    "Moldova": "MD",
    "Montenegro": "ME",
    "Morocco": "MA",
    "Mozambique": "MZ",
    "Myanmar": "MM",
    "Namibia": "NA",
    "Nepal": "NP",
    "Netherlands": "NL",
    "New Zealand": "NZ",
    "Nicaragua": "NI",
    "Nigeria": "NG",
    "North Macedonia": "MK",
    "Norway": "NO",
    "Oman": "OM",
    "Pakistan": "PK",
    "Panama": "PA",
    "Paraguay": "PY",
    "Peru": "PE",
    "Philippines": "PH",
    "Poland": "PL",
    "Portugal": "PT",
    "Puerto Rico": "PR",
    "Qatar": "QA",
    "Romania": "RO",
    "Russia": "RU",
    "Saudi Arabia": "SA",
    "Senegal": "SN",
    "Serbia": "RS",
    "Singapore": "SG",
    "Slovakia": "SK",
    "Slovenia": "SI",
    "South Africa": "ZA",
    "South Korea": "KR",
    "Spain": "ES",
    "Sri Lanka": "LK",
    "Sweden": "SE",
    "Switzerland": "CH",
    "Taiwan": "TW",
    "Tajikistan": "TJ",
    "Tanzania": "TZ",
    "Thailand": "TH",
    "Tunisia": "TN",
    "Turkey": "TR",
    "Turkmenistan": "TM",
    "Uganda": "UG",
    "Ukraine": "UA",
    "United Arab Emirates": "AE",
    "United Kingdom": "GB",
    "United States": "US",
    "Uruguay": "UY",
    "Uzbekistan": "UZ",
    "Venezuela": "VE",
    "Vietnam": "VN",
    "Yemen": "YE",
    "Zambia": "ZM",
    "Zimbabwe": "ZW",
    "Cayman Islands": "KY",
}


def _parse_city_country(raw: str) -> tuple[str, str] | None:
    """Parse 'City, Country' or 'City, ST, Country' → (city_name, iso2)."""
    # Handle US states: "New York, NY, United States" → city="New York", country="United States"
    # Handle "Hong Kong, Hong Kong (China)" → city="Hong Kong", country="HK"
    parts = [p.strip() for p in raw.split(",")]
    if not parts:
        return None

    # Last part is always the country
    country_raw = parts[-1].strip()
    # City is first part (drop state abbreviations in the middle)
    city = parts[0].strip()
    # Clean city: remove parentheticals like "Queretaro (Santiago de Querétaro)"
    city = re.sub(r"\s*\([^)]+\)", "", city).strip()

    iso2 = _COUNTRY_NAME_TO_ISO2.get(country_raw)
    if not iso2:
        # Try stripping " (China)" etc.
        country_clean = re.sub(r"\s*\([^)]+\)", "", country_raw).strip()
        iso2 = _COUNTRY_NAME_TO_ISO2.get(country_clean)
    if not iso2:
        return None
    return city, iso2


def scrape_numbeo_rankings() -> list[tuple[str, str, float]]:
    """Scrape Numbeo rankings → list of (city_name, iso2, col_index)."""
    logger.info(f"Fetching {NUMBEO_URL}")
    with httpx.Client(timeout=30, headers={"User-Agent": "Mozilla/5.0"}) as client:
        resp = client.get(NUMBEO_URL)
        resp.raise_for_status()

    content = resp.text
    # Extract: city+country name, then first numeric td (Cost of Living Index)
    rows = re.findall(
        r"cityOrCountryInIndicesTable[^>]*><a[^>]*>([^<]+)</a></td>\s*<td[^>]*>([\d.]+)</td>",
        content,
    )
    logger.info(f"Found {len(rows)} rows in Numbeo rankings")

    results: list[tuple[str, str, float]] = []
    skipped = 0
    for raw_name, col_str in rows:
        parsed = _parse_city_country(raw_name.strip())
        if not parsed:
            skipped += 1
            continue
        city, iso2 = parsed
        try:
            col_index = float(col_str)
        except ValueError:
            skipped += 1
            continue
        results.append((city, iso2, col_index))

    logger.info(f"Parsed {len(results)} cities ({skipped} skipped — unknown country)")
    return results


# Known Numbeo city name → destination name aliases
# Used when fuzzy score is below threshold due to alternate spellings
_CITY_ALIASES: dict[tuple[str, str], str] = {
    # (numbeo_city, iso2) → destination name
    ("The Hague", "NL"): "Hague",
    ("Hong Kong", "HK"): "Hong Kong Island",
    ("Taipei", "TW"): "Taipei",
    ("Bangalore", "IN"): "Bangalore",
    ("Bengaluru", "IN"): "Bangalore",
    ("Saint Petersburg", "RU"): "Saint Petersburg",
    ("St. Petersburg", "RU"): "Saint Petersburg",
    ("Krakow", "PL"): "Kraków",
    ("Cracow", "PL"): "Kraków",
    ("Warsaw", "PL"): "Warsaw",
    ("Kiev", "UA"): "Kyiv",
    ("Kyiv", "UA"): "Kyiv",
    ("Sao Paulo", "BR"): "São Paulo",
    ("Florianopolis", "BR"): "Florianópolis",
    ("Joao Pessoa", "BR"): "João Pessoa",
    ("Ulaanbaatar", "MN"): "Ulaanbaatar",
    ("Tbilisi", "GE"): "Tbilisi",
    ("Yerevan", "AM"): "Yerevan",
    ("Baku", "AZ"): "Baku",
    ("Almaty", "KZ"): "Almaty",
    ("Tashkent", "UZ"): "Tashkent",
    ("Bishkek", "KG"): "Bishkek",
    ("Minsk", "BY"): "Minsk",
    ("Chisinau", "MD"): "Chișinău",
    ("Ho Chi Minh City", "VN"): "Ho Chi Minh City",
    ("Saigon", "VN"): "Ho Chi Minh City",
    ("Hanoi", "VN"): "Hanoi",
    ("Da Nang", "VN"): "Da Nang",
    ("Kuala Lumpur", "MY"): "Kuala Lumpur",
    ("George Town", "MY"): "Penang",
    ("Colombo", "LK"): "Colombo Fort",
    ("Nairobi", "KE"): "Nairobi",
    ("Dar es Salaam", "TZ"): "Dar es Salaam",
    ("Casablanca", "MA"): "Casablanca",
    ("Cape Town", "ZA"): "Cape Town",
    ("Johannesburg", "ZA"): "Johannesburg",
    ("Accra", "GH"): "Accra",
    ("Lagos", "NG"): "Lagos",
    ("Abuja", "NG"): "Abuja",
    ("Algiers", "DZ"): "Algiers",
    ("Tunis", "TN"): "Tunis",
    ("Addis Ababa", "ET"): "Addis Ababa",
    ("Guatemala City", "GT"): "Guatemala City",
    ("San Salvador", "SV"): "San Salvador",
    ("Tegucigalda", "HN"): "Tegucigalpa",
    ("Managua", "NI"): "Managua",
    ("Panama City", "PA"): "Panama City",
    ("Santo Domingo", "DO"): "Santo Domingo",
    ("Quito", "EC"): "Quito",
    ("Guayaquil", "EC"): "Guayaquil",
    ("La Paz", "BO"): "La Paz",
    ("Asuncion", "PY"): "Asunción",
    ("Montevideo", "UY"): "Montevideo",
    ("Istanbul", "TR"): "Istanbul",
    ("Izmir", "TR"): "İzmir",
    ("Antalya", "TR"): "Antalya",
    ("Bursa", "TR"): "Bursa",
    ("Ankara", "TR"): "Ankara",
    ("Cairo", "EG"): "Cairo",
    ("Alexandria", "EG"): "Alexandria",
    ("Amman", "JO"): "Amman",
    ("Beirut", "LB"): "Beirut",
    ("Riyadh", "SA"): "Riyadh",
    ("Jeddah", "SA"): "Jeddah",
    ("Abu Dhabi", "AE"): "Abu Dhabi",
    ("Dubai", "AE"): "Dubai",
    ("Muscat", "OM"): "Muscat",
    ("Doha", "QA"): "Doha",
    ("Kuwait City", "KW"): "Kuwait City",
    ("Manama", "BH"): "Manama",
    ("Tehran", "IR"): "Tehran",
    ("Baghdad", "IQ"): "Baghdad",
    ("Karachi", "PK"): "Karachi",
    ("Lahore", "PK"): "Lahore",
    ("Islamabad", "PK"): "Islamabad",
    ("Dhaka", "BD"): "Dhaka",
    ("Chittagong", "BD"): "Chittagong",
    ("Kathmandu", "NP"): "Kathmandu",
    ("Phnom Penh", "KH"): "Phnom Penh",
    ("Vientiane", "LA"): "Vientiane",
    ("Rangoon", "MM"): "Yangon",
    ("Yangon", "MM"): "Yangon",
    ("Mandalay", "MM"): "Mandalay",
    ("Seoul", "KR"): "Seoul",
    ("Busan", "KR"): "Busan",
    ("Beijing", "CN"): "Beijing",
    ("Shanghai", "CN"): "Shanghai",
    ("Guangzhou", "CN"): "Guangzhou",
    ("Shenzhen", "CN"): "Shenzhen",
    ("Chengdu", "CN"): "Chengdu",
    ("Wuhan", "CN"): "Wuhan",
    ("Chongqing", "CN"): "Chongqing",
    ("Nanjing", "CN"): "Nanjing",
    ("Hangzhou", "CN"): "Hangzhou",
    ("Qingdao", "CN"): "Qingdao",
    ("Xi'an", "CN"): "Xi'an",
    ("Changsha", "CN"): "Changsha",
    ("Suzhou", "CN"): "Suzhou",
    ("Tokyo", "JP"): "Tokyo",
    ("Osaka", "JP"): "Osaka",
    ("Bangkok", "TH"): "Bangkok",
    ("Chiang Mai", "TH"): "Chiang Mai",
    ("Phuket", "TH"): "Phuket",
    ("Pattaya", "TH"): "Pattaya",
    ("Hua Hin", "TH"): "Hua Hin",
    ("Jakarta", "ID"): "Jakarta",
    ("Bali", "ID"): "Bali",
    ("Surabaya", "ID"): "Surabaya",
    ("Bandung", "ID"): "Bandung",
    ("Manila", "PH"): "Manila",
    ("Cebu City", "PH"): "Cebu",
    ("Singapore", "SG"): "Singapore",
    ("Mumbai", "IN"): "Mumbai",
    ("Delhi", "IN"): "New Delhi",
    ("New Delhi", "IN"): "New Delhi",
    ("Hyderabad", "IN"): "Hyderabad",
    ("Chennai", "IN"): "Chennai",
    ("Kolkata", "IN"): "Kolkata",
    ("Pune", "IN"): "Pune",
    ("Ahmedabad", "IN"): "Ahmedabad",
    ("Jaipur", "IN"): "Jaipur",
    ("Gurgaon", "IN"): "Gurgaon",
    ("Moscow", "RU"): "Moscow",
}


def match_and_update(rankings: list[tuple[str, str, float]]) -> None:
    """Fuzzy-match rankings to destinations and upsert cost records."""
    from rapidfuzz import fuzz
    from app.database import SessionLocal
    from app.models import Destination
    from app.models.costs import DestinationCosts

    db = SessionLocal()
    try:
        destinations = db.query(Destination).filter(Destination.is_active == True).all()  # noqa: E712
    finally:
        db.close()

    # Build lookup: {country_code: {dest_name_lower: (dest_id, dest_name)}}
    lookup: dict[str, list[tuple[str, str]]] = {}
    name_to_id: dict[str, dict[str, str]] = {}  # {iso2: {name_lower: dest_id}}
    for d in destinations:
        cc = (d.country_code or "").upper()
        lookup.setdefault(cc, []).append((str(d.id), d.name))
        name_to_id.setdefault(cc, {})[d.name.lower()] = str(d.id)

    # Match each ranking entry
    matched: dict[str, tuple[str, float]] = {}  # dest_id → (dest_name, col_index)
    unmatched: list[tuple[str, str, float]] = []

    for city, iso2, col_index in rankings:
        # 1. Try alias lookup first
        alias_dest_name = _CITY_ALIASES.get((city, iso2))
        if alias_dest_name:
            dest_id = name_to_id.get(iso2, {}).get(alias_dest_name.lower())
            if dest_id and dest_id not in matched:
                matched[dest_id] = (alias_dest_name, col_index)
                logger.debug(
                    f"  ✓ alias '{city}' ({iso2}) → '{alias_dest_name}' CoL={col_index}"
                )
                continue

        # 2. Fuzzy match with threshold 70
        candidates = lookup.get(iso2, [])
        if not candidates:
            unmatched.append((city, iso2, col_index))
            continue
        best_id, best_name, best_score = None, None, 0
        for dest_id, dest_name in candidates:
            score = fuzz.token_sort_ratio(city.lower(), dest_name.lower())
            if score > best_score:
                best_score = score
                best_id = dest_id
                best_name = dest_name
        if best_score >= 70 and best_id and best_name:
            if best_id not in matched:
                matched[best_id] = (best_name, col_index)
                logger.debug(
                    f"  ✓ '{city}' ({iso2}) → '{best_name}' score={best_score} CoL={col_index}"
                )
        else:
            unmatched.append((city, iso2, col_index))
            logger.debug(f"  ✗ '{city}' ({iso2}) no match (best_score={best_score})")

    logger.info(
        f"Matched {len(matched)} destinations, {len(unmatched)} unmatched from Numbeo"
    )
    if unmatched[:10]:
        logger.info(
            "Unmatched sample: " + str([(c, iso) for c, iso, _ in unmatched[:10]])
        )

    # Normalize: CoL index → cost_index [0,1] using p5/p95 of matched set
    col_values = np.array([col for _, col in matched.values()])
    p5 = float(np.percentile(col_values, 5))
    p95 = float(np.percentile(col_values, 95))
    rng = p95 - p5 if p95 > p5 else 1.0
    logger.info(f"CoL index normalization: p5={p5:.1f}, p95={p95:.1f}")

    # Build upsert records
    db = SessionLocal()
    try:
        updated = 0
        newly_numbeo = 0
        for dest_id, (dest_name, col_index) in matched.items():
            # daily cost estimate from CoL index
            daily_usd = round(col_index * COL_INDEX_TO_DAILY_USD, 2)
            clipped = max(p5, min(p95, col_index))
            new_cost_index = round((clipped - p5) / rng, 4)

            existing = (
                db.query(DestinationCosts)
                .filter(DestinationCosts.destination_id == dest_id)
                .first()
            )

            if existing:
                was_numbeo = existing.data_source == "numbeo"
                existing.avg_daily_cost_usd = daily_usd
                existing.avg_meal_cost_usd = round(daily_usd / 4.5, 2)
                existing.avg_transport_cost_usd = round(daily_usd * 0.05, 2)
                existing.avg_hotel_cost_usd = round(daily_usd * 0.6, 2)
                existing.cost_index = new_cost_index
                existing.data_source = "numbeo"
                existing.data_quality_score = 1.0
                if not was_numbeo:
                    newly_numbeo += 1
                updated += 1
            else:
                db.add(
                    DestinationCosts(
                        destination_id=dest_id,
                        avg_daily_cost_usd=daily_usd,
                        avg_meal_cost_usd=round(daily_usd / 4.5, 2),
                        avg_transport_cost_usd=round(daily_usd * 0.05, 2),
                        avg_hotel_cost_usd=round(daily_usd * 0.6, 2),
                        cost_index=new_cost_index,
                        data_source="numbeo",
                        data_quality_score=1.0,
                    )
                )
                updated += 1
                newly_numbeo += 1

        db.commit()
        logger.info(
            f"Upserted {updated} cost records ({newly_numbeo} upgraded from fallback → numbeo)"
        )
    finally:
        db.close()


def verify() -> None:
    """Print updated coverage stats."""
    from app.database import SessionLocal
    from app.models.costs import DestinationCosts

    db = SessionLocal()
    try:
        from sqlalchemy import func

        stats = (
            db.query(DestinationCosts.data_source, func.count().label("cnt"))
            .group_by(DestinationCosts.data_source)
            .all()
        )
        total = sum(r.cnt for r in stats)
        logger.info("\n=== Updated coverage ===")
        for row in sorted(stats, key=lambda r: -r.cnt):
            pct = row.cnt / total * 100
            logger.info(f"  {row.data_source:20s}: {row.cnt:4d}  ({pct:.1f}%)")
        numbeo = next((r.cnt for r in stats if r.data_source == "numbeo"), 0)
        logger.info(
            f"\nNumbero coverage: {numbeo}/{total} = {numbeo / total * 100:.1f}%"
        )
    finally:
        db.close()


if __name__ == "__main__":
    rankings = scrape_numbeo_rankings()
    if not rankings:
        logger.error("No rankings scraped — aborting")
        sys.exit(1)

    match_and_update(rankings)
    verify()
