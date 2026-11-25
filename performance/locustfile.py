from __future__ import annotations

import random
import uuid
from datetime import date, timedelta

from locust import HttpUser, between, task


class ItineraryUser(HttpUser):
    """Simulates a person browsing and occasionally creating itineraries."""

    wait_time = between(1, 3)

    def on_start(self) -> None:
        self.airport_ids: list[int] = []
        response = self.client.get("/api/airports", name="GET /api/airports (setup)")
        if response.ok:
            try:
                self.airport_ids = [int(airport["id"]) for airport in response.json()]
            except (TypeError, ValueError, KeyError):
                self.airport_ids = []

    @task(5)
    def list_itineraries(self) -> None:
        self.client.get("/api/itineraries", name="GET /api/itineraries")

    @task(2)
    def list_airports(self) -> None:
        self.client.get("/api/airports", name="GET /api/airports")

    @task(1)
    def create_itinerary(self) -> None:
        if len(self.airport_ids) < 2:
            return

        origin_id, destination_id = random.sample(self.airport_ids, 2)
        payload = {
            "user_name": f"Carga Locust {uuid.uuid4().hex[:8]}",
            "origin_airport_id": origin_id,
            "destination_airport_id": destination_id,
            "travel_date": (date.today() + timedelta(days=random.randint(1, 90))).isoformat(),
            "duration_minutes": random.choice([60, 90, 120, 180]),
            "purpose": "Registro generado por prueba local de carga",
        }
        with self.client.post(
            "/api/itineraries",
            json=payload,
            name="POST /api/itineraries",
            catch_response=True,
        ) as response:
            if response.status_code != 201:
                response.failure(f"HTTP {response.status_code}: {response.text[:200]}")

    @task(1)
    def check_health(self) -> None:
        self.client.get("/health", name="GET /health")
