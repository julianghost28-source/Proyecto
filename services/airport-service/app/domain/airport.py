from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Airport:
    id: int
    name: str
    iata_code: str | None
    oaci_code: str | None
    city: str | None
    department: str | None
    latitude: float | None
    longitude: float | None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "iata_code": self.iata_code,
            "oaci_code": self.oaci_code,
            "city": self.city,
            "department": self.department,
            "latitude": self.latitude,
            "longitude": self.longitude,
        }
