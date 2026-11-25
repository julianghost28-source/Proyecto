from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent.parent.parent
PACKAGES = ROOT / "packages" / "pis-platform"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(PACKAGES) not in sys.path:
    sys.path.insert(0, str(PACKAGES))

from fastapi import HTTPException
from fastapi.responses import HTMLResponse
from pis_platform.fastapi_app import create_service_app

DEFAULT_PORT = int(os.getenv("PORT", "8010"))


class AirportItem(BaseModel):
    id: int
    name: str
    iata_code: str | None = None
    oaci_code: str | None = None
    city: str | None = None
    department: str | None = None
    latitude: float | None = None
    longitude: float | None = None


FALLBACK_AIRPORTS = [
    AirportItem(
        id=1,
        name="Aeropuerto Internacional El Dorado",
        iata_code="BOG",
        oaci_code="SKBO",
        city="Bogotá",
        department="Cundinamarca",
        latitude=4.70159,
        longitude=-74.1469,
    ),
    AirportItem(
        id=2,
        name="Aeropuerto Internacional José María Córdova",
        iata_code="MDE",
        oaci_code="SKRG",
        city="Medellín",
        department="Antioquia",
        latitude=6.1667,
        longitude=-75.4231,
    ),
    AirportItem(
        id=3,
        name="Aeropuerto Internacional Rafael Núñez",
        iata_code="CTG",
        oaci_code="SKCG",
        city="Cartagena",
        department="Bolívar",
        latitude=10.4424,
        longitude=-75.5130,
    ),
    AirportItem(
        id=4,
        name="Aeropuerto Internacional Alfonso Bonilla Aragón",
        iata_code="CLO",
        oaci_code="SKCL",
        city="Cali",
        department="Valle del Cauca",
        latitude=3.5432,
        longitude=-76.3816,
    ),
    AirportItem(
        id=5,
        name="Aeropuerto Internacional Ernesto Cortissoz",
        iata_code="BAQ",
        oaci_code="SKBQ",
        city="Barranquilla",
        department="Atlántico",
        latitude=11.119,
        longitude=-74.781,
    ),
]

API_COLOMBIA_AIRPORTS_URL = "https://api-colombia.com/api/v1/airport"


def _clean_optional_text(value: Any) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    if not text or text.upper() in {"N/A", "NA", "NULL", "NONE"}:
        return None
    return text


def normalize_airport(raw: dict[str, Any]) -> AirportItem | None:
    if not isinstance(raw, dict):
        return None

    department = raw.get("department") or {}
    city = raw.get("city") or {}

    latitude = raw.get("latitude")
    longitude = raw.get("longitude")

    try:
        latitude_value = float(latitude) if latitude not in (None, "", "N/A") else None
        longitude_value = (
            float(longitude) if longitude not in (None, "", "N/A") else None
        )
    except (TypeError, ValueError):
        latitude_value = None
        longitude_value = None

    if (
        latitude_value is not None
        and longitude_value is not None
        and abs(latitude_value) > 13
        and abs(longitude_value) <= 13
    ):
        latitude_value, longitude_value = longitude_value, latitude_value

    return AirportItem(
        id=int(raw.get("id") or 0),
        name=str(raw.get("name") or "Aeropuerto sin nombre"),
        iata_code=(
            _clean_optional_text(raw.get("iataCode"))
            or _clean_optional_text(raw.get("iata_code"))
            or _clean_optional_text(raw.get("iata"))
            or _clean_optional_text(raw.get("codeIata"))
        ),
        oaci_code=(
            _clean_optional_text(raw.get("oaciCode"))
            or _clean_optional_text(raw.get("oaci_code"))
            or _clean_optional_text(raw.get("icao"))
            or _clean_optional_text(raw.get("codeOaci"))
        ),
        city=(city.get("name") if isinstance(city, dict) else None)
        or _clean_optional_text(raw.get("cityName"))
        or _clean_optional_text(raw.get("city")),
        department=(department.get("name") if isinstance(department, dict) else None)
        or _clean_optional_text(raw.get("departmentName")),
        latitude=latitude_value,
        longitude=longitude_value,
    )


async def fetch_airports() -> list[AirportItem]:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(API_COLOMBIA_AIRPORTS_URL)
            response.raise_for_status()
            payload = response.json()
    except Exception:
        return FALLBACK_AIRPORTS

    if not isinstance(payload, list):
        return FALLBACK_AIRPORTS

    airports: list[AirportItem] = []
    for item in payload:
        airport = normalize_airport(item)
        if (
            airport is not None
            and airport.latitude is not None
            and airport.longitude is not None
        ):
            airports.append(airport)

    return airports if airports else FALLBACK_AIRPORTS


app = create_service_app(
    service_name="airport-service",
    title="Airport Service",
    version="0.1.0",
    log_level="INFO",
    cors_origins=["http://127.0.0.1:8010", "http://localhost:8010"],
    enable_rate_limit=False,
    otel_console=False,
)


@app.get("/", include_in_schema=False)
async def root() -> HTMLResponse:
    return HTMLResponse(
        """
        <!doctype html>
        <html lang="es">
        <head>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1" />
            <title>Airport Service</title>
            <link rel="preconnect" href="https://fonts.googleapis.com">
            <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
            <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&display=swap" rel="stylesheet">
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossorigin="" />
            <link rel="stylesheet" href="https://unpkg.com/maplibre-gl@6.3.0/dist/maplibre-gl.css" />
            <script type="importmap">
                {
                    "imports": {
                        "leaflet": "https://unpkg.com/leaflet@1.9.4/dist/leaflet-src.esm.js",
                        "maplibre-gl": "https://unpkg.com/maplibre-gl@6.3.0/dist/maplibre-gl.mjs"
                    }
                }
            </script>
            <style>
                :root {
                    --bg-1: #edf6ff;
                    --bg-2: #dfeeff;
                    --bg-3: #cfe0ff;
                    --panel: rgba(255, 255, 255, 0.82);
                    --panel-strong: rgba(255, 255, 255, 0.94);
                    --line: rgba(76, 118, 176, 0.18);
                    --gold-1: #f7d37d;
                    --gold-2: #f0b95d;
                    --gold-3: #df9a3d;
                    --amber: #ffd99a;
                    --text: #163149;
                    --muted: #4d6782;
                    --sky: #59a9ff;
                    --mint: #5ec9d4;
                    --success: #2ec27e;
                    --danger: #eb6a55;
                    --shadow: 0 24px 60px rgba(40, 70, 102, 0.18);
                    --chip: rgba(89, 169, 255, 0.08);
                }

                * { box-sizing: border-box; }

                html, body {
                    margin: 0;
                    min-height: 100%;
                    font-family: "Poppins", "Segoe UI", sans-serif;
                    background:
                        radial-gradient(circle at top, rgba(130, 182, 255, 0.36), transparent 30%),
                        linear-gradient(180deg, #eaf5ff 0%, #dfeeff 34%, #cfe2ff 100%);
                    color: var(--text);
                }

                body::before {
                    content: "";
                    position: fixed;
                    inset: 0;
                    background:
                        linear-gradient(rgba(255,255,255,0.03), rgba(255,255,255,0.01)),
                        repeating-linear-gradient(90deg, rgba(255,255,255,0.012) 0, rgba(255,255,255,0.012) 1px, transparent 1px, transparent 7px);
                    pointer-events: none;
                }

                .viewport {
                    max-width: 1460px;
                    margin: 0 auto;
                    padding: 20px 18px 80px;
                }

                .shell {
                    position: relative;
                    background: linear-gradient(180deg, rgba(255,255,255,0.9), rgba(232,242,255,0.96));
                    border: 1px solid rgba(90, 142, 211, 0.2);
                    border-radius: 28px;
                    box-shadow: 0 22px 55px rgba(72, 111, 169, 0.16);
                    padding: 18px 18px 22px;
                    overflow: hidden;
                }

                .shell::before {
                    content: "";
                    position: absolute;
                    inset: 12px;
                    border: 1px solid rgba(255,255,255,0.04);
                    border-radius: 20px;
                    pointer-events: none;
                }

                .topbar {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    gap: 16px;
                    padding: 8px 12px 18px;
                    border-bottom: 1px solid var(--line);
                    margin-bottom: 18px;
                }

                .route-summary {
                    display: grid;
                    grid-template-columns: repeat(3, minmax(0, 1fr));
                    gap: 14px;
                    margin: 20px 0 4px;
                }

                .route-pill {
                    background: linear-gradient(180deg, rgba(255,255,255,0.8), rgba(239,248,255,0.92));
                    border: 1px solid rgba(90, 168, 255, 0.16);
                    border-radius: 16px;
                    padding: 14px 16px;
                    box-shadow: 0 10px 22px rgba(28, 56, 86, 0.06);
                }

                .route-pill-label {
                    display: block;
                    font-size: 0.64rem;
                    letter-spacing: 0.12em;
                    text-transform: uppercase;
                    color: var(--muted);
                    margin-bottom: 8px;
                }

                .route-pill-value {
                    font-size: 1.05rem;
                    font-weight: 700;
                    color: var(--text);
                }

                .eyebrow {
                    color: var(--metal-2);
                    letter-spacing: 0.18em;
                    text-transform: uppercase;
                    font-size: 0.66rem;
                    margin-bottom: 8px;
                    font-weight: 700;
                }

                .title-wrap h1 {
                    margin: 0;
                    font-size: clamp(2.1rem, 3vw, 3.3rem);
                    line-height: 1.05;
                    letter-spacing: -0.05em;
                    color: #f2e8d0;
                }

                .subtitle {
                    margin-top: 8px;
                    color: var(--muted);
                    font-size: 0.94rem;
                    letter-spacing: 0.05em;
                }

                .badge {
                    display: inline-flex;
                    align-items: center;
                    justify-content: center;
                    gap: 12px;
                    min-width: 200px;
                    height: 72px;
                    padding: 10px 18px;
                    border-radius: 18px;
                    background: linear-gradient(135deg, #0f4c81, #2fa0ea 42%, #9ad9ff 58%, #0e355e 100%);
                    box-shadow: 0 16px 28px rgba(14, 53, 94, 0.24), inset 0 1px 0 rgba(255,255,255,0.3);
                    border: 1px solid rgba(255,255,255,0.3);
                    color: #ffffff;
                    font-weight: 800;
                    font-size: 0.72rem;
                    letter-spacing: 0.18em;
                    text-transform: uppercase;
                }

                .badge .plane {
                    display: inline-flex;
                    align-items: center;
                    justify-content: center;
                    width: 38px;
                    height: 38px;
                    border-radius: 12px;
                    background: rgba(255,255,255,0.18);
                    border: 1px solid rgba(255,255,255,0.26);
                    font-size: 1.2rem;
                    box-shadow: inset 0 1px 0 rgba(255,255,255,0.3);
                }

                .content-grid {
                    display: grid;
                    grid-template-columns: minmax(0, 1.8fr) 330px;
                    gap: 18px;
                    align-items: stretch;
                }

                .map-panel,
                .side-panel,
                .form-panel {
                    background: rgba(255, 255, 255, 0.82);
                    border: 1px solid rgba(101, 137, 184, 0.16);
                    border-radius: 20px;
                    overflow: hidden;
                    box-shadow: inset 0 1px 0 rgba(255,255,255,0.5);
                }

                .panel-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 14px 18px 10px;
                    border-bottom: 1px solid var(--line);
                    background: rgba(255,255,255,0.06);
                    color: #113f63;
                    text-transform: uppercase;
                    font-size: 0.7rem;
                    letter-spacing: 0.15em;
                    font-weight: 700;
                }

                .kpi {
                    background: rgba(255,255,255,0.02);
                    border: 1px solid var(--line);
                    border-radius: 999px;
                    padding: 7px 11px;
                    font-size: 0.62rem;
                    color: var(--muted);
                    letter-spacing: 0.1em;
                }

                .map-shell {
                    position: relative;
                    width: 100%;
                    height: 560px;
                    background:
                        radial-gradient(circle at top, rgba(130, 223, 231, 0.15), transparent 34%),
                        linear-gradient(180deg, rgba(11, 27, 33, 0.86), rgba(7, 17, 22, 0.82));
                    overflow: hidden;
                    border-radius: 22px;
                    border: 1px solid rgba(247, 211, 125, 0.18);
                    box-shadow: inset 0 1px 0 rgba(255,255,255,0.06), 0 10px 28px rgba(2, 9, 12, 0.22);
                }

                .map-shell::before {
                    content: "";
                    position: absolute;
                    inset: 12px;
                    border-radius: 16px;
                    border: 1px solid rgba(255,255,255,0.06);
                    pointer-events: none;
                }

                #map {
                    position: relative;
                    z-index: 1;
                    width: 100%;
                    height: 100%;
                    filter: saturate(1.08) contrast(1.04);
                    background: #0b1721;
                }

                .leaflet-container {
                    background: #0b1721;
                }

                .leaflet-popup-content-wrapper,
                .leaflet-popup-tip {
                    background: rgba(12, 20, 26, 0.96);
                    color: #edf8fb;
                    border: 1px solid rgba(126, 212, 214, 0.22);
                }

                .leaflet-tooltip {
                    background: rgba(11, 20, 26, 0.96);
                    border: 1px solid rgba(126, 212, 214, 0.22);
                    color: #edf8fb;
                    box-shadow: 0 12px 24px rgba(0,0,0,0.22);
                    padding: 8px 10px;
                    font-size: 0.72rem;
                    line-height: 1.35;
                    border-radius: 10px;
                }

                .side-panel {
                    display: flex;
                    flex-direction: column;
                    gap: 12px;
                    padding: 16px 16px 18px;
                    background: linear-gradient(180deg, rgba(255,255,255,0.86), rgba(240,246,255,0.92));
                    border: 1px solid rgba(90, 168, 255, 0.14);
                }

                .clock {
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    align-items: center;
                    min-height: 170px;
                    padding: 18px 12px;
                    border-radius: 18px;
                    background: linear-gradient(145deg, rgba(19, 76, 146, 0.1), rgba(120, 191, 255, 0.12));
                    border: 1px solid rgba(17, 90, 155, 0.15);
                    text-align: center;
                }

                .clock-label {
                    letter-spacing: 0.2em;
                    font-size: 0.7rem;
                    text-transform: uppercase;
                    color: #3d5f81;
                    margin-bottom: 14px;
                    font-weight: 700;
                }

                .clock-date {
                    color: #0d3a5f;
                    font-weight: 800;
                    letter-spacing: 0.12em;
                    font-size: 0.95rem;
                    margin-bottom: 10px;
                }

                .clock-time {
                    color: #0b4d87;
                    font-size: clamp(2rem, 2vw, 2.8rem);
                    font-weight: 800;
                    letter-spacing: 0.08em;
                    text-shadow: 0 2px 10px rgba(11, 77, 135, 0.08);
                }

                .signal-box {
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    padding: 13px 14px;
                    border-radius: 14px;
                    border: 1px solid rgba(46, 194, 126, 0.2);
                    background: rgba(230, 248, 239, 0.95);
                    color: #145b3b;
                    font-size: 0.77rem;
                    letter-spacing: 0.05em;
                    font-weight: 600;
                }

                .signal-dot {
                    width: 10px;
                    height: 10px;
                    border-radius: 50%;
                    background: var(--success);
                    box-shadow: 0 0 14px rgba(123, 219, 165, 0.95);
                }

                .form-panel {
                    margin-top: 20px;
                    padding: 0;
                }

                .form-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 14px 18px 12px;
                    border-bottom: 1px solid var(--line);
                    color: #17324d;
                    text-transform: uppercase;
                    font-weight: 700;
                    letter-spacing: 0.14em;
                    font-size: 0.72rem;
                    background: linear-gradient(180deg, rgba(224,240,255,0.7), rgba(255,255,255,0.12));
                }

                #route-status {
                    color: #0f4c81;
                    font-weight: 700;
                    letter-spacing: 0.08em;
                }

                .itinerary-form {
                    display: grid;
                    grid-template-columns: repeat(2, minmax(0, 1fr));
                    gap: 14px;
                    padding: 16px 18px 18px;
                    background: linear-gradient(180deg, rgba(255,255,255,0.18), rgba(234,244,255,0.28));
                }

                .date-field input[type="date"] {
                    min-height: 44px;
                    padding: 8px 12px;
                    font-size: 0.9rem;
                    border-radius: 12px;
                }

                .field {
                    display: flex;
                    flex-direction: column;
                    gap: 8px;
                }

                .field.full {
                    grid-column: 1 / -1;
                }

                label {
                    font-size: 0.72rem;
                    color: #23496d;
                    text-transform: uppercase;
                    letter-spacing: 0.12em;
                    font-weight: 600;
                }

                select, input, button {
                    font: inherit;
                }

                select, input {
                    width: 100%;
                    border: 1px solid rgba(74, 127, 191, 0.25);
                    border-radius: 12px;
                    background: linear-gradient(180deg, rgba(255,255,255,0.96), rgba(235,244,255,0.95));
                    color: #123b5d;
                    padding: 12px 12px;
                    outline: none;
                    box-shadow: inset 0 1px 2px rgba(20, 55, 80, 0.04);
                }

                select option {
                    background: #ffffff;
                    color: #123b5d;
                }

                select:focus, input:focus {
                    border-color: rgba(59, 146, 255, 0.45);
                    box-shadow: 0 0 0 4px rgba(89, 169, 255, 0.15);
                }

                button {
                    background: linear-gradient(135deg, #0f4c81, #2d8fe9 42%, #7cc7ff 58%, #0d3761 100%);
                    color: #ffffff;
                    border: 1px solid rgba(255,255,255,0.22);
                    border-radius: 12px;
                    padding: 12px 16px;
                    font-weight: 800;
                    letter-spacing: 0.12em;
                    text-transform: uppercase;
                    cursor: pointer;
                    box-shadow: 0 12px 22px rgba(43, 117, 172, 0.24), inset 0 2px 8px rgba(255,255,255,0.2);
                }

                #cancel-edit {
                    background: linear-gradient(135deg, #edf6ff, #dfeeff);
                    color: #123b5d;
                    border-color: rgba(86, 146, 214, 0.2);
                    box-shadow: 0 10px 18px rgba(84, 125, 181, 0.08);
                }

                .airport-section-head {
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    gap: 12px;
                    margin-top: 28px;
                    margin-bottom: 18px;
                    padding: 0 6px;
                }

                .airport-section-head h2 {
                    margin: 0;
                    font-size: clamp(1.2rem, 2vw, 1.8rem);
                    color: #123b5d;
                    letter-spacing: -0.04em;
                }

                .itineraries-section {
                    margin-top: 24px;
                    scroll-margin-top: 18px;
                }

                .itineraries-heading {
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    gap: 16px;
                    padding: 0 6px;
                }

                .itineraries-eyebrow {
                    color: #3285c2;
                    font-size: 0.64rem;
                    font-weight: 800;
                    letter-spacing: 0.16em;
                    text-transform: uppercase;
                }

                .itineraries-heading h2 {
                    margin: 5px 0 3px;
                    color: #123b5d;
                    font-size: clamp(1.25rem, 2vw, 1.75rem);
                    letter-spacing: -0.04em;
                }

                .itineraries-heading p {
                    margin: 0;
                    color: #5b7691;
                    font-size: 0.82rem;
                }

                .itinerary-count {
                    flex-shrink: 0;
                    padding: 9px 13px;
                    border: 1px solid rgba(66, 142, 208, 0.2);
                    border-radius: 999px;
                    background: linear-gradient(135deg, #edf7ff, #dceeff);
                    color: #155889;
                    font-size: 0.72rem;
                    font-weight: 800;
                }

                .airport-badge {
                    display: inline-flex;
                    align-items: center;
                    justify-content: center;
                    padding: 8px 12px;
                    background: linear-gradient(135deg, #eaf5ff, #d8ebff);
                    color: #0f4c81;
                    border: 1px solid rgba(94, 139, 211, 0.22);
                    border-radius: 999px;
                    font-size: 0.68rem;
                    letter-spacing: 0.12em;
                    text-transform: uppercase;
                    font-weight: 800;
                }

                .airport-modal {
                    position: fixed;
                    inset: 0;
                    display: none;
                    align-items: center;
                    justify-content: center;
                    background: rgba(12, 28, 43, 0.44);
                    backdrop-filter: blur(4px);
                    z-index: 2000;
                    padding: 20px;
                }

                .airport-modal.is-open {
                    display: flex;
                }

                .airport-modal-panel {
                    width: min(560px, 100%);
                    background: linear-gradient(180deg, rgba(255,255,255,0.98), rgba(234,243,255,0.98));
                    border: 1px solid rgba(80, 135, 206, 0.2);
                    border-radius: 24px;
                    box-shadow: 0 26px 70px rgba(18, 49, 84, 0.2);
                    overflow: hidden;
                }

                .airport-modal-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    gap: 10px;
                    padding: 18px 20px 12px;
                    background: linear-gradient(180deg, rgba(224,240,255,0.82), rgba(255,255,255,0.18));
                    border-bottom: 1px solid var(--line);
                }

                .airport-modal-header h3 {
                    margin: 0;
                    color: #123b5d;
                    font-size: 1.15rem;
                    letter-spacing: -0.03em;
                }

                .airport-modal-close {
                    border: 0;
                    background: rgba(89, 169, 255, 0.12);
                    color: #123b5d;
                    width: 34px;
                    height: 34px;
                    border-radius: 50%;
                    font-size: 1.2rem;
                    cursor: pointer;
                }

                .airport-modal-body {
                    padding: 18px 20px 22px;
                    color: var(--text);
                }

                .airport-modal-body p {
                    margin: 0;
                    line-height: 1.7;
                    color: #35526d;
                }

                .airport-modal-tag {
                    display: inline-flex;
                    align-items: center;
                    padding: 6px 10px;
                    border-radius: 999px;
                    background: rgba(89, 169, 255, 0.08);
                    border: 1px solid rgba(86, 146, 214, 0.18);
                    color: #134d77;
                    font-size: 0.66rem;
                    letter-spacing: 0.12em;
                    font-weight: 800;
                    text-transform: uppercase;
                    margin-bottom: 12px;
                }

                .recommendations {
                    margin-top: 32px;
                }

                .recommendation-hero {
                    display: grid;
                    grid-template-columns: 1.4fr 1fr 1fr;
                    gap: 14px;
                    margin: 18px 0 16px;
                }

                .recommendation-hero-card {
                    position: relative;
                    min-height: 150px;
                    border-radius: 18px;
                    overflow: hidden;
                    border: 1px solid rgba(86, 146, 214, 0.18);
                    box-shadow: 0 12px 20px rgba(52, 94, 156, 0.1);
                }

                .recommendation-hero-card img {
                    position: absolute;
                    inset: 0;
                    width: 100%;
                    height: 100%;
                    object-fit: cover;
                    display: block;
                    filter: saturate(0.9) contrast(1.05);
                }

                .recommendation-hero-card::before {
                    content: "";
                    position: absolute;
                    inset: 0;
                    background: linear-gradient(180deg, rgba(9, 35, 62, 0.26), rgba(9, 35, 62, 0.75));
                    z-index: 1;
                }

                .recommendation-hero-copy {
                    position: absolute;
                    left: 16px;
                    right: 16px;
                    bottom: 14px;
                    z-index: 2;
                    color: white;
                }

                .recommendation-hero-copy span {
                    display: inline-block;
                    font-size: 0.64rem;
                    letter-spacing: 0.14em;
                    text-transform: uppercase;
                    font-weight: 800;
                    opacity: 0.9;
                    margin-bottom: 6px;
                }

                .recommendation-hero-copy strong {
                    display: block;
                    font-size: 1.08rem;
                    letter-spacing: -0.04em;
                }

                .recommendation-grid {
                    display: grid;
                    grid-template-columns: repeat(3, minmax(0, 1fr));
                    gap: 16px;
                    margin-top: 18px;
                }

                .recommendation-card {
                    background: linear-gradient(180deg, rgba(255,255,255,0.96), rgba(232,241,255,0.95));
                    border: 1px solid rgba(102, 160, 232, 0.18);
                    border-radius: 18px;
                    padding: 18px 18px 16px;
                    box-shadow: 0 14px 24px rgba(55, 93, 146, 0.08);
                    cursor: pointer;
                    transition: transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease;
                    position: relative;
                    overflow: hidden;
                    animation: recommendationFloat 5s ease-in-out infinite;
                }

                .recommendation-card::before {
                    content: "";
                    position: absolute;
                    inset: auto -30% -40% 0;
                    height: 120px;
                    background: radial-gradient(circle at center, rgba(134, 204, 255, 0.22), rgba(134, 204, 255, 0));
                    pointer-events: none;
                }

                .recommendation-card:hover {
                    transform: translateY(-4px) scale(1.01);
                    border-color: rgba(81, 140, 219, 0.28);
                    box-shadow: 0 18px 34px rgba(55, 93, 146, 0.14);
                }

                .recommendation-top {
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    gap: 12px;
                    margin-bottom: 12px;
                    position: relative;
                    z-index: 1;
                }

                .recommendation-badge {
                    display: inline-flex;
                    align-items: center;
                    justify-content: center;
                    padding: 6px 8px;
                    border-radius: 999px;
                    background: rgba(89, 169, 255, 0.08);
                    border: 1px solid rgba(86, 146, 214, 0.18);
                    color: #134d77;
                    font-size: 0.62rem;
                    letter-spacing: 0.12em;
                    text-transform: uppercase;
                    font-weight: 800;
                }

                .recommendation-price {
                    font-size: 1.15rem;
                    font-weight: 800;
                    color: #0f4c81;
                    letter-spacing: -0.04em;
                }

                .recommendation-route {
                    margin: 0 0 8px;
                    font-size: 1.08rem;
                    font-weight: 700;
                    color: #163149;
                    letter-spacing: -0.03em;
                    position: relative;
                    z-index: 1;
                }

                .recommendation-meta {
                    display: flex;
                    gap: 8px;
                    flex-wrap: wrap;
                    margin-bottom: 10px;
                    position: relative;
                    z-index: 1;
                }

                .recommendation-pill {
                    display: inline-flex;
                    align-items: center;
                    gap: 6px;
                    background: rgba(89, 169, 255, 0.08);
                    border: 1px solid rgba(86, 146, 214, 0.18);
                    border-radius: 999px;
                    color: #174d7c;
                    padding: 5px 9px;
                    font-size: 0.68rem;
                    font-weight: 700;
                }

                .recommendation-copy {
                    margin: 0;
                    font-size: 0.84rem;
                    line-height: 1.6;
                    color: #486784;
                    position: relative;
                    z-index: 1;
                }

                .recommendation-footer {
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    gap: 12px;
                    margin-top: 14px;
                    border-top: 1px solid rgba(103, 155, 222, 0.15);
                    padding-top: 12px;
                    position: relative;
                    z-index: 1;
                }

                .recommendation-action {
                    display: inline-flex;
                    align-items: center;
                    justify-content: center;
                    background: linear-gradient(135deg, #0e5d9a, #2f87d8);
                    color: white;
                    border: none;
                    border-radius: 10px;
                    padding: 8px 12px;
                    font-size: 0.72rem;
                    font-weight: 700;
                    letter-spacing: 0.06em;
                    text-transform: uppercase;
                    cursor: pointer;
                    box-shadow: 0 10px 18px rgba(30, 112, 197, 0.2);
                }

                .recommendation-trend {
                    font-size: 0.7rem;
                    font-weight: 700;
                    color: #2e6d9f;
                    letter-spacing: 0.04em;
                    text-transform: uppercase;
                }

                @keyframes recommendationFloat {
                    0%, 100% { transform: translateY(0px); }
                    50% { transform: translateY(-2px); }
                }

                .airport-tooltip {
                    background: rgba(255,255,255,0.96);
                    border: 1px solid rgba(90, 161, 245, 0.25);
                    border-radius: 10px;
                    box-shadow: 0 10px 24px rgba(31, 82, 147, 0.16);
                    color: #123b5d;
                    font-size: 0.74rem;
                    padding: 7px 9px;
                    letter-spacing: 0.02em;
                }

                .itinerary-list {
                    margin-top: 12px;
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(min(100%, 430px), 1fr));
                    gap: 16px;
                    const customPurposeField = document.getElementById('custom-purpose-field');
                    const customPurposeInput = document.getElementById('custom-purpose');
                    const [firstName, ...lastNameParts] = String(itinerary.user_name || '').trim().split(/\\s+/);
                }

                .itinerary-item {
                    position: relative;
                    state.editingTravelDate = itinerary.travel_date || null;
                    const today = getLocalDateValue();
                    dateInput.min = state.editingTravelDate && state.editingTravelDate < today
                        ? state.editingTravelDate
                        : today;
                    document.getElementById('first-name').value = firstName || '';
                    document.getElementById('last-name').value = lastNameParts.join(' ');
                    flex-direction: column;
                    const purposes = [...purposeInput.options].map(option => option.value);
                    if (purposes.includes(itinerary.purpose)) {
                        purposeInput.value = itinerary.purpose || '';
                        customPurposeField.hidden = true;
                        customPurposeInput.required = false;
                        customPurposeInput.value = '';
                    } else {
                        purposeInput.value = 'Otro';
                        customPurposeField.hidden = false;
                        customPurposeInput.required = true;
                        customPurposeInput.value = itinerary.purpose || '';
                    }
                    min-width: 0;
                    padding: 20px;
                    border: 1px solid rgba(89, 153, 224, 0.22);
                    border-radius: 22px;
                    background: linear-gradient(145deg, rgba(255,255,255,0.98), rgba(232,243,255,0.96));
                    color: var(--text);
                    box-shadow: 0 14px 30px rgba(50, 94, 145, 0.1), inset 0 1px 0 rgba(255,255,255,0.9);
                    state.editingTravelDate = null;
                    document.getElementById('date').min = getLocalDateValue();
                    transition: transform 0.22s ease, box-shadow 0.22s ease, border-color 0.22s ease;
                }


                document.getElementById('purpose').addEventListener('change', function () {
                    const customPurposeField = document.getElementById('custom-purpose-field');
                    const customPurposeInput = document.getElementById('custom-purpose');
                    const isOther = this.value === 'Otro';
                    customPurposeField.hidden = !isOther;
                    customPurposeInput.required = isOther;
                    if (!isOther) customPurposeInput.value = '';
                });
                .itinerary-item:not(.itinerary-empty):hover {
                    transform: translateY(-4px);
                    border-color: rgba(45, 143, 233, 0.44);
                    box-shadow: 0 20px 38px rgba(45, 108, 174, 0.17), inset 0 1px 0 rgba(255,255,255,0.95);
                        const form = document.getElementById('itinerary-form');
                        const message = document.getElementById('form-message');
                        const firstName = document.getElementById('first-name').value.trim();
                        const lastName = document.getElementById('last-name').value.trim();
                        const originValue = document.getElementById('origin').value;
                        const destinationValue = document.getElementById('destination').value;
                        const originId = originValue ? Number(originValue) : null;
                        const destinationId = destinationValue ? Number(destinationValue) : null;
                .itinerary-card-head,
                .itinerary-card-footer,
                        const travelDate = document.getElementById('date').value;
                        const durationValue = Number(document.getElementById('duration').value);
                        const purposeValue = document.getElementById('purpose').value;
                        const customPurpose = document.getElementById('custom-purpose').value.trim();
                        const submitButton = document.getElementById('submit-itinerary');
                        message.textContent = '';

                        if (!form.reportValidity()) return;
                        if (travelDate < getLocalDateValue() && travelDate !== state.editingTravelDate) {
                            message.textContent = 'La fecha del viaje no puede ser anterior a hoy.';
                            return;
                        }
                        if (!firstName || !lastName) {
                            message.textContent = 'Escribe tu nombre y tus apellidos.';
                            return;
                        }
                        if (originId === destinationId) {
                            message.textContent = 'El origen y el destino deben ser diferentes.';
                            return;
                        }
                        if (!origin || !destination) {
                            message.textContent = 'Selecciona un aeropuerto de origen y uno de destino válidos.';
                            return;
                        }
                        if (!Number.isInteger(durationValue) || durationValue < 1 || durationValue > 10080) {
                            message.textContent = 'Ingresa una duración válida en minutos (entre 1 y 10080).';
                            return;
                        }

                .itinerary-actions,
                .itinerary-details {
                            user_name: `${firstName} ${lastName}`.trim(),
                    justify-content: space-between;
                    align-items: center;
                            travel_date: travelDate,
                            duration_minutes: durationValue,
                            purpose: purposeValue === 'Otro' ? customPurpose : purposeValue
                .itinerary-card-head {
                        if (payload.user_name.length > 120 || !payload.purpose.trim()) {
                            message.textContent = 'Revisa el nombre completo y el motivo del viaje.';
                            submitButton.disabled = false;
                            return;
                        }
                    color: #426888;
                    font-size: 0.72rem;
                    font-weight: 700;
                }

                .itinerary-card-kind,
                .itinerary-date,
                .itinerary-chip {
                    display: inline-flex;
                    align-items: center;
                    gap: 7px;
                    border-radius: 999px;
                    padding: 7px 10px;
                }

                .itinerary-card-kind {
                    background: rgba(89, 169, 255, 0.1);
                    color: #145585;
                }

                .itinerary-date {
                    border: 1px solid rgba(91, 147, 205, 0.17);
                    background: rgba(255,255,255,0.76);
                    color: #4b6680;
                }

                .itinerary-route {
                    display: grid;
                    grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
                    align-items: center;
                    gap: 12px;
                    padding: 18px 16px;
                    border-radius: 17px;
                    background: linear-gradient(110deg, rgba(220,239,255,0.72), rgba(255,255,255,0.86), rgba(222,244,250,0.72));
                }

                .itinerary-airport {
                    min-width: 0;
                }

                .itinerary-airport-label {
                    display: block;
                    margin-bottom: 7px;
                    color: #67839e;
                    font-size: 0.62rem;
                    font-weight: 800;
                    letter-spacing: 0.14em;
                    text-transform: uppercase;
                }

                .itinerary-airport-code {
                    display: block;
                    color: #0f4c81;
                    font-size: clamp(1.1rem, 2vw, 1.4rem);
                    font-weight: 800;
                    letter-spacing: 0.04em;
                }

                .itinerary-airport-name {
                    display: -webkit-box;
                    overflow: hidden;
                    margin-top: 4px;
                    color: #294d6d;
                    font-size: 0.76rem;
                    line-height: 1.45;
                    -webkit-box-orient: vertical;
                    -webkit-line-clamp: 2;
                }

                .itinerary-route-arrow {
                    display: grid;
                    place-items: center;
                    width: 38px;
                    height: 38px;
                    border: 1px solid rgba(65, 149, 219, 0.18);
                    border-radius: 50%;
                    background: #fff;
                    color: #2785ce;
                    font-size: 1.2rem;
                    box-shadow: 0 6px 14px rgba(43, 117, 172, 0.1);
                }

                .itinerary-card-footer {
                    align-items: flex-end;
                }

                .itinerary-details {
                    justify-content: flex-start;
                    flex-wrap: wrap;
                }

                .itinerary-chip {
                    border: 1px solid rgba(83, 137, 190, 0.16);
                    background: rgba(255,255,255,0.8);
                    color: #486784;
                    font-size: 0.7rem;
                    font-weight: 600;
                }

                .itinerary-actions {
                    flex-shrink: 0;
                }

                .itinerary-actions button {
                    display: inline-flex;
                    align-items: center;
                    justify-content: center;
                    gap: 7px;
                    min-height: 40px;
                    padding: 9px 13px;
                    border-radius: 12px;
                    font-size: 0.68rem;
                    letter-spacing: 0.06em;
                    transition: transform 0.18s ease, box-shadow 0.18s ease, background 0.18s ease;
                }

                .itinerary-actions button:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 9px 16px rgba(44, 90, 150, 0.14);
                }

                .itinerary-actions button:focus-visible {
                    outline: 3px solid rgba(45, 143, 233, 0.3);
                    outline-offset: 2px;
                }

                .edit-btn {
                    border: 1px solid rgba(42, 128, 205, 0.24);
                    background: linear-gradient(135deg, #eaf5ff, #d9ecff);
                    color: #145585;
                }

                .itinerary-actions .delete-btn {
                    border: 1px solid rgba(207, 83, 66, 0.22);
                    background: linear-gradient(135deg, #fff1ef, #ffe1dc);
                    color: #a84437;
                    box-shadow: none;
                }

                .itinerary-empty {
                    border-color: rgba(89, 169, 255, 0.26);
                    background: linear-gradient(180deg, rgba(240,247,255,0.96), rgba(221,236,255,0.92));
                    align-items: center;
                    justify-content: center;
                    min-height: 190px;
                    text-align: center;
                }

                .itinerary-empty strong {
                    color: var(--text);
                }

                .itinerary-empty p {
                    max-width: 360px;
                    margin: 0;
                    color: var(--muted);
                }

                .itinerary-empty-icon {
                    display: grid;
                    place-items: center;
                    width: 48px;
                    height: 48px;
                    border-radius: 16px;
                    background: rgba(89, 169, 255, 0.12);
                    color: #145585;
                    font-size: 1.35rem;
                }

                .taskbar {
                    position: fixed;
                    left: 0;
                    right: 0;
                            form.reset();
                            document.getElementById('custom-purpose-field').hidden = true;
                            document.getElementById('custom-purpose').required = false;
                            message.textContent = '';
                    border-top: 1px solid rgba(213, 234, 255, 0.5);
                    backdrop-filter: blur(14px);
                    display: flex;
                            message.textContent = `No se pudo guardar el itinerario: ${error.message}`;
                    align-items: center;
                    justify-content: center;
                    border-radius: 10px;
                    color: white;
                }

                .win-icon {
                    width: 18px;
                    height: 18px;
                    background: linear-gradient(135deg, #dff5ff, #8ac9ff, #3b8fe2);
                    color: #0d355e;
                    font-size: 0.7rem;
                    font-weight: 700;
                    box-shadow: inset 0 1px 0 rgba(255,255,255,0.6);
                }

                .app-pill {
                    appearance: none;
                    height: 34px;
                    padding: 0 12px;
                    background: linear-gradient(135deg, rgba(223, 245, 255, 0.22), rgba(151, 205, 255, 0.3));
                    border: 1px solid rgba(236, 247, 255, 0.38);
                    font-size: 0.72rem;
                    color: #f4fbff;
                    font-weight: 700;
                    letter-spacing: 0.05em;
                    cursor: pointer;
                    transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
                    box-shadow: inset 0 1px 0 rgba(255,255,255,0.24), 0 8px 18px rgba(32, 104, 185, 0.12);
                    font-family: "Poppins", "Segoe UI", sans-serif;
                }

                .app-pill:hover {
                    transform: translateY(-1px);
                    border-color: rgba(255,255,255,0.64);
                    box-shadow: 0 10px 20px rgba(32, 104, 185, 0.18);
                }

                .app-pill__icon {
                    display: inline-flex;
                    align-items: center;
                    justify-content: center;
                    width: 18px;
                    height: 18px;
                    margin-right: 7px;
                    border-radius: 50%;
                    background: linear-gradient(135deg, rgba(255,255,255,0.32), rgba(156, 217, 255, 0.26));
                    color: #f4fbff;
                    font-size: 0.7rem;
                    box-shadow: inset 0 1px 0 rgba(255,255,255,0.2);
                    animation: taskbar-plane 3.2s ease-in-out infinite;
                    transform-origin: center;
                }

                @keyframes taskbar-plane {
                    0% { transform: translateX(-2px) translateY(0px) rotate(-4deg); opacity: 0.8; }
                    25% { transform: translateX(2px) translateY(-1px) rotate(0deg); }
                    50% { transform: translateX(5px) translateY(1px) rotate(4deg); opacity: 1; }
                    75% { transform: translateX(1px) translateY(-1px) rotate(0deg); }
                    100% { transform: translateX(-2px) translateY(0px) rotate(-4deg); opacity: 0.8; }
                }

                .task-dot {
                    width: 8px;
                    height: 8px;
                    border-radius: 50%;
                    background: rgba(255, 255, 255, 0.9);
                    box-shadow: 0 0 12px rgba(255, 255, 255, 0.7);
                }

                @media (max-width: 1080px) {
                    .content-grid {
                        grid-template-columns: 1fr;
                    }

                }

                @media (max-width: 700px) {
                    .viewport {
                        padding: 16px 12px 80px;
                    }

                    .topbar {
                        flex-direction: column;
                        align-items: flex-start;
                    }

                    .badge {
                        width: 100%;
                        min-width: 0;
                    }

                    .itinerary-form {
                        grid-template-columns: 1fr;
                    }

                    .itineraries-heading {
                        align-items: flex-start;
                    }

                    .itineraries-heading p {
                        max-width: 250px;
                    }

                    .itinerary-item {
                        padding: 15px;
                    }

                    .itinerary-route {
                        gap: 8px;
                        padding: 14px 10px;
                    }

                    .itinerary-route-arrow {
                        width: 32px;
                        height: 32px;
                    }

                    .itinerary-date {
                        max-width: 48%;
                        overflow: hidden;
                        text-overflow: ellipsis;
                        white-space: nowrap;
                    }

                    .itinerary-card-footer {
                        align-items: stretch;
                        flex-direction: column;
                    }

                    .itinerary-actions {
                        width: 100%;
                    }

                    .itinerary-actions button {
                        flex: 1;
                    }

                    .map-shell {
                        height: 430px;
                    }
                }

                :root {
                    --accent-violet: #4825e8;
                    --accent-violet-light: #eeeaff;
                    --dashboard-bg: #f3f4ff;
                }

                html,
                body {
                    background: var(--dashboard-bg);
                    color: #17213d;
                }

                .viewport {
                    display: grid;
                    grid-template-columns: 180px minmax(0, 1fr);
                    align-items: stretch;
                    width: 100%;
                    max-width: none;
                    min-height: 100vh;
                    padding: 0;
                    gap: 0;
                }

                .app-sidebar {
                    position: sticky;
                    top: 0;
                    display: flex;
                    flex-direction: column;
                    width: 180px;
                    height: 100vh;
                    min-height: 620px;
                    padding: 25px 14px 20px;
                    overflow: hidden;
                    color: #fff;
                    background-color: #13254b;
                    background-image: linear-gradient(180deg, rgba(14, 30, 65, 0.96) 0%, rgba(24, 48, 101, 0.93) 62%, rgba(43, 74, 151, 0.62) 100%), url("https://images.unsplash.com/photo-1436491865332-7a61a109cc05?auto=format&fit=crop&w=700&q=80");
                    background-repeat: no-repeat;
                    background-position: center, center bottom;
                    background-size: cover, auto 235px;
                    border-right: 1px solid rgba(255, 255, 255, 0.1);
                }

                .sidebar-brand {
                    display: flex;
                    flex-direction: column;
                    gap: 10px;
                    min-height: 118px;
                    padding: 0 8px 18px;
                    border-bottom: 1px solid rgba(219, 234, 254, 0.22);
                    color: #dce7ff;
                    font-size: 0.78rem;
                    line-height: 1.4;
                }

                .sidebar-brand-mark {
                    display: flex;
                    align-items: center;
                    gap: 9px;
                }

                .sidebar-brand-mark span {
                    color: #60a5fa;
                    font-size: 1.65rem;
                    transform: rotate(-18deg);
                }

                .sidebar-brand-mark strong {
                    color: #fff;
                    font-size: 1.8rem;
                    letter-spacing: 0.02em;
                }

                .sidebar-nav {
                    display: grid;
                    gap: 8px;
                    padding-top: 16px;
                }

                .sidebar-link {
                    display: flex;
                    align-items: center;
                    gap: 12px;
                    min-height: 42px;
                    padding: 9px 11px;
                    border: 0;
                    border-radius: 11px;
                    background: transparent;
                    color: #e4ecff;
                    box-shadow: none;
                    font-size: 0.82rem;
                    font-weight: 600;
                    text-align: left;
                    cursor: pointer;
                }

                .sidebar-link:hover,
                .sidebar-link.is-active {
                    background: linear-gradient(105deg, #315af0, #813cf2);
                    color: #fff;
                    box-shadow: 0 8px 18px rgba(30, 36, 117, 0.26);
                    transform: translateY(-1px);
                }

                .sidebar-icon {
                    display: inline-flex;
                    align-items: center;
                    justify-content: center;
                    width: 20px;
                    color: inherit;
                    font-size: 1rem;
                }

                .sidebar-caption {
                    margin-top: auto;
                    padding: 14px 8px 0;
                    border-top: 1px solid rgba(219, 234, 254, 0.22);
                    color: #bdc9eb;
                    font-size: 0.58rem;
                    font-weight: 700;
                    letter-spacing: 0.12em;
                }

                .shell {
                    min-width: 0;
                    max-width: none;
                    min-height: 100vh;
                    padding: 0 12px 24px;
                    overflow: hidden;
                    border: 0;
                    border-radius: 0;
                    background: var(--dashboard-bg);
                    box-shadow: none;
                }

                .topbar {
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    gap: 18px;
                    min-height: 98px;
                    margin: 0;
                    padding: 14px 8px 12px;
                    border: 0;
                    background: transparent;
                }

                .title-wrap {
                    min-width: 220px;
                }

                .eyebrow {
                    margin-bottom: 3px;
                    color: var(--accent-violet);
                    font-size: 0.64rem;
                    letter-spacing: 0.14em;
                }

                .topbar h1 {
                    margin: 0;
                    color: #111a38;
                    font-size: clamp(1.3rem, 2.1vw, 1.8rem);
                    line-height: 1.12;
                    letter-spacing: -0.035em;
                }

                .subtitle {
                    margin-top: 4px;
                    color: #52617e;
                    font-size: 0.78rem;
                    letter-spacing: 0;
                }

                .topbar-status {
                    display: flex;
                    align-items: center;
                    justify-content: flex-end;
                    gap: 10px;
                }

                .badge,
                .signal-box {
                    display: flex;
                    align-items: center;
                    justify-content: flex-start;
                    gap: 9px;
                    min-width: 150px;
                    height: 56px;
                    padding: 8px 12px;
                    border: 1px solid rgba(224, 228, 245, 0.9);
                    border-radius: 999px;
                    background: rgba(255, 255, 255, 0.9);
                    color: #17213d;
                    box-shadow: 0 5px 16px rgba(31, 41, 90, 0.08);
                    font-size: 0.73rem;
                    font-weight: 700;
                    letter-spacing: 0;
                    text-transform: none;
                }

                .badge .plane,
                .signal-symbol {
                    display: inline-flex;
                    flex: 0 0 28px;
                    align-items: center;
                    justify-content: center;
                    width: 28px;
                    height: 28px;
                    border: 0;
                    border-radius: 50%;
                    background: #e5fff5;
                    color: #10b981;
                    box-shadow: none;
                    font-size: 0.9rem;
                }

                .badge small,
                .signal-copy small {
                    display: block;
                    margin-top: 2px;
                    color: #16a34a;
                    font-size: 0.62rem;
                    font-weight: 600;
                }

                .signal-box {
                    min-width: 164px;
                }

                .signal-symbol {
                    background: #eaf0ff;
                    color: #3478ed;
                }

                .signal-copy {
                    flex: 1;
                    white-space: nowrap;
                }

                .signal-dot {
                    flex: 0 0 9px;
                    width: 9px;
                    height: 9px;
                    background: #16a34a;
                    box-shadow: none;
                }

                .clock {
                    display: flex;
                    flex-direction: row;
                    align-items: center;
                    justify-content: center;
                    gap: 10px;
                    min-width: 174px;
                    min-height: 56px;
                    padding: 8px 14px;
                    border: 0;
                    border-radius: 999px;
                    background: linear-gradient(110deg, #304c9a, #172c69);
                    color: #fff;
                    text-align: left;
                    box-shadow: 0 7px 18px rgba(41, 57, 134, 0.2);
                }

                .clock-symbol {
                    display: inline-flex;
                    align-items: center;
                    justify-content: center;
                    width: 34px;
                    height: 34px;
                    border: 1px solid rgba(255, 255, 255, 0.28);
                    border-radius: 50%;
                    background: rgba(140, 171, 255, 0.2);
                    color: #d8e5ff;
                    font-size: 1.25rem;
                }

                .clock-copy {
                    display: grid;
                    gap: 1px;
                }

                .clock-time {
                    color: #fff;
                    font-size: 1.15rem;
                    font-weight: 800;
                    letter-spacing: 0.02em;
                    line-height: 1.15;
                    text-shadow: none;
                }

                .clock-date {
                    margin: 0;
                    color: #d9e3ff;
                    font-size: 0.64rem;
                    font-weight: 500;
                    letter-spacing: 0;
                }

                .content-grid {
                    display: grid;
                    grid-template-columns: minmax(0, 0.95fr) minmax(0, 1.05fr);
                    gap: 16px;
                    align-items: stretch;
                    padding: 0;
                }

                .map-panel,
                .form-panel,
                .route-panel,
                .itineraries-section,
                .airport-section,
                .recommendations {
                    min-width: 0;
                    overflow: hidden;
                    border: 1px solid #e4e7f5;
                    border-radius: 16px;
                    background: linear-gradient(145deg, #fff, #f8f8ff);
                    box-shadow: 0 8px 22px rgba(38, 48, 109, 0.07);
                }

                .map-panel,
                .form-panel {
                    margin: 0;
                }

                .panel-header,
                .form-header {
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    min-height: 50px;
                    padding: 10px 14px;
                    border: 0;
                    border-bottom: 1px solid #eff0fa;
                    background: rgba(255, 255, 255, 0.62);
                    color: #14203f;
                    font-size: 0.88rem;
                    font-weight: 800;
                    letter-spacing: 0;
                    text-transform: none;
                }

                .panel-title {
                    display: inline-flex;
                    align-items: center;
                    gap: 8px;
                }

                .heading-icon {
                    color: var(--accent-violet);
                    font-size: 1rem;
                    font-weight: 800;
                }

                .kpi,
                .airport-badge {
                    display: inline-flex;
                    align-items: center;
                    gap: 6px;
                    padding: 6px 10px;
                    border: 1px solid #e6e2ff;
                    border-radius: 999px;
                    background: var(--accent-violet-light);
                    color: var(--accent-violet);
                    font-size: 0.65rem;
                    font-weight: 800;
                    letter-spacing: 0;
                    white-space: nowrap;
                }

                .map-shell {
                    height: clamp(420px, calc(100vh - 180px), 780px);
                    margin: 0;
                    border: 0;
                    border-radius: 0 0 15px 15px;
                    background: #dce7f2;
                    box-shadow: none;
                }

                #map {
                    filter: saturate(1.04) contrast(1.01);
                }

                .form-panel {
                    display: flex;
                    flex-direction: column;
                    background: linear-gradient(145deg, #fff, #f2f1ff);
                }

                .form-header {
                    min-height: 50px;
                    background: transparent;
                }

                #route-status {
                    max-width: 50%;
                    overflow: hidden;
                    padding: 5px 9px;
                    border-radius: 999px;
                    background: var(--accent-violet-light);
                    color: var(--accent-violet);
                    font-size: 0.64rem;
                    text-overflow: ellipsis;
                    white-space: nowrap;
                }

                .itinerary-form {
                    display: grid;
                    grid-template-columns: repeat(6, minmax(0, 1fr));
                    align-content: start;
                    gap: 9px 10px;
                    padding: 10px 14px 14px;
                    background: transparent;
                }

                .itinerary-form .field:first-child {
                    grid-column: 1 / -1;
                }

                .itinerary-form .field:nth-child(2),
                .itinerary-form .field:nth-child(3) {
                    grid-column: span 3;
                }

                .itinerary-form .field:nth-child(4),
                .itinerary-form .field:nth-child(5),
                .itinerary-form .field:nth-child(6) {
                    grid-column: span 2;
                }

                .field {
                    gap: 4px;
                    min-width: 0;
                }

                .field.full {
                    grid-column: 1 / -1;
                }

                label {
                    color: #34415f;
                    font-size: 0.66rem;
                    font-weight: 700;
                    letter-spacing: 0;
                    text-transform: none;
                }

                select,
                input {
                    min-width: 0;
                    min-height: 35px;
                    padding: 7px 10px;
                    border: 1px solid #d8d8f5;
                    border-radius: 9px;
                    background: rgba(255, 255, 255, 0.78);
                    color: #1c2745;
                    font-size: 0.72rem;
                    box-shadow: none;
                }

                .date-field input[type="date"] {
                    min-height: 35px;
                    padding: 7px 8px;
                    font-size: 0.68rem;
                }

                select:focus,
                input:focus {
                    border-color: #8062f1;
                    box-shadow: 0 0 0 3px rgba(110, 75, 235, 0.12);
                }

                #submit-itinerary {
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: 8px;
                    width: 100%;
                    min-height: 38px;
                    padding: 8px 14px;
                    border: 0;
                    border-radius: 999px;
                    background: linear-gradient(100deg, #874cf1, #3514cb);
                    color: #fff;
                    font-size: 0.74rem;
                    font-weight: 800;
                    letter-spacing: 0;
                    text-transform: none;
                    box-shadow: 0 7px 16px rgba(77, 42, 206, 0.2);
                }

                #submit-itinerary:hover {
                    background: linear-gradient(100deg, #7540e2, #2910b3);
                }

                .button-plane {
                    font-size: 0.95rem;
                }

                .route-itinerary-grid {
                    display: grid;
                    grid-template-columns: minmax(0, 0.85fr) minmax(0, 1.2fr);
                    gap: 16px;
                    margin-top: 16px;
                }

                .route-panel,
                .itineraries-section {
                    margin: 0;
                    padding: 0;
                }

                .section-title {
                    display: flex;
                    align-items: center;
                    gap: 9px;
                    min-height: 46px;
                    padding: 10px 14px;
                    color: #14203f;
                    font-size: 0.85rem;
                    font-weight: 800;
                }

                .route-summary {
                    display: grid;
                    grid-template-columns: minmax(0, 1.2fr) minmax(72px, 0.62fr) minmax(90px, 0.82fr);
                    gap: 0;
                    margin: 0;
                    padding: 0 10px 8px;
                }

                .route-pill {
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    min-width: 0;
                    min-height: 88px;
                    padding: 10px 11px;
                    border: 0;
                    border-right: 1px solid #e9e9f4;
                    border-radius: 0;
                    background: transparent;
                    box-shadow: none;
                }

                .route-pill:last-child {
                    border-right: 0;
                }

                .route-pill-label {
                    margin-bottom: 4px;
                    color: #687694;
                    font-size: 0.63rem;
                    letter-spacing: 0;
                }

                .route-pill-value {
                    overflow-wrap: anywhere;
                    color: #101a37;
                    font-size: 0.72rem;
                    line-height: 1.25;
                }

                .route-pill:first-child .route-pill-value {
                    color: #101a37;
                    font-size: clamp(1.1rem, 1.8vw, 1.6rem);
                    font-weight: 800;
                    white-space: nowrap;
                }

                .itineraries-heading {
                    min-height: 46px;
                    padding: 8px 14px;
                }

                .itineraries-heading h2 {
                    margin: 0;
                    color: #14203f;
                    font-size: 0.85rem;
                    letter-spacing: 0;
                }

                .itineraries-eyebrow,
                .itineraries-heading p {
                    display: none;
                }

                .itinerary-count {
                    padding: 6px 10px;
                    border: 1px solid #e6e2ff;
                    background: var(--accent-violet-light);
                    color: var(--accent-violet);
                    font-size: 0.65rem;
                }

                .itinerary-list {
                    margin: 0;
                    padding: 0 12px 8px;
                    gap: 0;
                    border: 0;
                    border-radius: 0;
                    background: transparent;
                    box-shadow: none;
                }

                .itinerary-item {
                    padding: 9px 4px;
                    border: 0;
                    border-bottom: 1px solid #eeeff7;
                    border-radius: 0;
                    background: transparent;
                    box-shadow: none;
                }

                .itinerary-item:last-child {
                    border-bottom: 0;
                }

                .itinerary-route {
                    padding: 8px 10px;
                    border-radius: 10px;
                    background: #f6f7ff;
                }

                .itinerary-airport-code,
                .itinerary-route-arrow {
                    color: var(--accent-violet);
                }

                .itinerary-actions button {
                    min-height: 34px;
                    padding: 7px 10px;
                    border-radius: 999px;
                    letter-spacing: 0;
                    text-transform: none;
                }

                .airport-section {
                    margin-top: 16px;
                    padding: 0 0 10px;
                }

                .airport-section-head {
                    min-height: 46px;
                    margin: 0;
                    padding: 8px 14px;
                }

                .airport-section-head h2 {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    color: #14203f;
                    font-size: 0.9rem;
                }

                .airport-grid {
                    display: grid;
                    grid-template-columns: repeat(4, minmax(0, 1fr));
                    gap: 12px;
                    padding: 0 10px;
                }

                .airport-card {
                    overflow: hidden;
                    border: 1px solid #e5e8f4;
                    border-radius: 13px;
                    background: #fff;
                    box-shadow: 0 5px 13px rgba(31, 41, 90, 0.08);
                }

                .airport-visual {
                    display: flex;
                    align-items: center;
                    justify-content: flex-end;
                    height: 82px;
                    padding: 10px;
                    background: linear-gradient(135deg, #4b7edb, #b5cafa);
                    color: rgba(255, 255, 255, 0.9);
                    font-size: 1.6rem;
                }

                .airport-card:nth-child(4n + 2) .airport-visual {
                    background: linear-gradient(135deg, #e69b57, #f4d18e);
                }

                .airport-card:nth-child(4n + 3) .airport-visual {
                    background: linear-gradient(135deg, #3f8090, #9bd1c0);
                }

                .airport-card:nth-child(4n + 4) .airport-visual {
                    background: linear-gradient(135deg, #6e6db1, #c0b9ed);
                }

                .airport-info {
                    position: relative;
                    min-height: 68px;
                    padding: 8px 11px 10px;
                }

                .airport-code {
                    position: absolute;
                    top: -15px;
                    left: 10px;
                    padding: 4px 8px;
                    border: 0;
                    border-radius: 999px;
                    background: var(--accent-violet);
                    color: #fff;
                    font-size: 0.58rem;
                    font-weight: 800;
                }

                .airport-name {
                    margin: 2px 0 0;
                    color: #17213d;
                    font-size: 0.72rem;
                    line-height: 1.3;
                }

                .airport-meta {
                    margin-top: 3px;
                    color: #687694;
                    font-size: 0.63rem;
                }

                .recommendations {
                    margin: 16px 0 0;
                    padding: 4px 0 14px;
                }

                .recommendations .airport-section-head {
                    margin: 0;
                }

                .recommendation-hero,
                .recommendation-grid {
                    padding: 0 10px;
                }

                .airport-modal {
                    z-index: 3000;
                }

                .taskbar {
                    display: none;
                }

                @media (prefers-reduced-motion: reduce) {
                    *,
                    *::before,
                    *::after {
                        scroll-behavior: auto !important;
                        transition-duration: 0.01ms !important;
                        animation-duration: 0.01ms !important;
                        animation-iteration-count: 1 !important;
                    }
                }

                @media (max-width: 1100px) {
                    .viewport {
                        grid-template-columns: 156px minmax(0, 1fr);
                    }

                    .app-sidebar {
                        width: 156px;
                    }

                    .topbar {
                        align-items: flex-start;
                        flex-direction: column;
                        gap: 10px;
                        padding: 14px 4px 12px;
                    }

                    .topbar-status {
                        width: 100%;
                        justify-content: flex-start;
                    }

                    .badge,
                    .signal-box,
                    .clock {
                        min-width: 0;
                    }

                    .content-grid {
                        grid-template-columns: minmax(0, 1fr);
                    }

                    .map-shell {
                        height: clamp(400px, calc(100vh - 220px), 740px);
                    }

                    .itinerary-form {
                        grid-template-columns: repeat(6, minmax(0, 1fr));
                    }
                }

                @media (max-width: 760px) {
                    .viewport {
                        display: block;
                    }

                    .app-sidebar {
                        display: none;
                    }

                    .shell {
                        min-height: 100vh;
                        padding: 0 10px 20px;
                    }

                    .topbar {
                        min-height: 0;
                        padding: 14px 2px;
                    }

                    .topbar-status {
                        display: grid;
                        grid-template-columns: repeat(2, minmax(0, 1fr));
                    }

                    .badge,
                    .signal-box,
                    .clock {
                        width: 100%;
                        min-width: 0;
                        height: 52px;
                        padding: 7px 9px;
                        font-size: 0.66rem;
                    }

                    .clock {
                        grid-column: 1 / -1;
                        justify-content: flex-start;
                    }

                    .content-grid {
                        gap: 12px;
                    }

                    .map-shell {
                        height: clamp(360px, calc(100vh - 220px), 680px);
                        min-height: 360px;
                    }

                    .itinerary-form {
                        grid-template-columns: repeat(2, minmax(0, 1fr));
                        gap: 10px;
                    }

                    .itinerary-form .field:first-child,
                    .itinerary-form .field:nth-child(2),
                    .itinerary-form .field:nth-child(3),
                    .itinerary-form .field:nth-child(4),
                    .itinerary-form .field:nth-child(5),
                    .itinerary-form .field:nth-child(6) {
                        grid-column: span 1;
                    }

                    .itinerary-form .field:first-child,
                    .itinerary-form .field:nth-child(3),
                    .itinerary-form .field:nth-child(6),
                    .itinerary-form .field.full {
                        grid-column: 1 / -1;
                    }

                    .route-itinerary-grid {
                        grid-template-columns: minmax(0, 1fr);
                        gap: 12px;
                        margin-top: 12px;
                    }

                    .airport-grid {
                        grid-template-columns: repeat(2, minmax(0, 1fr));
                        gap: 9px;
                    }

                    .itinerary-card-footer {
                        align-items: stretch;
                        flex-direction: column;
                    }
                }

                @media (max-width: 420px) {
                    .airport-grid {
                        grid-template-columns: minmax(0, 1fr);
                    }

                    .route-summary {
                        grid-template-columns: 1.1fr 0.75fr 0.9fr;
                        padding-right: 4px;
                        padding-left: 4px;
                    }

                    .route-pill {
                        padding: 8px 6px;
                    }

                    .route-pill:first-child .route-pill-value {
                        font-size: 1rem;
                    }
                }

                .itinerary-form {
                    display: grid;
                    grid-template-columns: minmax(0, 1fr);
                    gap: 0;
                    padding: 0;
                }

                .form-section {
                    grid-column: 1 / -1;
                    padding: 18px 22px;
                    border-bottom: 1px solid #eeeff7;
                }

                .form-section-heading {
                    margin-bottom: 12px;
                    color: #14203f;
                    font-size: 0.85rem;
                    font-weight: 800;
                }

                .form-section-fields {
                    display: grid;
                    grid-template-columns: repeat(2, minmax(0, 1fr));
                    gap: 12px;
                }

                .form-section .field[hidden] {
                    display: none;
                }

                .required-mark {
                    color: #b42318;
                }

                .form-actions {
                    grid-column: 1 / -1;
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    gap: 12px;
                    padding: 14px 22px 18px;
                }

                .form-message {
                    margin: 0;
                    color: #b42318;
                    font-size: 0.78rem;
                }

                .form-message:empty {
                    display: none;
                }

                .form-action-buttons {
                    display: flex;
                    flex-wrap: wrap;
                    justify-content: flex-end;
                    gap: 8px;
                    margin-left: auto;
                }

                .form-action-buttons #submit-itinerary {
                    width: auto;
                    min-width: 190px;
                }

                #cancel-edit {
                    min-height: 38px;
                    padding: 8px 14px;
                    border: 1px solid #d8d8f5;
                    border-radius: 999px;
                    background: #f7f7ff;
                    color: #34415f;
                    font-size: 0.74rem;
                    font-weight: 700;
                }

                @media (max-width: 760px) {
                    .form-section {
                        padding: 16px;
                    }

                    .form-section-fields {
                        grid-template-columns: minmax(0, 1fr);
                    }

                    .form-actions {
                        align-items: stretch;
                        flex-direction: column;
                        padding: 14px 16px 18px;
                    }

                    .form-action-buttons {
                        width: 100%;
                        margin-left: 0;
                    }

                    .form-action-buttons #submit-itinerary,
                    #cancel-edit {
                        flex: 1 1 100%;
                        width: 100%;
                    }
                }
            </style>
        </head>
        <body>
            <div class="viewport">
                <aside class="app-sidebar" aria-label="Navegación principal">
                    <div class="sidebar-brand">
                        <div class="sidebar-brand-mark"><span>✈</span><strong>SIS</strong></div>
                        <span>Sistema de<br />Itinerarios</span>
                    </div>
                    <nav class="sidebar-nav">
                        <button type="button" class="sidebar-link is-active" data-scroll-target="top">
                            <span class="sidebar-icon">⌂</span>Inicio
                        </button>
                        <button type="button" class="sidebar-link" data-scroll-target="itineraries-section">
                            <span class="sidebar-icon">✈</span>Itinerarios
                        </button>
                        <button type="button" class="sidebar-link" data-scroll-target="airport-section">
                            <span class="sidebar-icon">▣</span>Aeropuertos
                        </button>
                        <button type="button" class="sidebar-link" data-scroll-target="recommendation-section">
                            <span class="sidebar-icon">✧</span>Recomendaciones
                        </button>
                    </nav>
                    <div class="sidebar-caption">PLATAFORMA DE VIAJES</div>
                </aside>

                <main class="shell">
                    <header class="topbar">
                        <div class="title-wrap">
                            <div class="eyebrow">Explora Colombia</div>
                            <h1>Sistema de Itinerarios</h1>
                            <div class="subtitle">Encuentra rutas, aeropuertos y crea tu próximo viaje</div>
                        </div>
                        <div class="topbar-status">
                            <div class="badge">
                                <span class="plane">◆</span>
                                <span>Airport Service<small>Servicio de aeropuertos</small></span>
                            </div>
                            <div class="signal-box">
                                <span class="signal-symbol">▰</span>
                                <span class="signal-copy">API Colombia<small id="api-status">Verificando</small></span>
                                <span class="signal-dot" id="api-dot" title="Estado"></span>
                            </div>
                            <div class="clock">
                                <span class="clock-symbol">◷</span>
                                <div class="clock-copy">
                                    <time class="clock-time" id="clock-time">00:00</time>
                                    <span class="clock-date" id="clock-date">2026</span>
                                </div>
                            </div>
                        </div>
                    </header>

                    <div class="content-grid">
                        <section class="map-panel">
                            <div class="panel-header">
                                <span class="panel-title"><span class="heading-icon">⌖</span>Mapa de Colombia</span>
                                <span class="kpi"><span class="heading-icon">✈</span><span id="airport-count">0 aeropuertos</span></span>
                            </div>
                            <div class="map-shell">
                                <div id="map"></div>
                            </div>
                        </section>

                        <section class="form-panel">
                            <div class="form-header">
                                <span class="panel-title"><span class="heading-icon">▣</span>Crear itinerario</span>
                                <span id="route-status">Sin ruta</span>
                            </div>
                            <form class="itinerary-form" id="itinerary-form">
                                <section class="form-section" aria-labelledby="traveler-heading">
                                    <div class="form-section-heading" id="traveler-heading">Información del viajero</div>
                                    <div class="form-section-fields">
                                        <div class="field">
                                            <label for="first-name">Nombre <span class="required-mark">*</span></label>
                                            <input id="first-name" name="first_name" type="text" maxlength="60" autocomplete="given-name" required />
                                        </div>
                                        <div class="field">
                                            <label for="last-name">Apellidos <span class="required-mark">*</span></label>
                                            <input id="last-name" name="last_name" type="text" maxlength="60" autocomplete="family-name" required />
                                        </div>
                                    </div>
                                </section>
                                <section class="form-section" aria-labelledby="trip-heading">
                                    <div class="form-section-heading" id="trip-heading">Detalles del viaje</div>
                                    <div class="form-section-fields">
                                        <div class="field">
                                            <label for="origin">Aeropuerto de origen <span class="required-mark">*</span></label>
                                            <select id="origin" name="origin" required></select>
                                        </div>
                                        <div class="field">
                                            <label for="destination">Aeropuerto de destino <span class="required-mark">*</span></label>
                                            <select id="destination" name="destination" required></select>
                                        </div>
                                        <div class="field">
                                            <label for="date">Fecha del viaje <span class="required-mark">*</span></label>
                                            <input id="date" name="date" type="date" required />
                                        </div>
                                        <div class="field">
                                            <label for="duration">Duración del viaje (minutos) <span class="required-mark">*</span></label>
                                            <input id="duration" name="duration_minutes" type="number" min="1" max="10080" value="90" required />
                                        </div>
                                        <div class="field">
                                            <label for="purpose">Motivo del viaje <span class="required-mark">*</span></label>
                                            <select id="purpose" name="purpose" required>
                                                <option value="">Selecciona un motivo</option>
                                                <option value="Turismo">Turismo</option>
                                                <option value="Vacaciones">Vacaciones</option>
                                                <option value="Trabajo">Trabajo</option>
                                                <option value="Reunión de negocios">Reunión de negocios</option>
                                                <option value="Estudios">Estudios</option>
                                                <option value="Visita familiar">Visita familiar</option>
                                                <option value="Otro">Otro</option>
                                            </select>
                                        </div>
                                        <div class="field" id="custom-purpose-field" hidden>
                                            <label for="custom-purpose">Especifica el motivo <span class="required-mark">*</span></label>
                                            <input id="custom-purpose" name="custom_purpose" type="text" maxlength="120" />
                                        </div>
                                    </div>
                                </section>
                                <div class="form-actions">
                                    <p class="form-message" id="form-message" role="alert" aria-live="polite"></p>
                                    <div class="form-action-buttons">
                                        <button type="submit" id="submit-itinerary"><span class="button-plane">✈</span>Guardar itinerario</button>
                                        <button type="button" id="cancel-edit" style="display:none;">Cancelar edición</button>
                                    </div>
                                </div>
                            </form>
                        </section>
                    </div>

                    <div class="route-itinerary-grid" id="itinerary-overview">
                        <section class="route-panel">
                            <div class="section-title"><span class="heading-icon">⌘</span>Resumen de ruta</div>
                            <div class="route-summary" id="route-summary"></div>
                        </section>
                        <section class="itineraries-section" id="itineraries-section" aria-labelledby="itineraries-title">
                        <div class="itineraries-heading">
                            <div>
                                <span class="itineraries-eyebrow">Tus planes de viaje</span>
                                <h2 id="itineraries-title"><span class="heading-icon">▣</span>Itinerarios registrados</h2>
                                <p>Consulta tus rutas y administra cada viaje desde su tarjeta.</p>
                            </div>
                            <span class="itinerary-count" id="itinerary-count">0 viajes</span>
                        </div>
                        <div class="itinerary-list" id="itinerary-list"></div>
                        </section>
                    </div>

                    <section class="airport-section" id="airport-section">
                        <div class="airport-section-head">
                            <h2><span class="heading-icon">♙</span>Aeropuertos destacados</h2>
                            <span class="airport-badge">Datos de API Colombia</span>
                        </div>
                        <div class="airport-grid" id="airport-grid"></div>
                    </section>

                    <div class="recommendations" id="recommendation-section">
                        <div class="airport-section-head">
                            <h2>Recomendaciones</h2>
                            <span class="airport-badge">Más convenientes</span>
                        </div>
                        <div class="recommendation-hero">
                            <div class="recommendation-hero-card">
                                <img src="https://images.unsplash.com/photo-1436491865332-7a61a109cc05?auto=format&fit=crop&w=900&q=80" alt="Avión en vuelo" />
                                <div class="recommendation-hero-copy">
                                    <span>mejor valor</span>
                                    <strong>Promedios más bajos</strong>
                                </div>
                            </div>
                            <div class="recommendation-hero-card">
                                <img src="https://images.unsplash.com/photo-1542296332-2e4473faf563?auto=format&fit=crop&w=900&q=80" alt="Avión sobre pista" />
                                <div class="recommendation-hero-copy">
                                    <span>horario ideal</span>
                                    <strong>Compras tempranas</strong>
                                </div>
                            </div>
                            <div class="recommendation-hero-card">
                                <img src="https://images.unsplash.com/photo-1529074963764-98f45c47344b?auto=format&fit=crop&w=900&q=80" alt="Avión en aeropuerto" />
                                <div class="recommendation-hero-copy">
                                    <span>mejor día</span>
                                    <strong>Entre semana</strong>
                                </div>
                            </main>
                        </div>
                        <div class="recommendation-grid" id="recommendation-grid"></div>
                    </div>

                    <div class="airport-modal" id="airport-modal" aria-hidden="true">
                        <div class="airport-modal-panel" role="dialog" aria-modal="true" aria-labelledby="airport-modal-title">
                            <div class="airport-modal-header">
                                <h3 id="airport-modal-title">Detalle de ruta</h3>
                                <button type="button" class="airport-modal-close" data-close-airport-modal aria-label="Cerrar información">×</button>
                            </div>
                            <div class="airport-modal-body">
                                <span class="airport-modal-tag" id="airport-modal-tag">Recomendación</span>
                                <p id="airport-modal-text"></p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="taskbar">
                <div class="taskbar-left">
                    <div class="win-icon">◻</div>
                    <button type="button" class="app-pill" data-scroll-target="top">
                        <span class="app-pill__icon">✈</span>
                        Inicio
                    </button>
                    <button type="button" class="app-pill" data-scroll-target="itineraries-section">
                        <span class="app-pill__icon">✈</span>
                        Airport Service
                    </button>
                </div>
                <div class="taskbar-right">
                    <div class="task-dot"></div>
                    <div class="task-dot"></div>
                    <div class="task-dot"></div>
                </div>
            </div>

            <script type="module">
                import * as L from 'leaflet';
                import { maplibreGL } from 'https://unpkg.com/@maplibre/maplibre-gl-leaflet@0.1.4/dist/leaflet-maplibre-gl.mjs';

                const state = {
                    airports: [],
                    itineraries: [],
                    map: null,
                    markersLayer: null,
                    routeLayer: null,
                    editingId: null,
                    editingTravelDate: null
                };

                const COLOMBIA_MAP_BOUNDS = [[-5, -82], [14, -66]];

                function getLocalDateValue(date = new Date()) {
                    const year = date.getFullYear();
                    const month = String(date.getMonth() + 1).padStart(2, '0');
                    const day = String(date.getDate()).padStart(2, '0');
                    return `${year}-${month}-${day}`;
                }

                function updateClock() {
                    const now = new Date();
                    const dateEl = document.getElementById('clock-date');
                    const timeEl = document.getElementById('clock-time');
                    const date = now.toLocaleDateString('es-CO', { day: '2-digit', month: 'short', year: 'numeric' }).toUpperCase();
                    const time = now.toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
                    dateEl.textContent = date;
                    timeEl.textContent = time;
                }

                function setApiState(ok) {
                    const dot = document.getElementById('api-dot');
                    const status = document.getElementById('api-status');
                    dot.style.background = ok ? '#7ae0ab' : '#ff7b60';
                    dot.style.boxShadow = ok ? '0 0 14px rgba(122, 224, 171, 0.9)' : '0 0 14px rgba(255, 123, 96, 0.9)';
                    status.textContent = ok ? 'Conectada' : 'Sin conexión';
                }

                function getAirportById(id) {
                    if (id == null || id === '') return undefined;
                    return state.airports.find(a => Number(a.id) === Number(id));
                }

                function getAirportCoordinates(airport) {
                    if (!airport) return null;

                    const latitude = Number(airport.latitude);
                    const longitude = Number(airport.longitude);
                    const isColombianPosition = (lat, lon) =>
                        Number.isFinite(lat) && Number.isFinite(lon) &&
                        lat >= -5 && lat <= 14 && lon >= -82 && lon <= -66;

                    if (isColombianPosition(latitude, longitude)) return { latitude, longitude };
                    if (isColombianPosition(longitude, latitude)) return { latitude: longitude, longitude: latitude };
                    return null;
                }

                function escapeHtml(value) {
                    return String(value ?? '').replace(/[&<>"']/g, char => ({
                        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
                    })[char]);
                }

                async function apiRequest(url, options = {}) {
                    const response = await fetch(url, options);
                    if (response.status === 204) return null;
                    const body = await response.json().catch(() => ({}));
                    if (!response.ok) {
                        const error = new Error(body?.error?.message || body?.detail || `Error HTTP ${response.status}`);
                        error.status = response.status;
                        error.code = body?.error?.code;
                        throw error;
                    }
                    return body;
                }

                function normalizeAirportCode(value) {
                    const text = String(value ?? '').trim().toUpperCase();
                    if (!text || ['N/A', 'NA', 'NULL', 'NONE'].includes(text)) {
                        return '';
                    }
                    return text;
                }

                function airportDisplayCode(airport) {
                    return normalizeAirportCode(airport?.iata_code) || normalizeAirportCode(airport?.oaci_code) || 'S/C';
                }

                function haversineKm(lat1, lon1, lat2, lon2) {
                    const toRad = value => (value * Math.PI) / 180;
                    const R = 6371;
                    const dLat = toRad(lat2 - lat1);
                    const dLon = toRad(lon2 - lon1);
                    const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
                        Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) *
                        Math.sin(dLon / 2) * Math.sin(dLon / 2);
                    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
                    return R * c;
                }

                function renderRouteSummary(origin, destination) {
                    const summary = document.getElementById('route-summary');
                    const originCoordinates = getAirportCoordinates(origin);
                    const destinationCoordinates = getAirportCoordinates(destination);
                    if (!originCoordinates || !destinationCoordinates) {
                        summary.innerHTML = `
                            <div class="route-pill">
                                <span class="route-pill-label">Ruta</span>
                                <span class="route-pill-value">Sin selección</span>
                            </div>
                            <div class="route-pill">
                                <span class="route-pill-label">Distancia</span>
                                <span class="route-pill-value">--</span>
                            </div>
                            <div class="route-pill">
                                <span class="route-pill-label">Trayecto</span>
                                <span class="route-pill-value">Elige dos aeropuertos</span>
                            </div>
                        `;
                        return;
                    }

                    const km = haversineKm(
                        originCoordinates.latitude,
                        originCoordinates.longitude,
                        destinationCoordinates.latitude,
                        destinationCoordinates.longitude
                    );
                    const originCode = airportDisplayCode(origin);
                    const destinationCode = airportDisplayCode(destination);
                    summary.innerHTML = `
                        <div class="route-pill">
                            <span class="route-pill-label">Ruta</span>
                            <span class="route-pill-value">${originCode} → ${destinationCode}</span>
                        </div>
                        <div class="route-pill">
                            <span class="route-pill-label">Distancia</span>
                            <span class="route-pill-value">${Math.round(km).toLocaleString('es-CO')} km</span>
                        </div>
                        <div class="route-pill">
                            <span class="route-pill-label">Trayecto</span>
                            <span class="route-pill-value">${origin.city || 'Ciudad'} / ${destination.city || 'Ciudad'}</span>
                        </div>
                    `;
                }

                function initMap() {
                    if (state.map) return;

                    const map = L.map('map', {
                        zoomControl: true,
                        scrollWheelZoom: true,
                        attributionControl: true,
                        minZoom: 5,
                        maxZoom: 16
                    }).setView([4.5709, -74.2973], 6);

                    maplibreGL({
                        style: 'https://tiles.openfreemap.org/styles/liberty'
                    }).addTo(map);

                    state.map = map;
                    state.markersLayer = L.layerGroup().addTo(map);
                    state.routeLayer = L.layerGroup().addTo(map);
                }

                function renderMap() {
                    initMap();

                    const originId = Number(document.getElementById('origin').value);
                    const destinationId = Number(document.getElementById('destination').value);
                    const origin = getAirportById(originId);
                    const destination = getAirportById(destinationId);
                    renderRouteSummary(origin, destination);

                    state.markersLayer.clearLayers();
                    state.routeLayer.clearLayers();

                    const points = state.airports
                        .map(airport => ({ airport, coordinates: getAirportCoordinates(airport) }))
                        .filter(point => point.coordinates);
                    const bounds = [];

                    points.forEach(({ airport, coordinates }) => {
                        const selected = Number(airport.id) === originId || Number(airport.id) === destinationId;
                        const coords = [coordinates.latitude, coordinates.longitude];
                        bounds.push(coords);

                        const marker = L.circleMarker(coords, {
                            radius: selected ? 8 : 5,
                            color: selected ? '#8b5cf6' : '#7ae0ab',
                            weight: 2,
                            fillColor: selected ? '#8b5cf6' : '#7ae0ab',
                            fillOpacity: 1
                        }).addTo(state.markersLayer);

                        const codeText = airportDisplayCode(airport);
                        marker.bindTooltip(`<strong>${airport.name}</strong><br>${airport.city || 'Ciudad'} · ${airport.department || 'Departamento'}<br>${codeText}`, {
                            direction: 'top',
                            sticky: true,
                            opacity: 0.96
                        });

                        marker.bindPopup(`<strong>${airport.name}</strong><br>${airport.city || 'Ciudad'}<br>${airport.department || 'Departamento'}<br>${codeText}`);
                    });

                    const originCoordinates = getAirportCoordinates(origin);
                    const destinationCoordinates = getAirportCoordinates(destination);
                    if (origin && destination && origin.id !== destination.id && originCoordinates && destinationCoordinates) {
                        const route = L.polyline([
                            [originCoordinates.latitude, originCoordinates.longitude],
                            [destinationCoordinates.latitude, destinationCoordinates.longitude]
                        ], {
                            color: '#8b5cf6',
                            weight: 2.5,
                            opacity: 0.9,
                            dashArray: '8 8'
                        }).addTo(state.routeLayer);

                        if (state.map) {
                            state.map.fitBounds(route.getBounds(), { padding: [28, 28] });
                        }
                    } else if (bounds.length) {
                        state.map.fitBounds(COLOMBIA_MAP_BOUNDS, { padding: [28, 28] });
                    } else {
                        state.map.setView([4.5709, -74.2973], 6);
                    }
                }

                function renderMapFallback() {
                    if (state.map) {
                        renderMap();
                        return;
                    }
                    initMap();
                    renderMap();
                }

                function bindTaskbarActions() {
                    document.querySelectorAll('[data-scroll-target]').forEach((button) => {
                        button.addEventListener('click', () => {
                            const target = button.dataset.scrollTarget;
                            const element = target === 'top' ? document.querySelector('.shell') : document.getElementById(target);
                            if (element) {
                                element.scrollIntoView({ behavior: 'smooth', block: 'start' });
                            }
                        });
                    });
                }

                function renderAirportHighlights(airports) {
                    const grid = document.getElementById('airport-grid');
                    if (!grid) return;

                    grid.innerHTML = airports.slice(0, 4).map((airport) => {
                        const location = [airport.city, airport.department].filter(Boolean).join(' · ') || 'Colombia';
                        return `
                            <article class="airport-card">
                                <div class="airport-visual" aria-hidden="true"><span>✈</span></div>
                                <div class="airport-info">
                                    <span class="airport-code">${escapeHtml(airportDisplayCode(airport))}</span>
                                    <h3 class="airport-name">${escapeHtml(airport.name)}</h3>
                                    <div class="airport-meta">${escapeHtml(location)}</div>
                                </div>
                            </article>
                        `;
                    }).join('');
                }

                function renderRecommendations() {
                    const grid = document.getElementById('recommendation-grid');
                    if (!grid || !state.airports.length) return;

                    const airportsByCity = new Map();
                    state.airports.forEach((airport) => {
                        const cityKey = (airport.city || '').toLowerCase();
                        if (cityKey) airportsByCity.set(cityKey, airport);
                    });

                    const routePresets = [
                        { from: 'bogota', to: 'medellin', label: 'Más directo', avgPrice: '$185.000', priceRange: 'Promedio mensual', bestDay: 'Martes', bestWindow: '06:00–10:00', trend: 'Más barato', copy: 'El mejor momento para comprar suele ser a mitad de semana, cuando el precio baja y la disponibilidad está más estable.' },
                        { from: 'bogota', to: 'cartagena', label: 'Playa + ciudad', avgPrice: '$235.000', priceRange: 'Promedio fin de semana', bestDay: 'Miércoles', bestWindow: '07:30–09:30', trend: 'Buena oferta', copy: 'Los precios más equilibrados aparecen antes del mediodía y en días de menor densidad turística.' },
                        { from: 'medellin', to: 'barranquilla', label: 'Ruta Caribe', avgPrice: '$210.000', priceRange: 'Promedio Caribe', bestDay: 'Jueves', bestWindow: '08:00–11:00', trend: 'Muy estable', copy: 'La mejor ventana suele llegar entre semana, con tarifas de compra más predecibles y menos presión de demanda.' },
                        { from: 'cali', to: 'bogota', label: 'Eje central', avgPrice: '$170.000', priceRange: 'Promedio semanal', bestDay: 'Lunes', bestWindow: '05:30–08:30', trend: 'Precio bajo', copy: 'Es la ruta con mejor valor relativo en promedio y suele ser más económica si compras con anticipación y en horas tempranas.' },
                        { from: 'pereira', to: 'cartagena', label: 'Turismo y escala', avgPrice: '$240.000', priceRange: 'Promedio nacional', bestDay: 'Martes', bestWindow: '06:15–09:15', trend: 'Ahorro medio', copy: 'Suele ser una de las rutas con mayor variación, pero el mejor calce ocurre en horarios matutinos y entre semana.' },
                        { from: 'bucaramanga', to: 'bogota', label: 'Conexión norte', avgPrice: '$165.000', priceRange: 'Promedio regional', bestDay: 'Miércoles', bestWindow: '07:00–09:45', trend: 'Buen valor', copy: 'Tiene un buen balance entre precio y conveniencia; los mejores momentos de compra suelen aparecer en la mañana.' }
                    ];

                    const cards = routePresets.map((route) => {
                        const fromAirport = airportsByCity.get(route.from) || state.airports[0];
                        const toAirport = airportsByCity.get(route.to) || state.airports[1] || state.airports[0];
                        const distance = fromAirport && toAirport && fromAirport.latitude != null && fromAirport.longitude != null && toAirport.latitude != null && toAirport.longitude != null
                            ? haversineKm(fromAirport.latitude, fromAirport.longitude, toAirport.latitude, toAirport.longitude)
                            : 0;

                        return `
                            <article class="recommendation-card" data-route-label="${route.label}" data-route-price="${route.avgPrice}" data-route-from="${(fromAirport?.city || 'Bogotá')}" data-route-to="${(toAirport?.city || 'Medellín')}" data-route-bestday="${route.bestDay}" data-route-window="${route.bestWindow}" data-route-range="${route.priceRange}" data-route-copy="${route.copy.replace(/"/g, '&quot;')}" data-route-trend="${route.trend}">
                                <div class="recommendation-top">
                                    <span class="recommendation-badge">${route.label}</span>
                                    <span class="recommendation-price">${route.avgPrice}</span>
                                </div>
                                <p class="recommendation-route">${(fromAirport?.city || 'Bogotá')} → ${(toAirport?.city || 'Medellín')}</p>
                                <div class="recommendation-meta">
                                    <span class="recommendation-pill">Promedio ${route.avgPrice}</span>
                                    <span class="recommendation-pill">Mejor día ${route.bestDay}</span>
                                    <span class="recommendation-pill">${route.bestWindow}</span>
                                </div>
                                <p class="recommendation-copy">${route.copy}</p>
                                <div class="recommendation-footer">
                                    <span class="recommendation-trend">${route.trend}</span>
                                    <button type="button" class="recommendation-action">Ver detalle</button>
                                </div>
                            </article>
                        `;
                    }).join('');

                    grid.innerHTML = cards;

                    grid.querySelectorAll('.recommendation-card').forEach((card) => {
                        card.addEventListener('click', () => {
                            const routeLabel = card.dataset.routeLabel;
                            const fromCity = card.dataset.routeFrom;
                            const toCity = card.dataset.routeTo;
                            const routePrice = card.dataset.routePrice;
                            const bestDay = card.dataset.routeBestday;
                            const bestWindow = card.dataset.routeWindow;
                            const priceRange = card.dataset.routeRange;
                            const routeCopy = card.dataset.routeCopy;
                            const trend = card.dataset.routeTrend;

                            const modal = document.getElementById('airport-modal');
                            const title = document.getElementById('airport-modal-title');
                            const tag = document.getElementById('airport-modal-tag');
                            const text = document.getElementById('airport-modal-text');

                            title.textContent = `${routeLabel} · ${fromCity} → ${toCity}`;
                            tag.textContent = 'Promedio de compra';
                            text.innerHTML = `
                                <strong style="font-size:1.1rem; color:#113d69;">${routePrice}</strong><br>
                                <span style="display:block; margin-top:8px; color:#2d5b84;">Rango estimado: ${priceRange}</span>
                                <span style="display:block; margin-top:6px; color:#2d5b84;">Mejor día para comprar: ${bestDay}</span>
                                <span style="display:block; margin-top:6px; color:#2d5b84;">Horario ideal: ${bestWindow}</span>
                                <span style="display:block; margin-top:6px; color:#2d5b84;">Señal: ${trend}</span>
                                <p style="margin-top:12px; line-height:1.7; color:#486784;">${routeCopy}</p>
                            `;
                            modal.classList.add('is-open');
                            modal.setAttribute('aria-hidden', 'false');
                        });
                    });

                    document.querySelector('[data-close-airport-modal]')?.addEventListener('click', closeAirportModal);
                    document.getElementById('airport-modal')?.addEventListener('click', (event) => {
                        if (event.target === event.currentTarget) closeAirportModal();
                    });
                }

                function closeAirportModal() {
                    const modal = document.getElementById('airport-modal');
                    modal.classList.remove('is-open');
                    modal.setAttribute('aria-hidden', 'true');
                }

                function populateSelectors(airports) {
                    const origin = document.getElementById('origin');
                    const destination = document.getElementById('destination');
                    const options = airports.map(airport => `<option value="${airport.id}">${escapeHtml(airport.name)} (${airportDisplayCode(airport)})</option>`).join('');
                    origin.innerHTML = `<option value="">Selecciona un aeropuerto</option>${options}`;
                    destination.innerHTML = `<option value="">Selecciona un aeropuerto</option>${options}`;

                    updateRoute();
                }

                function updateRoute() {
                    const originValue = document.getElementById('origin').value;
                    const destinationValue = document.getElementById('destination').value;
                    const originId = originValue ? Number(originValue) : null;
                    const destinationId = destinationValue ? Number(destinationValue) : null;
                    const origin = getAirportById(originId);
                    const destination = getAirportById(destinationId);
                    const routeStatusEl = document.getElementById('route-status');
                    const originCoordinates = getAirportCoordinates(origin);
                    const destinationCoordinates = getAirportCoordinates(destination);

                    if (!origin || !destination || origin.id === destination.id || !originCoordinates || !destinationCoordinates) {
                        routeStatusEl.textContent = origin && destination && origin.id === destination.id
                            ? 'Selecciona aeropuertos diferentes'
                            : origin && destination && (!originCoordinates || !destinationCoordinates)
                                ? 'Coordenadas no disponibles'
                                : 'Sin ruta';
                        renderMap();
                        return;
                    }

                    routeStatusEl.textContent = `${airportDisplayCode(origin)} → ${airportDisplayCode(destination)}`;
                    renderMap();
                }

                function renderItineraries() {
                    const list = document.getElementById('itinerary-list');
                    const count = document.getElementById('itinerary-count');
                    count.textContent = `${state.itineraries.length} ${state.itineraries.length === 1 ? 'viaje' : 'viajes'}`;
                    if (!state.itineraries.length) {
                        list.innerHTML = '<div class="itinerary-item itinerary-empty"><span class="itinerary-empty-icon" aria-hidden="true">✈</span><strong>Aún no tienes itinerarios</strong><p>Completa el formulario de arriba y guarda tu primera ruta para verla aquí.</p></div>';
                        return;
                    }

                    list.innerHTML = state.itineraries.map(item => {
                        const origin = getAirportById(item.origin_airport_id);
                        const destination = getAirportById(item.destination_airport_id);
                        const originCode = origin ? airportDisplayCode(origin) : `#${item.origin_airport_id}`;
                        const destinationCode = destination ? airportDisplayCode(destination) : `#${item.destination_airport_id}`;
                        const originName = origin?.name || `Aeropuerto ${item.origin_airport_id}`;
                        const destinationName = destination?.name || `Aeropuerto ${item.destination_airport_id}`;
                        const purposeChip = item.purpose ? `<span class="itinerary-chip">✦ ${escapeHtml(item.purpose)}</span>` : '';
                        return `
                        <article class="itinerary-item" data-itinerary-id="${item.id}">
                            <div class="itinerary-card-head">
                                <span class="itinerary-card-kind">✈ Viaje personal</span>
                                <span class="itinerary-date">▦ ${escapeHtml(item.travel_date)}</span>
                            </div>
                            <div class="itinerary-route">
                                <div class="itinerary-airport">
                                    <span class="itinerary-airport-label">Origen</span>
                                    <strong class="itinerary-airport-code">${escapeHtml(originCode)}</strong>
                                    <span class="itinerary-airport-name">${escapeHtml(originName)}</span>
                                </div>
                                <span class="itinerary-route-arrow" aria-label="hacia">→</span>
                                <div class="itinerary-airport">
                                    <span class="itinerary-airport-label">Destino</span>
                                    <strong class="itinerary-airport-code">${escapeHtml(destinationCode)}</strong>
                                    <span class="itinerary-airport-name">${escapeHtml(destinationName)}</span>
                                </div>
                            </div>
                            <div class="itinerary-card-footer">
                                <div class="itinerary-details">
                                    <span class="itinerary-chip">◷ ${escapeHtml(item.duration_minutes)} min</span>
                                    <span class="itinerary-chip">♙ ${escapeHtml(item.user_name)}</span>
                                    ${purposeChip}
                                </div>
                                <div class="itinerary-actions">
                                    <button type="button" class="edit-btn" data-id="${item.id}"><span aria-hidden="true">✎</span> Editar</button>
                                    <button type="button" class="delete-btn" data-id="${item.id}"><span aria-hidden="true">×</span> Eliminar</button>
                                </div>
                            </div>
                        </article>
                    `;
                    }).join('');
                }

                function populateFormForEdit(itinerary) {
                    if (!itinerary) return;
                    state.editingId = itinerary.id;
                    const originSelect = document.getElementById('origin');
                    const destinationSelect = document.getElementById('destination');
                    const dateInput = document.getElementById('date');
                    const purposeInput = document.getElementById('purpose');
                    const submitButton = document.getElementById('submit-itinerary');
                    const cancelButton = document.getElementById('cancel-edit');

                    originSelect.value = String(itinerary.origin_airport_id);
                    destinationSelect.value = String(itinerary.destination_airport_id);
                    dateInput.value = itinerary.travel_date || '';
                    document.getElementById('user-name').value = itinerary.user_name || '';
                    document.getElementById('duration').value = itinerary.duration_minutes || 90;
                    purposeInput.value = itinerary.purpose || '';
                    submitButton.textContent = 'Guardar cambios';
                    cancelButton.style.display = 'inline-block';
                    updateRoute();
                }

                function resetFormMode() {
                    state.editingId = null;
                    const submitButton = document.getElementById('submit-itinerary');
                    const cancelButton = document.getElementById('cancel-edit');
                    submitButton.textContent = 'Guardar itinerario';
                    cancelButton.style.display = 'none';
                }

                document.getElementById('itinerary-form').addEventListener('submit', function (event) {
                    event.preventDefault();
                    (async () => {
                        const originId = Number(document.getElementById('origin').value);
                        const destinationId = Number(document.getElementById('destination').value);
                        const origin = getAirportById(originId);
                        const destination = getAirportById(destinationId);
                        if (!origin || !destination) return;
                        if (originId === destinationId) {
                            window.alert('El origen y el destino deben ser diferentes.');
                            return;
                        }

                        const submitButton = document.getElementById('submit-itinerary');
                        submitButton.disabled = true;
                        const payload = {
                            user_name: document.getElementById('user-name').value.trim(),
                            origin_airport_id: originId,
                            destination_airport_id: destinationId,
                            travel_date: document.getElementById('date').value,
                            duration_minutes: Number(document.getElementById('duration').value),
                            purpose: document.getElementById('purpose').value.trim()
                        };
                        const isEditing = state.editingId !== null;
                        try {
                            await apiRequest(
                                isEditing ? `/api/itineraries/${state.editingId}` : '/api/itineraries',
                                {
                                    method: isEditing ? 'PATCH' : 'POST',
                                    headers: { 'Content-Type': 'application/json' },
                                    body: JSON.stringify(payload)
                                }
                            );
                            await loadItineraries();
                            document.getElementById('itinerary-form').reset();
                            document.getElementById('user-name').value = 'Julian';
                            document.getElementById('duration').value = '90';
                            resetFormMode();
                            updateRoute();
                        } catch (error) {
                            if (isEditing && error.status === 404) {
                                try {
                                    await loadItineraries();
                                } catch (_) {
                                    // El formulario también debe salir del modo de edición si la lista no responde.
                                }
                                document.getElementById('itinerary-form').reset();
                                document.getElementById('user-name').value = 'Julian';
                                document.getElementById('duration').value = '90';
                                resetFormMode();
                                updateRoute();
                                window.alert('Este itinerario ya no existe. Actualicé la lista; puedes crear uno nuevo.');
                            } else {
                                window.alert(`No se pudo guardar el itinerario: ${error.message}`);
                            }
                        } finally {
                            submitButton.disabled = false;
                        }
                    })();
                });

                document.getElementById('cancel-edit').addEventListener('click', function () {
                    resetFormMode();
                    document.getElementById('itinerary-form').reset();
                    document.getElementById('custom-purpose-field').hidden = true;
                    document.getElementById('custom-purpose').required = false;
                    document.getElementById('form-message').textContent = '';
                    updateRoute();
                });

                document.getElementById('itinerary-list').addEventListener('click', function (event) {
                    const button = event.target.closest('.delete-btn');
                    if (button) {
                        const itineraryId = Number(button.dataset.id);
                        if (!Number.isInteger(itineraryId) || itineraryId < 1) return;
                        if (!window.confirm('¿Eliminar este itinerario?')) return;
                        apiRequest(`/api/itineraries/${itineraryId}`, { method: 'DELETE' })
                            .then(loadItineraries)
                            .catch(error => window.alert(`No se pudo eliminar: ${error.message}`));
                        return;
                    }

                    const editButton = event.target.closest('.edit-btn');
                    if (!editButton) return;

                    const itineraryId = Number(editButton.dataset.id);
                    const itinerary = state.itineraries.find(item => Number(item.id) === itineraryId);
                    if (itinerary) populateFormForEdit(itinerary);
                });

                async function loadItineraries() {
                    state.itineraries = await apiRequest('/api/itineraries');
                    renderItineraries();
                }

                document.getElementById('origin').addEventListener('change', updateRoute);
                document.getElementById('destination').addEventListener('change', updateRoute);

                async function loadAirports() {
                    try {
                        const res = await fetch('/api/airports');
                        if (!res.ok) throw new Error('Falló la API');
                        const airports = await res.json();
                        state.airports = airports;
                        setApiState(true);
                        document.getElementById('airport-count').textContent = `${airports.length} aeropuertos`;
                        renderAirportHighlights(airports);
                        renderRecommendations();
                        populateSelectors(airports);
                    } catch (error) {
                        setApiState(false);
                        document.getElementById('airport-count').textContent = 'API error';
                        renderMapFallback();
                        return;
                    }
                    try {
                        await loadItineraries();
                    } catch (error) {
                        document.getElementById('itinerary-list').innerHTML = '<div class="itinerary-item itinerary-empty"><span class="itinerary-empty-icon" aria-hidden="true">!</span><strong>No se pudieron cargar tus itinerarios</strong><p>Revisa que Itinerary Service esté disponible e inténtalo de nuevo.</p></div>';
                    }
                }

                updateClock();
                document.getElementById('date').min = getLocalDateValue();
                setInterval(updateClock, 1000);
                bindTaskbarActions();
                initMap();
                loadAirports();
                window.addEventListener('resize', () => {
                    if (state.map) {
                        state.map.invalidateSize();
                    }
                });
            </script>
        </body>
        </html>
        """
    )


@app.get("/api/airports", response_model=list[AirportItem], include_in_schema=False)
async def list_airports() -> list[AirportItem]:
    return await fetch_airports()


@app.get(
    "/api/airports/{airport_id}", response_model=AirportItem, include_in_schema=False
)
async def get_airport(airport_id: int) -> AirportItem:
    for airport in await fetch_airports():
        if airport.id == airport_id:
            return airport
    raise HTTPException(status_code=404, detail="Airport not found")


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", str(DEFAULT_PORT)))
    uvicorn.run("main:app", host="127.0.0.1", port=port, reload=True)

