from app.services.destination_search import (
    DestinationSearchCandidate,
    destination_search_aliases,
    normalize_search_text,
    rank_destination_candidates,
)


def test_normalize_search_text_folds_case_punctuation_and_yo():
    assert normalize_search_text("  Санкт-Петербург, Ёлки! ") == "санкт петербург елки"


def test_rank_prefers_exact_russian_name_over_fuzzy_match():
    candidates = [
        DestinationSearchCandidate(key="moscow", name="Москва", population=12_000_000, capital=True),
        DestinationSearchCandidate(key="muscat", name="Маскат", population=1_700_000, capital=True),
        DestinationSearchCandidate(key="mostar", name="Мостар", population=100_000),
    ]

    result = rank_destination_candidates("москва", candidates, limit=3)

    assert [match.key for match in result] == ["moscow"]


def test_rank_prefers_prefix_before_contains_and_fuzzy():
    candidates = [
        DestinationSearchCandidate(key="new-york", name="New York", population=8_000_000),
        DestinationSearchCandidate(key="york", name="York", population=150_000),
        DestinationSearchCandidate(key="mallorca", name="Palma de Mallorca", population=400_000),
    ]

    result = rank_destination_candidates("yor", candidates, limit=3)

    assert [match.key for match in result[:2]] == ["york", "new-york"]


def test_rank_matches_multi_word_prefixes():
    candidates = [
        DestinationSearchCandidate(key="spb", name="Санкт-Петербург", population=5_000_000),
        DestinationSearchCandidate(key="santiago", name="Сантьяго", population=6_000_000),
    ]

    result = rank_destination_candidates("сан пе", candidates, limit=3)

    assert [match.key for match in result] == ["spb"]


def test_short_query_uses_prefix_logic_without_noisy_fuzzy_results():
    candidates = [
        DestinationSearchCandidate(key="rome", name="Rome", population=2_800_000, capital=True),
        DestinationSearchCandidate(key="rotterdam", name="Rotterdam", population=600_000),
        DestinationSearchCandidate(key="bordeaux", name="Bordeaux", population=260_000),
    ]

    result = rank_destination_candidates("ro", candidates, limit=10)

    assert [match.key for match in result] == ["rome", "rotterdam"]


def test_three_letter_query_does_not_include_fuzzy_only_noise():
    candidates = [
        DestinationSearchCandidate(key="moscow", name="Москва", population=12_000_000, capital=True),
        DestinationSearchCandidate(key="mostar", name="Мостар", population=100_000),
        DestinationSearchCandidate(key="oslo", name="Осло", population=700_000, capital=True),
    ]

    result = rank_destination_candidates("мос", candidates, limit=10)

    assert [match.key for match in result] == ["moscow", "mostar"]


def test_destination_search_aliases_include_common_st_petersburg_inputs():
    aliases = destination_search_aliases("St. Petersburg", "Санкт-Петербург")

    assert "Сан Петербург" in aliases
    assert "Питер" in aliases
    assert "СПб" in aliases
