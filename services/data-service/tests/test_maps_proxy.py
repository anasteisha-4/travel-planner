import os

os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/travel_planner")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("INTERNAL_API_SECRET", "test-secret")

import httpx  # noqa: E402
import pytest  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.routers import maps  # noqa: E402


class _FakeAsyncClient:
    last_headers: dict[str, str] | None = None
    calls: list[str] = []
    response_queue: list[httpx.Response] = []
    status_code = 200

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def get(self, url, params=None, headers=None):
        _FakeAsyncClient.calls.append(url)
        _FakeAsyncClient.last_headers = headers
        if _FakeAsyncClient.response_queue:
            return _FakeAsyncClient.response_queue.pop(0)
        return httpx.Response(
            self.status_code,
            content=b"window.ymaps3 = {};",
            headers={"content-type": "application/javascript"},
        )


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setattr(maps.settings, "YANDEX_MAPS_API_TOKEN", "test-token")
    monkeypatch.setattr(maps.httpx, "AsyncClient", _FakeAsyncClient)
    _FakeAsyncClient.status_code = 200
    _FakeAsyncClient.last_headers = None
    _FakeAsyncClient.calls = []
    _FakeAsyncClient.response_queue = []

    app = FastAPI()
    app.include_router(maps.router, prefix="/api")
    return TestClient(app)


def test_yandex_maps_proxy_forwards_public_referer(client):
    response = client.get(
        "/api/maps/yandex/v3",
        headers={
            "Referer": "https://www.triply-ai.ru/trips/1",
            "Host": "www.triply-ai.ru",
        },
    )

    assert response.status_code == 200
    assert response.headers["cache-control"] == "public, max-age=3600"
    assert _FakeAsyncClient.last_headers == {
        "Referer": "https://www.triply-ai.ru/",
        "Origin": "https://www.triply-ai.ru",
    }


def test_yandex_maps_proxy_uses_forwarded_host_when_referer_is_missing(client):
    response = client.get(
        "/api/maps/yandex/v3",
        headers={"X-Forwarded-Proto": "https", "X-Forwarded-Host": "www.triply-ai.ru"},
    )

    assert response.status_code == 200
    assert _FakeAsyncClient.last_headers == {
        "Referer": "https://www.triply-ai.ru/",
        "Origin": "https://www.triply-ai.ru",
    }


def test_yandex_maps_proxy_uses_canonical_referer_for_local_requests(client):
    response = client.get(
        "/api/maps/yandex/v3",
        headers={
            "Referer": "http://localhost/trips/1",
            "Host": "localhost",
        },
    )

    assert response.status_code == 200
    assert _FakeAsyncClient.last_headers == {
        "Referer": "https://www.triply-ai.ru/",
        "Origin": "https://www.triply-ai.ru",
    }


def test_yandex_maps_proxy_does_not_cache_upstream_403(client):
    _FakeAsyncClient.status_code = 403

    response = client.get(
        "/api/maps/yandex/v3",
        headers={
            "Referer": "https://www.triply-ai.ru/trips/1",
            "Host": "www.triply-ai.ru",
        },
    )

    assert response.status_code == 403
    assert response.headers["cache-control"] == "no-store"


def test_yandex_maps_proxy_falls_back_to_v2_when_v3_rejects_key(client):
    _FakeAsyncClient.response_queue = [
        httpx.Response(
            403,
            json={"statusCode": 403, "error": "Forbidden", "message": "Invalid api key"},
            headers={"content-type": "application/json"},
        ),
        httpx.Response(
            200,
            content=b"window.ymaps = {};",
            headers={"content-type": "application/javascript"},
        ),
    ]

    response = client.get(
        "/api/maps/yandex/v3",
        headers={
            "Referer": "https://www.triply-ai.ru/trips/1",
            "Host": "www.triply-ai.ru",
        },
    )

    assert response.status_code == 200
    assert response.headers["x-yandex-maps-fallback"] == "2.1"
    assert _FakeAsyncClient.calls == ["https://api-maps.yandex.ru/v3/", "https://api-maps.yandex.ru/2.1/"]
    assert b"\n;\n\n(function ()" in response.content
    assert b"window.ymaps3" in response.content


def test_yandex_maps_proxy_rejects_unknown_referer(client):
    response = client.get(
        "/api/maps/yandex/v3",
        headers={
            "Referer": "https://example.com/",
            "Host": "example.com",
        },
    )

    assert response.status_code == 403
