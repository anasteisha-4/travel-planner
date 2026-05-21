import os

import httpx
from fastapi import APIRouter, HTTPException, Query, Response

from app.config import settings

router = APIRouter(prefix="/maps", tags=["maps"])

YANDEX_MAPS_V3_URL = "https://api-maps.yandex.ru/v3/"


def _env_value(name: str, legacy_name: str) -> str:
    value = getattr(settings, name, "") or os.getenv(name, "")
    return value or os.getenv(legacy_name, "")


@router.get("/yandex/v3")
async def proxy_yandex_maps_v3(lang: str = Query("ru_RU", max_length=16)) -> Response:
    api_key = _env_value("YANDEX_MAPS_API_TOKEN", "VITE_YANDEX_MAPS_API_TOKEN")
    if not api_key:
        raise HTTPException(status_code=503, detail="Yandex Maps provider is not configured")

    async with httpx.AsyncClient(timeout=10.0) as client:
        upstream = await client.get(YANDEX_MAPS_V3_URL, params={"apikey": api_key, "lang": lang})

    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        media_type=upstream.headers.get("content-type", "application/javascript"),
        headers={"Cache-Control": "public, max-age=3600"},
    )
