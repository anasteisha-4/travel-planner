import uuid

from app.services.travel_advisory import filter_destinations_by_travel_advisory


def _dest(name: str, country_code: str) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "name": name,
        "country_code": country_code,
    }


def test_travel_advisory_blocks_uae_for_ru_citizenship():
    dubai = _dest("Dubai", "AE")
    istanbul = _dest("Istanbul", "TR")

    allowed, blocked = filter_destinations_by_travel_advisory(
        destinations=[dubai, istanbul],
        citizenship_code="RU",
    )

    assert [item["name"] for item in allowed] == ["Istanbul"]
    assert blocked == [
        {
            "destination_id": dubai["id"],
            "name": "Dubai",
            "country_code": "AE",
            "reason": "country_travel_advisory",
        }
    ]


def test_travel_advisory_keeps_allowed_middle_east_destinations():
    destinations = [
        _dest("Doha", "QA"),
        _dest("Aqaba", "JO"),
        _dest("Antalya", "TR"),
    ]

    allowed, blocked = filter_destinations_by_travel_advisory(
        destinations=destinations,
        citizenship_code="RU",
    )

    assert [item["name"] for item in allowed] == ["Aqaba", "Antalya"]
    assert [item["name"] for item in blocked] == ["Doha"]


def test_travel_advisory_blocks_domestic_security_advisory_for_ru():
    destinations = [
        _dest("Moscow", "RU"),
        _dest("Rostov-on-Don", "RU"),
    ]

    allowed, blocked = filter_destinations_by_travel_advisory(
        destinations=destinations,
        citizenship_code="RU",
    )

    assert [item["name"] for item in allowed] == ["Moscow"]
    assert blocked[0]["reason"] == "domestic_security_advisory"
