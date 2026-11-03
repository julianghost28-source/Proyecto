from __future__ import annotations

import logging
import time
from collections import defaultdict, deque

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from opentelemetry import trace
from starlette.middleware.base import BaseHTTPMiddleware

from pis_platform.correlation import (
    CORRELATION_HEADER,
    TRACE_HEADER,
    ensure_correlation_id,
    get_correlation_id,
    get_trace_id,
)
from pis_platform.errors import AppError, error_body

LOGGER = logging.getLogger(__name__)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        cid = ensure_correlation_id(request.headers.get(CORRELATION_HEADER))
        incoming_trace = request.headers.get(TRACE_HEADER)
        if incoming_trace:
            from pis_platform.correlation import set_trace_id

            set_trace_id(incoming_trace)
        response = await call_next(request)
        response.headers[CORRELATION_HEADER] = cid
        response.headers[TRACE_HEADER] = get_trace_id() or cid
        span = trace.get_current_span()
        if span.get_span_context().is_valid:
            response.headers["X-Trace-Otel"] = format(span.get_span_context().trace_id, "032x")
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limit: int = 120, window_seconds: int = 60) -> None:
        super().__init__(app)
        self.limit = limit
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        if request.url.path in {"/health", "/ready", "/metrics"}:
            return await call_next(request)
        ip = request.client.host if request.client else "unknown"
        now = time.time()
        bucket = self._hits[ip]
        while bucket and now - bucket[0] > self.window_seconds:
            bucket.popleft()
        if len(bucket) >= self.limit:
            return JSONResponse(
                status_code=429,
                content=error_body("RATE_LIMITED", "Too many requests", get_correlation_id()),
            )
        bucket.append(now)
        return await call_next(request)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        LOGGER.warning("app_error", extra={"code": exc.code, "path": request.url.path})
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(exc.code, exc.message, get_correlation_id()),
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
        LOGGER.exception("unhandled_error", extra={"path": request.url.path})
        return JSONResponse(
            status_code=500,
            content=error_body("INTERNAL_ERROR", "Unexpected server error", get_correlation_id()),
        )
