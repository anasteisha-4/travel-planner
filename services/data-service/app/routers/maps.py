import os
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, HTTPException, Query, Request, Response

from app.config import settings

router = APIRouter(prefix="/maps", tags=["maps"])

YANDEX_MAPS_V3_URL = "https://api-maps.yandex.ru/v3/"
YANDEX_MAPS_V2_URL = "https://api-maps.yandex.ru/2.1/"
CANONICAL_MAP_REFERER = "https://www.triply-ai.ru/"
PUBLIC_MAP_REFERER_HOSTS = {"triply-ai.ru", "www.triply-ai.ru"}
LOCAL_MAP_REFERER_HOSTS = {"localhost", "127.0.0.1", "::1"}


def _env_value(name: str, legacy_name: str) -> str:
    value = getattr(settings, name, "") or os.getenv(name, "")
    return value or os.getenv(legacy_name, "")


@router.get("/yandex/v3")
async def proxy_yandex_maps_v3(request: Request, lang: str = Query("ru_RU", max_length=16)) -> Response:
    api_key = _env_value("YANDEX_MAPS_API_TOKEN", "VITE_YANDEX_MAPS_API_TOKEN")
    if not api_key:
        raise HTTPException(status_code=503, detail="Yandex Maps provider is not configured")

    referer = _resolve_yandex_referer(request)
    if not referer:
        raise HTTPException(status_code=403, detail="Unsupported map request origin")

    headers = {
        "Referer": referer,
        "Origin": referer.rstrip("/"),
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        upstream = await client.get(YANDEX_MAPS_V3_URL, params={"apikey": api_key, "lang": lang}, headers=headers)
        if _is_invalid_key_response(upstream):
            fallback = await client.get(YANDEX_MAPS_V2_URL, params={"apikey": api_key, "lang": lang}, headers=headers)
            if fallback.is_success:
                return Response(
                    content=fallback.content + b"\n;\n" + _ymaps2_to_ymaps3_compat().encode("utf-8"),
                    status_code=200,
                    media_type=fallback.headers.get("content-type", "application/javascript"),
                    headers={"Cache-Control": "public, max-age=3600", "X-Yandex-Maps-Fallback": "2.1"},
                )

    cache_control = "public, max-age=3600" if upstream.is_success else "no-store"

    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        media_type=upstream.headers.get("content-type", "application/javascript"),
        headers={"Cache-Control": cache_control},
    )


def _resolve_yandex_referer(request: Request) -> str | None:
    for header_name in ("referer", "origin"):
        referer = _normalize_referer(request.headers.get(header_name))
        if referer:
            return referer

    proto = request.headers.get("x-forwarded-proto") or request.url.scheme
    host = request.headers.get("x-forwarded-host") or request.headers.get("host")
    if not host:
        return None
    return _normalize_referer(f"{proto}://{host}/")


def _normalize_referer(value: str | None) -> str | None:
    if not value:
        return None
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return None
    if parsed.hostname in LOCAL_MAP_REFERER_HOSTS:
        return CANONICAL_MAP_REFERER
    if parsed.hostname in PUBLIC_MAP_REFERER_HOSTS:
        return f"https://{parsed.hostname}/"
    return None


def _is_invalid_key_response(response: httpx.Response) -> bool:
    if response.status_code != 403:
        return False
    try:
        message = str(response.json().get("message", ""))
    except ValueError:
        return False
    return "invalid api key" in message.lower() or "invalid apikey" in message.lower()


def _ymaps2_to_ymaps3_compat() -> str:
    return r"""
(function () {
  if (window.ymaps3 || !window.ymaps) return;

  const toV2 = (coordinates) => [coordinates[1], coordinates[0]];
  const fromV2 = (coordinates) => [coordinates[1], coordinates[0]];

  class NoopLayer {
    _apply() {}
    _remove() {}
  }

  class YMapCompat {
    constructor(container, props) {
      this.children = new Set();
      this.map = new ymaps.Map(
        container,
        { center: [0, 0], zoom: 10, controls: [] },
        { suppressMapOpenBlock: true }
      );
      this.update(props);
    }

    addChild(child) {
      this.children.add(child);
      if (child && typeof child._apply === 'function') child._apply(this.map);
    }

    removeChild(child) {
      if (child && typeof child._remove === 'function') child._remove(this.map);
      this.children.delete(child);
    }

    update(props) {
      if (!props || !props.location) return;
      if (props.location.center) {
        this.map.setCenter(toV2(props.location.center), props.location.zoom || this.map.getZoom());
        return;
      }
      if (props.location.bounds) {
        this.map.setBounds(props.location.bounds.map(toV2), {
          checkZoomRange: true,
          zoomMargin: props.margin || 24,
        });
      }
    }

    destroy() {
      this.map.destroy();
    }
  }

  class YMapMarkerCompat {
    constructor(props, element) {
      this.props = props;
      this.element = element;
      this.geoObject = null;
    }

    _apply(map) {
      const layout = ymaps.templateLayoutFactory.createClass(this.element ? this.element.outerHTML : '');
      this.geoObject = new ymaps.Placemark(
        toV2(this.props.coordinates),
        {},
        { iconLayout: layout, iconShape: { type: 'Rectangle', coordinates: [[-24, -24], [24, 24]] } }
      );
      map.geoObjects.add(this.geoObject);
    }

    _remove(map) {
      if (this.geoObject) map.geoObjects.remove(this.geoObject);
      this.geoObject = null;
    }
  }

  class YMapFeatureCompat {
    constructor(props) {
      this.props = props;
      this.geoObject = null;
    }

    _apply(map) {
      const stroke = (this.props.style && this.props.style.stroke && this.props.style.stroke[0]) || {};
      this.geoObject = new ymaps.Polyline(
        this.props.geometry.coordinates.map(toV2),
        {},
        {
          strokeColor: stroke.color || '#2563eb',
          strokeWidth: stroke.width || 4,
          strokeOpacity: stroke.opacity || 0.9,
        }
      );
      map.geoObjects.add(this.geoObject);
    }

    _remove(map) {
      if (this.geoObject) map.geoObjects.remove(this.geoObject);
      this.geoObject = null;
    }
  }

  class YMapListenerCompat {
    constructor(props) {
      this.props = props;
      this.handler = null;
    }

    _apply(map) {
      if (!this.props.onClick) return;
      this.handler = (event) => {
        this.props.onClick(null, { coordinates: fromV2(event.get('coords')) });
      };
      map.events.add('click', this.handler);
    }

    _remove(map) {
      if (this.handler) map.events.remove('click', this.handler);
      this.handler = null;
    }
  }

  window.ymaps3 = {
    ready: new Promise((resolve) => ymaps.ready(resolve)),
    YMap: YMapCompat,
    YMapDefaultSchemeLayer: NoopLayer,
    YMapDefaultFeaturesLayer: NoopLayer,
    YMapMarker: YMapMarkerCompat,
    YMapFeature: YMapFeatureCompat,
    YMapListener: YMapListenerCompat,
  };
})();
"""
