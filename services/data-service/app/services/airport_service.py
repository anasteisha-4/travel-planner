import math
import re
from unicodedata import normalize

from sqlalchemy.orm import Session

from app.models import Airport

CITY_IATA_OVERRIDES: dict[str, str] = {
    "абу даби": "AUH",
    "алматы": "ALA",
    "амстердам": "AMS",
    "анкара": "ANK",
    "антиб": "NCE",
    "астана": "NQZ",
    "афины": "ATH",
    "баку": "BAK",
    "бали": "DPS",
    "бангкок": "BKK",
    "барселона": "BCN",
    "берлин": "BER",
    "бишкек": "FRU",
    "будапешт": "BUD",
    "буэнос айрес": "BUE",
    "варшава": "WAW",
    "вена": "VIE",
    "владивосток": "VVO",
    "гоа": "GOI",
    "гонконг": "HKG",
    "дели": "DEL",
    "дубай": "DXB",
    "душанбе": "DYU",
    "ереван": "EVN",
    "каир": "CAI",
    "коломбо": "CMB",
    "копенгаген": "CPH",
    "куала лумпур": "KUL",
    "лимассол": "LCA",
    "лиссабон": "LIS",
    "лондон": "LON",
    "мадрид": "MAD",
    "мале": "MLE",
    "москва": "MOW",
    "мюнхен": "MUC",
    "нью йорк": "NYC",
    "нью-йорк": "NYC",
    "париж": "PAR",
    "пекин": "BJS",
    "пхукет": "HKT",
    "рим": "ROM",
    "санкт петербург": "LED",
    "санкт-петербург": "LED",
    "сеул": "SEL",
    "сингапур": "SIN",
    "сочи": "AER",
    "стамбул": "IST",
    "ташкент": "TAS",
    "тбилиси": "TBS",
    "токио": "TYO",
    "хошимин": "SGN",
    "шанхай": "SHA",
    "эдинбург": "EDI",
    "экатеринбург": "SVX",
    "южно сахалинск": "UUS",
    "yerevan": "EVN",
    "abu dhabi": "AUH",
    "almaty": "ALA",
    "amsterdam": "AMS",
    "ankara": "ANK",
    "astana": "NQZ",
    "athens": "ATH",
    "baku": "BAK",
    "bali": "DPS",
    "bangkok": "BKK",
    "barcelona": "BCN",
    "beijing": "BJS",
    "berlin": "BER",
    "bishkek": "FRU",
    "budapest": "BUD",
    "buenos aires": "BUE",
    "cairo": "CAI",
    "colombo": "CMB",
    "copenhagen": "CPH",
    "delhi": "DEL",
    "dubai": "DXB",
    "dushanbe": "DYU",
    "edinburgh": "EDI",
    "goa": "GOI",
    "hong kong": "HKG",
    "istanbul": "IST",
    "kuala lumpur": "KUL",
    "limassol": "LCA",
    "lisbon": "LIS",
    "london": "LON",
    "madrid": "MAD",
    "male": "MLE",
    "moscow": "MOW",
    "munich": "MUC",
    "new york": "NYC",
    "paris": "PAR",
    "phuket": "HKT",
    "rome": "ROM",
    "saint petersburg": "LED",
    "st petersburg": "LED",
    "saint-petersburg": "LED",
    "seoul": "SEL",
    "shanghai": "SHA",
    "singapore": "SIN",
    "sochi": "AER",
    "tashkent": "TAS",
    "tbilisi": "TBS",
    "tokyo": "TYO",
    "yekaterinburg": "SVX",
    "ekaterinburg": "SVX",
}

EARTH_RADIUS_KM = 6371.0
AIRPORT_TYPE_WEIGHT = {
    "large_airport": 0.0,
    "medium_airport": 30.0,
    "small_airport": 90.0,
}


def normalize_city(value: str | None) -> str:
    if not value:
        return ""
    ascii_value = normalize("NFKD", value).encode("ascii", "ignore").decode("ascii").lower()
    base = ascii_value if ascii_value.strip() else value.lower()
    base = re.sub(r"[,()/]", " ", base)
    return re.sub(r"\s+", " ", base).strip()


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def resolve_iata(
    db: Session,
    city_name: str | None,
    *,
    lat: float | None = None,
    lng: float | None = None,
    country_code: str | None = None,
) -> str | None:
    normalized = normalize_city(city_name)
    if normalized in CITY_IATA_OVERRIDES:
        return CITY_IATA_OVERRIDES[normalized]
    for candidate, iata in CITY_IATA_OVERRIDES.items():
        if normalized and (candidate in normalized or normalized in candidate):
            return iata

    airports = db.query(Airport).filter(Airport.iata_code.isnot(None)).all()
    if normalized:
        for airport in airports:
            municipality = normalize_city(airport.municipality)
            name = normalize_city(airport.name)
            if normalized == municipality or normalized in name:
                return airport.iata_code

    if lat is None or lng is None:
        return None

    cc = (country_code or "").upper()
    best: tuple[float, Airport] | None = None
    for airport in airports:
        distance = haversine_km(lat, lng, airport.lat, airport.lng)
        if distance > 350:
            continue
        same_country_penalty = 0.0 if not cc or airport.country_code == cc else 500.0
        scheduled_penalty = 0.0 if airport.scheduled_service else 120.0
        score = (
            distance + AIRPORT_TYPE_WEIGHT.get(airport.airport_type, 120.0) + same_country_penalty + scheduled_penalty
        )
        if best is None or score < best[0]:
            best = (score, airport)
    return best[1].iata_code if best else None
