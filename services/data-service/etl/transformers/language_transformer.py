"""Compute destination_language_accessibility from rule-based country_code logic.

All rules are derived from the perspective of a CIS (primarily Russian-speaking)
traveler who may also speak limited English.

russian_speaking_score:
  1.0  — Russian is an official/co-official language
  0.9  — CIS countries: Russian is widely understood (post-Soviet legacy)
  0.75 — TR/EG/CY: large Russian-speaking tourist infrastructure
  0.7  — BG: strong Slavic/Soviet ties, Cyrillic script shared
  0.5  — IL: large Russian-speaking diaspora
  0.45 — ME/RS/MK: partial Slavic intelligibility
  0.35 — EU Latin countries: Russian poorly understood, but tourism English covers
  0.2  — CJK, Southeast Asia, Arabic countries: Russian very rare
  0.15 — remote/isolated countries: minimal tourist infrastructure

english_speaking_score:
  0.95 — native-English nations
  0.85 — SG, MT, CY, PH: English is co-official with high penetration
  0.75 — Nordic + NL + CH + IE: very high English proficiency
  0.65 — W. Europe: good English in cities/tourism
  0.5  — E. Europe, Balkans, Baltics: moderate English in tourism
  0.4  — CIS (ex-RU), TR, EG: English in tourist zones only
  0.3  — RU: English limited to major cities
  0.25 — Central Asia, Caucasus: minimal English outside capitals
  0.2  — Arab world, South Asia, SEA non-tourist: variable, often low
  0.15 — Sub-Saharan Africa, Pacific islands (ex-English): very limited

script_difficulty (from a Russian reader's perspective):
  easy     — Latin and Cyrillic scripts (both familiar or learnable)
  moderate — Arabic, Greek, Hebrew, Devanagari, Georgian, Armenian, Thai-adjacent
  hard     — CJK (Chinese/Japanese/Korean), Thai, Khmer, Myanmar, Lao, Tibetan

has_cyrillic_signs: True where Cyrillic appears on public signs/menus for tourists.
"""

import logging

logger = logging.getLogger(__name__)

# ── Russian-speaking score rules ────────────────────────────────────────────

_RUSSIAN_IS_OFFICIAL: frozenset[str] = frozenset({"RU"})

_CIS: frozenset[str] = frozenset(
    {
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
        "UA",
    }
)

# Heavy Russian tourist infrastructure (TR, EG, CY treated as one tier)
_RU_TOURIST_HEAVY: frozenset[str] = frozenset({"TR", "EG", "CY"})

# Bulgaria: strong Cyrillic/Slavic tie
_RU_BULGARIA: frozenset[str] = frozenset({"BG"})

# Israel: large Russian-speaking diaspora (~1.5M, ~20% of population)
_RU_DIASPORA: frozenset[str] = frozenset({"IL"})

# Partial Slavic intelligibility
_RU_SLAVIC_PARTIAL: frozenset[str] = frozenset(
    {"RS", "ME", "MK", "BA", "HR", "SI", "SK", "PL", "CZ"}
)

# EU / developed Latin-script countries
_EU_LATIN: frozenset[str] = frozenset(
    {
        "FR",
        "ES",
        "IT",
        "PT",
        "DE",
        "AT",
        "CH",
        "NL",
        "BE",
        "SE",
        "DK",
        "NO",
        "FI",
        "IS",
        "IE",
        "LU",
        "LI",
        "AD",
        "SM",
        "MC",
        "VA",
        "LV",
        "LT",
        "EE",
        "RO",
        "HU",
        "GR",
        "AL",
        "MK",  # MK also in Slavic partial; this tier takes lower
    }
)

# ── English-speaking score rules ────────────────────────────────────────────

_ENGLISH_NATIVE: frozenset[str] = frozenset(
    {
        "US",
        "GB",
        "AU",
        "NZ",
        "CA",
        "IE",
    }
)

_ENGLISH_COOFFICIAL_HIGH: frozenset[str] = frozenset(
    {
        "SG",
        "MT",
        "CY",
        "PH",
        "JM",
        "TT",
        "BB",
        "BS",
        "BZ",
        "GY",
        "ZA",
        "NG",
        "KE",
        "GH",
        "TZ",
        "UG",
        "ZW",
        "ZM",
        "MW",
        "RW",
        "BW",
        "NA",
        "SL",
        "LR",
        "GM",
    }
)

_ENGLISH_NORDIC_HIGH: frozenset[str] = frozenset(
    {
        "SE",
        "DK",
        "NO",
        "FI",
        "NL",
        "LU",
    }
)

_ENGLISH_W_EUROPE: frozenset[str] = frozenset(
    {
        "DE",
        "AT",
        "CH",
        "BE",
        "FR",
        "IS",
        "LI",
        "ES",
        "IT",
        "PT",
    }
)

_ENGLISH_E_EUROPE: frozenset[str] = frozenset(
    {
        "PL",
        "CZ",
        "SK",
        "HU",
        "RO",
        "BG",
        "HR",
        "SI",
        "RS",
        "ME",
        "BA",
        "AL",
        "MK",
        "GR",
        "LV",
        "LT",
        "EE",
    }
)

_ENGLISH_TOURIST_ZONES: frozenset[str] = frozenset(
    {
        "TR",
        "EG",
        "TH",
        "ID",
        "MY",
        "VN",
        "IN",
        "LK",
        "NP",
        "MA",
        "TN",
        "JO",
        "AE",
        "QA",
        "BH",
        "OM",
        "KW",
        "SA",
        "MX",
        "BR",
        "AR",
        "CO",
        "PE",
        "CL",
        "EC",
        "CU",
        "DO",
        "CR",
        "PA",
        "JP",
        "KR",
        "HK",
        "MO",
        "TW",
        "MV",
        "SC",
        "MU",
        "MG",
        "ET",
        "SN",
        "CI",
    }
)

# ── Script difficulty ────────────────────────────────────────────────────────

_SCRIPT_HARD: frozenset[str] = frozenset(
    {
        # CJK
        "CN",
        "TW",
        "HK",
        "MO",
        "JP",
        "KR",
        # Thai
        "TH",
        # Khmer
        "KH",
        # Myanmar
        "MM",
        # Lao
        "LA",
        # Tibetan-script (Bhutan uses Dzongkha/Tibetan)
        "BT",
        # Sinhala (Sri Lanka)
        "LK",
        # Ethiopic
        "ET",
        "ER",
    }
)

_SCRIPT_MODERATE: frozenset[str] = frozenset(
    {
        # Arabic-script countries
        "SA",
        "AE",
        "QA",
        "BH",
        "KW",
        "OM",
        "YE",
        "IQ",
        "SY",
        "JO",
        "LB",
        "EG",
        "LY",
        "TN",
        "DZ",
        "MA",
        "MR",
        "SD",
        "SO",
        "DJ",
        "IR",
        "AF",
        "PK",
        # Hebrew
        "IL",
        # Greek
        "GR",
        "CY",
        # Devanagari / Indic scripts
        "IN",
        "NP",
        "BD",
        # Georgian (unique script, but CIS neighbor — moderate not hard)
        "GE",
        # Armenian (unique script, CIS neighbor)
        "AM",
        # Mongolian (Cyrillic official but traditional script present)
        # Keep MN as easy (Cyrillic is standard)
    }
)

# ── has_cyrillic_signs ───────────────────────────────────────────────────────
# Countries where Cyrillic appears on tourist infrastructure signs/menus.
# Includes official Cyrillic states + high-Russian-tourism destinations.
_CYRILLIC_SIGNS: frozenset[str] = frozenset(
    {
        # Official Cyrillic script
        "RU",
        "UA",
        "BY",
        "KZ",
        "KG",
        "TJ",
        "MN",
        "BG",
        "MK",
        "RS",
        # Post-Soviet countries where Russian remains common on signs
        "UZ",
        "TM",
        "AZ",
        "AM",
        "GE",
        "MD",
        # Heavy Russian tourism — Cyrillic menus common
        "TR",
        "EG",
        "CY",
    }
)


# ── Score lookup ─────────────────────────────────────────────────────────────


def _russian_score(cc: str) -> float:
    if cc in _RUSSIAN_IS_OFFICIAL:
        return 1.0
    if cc in _CIS:
        return 0.9
    if cc in _RU_TOURIST_HEAVY:
        return 0.75
    if cc in _RU_BULGARIA:
        return 0.7
    if cc in _RU_DIASPORA:
        return 0.5
    if cc in _RU_SLAVIC_PARTIAL:
        return 0.45
    if cc in _EU_LATIN:
        return 0.35
    return 0.2


def _english_score(cc: str) -> float:
    if cc in _ENGLISH_NATIVE:
        return 0.95
    if cc in _ENGLISH_COOFFICIAL_HIGH:
        return 0.85
    if cc in _ENGLISH_NORDIC_HIGH:
        return 0.75
    if cc in _ENGLISH_W_EUROPE:
        return 0.65
    if cc in _ENGLISH_E_EUROPE:
        return 0.5
    if cc in _ENGLISH_TOURIST_ZONES:
        return 0.4
    if cc == "RU":
        return 0.3
    if cc in _CIS:
        return 0.25
    return 0.2


def _script_difficulty(cc: str) -> str:
    if cc in _SCRIPT_HARD:
        return "hard"
    if cc in _SCRIPT_MODERATE:
        return "moderate"
    return "easy"


# ── Main transformer ─────────────────────────────────────────────────────────


def transform_language_accessibility(
    country_languages: dict[str, list[str]],
    skip_existing: bool = False,
) -> list[dict]:
    """Build language_accessibility records for all active destinations.

    Args:
        country_languages: {country_code: [iso_639_1_codes]} from REST Countries.
                           Pass empty dict to fall back to rule-based local_languages.
        skip_existing: If True, skip destinations that already have a language record.

    Returns list[dict] ready for upsert into destination_language_accessibility.
    """
    from app.database import SessionLocal
    from app.models import Destination
    from app.models.language import DestinationLanguageAccessibility

    db = SessionLocal()
    try:
        destinations = (
            db.query(Destination)
            .filter(Destination.is_active == True)  # noqa: E712
            .all()
        )
        if skip_existing:
            existing = db.query(DestinationLanguageAccessibility.destination_id).all()
            existing_ids = {str(r[0]) for r in existing}
            before = len(destinations)
            destinations = [d for d in destinations if str(d.id) not in existing_ids]
            logger.info(
                f"skip_existing=True: skipping {before - len(destinations)}, {len(destinations)} remaining."
            )
    finally:
        db.close()

    records = []
    for dest in destinations:
        cc = (dest.country_code or "").upper()

        local_langs = country_languages.get(cc, [])

        # Ensure Russian is listed for countries where it's official/widespread
        if cc in _RUSSIAN_IS_OFFICIAL | _CIS and "ru" not in local_langs:
            local_langs = ["ru"] + local_langs

        ru_score = round(_russian_score(cc), 2)
        en_score = round(_english_score(cc), 2)
        cyrillic = cc in _CYRILLIC_SIGNS
        script = _script_difficulty(cc)

        records.append(
            {
                "destination_id": str(dest.id),
                "local_languages": local_langs,
                "russian_speaking_score": ru_score,
                "english_speaking_score": en_score,
                "has_cyrillic_signs": cyrillic,
                "script_difficulty": script,
                "data_source": "rule_based",
            }
        )

    logger.info(
        f"Transformed {len(records)} language_accessibility records. "
        f"russian≥0.7: {sum(1 for r in records if r['russian_speaking_score'] >= 0.7)}, "
        f"script_hard: {sum(1 for r in records if r['script_difficulty'] == 'hard')}."
    )
    return records
