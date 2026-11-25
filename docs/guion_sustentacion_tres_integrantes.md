# Guion integral de sustentación — Sistema de Itinerarios Personales

**Versión de trabajo:** 24 de noviembre de 2026

**Repositorio:** [julianghost28-source/Proyecto](https://github.com/julianghost28-source/Proyecto)

**Rama de revisión:** `feature/modernizacion-frontend`

**Pull Request:** [#5](https://github.com/julianghost28-source/Proyecto/pull/5), abierto hacia `main`; aún no integrado.

> Este guion se basa en el código y las evidencias disponibles en la rama indicada. Distingue lo que está implementado, lo que se ha ejecutado y lo que sigue pendiente. Si algo está marcado como “confirmar”, revísenlo con el tablero o la captura correspondiente antes de exponer.

## Cómo usar este documento

La exposición se reparte entre tres personas. **Julián presenta la Parte 1**, que incluye la bienvenida, el recorrido sencillo de la aplicación, el CRUD, Swagger y las dos evidencias que ya practicó: SonarQube y Locust. Las otras personas desarrollan arquitectura y operación/DevOps.

No lean todo literalmente. Aprendan la idea central, usen los pasos de demostración como mapa y abran los archivos señalados cuando quieran mostrar evidencia. Las frases entre comillas son un guion oral sencillo; las notas técnicas sirven para responder preguntas.

## Resumen del proyecto en una frase

Construimos una aplicación web local para consultar aeropuertos de Colombia y crear, consultar, editar y eliminar itinerarios personales; el sistema separa esas responsabilidades en servicios, usa HTTP para operaciones que necesitan respuesta inmediata, RabbitMQ para entregar eventos de creación y Docker Compose para iniciar la aplicación y sus dependencias en un computador.

## Reparto sugerido

| Persona | Parte | Contenido | Nivel de dificultad |
|---|---|---|---|
| Julián | 1 | Problema, interfaz, API, CRUD, Swagger, SonarQube, Locust y demo | Más accesible; coincide con lo que ya mostró y practicó |
| Integrante 2 | 2 | Arquitectura, módulos, HTTP, eventos, bases de datos, Adapter, Outbox y resiliencia | Diseño y código |
| Integrante 3 | 3 | Jira, GitHub, PR, Dockerfiles, Compose, pruebas, observabilidad, despliegue y brechas de rúbrica | Herramientas y operación |

Si el profesor pide cambiar el orden, se puede intercambiar el turno sin cambiar el contenido.

---

# PARTE 1 — JULIÁN: aplicación, endpoints y evidencia

## 1. Apertura y problema

### Guion oral

“Buenos días. Nuestro proyecto es un sistema de itinerarios personales. La idea es que una persona consulte aeropuertos de Colombia y pueda guardar viajes con origen, destino, fecha, duración y motivo. Lo organizamos en tres servicios principales: aeropuertos, itinerarios y notificaciones. En esta primera parte voy a mostrar qué hace la aplicación, cómo se prueba su API y qué resultados tenemos del análisis de código y de una prueba de carga.”

### Qué problema y objetivo describimos

- **Problema abordado:** demostrar en una aplicación concreta la consulta de aeropuertos y la gestión de itinerarios, aplicando APIs y separación de responsabilidades.
- **Objetivo general:** construir y ejecutar una aplicación web que permita consultar aeropuertos y administrar itinerarios personales.
- **Objetivos específicos observables:** obtener y normalizar datos de aeropuertos; ofrecer operaciones CRUD de itinerarios; guardar itinerarios en una base de datos; emitir un evento para que notificaciones procese el aviso; empaquetar los servicios para reproducir el entorno local.
- **Alcance visible:** interfaz web de navegador, APIs HTTP, persistencia, evento de creación y ejecución local con Docker Compose.
- **No afirmar como terminado:** despliegue público en Azure, CI/CD automático, cobertura de pruebas o envío de correo real. Esas capacidades no están demostradas en esta versión.

## 2. Recorrido en pantalla: qué mostrar primero

1. Mostrar Docker Desktop o la terminal y ejecutar `docker compose ps` desde la carpeta del proyecto. Esto demuestra qué contenedores están activos. La salida debe revisarse en ese momento; el estado puede cambiar.
2. Abrir `http://localhost:8000`. El puerto 8000 es la entrada por Nginx Gateway y muestra la interfaz que entrega Airport Service.
3. Explicar el mapa, la selección de origen/destino y el formulario. La página está servida desde `services/airport-service/main.py`; el HTML, CSS y JavaScript están integrados en ese servicio, no existe un contenedor separado de React.
4. Crear un itinerario de demostración con datos válidos. La interfaz usa `POST` al Gateway y luego vuelve a consultar la lista para pintar la tarjeta.
5. Enseñar editar y eliminar usando las tarjetas. Si se elimina el registro mientras está en edición, la interfaz maneja el `404`, actualiza la lista y sale del modo de edición.
6. Pasar a Swagger en `http://localhost:8002/docs` y enseñar el contrato de Itinerary Service. Notification Service tiene Swagger en `http://localhost:8003/docs`.

**Cuidado para la demo:** las operaciones `POST` escriben datos en la base de datos y producen un evento. Locust también crea itinerarios persistentes. No ejecutar carga si no quieren que se agreguen más registros durante la presentación.

## 3. Qué es un endpoint y cómo contar el CRUD

“Un endpoint es una dirección de la API, junto con el método HTTP que indica qué operación pedimos. Por ejemplo, `GET` consulta y `POST` crea. La interfaz y Swagger envían solicitudes HTTP; FastAPI valida la entrada, ejecuta reglas y devuelve una respuesta con un código de estado y, normalmente, JSON.”

| Método y ruta | Acción | Ejemplo de respuesta/resultado |
|---|---|---|
| `GET /api/itineraries` | Lista itinerarios | `200 OK` y una lista JSON; `[]` si no hay registros |
| `POST /api/itineraries` | Crea un itinerario | `201 Created` y el objeto creado con su identificador |
| `GET /api/itineraries/{itinerary_id}` | Consulta uno por ID entero | `200 OK`; `404` si ese ID no existe |
| `PATCH /api/itineraries/{itinerary_id}` | Actualiza los campos enviados | `200 OK`; los campos omitidos conservan su valor actual |
| `DELETE /api/itineraries/{itinerary_id}` | Elimina uno por ID entero | `204 No Content`; `404` si ya no existe |
| `GET /api/notifications` | Consulta el historial de notificaciones | `200 OK`; `simulated_sent` significa simulado, no correo real |
| `GET /api/airports` | Consulta aeropuertos | Entrega catálogo normalizado; algunas rutas de Airport se excluyen de Swagger |

### Qué campos viajan en el `POST`

El esquema de creación usa `user_name`, `origin_airport_id`, `destination_airport_id`, `travel_date`, `duration_minutes` y `purpose`. Los IDs de aeropuerto son enteros. FastAPI/Pydantic valida el tipo y el formato, y el caso de uso revisa reglas como que origen y destino sean distintos y que ambos aeropuertos existan.

Ejemplo didáctico (usen IDs que existan en el catálogo que muestre su aplicación):

```json
{
  "user_name": "Julian",
  "origin_airport_id": 9,
  "destination_airport_id": 7,
  "travel_date": "2026-11-10",
  "duration_minutes": 90,
  "purpose": "Trabajo"
}
```

### Códigos HTTP explicados fácil

| Código | Significado para esta demo |
|---|---|
| `200` | La consulta o actualización se completó correctamente. |
| `201` | El servidor creó un itinerario. |
| `204` | El servidor eliminó el itinerario; por diseño no devuelve contenido. |
| `404` | No encontró el itinerario o aeropuerto solicitado. |
| `422` | El cuerpo o parámetro no cumple el esquema o una validación de entrada. |
| `502/503` | Puede indicar que un servicio dependiente no responde o que el proxy no logra enrutar; revisar logs y salud de dependencias. |

## 4. Swagger: cómo mostrarlo y qué prueba

“Swagger UI se genera desde el esquema OpenAPI de FastAPI. Me sirve para ver rutas, parámetros, formato del JSON, respuestas esperadas y probar una llamada sin escribir un cliente aparte. Swagger no sustituye las pruebas automatizadas; es una herramienta para explorar el contrato.”

Pasos:

1. Abrir `http://localhost:8002/docs`.
2. Expandir `POST /api/itineraries`, seleccionar **Try it out**, pegar un JSON válido con dos aeropuertos distintos y presionar **Execute**.
3. Señalar Request URL, código de respuesta `201` y Response body. Ese body incluye el ID recién generado.
4. Usar ese ID entero en `GET /api/itineraries/{itinerary_id}`, luego `PATCH` con un campo como `duration_minutes`, y finalmente `DELETE` si desean completar el ciclo.
5. Mostrar `http://localhost:8003/docs` para el endpoint de notificaciones.

Las rutas de Airport se declaran con `include_in_schema=False`; por eso la API de aeropuertos puede responder aunque no aparezca como operación en ese Swagger. No digan que todos los endpoints aparecen documentados en una sola pantalla.

## 5. SonarQube: análisis de calidad

### Guion oral

“SonarQube analiza el código de forma estática: busca patrones de errores, riesgos y mantenibilidad. No ejecuta las pruebas unitarias ni reemplaza la revisión humana. El scanner envía el análisis al servidor local y después revisamos el dashboard. En la corrida que observamos, el análisis terminó exitosamente y la Quality Gate pasó, pero todavía aparecen hallazgos y cobertura de cero; por eso no decimos que el código esté perfecto.”

### Qué significa cada indicador

- **Bug/confiabilidad:** patrón que puede causar comportamiento incorrecto o fallo.
- **Vulnerabilidad/seguridad:** patrón con posible impacto de seguridad que se debe revisar y priorizar.
- **Code smell/mantenibilidad:** deuda o complejidad que dificulta modificar el código; no siempre es un bug funcional.
- **Cobertura:** proporción de líneas o condiciones ejecutadas por pruebas reportadas al análisis. Si no se importa un reporte de cobertura, Sonar puede mostrar `0 %`; no significa automáticamente que no se haya ejecutado ninguna prueba.
- **Duplicaciones:** proporción de código repetido detectado.
- **Quality Gate:** conjunto de condiciones de calidad configuradas para declarar si el análisis pasa. `Passed` no significa cero issues.

### Evidencia real que se mostró

El dashboard compartido mostró **Quality Gate: Passed**, aproximadamente **4.6k líneas**, **4 issues de seguridad**, **2 de confiabilidad**, **2 de mantenibilidad**, **0.0 % de cobertura** y **1.5 % de duplicación**. Los valores son una captura de un análisis en ese momento y podrían cambiar si se vuelve a analizar el código.

El scanner también mostró advertencias: asumió Python 3.10–3.14 porque no se fijó versión para el análisis y detectó archivos que parecían pruebas, pero no tenía `sonar.tests` configurado. Un intento posterior de pasar opciones `-D...` con Pysonar falló; por tanto, no afirmemos que esos avisos quedaron corregidos.

### Cómo abrir y ejecutar con cuidado

SonarQube se ejecuta en un contenedor Docker separado, no como servicio del Compose principal. La interfaz local es `http://localhost:9000`. Si el contenedor ya existe pero está detenido:

```powershell
docker start personal-itinerary-system-sonarqube-1
docker ps --filter "name=sonarqube"
```

Desde la raíz del repositorio, usar el scanner que instalaron. No pegar ni mostrar el token en una grabación, presentación o archivo versionado. Si el scanner instalado toma `SONAR_TOKEN` del entorno:

```powershell
$env:SONAR_TOKEN = Read-Host "Pega el token de SonarQube"
pysonar --sonar-host-url=http://localhost:9000 --sonar-project-key=Aeropuerto-Itinerario
Remove-Item Env:SONAR_TOKEN
```

Pysonar admite propiedades del análisis desde argumentos de CLI, variables de entorno y configuración de proyecto; ver la [documentación oficial de SonarScanner for Python](https://docs.sonarsource.com/sonarqube-server/analyzing-source-code/scanners/sonarscanner-for-python). La forma anterior usa `SONAR_TOKEN` para evitar guardar el secreto dentro del comando o del repositorio.

Después revisar la salida final del scanner y actualizar el dashboard en el navegador. Si Pysonar pide el token de otra forma, seguir la sintaxis que muestre la versión instalada. **No reusar comandos antiguos que incluyen un token literal**: el token ya se compartió en el chat y debe tratarse como expuesto; rotenlo desde SonarQube antes de volverlo a usar.

## 6. Locust: prueba de carga observada

### Guion oral

“Locust simula usuarios virtuales que hacen solicitudes a la aplicación. En la ejecución que mostramos usamos 10 usuarios; Locust envió solicitudes a aeropuertos, itinerarios y salud. La captura registró 96 solicitudes, cero fallidas y cerca de 4.5 solicitudes por segundo. Es una prueba pequeña en nuestro PC, no una prueba de capacidad máxima ni una prueba de estrés.”

### Qué hace el escenario actual

El archivo `performance/locustfile.py` define al usuario simulado. En su inicio hace una consulta de preparación a `/api/airports`. Sus tareas consultan itinerarios, consultan aeropuertos, crean itinerarios y revisan `/health`, con pesos distintos y pausas de 1 a 3 segundos. Los `POST` crean datos reales y persistentes. `performance/README.md` contiene el procedimiento.

### Cifras de la captura compartida

| Solicitud | Cantidad observada | p95 aproximado en captura |
|---|---:|---:|
| `GET /api/airports` | 20 | 460 ms |
| Preparación `GET /api/airports (setup)` | 10 | 2,500 ms |
| `GET /api/itineraries` | 48 | 17 ms |
| `GET /health` | 9 | 7 ms |
| `POST /api/itineraries` | 9 | 480 ms |
| **Total mostrado** | **96** | **0 fallas; ~4.5 RPS agregadas** |

El p95 es el tiempo por debajo del cual terminó el 95 % de las solicitudes en esa muestra. El total se ve afectado por la consulta de preparación, que fue la más lenta; separen resultados por endpoint para explicar el CRUD. La medición es de la captura compartida por el equipo, no una medición que se acaba de repetir al preparar este documento.

### Ejecutar la demo de Locust

Desde la raíz del proyecto:

```powershell
py -m pip install -r requirements-load.txt
py -m locust -f performance/locustfile.py --host http://localhost:8000
```

Abrir `http://localhost:8089`, introducir **10** usuarios para replicar el nivel de concurrencia de la captura, indicar una tasa de inicio adecuada para un PC local y comenzar. Locust permite ver Statistics, Charts, Failures y Exceptions. Detener la ejecución antes de seguir con la exposición. Este escenario es una demostración de carga; para llamarlo prueba de estrés habría que aumentar la intensidad de forma controlada, definir una duración y un criterio de saturación, medir recursos del host y acordar umbrales.

## 7. Cierre de Julián

“Con esto vimos el sistema desde el punto de vista del usuario y del contrato HTTP. El CRUD funciona a través de la API, SonarQube nos da observaciones de calidad y Locust nos permite simular tráfico. Ahora mi compañero explicará cómo se reparten esas responsabilidades por dentro y cómo se comunican los servicios.”

---

# PARTE 2 — INTEGRANTE 2: arquitectura y flujo de datos

## 8. Componentes y responsabilidades

| Componente | Responsabilidad | Dónde buscar evidencia |
|---|---|---|
| Airport Service | Sirve la interfaz, consulta el proveedor externo de aeropuertos y normaliza el catálogo | `services/airport-service/main.py`; `services/airport-service/app/` |
| Itinerary Service | Valida reglas del itinerario y expone el CRUD | `services/itinerary-service/main.py`; `app/domain/`, `app/application/`, `app/infrastructure/` |
| Notification Service | Consume evento de itinerario y guarda registro de notificación simulada | `services/notification-service/consumer.py`, `main.py`, `app/` |
| Nginx Gateway | Da una entrada local común y enruta solicitudes a los servicios | `infra/nginx/nginx.conf` |
| PostgreSQL | Guarda itinerarios y notificaciones, cada contexto en su propia instancia | `docker-compose.yml`, migraciones de cada servicio |
| RabbitMQ | Transporta eventos de creación de itinerarios al consumidor | `infra/rabbitmq/definitions.json`, `rabbitmq.conf`, publisher y consumer |
| Redis | Infraestructura declarada para caché; no está conectado al flujo visible actual de aeropuertos | `docker-compose.yml`; paquete compartido |

## 9. Diagrama de contexto

```text
Persona usuaria
    │ navegador: HTML/CSS/JavaScript
    ▼
Nginx Gateway :8000 ───────► Airport Service :8010 ───────► API Colombia
    │                              │                         proveedor externo
    ├── /api/itineraries ─────► Itinerary Service :8000
    │                              ├── HTTP ───────────────► Airport Service
    │                              ├── SQL ────────────────► PostgreSQL Itinerary
    │                              └── Outbox/publisher ───► RabbitMQ
    │                                                          │ evento
    └── /api/notifications ◄──── Notification Service ◄────────┘
                                      │
                                      └── SQL ───────────────► PostgreSQL Notification
```

Los puertos después del nombre de un servicio son los puertos internos de la red Compose. Los puertos publicados al PC están limitados a `127.0.0.1`. En particular, el Itinerary Service escucha internamente en 8000 y el host lo publica como 8002; por eso las URLs directas de Swagger y la del Gateway no son la misma.

## 10. Recorrido de una creación de itinerario

1. La persona envía el formulario web o una solicitud desde Swagger.
2. Nginx recibe la solicitud por el puerto local 8000 y la enruta a Itinerary Service.
3. FastAPI/Pydantic valida estructura y tipos del cuerpo. `ItineraryService` aplica reglas de negocio: IDs de origen y destino distintos y existentes.
4. `HttpAirportCatalog` hace dos consultas HTTP concurrentes al servicio de aeropuertos. El caso de uso no depende de Nginx para esa comunicación: usa DNS interno de Compose.
5. El repositorio persiste el itinerario y registra el evento pendiente en Outbox en la transacción del contexto de itinerarios.
6. La API responde con `201 Created`. El procesamiento del aviso es asíncrono: el publisher envía `ItineraryCreatedEvent` a RabbitMQ.
7. Notification Service recibe el evento, evita repetir un mismo `event_id` y almacena la notificación con estado simulado.

**Versión sencilla:** “Primero validamos que la ruta tenga sentido; después guardamos el viaje. El aviso va por una cola aparte para que la respuesta al usuario no tenga que esperar a que se procese.”

## 11. HTTP frente a eventos

- **HTTP sincrónico:** el emisor espera respuesta. Se usa para CRUD y para comprobar que los aeropuertos referenciados existen. La validación necesita conocer el resultado antes de guardar.
- **RabbitMQ asíncrono:** el productor publica un mensaje y el consumidor lo procesa aparte. Se usa para notificar la creación; desacopla el CRUD del trabajo de Notification.
- **Límite eventual:** una respuesta `201` confirma la creación del itinerario, no que un correo se haya enviado. La notificación actual es un registro simulado.
- **RabbitMQ no es la base de datos de negocio:** transporta y enruta mensajes. PostgreSQL conserva itinerarios y notificaciones.

## 12. Hexagonal y Adapter, explicados sin exagerar

### Arquitectura hexagonal

“En el centro están las reglas de negocio. Los puertos son contratos que dicen qué necesita el caso de uso; los adaptadores conectan esos contratos con HTTP o con almacenamiento. Así se reduce la dependencia del centro respecto a los detalles externos.”

En Itinerary se ve con más claridad:

- `services/itinerary-service/app/domain/itinerary.py`: entidad del dominio.
- `services/itinerary-service/app/domain/ports.py`: protocolos `ItineraryRepository` y `AirportCatalog`.
- `services/itinerary-service/app/application/use_cases.py`: `ItineraryService`, casos de uso/reglas de aplicación.
- `services/itinerary-service/app/infrastructure/airport_http.py`: adaptador que consulta Airport por HTTP.
- `services/itinerary-service/app/infrastructure/repository.py` y `orm.py`: persistencia/ORM.
- `services/itinerary-service/main.py`: API HTTP de entrada y composición de dependencias.

No decir que todos los servicios implementan un hexágono idéntico y completo. La rúbrica pide arquitectura hexagonal por servicio; el estado del código es **parcial y desigual**, especialmente porque Airport Service concentra más lógica en su `main.py`.

### Adapter: qué existe realmente

Hay dos ejemplos que permiten explicar el concepto sin inventar clases:

1. `HttpAirportCatalog` implementa el puerto `AirportCatalog` que consume el caso de uso de Itinerary. Traduce la consulta de existencia a una llamada HTTP al servicio Airport.
2. `normalize_airport` en `services/airport-service/main.py` transforma el formato externo de API Colombia a la estructura que usa la aplicación y maneja coordenadas mal ordenadas.

`normalize_airport` es una función, no una clase separada llamada `ApiColombiaAirportAdapter`. El comportamiento de adaptación está presente; el aislamiento formal del adaptador externo en un módulo propio podría mejorarse.

### Alternativas y compensaciones

| Decisión | Motivo | Costo/limitación aceptada |
|---|---|---|
| Servicios separados | Mostrar límites de responsabilidad y comunicación HTTP/eventos | Más procesos, configuración y fallas de red que un monolito |
| HTTP para validar IDs | Se necesita saber si existen los aeropuertos antes de guardar | Itinerary depende de la disponibilidad de Airport al crear/editar |
| RabbitMQ para avisos | No hacer que el CRUD espere al procesamiento de Notification | Se requiere broker, consumidor, cola y tratamiento de reintentos |
| Outbox | Reducir el riesgo de guardar el viaje y perder su evento en un fallo entre sistemas | Aumenta tablas/código operativo y requiere publicar pendientes |
| PostgreSQL por contexto | Mantener datos de cada servicio separados | Más instancias/volúmenes y más administración local |
| FastAPI | API Python, validación y OpenAPI/Swagger generados desde modelos | La documentación depende de configurar correctamente el esquema; no todas las rutas se exponen |
| Docker Compose central | Levantar el entorno local completo con una orden | No cumple literalmente “un Compose por cada servicio” si el profesor lo interpreta como archivos separados |

## 13. Base de datos, migraciones y propiedad de datos

Itinerary Service es propietario de los itinerarios y usa PostgreSQL Itinerary. Notification Service es propietario de sus avisos y usa PostgreSQL Notification. Las migraciones Alembic de ambos se aplican al iniciar sus contenedores de aplicación. Esto evita que Notification consulte directamente tablas internas de Itinerary.

Compose también declara `postgres-airport`, pero el catálogo actual mostrado viene de API Colombia/fallback y el endpoint visible no usa esa base para servir el catálogo. Redis también está levantado para el diseño de caché, pero el flujo actual de Airport no demuestra ese uso. Sean transparentes: **contenedor declarado no significa función integrada en el flujo**.

## 14. API Colombia y fallback

Airport Service consulta el proveedor externo en `https://api-colombia.com/api/v1/airport` usando HTTPX y un timeout. Adapta el resultado para normalizar campos, códigos y coordenadas. Si el proveedor falla, la respuesta es inválida o viene vacía, puede usar un catálogo fijo de respaldo. Es una forma de evitar que la página quede sin catálogo ante una indisponibilidad externa; ese respaldo no sustituye datos persistidos ni garantiza que el proveedor siempre responda.

Las rutas de Airport se marcan `include_in_schema=False`, así que pueden funcionar desde la interfaz aunque no se vean en OpenAPI. Se puede comprobar llamando a `/api/airports` en el Gateway y comparar con el código de `main.py`.

## 15. Errores, seguridad y resiliencia: estado real

- `ItineraryService` convierte ausencia del ID en `NotFoundError`; errores comunes se traducen a respuestas HTTP estructuradas por la librería compartida.
- El cliente de Airport tiene timeout; si el servicio dependiente falla, la creación no debe continuar como si la validación hubiera sido exitosa.
- RabbitMQ usa conexión robusta, las colas durables y eventos persistentes; Outbox y reintentos reducen pérdida de publicación, no garantizan por sí solos alta disponibilidad.
- Notification hace deduplicación por `event_id` para no crear dos registros ante una entrega repetida. La entrega de mensajes suele ser “al menos una vez”; por eso deduplicar importa.
- Compose define healthchecks y `restart: unless-stopped`. Eso permite comprobar salud y reiniciar un contenedor según la política, pero no crea réplicas ni failover.
- Nginx tiene límite configurado de 15 solicitudes por segundo por IP, con ráfaga de 30 sin demora (`burst=30 nodelay`). Esto afecta una prueba local y no es una capacidad de escalado.
- Los puertos publicados se atan a localhost; la configuración es de desarrollo local, no un despliegue endurecido para Internet.
- No afirmar que JWT/autenticación está activo sólo porque exista un módulo compartido de auth: hay que mostrar el middleware/ruta que realmente lo use.

---

# PARTE 3 — INTEGRANTE 3: DevOps, Git, Compose, pruebas y cumplimiento

## 16. Qué significa el ciclo DevOps en este proyecto

“DevOps conecta la planeación, el trabajo de desarrollo, la revisión, las pruebas, el empaquetado, la ejecución y la observación. En nuestro proyecto varias etapas ya se hacen manualmente; no debemos presentar como automático lo que todavía no tiene pipeline.”

Flujo demostrado y brechas:

```text
Backlog/Jira (confirmar tablero)
        ↓ trabajo
Rama feature/fix/docs → commits → Pull Request → revisión humana
        ↓ (actualmente manual)
Docker Compose local + pruebas puntuales + SonarQube + Locust
        ↓
Demo local; todavía sin workflow de CI ni CD automático
```

## 17. Jira, iteraciones y planeación

Jira representa el backlog (trabajo pendiente), historias/tareas, responsables y sprints. El repositorio no permite confirmar cuántos sprints cerraron. **Antes de exponer, abrir el tablero del equipo y verificar número, nombre y fechas reales de iteraciones.** No convertir etapas o “fases” del README antiguo en iteraciones: son conceptos distintos.

Frase segura si no alcanzan a confirmar el dato: “El trabajo lo organizamos en Jira; para dar el número exacto de sprints prefiero mostrar el tablero y no confundir fases del proyecto con iteraciones.”

## 18. GitHub, ramas y Pull Request

### Explicación fácil de por qué hay ramas

“Una rama es una línea de trabajo dentro del mismo historial del proyecto. Las ramas comparten ancestros y commits, pero pueden avanzar de forma independiente; no son tres copias completas que el equipo mantiene a mano. Cuando el cambio está listo se abre un Pull Request para revisar el diff y decidir si entra a `main`.”

El proyecto usa nombres que describen intención, por ejemplo `feature/`, `fix/` y `docs/`. `main` guarda trabajo integrado. El PR permite ver archivos cambiados, conversación y estado de revisión. PR no significa que todo se pruebe automáticamente; eso requiere workflows de CI, que no encontramos en `.github/workflows`.

### Estado verificado para esta presentación

- Repositorio: `julianghost28-source/Proyecto`.
- PR #1, #3 y #4 se integraron; PR #2 se cerró sin merge porque duplicaba una corrección que quedó en #3.
- PR #5 desde `feature/modernizacion-frontend` hacia `main` está abierto y mergeable, pero **no está integrado**. Contiene cambios recientes de interfaz, Locust y documentación.
- Al actualizar esta guía, debe aparecer en el diff del PR #5 tras subir la rama.
- Nunca afirmar que PR #5 ya está en `main` hasta comprobar el estado actual en GitHub.

### Qué enseñar en GitHub

1. Abrir el repositorio y la pestaña **Branches** para mostrar `main` y ramas de trabajo.
2. Abrir **Pull requests** y enseñar un PR integrado y el PR #5 abierto.
3. En el PR abierto, mostrar **Files changed** para explicar revisión de cambios. La evidencia debe reflejar la rama más reciente.
4. Explicar que merge sólo lo hace la persona responsable después de revisar y que no se hace automáticamente por abrir el PR.

## 19. Dockerfile: receta de una imagen

“Dockerfile describe cómo construir la imagen de cada servicio de aplicación. En este proyecto parte de Python 3.12 slim, copia el paquete común `pis-platform` y el código del servicio, instala las dependencias y deja listo el directorio/ejecutable de la aplicación.”

Hay Dockerfile para Airport, Itinerary y Notification:

- `services/airport-service/Dockerfile`
- `services/itinerary-service/Dockerfile`
- `services/notification-service/Dockerfile`

`python:3.12-slim` reduce el tamaño respecto a una imagen general completa y mantiene la versión mayor/menor de Python. Las imágenes no equivalen al contenedor: la imagen es la plantilla construida y el contenedor es su instancia en ejecución. Para demostrar la construcción se ejecuta `docker compose up -d --build` y se inspeccionan los servicios/imágenes en `docker compose ps` o Docker Desktop.

## 20. Docker Compose: el plano del entorno local

Docker construye y ejecuta contenedores; Docker Compose lee un manifiesto YAML para definir varios servicios y cómo se conectan. El archivo central está en `docker-compose.yml`. **No hay un Compose separado por cada servicio**: hay tres Dockerfiles de aplicación y un Compose central para la aplicación y la infraestructura.

### Contenedores y función

| Servicio Compose | Imagen/configuración | Uso | Puerto en el PC |
|---|---|---|---|
| `gateway` | `nginx:1.27-alpine` | Entrada y proxy hacia APIs | `127.0.0.1:8000` |
| `airport-service` | Construida desde su Dockerfile; Python 3.12 slim | Interfaz, catálogo de aeropuertos | `127.0.0.1:8010` |
| `itinerary-service` | Construida desde su Dockerfile | CRUD/reglas de itinerarios | `127.0.0.1:8002` → puerto interno 8000 |
| `notification-service` | Construida desde su Dockerfile | API de avisos y consumidor RabbitMQ | `127.0.0.1:8003` → interno 8000 |
| `postgres-airport` | `postgres:16-alpine` | Persistencia provisionada para contexto Airport; flujo actual no la usa | No publicado |
| `postgres-itinerary` | `postgres:16-alpine` | Persistencia de itinerarios | No publicado |
| `postgres-notification` | `postgres:16-alpine` | Persistencia de notificaciones | No publicado |
| `rabbitmq` | `rabbitmq:3.13-management-alpine` | Broker de eventos; management UI | `127.0.0.1:15672`; AMQP sólo interno |
| `redis` | `redis:7-alpine` | Caché declarada/provisionada; flujo Airport actual no demuestra uso | No publicado |
| `jaeger` | `jaegertracing/all-in-one:1.62.0` | UI/almacén local de trazas | `127.0.0.1:16686` |
| `otel-collector` | `otel/opentelemetry-collector-contrib:0.109.0` | Recibe/exporta telemetría según su configuración | Puertos internos OTLP 4317/4318 |
| `prometheus` | `prom/prometheus:v2.54.1` | Scraping y consulta de métricas configuradas | `127.0.0.1:9090` |
| `grafana` | `grafana/grafana:11.2.0` | Paneles/dashboards | `127.0.0.1:3000` |

Los tags de imagen anotados son las referencias que aparecen en Compose. No todos se fijan por digest; para producción sería recomendable fijar digests y gestionar actualizaciones deliberadamente.

### Red, puertos y volúmenes

- La red bridge `itinerary-net` permite comunicación por DNS usando nombres de servicios, por ejemplo `http://airport-service:8010`.
- Los servicios que exponen puertos al PC se enlazan a `127.0.0.1`: funcionan desde ese equipo, no se ofrecen públicamente a la red por esta configuración.
- PostgreSQL, Redis y el puerto AMQP de RabbitMQ no se publican al host; los servicios se comunican por la red de Compose.
- Los volúmenes nombrados guardan datos fuera del ciclo de vida del contenedor: `airport_pg_data`, `itinerary_pg_data`, `notification_pg_data`, `redis_data`, `rabbitmq_data`, `prometheus_data`, `grafana_data`.
- `docker compose down` detiene/elimina contenedores y red del proyecto, pero conserva volúmenes. `docker compose down -v` elimina también volúmenes nombrados y puede borrar datos locales; no usarlo por accidente durante la demo.
- `infra/nginx/nginx.conf`, configuración RabbitMQ, Prometheus, OTel y Grafana se montan o consumen desde la carpeta `infra/`.

### Dependencias, healthchecks y reinicios

`depends_on` con `condition: service_healthy` hace que Compose espere a que dependencias definidas reporten salud antes de iniciar ciertos servicios. Healthchecks consultan endpoints `/health`, usan `pg_isready`, `redis-cli ping`, diagnósticos de RabbitMQ u operaciones equivalentes. `restart: unless-stopped` pide a Docker que reinicie procesos que salen, excepto si se detuvieron intencionalmente.

Eso ayuda al arranque y a detectar procesos no saludables; **no garantiza** que todas las dependencias estén operativas para cada operación, que los datos estén replicados, ni que exista alta disponibilidad.

## 21. Arranque y comprobación: paso a paso

Desde PowerShell, ubicarse en la raíz del proyecto:

```powershell
cd C:\Users\Julian\Downloads\Funcional\Proyecto
```

Si `.env` no existe, crearla desde la plantilla y completarla con valores locales:

```powershell
Copy-Item .env.example .env
```

No poner `.env` real en Git. Las credenciales de ejemplo son sólo para desarrollo local. Luego:

```powershell
docker compose up -d --build
docker compose ps
Invoke-RestMethod http://localhost:8000/health
```

- `up` crea/inicia red, volúmenes y servicios declarados.
- `-d` deja los contenedores en segundo plano.
- `--build` vuelve a construir imágenes para los servicios que usan Dockerfile.
- `ps` muestra estado, health y puertos.
- La llamada a `/health` prueba que el Gateway responde y en esta configuración enruta `/health` hacia Airport Service; no verifica por sí sola cada servicio ni el flujo de eventos.

Para revisar un fallo:

```powershell
docker compose ps
docker compose logs --tail 80 gateway
docker compose logs --tail 80 itinerary-service
docker compose logs --tail 80 notification-service
```

Para detener conservando datos locales:

```powershell
docker compose down
```

## 22. Pruebas unitarias e integración: lo que sí y lo que no

Una prueba **unitaria** revisa una unidad pequeña de código de forma aislada. Una prueba **de integración** comprueba interacción entre componentes reales, por ejemplo, API + PostgreSQL o productor + RabbitMQ + consumidor. Un `GET` manual desde Swagger comprueba una llamada y su respuesta, pero no es por sí solo una suite automatizada.

En el código fuente actual hay un test rastreado: `services/airport-service/test_airport_coords.py`, que verifica la normalización/intercambio correcto de latitud y longitud. Esta cobertura es parcial: no hay evidencia en los archivos fuente de una suite automatizada completa para CRUD, PostgreSQL, Outbox y RabbitMQ. Tampoco se debe repetir el dato antiguo de “18 pruebas”; no corresponde al test fuente revisado.

Comando desde la raíz:

```powershell
py -m pytest services/airport-service/test_airport_coords.py
```

El resultado de pytest indica las pruebas recolectadas, cuántas pasaron/fallaron y el código de salida. Ejecuten el comando antes de exponer si quieren mostrar una salida actual; este documento no afirma una ejecución hecha ahora. La versión de pytest no está fijada en las dependencias del proyecto; no inventar una versión exacta.

**Distinción para el profesor:** Locust genera solicitudes concurrentes de carga; no prueba una función de forma aislada. SonarQube analiza código estático; no ejecuta las pruebas. Swagger permite llamadas manuales; no produce por sí solo un reporte de pytest.

## 23. Observabilidad

Compose provisiona OpenTelemetry Collector, Prometheus, Grafana y Jaeger. Sus funciones generales son:

- **OpenTelemetry Collector:** recibir y enrutar telemetría con la configuración en `infra/otel-collector-config.yaml`.
- **Prometheus:** recolectar/consultar métricas a partir de objetivos configurados en `infra/prometheus/prometheus.yml`.
- **Grafana:** visualizar fuentes y dashboards configurados en `infra/grafana/`.
- **Jaeger:** explorar trazas cuando los servicios realmente las exportan.

El stack está provisionado, pero la exportación desde las aplicaciones está parcial. La presencia de contenedores saludables no demuestra que aparezcan métricas de negocio o trazas completas. En el código compartido hay instrumentación básica y configuración de telemetría; antes de decir “observabilidad completa”, comprueben en vivo que aparece una solicitud/traza de la aplicación en Jaeger, métrica en Prometheus y panel en Grafana. La formulación segura es: “Montamos la infraestructura de observabilidad; la instrumentación extremo a extremo de las aplicaciones sigue pendiente de completar y validar.”

URLs locales previstas: Prometheus `http://localhost:9090`, Grafana `http://localhost:3000`, Jaeger `http://localhost:16686`. No exponer credenciales de `.env` en pantalla.

## 24. SonarQube como proceso DevOps

SonarQube corre fuera del Compose principal en un contenedor Docker separado. El contenedor observado usa la etiqueta `sonarqube:26.11.0.134175-community` y publica el puerto local 9000. Pysonar se ejecutó desde Windows en la raíz del repositorio; la versión observada en una captura fue 1.11.0.6012. Esas versiones describen la ejecución mostrada, no una configuración reproducible fijada en el repositorio.

Secuencia conceptual:

1. Arrancar/revisar el contenedor SonarQube.
2. Abrir `http://localhost:9000` y verificar que el servidor terminó de iniciar.
3. Crear/usar el proyecto y generar un token de análisis.
4. Ejecutar Pysonar desde la raíz con host, project key y token seguro.
5. Esperar el mensaje de análisis exitoso.
6. Actualizar el dashboard y leer Quality Gate, issues, cobertura y duplicación.

SonarQube es análisis estático, no el servidor de la aplicación. Abrir el dashboard no vuelve a escanear automáticamente; el scanner debe ejecutarse otra vez después de cambios. Quality Gate Passed es el estado de las condiciones configuradas para esa corrida, no una certificación de “cero defectos”.

## 25. Despliegue: alcance y pregunta de falla

### Cómo explicarlo

“El despliegue que demostramos es local: Docker Compose construye las imágenes y levanta contenedores y dependencias en Docker Desktop. Usamos servicios, variables de entorno, red, volúmenes, healthchecks y reinicio para hacer repetible el arranque. No publicamos esta versión en Azure ni tenemos despliegue continuo configurado.”

### Si falla o se detiene algo

| Falla | Impacto probable | Qué revisar |
|---|---|---|
| Se detiene Notification Service | Endpoint de notificaciones no disponible; procesamiento/consumo se detiene temporalmente | `docker compose ps`, logs Notification y Rabbit |
| Se detiene RabbitMQ | Producer/consumer no procesa temporalmente; eventos de Outbox pueden esperar y reintentar | logs del broker, estado Outbox y logs Itinerary |
| Se detiene Airport Service | Página/API de aeropuertos falla; crear/editar itinerario no puede validar IDs | `/health`, logs Airport, proveedor externo y fallback |
| Se detiene PostgreSQL Itinerary | Operaciones CRUD de itinerario fallan | healthcheck y logs de la base; no hay failover |
| Se detiene Gateway | Puerto común 8000 falla aunque algunos servicios directos sigan respondiendo | logs y configuración Nginx; Swagger directo en 8002/8003 ayuda a aislarlo |
| Se detiene Docker Desktop/Engine o el PC | Todo el sistema local deja de atender | reiniciar Engine y luego revisar estado de Compose |

Si se inicia de nuevo Docker Compose con los volúmenes intactos, los datos persisten y los contenedores se recrean/inician según el comando. Si se eliminan volúmenes, los datos locales pueden perderse. Outbox y RabbitMQ aportan tolerancia a interrupciones de mensajería, pero este proyecto no tiene alta disponibilidad: no hay réplicas de cada servicio, clúster de base de datos ni balanceo entre varias instancias.

### Cómo demostrar que un fallo no siempre derriba todo

En una demostración controlada se puede parar **solo** Notification Service (`docker compose stop notification-service`), probar el health de Itinerary y explicar que los servicios tienen procesos separados. Para reanudar: `docker compose start notification-service`, revisar `docker compose ps` y logs. Hacerlo sólo si hay tiempo y si el equipo sabe restaurarlo. No parar la base ni borrar volúmenes durante la sustentación. La disponibilidad real de otras operaciones debe comprobarse en ese momento; no prometer que todo seguirá funcionando idénticamente.

## 26. Matriz de rúbrica y evidencia

| Requisito del profesor | Estado honesto | Dónde/evidencia | Cómo mostrarlo |
|---|---|---|---|
| Documento de arquitectura corto | Pendiente de agregar/verificar en el repo | El equipo dijo que otro integrante lo prepara; no aparece en la rama inspeccionada | Abrir el documento final cuando se integre y relacionarlo con este código |
| Microservicios con HTTP y eventos | Implementado en el flujo principal | Itinerary, Airport, Notification, publisher/consumer, RabbitMQ | Crear itinerario y mostrar evento/notificación en el historial/logs |
| Arquitectura hexagonal por servicio | Parcial; más visible en Itinerary | `app/domain`, `app/application`, `app/infrastructure`, `main.py` | Mostrar puertos `Protocol`, caso de uso y adaptador; reconocer desigualdad entre servicios |
| Patrón Adapter | Comportamiento de adaptación implementado, estructura formal parcial | `HttpAirportCatalog`, `normalize_airport` | Mostrar cómo traduce contrato/proveedor; no inventar una clase inexistente |
| Planning / backlog Jira | Debe confirmarse en Jira | Tablero/sprints del equipo, no demostrable solo con repo | Mostrar backlog e iteraciones reales |
| Repositorio Git y ramas estándar | Implementado | Repo, ramas `feature/`, `fix/`, `docs/` | Mostrar branch list e historial |
| Pull Request | Implementado como flujo; PR #5 abierto | PR #1/#3/#4 integrados; #5 aún sin merge | Mostrar diff y estado verdadero del PR |
| Pruebas unitarias | Parcial: un test fuente visible | `services/airport-service/test_airport_coords.py` | Ejecutar pytest y explicar qué valida; no llamar suite completa |
| Pruebas de integración | Pendiente/no demostradas como suite automatizada | No se identificó una suite fuente de integración | Mostrar flujo manual o reconocer pendiente |
| Pruebas de carga | Escenario Locust local ejecutado | `performance/locustfile.py`; captura con 10 usuarios, 96 requests, 0 fallas | Mostrar Statistics/Charts y aclarar límites de entorno |
| Swagger/OpenAPI | Implementado parcialmente | Itinerary `:8002/docs`, Notification `:8003/docs`; rutas Airport ocultas del schema | Ejecutar una operación y explicar códigos |
| SonarQube | Análisis local manual realizado | UI `:9000`; captura con Quality Gate Passed y hallazgos | Mostrar dashboard; aclarar cero cobertura y advertencias |
| CI automatizado en GitHub | Pendiente | No se encontró workflow bajo `.github/workflows` | Decir explícitamente que tests/scanner se ejecutan manualmente |
| Despliegue continuo (CD) | Pendiente | Sin pipeline ni entorno remoto demostrados | Presentar Compose local como despliegue local, no CD |
| Dockerizado | Implementado para tres servicios de aplicación | Tres Dockerfiles + central `docker-compose.yml` | Mostrar Dockerfiles e imágenes/contenedores |
| Compose por cada servicio | Parcial respecto a lectura literal | Un único Compose orquesta todos los servicios | Explicar decisión y confirmar interpretación del docente |
| Diseño básico de software | Parcial/implementado en código | Límites de servicio, capas de Itinerary, contratos y flujo | Mostrar diagrama y responsabilidades |
| Observabilidad | Parcial | Stack OTel/Prometheus/Grafana/Jaeger configurado; exportación de apps incompleta | Mostrar solo datos que aparezcan realmente |
| Resiliencia | Parcial | Outbox, reintentos, colas durables, healthchecks, restart policy | Explicar que ayuda a recuperarse, no es alta disponibilidad |

## 27. Secuencia de demostración recomendada en vivo

### Antes de entrar al salón

- Abrir Docker Desktop y esperar a que Engine esté listo.
- Abrir PowerShell ya ubicado en `C:\Users\Julian\Downloads\Funcional\Proyecto`.
- Ejecutar `docker compose ps`; si servicios están detenidos, usar `docker compose up -d` (reconstruir sólo con `--build` si hubo cambios de código).
- Verificar `Invoke-RestMethod http://localhost:8000/health`.
- Abrir pestañas de `http://localhost:8000`, `http://localhost:8002/docs`, `http://localhost:8003/docs`, GitHub PR #5 y SonarQube si está activo.
- Abrir Locust sólo si quieren mostrar la prueba; su proceso se lanza en terminal y UI en `http://localhost:8089`.
- Cerrar/ocultar archivos `.env`, tokens y contraseñas.

### Orden de 8–12 minutos (ajustar al tiempo del profesor)

1. Julián presenta problema/objetivo y página funcional.
2. Julián crea/consulta/edita un itinerario desde UI o Swagger; muestra status code.
3. Julián abre SonarQube y explica una fortaleza y dos pendientes de calidad.
4. Julián abre Locust y explica resultados y límites de una prueba pequeña.
5. Integrante 2 explica diagrama, validación HTTP, evento, Adapter y Outbox.
6. Integrante 3 explica Jira/Git/PR, Dockerfile/Compose, pruebas, observabilidad y estado de CI/CD.
7. Cierre: decir qué está hecho y las mejoras priorizadas sin presentar pendientes como implementadas.

## 28. Preguntas técnicas probables (con respuestas defendibles)

### ¿Cuántas iteraciones o sprints tiene el proyecto?

“Ese número se confirma en el tablero de Jira. Las fases de desarrollo que aparecían en un README no son necesariamente sprints. Abrimos Jira y mostramos el número real para no confundir los términos.”

### ¿Las ramas son copias iguales del proyecto?

“No son tres repositorios independientes que mantengamos a mano. Son referencias a líneas de commits dentro del mismo repositorio. Todas parten de historial común, y una rama avanza mientras trabajamos en un cambio. El Pull Request compara su diferencia con la rama destino.”

### ¿Por qué usar `main` y ramas de feature/fix?

“`main` queda como línea integrada. Una rama limita el cambio mientras se desarrolla y permite revisar el diff antes del merge. Reduce el riesgo de mezclar un cambio a medio hacer; no elimina errores por sí sola.”

### ¿El PR #5 ya está en `main`?

“No. Está abierto hacia `main`; sus cambios se revisan en el PR. El estado se puede comprobar en GitHub. Por eso el profesor puede ver tanto la rama como el proceso de revisión.”

### ¿Qué diferencia hay entre Docker y Docker Compose?

“Docker construye imágenes y ejecuta contenedores. Compose describe varios contenedores y sus redes, dependencias, puertos, variables y volúmenes para levantarlos como un entorno.”

### ¿Qué hay dentro de cada contenedor?

“En los de aplicación hay una imagen base Python, dependencias y el código de cada servicio. También hay contenedores de PostgreSQL, RabbitMQ, Redis, Gateway Nginx y herramientas de observabilidad. `docker compose ps` enumera los procesos; Compose no hace un único contenedor gigante.”

### ¿Por qué el navegador usa 8000 y Swagger 8002?

“8000 es el puerto publicado del Gateway. Itinerary escucha en el puerto interno 8000, pero Compose lo publica en el host como 8002 para acceder a su Swagger directamente. Si paso por el Gateway, la ruta del CRUD está bajo `http://localhost:8000/api/itineraries`.”

### ¿Qué hace RabbitMQ en este sistema?

“Transporta el evento de creación hacia Notification Service. Itinerary guarda el viaje y deja un evento pendiente en Outbox; el publisher lo publica, el consumer lo procesa y Notification persiste un aviso simulado. Los datos del viaje siguen en PostgreSQL, no en RabbitMQ.”

### ¿El evento envía un correo real?

“No. El consumidor guarda una notificación con estado simulado. No hay integración demostrada con SMTP, SMS o proveedor externo de correo.”

### Si un contenedor falla, ¿se cae todo?

“No necesariamente. Son procesos separados, así que algunas funciones pueden seguir. Si cae Notification, el historial/consumidor se afecta; si cae Airport, la validación de nuevas rutas se afecta; si cae la base de Itinerary, el CRUD falla. Si se detiene Docker Engine o el PC, todo el entorno local se detiene. No tenemos clúster ni failover.”

### ¿Qué pasa al levantar Compose otra vez?

“Docker inicia o recrea los servicios definidos; los volúmenes nombrados conservan los datos mientras no se eliminen. Los healthchecks ayudan a ver si un proceso está listo. Si ejecutamos `down -v`, sí podemos borrar persistencia local.”

### ¿Hicieron pruebas unitarias?

“Tenemos un test fuente para normalización de coordenadas de aeropuerto y se ejecuta con Pytest. Es cobertura puntual, todavía no una suite extensa por servicio.”

### ¿Hicieron pruebas de integración?

“No tenemos una suite automatizada de integración demostrada en el repositorio actual. Sí comprobamos manualmente APIs y servicios con Compose/Swagger, pero eso no equivale a una batería automatizada de integración.”

### ¿Locust es una prueba de estrés?

“Lo que ejecutamos es una prueba de carga local con 10 usuarios virtuales. Una prueba de estrés busca aumentar carga hasta observar degradación o saturación con criterios, duración y monitoreo definidos. No afirmamos haber medido el límite máximo.”

### ¿Qué significa p95?

“El percentil 95 es el tiempo de respuesta que cubre el 95 % de las solicitudes de la muestra; un 5 % tarda más. Debemos compararlo por endpoint y bajo el mismo ambiente, no interpretarlo como garantía de producción.”

### ¿SonarQube ejecutó las pruebas?

“No. Pytest ejecuta tests. Sonar analiza el código estáticamente y puede importar reportes como cobertura si están configurados. El dashboard observado tenía cobertura cero porque no habíamos integrado un reporte de cobertura.”

### Si la Quality Gate pasó, ¿por qué hay issues?

“La Quality Gate evalúa condiciones configuradas. Puede pasar aun cuando hay issues abiertos si esos issues no rompen las condiciones definidas. Por eso explicamos el detalle y no usamos `Passed` como sinónimo de código perfecto.”

### ¿El proyecto está desplegado en Internet o Azure?

“No. Lo que demostramos se ejecuta localmente con Docker Desktop y Compose. Para publicarlo faltaría diseñar entorno, secretos, red, persistencia administrada, observabilidad, seguridad y automatización de despliegue.”

### ¿Por qué no usar un monolito?

“Para el alcance pequeño, un monolito modular sería más sencillo y barato. Elegimos servicios separados para practicar y demostrar límites de contexto, HTTP y eventos, que son parte del objetivo académico. Reconocemos el costo adicional en operación y fallas de red.”

### ¿Qué significa que el Adapter está parcial?

“El sistema traduce formatos externos y `HttpAirportCatalog` implementa un puerto, así que podemos señalar comportamiento de adaptación real. Pero el normalizador de API Colombia vive dentro de `main.py`, no como un adaptador formal aislado. Para mejorar, moveríamos ese cliente/traducción a infraestructura y añadiríamos pruebas unitarias.”

### ¿Está completa la observabilidad?

“La infraestructura base está en Compose, pero todavía debemos verificar/exportar telemetría extremo a extremo desde cada aplicación. Por eso decimos observabilidad parcial y enseñamos únicamente paneles con datos reales.”

## 29. Mejoras futuras priorizadas

1. Agregar una suite de pruebas unitarias de reglas de Itinerary y Notification, más pruebas de integración con PostgreSQL/RabbitMQ.
2. Ejecutar pruebas en GitHub Actions en cada Pull Request; después diseñar CD para un entorno real.
3. Incorporar el documento corto de arquitectura y trazar cada requisito a código/evidencia.
4. Definir de forma más explícita el patrón Adapter en Airport, separar HTTP del normalizador y añadir tests de proveedor.
5. Generar e importar cobertura a SonarQube; configurar versión Python y rutas de test usando opciones compatibles con Pysonar.
6. Completar exportación y dashboards de métricas/trazas de las aplicaciones.
7. Confirmar con el docente qué entiende por “Compose por cada servicio”; documentar o separar manifiestos si se exige literalmente.
8. Definir política de secretos, autenticación, backups, persistencia y alta disponibilidad antes de despliegue público.

## 30. Cierre conjunto

“El resultado es una aplicación funcional y dockerizada para demostración local, con tres servicios de aplicación, CRUD, integración HTTP y eventos, persistencia separada y herramientas para revisar calidad y carga. También identificamos con evidencia las brechas: cobertura y pruebas aún limitadas, integración hexagonal desigual, observabilidad parcial y ausencia de CI/CD y despliegue público. El siguiente paso es convertir las comprobaciones manuales en una pipeline automática y ampliar pruebas.”

---

# Chuleta rápida de URLs y comandos

| Uso | URL o comando |
|---|---|
| Web principal / Gateway | `http://localhost:8000` |
| Health del Gateway | `Invoke-RestMethod http://localhost:8000/health` |
| Itinerary Swagger | `http://localhost:8002/docs` |
| Notification Swagger | `http://localhost:8003/docs` |
| Airport directo | `http://localhost:8010` |
| SonarQube | `http://localhost:9000` |
| Locust UI | `http://localhost:8089` |
| Prometheus | `http://localhost:9090` |
| Grafana | `http://localhost:3000` |
| Jaeger | `http://localhost:16686` |
| Estado Compose | `docker compose ps` |
| Logs de un servicio | `docker compose logs -f itinerary-service` |
| Iniciar/reconstruir entorno | `docker compose up -d --build` |
| Detener y conservar volúmenes | `docker compose down` |
| Test unitario fuente actual | `py -m pytest services/airport-service/test_airport_coords.py` |
| Locust | `py -m locust -f performance/locustfile.py --host http://localhost:8000` |

**Antes de presentar:** confirmar en Jira el número de iteraciones; revisar en vivo el estado del PR #5; actualizar las capturas si el dashboard de Sonar o la ejecución de Locust cambiaron; no mostrar secretos; describir como pendientes las integraciones parciales.
