from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

import aio_pika
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.infrastructure.orm import OutboxEventRow

LOGGER = logging.getLogger(__name__)


async def run_outbox_publisher(
    session_factory: async_sessionmaker,
    rabbitmq_url: str,
    exchange_name: str = "itinerary.events",
) -> None:
    while True:
        connection = None
        try:
            connection = await aio_pika.connect_robust(rabbitmq_url)
            channel = await connection.channel(publisher_confirms=True)
            exchange = await channel.declare_exchange(
                exchange_name,
                aio_pika.ExchangeType.TOPIC,
                durable=True,
            )
            LOGGER.info("outbox_publisher_connected")
            while True:
                async with session_factory() as session:
                    now = datetime.now(timezone.utc)
                    result = await session.scalars(
                        select(OutboxEventRow)
                        .where(
                            OutboxEventRow.status == "pending",
                            OutboxEventRow.available_at <= now,
                        )
                        .order_by(OutboxEventRow.created_at)
                        .limit(25)
                        .with_for_update(skip_locked=True)
                    )
                    rows = result.all()
                    if not rows:
                        await session.rollback()
                        await asyncio.sleep(1)
                        continue

                    for row in rows:
                        try:
                            await exchange.publish(
                                aio_pika.Message(
                                    body=row.payload.encode("utf-8"),
                                    message_id=row.id,
                                    type=row.event_type,
                                    content_type="application/json",
                                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                                ),
                                routing_key=row.routing_key,
                                mandatory=True,
                            )
                            row.status = "published"
                            row.published_at = datetime.now(timezone.utc)
                            row.last_error = None
                            LOGGER.info("outbox_event_published", extra={"event_id": row.id})
                        except Exception as exc:
                            row.attempts += 1
                            row.last_error = str(exc)[:2000]
                            row.available_at = datetime.now(timezone.utc) + timedelta(
                                seconds=min(300, 2 ** min(row.attempts, 8))
                            )
                            LOGGER.warning(
                                "outbox_publish_retry",
                                extra={"event_id": row.id, "attempts": row.attempts, "error": str(exc)},
                            )
                    await session.commit()
        except asyncio.CancelledError:
            if connection and not connection.is_closed:
                await connection.close()
            raise
        except Exception:
            LOGGER.exception("outbox_publisher_unavailable")
            if connection and not connection.is_closed:
                await connection.close()
            await asyncio.sleep(3)
