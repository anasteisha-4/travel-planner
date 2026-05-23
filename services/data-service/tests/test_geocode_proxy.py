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
    calls: list[str] = []
    geoapify_features: list[dict] = [
        {
            "geometry": {"coordinates": [37.61748, 55.75054]},
            "properties": {
                "name": "Москва",
                "formatted": "Москва, Россия",
                "result_type": "city",
            },
        }
    ]

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
        _FakeAsyncClient.calls.append(url)
        if url.endswith("/autocomplete"):
            return httpx.Response(200, json={"features": _FakeAsyncClient.geoapify_features})
        if url == geocode.YANDEX_GEOCODER_URL:
            return httpx.Response(
                200,
                json={
                    "response": {
                        "GeoObjectCollection": {
                            "featureMember": [
                                {
                                    "GeoObject": {
                                        "name": "Москва",
                                        "Point": {"pos": "37.61748 55.75054"},
                                        "metaDataProperty": {
                                            "GeocoderMetaData": {
                                                "text": "Москва, Россия",
                                                "kind": "locality",
                                            }
                                        },
                                    }
                                }
                            ]
                        }
                    }
                },
                headers={"content-type": "application/json"},
            )
        return httpx.Response(200, json={"ok": True}, headers={"content-type": "application/json"})


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setattr(geocode.settings, "YANDEX_GEOCODER_API_KEY", "geocoder-key")
    monkeypatch.setattr(geocode.settings, "YANDEX_GEOSUGGEST_API_KEY", "suggest-key")
    monkeypatch.setenv("GEOAPIFY_API_KEY", "geoapify-key")
    monkeypatch.setattr(geocode.httpx, "AsyncClient", _FakeAsyncClient)
    geocode._geocode_cache.clear()
    _FakeAsyncClient.last_url = None
    _FakeAsyncClient.last_headers = None
    _FakeAsyncClient.last_params = None
    _FakeAsyncClient.calls = []
    _FakeAsyncClient.geoapify_features = [
        {
            "geometry": {"coordinates": [37.61748, 55.75054]},
            "properties": {
                "name": "Москва",
                "formatted": "Москва, Россия",
                "result_type": "city",
            },
        }
    ]

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


def test_search_prefers_geoapify_without_spending_yandex_geocoder(client):
    response = client.get("/api/geocode/search?q=Москва&results=5&bias_lon=37.61748&bias_lat=55.75054")

    assert response.status_code == 200
    assert response.json()[0]["name"] == "Москва"
    assert _FakeAsyncClient.calls == ["https://api.geoapify.com/v1/geocode/autocomplete"]


def test_search_falls_back_to_single_yandex_geocoder_request(client):
    _FakeAsyncClient.geoapify_features = []

    response = client.get("/api/geocode/search?q=Москва&results=5&bias_lon=37.61748&bias_lat=55.75054")

    assert response.status_code == 200
    assert response.json()[0]["name"] == "Москва"
    assert _FakeAsyncClient.calls == [
        "https://api.geoapify.com/v1/geocode/autocomplete",
        "https://geocode-maps.yandex.ru/v1",
    ]


def test_search_reuses_backend_cache(client):
    for _ in range(2):
        response = client.get("/api/geocode/search?q=Москва&results=5&bias_lon=37.617481&bias_lat=55.750541")
        assert response.status_code == 200

    assert _FakeAsyncClient.calls == ["https://api.geoapify.com/v1/geocode/autocomplete"]
