from __future__ import annotations

import os
import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.use_cases import ItineraryService
from app.domain.itinerary import Itinerary
from app.infrastructure.airport_http import HttpAirportCatalog
from app.infrastructure.orm import Base
from app.infrastructure.outbox_publisher import run_outbox_publisher
from app.infrastructure.repository import SQLAlchemyItineraryRepository
from app.schemas import ItineraryCreate, ItineraryResponse, ItineraryUpdate
from pis_platform.db import make_engine, make_session_factory
from pis_platform.fastapi_app import create_service_app

DATABASE_URL = os.getenv(
    "ITINERARY_DATABASE_URL",
    "sqlite+aiosqlite:///./data/itineraries.db",
)
AIRPORT_SERVICE_URL = os.getenv("AIRPORT_SERVICE_URL", "http://localhost:8010")
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
engine = make_engine(DATABASE_URL)
session_factory = make_session_factory(engine)


@asynccontextmanager
async def lifespan(_: FastAPI):
    if DATABASE_URL.startswith("sqlite"):
        from pis_platform.db import create_schema

        await create_schema(engine, Base)
    publisher_task = asyncio.create_task(run_outbox_publisher(session_factory, RABBITMQ_URL))
    try:
        yield
    finally:
        publisher_task.cancel()
        try:
            await publisher_task
        except asyncio.CancelledError:
            pass
        await engine.dispose()


app = create_service_app(
    service_name="itinerary-service",
    title="Personal Itinerary Service",
    log_level=os.getenv("LOG_LEVEL", "INFO"),
)
app.router.lifespan_context = lifespan


async def get_session() -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session


def get_service(session: AsyncSession = Depends(get_session)) -> ItineraryService:
    return ItineraryService(
        SQLAlchemyItineraryRepository(session),
        HttpAirportCatalog(AIRPORT_SERVICE_URL),
    )


def to_response(itinerary: Itinerary) -> ItineraryResponse:
    return ItineraryResponse(
        id=itinerary.id,
        user_name=itinerary.user_name,
        origin_airport_id=itinerary.origin_airport_id,
        destination_airport_id=itinerary.destination_airport_id,
        travel_date=itinerary.travel_date,
        duration_minutes=itinerary.duration_minutes,
        purpose=itinerary.purpose,
        created_at=itinerary.created_at,
        updated_at=itinerary.updated_at,
    )


@app.get("/api/itineraries", response_model=list[ItineraryResponse], tags=["itineraries"])
async def list_itineraries(service: ItineraryService = Depends(get_service)) -> list[ItineraryResponse]:
    return [to_response(item) for item in await service.list()]


@app.post(
    "/api/itineraries",
    response_model=ItineraryResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["itineraries"],
)
async def create_itinerary(
    payload: ItineraryCreate,
    service: ItineraryService = Depends(get_service),
) -> ItineraryResponse:
    return to_response(await service.create(**payload.model_dump()))


@app.get("/api/itineraries/{itinerary_id}", response_model=ItineraryResponse, tags=["itineraries"])
async def get_itinerary(
    itinerary_id: int,
    service: ItineraryService = Depends(get_service),
) -> ItineraryResponse:
    return to_response(await service.get(itinerary_id))


@app.patch("/api/itineraries/{itinerary_id}", response_model=ItineraryResponse, tags=["itineraries"])
async def update_itinerary(
    itinerary_id: int,
    payload: ItineraryUpdate,
    service: ItineraryService = Depends(get_service),
) -> ItineraryResponse:
    changes = payload.model_dump(exclude_unset=True)
    if any(value is None for value in changes.values()):
        from pis_platform.errors import ValidationError

        raise ValidationError("NULL_FIELD", "Itinerary fields cannot be set to null")
    return to_response(await service.update(itinerary_id, changes))


@app.delete("/api/itineraries/{itinerary_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["itineraries"])
async def delete_itinerary(
    itinerary_id: int,
    service: ItineraryService = Depends(get_service),
) -> Response:
    await service.delete(itinerary_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
