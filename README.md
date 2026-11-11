# Sistema de Itinerarios Personales

Plataforma de microservicios para consultar aeropuertos colombianos, diseñar itinerarios personales, notificar la creación de itinerarios de forma asíncrona y generar reportes bajo demanda.

## Estado actual

La infraestructura, el Airport Service y el Itinerary Service se ejecutan con Docker Compose. Itinerary valida los aeropuertos mediante HTTP, persiste itinerarios en PostgreSQL y tiene CRUD documentado con Swagger. La publicación de eventos está implementada con Outbox transaccional y RabbitMQ; Notification Service consume esos eventos y guarda un historial en su propia base de datos.

El mapa del Airport Service consume el modelo adaptado de aeropuertos y muestra sus ubicaciones. La interfaz de mapas usa Leaflet y OpenFreeMap.

El entorno local incluye:

| Componente | Rol | Persistencia / UI |
| --- | --- | --- |
| `postgres-airport` | Base del bounded context Aeropuertos | volumen `airport_pg_data` (no expuesta al host) |
| `postgres-itinerary` | Base del bounded context Itinerarios | volumen `itinerary_pg_data` |
| `postgres-notification` | Base del bounded context Notificaciones | volumen `notification_pg_data` |
| `redis` | Caché (Aeropuertos, Fase 2) | volumen `redis_data` |
| `rabbitmq` | Broker de `ItineraryCreatedEvent` | UI `http://127.0.0.1:15672` |
| `airport-service` | Adaptador REST de aeropuertos colombianos | API y Swagger `http://127.0.0.1:8010/docs` |
| `itinerary-service` | CRUD, validación HTTP y Outbox transaccional | API y Swagger `http://127.0.0.1:8002/docs` |
| `notification-service` | Consumidor de eventos e historial de notificaciones simuladas | API y Swagger `http://127.0.0.1:8003/docs` |
| `gateway` | Entrada HTTP única con proxy y limitación básica de solicitudes | `http://127.0.0.1:8000` |
| `jaeger` | Trazas | UI `http://127.0.0.1:16686` |
| `otel-collector` | Recepción OTLP y exportación | interno |
| `prometheus` | Métricas | `http://127.0.0.1:9090` |
| `grafana` | Dashboards | `http://127.0.0.1:3000` |

Red Docker: `personal-itinerary-net`.

## Arquitectura actual y objetivo

```text
Usuario → Frontend → API Gateway
                      ├─ Airport Service → API Colombia
                      │                    Redis (caché)
                      │                    PostgreSQL airport_db
                      └─ Itinerary Service → PostgreSQL itinerary_db
                                             ↓ ItineraryCreatedEvent
                                             ↓ (Outbox en la transacción)
                                           RabbitMQ
                                             ↓
                                      Notification Service
                                             ↓
                                      PostgreSQL notification_db

Observabilidad: OpenTelemetry → Collector → Jaeger / Prometheus → Grafana
```

## Requisitos

- Docker Desktop en Windows, con el motor iniciado y WSL 2 habilitado; o Docker Engine con Docker Compose v2 en Linux/macOS.
- Git para clonar el repositorio.

Todos los servicios de la aplicación se ejecutan con Docker Compose. No es necesario instalar Python, PostgreSQL, Redis, RabbitMQ, Jaeger, Prometheus ni Grafana en el computador.

## Iniciar el proyecto

En Windows, abre Docker Desktop y espera a que indique que está funcionando. Después, en PowerShell:

```powershell
git clone https://github.com/julianghost28-source/Proyecto.git
cd Proyecto
Copy-Item .env.example .env
docker compose up -d --build
docker compose ps
```

La primera vez, Docker descarga las imágenes y construye los servicios; puede tardar unos minutos. Cuando ya está instalado y no cambiaste el código, inicia el entorno con:

```powershell
docker compose up -d
docker compose ps
```

La aplicación principal queda en [http://localhost:8000](http://localhost:8000). Verifica que los servicios principales aparezcan como `healthy` en `docker compose ps` antes de usarla.

### Direcciones locales

- Aplicación y Gateway: http://localhost:8000
- API de aeropuertos: http://localhost:8010/docs
- API de itinerarios: http://localhost:8002/docs
- API de notificaciones: http://localhost:8003/docs
- RabbitMQ Management: http://localhost:15672
- Jaeger: http://localhost:16686
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000

Las bases de datos y Redis se mantienen dentro de la red de Docker Compose; no se publican directamente al computador.

### Detener el proyecto

Para apagar los contenedores sin borrar los datos guardados:

```powershell
docker compose down
```

Los datos se conservan en volúmenes de Docker. No uses `docker compose down -v` a menos que quieras borrar esos datos.

## Credenciales de desarrollo

Definidas en `.env` / `.env.example`. Son valores **solo locales**, no de producción.

- Grafana: `GRAFANA_ADMIN_USER` / `GRAFANA_ADMIN_PASSWORD`
- RabbitMQ management: `RABBITMQ_USER` / `RABBITMQ_PASSWORD`
- Redis y PostgreSQL no se publican en el host; los servicios de aplicación (Fase 2+) los usan por nombre DNS interno.

## Topología de eventos (predeclarada)

| Recurso | Nombre |
| --- | --- |
| Exchange | `itinerary.events` (topic) |
| Routing key | `itinerary.created` |
| Cola | `notification.itinerary-created` |
| DLX / DLQ | `itinerary.events.dlx` / `notification.itinerary-created.dlq` |

Definición versionada en `infra/rabbitmq/definitions.json`.

El contrato `ItineraryCreatedEvent` está documentado en [docs/asyncapi.yaml](docs/asyncapi.yaml). El Outbox se guarda en la misma transacción que el itinerario; el publicador reintenta si RabbitMQ no está disponible. Notification Service deduplica por `event_id` y registra una notificación simulada, sin enviar correos reales.

## Documentación relacionada

- [SECURITY.md](SECURITY.md)
- [REQUIREMENTS_TRACEABILITY.md](REQUIREMENTS_TRACEABILITY.md)
- Reglas de Cursor: `.cursor/rules/project.mdc`

## Fases

1. Infraestructura (este documento, Compose)
2. Airport Service
3. Itinerary Service
4. Eventos
5. Notification Worker
6. API Gateway
7. Frontend
8. Report Function
9. Seguridad
10. Observabilidad de aplicación
11. Pruebas E2E
12. CI/CD

## Comando de portabilidad

En cualquier máquina:

```text
git clone <repo>
docker compose up --build
```

El stack de infraestructura debe quedar healthy sin instalaciones manuales de dependencias de runtime.
