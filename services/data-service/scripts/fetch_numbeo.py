"""
Fetch Numbeo cost of living data and save to data/raw/numbeo_costs.csv

Numbeo publishes cost of living data publicly. We scrape the city-level cost index page.

Usage:
    python scripts/fetch_numbeo.py
"""

import csv
import logging
import time
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OUTPUT_PATH = Path(__file__).resolve().parents[1] / "data" / "raw" / "numbeo_costs.csv"

# Numbeo cost of living by city page (public, no auth needed)
NUMBEO_URL = "https://www.numbeo.com/cost-of-living/prices_by_city.jsp"

# Specific item indices on Numbeo:
# Item 1  = Meal, Inexpensive Restaurant (USD)
# Item 2  = Meal for 2 People, Mid-range Restaurant (USD) → divide by 2 for per-meal mid
# Item 20 = Monthly Pass (public transport)
# Item 26 = 1-day public transport ticket  ← most relevant for "transport_day_usd"
# Item 40 = Hotel 1 night, 3-star, city center

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

# Numbeo item IDs for the specific metrics we need
# Item 2:  Meal for 2 at mid-range restaurant (÷2 per person)
# Item 18: One-way ticket local transport (×2 = approx daily cost)
# Item 26: 1BR city-centre rent/month (÷30 ×2.5 = hotel proxy)
ITEM_IDS = {
    "meal_mid": 2,
    "transport_ticket": 18,
    "rent_1br": 26,
}


def fetch_item_prices(item_id: int) -> dict[str, float]:
    """Fetch price data for a specific Numbeo item across all cities."""
    url = f"https://www.numbeo.com/cost-of-living/prices_by_city.jsp?itemId={item_id}&displayCurrency=USD"

    with httpx.Client(timeout=30, headers=HEADERS, follow_redirects=True) as client:
        resp = client.get(url, headers=HEADERS)
        resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    table = soup.find("table", id="t2")
    if not table:
        logger.warning(f"No table found for item {item_id}")
        return {}

    prices = {}
    # Numbeo table format: [rank/empty, "City, Country", price]
    rows = (
        table.find("tbody").find_all("tr")
        if table.find("tbody")
        else table.find_all("tr")[1:]
    )
    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 3:
            continue
        try:
            city_country = cells[1].get_text(strip=True)
            # Format: "Bangkok, Thailand" or "New York, NY, United States"
            # Split on last comma for country
            parts = [p.strip() for p in city_country.rsplit(",", 1)]
            if len(parts) != 2:
                continue
            city = parts[0]
            country = parts[1]
            price_str = (
                cells[2].get_text(strip=True).replace(",", "").replace("$", "").strip()
            )
            price = float(price_str)
            key = f"{city}|{country}"
            prices[key] = price
        except (ValueError, IndexError):
            continue

    logger.info(f"Item {item_id}: fetched {len(prices)} city prices")
    return prices


# Map Numbeo country names to ISO2
NUMBEO_COUNTRY_TO_ISO2 = {
    "Russia": "RU",
    "United States": "US",
    "Germany": "DE",
    "France": "FR",
    "United Kingdom": "GB",
    "Japan": "JP",
    "China": "CN",
    "India": "IN",
    "Brazil": "BR",
    "Canada": "CA",
    "Australia": "AU",
    "Spain": "ES",
    "Italy": "IT",
    "Mexico": "MX",
    "South Korea": "KR",
    "Indonesia": "ID",
    "Netherlands": "NL",
    "Turkey": "TR",
    "Switzerland": "CH",
    "Sweden": "SE",
    "Poland": "PL",
    "Belgium": "BE",
    "Argentina": "AR",
    "Norway": "NO",
    "Austria": "AT",
    "United Arab Emirates": "AE",
    "Thailand": "TH",
    "Malaysia": "MY",
    "Singapore": "SG",
    "Philippines": "PH",
    "South Africa": "ZA",
    "Egypt": "EG",
    "Colombia": "CO",
    "Chile": "CL",
    "Portugal": "PT",
    "Czech Republic": "CZ",
    "Romania": "RO",
    "New Zealand": "NZ",
    "Hungary": "HU",
    "Greece": "GR",
    "Ukraine": "UA",
    "Denmark": "DK",
    "Finland": "FI",
    "Slovakia": "SK",
    "Croatia": "HR",
    "Vietnam": "VN",
    "Pakistan": "PK",
    "Bangladesh": "BD",
    "Nigeria": "NG",
    "Kenya": "KE",
    "Ethiopia": "ET",
    "Morocco": "MA",
    "Peru": "PE",
    "Venezuela": "VE",
    "Ecuador": "EC",
    "Bolivia": "BO",
    "Paraguay": "PY",
    "Uruguay": "UY",
    "Cuba": "CU",
    "Dominican Republic": "DO",
    "Israel": "IL",
    "Saudi Arabia": "SA",
    "Kuwait": "KW",
    "Qatar": "QA",
    "Bahrain": "BH",
    "Oman": "OM",
    "Jordan": "JO",
    "Lebanon": "LB",
    "Iran": "IR",
    "Iraq": "IQ",
    "Kazakhstan": "KZ",
    "Uzbekistan": "UZ",
    "Azerbaijan": "AZ",
    "Georgia": "GE",
    "Armenia": "AM",
    "Belarus": "BY",
    "Moldova": "MD",
    "Lithuania": "LT",
    "Latvia": "LV",
    "Estonia": "EE",
    "Bulgaria": "BG",
    "Serbia": "RS",
    "Slovenia": "SI",
    "Bosnia And Herzegovina": "BA",
    "North Macedonia": "MK",
    "Albania": "AL",
    "Montenegro": "ME",
    "Kosovo (Disputed Territory)": "XK",
    "Luxembourg": "LU",
    "Ireland": "IE",
    "Iceland": "IS",
    "Malta": "MT",
    "Cyprus": "CY",
    "Sri Lanka": "LK",
    "Nepal": "NP",
    "Myanmar (Burma)": "MM",
    "Cambodia": "KH",
    "Laos": "LA",
    "Mongolia": "MN",
    "Taiwan": "TW",
    "Hong Kong": "HK",
    "Macau": "MO",
    "Ghana": "GH",
    "Tanzania": "TZ",
    "Uganda": "UG",
    "Rwanda": "RW",
    "Senegal": "SN",
    "Cameroon": "CM",
    "Algeria": "DZ",
    "Tunisia": "TN",
    "Libya": "LY",
    "Sudan": "SD",
    "Zimbabwe": "ZW",
    "Zambia": "ZM",
    "Mozambique": "MZ",
    "Namibia": "NA",
    "Botswana": "BW",
    "Ivory Coast": "CI",
    "Guatemala": "GT",
    "Honduras": "HN",
    "El Salvador": "SV",
    "Nicaragua": "NI",
    "Costa Rica": "CR",
    "Panama": "PA",
    "Trinidad And Tobago": "TT",
    "Jamaica": "JM",
    "Puerto Rico": "PR",
    "Kyrgyzstan": "KG",
    "Tajikistan": "TJ",
    "Turkmenistan": "TM",
    "Afghanistan": "AF",
    "Fiji": "FJ",
    "Papua New Guinea": "PG",
    "New Caledonia": "NC",
}


def main():
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Fetching meal prices (item 2: meal for 2, mid-range)...")
    meal_prices = fetch_item_prices(2)
    time.sleep(2)

    logger.info("Fetching transport prices (item 18: one-way ticket)...")
    transport_prices = fetch_item_prices(18)
    time.sleep(2)

    logger.info("Fetching rent prices (item 26: 1BR city-centre monthly)...")
    rent_prices = fetch_item_prices(26)
    time.sleep(2)

    # Merge all city data
    all_cities = (
        set(meal_prices.keys()) | set(transport_prices.keys()) | set(rent_prices.keys())
    )
    logger.info(f"Total cities with at least one price: {len(all_cities)}")

    written = 0
    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "city_name",
                "country_code",
                "meal_mid_usd",
                "transport_day_usd",
                "hotel_3star_usd",
            ]
        )

        for key in sorted(all_cities):
            city, country = key.split("|", 1)
            iso2 = NUMBEO_COUNTRY_TO_ISO2.get(country)
            if not iso2:
                logger.debug(f"No ISO2 for Numbeo country: {country!r}")
                continue

            meal = meal_prices.get(key, 0)
            meal_per_person = round(meal / 2, 2) if meal else 0.0
            # 2× one-way ticket ≈ daily local transport cost
            transport = round((transport_prices.get(key, 0) or 0) * 2, 2)
            # 1BR monthly rent ÷ 30 × 2.5 ≈ 3-star hotel night price
            rent = rent_prices.get(key, 0) or 0
            hotel = round(rent / 30 * 2.5, 2) if rent else 0.0

            if meal_per_person == 0 and transport == 0 and hotel == 0:
                continue

            writer.writerow([city, iso2, meal_per_person, transport, hotel])
            written += 1

    logger.info(f"Saved {written} city cost records to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
