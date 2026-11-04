from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ItineraryCreate(BaseModel):
    user_name: str = Field(min_length=1, max_length=120)
    origin_airport_id: int = Field(gt=0)
    destination_airport_id: int = Field(gt=0)
    travel_date: date
    duration_minutes: int = Field(gt=0, le=10080)
    purpose: str = Field(default="", max_length=250)

    @field_validator("user_name")
    @classmethod
    def require_nonblank_user_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("user_name cannot be blank")
        return value


class ItineraryUpdate(BaseModel):
    user_name: str | None = Field(default=None, min_length=1, max_length=120)
    origin_airport_id: int | None = Field(default=None, gt=0)
    destination_airport_id: int | None = Field(default=None, gt=0)
    travel_date: date | None = None
    duration_minutes: int | None = Field(default=None, gt=0, le=10080)
    purpose: str | None = Field(default=None, max_length=250)

    @field_validator("user_name")
    @classmethod
    def require_nonblank_user_name(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("user_name cannot be blank")
        return value


class ItineraryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_name: str
    origin_airport_id: int
    destination_airport_id: int
    travel_date: date
    duration_minutes: int
    purpose: str
    created_at: datetime
    updated_at: datetime
