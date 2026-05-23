import os

os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/travel_planner")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("INTERNAL_API_SECRET", "test-secret")

import httpx  # noqa: E402
import pytest  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.routers import geocode  # noqa: E402


class _FakeAsyncClient:
    last_url: str | None = None
    last_headers: dict[str, str] | None = None
    last_params: dict[str, str] | None = None

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def get(self, url, params=None, headers=None):
        _FakeAsyncClient.last_url = url
        _FakeAsyncClient.last_headers = headers
        _FakeAsyncClient.last_params = params
        return httpx.Response(200, json={"ok": True}, headers={"content-type": "application/json"})


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setattr(geocode.settings, "YANDEX_GEOCODER_API_KEY", "geocoder-key")
    monkeypatch.setattr(geocode.settings, "YANDEX_GEOSUGGEST_API_KEY", "suggest-key")
    monkeypatch.setattr(geocode.httpx, "AsyncClient", _FakeAsyncClient)
    _FakeAsyncClient.last_url = None
    _FakeAsyncClient.last_headers = None
    _FakeAsyncClient.last_params = None

    app = FastAPI()
    app.include_router(geocode.router, prefix="/api")
    return TestClient(app)


def test_yandex_geocoder_proxy_uses_v1_endpoint_and_referer(client):
    response = client.get("/api/geocode/yandex/1.x?format=json&geocode=Москва")

    assert response.status_code == 200
    assert _FakeAsyncClient.last_url == "https://geocode-maps.yandex.ru/v1"
    assert _FakeAsyncClient.last_params["apikey"] == "geocoder-key"
    assert _FakeAsyncClient.last_headers == {
        "Referer": "https://www.triply-ai.ru/",
        "Origin": "https://www.triply-ai.ru",
    }


def test_yandex_geosuggest_proxy_forwards_referer(client):
    response = client.get("/api/geocode/yandex/suggest?text=Москва")

    assert response.status_code == 200
    assert _FakeAsyncClient.last_params["apikey"] == "suggest-key"
    assert _FakeAsyncClient.last_headers == {
        "Referer": "https://www.triply-ai.ru/",
        "Origin": "https://www.triply-ai.ru",
    }
