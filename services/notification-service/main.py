from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import NotificationRow
from consumer import run_notification_consumer
from pis_platform.db import make_engine, make_session_factory
from pis_platform.fastapi_app import create_service_app

DATABASE_URL = os.getenv(
    "NOTIFICATION_DATABASE_URL",
    "sqlite+aiosqlite:///./data/notifications.db",
)
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
RABBITMQ_QUEUE = os.getenv("RABBITMQ_QUEUE", "notification.itinerary-created")
engine = make_engine(DATABASE_URL)
session_factory = make_session_factory(engine)


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: str
    event_type: str
    recipient: str
    message: str
    status: str


@asynccontextmanager
async def lifespan(_: FastAPI):
    consumer_task = asyncio.create_task(
        run_notification_consumer(session_factory, RABBITMQ_URL, RABBITMQ_QUEUE)
    )
    try:
        yield
    finally:
        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass
        await engine.dispose()


app = create_service_app(
    service_name="notification-service",
    title="Personal Itinerary Notification Service",
    log_level=os.getenv("LOG_LEVEL", "INFO"),
)
app.router.lifespan_context = lifespan


async def get_session():
    async with session_factory() as session:
        yield session


@app.get("/api/notifications", response_model=list[NotificationResponse], tags=["notifications"])
async def list_notifications(session: AsyncSession = Depends(get_session)) -> list[NotificationResponse]:
    result = await session.scalars(select(NotificationRow).order_by(NotificationRow.id.desc()))
    return [NotificationResponse.model_validate(row) for row in result.all()]
