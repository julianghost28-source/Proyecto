# Sistema de Itinerarios Personales

Aplicación web para consultar aeropuertos colombianos y crear, consultar, editar y eliminar itinerarios. El proyecto separa el catálogo de aeropuertos, la gestión de itinerarios y las notificaciones en servicios independientes. La ejecución que tenemos demostrada es local, con Docker Compose.

## Qué funciona hoy

- Interfaz web con mapa y tarjetas de itinerarios, servida por Airport Service.
- CRUD de itinerarios con FastAPI, validación de aeropuertos por HTTP y PostgreSQL.
- Notificaciones simuladas procesadas de forma asíncrona mediante RabbitMQ.
- Gateway Nginx que expone la aplicación y enruta las APIs por `http://localhost:8000`.
- Pruebas unitarias para normalizar coordenadas y validar los casos de uso del CRUD de itinerarios.
- Escenario de carga Locust en `performance/`; una ejecución local observada usó 10 usuarios y tuvo 0 solicitudes fallidas.
- Análisis local SonarQube. La última pantalla revisada mostraba Quality Gate Passed, hallazgos abiertos y avisos de configuración.

## Arquitectura actual

```text
Navegador
   │ HTTP
   ▼
Gateway Nginx :8000 ───────► Airport Service :8010 ─────► API Colombia
   │                         └─ entrega la interfaz web
   ├───────────────────────► Itinerary Service :8002 ─────► PostgreSQL itinerary
   │                                                     └─ Outbox → RabbitMQ
   └───────────────────────► Notification Service :8003 ◄── RabbitMQ
                                                         └─ PostgreSQL notification

Compose también levanta las bases auxiliares, Redis y el stack de observabilidad.
SonarQube se ejecuta aparte del Compose principal.
```

Los tres servicios de aplicación tienen sus propios Dockerfile. Hay **un solo `docker-compose.yml` central** para levantar el entorno; no hay un Compose independiente por servicio.

| Servicio / componente | Función actual | Dirección local |
| --- | --- | --- |
| Gateway | Entrada web y proxy Nginx | [http://localhost:8000](http://localhost:8000) |
| Airport Service | Interfaz, catálogo de aeropuertos y adaptación del JSON externo | [http://localhost:8010](http://localhost:8010) |
| Itinerary Service | CRUD, reglas de negocio, PostgreSQL y Outbox | [http://localhost:8002/docs](http://localhost:8002/docs) |
| Notification Service | Consume eventos y guarda avisos simulados | [http://localhost:8003/docs](http://localhost:8003/docs) |
| RabbitMQ Management | Estado del broker y colas | [http://localhost:15672](http://localhost:15672) |
| Prometheus | Consulta de métricas scrapeadas | [http://localhost:9090](http://localhost:9090) |
| Grafana | Visualización de métricas | [http://localhost:3000](http://localhost:3000) |
| Jaeger | Interfaz para trazas recibidas | [http://localhost:16686](http://localhost:16686) |
| SonarQube | Análisis estático local; contenedor separado | [http://localhost:9000](http://localhost:9000) |
| Locust | Pantalla de la prueba de carga; proceso local | [http://localhost:8089](http://localhost:8089) |

Las rutas de aeropuertos existen, pero algunas no están incluidas en el esquema OpenAPI de Airport Service. Para el CRUD de itinerarios usa su Swagger en el puerto 8002.

## Iniciar con Docker Compose

Requisitos: Docker Desktop con el motor activo y Git. En PowerShell, desde la raíz:

```powershell
Copy-Item .env.example .env   # solo la primera vez
# Completa .env con valores locales propios y nunca lo subas a GitHub.
docker compose up -d --build
docker compose ps
```

Cuando ya construiste las imágenes y no cambiaste código:

```powershell
docker compose up -d
docker compose ps
```

Abre [http://localhost:8000](http://localhost:8000). Los datos de PostgreSQL se conservan en volúmenes si detienes el entorno con:

```powershell
docker compose down
```

`docker compose down -v` también elimina los volúmenes y sus datos. Úsalo solo si realmente quieres reiniciar la información.

## Endpoints principales

| Método | Ruta | Propósito | Respuesta habitual |
| --- | --- | --- | --- |
| GET | `/api/itineraries` | Listar itinerarios | 200 |
| POST | `/api/itineraries` | Crear un itinerario | 201 |
| GET | `/api/itineraries/{itinerary_id}` | Consultar uno por ID entero | 200 / 404 |
| PATCH | `/api/itineraries/{itinerary_id}` | Actualizar campos enviados | 200 / 404 |
| DELETE | `/api/itineraries/{itinerary_id}` | Eliminar por ID | 204 / 404 |
| GET | `/api/airports` | Listar aeropuertos | 200 |
| GET | `/api/notifications` | Listar notificaciones simuladas | 200 |
| GET | `/health` | Comprobar salud del servicio | 200 |

El Gateway enruta las APIs al servicio correspondiente. Itinerary valida que origen y destino sean distintos, que existan y que la duración sea positiva. `PATCH` conserva los campos que no se envían.

## Pruebas unitarias

La suite actual contiene 10 pruebas: una comprueba la normalización de coordenadas de aeropuertos y nueve prueban la lógica de los casos de uso del CRUD de itinerarios (listar, crear, consultar, editar y eliminar), incluyendo validaciones. Estas pruebas llaman la lógica de aplicación con repositorio y catálogo en memoria: no hacen clic en el navegador ni modifican PostgreSQL o RabbitMQ.

Instala las dependencias de prueba una vez y ejecuta toda la suite desde la raíz:

```powershell
py -m pip install -r requirements-test.txt
py -m pytest
```

## Prueba de carga con Locust

El escenario está en [`performance/locustfile.py`](performance/locustfile.py). Usa el Gateway, lee aeropuertos e itinerarios, consulta `/health` y crea ocasionalmente itinerarios. Los `POST` exitosos escriben datos persistentes y producen los eventos normales de la aplicación. Úsalo solo contra el entorno local, nunca contra producción.

Instalación y arranque:

```powershell
py -m pip install -r requirements-load.txt
py -m locust -f performance/locustfile.py --host http://localhost:8000
```

Abre [http://localhost:8089](http://localhost:8089). Para una demo pequeña, configura 10 usuarios y una tasa de subida de 1 usuario por segundo; detén la prueba con **STOP**. Revisa las estadísticas por endpoint, no solo el total. Consulta [`performance/README.md`](performance/README.md) para ver el significado y los efectos sobre los datos.

Evidencia observada durante la demo: 10 usuarios virtuales, 96 solicitudes, 0 fallos y cerca de 4,5 solicitudes por segundo. Es una medición en un computador local, no una capacidad máxima garantizada ni un SLA.

## SonarQube

La aplicación se analizó localmente con `pysonar` contra `http://localhost:9000`. La última página revisada indicó **Quality Gate: Passed**, 4 hallazgos de seguridad, 2 de confiabilidad y 2 de mantenibilidad, cobertura 0 % y duplicación 1,5 %. También mostró avisos de versión objetivo de Python y de configuración de pruebas. Un intento posterior de pasar opciones `-D` a Pysonar terminó con `Unexpected argument`; por tanto esos ajustes no están confirmados.

SonarQube revisa código estáticamente; no ejecuta pytest ni es CI/CD. Su contenedor está separado del `docker-compose.yml` principal. No guardes tokens en este repositorio, archivos, capturas ni commits.

## Mensajería y persistencia

Itinerary Service guarda el itinerario y el evento pendiente en una misma transacción (Outbox). Un publicador envía `ItineraryCreatedEvent` a RabbitMQ; Notification Service consume el evento y guarda una notificación simulada en su propia base. RabbitMQ transporta mensajes: no es la base de datos de itinerarios ni escribe directamente en PostgreSQL.

Las bases PostgreSQL de Itinerary y Notification se usan. La base `postgres-airport` y Redis aparecen configurados en Compose, pero el flujo visible del catálogo no está conectado a esos servicios actualmente.

## Calidad, despliegue y límites confirmados

- El despliegue presentado es local en Docker Compose; no está publicado en Azure ni en Internet.
- No hay workflow de GitHub Actions en `.github/workflows`; build, pruebas, SonarQube y carga se ejecutan manualmente.
- La observabilidad está parcialmente conectada: Compose provisiona Collector, Prometheus, Grafana y Jaeger, pero no afirmes que todas las aplicaciones exportan trazas o métricas a todos ellos sin comprobarlo.
- La arquitectura hexagonal se aprecia con más claridad en Itinerary Service; los tres servicios no tienen la misma separación por capas.
- Airport Service adapta el JSON externo mediante `normalize_airport`; el traductor está en `main.py`, no en una clase separada llamada `ApiColombiaAirportAdapter`.
- La rúbrica pide revisar si requiere un `docker-compose.yml` por servicio. El proyecto actual usa un Compose central y un Dockerfile por servicio de aplicación.
- El documento corto de arquitectura y el conteo real de sprints deben verificarse con el equipo/aula/Jira antes de presentarlos.

## Git y solicitudes de extracción

El repositorio es [julianghost28-source/Proyecto](https://github.com/julianghost28-source/Proyecto). Se usan nombres descriptivos con prefijos `feature/`, `fix/` y `docs/`. Una rama contiene una tarea; un pull request (PR) permite revisar el diff antes de integrar a `main`.

Historial verificado: PR #1 (Docker-only startup), #3 (edición de itinerario eliminado) y #4 (tarjetas del frontend) se integraron; PR #2 se cerró sin integrar por duplicar la corrección del #3. La rama de modernización de frontend tiene el PR #5 abierto hacia `main`. El PR #5 incluye Locust, el README actualizado y el guion de exposición. Está publicado para revisión, pero aún no se ha integrado a `main`.

## Documentos

- [Guion para exponer en tres partes](docs/guion_sustentacion_tres_integrantes.md)
- [Trazabilidad de la rúbrica y estado real](REQUIREMENTS_TRACEABILITY.md)
- [Guía de Locust](performance/README.md)
- [Contrato de eventos](docs/asyncapi.yaml)
