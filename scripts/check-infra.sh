#!/usr/bin/env bash
set -euo pipefail

assert_healthy() {
  local name="$1"
  local status="$2"
  if [[ "$status" != "healthy" ]]; then
    echo "Service '$name' is not healthy (status='$status')." >&2
    exit 1
  fi
  echo "OK  $name is healthy"
}

echo "Validating docker compose configuration..."
docker compose config --quiet

services=(
  postgres-airport
  postgres-itinerary
  postgres-notification
  redis
  rabbitmq
  jaeger
  otel-collector
  prometheus
  grafana
)

for service in "${services[@]}"; do
  status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "pis-${service}")"
  if [[ "$status" == "running" ]]; then
    echo "OK  ${service} is running (no Docker healthcheck)"
    continue
  fi
  assert_healthy "$service" "$status"
done

curl -fsS "http://127.0.0.1:9090/-/healthy" >/dev/null
echo "OK  Prometheus HTTP"

curl -fsS "http://127.0.0.1:3000/api/health" >/dev/null
echo "OK  Grafana HTTP"

curl -fsS "http://127.0.0.1:16686/" >/dev/null
echo "OK  Jaeger UI HTTP"

RABBITMQ_USER="${RABBITMQ_USER:-itinerary}"
RABBITMQ_PASSWORD="${RABBITMQ_PASSWORD:-rabbitmq_dev_only}"
curl -fsS -u "${RABBITMQ_USER}:${RABBITMQ_PASSWORD}" "http://127.0.0.1:15672/api/health/checks/alarms" >/dev/null
echo "OK  RabbitMQ management HTTP"

echo
echo "Phase 1 infrastructure checks passed."
