"""
Fetch GPI 2025 data from Wikipedia and save to data/raw/gpi_scores.csv

Usage:
    python scripts/fetch_gpi.py
"""

import csv
import logging
import re
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OUTPUT_PATH = Path(__file__).resolve().parents[1] / "data" / "raw" / "gpi_scores.csv"

# Vision of Humanity publishes GPI data in a downloadable format
# We use the public rankings page
GPI_URL = "https://www.visionofhumanity.org/maps/#/"

# Fallback: Wikipedia GPI table (more scrapable)
WIKI_GPI_URL = "https://en.wikipedia.org/wiki/Global_Peace_Index"


def fetch_gpi_from_wikipedia() -> list[dict]:
    """Scrape GPI 2024 rankings from Wikipedia."""
    # Use the Wikipedia MediaWiki API which returns JSON (no 403 issues)
    api_url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "parse",
        "page": "Global_Peace_Index",
        "prop": "text",
        "format": "json",
        "disabletoc": 1,
    }
    headers = {"User-Agent": "TriplyDataBot/1.0 (travel-planner ETL; contact@triply.app)"}
    with httpx.Client(timeout=30, follow_redirects=True, headers=headers) as client:
        resp = client.get(api_url, params=params)
        resp.raise_for_status()
        html = resp.json()["parse"]["text"]["*"]

    soup = BeautifulSoup(html, "lxml")

    # Find the main GPI rankings table
    # Wikipedia GPI page has a table with Country, Score columns
    records = []
    tables = soup.find_all("table", class_="wikitable")
    logger.info(f"Found {len(tables)} wikitables")

    for table in tables:
        headers = [th.get_text(strip=True).lower() for th in table.find_all("th")]
        logger.info(f"Table headers: {headers[:6]}")

        # Look for table with rank and score columns
        has_rank = any("rank" in h for h in headers)
        has_score = any("score" in h or "index" in h for h in headers)
        if not (has_rank or has_score):
            continue

        rows = table.find_all("tr")[1:]  # skip header
        for row in rows:
            cells = row.find_all(["td", "th"])
            if len(cells) < 3:
                continue
            try:
                texts = [c.get_text(strip=True) for c in cells]
                # Rank may have tied markers ("=4"), footnotes ("1[a]"), or be empty
                rank_raw = re.sub(r"[^0-9]", "", texts[0])
                rank = int(rank_raw) if rank_raw else 0
                # Country cell might have flag image — strip footnote markers like [a]
                country_text = re.sub(r"\[.*?\]", "", texts[1]).strip()
                score_text = texts[2].replace(",", ".")
                # Score may also have footnote markers
                score_text = re.sub(r"[^0-9.]", "", score_text)
                score = float(score_text)
                if 1.0 <= score <= 5.0 and country_text:
                    records.append({"rank": rank, "country": country_text, "score": score})
            except (ValueError, IndexError):
                continue

        if records:
            logger.info(f"Parsed {len(records)} GPI records from Wikipedia table")
            break

    return records


# ISO2 mapping for country names as they appear in GPI/Wikipedia
COUNTRY_NAME_TO_ISO2 = {
    "Iceland": "IS",
    "Ireland": "IE",
    "Austria": "AT",
    "New Zealand": "NZ",
    "Singapore": "SG",
    "Switzerland": "CH",
    "Portugal": "PT",
    "Slovenia": "SI",
    "Czech Republic": "CZ",
    "Czechia": "CZ",
    "Canada": "CA",
    "Japan": "JP",
    "Slovakia": "SK",
    "Hungary": "HU",
    "Malaysia": "MY",
    "Bhutan": "BT",
    "Finland": "FI",
    "Croatia": "HR",
    "Germany": "DE",
    "Norway": "NO",
    "Mauritius": "MU",
    "Botswana": "BW",
    "Sweden": "SE",
    "Denmark": "DK",
    "Romania": "RO",
    "Estonia": "EE",
    "Netherlands": "NL",
    "Belgium": "BE",
    "Bulgaria": "BG",
    "Spain": "ES",
    "Chile": "CL",
    "Australia": "AU",
    "Latvia": "LV",
    "Lithuania": "LT",
    "Uruguay": "UY",
    "Laos": "LA",
    "Poland": "PL",
    "Serbia": "RS",
    "Kosovo": "XK",
    "Italy": "IT",
    "Qatar": "QA",
    "France": "FR",
    "Namibia": "NA",
    "Bosnia and Herzegovina": "BA",
    "Montenegro": "ME",
    "Albania": "AL",
    "Zambia": "ZM",
    "United Kingdom": "GB",
    "Madagascar": "MG",
    "Timor-Leste": "TL",
    "Moldova": "MD",
    "Georgia": "GE",
    "Panama": "PA",
    "Guyana": "GY",
    "Ecuador": "EC",
    "Costa Rica": "CR",
    "North Macedonia": "MK",
    "Morocco": "MA",
    "Vietnam": "VN",
    "Cyprus": "CY",
    "Kazakhstan": "KZ",
    "Jordan": "JO",
    "Indonesia": "ID",
    "Bolivia": "BO",
    "Nicaragua": "NI",
    "Tanzania": "TZ",
    "Paraguay": "PY",
    "Mongolia": "MN",
    "Benin": "BJ",
    "Armenia": "AM",
    "Kuwait": "KW",
    "Malawi": "MW",
    "Ghana": "GH",
    "Sierra Leone": "SL",
    "Peru": "PE",
    "Cuba": "CU",
    "Senegal": "SN",
    "Mozambique": "MZ",
    "Kyrgyzstan": "KG",
    "Taiwan": "TW",
    "China": "CN",
    "Burkina Faso": "BF",
    "Zimbabwe": "ZW",
    "Lesotho": "LS",
    "Gabon": "GA",
    "Tajikistan": "TJ",
    "Angola": "AO",
    "United States": "US",
    "United Arab Emirates": "AE",
    "Tunisia": "TN",
    "Algeria": "DZ",
    "Saudi Arabia": "SA",
    "Israel": "IL",
    "Oman": "OM",
    "Bahrain": "BH",
    "Trinidad and Tobago": "TT",
    "Argentina": "AR",
    "Greece": "GR",
    "Uzbekistan": "UZ",
    "Brazil": "BR",
    "Mexico": "MX",
    "Ethiopia": "ET",
    "Uganda": "UG",
    "Djibouti": "DJ",
    "Azerbaijan": "AZ",
    "Guinea": "GN",
    "Rwanda": "RW",
    "Gambia": "GM",
    "Nepal": "NP",
    "Kenya": "KE",
    "Togo": "TG",
    "Thailand": "TH",
    "Cambodia": "KH",
    "Sri Lanka": "LK",
    "Papua New Guinea": "PG",
    "Ivory Coast": "CI",
    "Côte d'Ivoire": "CI",
    "Eswatini": "SZ",
    "Dominican Republic": "DO",
    "Haiti": "HT",
    "Guinea-Bissau": "GW",
    "Eritrea": "ER",
    "Niger": "NE",
    "Mali": "ML",
    "Nigeria": "NG",
    "Cameroon": "CM",
    "Bangladesh": "BD",
    "Liberia": "LR",
    "Egypt": "EG",
    "Belarus": "BY",
    "Honduras": "HN",
    "El Salvador": "SV",
    "Guatemala": "GT",
    "Venezuela": "VE",
    "Philippines": "PH",
    "Mauritania": "MR",
    "Burundi": "BI",
    "Myanmar": "MM",
    "Pakistan": "PK",
    "Colombia": "CO",
    "Turkey": "TR",
    "Türkiye": "TR",
    "India": "IN",
    "Ukraine": "UA",
    "Iran": "IR",
    "Chad": "TD",
    "Central African Republic": "CF",
    "Democratic Republic of the Congo": "CD",
    "DR Congo": "CD",
    "South Sudan": "SS",
    "Somalia": "SO",
    "Yemen": "YE",
    "Syria": "SY",
    "Afghanistan": "AF",
    "Russia": "RU",
    "Libya": "LY",
    "North Korea": "KP",
    "South Korea": "KR",
    "The Gambia": "GM",
    "Republic of the Congo": "CG",
    "Iraq": "IQ",
    "Sudan": "SD",
    "Congo": "CG",
    "Comoros": "KM",
    "Lebanon": "LB",
    "Palestine": "PS",
    "Jamaica": "JM",
    "Maldives": "MV",
    "Fiji": "FJ",
    "Bahamas": "BS",
    "Barbados": "BB",
    "Belize": "BZ",
    "Cape Verde": "CV",
    "Cabo Verde": "CV",
    "São Tomé and Príncipe": "ST",
    "Vanuatu": "VU",
    "Solomon Islands": "SB",
    "Samoa": "WS",
    "Tonga": "TO",
    "Kiribati": "KI",
    "Micronesia": "FM",
    "Marshall Islands": "MH",
    "Palau": "PW",
    "Nauru": "NR",
    "Tuvalu": "TV",
    "Seychelles": "SC",
    "Brunei": "BN",
    "Equatorial Guinea": "GQ",
    "South Africa": "ZA",
    "Swaziland": "SZ",
    "Turkmenistan": "TM",
    "Luxembourg": "LU",
    "Malta": "MT",
    "Andorra": "AD",
    "Liechtenstein": "LI",
    "Monaco": "MC",
    "San Marino": "SM",
    "Antigua and Barbuda": "AG",
    "Dominica": "DM",
    "Grenada": "GD",
    "Saint Kitts and Nevis": "KN",
    "Saint Lucia": "LC",
    "Saint Vincent and the Grenadines": "VC",
    "Trinidad & Tobago": "TT",
}


def main():
    logger.info("Fetching GPI data from Wikipedia...")
    records = fetch_gpi_from_wikipedia()

    if not records:
        logger.error("Failed to parse GPI data from Wikipedia")
        return

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    written = 0
    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
        # QUOTE_NONNUMERIC ensures ISO2 codes like "NA" are quoted and won't be
        # misread as NaN by pandas (Namibia's code is NA)
        writer = csv.writer(f, quoting=csv.QUOTE_NONNUMERIC)
        writer.writerow(["country_iso2", "gpi_score", "gpi_rank", "year"])
        for r in records:
            iso2 = COUNTRY_NAME_TO_ISO2.get(r["country"])
            if not iso2:
                logger.warning(f"No ISO2 for country: {r['country']!r}")
                continue
            writer.writerow([iso2, r["score"], r["rank"], 2025])
            written += 1

    logger.info(f"Saved {written} GPI records to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
