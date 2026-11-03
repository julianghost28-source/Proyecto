# Trazabilidad de requerimientos

Leyenda de estado: `PENDIENTE` · `PARCIAL` · `CUBIERTO`.

## Requerimientos funcionales

| ID | Descripción | Servicio | Endpoint / artefacto | Código | Test | Estado |
| --- | --- | --- | --- | --- | --- | --- |
| RF-01 | Consultar aeropuertos | Airport Service | Fase 2 | — | — | PENDIENTE |
| RF-02 | Consultar aeropuerto por ID | Airport Service | Fase 2 | — | — | PENDIENTE |
| RF-03 | Mapa interactivo Plotly JS | Frontend | Fase 7 | — | — | PENDIENTE |
| RF-04 | Crear itinerario | Itinerary Service | Fase 3 | — | — | PENDIENTE |
| RF-05 | Validar aeropuertos vía Airport Service | Itinerary Service | Fase 3 | — | — | PENDIENTE |
| RF-06 | Consultar itinerarios | Itinerary Service | Fase 3 | — | — | PENDIENTE |
| RF-07 | Consultar itinerario por ID | Itinerary Service | Fase 3 | — | — | PENDIENTE |
| RF-08 | Actualizar itinerario | Itinerary Service | Fase 3 | — | — | PENDIENTE |
| RF-09 | Eliminar itinerario | Itinerary Service | Fase 3 | — | — | PENDIENTE |
| RF-10 | Generar `ItineraryCreatedEvent` | Itinerary Service | Fase 4 | — | — | PENDIENTE |
| RF-11 | Procesar evento de forma asíncrona | Notification Worker | Fase 5 | — | — | PENDIENTE |
| RF-12 | Registrar notificación | Notification Worker | Fase 5 | — | — | PENDIENTE |
| RF-13 | Reportes bajo demanda | Report Function | Fase 8 | — | — | PENDIENTE |

## Requerimientos no funcionales

| ID | Descripción | Evidencia Fase 1 | Estado |
| --- | --- | --- | --- |
| RNF-01 | Microservicios | Bounded contexts aislados; servicios de aplicación en fases 2–8 | PARCIAL |
| RNF-02 | Hexagonal | Se aplicará por servicio desde Fase 2 | PENDIENTE |
| RNF-03 | Adapter API externa | Airport Service Fase 2 | PENDIENTE |
| RNF-04 | DDD | Un contexto por servicio; DBs separadas ya provisionadas | PARCIAL |
| RNF-05 | Independencia de datos | `postgres-airport`, `postgres-itinerary`, `postgres-notification` (contenedores y volúmenes distintos) | CUBIERTO (infra) |
| RNF-06 | Alembic | Fase 2+ | PENDIENTE |
| RNF-07 | OpenAPI | Fase 2+ | PENDIENTE |
| RNF-08 | Errores uniformes | Fase 2+ | PENDIENTE |
| RNF-09 | Resiliencia HTTP | Fase 2 | PENDIENTE |
| RNF-10 | Redis | Servicio `redis` healthy, password por env, volumen persistente | CUBIERTO (infra) |
| RNF-11 | Mensajería | RabbitMQ + exchange/colas/DLQ en `infra/rabbitmq/definitions.json` | CUBIERTO (infra) |
| RNF-12 | Observabilidad | Collector OTLP, Jaeger, Prometheus, Grafana, dashboard de infra | PARCIAL (stack; falta instrumentación de apps) |
| RNF-13 | Correlation ID | Fase 6 | PENDIENTE |
| RNF-14 | Seguridad | `.env` gitignored, secretos por env, DBs no publicadas, Grafana sin signup | PARCIAL |
| RNF-15 | Contenerización | Imágenes oficiales versionadas en Compose | CUBIERTO (infra) |
| RNF-16 | Docker Compose | `docker-compose.yml` orquesta el entorno | CUBIERTO |
| RNF-17 | Pruebas | `scripts/check-infra.ps1` / `.sh` como smoke de infra; pytest desde Fase 2 | PARCIAL |
| RNF-18 | CI/CD | Fase 12 | PENDIENTE |

## Verificación de runtime (Fase 1)

| Comando | Resultado |
| --- | --- |
| `docker compose config` | **BLOQUEADO** — `docker` no está instalado en el PATH de esta máquina |
| `docker compose build` | **BLOQUEADO** (mismo motivo) |
| `docker compose up -d` | **BLOQUEADO** |
| `docker compose ps` | **BLOQUEADO** |
| `scripts/check-infra.ps1` | Pendiente de Docker healthy |

Reanudar verificación en cuanto Docker Desktop esté instalado y el daemon activo. No iniciar Fase 2 hasta entonces.

## Decisiones de Fase 1

| Decisión | Motivo | Impacto RF/RNF |
| --- | --- | --- |
| Tres contenedores PostgreSQL en lugar de un solo motor con tres bases | Aislamiento operativo alineado con RNF-05 y claridad de bounded context | No viola RF; simplifica que un servicio no pueda “ver” el disco del otro |
| No publicar PostgreSQL/Redis/AMQP en el host | RNF-14: reducir superficie | Los clientes de aplicación usarán DNS interno de Compose |
| Precargar topología RabbitMQ | El worker no debe declarar la verdad de routing en caliente de forma implícita | RF-10/11 listos a nivel de broker |
| No crear carpetas vacías de servicios | Evitar falsos positivos de “estructura completa” | Las fases 2+ añaden código ejecutable |

## Mapeo de fases

| Fase | Alcance | Criterio de cierre |
| --- | --- | --- |
| 1 | Compose, redes, volúmenes, health checks, observabilidad de plataforma | `docker compose ps` healthy + script de smoke |
| 2–12 | Según prompt maestro | Código + tests + build + health + docs + esta matriz |
