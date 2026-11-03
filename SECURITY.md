# Seguridad

Este documento cubre la postura de seguridad del Sistema de Itinerarios Personales. La autenticación de aplicación se completa en la Fase 9; la Fase 1 ya aplica límites de exposición y secretos por entorno.

## Secretos

- Los secretos viven en variables de entorno (`.env` local).
- `.env` está en `.gitignore`. El archivo versionado es `.env.example` con valores de desarrollo explícitamente no productivos.
- Nunca se registran contraseñas, tokens ni URLs productivas en el código.
- Los logs no deben imprimir secretos.

Valores actuales de `.env.example` (desarrollo):

- Contraseñas PostgreSQL / Redis / RabbitMQ / Grafana con sufijo `_dev_only`.
- `AUTH_JWT_SECRET` es un placeholder para la Fase 9.

## Superficie de red (Fase 1)

Publicado **solo en loopback** (`127.0.0.1`):

| Puerto | Servicio | Motivo |
| --- | --- | --- |
| 15672 | RabbitMQ Management | operación local |
| 16686 | Jaeger UI | observabilidad |
| 9090 | Prometheus | observabilidad |
| 3000 | Grafana | observabilidad |

**No** se publican en el host:

- PostgreSQL (tres instancias independientes)
- Redis
- AMQP 5672
- OTLP 4317/4318

Los microservicios se comunicarán por la red Docker `personal-itinerary-net`.

## Aislamiento de datos

Cada bounded context tiene su propio contenedor PostgreSQL y su propio volumen. No hay tablas compartidas ni usuarios cruzados.

## Contenedores

- Imágenes oficiales versionadas.
- Servicios de infra con `restart: unless-stopped` y health checks.
- Grafana: registro de usuarios deshabilitado (`GF_USERS_ALLOW_SIGN_UP=false`).
- Redis autentica con contraseña de entorno.

## Controles previstos (fases posteriores)

- Autenticación y autorización en el API Gateway para recursos protegidos.
- CORS explícito.
- Validación de entrada (Pydantic) y envelope de error uniforme.
- Rate limiting razonable en el Gateway.
- Contenedores de aplicación como usuario no root cuando la imagen lo permita.
- Cabeceras de seguridad HTTP en el Gateway y el frontend.

## Correlation ID

Todas las peticiones de aplicación deben transportar `X-Correlation-ID` (Fase 6+). No incluye secretos.

## Respuesta a incidentes de desarrollo

Si un secreto de desarrollo se filtra en un fork público, rotarlo en `.env` y no reutilizarlo. No hay secretos de producción en este repositorio.

