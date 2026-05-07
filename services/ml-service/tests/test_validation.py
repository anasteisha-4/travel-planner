import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

DEST_ID = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")


@pytest.fixture(autouse=True)
def seed_tables(db: Session):
    for tbl in ["visa_rules", "destination_seasonality", "destination_safety", "destination_costs"]:
        db.execute(
            text(f"""
            CREATE TABLE IF NOT EXISTS {tbl} (
                destination_id UUID,
                {"citizenship_code TEXT," if tbl == "visa_rules" else ""}
                {"visa_type TEXT, visa_score NUMERIC, max_stay_days INTEGER," if tbl == "visa_rules" else ""}
                {"month INTEGER, season_score NUMERIC, avg_temp_c NUMERIC, avg_precipitation_mm NUMERIC, avg_humidity_pct NUMERIC," if tbl == "destination_seasonality" else ""}
                {"safety_score NUMERIC," if tbl == "destination_safety" else ""}
                {"avg_daily_cost_usd NUMERIC," if tbl == "destination_costs" else ""}
                PRIMARY KEY (destination_id {"," + "citizenship_code" if tbl == "visa_rules" else ", month" if tbl == "destination_seasonality" else ""})
            )
        """)
        )
    db.commit()

    # visa: RU visa_free
    db.execute(
        text(
            "INSERT INTO visa_rules (destination_id, citizenship_code, visa_type, visa_score, max_stay_days) "
            "VALUES (:did, 'RU', 'visa_free', 1.0, 90) ON CONFLICT DO NOTHING"
        ),
        {"did": str(DEST_ID)},
    )

    # seasonality: month 7 good, month 8 terrible (monsoon)
    db.execute(
        text(
            "INSERT INTO destination_seasonality "
            "(destination_id, month, season_score, avg_temp_c, avg_precipitation_mm, avg_humidity_pct) "
            "VALUES (:did, 7, 0.85, 24.0, 30.0, 60.0) ON CONFLICT DO NOTHING"
        ),
        {"did": str(DEST_ID)},
    )
    db.execute(
        text(
            "INSERT INTO destination_seasonality "
            "(destination_id, month, season_score, avg_temp_c, avg_precipitation_mm, avg_humidity_pct) "
            "VALUES (:did, 8, 0.25, 38.0, 280.0, 90.0) ON CONFLICT DO NOTHING"
        ),
        {"did": str(DEST_ID)},
    )

    # safety: safe
    db.execute(
        text("INSERT INTO destination_safety (destination_id, safety_score) VALUES (:did, 0.8) ON CONFLICT DO NOTHING"),
        {"did": str(DEST_ID)},
    )

    # costs
    db.execute(
        text(
            "INSERT INTO destination_costs (destination_id, avg_daily_cost_usd) "
            "VALUES (:did, 100.0) ON CONFLICT DO NOTHING"
        ),
        {"did": str(DEST_ID)},
    )

    db.commit()
    yield

    for tbl in ["visa_rules", "destination_seasonality", "destination_safety", "destination_costs"]:
        db.execute(text(f"DELETE FROM {tbl} WHERE destination_id = :did"), {"did": str(DEST_ID)})
    db.commit()


def _payload(**overrides) -> dict:
    base = {
        "destination_id": str(DEST_ID),
        "citizenship_code": "RU",
        "travel_month": 7,
    }
    base.update(overrides)
    return base


def test_validate_no_warnings_good_conditions(client: TestClient):
    resp = client.post("/api/v1/validate", json=_payload())
    assert resp.status_code == 200
    data = resp.json()
    assert data["destination_id"] == str(DEST_ID)
    assert data["warnings"] == []
    assert data["info"]["visa_type"] == "visa_free"
    assert data["info"]["visa_score"] == 1.0
    assert data["info"]["season_score"] == pytest.approx(0.85)
    assert data["info"]["safety_score"] == pytest.approx(0.8)


def test_validate_poor_season_warning(client: TestClient):
    resp = client.post("/api/v1/validate", json=_payload(travel_month=8))
    assert resp.status_code == 200
    warnings = resp.json()["warnings"]
    types = [w["type"] for w in warnings]
    assert "season" in types
    season_warning = next(w for w in warnings if w["type"] == "season")
    assert season_warning["severity"] == "medium"


def test_validate_visa_required_warning(client: TestClient, db: Session):
    # insert visa_required row for US citizen
    db.execute(
        text(
            "INSERT INTO visa_rules (destination_id, citizenship_code, visa_type, visa_score, max_stay_days) "
            "VALUES (:did, 'US', 'visa_required', 0.2, NULL) ON CONFLICT DO NOTHING"
        ),
        {"did": str(DEST_ID)},
    )
    db.commit()

    resp = client.post("/api/v1/validate", json=_payload(citizenship_code="US"))
    assert resp.status_code == 200
    warnings = resp.json()["warnings"]
    visa_warns = [w for w in warnings if w["type"] == "visa"]
    assert len(visa_warns) == 1
    assert visa_warns[0]["severity"] == "medium"


def test_validate_no_admission_high_severity(client: TestClient, db: Session):
    db.execute(
        text(
            "INSERT INTO visa_rules (destination_id, citizenship_code, visa_type, visa_score, max_stay_days) "
            "VALUES (:did, 'KP', 'no_admission', 0.0, NULL) ON CONFLICT DO NOTHING"
        ),
        {"did": str(DEST_ID)},
    )
    db.commit()

    resp = client.post("/api/v1/validate", json=_payload(citizenship_code="KP"))
    assert resp.status_code == 200
    warnings = resp.json()["warnings"]
    visa_warns = [w for w in warnings if w["type"] == "visa"]
    assert visa_warns[0]["severity"] == "high"


def test_validate_unknown_visa_low_warning(client: TestClient):
    unknown_dest = uuid.uuid4()
    # only seed safety for this dest to avoid missing table errors
    next(
        iter(
            [
                None,
            ]
        )
    )
    resp = client.post(
        "/api/v1/validate",
        json={
            "destination_id": str(unknown_dest),
            "citizenship_code": "RU",
            "travel_month": 7,
        },
    )
    assert resp.status_code == 200
    warnings = resp.json()["warnings"]
    visa_warn = next((w for w in warnings if w["type"] == "visa"), None)
    assert visa_warn is not None
    assert visa_warn["severity"] == "low"


def test_validate_budget_tight_warning(client: TestClient):
    resp = client.post("/api/v1/validate", json={**_payload(), "budget_per_day_usd": 50.0})
    assert resp.status_code == 200
    warnings = resp.json()["warnings"]
    budget_warns = [w for w in warnings if w["type"] == "budget"]
    assert len(budget_warns) == 1
    assert budget_warns[0]["severity"] == "medium"


def test_validate_budget_warning_uses_display_currency(client: TestClient):
    resp = client.post(
        "/api/v1/validate",
        json={**_payload(), "budget_per_day_usd": 50.0, "display_currency": "RUB"},
    )
    assert resp.status_code == 200
    data = resp.json()
    budget_warn = next(w for w in data["warnings"] if w["type"] == "budget")
    assert "$" not in budget_warn["message"]
    assert "RUB/day" in budget_warn["message"]
    assert data["info"]["avg_daily_cost"] == 9000.0
    assert data["info"]["budget_per_day"] == 4500.0
    assert data["info"]["display_currency"] == "RUB"


def test_validate_budget_ok_no_warning(client: TestClient):
    resp = client.post("/api/v1/validate", json={**_payload(), "budget_per_day_usd": 200.0})
    assert resp.status_code == 200
    budget_warns = [w for w in resp.json()["warnings"] if w["type"] == "budget"]
    assert budget_warns == []


def test_validate_returns_destination_id(client: TestClient):
    resp = client.post("/api/v1/validate", json=_payload())
    assert resp.json()["destination_id"] == str(DEST_ID)
