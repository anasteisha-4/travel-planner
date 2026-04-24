import uuid
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.model_registry import ModelRegistry


def _make_model(name: str = "ranker", version: str = "v1", is_active: bool = True) -> ModelRegistry:
    return ModelRegistry(
        id=uuid.uuid4(),
        name=name,
        version=version,
        model_type="lightgbm",
        is_active=is_active,
        metrics={"ndcg": 0.87},
        trained_at=datetime(2025, 1, 1, tzinfo=UTC),
    )


def test_get_model_versions_empty(client: TestClient):
    resp = client.get("/api/v1/models/versions")
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_model_versions_returns_all(client: TestClient, db: Session):
    db.add(_make_model("ranker", "v1"))
    db.add(_make_model("budget", "v2", is_active=False))
    db.commit()

    resp = client.get("/api/v1/models/versions")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    names = {d["name"] for d in data}
    assert names == {"ranker", "budget"}


def test_get_model_versions_fields(client: TestClient, db: Session):
    db.add(_make_model("ranker", "v1"))
    db.commit()

    resp = client.get("/api/v1/models/versions")
    item = resp.json()[0]
    assert "id" in item
    assert item["name"] == "ranker"
    assert item["version"] == "v1"
    assert item["model_type"] == "lightgbm"
    assert item["is_active"] is True
    assert item["metrics"] == {"ndcg": 0.87}
    assert item["trained_at"] is not None
    assert item["created_at"] is not None


def test_get_model_versions_sorted_by_created_desc(client: TestClient, db: Session):

    m1 = _make_model("ranker", "v1")
    m2 = _make_model("ranker", "v2")
    db.add(m1)
    db.flush()
    # Force m2 to have a later created_at by setting it explicitly
    from sqlalchemy import text
    db.add(m2)
    db.commit()

    # Update m2 created_at to be clearly newer
    db.execute(
        text("UPDATE model_registry SET created_at = NOW() + interval '1 second' WHERE version = 'v2'")
    )
    db.commit()

    resp = client.get("/api/v1/models/versions")
    data = resp.json()
    assert len(data) == 2
    assert data[0]["version"] == "v2"
