from __future__ import annotations

import asyncio
import json
import logging

import aio_pika
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app import NotificationRow

LOGGER = logging.getLogger(__name__)


async def handle_itinerary_created(session_factory: async_sessionmaker, event: dict) -> None:
    data = event["data"]
    event_id = event["event_id"]
    async with session_factory() as session:
        existing = await session.scalar(select(NotificationRow).where(NotificationRow.event_id == event_id))
        if existing:
            LOGGER.info("notification_event_duplicate", extra={"event_id": event_id})
            return
        row = NotificationRow(
            event_id=event_id,
            event_type=event["event_type"],
            recipient=data["user_name"],
            message=(
                f"Itinerary {data['itinerary_id']} created: airport "
                f"{data['origin_airport_id']} to {data['destination_airport_id']} "
                f"on {data['travel_date']} ({data['duration_minutes']} minutes)."
            ),
            status="simulated_sent",
        )
        session.add(row)
        await session.commit()
        LOGGER.info(
            "simulated_notification_sent",
            extra={"event_id": event_id, "recipient": row.recipient, "itinerary_id": data["itinerary_id"]},
        )


async def run_notification_consumer(
    session_factory: async_sessionmaker,
    rabbitmq_url: str,
    queue_name: str,
) -> None:
    while True:
        connection = None
        try:
            connection = await aio_pika.connect_robust(rabbitmq_url)
            channel = await connection.channel()
            await channel.set_qos(prefetch_count=20)
            queue = await channel.declare_queue(queue_name, passive=True)
            LOGGER.info("notification_consumer_connected", extra={"queue": queue_name})
            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    async with message.process(requeue=False):
                        event = json.loads(message.body.decode("utf-8"))
                        if event.get("event_type") == "ItineraryCreatedEvent":
                            await handle_itinerary_created(session_factory, event)
                        else:
                            LOGGER.warning(
                                "notification_event_ignored",
                                extra={"event_type": event.get("event_type")},
                            )
        except asyncio.CancelledError:
            if connection and not connection.is_closed:
                await connection.close()
            raise
        except Exception:
            LOGGER.exception("notification_consumer_unavailable")
            if connection and not connection.is_closed:
                await connection.close()
            await asyncio.sleep(3)
