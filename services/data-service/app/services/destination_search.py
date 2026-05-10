import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher

try:
    from rapidfuzz import fuzz
except ModuleNotFoundError:
    fuzz = None

WORD_RE = re.compile(r"[\w]+", re.UNICODE)


@dataclass(frozen=True)
class DestinationSearchCandidate:
    key: str
    name: str
    country_code: str | None = None
    population: int | None = None
    capital: bool = False


@dataclass(frozen=True)
class DestinationSearchMatch:
    key: str
    score: float


def normalize_search_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold().replace("ё", "е"))
    ascii_folded = "".join(char for char in normalized if not unicodedata.combining(char))
    words = WORD_RE.findall(ascii_folded)
    return " ".join(words)


def destination_search_aliases(original_name: str, display_name: str) -> list[str]:
    normalized_names = {normalize_search_text(original_name), normalize_search_text(display_name)}
    if {"st petersburg", "санкт петербург"} & normalized_names:
        return [
            "Saint Petersburg",
            "St Petersburg",
            "Сан Петербург",
            "Санкт Петербург",
            "Питер",
            "СПб",
        ]
    return []


def _tokens(value: str) -> list[str]:
    return [token for token in value.split() if token]


def _variant_score(query: str, candidate: str) -> float:
    if not query or not candidate:
        return 0.0
    if candidate == query:
        return 1000.0
    if candidate.startswith(query):
        return 930.0 - min(len(candidate) - len(query), 80) * 0.4

    query_tokens = _tokens(query)
    candidate_tokens = _tokens(candidate)
    if query_tokens and candidate_tokens:
        if all(any(token == candidate_token for candidate_token in candidate_tokens) for token in query_tokens):
            return 920.0 - max(0, len(candidate_tokens) - len(query_tokens)) * 3
        if all(
            any(candidate_token.startswith(token) for candidate_token in candidate_tokens) for token in query_tokens
        ):
            return 880.0 - max(0, len(candidate_tokens) - len(query_tokens)) * 2
        if any(candidate_token.startswith(query) for candidate_token in candidate_tokens):
            return 850.0

    if len(query) >= 3 and query in candidate:
        return 760.0 - min(candidate.index(query), 80) * 0.8
    if len(query) < 4:
        return 0.0

    if fuzz is not None:
        fuzzy_score = max(
            fuzz.WRatio(query, candidate),
            fuzz.token_set_ratio(query, candidate),
            fuzz.partial_ratio(query, candidate) * 0.92,
        )
    else:
        fuzzy_score = SequenceMatcher(None, query, candidate).ratio() * 100
    return fuzzy_score if fuzzy_score >= 68 else 0.0


def rank_destination_candidates(
    query: str,
    candidates: list[DestinationSearchCandidate],
    limit: int,
) -> list[DestinationSearchMatch]:
    normalized_query = normalize_search_text(query)
    if not normalized_query:
        return []

    best_by_key: dict[str, tuple[DestinationSearchCandidate, float]] = {}
    for candidate in candidates:
        score = _variant_score(normalized_query, normalize_search_text(candidate.name))
        if score <= 0:
            continue
        current = best_by_key.get(candidate.key)
        if current is None or score > current[1]:
            best_by_key[candidate.key] = (candidate, score)

    ranked = sorted(
        best_by_key.values(),
        key=lambda item: (
            item[1],
            1 if item[0].capital else 0,
            item[0].population or 0,
            -len(normalize_search_text(item[0].name)),
            item[0].name.casefold(),
        ),
        reverse=True,
    )
    return [DestinationSearchMatch(key=candidate.key, score=score) for candidate, score in ranked[:limit]]
