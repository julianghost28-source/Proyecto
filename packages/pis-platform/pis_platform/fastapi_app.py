from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.responses import Response

from pis_platform.logging import configure_logging
from pis_platform.middleware import (
    CorrelationIdMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    register_exception_handlers,
)
from pis_platform.telemetry import configure_telemetry

REQUESTS = Counter("http_requests_total", "HTTP requests", ["service", "method", "path", "status"])
LATENCY = Histogram("http_request_duration_seconds", "HTTP latency", ["service"])


def create_service_app(
    *,
    service_name: str,
    title: str,
    version: str = "1.0.0",
    log_level: str = "INFO",
    cors_origins: list[str] | None = None,
    enable_rate_limit: bool = False,
    otel_console: bool = False,
) -> FastAPI:
    configure_logging(service_name, log_level)
    configure_telemetry(service_name, console=otel_console)
    app = FastAPI(title=title, version=version)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(CorrelationIdMiddleware)
    if enable_rate_limit:
        app.add_middleware(RateLimitMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins or ["http://127.0.0.1:8000", "http://localhost:8000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_exception_handlers(app)

    @app.middleware("http")
    async def metrics_mw(request, call_next):
        from time import perf_counter

        start = perf_counter()
        response = await call_next(request)
        LATENCY.labels(service_name).observe(perf_counter() - start)
        path = request.url.path
        if path not in {"/metrics"}:
            REQUESTS.labels(service_name, request.method, path, str(response.status_code)).inc()
        return response

    @app.get("/health", tags=["ops"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": service_name}

    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return app
