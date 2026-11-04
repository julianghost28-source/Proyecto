FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/packages/pis-platform:/app/services/itinerary-service \
    PORT=8000

WORKDIR /app

COPY packages/pis-platform /app/packages/pis-platform
COPY services/itinerary-service /app/services/itinerary-service

RUN pip install --no-cache-dir /app/packages/pis-platform

WORKDIR /app/services/itinerary-service

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8000"]
