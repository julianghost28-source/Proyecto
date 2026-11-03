from __future__ import annotations

from typing import Protocol

from app.domain.airport import Airport


class AirportProvider(Protocol):
    """Port toward the external airport source. Domain never talks to API Colombia."""

    async def list_airports(self) -> list[Airport]: ...

    async def get_airport(self, airport_id: int) -> Airport | None: ...


class AirportRepository(Protocol):
    async def upsert_many(self, airports: list[Airport]) -> None: ...

    async def get(self, airport_id: int) -> Airport | None: ...

    async def list_all(self) -> list[Airport]: ...
