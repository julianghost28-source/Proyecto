from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.itinerary import Itinerary
from app.infrastructure.orm import ItineraryRow, OutboxEventRow
from pis_platform.correlation import get_correlation_id


class SQLAlchemyItineraryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _to_domain(row: ItineraryRow) -> Itinerary:
        return Itinerary(
            id=row.id,
            user_name=row.user_name,
            origin_airport_id=row.origin_airport_id,
            destination_airport_id=row.destination_airport_id,
            travel_date=row.travel_date,
            duration_minutes=row.duration_minutes,
            purpose=row.purpose,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def list_all(self) -> list[Itinerary]:
        result = await self.session.scalars(
            select(ItineraryRow).order_by(ItineraryRow.travel_date, ItineraryRow.id)
        )
        return [self._to_domain(row) for row in result.all()]

    async def get(self, itinerary_id: int) -> Itinerary | None:
        row = await self.session.get(ItineraryRow, itinerary_id)
        return self._to_domain(row) if row else None

    async def create(self, itinerary: Itinerary) -> Itinerary:
        row = ItineraryRow(
            user_name=itinerary.user_name,
            origin_airport_id=itinerary.origin_airport_id,
            destination_airport_id=itinerary.destination_airport_id,
            travel_date=itinerary.travel_date,
            duration_minutes=itinerary.duration_minutes,
            purpose=itinerary.purpose,
        )
        self.session.add(row)
        await self.session.flush()
        event_id = str(uuid4())
        occurred_at = datetime.now(timezone.utc).isoformat()
        correlation_id = get_correlation_id()
        event = {
            "event_id": event_id,
            "event_type": "ItineraryCreatedEvent",
            "version": 1,
            "occurred_at": occurred_at,
            "correlation_id": correlation_id,
            "data": {
                "itinerary_id": row.id,
                "user_name": row.user_name,
                "origin_airport_id": row.origin_airport_id,
                "destination_airport_id": row.destination_airport_id,
                "travel_date": row.travel_date.isoformat(),
                "duration_minutes": row.duration_minutes,
                "purpose": row.purpose,
            },
        }
        self.session.add(
            OutboxEventRow(
                id=event_id,
                event_type="ItineraryCreatedEvent",
                routing_key="itinerary.created",
                payload=json.dumps(event),
                status="pending",
                attempts=0,
            )
        )
        await self.session.commit()
        await self.session.refresh(row)
        return self._to_domain(row)

    async def update(self, itinerary: Itinerary) -> Itinerary:
        row = await self.session.get(ItineraryRow, itinerary.id)
        if row is None:
            raise RuntimeError("Itinerary disappeared during update")
        row.user_name = itinerary.user_name
        row.origin_airport_id = itinerary.origin_airport_id
        row.destination_airport_id = itinerary.destination_airport_id
        row.travel_date = itinerary.travel_date
        row.duration_minutes = itinerary.duration_minutes
        row.purpose = itinerary.purpose
        await self.session.commit()
        await self.session.refresh(row)
        return self._to_domain(row)

    async def delete(self, itinerary_id: int) -> bool:
        row = await self.session.get(ItineraryRow, itinerary_id)
        if row is None:
            return False
        await self.session.delete(row)
        await self.session.commit()
        return True
