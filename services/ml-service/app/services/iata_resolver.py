import re
from functools import lru_cache
from unicodedata import normalize

import httpx

from app.config import settings

_CITY_IATA_OVERRIDES: dict[str, str] = {
    "абу даби": "AUH",
    "алматы": "ALA",
    "амстердам": "AMS",
    "анкара": "ANK",
    "астана": "NQZ",
    "афины": "ATH",
    "баку": "BAK",
    "бали": "DPS",
    "бангкок": "BKK",
    "барселона": "BCN",
    "берлин": "BER",
    "бишкек": "FRU",
    "будапешт": "BUD",
    "варшава": "WAW",
    "вена": "VIE",
    "дубай": "DXB",
    "ереван": "EVN",
    "каир": "CAI",
    "лиссабон": "LIS",
    "лондон": "LON",
    "мадрид": "MAD",
    "мале": "MLE",
    "москва": "MOW",
    "париж": "PAR",
    "пхукет": "HKT",
    "рим": "ROM",
    "санкт петербург": "LED",
    "санкт-петербург": "LED",
    "стамбул": "IST",
    "тбилиси": "TBS",
    "токио": "TYO",
    "шарм эль шейх": "SSH",
    "экатеринбург": "SVX",
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
    "berlin": "BER",
    "bishkek": "FRU",
    "budapest": "BUD",
    "cairo": "CAI",
    "dubai": "DXB",
    "istanbul": "IST",
    "lisbon": "LIS",
    "london": "LON",
    "madrid": "MAD",
    "male": "MLE",
    "moscow": "MOW",
    "paris": "PAR",
    "phuket": "HKT",
    "rome": "ROM",
    "saint petersburg": "LED",
    "saint-petersburg": "LED",
    "sharm el sheikh": "SSH",
    "tbilisi": "TBS",
    "tokyo": "TYO",
    "yekaterinburg": "SVX",
}


def _normalize_city(value: str | None) -> str:
    if not value:
        return ""
    ascii_value = normalize("NFKD", value).encode("ascii", "ignore").decode("ascii").lower()
    base = ascii_value if ascii_value.strip() else value.lower()
    base = re.sub(r"[,()/]", " ", base)
    return re.sub(r"\s+", " ", base).strip()


def _override_iata(city_name: str | None) -> str | None:
    normalized = _normalize_city(city_name)
    if normalized in _CITY_IATA_OVERRIDES:
        return _CITY_IATA_OVERRIDES[normalized]
    for candidate, iata in _CITY_IATA_OVERRIDES.items():
        if normalized and (candidate in normalized or normalized in candidate):
            return iata
    return None


@lru_cache(maxsize=4096)
def _resolve_iata_from_data_service(
    city_name: str | None,
    lat: float | None,
    lng: float | None,
    country_code: str | None,
) -> str | None:
    secret = settings.INTERNAL_API_SECRET or settings.DATA_SERVICE_SECRET
    if not secret:
        return None
    try:
        response = httpx.get(
            f"{settings.DATA_SERVICE_URL}/internal/airports/resolve-iata",
            params={
                "city_name": city_name,
                "lat": lat,
                "lng": lng,
                "country_code": country_code,
            },
            headers={"X-Internal-Secret": secret},
            timeout=2.0,
        )
        response.raise_for_status()
        value = response.json().get("iata_code")
        return str(value).upper() if value else None
    except Exception:
        return None


def resolve_iata(
    city_name: str | None,
    *,
    lat: float | None = None,
    lng: float | None = None,
    country_code: str | None = None,
) -> str | None:
    return _override_iata(city_name) or _resolve_iata_from_data_service(city_name, lat, lng, country_code)
