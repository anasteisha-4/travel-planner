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
        self._cache: dict[str, dict[str, int]] = defaultdict(lambda: {"hit": 0, "miss": 0, "set": 0, "error": 0})
        self._external: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"calls": 0, "errors": 0, "no_coverage": 0, "latencies_ms": deque(maxlen=500)}
        )
        self._llm_quality: dict[str, Any] = {
            "requests": 0,
            "errors": 0,
            "timeouts": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "latencies_ms": deque(maxlen=500),
            "statuses": defaultdict(int),
            "issue_codes": defaultdict(int),
            "candidate_poi": defaultdict(int),
            "price_evidence_found": 0,
            "external_routes_generated": 0,
        }

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

    def record_cache(self, cache_name: str, result: str) -> None:
        with self._lock:
            if result not in {"hit", "miss", "set", "error"}:
                return
            self._cache[cache_name][result] += 1

    def record_external_api(self, provider: str, duration_ms: float, *, ok: bool, no_coverage: bool = False) -> None:
        with self._lock:
            metrics = self._external[provider]
            metrics["calls"] += 1
            metrics["latencies_ms"].append(duration_ms)
            if not ok:
                metrics["errors"] += 1
            if no_coverage:
                metrics["no_coverage"] += 1

    def record_llm_review(
        self,
        *,
        status: str,
        latency_ms: int | None,
        cache_hit: bool,
        error_code: str | None,
        issue_codes: list[str] | None = None,
    ) -> None:
        with self._lock:
            self._llm_quality["requests"] += 1
            self._llm_quality["statuses"][status] += 1
            if latency_ms is not None:
                self._llm_quality["latencies_ms"].append(latency_ms)
            if cache_hit:
                self._llm_quality["cache_hits"] += 1
            else:
                self._llm_quality["cache_misses"] += 1
            if error_code:
                self._llm_quality["errors"] += 1
                if error_code == "provider_timeout":
                    self._llm_quality["timeouts"] += 1
            for code in issue_codes or []:
                self._llm_quality["issue_codes"][code] += 1

    def record_llm_candidate_poi(self, status: str) -> None:
        with self._lock:
            self._llm_quality["candidate_poi"][status] += 1

    def record_llm_price_evidence(self) -> None:
        with self._lock:
            self._llm_quality["price_evidence_found"] += 1

    def record_llm_external_route(self) -> None:
        with self._lock:
            self._llm_quality["external_routes_generated"] += 1

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
            llm_latencies = list(self._llm_quality["latencies_ms"])
            llm_requests = int(self._llm_quality["requests"])
            llm_cache_hits = int(self._llm_quality["cache_hits"])
            return {
                "service": self.service_name,
                "started_at": self.started_at,
                "uptime_seconds": round(time.time() - self.started_at, 2),
                "routes": routes,
                "slow_db_queries": list(self._slow_db_queries),
                "cache": {name: dict(values) for name, values in self._cache.items()},
                "external_apis": {
                    name: {
                        "calls": values["calls"],
                        "errors": values["errors"],
                        "no_coverage": values["no_coverage"],
                        "latency_ms": {
                            "p50": _percentile(list(values["latencies_ms"]), 50),
                            "p95": _percentile(list(values["latencies_ms"]), 95),
                            "p99": _percentile(list(values["latencies_ms"]), 99),
                        },
                    }
                    for name, values in self._external.items()
                },
                "llm_quality": {
                    "requests": llm_requests,
                    "errors": self._llm_quality["errors"],
                    "timeouts": self._llm_quality["timeouts"],
                    "cache_hits": llm_cache_hits,
                    "cache_misses": self._llm_quality["cache_misses"],
                    "cache_hit_rate": round(llm_cache_hits / llm_requests, 4) if llm_requests else 0,
                    "latency_ms": {
                        "p50": _percentile(llm_latencies, 50),
                        "p95": _percentile(llm_latencies, 95),
                        "p99": _percentile(llm_latencies, 99),
                    },
                    "statuses": dict(self._llm_quality["statuses"]),
                    "issue_codes": dict(self._llm_quality["issue_codes"]),
                    "candidate_poi": dict(self._llm_quality["candidate_poi"]),
                    "price_evidence_found": self._llm_quality["price_evidence_found"],
                    "external_routes_generated": self._llm_quality["external_routes_generated"],
                },
            }


def record_cache(cache_name: str, result: str) -> None:
    store.record_cache(cache_name, result)


def record_external_api(provider: str, duration_ms: float, *, ok: bool, no_coverage: bool = False) -> None:
    store.record_external_api(provider, duration_ms, ok=ok, no_coverage=no_coverage)


def record_llm_review(
    *,
    status: str,
    latency_ms: int | None,
    cache_hit: bool,
    error_code: str | None,
    issue_codes: list[str] | None = None,
) -> None:
    store.record_llm_review(
        status=status,
        latency_ms=latency_ms,
        cache_hit=cache_hit,
        error_code=error_code,
        issue_codes=issue_codes,
    )


def record_llm_candidate_poi(status: str) -> None:
    store.record_llm_candidate_poi(status)


def record_llm_price_evidence() -> None:
    store.record_llm_price_evidence()


def record_llm_external_route() -> None:
    store.record_llm_external_route()


def _percentile(values: list[float], percentile: int) -> float | None:
    if not values:
        return None
    if len(values) == 1:
        return round(values[0], 2)
    return round(statistics.quantiles(values, n=100, method="inclusive")[percentile - 1], 2)


store = ObservabilityStore("ml-service")


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
