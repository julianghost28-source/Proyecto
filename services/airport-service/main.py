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

                .airport-grid {
                    display: grid;
                    grid-template-columns: repeat(4, minmax(180px, 1fr));
                    gap: 18px;
                    margin-top: 10px;
                }

                .airport-card {
                    background: linear-gradient(180deg, rgba(255,255,255,0.96), rgba(238,246,255,0.96));
                    border: 1px solid rgba(96, 152, 224, 0.18);
                    border-radius: 20px;
                    overflow: hidden;
                    box-shadow: 0 16px 30px rgba(43, 93, 153, 0.1);
                    transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
                    cursor: pointer;
                }

                .airport-card:hover {
                    transform: translateY(-2px);
                    border-color: rgba(59, 146, 255, 0.28);
                    box-shadow: 0 20px 36px rgba(39, 96, 167, 0.14);
                }

                .airport-card:focus-visible {
                    outline: 3px solid rgba(89, 169, 255, 0.35);
                    outline-offset: 3px;
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

                .airport-visual {
                    position: relative;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    width: 100%;
                    height: 136px;
                    overflow: hidden;
                    font-size: 2rem;
                    background: linear-gradient(135deg, #dff2ff 0%, #bfdcff 38%, #8fbef9 100%);
                }

                .airport-visual::before {
                    content: "";
                    position: absolute;
                    inset: 0;
                    background: linear-gradient(180deg, rgba(255,255,255,0.14), rgba(21, 58, 98, 0.12));
                    z-index: 1;
                }

                .airport-visual img {
                    position: absolute;
                    inset: 0;
                    width: 100%;
                    height: 100%;
                    object-fit: cover;
                    object-position: center;
                    display: block;
                }

                .airport-pin {
                    position: relative;
                    z-index: 1;
                    width: 62px;
                    height: 62px;
                    border-radius: 50%;
                    display: inline-flex;
                    align-items: center;
                    justify-content: center;
                    background: rgba(11, 63, 108, 0.9);
                    border: 1px solid rgba(255,255,255,0.24);
                    color: #f8d27a;
                    box-shadow: 0 14px 24px rgba(14, 84, 151, 0.2), 0 0 18px rgba(248, 210, 122, 0.25);
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

                .airport-info {
                    padding: 14px 14px 16px;
                }

                .airport-code {
                    display: inline-block;
                    font-size: 0.68rem;
                    letter-spacing: 0.14em;
                    font-weight: 800;
                    border-radius: 999px;
                    background: rgba(89, 169, 255, 0.08);
                    border: 1px solid rgba(86, 146, 214, 0.18);
                    color: #134d77;
                    padding: 6px 10px;
                    text-transform: uppercase;
                }

                .airport-name {
                    margin: 12px 0 0;
                    font-size: 1rem;
                    line-height: 1.35;
                    color: #123b5d;
                }

                .airport-meta {
                    margin-top: 8px;
                    color: #4e6f8f;
                    font-size: 0.8rem;
                }

                .itinerary-list {
                    margin-top: 18px;
                    display: grid;
                    gap: 12px;
                }

                .itinerary-item {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    gap: 14px;
                    padding: 12px 16px;
                    border: 1px solid var(--line);
                    border-radius: 14px;
                    background: linear-gradient(180deg, rgba(255,255,255,0.9), rgba(232,242,255,0.92));
                    color: var(--text);
                    box-shadow: 0 8px 22px rgba(50, 82, 120, 0.08);
                }

                .itinerary-item strong {
                    color: var(--text);
                }

                .itinerary-empty {
                    border-color: rgba(89, 169, 255, 0.26);
                    background: linear-gradient(180deg, rgba(240,247,255,0.96), rgba(221,236,255,0.92));
                }

                .itinerary-empty strong {
                    color: var(--text);
                }

                .itinerary-empty span:last-child {
                    color: var(--muted);
                }

                .itinerary-copy {
                    display: grid;
                    gap: 4px;
                }

                .itinerary-meta {
                    color: var(--muted);
                    font-size: 0.8rem;
                }

                .delete-btn {
                    border: 1px solid rgba(255, 123, 96, 0.36);
                    background: rgba(255, 123, 96, 0.12);
                    color: #ffd6ce;
                    padding: 8px 12px;
                    border-radius: 10px;
                    cursor: pointer;
                    font-size: 0.75rem;
                    font-weight: 700;
                    letter-spacing: 0.08em;
                    text-transform: uppercase;
                }

                .taskbar {
                    position: fixed;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    height: 52px;
                    background: linear-gradient(180deg, rgba(64, 124, 206, 0.95), rgba(33, 92, 175, 0.96));
                    border-top: 1px solid rgba(213, 234, 255, 0.5);
                    backdrop-filter: blur(14px);
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    padding: 0 18px;
                    z-index: 10;
                    box-shadow: 0 -10px 20px rgba(44, 90, 160, 0.18);
                }

                .taskbar-left, .taskbar-right {
                    display: flex;
                    align-items: center;
                    gap: 12px;
                }

                .win-icon, .app-pill, .task-dot {
                    display: inline-flex;
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

                    .airport-grid {
                        grid-template-columns: repeat(2, minmax(180px, 1fr));
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

                    .airport-grid {
                        grid-template-columns: 1fr;
                    }

                    .map-shell {
                        height: 430px;
                    }
                }
            </style>
        </head>
        <body>
            <div class="viewport">
                <div class="shell">
                    <header class="topbar">
                        <div class="title-wrap">
                            <div class="eyebrow">Airport Service</div>
                            <h1>Sistema de Itinerarios Personales</h1>
                            <div class="subtitle">Servicio de aeropuertos · Colombia</div>
                        </div>
                        <div class="badge"><span class="plane">✈</span> Airport Service</div>
                    </header>

                    <div class="content-grid">
                        <section class="map-panel">
                            <div class="panel-header">
                                <span>Mapa de Colombia</span>
                                <span class="kpi" id="airport-count">0 registros</span>
                            </div>
                            <div class="map-shell">
                                <div id="map"></div>
                            </div>
                        </section>

                        <aside class="side-panel">
                            <div class="clock">
                                <div class="clock-label">Colombia</div>
                                <div class="clock-date" id="clock-date">2026</div>
                                <div class="clock-time" id="clock-time">00:00</div>
                            </div>
                            <div class="signal-box">
                                <span>API Colombia</span>
                                <span class="signal-dot" id="api-dot" title="Estado"></span>
                            </div>
                        </aside>
                    </div>

                    <section class="form-panel">
                        <div class="form-header">
                            <span>Crear itinerario</span>
                            <span id="route-status">Sin ruta</span>
                        </div>
                        <form class="itinerary-form" id="itinerary-form">
                            <div class="field">
                                <label for="origin">Origen</label>
                                <select id="origin" name="origin"></select>
                            </div>
                            <div class="field">
                                <label for="destination">Destino</label>
                                <select id="destination" name="destination"></select>
                            </div>
                            <div class="field date-field">
                                <label for="date">Fecha</label>
                                <input id="date" name="date" type="date" />
                            </div>
                            <div class="field">
                                <label for="purpose">Motivo</label>
                                <input id="purpose" name="purpose" type="text" placeholder="Trabajo, turismo, reunión..." />
                            </div>
                            <div class="field full">
                                <button type="submit" id="submit-itinerary">Guardar itinerario</button>
                                <button type="button" id="cancel-edit" style="display:none; margin-top:10px; background: linear-gradient(135deg, #dfeaf9, #f2f8ff); color: var(--text); border-color: rgba(90,168,255,0.18);">Cancelar edición</button>
                            </div>
                        </form>
                    </section>

                    <div class="route-summary" id="route-summary"></div>

                    <div class="itinerary-list" id="itinerary-list"></div>

                    <div class="airport-section-head" id="airport-section">
                        <h2>Los más visitados</h2>
                        <span class="airport-badge">Top Colombia</span>
                    </div>
                    <div class="airport-grid" id="airport-grid"></div>

                    <div class="recommendations">
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
                            </div>
                        </div>
                        <div class="recommendation-grid" id="recommendation-grid"></div>
                    </div>

                    <div class="airport-modal" id="airport-modal" aria-hidden="true">
                        <div class="airport-modal-panel" role="dialog" aria-modal="true" aria-labelledby="airport-modal-title">
                            <div class="airport-modal-header">
                                <h3 id="airport-modal-title">Aeropuerto</h3>
                                <button type="button" class="airport-modal-close" data-close-airport-modal aria-label="Cerrar información">×</button>
                            </div>
                            <div class="airport-modal-body">
                                <span class="airport-modal-tag" id="airport-modal-tag">Historia</span>
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
                    <button type="button" class="app-pill" data-scroll-target="airport-section">
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

            <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>
            <script>
                const state = {
                    airports: [],
                    itineraries: JSON.parse(localStorage.getItem('pis-itineraries') || '[]'),
                    map: null,
                    markersLayer: null,
                    routeLayer: null,
                    editingId: null
                };

                function persistItineraries() {
                    localStorage.setItem('pis-itineraries', JSON.stringify(state.itineraries));
                }

                function updateClock() {
                    const now = new Date();
                    const dateEl = document.getElementById('clock-date');
                    const timeEl = document.getElementById('clock-time');
                    const date = now.toLocaleDateString('es-CO', { day: '2-digit', month: 'short', year: 'numeric' }).toUpperCase();
                    const time = now.toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
                    dateEl.textContent = `COLOMBIA, ${date}`;
                    timeEl.textContent = time;
                }

                function setApiState(ok) {
                    const dot = document.getElementById('api-dot');
                    dot.style.background = ok ? '#7ae0ab' : '#ff7b60';
                    dot.style.boxShadow = ok ? '0 0 14px rgba(122, 224, 171, 0.9)' : '0 0 14px rgba(255, 123, 96, 0.9)';
                }

                function getAirportById(id) {
                    return state.airports.find(a => Number(a.id) === Number(id));
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
                    if (!origin || !destination || origin.latitude == null || origin.longitude == null || destination.latitude == null || destination.longitude == null) {
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

                    const km = haversineKm(origin.latitude, origin.longitude, destination.latitude, destination.longitude);
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

                    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                        maxZoom: 18,
                        attribution: '&copy; OpenStreetMap contributors'
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

                    const points = state.airports.filter(airport => airport.latitude != null && airport.longitude != null);
                    const bounds = [];

                    points.forEach((airport) => {
                        const selected = Number(airport.id) === originId || Number(airport.id) === destinationId;
                        const coords = [airport.latitude, airport.longitude];
                        bounds.push(coords);

                        const marker = L.circleMarker(coords, {
                            radius: selected ? 8 : 5,
                            color: selected ? '#f7d37d' : '#7ae0ab',
                            weight: 2,
                            fillColor: selected ? '#f7d37d' : '#7ae0ab',
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

                    if (origin && destination && origin.latitude != null && origin.longitude != null && destination.latitude != null && destination.longitude != null) {
                        const route = L.polyline([
                            [origin.latitude, origin.longitude],
                            [destination.latitude, destination.longitude]
                        ], {
                            color: '#f7d37d',
                            weight: 2.5,
                            opacity: 0.9,
                            dashArray: '8 8'
                        }).addTo(state.routeLayer);

                        if (state.map) {
                            state.map.fitBounds(route.getBounds(), { padding: [28, 28] });
                        }
                    } else if (bounds.length) {
                        state.map.fitBounds(bounds, { padding: [28, 28] });
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
                            const element = target === 'top' ? document.querySelector('.shell') : document.getElementById('airport-section');
                            if (element) {
                                element.scrollIntoView({ behavior: 'smooth', block: 'start' });
                            }
                        });
                    });
                }

                function getAirportImage(airport) {
                    const city = (airport.city || '').toLowerCase();
                    const code = (airport.iata_code || airport.oaci_code || '').toUpperCase();

                    const airportImages = {
                        bog: 'https://images.unsplash.com/photo-1436491865332-7a61a109cc05?auto=format&fit=crop&w=900&q=80',
                        mde: 'https://images.unsplash.com/photo-1529074963764-98f45c47344b?auto=format&fit=crop&w=900&q=80',
                        cta: 'https://images.unsplash.com/photo-1517479149777-5f3b1511d5ad?auto=format&fit=crop&w=900&q=80',
                        ctg: 'https://images.unsplash.com/photo-1503220317375-aaad61436b1b?auto=format&fit=crop&w=900&q=80',
                        clo: 'https://images.unsplash.com/photo-1473448912268-2022ce9509d8?auto=format&fit=crop&w=900&q=80',
                        baq: 'https://images.unsplash.com/photo-1520607162513-77705c0f0d4a?auto=format&fit=crop&w=900&q=80',
                        medellin: 'https://images.unsplash.com/photo-1529074963764-98f45c47344b?auto=format&fit=crop&w=900&q=80',
                        bogota: 'https://images.unsplash.com/photo-1436491865332-7a61a109cc05?auto=format&fit=crop&w=900&q=80',
                        cartagena: 'https://images.unsplash.com/photo-1503220317375-aaad61436b1b?auto=format&fit=crop&w=900&q=80',
                        cali: 'https://images.unsplash.com/photo-1473448912268-2022ce9509d8?auto=format&fit=crop&w=900&q=80',
                        barranquilla: 'https://images.unsplash.com/photo-1520607162513-77705c0f0d4a?auto=format&fit=crop&w=900&q=80'
                    };

                    return airportImages[code.toLowerCase()] || airportImages[city] || 'https://images.unsplash.com/photo-1436491865332-7a61a109cc05?auto=format&fit=crop&w=900&q=80';
                }

                function getAirportPopularity(airport) {
                    const text = `${airport.name || ''} ${airport.city || ''} ${airport.department || ''}`.toLowerCase();
                    const normalized = text.normalize('NFD').replace(/[\u0300-\u036f]/g, '');

                    if (normalized.includes('dorado') || normalized.includes('bogota')) return 10000;
                    if (normalized.includes('jose maria cordova') || normalized.includes('medellin')) return 9800;
                    if (normalized.includes('rafael nunez') || normalized.includes('cartagena')) return 9600;
                    if (normalized.includes('alfonso bonilla aragon') || normalized.includes('cali')) return 9400;
                    if (normalized.includes('ernesto cortissoz') || normalized.includes('barranquilla')) return 9200;
                    if (normalized.includes('pereira') || normalized.includes('armenia') || normalized.includes('manizales')) return 7000;
                    if (normalized.includes('internacional') || normalized.includes('international')) return 6500;
                    if (normalized.includes('cucuta') || normalized.includes('bucaramanga')) return 6000;
                    if (normalized.includes('neiva') || normalized.includes('florencia') || normalized.includes('popayan')) return 5500;

                    return 3000;
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
                }

                function getAirportHistory(airport) {
                    const name = (airport.name || 'Este aeropuerto').toLowerCase();
                    const city = (airport.city || '').toLowerCase();

                    if (name.includes('dorado') || city.includes('bogotá') || city.includes('bogota')) {
                        return 'El Aeropuerto El Dorado de Bogotá es uno de los hubs más importantes de Colombia y del continente. Fue clave en la expansión de la aviación comercial del país y sigue conectando rutas regionales e internacionales con alta frecuencia.';
                    }

                    if (name.includes('rafael núñez') || name.includes('rafael nunez') || city.includes('cartagena')) {
                        return 'El aeropuerto Rafael Núñez de Cartagena es un símbolo de la historia turística del Caribe colombiano. Su crecimiento estuvo ligado al auge del turismo, la conexión regional y la consolidación de Cartagena como destino internacional.';
                    }

                    if (name.includes('córdoba') || name.includes('cordoba') || city.includes('medellín') || city.includes('medellin')) {
                        return 'El aeropuerto José María Córdova, cerca de Medellín, se convirtió en una de las principales puertas de entrada al eje cafetero y al país. Su desarrollo impulsó comercio, emprendimiento y movilidad regional durante décadas.';
                    }

                    if (name.includes('bonilla') || city.includes('cali')) {
                        return 'El aeropuerto Alfonso Bonilla Aragón de Cali es un punto estratégico para la conectividad del suroccidente. Su historia refleja el crecimiento económico de la región y la importancia del valle del Cauca en el tráfico aéreo nacional.';
                    }

                    if (name.includes('cortissoz') || city.includes('barranquilla')) {
                        return 'El aeropuerto Ernesto Cortissoz de Barranquilla ha sido pieza clave en la conectividad del Caribe colombiano. Desde su expansión, ha apoyado la logística, el turismo y la actividad comercial del litoral norte.';
                    }

                    if (city.includes('pereira') || city.includes('armenia') || city.includes('manizales')) {
                        return 'Estos aeropuertos del eje cafetero representan la conectividad de una de las regiones más dinámicas del país, con fuerte vínculo entre turismo, negocios y movilidad regional.';
                    }

                    return `${airport.name || 'Este aeropuerto'} es una terminal importante para ${airport.city || 'la región'} y refleja la red de conectividad que sostiene el desarrollo de ${airport.department || 'el departamento'} en Colombia.`;
                }

                function openAirportModal(airport) {
                    const modal = document.getElementById('airport-modal');
                    const title = document.getElementById('airport-modal-title');
                    const tag = document.getElementById('airport-modal-tag');
                    const text = document.getElementById('airport-modal-text');

                    title.textContent = airport.name;
                    tag.textContent = airport.city || 'Aeropuerto';
                    text.textContent = getAirportHistory(airport);
                    modal.classList.add('is-open');
                    modal.setAttribute('aria-hidden', 'false');
                }

                function closeAirportModal() {
                    const modal = document.getElementById('airport-modal');
                    modal.classList.remove('is-open');
                    modal.setAttribute('aria-hidden', 'true');
                }

                function renderAirportsList(airports) {
                    const airportGrid = document.getElementById('airport-grid');
                    const rankedAirports = [...airports].sort((a, b) => getAirportPopularity(b) - getAirportPopularity(a) || (a.name || '').localeCompare(b.name || '')).slice(0, 8);

                    airportGrid.innerHTML = rankedAirports.map((airport) => {
                        const imageUrl = getAirportImage(airport);
                        const codeText = airportDisplayCode(airport);
                        return `
                            <article class="airport-card" data-airport-id="${airport.id}" tabindex="0" role="button" aria-label="Abrir información de ${airport.name}">
                                <div class="airport-visual">
                                    <img src="${imageUrl}" alt="${airport.name}" />
                                    <span class="airport-pin">✈</span>
                                </div>
                                <div class="airport-info">
                                    <span class="airport-code">${codeText}</span>
                                    <h3 class="airport-name">${airport.name}</h3>
                                    <div class="airport-meta">${airport.city || 'Ciudad'} · ${airport.department || 'Departamento'}</div>
                                </div>
                            </article>
                        `;
                    }).join('');

                    airportGrid.querySelectorAll('.airport-card').forEach((card) => {
                        const airportId = Number(card.dataset.airportId);
                        const airport = state.airports.find((item) => Number(item.id) === airportId);
                        if (!airport) return;

                        card.addEventListener('click', () => openAirportModal(airport));
                        card.addEventListener('keydown', (event) => {
                            if (event.key === 'Enter' || event.key === ' ') {
                                event.preventDefault();
                                openAirportModal(airport);
                            }
                        });
                    });

                    document.querySelector('[data-close-airport-modal]')?.addEventListener('click', closeAirportModal);
                    document.getElementById('airport-modal')?.addEventListener('click', (event) => {
                        if (event.target === event.currentTarget) closeAirportModal();
                    });
                }

                function populateSelectors(airports) {
                    const origin = document.getElementById('origin');
                    const destination = document.getElementById('destination');
                    origin.innerHTML = airports.map(a => `<option value="${a.id}">${a.name} (${airportDisplayCode(a)})</option>`).join('');
                    destination.innerHTML = airports.map(a => `<option value="${a.id}">${a.name} (${airportDisplayCode(a)})</option>`).join('');

                    if (airports.length > 1) {
                        origin.value = String(airports[0].id);
                        destination.value = String(airports[1].id);
                    }

                    updateRoute();
                }

                function updateRoute() {
                    const originId = Number(document.getElementById('origin').value);
                    const destinationId = Number(document.getElementById('destination').value);
                    const origin = getAirportById(originId);
                    const destination = getAirportById(destinationId);
                    const routeStatusEl = document.getElementById('route-status');

                    if (!origin || !destination || origin.latitude == null || origin.longitude == null || destination.latitude == null || destination.longitude == null) {
                        routeStatusEl.textContent = 'Sin ruta';
                        renderMap();
                        return;
                    }

                    routeStatusEl.textContent = `${airportDisplayCode(origin)} → ${airportDisplayCode(destination)}`;
                    renderMap();
                }

                function renderItineraries() {
                    const list = document.getElementById('itinerary-list');
                    if (!state.itineraries.length) {
                        list.innerHTML = '<div class="itinerary-item itinerary-empty"><div class="itinerary-copy"><strong>Sin itinerarios</strong></div><span>Agrega una ruta para comenzar</span></div>';
                        return;
                    }

                    list.innerHTML = state.itineraries.map((item, index) => `
                        <div class="itinerary-item">
                            <div class="itinerary-copy">
                                <span><strong>${item.origin}</strong> → <strong>${item.destination}</strong></span>
                                <span class="itinerary-meta">${item.date || 'Sin fecha'} · ${item.purpose || 'Viaje'}</span>
                            </div>
                            <div style="display:flex; gap:8px;">
                                <button type="button" class="delete-btn" data-index="${index}" style="background: rgba(235,106,85,0.12); color:#b84e3d; border-color: rgba(235,106,85,0.2);">Eliminar</button>
                                <button type="button" class="edit-btn" data-index="${index}" style="border: 1px solid rgba(90,168,255,0.2); background: rgba(90,168,255,0.08); color: var(--text); padding: 8px 12px; border-radius: 10px; cursor:pointer; font-size:0.75rem; font-weight:700; letter-spacing:0.08em; text-transform:uppercase;">Editar</button>
                            </div>
                        </div>
                    `).join('');
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

                    const originAirport = state.airports.find(airport => (airport.iata_code || '').toUpperCase() === String(itinerary.origin || '').toUpperCase()) || state.airports.find(airport => airport.name === itinerary.origin);
                    const destinationAirport = state.airports.find(airport => (airport.iata_code || '').toUpperCase() === String(itinerary.destination || '').toUpperCase()) || state.airports.find(airport => airport.name === itinerary.destination);

                    if (originAirport) originSelect.value = String(originAirport.id);
                    if (destinationAirport) destinationSelect.value = String(destinationAirport.id);
                    dateInput.value = itinerary.date || '';
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
                    const originId = Number(document.getElementById('origin').value);
                    const destinationId = Number(document.getElementById('destination').value);
                    const origin = getAirportById(originId);
                    const destination = getAirportById(destinationId);
                    const date = document.getElementById('date').value;
                    const purpose = document.getElementById('purpose').value.trim() || 'Viaje';

                    if (!origin || !destination) return;

                    const itineraryPayload = {
                        id: state.editingId || ((typeof crypto !== 'undefined' && crypto.randomUUID) ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`),
                        origin: normalizeAirportCode(origin.iata_code) || origin.name,
                        destination: normalizeAirportCode(destination.iata_code) || destination.name,
                        date: date || 'Fecha libre',
                        purpose
                    };

                    if (state.editingId) {
                        const idx = state.itineraries.findIndex(item => item.id === state.editingId);
                        if (idx >= 0) state.itineraries[idx] = { ...state.itineraries[idx], ...itineraryPayload };
                    } else {
                        state.itineraries.unshift(itineraryPayload);
                    }

                    persistItineraries();
                    resetFormMode();
                    renderItineraries();
                    updateRoute();
                });

                document.getElementById('cancel-edit').addEventListener('click', function () {
                    resetFormMode();
                    document.getElementById('purpose').value = '';
                    document.getElementById('date').value = '';
                });

                document.getElementById('itinerary-list').addEventListener('click', function (event) {
                    const button = event.target.closest('.delete-btn');
                    if (button) {
                        const index = Number(button.dataset.index);
                        if (!Number.isInteger(index) || index < 0) return;

                        state.itineraries.splice(index, 1);
                        persistItineraries();
                        renderItineraries();
                        return;
                    }

                    const editButton = event.target.closest('.edit-btn');
                    if (!editButton) return;

                    const index = Number(editButton.dataset.index);
                    if (!Number.isInteger(index) || index < 0) return;
                    populateFormForEdit(state.itineraries[index]);
                });

                document.getElementById('origin').addEventListener('change', updateRoute);
                document.getElementById('destination').addEventListener('change', updateRoute);

                async function loadAirports() {
                    try {
                        const res = await fetch('/api/airports');
                        if (!res.ok) throw new Error('Falló la API');
                        const airports = await res.json();
                        state.airports = airports;
                        setApiState(true);
                        document.getElementById('airport-count').textContent = `${airports.length} registros`;
                        renderAirportsList(airports);
                        renderRecommendations();
                        populateSelectors(airports);
                        renderItineraries();
                    } catch (error) {
                        setApiState(false);
                        document.getElementById('airport-count').textContent = 'API error';
                        renderMapFallback();
                    }
                }

                updateClock();
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

