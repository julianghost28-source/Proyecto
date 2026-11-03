from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Protocol

from sqlalchemy import DateTime, Integer, String, Text, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from pis_platform.correlation import get_correlation_id

LOGGER = logging.getLogger(__name__)

ITINERARY_CREATED = "itinerary.created"
ITINERARY_CREATED_EVENT = "ItineraryCreatedEvent"


class Base(DeclarativeBase):
    pass


class MessageRow(Base):
    __tablename__ = "broker_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(80))
    routing_key: Mapped[str] = mapped_column(String(80), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    payload: Mapped[str] = mapped_column(Text)
    correlation_id: Mapped[str] = mapped_column(String(36))
    status: Mapped[str] = mapped_column(String(20), index=True, default="pending")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class EventPublisher(Protocol):
    async def publish(self, envelope: dict[str, Any], routing_key: str) -> None: ...


class SqliteBroker:
    """Durable local broker replacing RabbitMQ while Docker is forbidden.

    Persistence lives in data/broker.db — not in any service domain database.
    """

    def __init__(self, url: str) -> None:
        self._engine = create_async_engine(url, future=True)
        self._session = async_sessionmaker(self._engine, expire_on_commit=False)

    async def setup(self) -> None:
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def publish(self, envelope: dict[str, Any], routing_key: str) -> None:
        now = datetime.now(timezone.utc)
        row = MessageRow(
            id=envelope["event_id"],
            event_type=envelope["event_type"],
            routing_key=routing_key,
            version=int(envelope.get("version", 1)),
            payload=json.dumps(envelope),
            correlation_id=envelope.get("correlation_id") or get_correlation_id() or "",
            status="pending",
            attempts=0,
            created_at=now,
            available_at=now,
        )
        async with self._session() as session:
            session.add(row)
            await session.commit()
        LOGGER.info("event_published", extra={"event_id": row.id, "routing_key": routing_key})

    async def consume_one(self, routing_key: str, max_attempts: int = 5) -> dict[str, Any] | None:
        async with self._session() as session:
            now = datetime.now(timezone.utc)
            result = await session.execute(
                select(MessageRow)
                .where(
                    MessageRow.routing_key == routing_key,
                    MessageRow.status == "pending",
                    MessageRow.available_at <= now,
                )
                .order_by(MessageRow.created_at)
                .limit(1)
            )
            row = result.scalar_one_or_none()
            if row is None:
                return None
            row.status = "processing"
            row.attempts += 1
            await session.commit()
            envelope = json.loads(row.payload)
            envelope["_broker_attempts"] = row.attempts
            envelope["_broker_max_attempts"] = max_attempts
            return envelope

    async def ack(self, event_id: str) -> None:
        async with self._session() as session:
            row = await session.get(MessageRow, event_id)
            if row:
                row.status = "done"
                await session.commit()

    async def retry_or_dead(self, event_id: str, error: str, max_attempts: int = 5) -> None:
        async with self._session() as session:
            row = await session.get(MessageRow, event_id)
            if row is None:
                return
            if row.attempts >= max_attempts:
                row.status = "dead"
                LOGGER.error("event_dead_lettered", extra={"event_id": event_id, "error": error})
            else:
                row.status = "pending"
                delay = min(30, 2 ** row.attempts)
                row.available_at = datetime.now(timezone.utc) + timedelta(seconds=delay)
                LOGGER.warning(
                    "event_retry_scheduled",
                    extra={"event_id": event_id, "attempts": row.attempts, "delay": delay, "error": error},
                )
            await session.commit()


def broker_url_from_path(path: str | Path) -> str:
    resolved = Path(path).resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite+aiosqlite:///{resolved.as_posix()}"

