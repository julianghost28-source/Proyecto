from __future__ import annotations

from asyncio import gather
from datetime import date

from app.domain.itinerary import Itinerary
from app.domain.ports import AirportCatalog, ItineraryRepository
from pis_platform.errors import DependencyUnavailableError, NotFoundError, ValidationError


class ItineraryService:
    def __init__(
        self,
        repository: ItineraryRepository,
        airport_catalog: AirportCatalog,
    ) -> None:
        self.repository = repository
        self.airport_catalog = airport_catalog

    async def list(self) -> list[Itinerary]:
        return await self.repository.list_all()

    async def get(self, itinerary_id: int) -> Itinerary:
        itinerary = await self.repository.get(itinerary_id)
        if itinerary is None:
            raise NotFoundError("ITINERARY_NOT_FOUND", f"Itinerary {itinerary_id} was not found")
        return itinerary

    async def create(
        self,
        *,
        user_name: str,
        origin_airport_id: int,
        destination_airport_id: int,
        travel_date: date,
        duration_minutes: int,
        purpose: str = "",
    ) -> Itinerary:
        if origin_airport_id == destination_airport_id:
            raise ValidationError("SAME_AIRPORT", "Origin and destination airports must be different")
        await self._validate_airports(origin_airport_id, destination_airport_id)
        return await self.repository.create(
            Itinerary(
                id=None,
                user_name=user_name.strip(),
                origin_airport_id=origin_airport_id,
                destination_airport_id=destination_airport_id,
                travel_date=travel_date,
                duration_minutes=duration_minutes,
                purpose=purpose.strip(),
            )
        )

    async def update(self, itinerary_id: int, changes: dict) -> Itinerary:
        current = await self.get(itinerary_id)
        values = {
            "user_name": current.user_name,
            "origin_airport_id": current.origin_airport_id,
            "destination_airport_id": current.destination_airport_id,
            "travel_date": current.travel_date,
            "duration_minutes": current.duration_minutes,
            "purpose": current.purpose,
        }
        values.update(changes)
        if values["origin_airport_id"] == values["destination_airport_id"]:
            raise ValidationError("SAME_AIRPORT", "Origin and destination airports must be different")
        await self._validate_airports(values["origin_airport_id"], values["destination_airport_id"])
        values["user_name"] = values["user_name"].strip()
        return await self.repository.update(Itinerary(id=itinerary_id, **values))

    async def delete(self, itinerary_id: int) -> None:
        if not await self.repository.delete(itinerary_id):
            raise NotFoundError("ITINERARY_NOT_FOUND", f"Itinerary {itinerary_id} was not found")

    async def _validate_airports(self, origin_id: int, destination_id: int) -> None:
        origin_exists, destination_exists = await gather(
            self.airport_catalog.exists(origin_id),
            self.airport_catalog.exists(destination_id),
        )
        if not origin_exists or not destination_exists:
            missing_id = origin_id if not origin_exists else destination_id
            raise NotFoundError("AIRPORT_NOT_FOUND", f"Airport {missing_id} was not found")
