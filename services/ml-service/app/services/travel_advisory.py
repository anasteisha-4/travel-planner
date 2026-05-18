"""Hard travel-advisory exclusions for recommendation candidates.

The recommendation pipeline applies this before content/LTR scoring and before
LLM review. That makes safety blocks deterministic: a blocked destination cannot
be reintroduced by ranker score, region filters, or Qwen adjustments.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

CIS_CITIZENSHIP_CODES = {"RU", "BY", "KZ", "AM", "KG", "UZ", "TJ"}

DEFAULT_BLOCKED_COUNTRIES_CIS = {
    "AE",
    "BH",
    "CU",
    "IL",
    "IR",
    "KW",
    "OM",
    "QA",
    "SA",
}

DEFAULT_DOMESTIC_BLOCKED_NAMES_RU = {
    "bryansk",
    "брянск",
    "rostov-on-don",
    "rostov on don",
    "ростов-на-дону",
    "ростов на дону",
}

RULES_PATH = Path(__file__).resolve().parents[1] / "data" / "travel_advisory_rules.json"


def _normalize_code(value: Any) -> str:
    return str(value or "").strip().upper()


def _normalize_name(value: Any) -> str:
    return str(value or "").strip().casefold().replace("ё", "е")


@lru_cache(maxsize=1)
def _load_rules() -> dict[str, Any]:
    if not RULES_PATH.exists():
        return {}
    try:
        raw = json.loads(RULES_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _blocked_country_codes(citizenship_code: str) -> set[str]:
    rules = _load_rules()
    by_citizenship = rules.get("blocked_countries_by_citizenship")
    if isinstance(by_citizenship, dict):
        exact = by_citizenship.get(citizenship_code)
        if isinstance(exact, list):
            return {_normalize_code(code) for code in exact}
        cis = by_citizenship.get("CIS")
        if citizenship_code in CIS_CITIZENSHIP_CODES and isinstance(cis, list):
            return {_normalize_code(code) for code in cis}

    if citizenship_code in CIS_CITIZENSHIP_CODES:
        return set(DEFAULT_BLOCKED_COUNTRIES_CIS)
    return set()


def _blocked_domestic_names(citizenship_code: str) -> set[str]:
    rules = _load_rules()
    by_citizenship = rules.get("blocked_domestic_names_by_citizenship")
    if isinstance(by_citizenship, dict):
        exact = by_citizenship.get(citizenship_code)
        if isinstance(exact, list):
            return {_normalize_name(name) for name in exact}

    if citizenship_code == "RU":
        return set(DEFAULT_DOMESTIC_BLOCKED_NAMES_RU)
    return set()


def _block_record(destination: dict, reason: str) -> dict[str, Any]:
    return {
        "destination_id": str(destination.get("id")),
        "name": destination.get("name"),
        "country_code": destination.get("country_code"),
        "reason": reason,
    }


def filter_destinations_by_travel_advisory(
    *,
    destinations: list[dict],
    citizenship_code: str,
) -> tuple[list[dict], list[dict]]:
    normalized_citizenship = _normalize_code(citizenship_code)
    blocked_countries = _blocked_country_codes(normalized_citizenship)
    blocked_domestic_names = _blocked_domestic_names(normalized_citizenship)

    allowed: list[dict] = []
    blocked: list[dict] = []

    for destination in destinations:
        country_code = _normalize_code(destination.get("country_code"))
        destination_name = _normalize_name(destination.get("name"))
        display_name = _normalize_name(destination.get("display_name") or destination.get("name_ru"))

        if country_code in blocked_countries:
            blocked.append(_block_record(destination, "country_travel_advisory"))
            continue

        if (
            normalized_citizenship == "RU"
            and country_code == "RU"
            and (destination_name in blocked_domestic_names or display_name in blocked_domestic_names)
        ):
            blocked.append(_block_record(destination, "domestic_security_advisory"))
            continue

        allowed.append(destination)

    return allowed, blocked
