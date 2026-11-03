from __future__ import annotations

import asyncio
import logging
import random
import time
from collections.abc import Awaitable, Callable
from enum import Enum
from typing import TypeVar

T = TypeVar("T")
LOGGER = logging.getLogger(__name__)


class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitOpenError(Exception):
    def __init__(self, name: str) -> None:
        super().__init__(f"Circuit breaker '{name}' is OPEN")
        self.name = name


class CircuitBreaker:
    """In-process circuit breaker: CLOSED → OPEN → HALF_OPEN → CLOSED."""

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_seconds: float = 30.0,
        half_open_success_threshold: int = 1,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_seconds = recovery_seconds
        self.half_open_success_threshold = half_open_success_threshold
        self._state = CircuitState.CLOSED
        self._failures = 0
        self._opened_at = 0.0
        self._half_open_successes = 0

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN and time.monotonic() - self._opened_at >= self.recovery_seconds:
            self._state = CircuitState.HALF_OPEN
            self._half_open_successes = 0
            LOGGER.info("circuit_half_open", extra={"circuit": self.name})
        return self._state

    async def call(self, fn: Callable[[], Awaitable[T]]) -> T:
        state = self.state
        if state == CircuitState.OPEN:
            raise CircuitOpenError(self.name)
        try:
            result = await fn()
        except Exception:
            self._on_failure()
            raise
        self._on_success()
        return result

    def _on_success(self) -> None:
        if self._state == CircuitState.HALF_OPEN:
            self._half_open_successes += 1
            if self._half_open_successes >= self.half_open_success_threshold:
                self._state = CircuitState.CLOSED
                self._failures = 0
                LOGGER.info("circuit_closed", extra={"circuit": self.name})
            return
        self._failures = 0

    def _on_failure(self) -> None:
        self._failures += 1
        if self._state == CircuitState.HALF_OPEN or self._failures >= self.failure_threshold:
            self._state = CircuitState.OPEN
            self._opened_at = time.monotonic()
            LOGGER.warning("circuit_open", extra={"circuit": self.name, "failures": self._failures})


async def retry_with_backoff(
    fn: Callable[[], Awaitable[T]],
    *,
    retries: int = 3,
    base_delay: float = 0.2,
    max_delay: float = 2.0,
    retry_on: tuple[type[BaseException], ...] = (Exception,),
) -> T:
    last_error: BaseException | None = None
    attempts = retries + 1
    for attempt in range(attempts):
        try:
            return await fn()
        except retry_on as exc:
            last_error = exc
            if attempt >= retries:
                break
            exp = min(max_delay, base_delay * (2**attempt))
            delay = exp * (0.5 + random.random())
            LOGGER.info(
                "retrying_call",
                extra={"attempt": attempt + 1, "delay": round(delay, 3), "error": str(exc)},
            )
            await asyncio.sleep(delay)
    assert last_error is not None
    raise last_error

