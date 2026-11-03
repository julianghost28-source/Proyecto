from __future__ import annotations

import uuid
from contextvars import ContextVar

CORRELATION_HEADER = "X-Correlation-ID"
TRACE_HEADER = "X-Trace-ID"

_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)
_trace_id: ContextVar[str | None] = ContextVar("trace_id", default=None)


def new_id() -> str:
    return str(uuid.uuid4())


def get_correlation_id() -> str | None:
    return _correlation_id.get()


def set_correlation_id(value: str) -> None:
    _correlation_id.set(value)


def get_trace_id() -> str | None:
    return _trace_id.get()


def set_trace_id(value: str) -> None:
    _trace_id.set(value)


def ensure_correlation_id(incoming: str | None) -> str:
    value = (incoming or "").strip() or new_id()
    set_correlation_id(value)
    if not get_trace_id():
        set_trace_id(new_id())
    return value

