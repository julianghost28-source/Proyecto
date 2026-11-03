from __future__ import annotations

import logging
from typing import Any, Protocol

from app.domain.airport import Airport
from app.domain.ports import AirportProvider, AirportRepository
from pis_platform.errors import DependencyUnavailableError, NotFoundError
from pis_platform.resilience import CircuitOpenError
from pis_platform.telemetry import tracer

LOGGER = logging.getLogger(__name__)
TRACER = tracer("airport-service")

LIST_CACHE_KEY = "airports:all"
ITEM_CACHE_KEY = "airports:{id}"


class CachePort(Protocol):
    def get(self, key: str) -> Any | None: ...

    def set(self, key: str, value: Any, ttl_seconds: int) -> None: ...


class ListAirportsUseCase:
    def __init__(
        self,
        provider: AirportProvider,
        repository: AirportRepository,
        cache: CachePort,
        ttl: int,
    ) -> None:
        self._provider = provider
        self._repository = repository
        self._cache = cache
        self._ttl = ttl

    async def execute(self) -> list[Airport]:
        with TRACER.start_as_current_span("list_airports"):
            cached = self._cache.get(LIST_CACHE_KEY)
            if cached is not None:
                return [Airport(**item) for item in cached]
            try:
                airports = await self._provider.list_airports()
                await self._repository.upsert_many(airports)
                self._cache.set(LIST_CACHE_KEY, [a.to_dict() for a in airports], self._ttl)
                return airports
            except (CircuitOpenError, Exception) as exc:
                LOGGER.warning("provider_failed_fallback_db", extra={"error": str(exc)})
                snapshot = await self._repository.list_all()
                if snapshot:
                    return snapshot
                raise DependencyUnavailableError(
                    "AIRPORT_PROVIDER_UNAVAILABLE",
                    "Airport provider is unavailable and no local snapshot exists",
                ) from exc


class GetAirportUseCase:
    def __init__(
        self,
        provider: AirportProvider,
        repository: AirportRepository,
        cache: CachePort,
        ttl: int,
    ) -> None:
        self._provider = provider
        self._repository = repository
        self._cache = cache
        self._ttl = ttl

    async def execute(self, airport_id: int) -> Airport:
        with TRACER.start_as_current_span("get_airport"):
            key = ITEM_CACHE_KEY.format(id=airport_id)
            cached = self._cache.get(key)
            if cached is not None:
                return Airport(**cached)
            local = await self._repository.get(airport_id)
            try:
                remote = await self._provider.get_airport(airport_id)
            except (CircuitOpenError, Exception) as exc:
                if local:
                    LOGGER.warning("provider_failed_using_snapshot", extra={"id": airport_id, "error": str(exc)})
                    return local
                raise DependencyUnavailableError(
                    "AIRPORT_PROVIDER_UNAVAILABLE",
                    "Airport provider is unavailable",
                ) from exc
            if remote is None:
                if local:
                    return local
                raise NotFoundError("AIRPORT_NOT_FOUND", f"Airport {airport_id} was not found")
            await self._repository.upsert_many([remote])
            self._cache.set(key, remote.to_dict(), self._ttl)
            return remote
