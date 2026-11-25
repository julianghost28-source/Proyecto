from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import date

import pytest

from app.application.use_cases import ItineraryService
from app.domain.itinerary import Itinerary
from pis_platform.errors import NotFoundError, ValidationError


class InMemoryItineraryRepository:
    """Repositorio de prueba: guarda los itinerarios solo en memoria."""

    def __init__(self, itineraries: list[Itinerary] | None = None) -> None:
        self.items = {
            item.id: item for item in (itineraries or []) if item.id is not None
        }
        self.next_id = max(self.items, default=0) + 1

    async def list_all(self) -> list[Itinerary]:
        return list(self.items.values())

    async def get(self, itinerary_id: int) -> Itinerary | None:
        return self.items.get(itinerary_id)

    async def create(self, itinerary: Itinerary) -> Itinerary:
        saved = replace(itinerary, id=self.next_id)
        self.items[self.next_id] = saved
        self.next_id += 1
        return saved

    async def update(self, itinerary: Itinerary) -> Itinerary:
        self.items[itinerary.id] = itinerary
        return itinerary

    async def delete(self, itinerary_id: int) -> bool:
        return self.items.pop(itinerary_id, None) is not None


class InMemoryAirportCatalog:
    """Catálogo de prueba que reconoce dos aeropuertos."""

    def __init__(self, airport_ids: set[int] | None = None) -> None:
        self.airport_ids = airport_ids or {9, 7}

    async def exists(self, airport_id: int) -> bool:
        return airport_id in self.airport_ids


def make_itinerary(
    itinerary_id: int = 1,
    *,
    duration_minutes: int = 90,
    purpose: str = "Trabajo",
) -> Itinerary:
    return Itinerary(
        id=itinerary_id,
        user_name="Julian",
        origin_airport_id=9,
        destination_airport_id=7,
        travel_date=date(2026, 11, 10),
        duration_minutes=duration_minutes,
        purpose=purpose,
    )


def make_service(
    itineraries: list[Itinerary] | None = None,
) -> tuple[ItineraryService, InMemoryItineraryRepository]:
    repository = InMemoryItineraryRepository(itineraries)
    service = ItineraryService(repository, InMemoryAirportCatalog())
    return service, repository


def test_list_returns_saved_itineraries():
    first = make_itinerary(1)
    second = replace(make_itinerary(2), user_name="Ana")
    service, _ = make_service([first, second])

    result = asyncio.run(service.list())

    assert result == [first, second]


def test_create_saves_itinerary_with_trimmed_text():
    service, repository = make_service()

    created = asyncio.run(
        service.create(
            user_name="  Julian  ",
            origin_airport_id=9,
            destination_airport_id=7,
            travel_date=date(2026, 11, 10),
            duration_minutes=90,
            purpose="  Trabajo  ",
        )
    )

    assert created.id == 1
    assert created.user_name == "Julian"
    assert created.purpose == "Trabajo"
    assert repository.items[1] == created


def test_create_rejects_same_origin_and_destination():
    service, repository = make_service()

    with pytest.raises(ValidationError) as error:
        asyncio.run(
            service.create(
                user_name="Julian",
                origin_airport_id=9,
                destination_airport_id=9,
                travel_date=date(2026, 11, 10),
                duration_minutes=90,
            )
        )

    assert error.value.code == "SAME_AIRPORT"
    assert repository.items == {}


def test_create_rejects_unknown_airport():
    service, repository = make_service()

    with pytest.raises(NotFoundError) as error:
        asyncio.run(
            service.create(
                user_name="Julian",
                origin_airport_id=9,
                destination_airport_id=999,
                travel_date=date(2026, 11, 10),
                duration_minutes=90,
            )
        )

    assert error.value.code == "AIRPORT_NOT_FOUND"
    assert repository.items == {}


def test_get_returns_requested_itinerary():
    itinerary = make_itinerary()
    service, _ = make_service([itinerary])

    result = asyncio.run(service.get(1))

    assert result == itinerary


def test_get_missing_itinerary_reports_not_found():
    service, _ = make_service()

    with pytest.raises(NotFoundError) as error:
        asyncio.run(service.get(404))

    assert error.value.code == "ITINERARY_NOT_FOUND"


def test_update_changes_duration_and_preserves_other_fields():
    itinerary = make_itinerary()
    service, repository = make_service([itinerary])

    updated = asyncio.run(service.update(1, {"duration_minutes": 120}))

    assert updated.duration_minutes == 120
    assert updated.user_name == itinerary.user_name
    assert updated.origin_airport_id == itinerary.origin_airport_id
    assert updated.destination_airport_id == itinerary.destination_airport_id
    assert repository.items[1] == updated


def test_delete_removes_existing_itinerary():
    service, repository = make_service([make_itinerary()])

    asyncio.run(service.delete(1))

    assert repository.items == {}


def test_delete_missing_itinerary_reports_not_found():
    service, _ = make_service()

    with pytest.raises(NotFoundError) as error:
        asyncio.run(service.delete(404))

    assert error.value.code == "ITINERARY_NOT_FOUND"
