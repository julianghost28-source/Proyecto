from __future__ import annotations

import httpx

from pis_platform.errors import DependencyUnavailableError


class HttpAirportCatalog:
    def __init__(self, base_url: str, timeout_seconds: float = 3.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    async def exists(self, airport_id: int) -> bool:
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(f"{self.base_url}/api/airports/{airport_id}")
        except httpx.HTTPError as exc:
            raise DependencyUnavailableError(
                "AIRPORT_SERVICE_UNAVAILABLE",
                "Airport Service could not be reached",
            ) from exc
        if response.status_code == 404:
            return False
        if response.status_code != 200:
            raise DependencyUnavailableError(
                "AIRPORT_SERVICE_UNAVAILABLE",
                "Airport Service returned an unexpected response",
            )
        return True
