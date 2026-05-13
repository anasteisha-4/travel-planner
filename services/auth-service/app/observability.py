import logging
import statistics
import time
import uuid
from collections import defaultdict, deque
from collections.abc import Callable
from threading import Lock
from typing import Any

from fastapi import FastAPI, Request
from sqlalchemy import event
from sqlalchemy.engine import Engine
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

logger = logging.getLogger("triply.observability")


class _RouteMetrics:
    def __init__(self) -> None:
        self.count = 0
        self.errors_4xx = 0
        self.errors_5xx = 0
        self.unhandled_exceptions = 0
        self.latencies_ms: deque[float] = deque(maxlen=500)


class ObservabilityStore:
    def __init__(self, service_name: str) -> None:
        self.service_name = service_name
        self.started_at = time.time()
        self._lock = Lock()
        self._routes: dict[str, _RouteMetrics] = defaultdict(_RouteMetrics)
        self._slow_db_queries: deque[dict[str, Any]] = deque(maxlen=100)

    def record_request(self, route: str, status_code: int, duration_ms: float, exception: bool = False) -> None:
        with self._lock:
            metrics = self._routes[route]
            metrics.count += 1
            metrics.latencies_ms.append(duration_ms)
            if 400 <= status_code < 500:
                metrics.errors_4xx += 1
            if status_code >= 500:
                metrics.errors_5xx += 1
            if exception:
                metrics.unhandled_exceptions += 1

    def record_slow_db_query(self, statement: str, duration_ms: float) -> None:
        with self._lock:
            self._slow_db_queries.append(
                {
                    "statement": " ".join(statement.split())[:500],
                    "duration_ms": round(duration_ms, 2),
                    "occurred_at": time.time(),
                }
            )

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            routes = {}
            for route, metrics in self._routes.items():
                latencies = list(metrics.latencies_ms)
                routes[route] = {
                    "count": metrics.count,
                    "errors_4xx": metrics.errors_4xx,
                    "errors_5xx": metrics.errors_5xx,
                    "unhandled_exceptions": metrics.unhandled_exceptions,
                    "latency_ms": {
                        "p50": _percentile(latencies, 50),
                        "p95": _percentile(latencies, 95),
                        "p99": _percentile(latencies, 99),
                    },
                }
            return {
                "service": self.service_name,
                "started_at": self.started_at,
                "uptime_seconds": round(time.time() - self.started_at, 2),
                "routes": routes,
                "slow_db_queries": list(self._slow_db_queries),
            }


def _percentile(values: list[float], percentile: int) -> float | None:
    if not values:
        return None
    if len(values) == 1:
        return round(values[0], 2)
    return round(statistics.quantiles(values, n=100, method="inclusive")[percentile - 1], 2)


store = ObservabilityStore("auth-service")


class ObservabilityMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: Callable[..., Any], service_name: str) -> None:
        super().__init__(app)
        self.service_name = service_name

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        started_at = time.perf_counter()
        route = f"{request.method} {request.url.path}"
        user_id = getattr(request.state, "user_id", None)

        try:
            response = await call_next(request)
        except Exception as exc:
            duration_ms = (time.perf_counter() - started_at) * 1000
            store.record_request(route, 500, duration_ms, exception=True)
            logger.exception(
                "request_failed",
                extra={
                    "service": self.service_name,
                    "route": request.url.path,
                    "method": request.method,
                    "status": 500,
                    "duration_ms": round(duration_ms, 2),
                    "request_id": request_id,
                    "user_id": user_id,
                    "exception_type": type(exc).__name__,
                },
            )
            raise

        duration_ms = (time.perf_counter() - started_at) * 1000
        response.headers["X-Request-ID"] = request_id
        store.record_request(route, response.status_code, duration_ms)
        log_level = (
            logging.ERROR
            if response.status_code >= 500
            else logging.WARNING
            if response.status_code >= 400
            else logging.INFO
        )
        logger.log(
            log_level,
            "request_completed",
            extra={
                "service": self.service_name,
                "route": request.url.path,
                "method": request.method,
                "status": response.status_code,
                "duration_ms": round(duration_ms, 2),
                "request_id": request_id,
                "user_id": user_id,
            },
        )
        return response


def add_observability(app: FastAPI, service_name: str) -> None:
    app.add_middleware(ObservabilityMiddleware, service_name=service_name)


def install_sqlalchemy_observability(engine: Engine, service_name: str, slow_query_ms: float = 500.0) -> None:
    @event.listens_for(engine, "before_cursor_execute")
    def before_cursor_execute(
        conn: Any, cursor: Any, statement: str, parameters: Any, context: Any, executemany: bool
    ) -> None:
        context._triply_query_started_at = time.perf_counter()

    @event.listens_for(engine, "after_cursor_execute")
    def after_cursor_execute(
        conn: Any, cursor: Any, statement: str, parameters: Any, context: Any, executemany: bool
    ) -> None:
        started_at = getattr(context, "_triply_query_started_at", None)
        if started_at is None:
            return
        duration_ms = (time.perf_counter() - started_at) * 1000
        if duration_ms < slow_query_ms:
            return
        store.record_slow_db_query(statement, duration_ms)
        logger.warning(
            "slow_db_query",
            extra={
                "service": service_name,
                "duration_ms": round(duration_ms, 2),
                "statement": " ".join(statement.split())[:500],
            },
        )
