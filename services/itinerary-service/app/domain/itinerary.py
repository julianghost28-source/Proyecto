from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True, slots=True)
class Itinerary:
    id: int | None
    user_name: str
    origin_airport_id: int
    destination_airport_id: int
    travel_date: date
    duration_minutes: int
    purpose: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
