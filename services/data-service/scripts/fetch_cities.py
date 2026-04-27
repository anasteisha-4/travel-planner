"""
Fetch top tourist cities (non-capitals) via OpenStreetMap Nominatim API
and save to data/raw/cities_supplement.csv

Nominatim is free, no registration needed (polite: 1 req/sec, User-Agent required).
https://nominatim.org/release-docs/develop/api/Search/

Usage:
    python scripts/fetch_cities.py
"""

import csv
import logging
import time
from pathlib import Path

import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OUTPUT_PATH = Path(__file__).resolve().parents[1] / "data" / "raw" / "cities_supplement.csv"

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

# Known capitals to exclude (they'll come from REST Countries)
# This list covers major capital cities that REST Countries already provides
KNOWN_CAPITALS = {
    "Paris",
    "London",
    "Berlin",
    "Madrid",
    "Rome",
    "Vienna",
    "Amsterdam",
    "Brussels",
    "Bern",
    "Stockholm",
    "Oslo",
    "Copenhagen",
    "Helsinki",
    "Dublin",
    "Lisbon",
    "Warsaw",
    "Prague",
    "Budapest",
    "Bucharest",
    "Sofia",
    "Athens",
    "Zagreb",
    "Belgrade",
    "Sarajevo",
    "Ljubljana",
    "Skopje",
    "Podgorica",
    "Tirana",
    "Pristina",
    "Valletta",
    "Nicosia",
    "Reykjavik",
    "Luxembourg",
    "Monaco",
    "Andorra la Vella",
    "Vaduz",
    "San Marino",
    "Washington",
    "Ottawa",
    "Mexico City",
    "Brasília",
    "Buenos Aires",
    "Santiago",
    "Lima",
    "Bogotá",
    "Caracas",
    "Quito",
    "La Paz",
    "Asunción",
    "Montevideo",
    "Georgetown",
    "Paramaribo",
    "Havana",
    "Kingston",
    "Port-au-Prince",
    "Santo Domingo",
    "Bridgetown",
    "Port of Spain",
    "Nassau",
    "Tokyo",
    "Beijing",
    "Seoul",
    "New Delhi",
    "Islamabad",
    "Dhaka",
    "Kathmandu",
    "Kabul",
    "Tehran",
    "Baghdad",
    "Riyadh",
    "Abu Dhabi",
    "Doha",
    "Muscat",
    "Kuwait City",
    "Manama",
    "Amman",
    "Beirut",
    "Jerusalem",
    "Cairo",
    "Tunis",
    "Algiers",
    "Tripoli",
    "Rabat",
    "Khartoum",
    "Addis Ababa",
    "Nairobi",
    "Kampala",
    "Dar es Salaam",
    "Kigali",
    "Harare",
    "Lusaka",
    "Gaborone",
    "Windhoek",
    "Pretoria",
    "Johannesburg",
    "Cape Town",
    "Abuja",
    "Lagos",
    "Accra",
    "Dakar",
    "Bamako",
    "Ouagadougou",
    "Niamey",
    "N'Djamena",
    "Bangui",
    "Kinshasa",
    "Brazzaville",
    "Libreville",
    "Yaoundé",
    "Malabo",
    "Banjul",
    "Conakry",
    "Freetown",
    "Monrovia",
    "Abidjan",
    "Lomé",
    "Cotonou",
    "Porto-Novo",
    "Mogadishu",
    "Djibouti City",
    "Asmara",
    "Lilongwe",
    "Maputo",
    "Antananarivo",
    "Moroni",
    "Victoria",
    "Port Louis",
    "Kuala Lumpur",
    "Jakarta",
    "Manila",
    "Hanoi",
    "Phnom Penh",
    "Vientiane",
    "Naypyidaw",
    "Bangkok",
    "Bandar Seri Begawan",
    "Dili",
    "Port Moresby",
    "Canberra",
    "Wellington",
    "Suva",
    "Honiara",
    "Port Vila",
    "Apia",
    "Nuku'alofa",
    "Funafuti",
    "Tarawa",
    "Palikir",
    "Majuro",
    "Ngerulmud",
    "Yaren",
    "Astana",
    "Tashkent",
    "Bishkek",
    "Dushanbe",
    "Ashgabat",
    "Tbilisi",
    "Yerevan",
    "Baku",
    "Minsk",
    "Kyiv",
    "Chișinău",
    "Riga",
    "Vilnius",
    "Tallinn",
    "Ulaanbaatar",
    "Pyongyang",
    "Taipei",
    "Thimphu",
    "Male",
    "Colombo",
    "Singapore",
}

# Top tourist cities that are NOT capitals — curated list for GeoNames lookup
TOURIST_CITIES = [
    # Europe
    ("Barcelona", "ES"),
    ("Seville", "ES"),
    ("Valencia", "ES"),
    ("Málaga", "ES"),
    ("Milan", "IT"),
    ("Venice", "IT"),
    ("Florence", "IT"),
    ("Naples", "IT"),
    ("Nice", "FR"),
    ("Lyon", "FR"),
    ("Marseille", "FR"),
    ("Bordeaux", "FR"),
    ("Hamburg", "DE"),
    ("Munich", "DE"),
    ("Cologne", "DE"),
    ("Frankfurt", "DE"),
    ("Manchester", "GB"),
    ("Edinburgh", "GB"),
    ("Birmingham", "GB"),
    ("Liverpool", "GB"),
    ("Porto", "PT"),
    ("Lisbon", "PT"),
    ("Dubrovnik", "HR"),
    ("Split", "HR"),
    ("Bruges", "BE"),
    ("Ghent", "BE"),
    ("Santorini", "GR"),
    ("Mykonos", "GR"),
    ("Thessaloniki", "GR"),
    ("Salzburg", "AT"),
    ("Innsbruck", "AT"),
    ("Krakow", "PL"),
    ("Wroclaw", "PL"),
    ("Gdansk", "PL"),
    ("Zurich", "CH"),
    ("Geneva", "CH"),
    ("Lucerne", "CH"),
    ("St. Petersburg", "RU"),
    ("Kazan", "RU"),
    ("Sochi", "RU"),
    ("Tallinn", "EE"),
    ("Riga", "LV"),
    ("Kotor", "ME"),
    ("Budva", "ME"),
    ("Mostar", "BA"),
    # Americas
    ("New York", "US"),
    ("Los Angeles", "US"),
    ("Miami", "US"),
    ("Chicago", "US"),
    ("San Francisco", "US"),
    ("Las Vegas", "US"),
    ("New Orleans", "US"),
    ("Orlando", "US"),
    ("Honolulu", "US"),
    ("Seattle", "US"),
    ("Rio de Janeiro", "BR"),
    ("São Paulo", "BR"),
    ("Salvador", "BR"),
    ("Cartagena", "CO"),
    ("Medellín", "CO"),
    ("Cusco", "PE"),
    ("Arequipa", "PE"),
    ("Cancún", "MX"),
    ("Playa del Carmen", "MX"),
    ("Guadalajara", "MX"),
    ("Puerto Vallarta", "MX"),
    ("Tulum", "MX"),
    ("Oaxaca", "MX"),
    ("Santa Marta", "CO"),
    ("Punta Cana", "DO"),
    ("Cuzco", "PE"),
    # Asia
    ("Dubai", "AE"),
    ("Sharjah", "AE"),
    ("Shanghai", "CN"),
    ("Guangzhou", "CN"),
    ("Shenzhen", "CN"),
    ("Xi'an", "CN"),
    ("Chengdu", "CN"),
    ("Guilin", "CN"),
    ("Hangzhou", "CN"),
    ("Hong Kong", "HK"),
    ("Macau", "MO"),
    ("Osaka", "JP"),
    ("Kyoto", "JP"),
    ("Sapporo", "JP"),
    ("Hiroshima", "JP"),
    ("Busan", "KR"),
    ("Jeju", "KR"),
    ("Bali", "ID"),
    ("Yogyakarta", "ID"),
    ("Lombok", "ID"),
    ("Komodo", "ID"),
    ("Phuket", "TH"),
    ("Chiang Mai", "TH"),
    ("Pattaya", "TH"),
    ("Krabi", "TH"),
    ("Ho Chi Minh City", "VN"),
    ("Hoi An", "VN"),
    ("Da Nang", "VN"),
    ("Ha Long", "VN"),
    ("Siem Reap", "KH"),
    ("Luang Prabang", "LA"),
    ("Penang", "MY"),
    ("Langkawi", "MY"),
    ("Kota Kinabalu", "MY"),
    ("Boracay", "PH"),
    ("Palawan", "PH"),
    ("Cebu", "PH"),
    ("Colombo", "LK"),
    ("Sigiriya", "LK"),
    ("Agra", "IN"),
    ("Jaipur", "IN"),
    ("Varanasi", "IN"),
    ("Goa", "IN"),
    ("Mumbai", "IN"),
    ("Udaipur", "IN"),
    ("Lahore", "PK"),
    # Middle East
    ("Istanbul", "TR"),
    ("Antalya", "TR"),
    ("Cappadocia", "TR"),
    ("Bodrum", "TR"),
    ("Petra", "JO"),
    ("Musandam", "OM"),
    ("Samarkand", "UZ"),
    ("Bukhara", "UZ"),
    # Africa
    ("Marrakech", "MA"),
    ("Fez", "MA"),
    ("Casablanca", "MA"),
    ("Cairo", "EG"),
    ("Luxor", "EG"),
    ("Aswan", "EG"),
    ("Cape Town", "ZA"),
    ("Johannesburg", "ZA"),
    ("Durban", "ZA"),
    ("Zanzibar", "TZ"),
    ("Arusha", "TZ"),
    ("Mombasa", "KE"),
    ("Hurghada", "EG"),
    ("Sharm el-Sheikh", "EG"),
    ("Nairobi", "KE"),
    ("Tbilisi", "GE"),
    ("Batumi", "GE"),
    # Oceania
    ("Sydney", "AU"),
    ("Melbourne", "AU"),
    ("Brisbane", "AU"),
    ("Gold Coast", "AU"),
    ("Queenstown", "NZ"),
    ("Christchurch", "NZ"),
    ("Auckland", "NZ"),
    # Island destinations
    ("Malé", "MV"),
    ("Nassau", "BS"),
]


HEADERS = {"User-Agent": "TriplyDataBot/1.0 (travel-planner ETL; contact@triply.app)"}


def fetch_city_info(city: str, country_code: str) -> dict | None:
    """Fetch city coordinates from Nominatim OpenStreetMap API."""
    params = {
        "q": city,
        "countrycodes": country_code.lower(),
        "limit": 1,
        "format": "jsonv2",
        "addressdetails": 0,
        "extratags": 1,  # includes population when available
    }
    try:
        with httpx.Client(timeout=10, headers=HEADERS) as client:
            resp = client.get(NOMINATIM_URL, params=params)
            resp.raise_for_status()
            results = resp.json()

        if not results:
            logger.warning(f"No Nominatim result for {city}, {country_code}")
            return None

        r = results[0]
        population = None
        extra = r.get("extratags") or {}
        import contextlib

        if extra.get("population"):
            with contextlib.suppress(ValueError, TypeError):
                population = int(extra["population"])

        return {
            "name": city,
            "country_code": country_code,
            "lat": float(r["lat"]),
            "lng": float(r["lon"]),
            "region": None,
            "subregion": None,
            "population": population,
        }
    except Exception as e:
        logger.warning(f"Failed to fetch {city}, {country_code}: {e}")
        return None


def main():
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    results = []
    for i, (city, country_code) in enumerate(TOURIST_CITIES):
        logger.info(f"[{i + 1}/{len(TOURIST_CITIES)}] Fetching {city}, {country_code}...")
        info = fetch_city_info(city, country_code)
        if info:
            results.append(info)
        time.sleep(1.1)  # Nominatim policy: max 1 req/sec

    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "name",
                "country_code",
                "lat",
                "lng",
                "region",
                "subregion",
                "population",
            ],
        )
        writer.writeheader()
        writer.writerows(results)

    logger.info(f"Saved {len(results)} tourist cities to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
