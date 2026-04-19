"""OpenFlights connectivity extractor.

Reads connectivity_overrides.csv (manually curated top-50 destinations)
and applies rule-based logic for the remaining destinations by country_code.

Data source: connectivity_overrides.csv (manual curation based on post-2022 situation).

All rules represent the situation for Russian travelers as of 2025:
- Direct flights suspended to EU/US/UK after Feb 2022
- Mir card accepted in limited countries only
- Dubai (AE), Istanbul (TR), Yerevan (AM), Tashkent (UZ), Tbilisi (GE) are main hubs
"""

import csv
import logging
import os

logger = logging.getLogger(__name__)

# CSV path relative to data-service root
_OVERRIDES_CSV = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "raw", "connectivity_overrides.csv"
)

# Country codes with direct flights from Moscow (post-2022 situation)
_DIRECT_FROM_MOSCOW: frozenset[str] = frozenset(
    {
        # CIS
        "KZ",
        "BY",
        "UZ",
        "KG",
        "TJ",
        "TM",
        "AZ",
        "AM",
        "GE",
        "MD",
        # Major tourist destinations with maintained direct routes
        "TR",
        "EG",
        "AE",
        "TH",
        "IN",
        "CN",
        "IL",
        "VN",
        # Cuba (Aeroflot)
        "CU",
        # Domestic — not applicable (no country_code for cities within RU)
    }
)

# Country codes with direct flights from SPb (subset of Moscow)
_DIRECT_FROM_SPB: frozenset[str] = frozenset(
    {
        "KZ",
        "BY",
        "UZ",
        "TR",
        "EG",
        "AE",
        "CN",
    }
)

# Country codes with direct flights from Ekaterinburg
_DIRECT_FROM_EKB: frozenset[str] = frozenset(
    {
        "KZ",
        "UZ",
        "TR",
        "AE",
    }
)

# Country codes with direct flights from Novosibirsk
_DIRECT_FROM_NSK: frozenset[str] = frozenset(
    {
        "KZ",
        "UZ",
        "KG",
        "TR",
        "AE",
    }
)

# Countries where Mir card is accepted (as of 2025)
_MIR_ACCEPTED: frozenset[str] = frozenset(
    {
        "TR",
        "VN",
        "CU",
        "AM",
        "KZ",
        "KG",
        "TJ",
        "UZ",
        "BY",
        "AZ",
        "TM",
        "GE",
        "MD",
    }
)

# Countries accessible by train from Moscow
_TRAIN_FROM_MOSCOW: frozenset[str] = frozenset(
    {
        "BY",
        "UA",  # Belarus (direct), Ukraine (suspended)
        "KZ",
        "MN",
        "CN",  # Trans-Siberian / Trans-Mongolian
        "UZ",  # Via Kazakhstan
    }
)

# Approximate train hours from Moscow (one-way)
_TRAIN_HOURS: dict[str, float] = {
    "BY": 8.0,
    "KZ": 72.0,
    "UZ": 70.0,
    "MN": 100.0,
    "CN": 130.0,
}

# Approximate flight hours from Moscow (non-stop or nearest airport)
_FLIGHT_HOURS: dict[str, float] = {
    "BY": 2.0,
    "UA": 2.5,
    "MD": 2.5,
    "TR": 4.0,
    "AM": 3.5,
    "GE": 3.0,
    "AZ": 3.5,
    "IL": 4.5,
    "EG": 4.5,
    "KZ": 3.5,
    "UZ": 4.0,
    "KG": 4.5,
    "TJ": 5.5,
    "TM": 5.0,
    "AE": 6.0,
    "QA": 5.5,
    "IN": 6.5,
    "TH": 9.5,
    "CN": 8.5,
    "MN": 7.0,
    "JP": 9.0,
    "KR": 9.5,
    "VN": 10.5,
    "ID": 11.0,
    "MY": 10.0,
    "LK": 9.0,
    "MV": 8.5,
    "CU": 14.0,
    "ZA": 11.0,
    # Europe — all via hubs post-2022
    "FR": 5.0,
    "DE": 3.5,
    "IT": 4.0,
    "ES": 5.0,
    "PT": 5.5,
    "GR": 4.0,
    "CY": 3.5,
    "BG": 3.5,
    "RS": 3.5,
    "ME": 3.5,
    "BA": 4.0,
    "AT": 3.5,
    "CH": 4.0,
    "NL": 4.0,
    "BE": 4.0,
    "SE": 3.0,
    "NO": 3.5,
    "FI": 2.5,
    "DK": 3.0,
    "PL": 3.0,
    "CZ": 3.0,
    "HU": 3.0,
    "RO": 3.0,
    "HR": 3.5,
    "SI": 4.0,
    "SK": 3.5,
    "LV": 2.5,
    "LT": 2.5,
    "EE": 2.5,
    "MA": 6.0,
    "TN": 5.0,
    "DZ": 5.5,
    "LY": 5.0,
    "MX": 14.0,
    "BR": 14.0,
    "AR": 16.0,
    "PE": 17.0,
    "CO": 15.0,
    "CL": 18.0,
    "US": 12.0,
    "CA": 11.0,
    "AU": 18.0,
    "NZ": 22.0,
    "SG": 11.0,
    "HK": 9.5,
    "TW": 9.0,
    "PH": 11.5,
    "MM": 10.0,
    "KH": 10.0,
    "NP": 7.0,
    "BD": 8.0,
    "PK": 6.5,
    "AF": 6.0,
    "KE": 9.0,
    "TZ": 9.5,
    "ET": 8.0,
    "JO": 4.5,
    "SA": 5.5,
    "IQ": 5.0,
    "IR": 4.5,
    "LB": 4.0,
    "SY": 4.5,
    "OM": 5.5,
    "BH": 5.5,
    "YE": 6.0,
    "IS": 5.0,
    "IE": 4.5,
    "GB": 4.0,
    "LU": 4.0,
    "SC": 9.0,
    "MU": 10.0,
    "DO": 14.0,
    "JM": 14.0,
    "TT": 15.0,
    "BB": 14.5,
    "BS": 14.0,
}

# Countries where transit via Dubai is typical (1 stop)
_TRANSIT_DUBAI: frozenset[str] = frozenset(
    {
        "TH",
        "ID",
        "MY",
        "SG",
        "VN",
        "PH",
        "LK",
        "MV",
        "NP",
        "BD",
        "JP",
        "KR",
        "HK",
        "TW",
        "KH",
        "MM",
        "LA",
        "KE",
        "TZ",
        "ZA",
        "ET",
        "MU",
        "SC",
        "MG",
        "RW",
        "UG",
        "TZ",
        "AU",
        "NZ",
        "MA",
        "TN",
        "IN",
        "OM",
        "BH",
        "YE",
        "PK",
        "AF",
    }
)

# Countries where transit via Istanbul is typical (1 stop)
_TRANSIT_ISTANBUL: frozenset[str] = frozenset(
    {
        "GR",
        "CY",
        "BG",
        "RS",
        "ME",
        "BA",
        "HR",
        "SI",
        "AL",
        "MK",
        "MA",
        "TN",
        "DZ",
        "DE",
        "FR",
        "IT",
        "ES",
        "PT",
        "NL",
        "BE",
        "AT",
        "CH",
        "SE",
        "DK",
        "NO",
        "FI",
        "IS",
        "IE",
        "GB",
        "PL",
        "CZ",
        "HU",
        "RO",
        "LV",
        "LT",
        "EE",
        "SK",
        "BR",
        "AR",
        "CO",
        "PE",
        "CL",
        "MX",
        "US",
        "CA",
        "DO",
        "JM",
        "TT",
        "BB",
        "BS",
        "JP",
        "KR",
        "NG",
        "GH",
        "SN",
        "CI",
    }
)

# Countries where transit via Yerevan is an option
_TRANSIT_YEREVAN: frozenset[str] = frozenset(
    {
        "FR",
        "DE",
        "IT",
        "ES",
        "GR",
        "CY",
        "IL",
        "LB",
        "JO",
        "IN",
    }
)

# Countries where transit via Tashkent is an option
_TRANSIT_TASHKENT: frozenset[str] = frozenset(
    {
        "TJ",
        "AF",
        "IN",
        "NP",
        "BD",
        "KG",
    }
)

# Countries where transit via Tbilisi is an option
_TRANSIT_TBILISI: frozenset[str] = frozenset(
    {
        "TR",
        "AM",
        "AZ",
        "DE",
        "FR",
        "GR",
        "CY",
    }
)


def _parse_bool(val: str) -> bool:
    return str(val).strip().lower() in ("true", "1", "yes")


def _parse_float(val: str) -> float | None:
    val = val.strip()
    if not val:
        return None
    try:
        return float(val)
    except ValueError:
        return None


def load_overrides() -> dict[str, dict]:
    """Load manual connectivity overrides keyed by country_code."""
    overrides: dict[str, dict] = {}
    path = os.path.normpath(_OVERRIDES_CSV)
    if not os.path.exists(path):
        logger.warning(
            f"connectivity_overrides.csv not found at {path}, skipping overrides."
        )
        return overrides
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cc = row["country_code"].strip().upper()
            overrides[cc] = {
                "direct_from_moscow": _parse_bool(row["direct_from_moscow"]),
                "direct_from_spb": _parse_bool(row["direct_from_spb"]),
                "direct_from_ekb": _parse_bool(row["direct_from_ekb"]),
                "direct_from_novosibirsk": _parse_bool(row["direct_from_novosibirsk"]),
                "transit_via_dubai": _parse_bool(row["transit_via_dubai"]),
                "transit_via_istanbul": _parse_bool(row["transit_via_istanbul"]),
                "transit_via_yerevan": _parse_bool(row["transit_via_yerevan"]),
                "transit_via_tashkent": _parse_bool(row["transit_via_tashkent"]),
                "transit_via_tbilisi": _parse_bool(row["transit_via_tbilisi"]),
                "train_from_moscow": _parse_bool(row["train_from_moscow"]),
                "train_hours_from_moscow": _parse_float(row["train_hours_from_moscow"]),
                "flight_hours_from_moscow": _parse_float(
                    row["flight_hours_from_moscow"]
                ),
                "min_transit_hours": _parse_float(row["min_transit_hours"]),
                "mir_card_accepted": _parse_bool(row["mir_card_accepted"]),
            }
    logger.info(f"Loaded {len(overrides)} connectivity overrides.")
    return overrides


def get_connectivity_for_country(cc: str, overrides: dict[str, dict]) -> dict:
    """Return connectivity data for a country_code, applying override if available."""
    if cc in overrides:
        data = dict(overrides[cc])
        data["data_source"] = "manual_override"
        return data

    direct_msk = cc in _DIRECT_FROM_MOSCOW
    data = {
        "direct_from_moscow": direct_msk,
        "direct_from_spb": cc in _DIRECT_FROM_SPB,
        "direct_from_ekb": cc in _DIRECT_FROM_EKB,
        "direct_from_novosibirsk": cc in _DIRECT_FROM_NSK,
        "transit_via_dubai": cc in _TRANSIT_DUBAI,
        "transit_via_istanbul": cc in _TRANSIT_ISTANBUL,
        "transit_via_yerevan": cc in _TRANSIT_YEREVAN,
        "transit_via_tashkent": cc in _TRANSIT_TASHKENT,
        "transit_via_tbilisi": cc in _TRANSIT_TBILISI,
        "train_from_moscow": cc in _TRAIN_FROM_MOSCOW,
        "train_hours_from_moscow": _TRAIN_HOURS.get(cc),
        "flight_hours_from_moscow": _FLIGHT_HOURS.get(cc),
        "min_transit_hours": None,
        "mir_card_accepted": cc in _MIR_ACCEPTED,
        "data_source": "rule_based",
    }
    return data
