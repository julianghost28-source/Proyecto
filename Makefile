COMPOSE ?= docker compose

.PHONY: help up down build ps logs config health migrate test lint clean

help:
	@echo "Available targets:"
	@echo "  make up       Start the full stack (build if needed)"
	@echo "  make down     Stop containers (keep volumes)"
	@echo "  make build    Build images"
	@echo "  make ps       Show container status"
	@echo "  make logs     Follow logs"
	@echo "  make config   Validate docker-compose.yml"
	@echo "  make health   Check infrastructure health"
	@echo "  make migrate  Run database migrations (from Phase 2)"
	@echo "  make test     Run test suites (from Phase 2)"
	@echo "  make lint     Run linters (from Phase 2)"
	@echo "  make clean    Stop stack and remove volumes"

up:
	$(COMPOSE) up --build -d

down:
	$(COMPOSE) down

build:
	$(COMPOSE) build

ps:
	$(COMPOSE) ps

logs:
	$(COMPOSE) logs -f --tail=200

config:
	$(COMPOSE) config

health:
	pwsh -File scripts/check-infra.ps1

migrate:
	@echo "Migrations are introduced in Phase 2 (Alembic per service)."

test:
	@echo "Application tests start in Phase 2."

lint:
	@echo "Lint pipeline starts with application services (Phase 2 / CI)."

clean:
	$(COMPOSE) down -v --remove-orphans

