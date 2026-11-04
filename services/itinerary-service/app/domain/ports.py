from __future__ import annotations

from typing import Protocol

from app.domain.itinerary import Itinerary


class ItineraryRepository(Protocol):
    async def list_all(self) -> list[Itinerary]: ...

    async def get(self, itinerary_id: int) -> Itinerary | None: ...

    async def create(self, itinerary: Itinerary) -> Itinerary: ...

    async def update(self, itinerary: Itinerary) -> Itinerary: ...

    async def delete(self, itinerary_id: int) -> bool: ...


class AirportCatalog(Protocol):
    async def exists(self, airport_id: int) -> bool: ...
