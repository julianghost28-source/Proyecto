# Guion de sustentación en tres partes

## Para qué sirve este guion

La exposición está dividida entre tres integrantes. La primera parte queda para Julián porque cubre lo que ha mostrado y practicado más: la aplicación, las APIs, Swagger, SonarQube y Locust. Las otras dos partes cubren arquitectura y DevOps. La guía diferencia resultados observados de elementos pendientes para que la exposición sea honesta y defendible.

**Idea central:** construimos una aplicación web local para consultar aeropuertos colombianos y administrar itinerarios. Separamos aeropuertos, viajes y notificaciones. Usamos HTTP cuando se necesita respuesta inmediata, RabbitMQ para procesar el evento de creación sin bloquear el CRUD y Docker Compose para levantar el entorno local.

## Orden de exposición

1. Julián: qué resuelve, demo del frontend, APIs/CRUD/Swagger y evidencias de SonarQube y Locust.
2. Integrante 2: arquitectura de microservicios, capas, Adapter, bases de datos, HTTP, RabbitMQ y Outbox.
3. Integrante 3: ciclo DevOps, GitHub/PR, Dockerfile/Compose, pruebas, observabilidad, despliegue y límites.

Cada persona puede pasar al siguiente integrante con una frase de enlace; no es necesario repetir la arquitectura completa.

# Parte 1 — Julián: aplicación, APIs y resultados

## Guion oral

“Desarrollamos un sistema de itinerarios personales. Desde la página se puede consultar el mapa de aeropuertos y crear, listar, editar y eliminar itinerarios. La interfaz está hecha con HTML, CSS y JavaScript, y el backend usa FastAPI. El navegador entra por el Gateway en el puerto 8000. Voy a mostrar el CRUD con Swagger y luego los resultados del análisis de código y de una prueba de carga local.”

## Qué mostrar y cómo explicarlo

1. **Docker Desktop / Compose:** muestra los contenedores y luego ejecuta `docker compose ps`. Los servicios deben aparecer activos y saludables. El Compose es la forma de iniciar el backend y sus dependencias.
2. **Aplicación:** abre `http://localhost:8000`. El formulario y las tarjetas son la interfaz; el mapa visualiza los aeropuertos.
3. **Swagger CRUD:** abre `http://localhost:8002/docs`. Explica que Swagger muestra el contrato de Itinerary Service y deja probar las rutas.
4. **Operaciones:**
   - `GET /api/itineraries`: consulta la lista; no crea ni modifica datos.
   - `POST /api/itineraries`: crea un viaje con JSON y normalmente responde `201`.
   - `GET /api/itineraries/{itinerary_id}`: busca usando un ID entero, por ejemplo `1`.
   - `PATCH /api/itineraries/{itinerary_id}`: cambia solo los campos que envías.
   - `DELETE /api/itineraries/{itinerary_id}`: elimina y responde `204` sin cuerpo cuando tuvo éxito.
5. **Swagger de notificaciones:** abre `http://localhost:8003/docs` y enseña `GET /api/notifications`. El estado `simulated_sent` significa aviso registrado en la aplicación; no es un correo real.

### Explicación de POST “con plastilina”

“El navegador manda un paquete JSON con nombre, aeropuerto de origen y destino, fecha y duración. Itinerary revisa que los datos tengan sentido y pregunta al servicio de aeropuertos si esos IDs existen. Si pasa las validaciones, lo guarda en PostgreSQL y responde `201 Created` con el itinerario creado.”

### Qué significan los códigos

| Código | Explicación sencilla |
| --- | --- |
| 200 | La consulta o actualización salió bien. |
| 201 | Se creó un itinerario nuevo. |
| 204 | Se eliminó correctamente y no queda cuerpo que devolver. |
| 404 | No existe el itinerario o aeropuerto con ese ID. |
| 422 | Los datos enviados no cumplen la forma o las reglas esperadas. |

## SonarQube: qué decir

“SonarQube hace análisis estático: inspecciona el código y publica hallazgos en un panel; no ejecuta las pruebas unitarias. El análisis local que mostramos terminó correctamente y la Quality Gate aparece Passed. También hay hallazgos abiertos, y cobertura en cero porque no se importó un informe de cobertura.”

En el panel revisado aparecen 4 issues de seguridad, 2 de confiabilidad y 2 de mantenibilidad, con duplicación de 1,5 %. El análisis también mostró avisos: la versión de Python se toma como rango 3.10–3.14 y los directorios de pruebas no están configurados con precisión. Un intento posterior de cambiar esas propiedades desde la línea de comando fue rechazado por Pysonar; no digas que esos avisos ya se corrigieron.

SonarQube se abre en `http://localhost:9000` y corre en un contenedor separado del Compose principal. **Nunca muestres ni leas en voz alta el token.**

## Locust: qué decir

“Locust simula usuarios virtuales que envían solicitudes a la API. En una ejecución local configuramos 10 usuarios. La captura mostró 96 solicitudes, 0 fallos y aproximadamente 4,5 solicitudes por segundo. El percentil 95 global subió por las consultas de preparación de aeropuertos; para comparar, miramos cada endpoint.”

En la tabla observada: `GET /api/itineraries` tuvo p95 de 17 ms, `POST /api/itineraries` p95 de 480 ms y `GET /health` p95 de 7 ms. La llamada de preparación a aeropuertos estuvo cerca de 2,5 s. Aclara que esto prueba una carga pequeña en un solo PC; no es una capacidad máxima ni un SLA. Los POST generan itinerarios persistentes.

Locust se ejecuta en el PC con `py -m locust -f performance/locustfile.py --host http://localhost:8000` y la interfaz está en `http://localhost:8089`.

## Cierre y pase de palabra

“Ya vimos qué puede hacer el usuario y cómo probar la API. Ahora mi compañero explicará cómo distribuimos el trabajo entre servicios y cómo se conectan por HTTP y eventos.”

# Parte 2 — Integrante 2: arquitectura y comunicación

## Guion oral

“Separamos el sistema por responsabilidades para que cada servicio tenga una función clara. Airport entrega y normaliza el catálogo de aeropuertos; Itinerary aplica las reglas del CRUD y guarda viajes; Notification consume eventos y registra avisos. Se comunican por HTTP cuando necesitamos una respuesta en el momento y por RabbitMQ cuando basta con procesar algo después.”

## Servicios y decisiones

| Servicio | Responsabilidad | Tecnologías / detalle |
| --- | --- | --- |
| Airport Service | Página web, catálogo y traducción del formato externo | FastAPI, API Colombia, `normalize_airport`, fallback fijo si falla la API |
| Itinerary Service | Reglas y CRUD de viajes | FastAPI, Pydantic, SQLAlchemy, PostgreSQL, capas de dominio/aplicación/infraestructura |
| Notification Service | Consumir `ItineraryCreatedEvent` y guardar un aviso | RabbitMQ, API de historial y PostgreSQL propio; el aviso es simulado |
| Gateway | Entrada común y proxy a las APIs | Nginx, accesible en puerto 8000 |

### Arquitectura hexagonal “con plastilina”

“En el centro ponemos las reglas de itinerarios. Alrededor definimos contratos llamados puertos. Los adaptadores conectan esos contratos con cosas externas, como HTTP, PostgreSQL o API Colombia. Así la regla de negocio no depende directamente de una marca de base de datos o de la forma exacta del JSON externo.”

Itinerary es donde más claramente se ven dominio, puertos, casos de uso y adaptadores. La separación no está igual de completa en los tres servicios; descríbela como una arquitectura aplicada parcialmente, no como tres hexágonos perfectos.

### Patrón Adapter

“API Colombia entrega un JSON con sus nombres de campos y coordenadas. `normalize_airport` lo traduce al modelo que usa nuestra app y corrige el orden de latitud/longitud si viene invertido. Itinerary usa `HttpAirportCatalog` como adaptador HTTP del puerto `AirportCatalog`.”

Precisión: en la rama actual `normalize_airport` está en `services/airport-service/main.py`; no hay una clase fuente llamada `ApiColombiaAirportAdapter`. No inventes esa clase al señalar el código.

### HTTP frente a RabbitMQ

- **HTTP es síncrono:** Itinerary pide a Airport confirmar origen/destino y necesita respuesta antes de crear el itinerario.
- **RabbitMQ es asíncrono:** después de guardar un itinerario se publica un evento para Notification. Itinerary no espera que el aviso termine para devolver el `201`.
- RabbitMQ transporta el evento; no guarda el itinerario ni escribe por sí solo en las bases de datos.

### Outbox y bases de datos

“Outbox guarda el evento pendiente en la misma transacción que el itinerario. Si RabbitMQ no está disponible en ese momento, el registro sigue pendiente y el publicador puede reintentar después. El consumidor registra el aviso en la base de Notification.”

Itinerary y Notification usan PostgreSQL. Compose también define PostgreSQL de Airport y Redis, pero el flujo visible del catálogo no está conectado a ellos actualmente. Las bases no se publican directamente al host; los servicios se encuentran por el DNS interno de la red Compose.

# Parte 3 — Integrante 3: DevOps, contenedores, pruebas y operación

## Guion oral

“El ciclo DevOps que demostramos conecta planeación, trabajo en ramas, revisión con Pull Request, construcción de imágenes, pruebas, análisis y despliegue local. Todavía no tenemos automatizado el ciclo: las pruebas y el scanner se corren manualmente y no hay un workflow de GitHub Actions ni despliegue automático.”

## GitHub y control de versiones

- `main` guarda la versión integrada.
- `feature/` identifica funcionalidad nueva, `fix/` una corrección y `docs/` documentación.
- Se trabaja en una rama y se abre un PR hacia `main`; el PR permite ver diff, conversación y aprobación antes de integrar.
- PR #1, #3 y #4 se integraron; PR #2 se cerró sin merge porque duplicaba la corrección que se integró en #3.
- La rama `feature/modernizacion-frontend` está publicada; los cambios locales de Locust y este guion aún deben quedar en un commit y PR para que también se vean en GitHub.
- Las iteraciones se cuentan en los sprints de Jira. Las 12 fases de una versión anterior del README eran etapas del plan, no una prueba de que existan 12 sprints. Confirmen la cifra en Jira.

## Dockerfile, Compose y despliegue

“Un Dockerfile es la receta para construir una imagen de servicio: define Python base, copia archivos, instala el paquete común y dice cómo arrancar Uvicorn. Docker Compose define cómo se relacionan esos contenedores: red, puertos, variables, volúmenes, dependencias y healthchecks.”

Los tres servicios de aplicación tienen Dockerfile. El proyecto usa un `docker-compose.yml` central, no un Compose por servicio. Para iniciar:

```powershell
docker compose up -d --build
docker compose ps
```

Se considera despliegue local. Compose facilita reproducirlo en otro computador, pero no crea alta disponibilidad ni publica el sistema a Internet. Si Docker Engine o el PC se detienen, la aplicación local deja de responder. Los volúmenes conservan los datos mientras no se borren con `docker compose down -v`.

## Pruebas

### Unitarias

“Una prueba unitaria revisa una función o regla pequeña aislada. En esta rama hay un test fuente para la normalización de coordenadas del aeropuerto. No representa una suite completa de todos los servicios.”

Comando desde la raíz:

```powershell
py -m pytest services/airport-service/test_airport_coords.py
```

Locust es una prueba de carga, no reemplaza pytest. En la ejecución mostrada: 10 usuarios virtuales, 96 solicitudes, 0 fallos y cerca de 4,5 RPS.

## Jira y CI/CD

Jira sirve para convertir el trabajo en backlog, asignar tareas y registrar sprints. El equipo debe abrir su tablero y decir el número de iteraciones que realmente ve. GitHub tiene PRs, pero eso no significa que exista CI/CD automático.

Para esta rama no se encontró `.github/workflows`. Por tanto, no decir “cada PR corre pruebas automáticamente” o “se despliega a Azure”. El entorno demostrado se levanta manualmente con Docker Compose en el PC.

## Observabilidad y resiliencia

Compose provisiona Prometheus, Grafana, Jaeger y OpenTelemetry Collector. Prometheus guarda series de métricas y Grafana las presenta; Jaeger explora trazas. La integración de telemetría de las aplicaciones está parcial, así que solo deben mostrar los paneles/datos que efectivamente aparezcan.

Resiliencia actual es parcial, no alta disponibilidad:

- Si Notification se detiene, la API de notificaciones no responde, pero el CRUD de itinerarios puede seguir; mensajes/eventos pueden quedar pendientes.
- Si RabbitMQ falla, Outbox retiene eventos pendientes y el publicador reintenta.
- Si Airport no responde, Itinerary no puede validar nuevos aeropuertos.
- Si cae una base, falla el servicio que la necesita; no hay failover de base.
- Si se detiene Docker Engine, todo el entorno local para.

## Preguntas probables y respuestas cortas

**¿Cuántas iteraciones tiene?**

“Lo confirmaré en Jira. El README tenía 12 fases de desarrollo, pero eso no equivale a 12 iteraciones.”

**¿Hicieron despliegue continuo?**

“Todavía no. Desplegamos localmente con Docker Compose. Tenemos PRs, pero falta automatizar pruebas y despliegue con un workflow.”

**¿Qué pasa si falla un contenedor?**

“Depende del servicio. No se cae todo necesariamente: si Notification falla, el CRUD puede continuar; si cae Docker Engine, sí deja de funcionar todo localmente. No tenemos réplicas de alta disponibilidad.”

**¿SonarQube ejecutó las pruebas?**

“No. Pytest ejecuta pruebas; SonarQube analiza patrones y calidad del código. La cobertura aparece en 0 % porque no importamos un reporte de cobertura.”

**¿Los avisos son correos reales?**

“No. El evento se procesa y queda una notificación simulada en la base de Notification.”

**¿Por qué microservicios?**

“Para separar responsabilidades y mostrar comunicación HTTP y por eventos. Reconocemos que aumenta la complejidad operativa y que para un sistema pequeño un monolito modular podría ser más simple.”

**¿Está en Azure?**

“No. Lo mostrado corre en Docker Desktop local; no se ha hecho despliegue público en Azure.”

## Lista previa a la exposición

- [ ] Docker Desktop abierto y motor activo.
- [ ] `docker compose ps` muestra los servicios requeridos en ejecución/saludables.
- [ ] Aplicación abre en `http://localhost:8000`.
- [ ] Swagger CRUD abre en `http://localhost:8002/docs`.
- [ ] SonarQube abre en `http://localhost:9000`; no proyectar el token.
- [ ] Para mostrar Locust, iniciar el proceso y abrir `http://localhost:8089`.
- [ ] Aclarar que Locust creó registros y que la muestra fue local.
- [ ] Abrir GitHub con los PRs integrados y la rama/PR actual que el equipo dejó listos.
- [ ] Confirmar sprints en Jira y recibir del integrante el documento de arquitectura.
- [ ] No usar `docker compose down -v` durante la demo.

## Resumen para memorizar

“Es una aplicación web local de itinerarios. El navegador entra por un gateway; FastAPI expone el CRUD; HTTP valida aeropuertos; RabbitMQ lleva el evento de creación; Outbox protege eventos pendientes; PostgreSQL persiste los datos. Docker Compose levanta el entorno. Usamos PRs para revisar cambios, una prueba unitaria puntual, Locust para una muestra de carga y SonarQube para análisis estático. CI/CD automático, cobertura y telemetría completa siguen pendientes.”
