# Trazabilidad de la rúbrica y estado del proyecto

Esta matriz refleja el código y las ejecuciones observadas en la rama local `feature/modernizacion-frontend` a 24 de noviembre de 2026. Se separa lo implementado de lo ejecutado y de lo que está pendiente de integración en GitHub. No convierte fases del README en iteraciones de Jira.

| Punto | Estado actual | Evidencia / comentario |
| --- | --- | --- |
| Documento corto de arquitectura | Pendiente de incorporar/verificar | El equipo indicó que un integrante lo prepara. No se encontró el documento dentro del repositorio local inspeccionado. |
| Microservicios con HTTP y eventos | Implementado | Airport, Itinerary y Notification; HTTP para lectura/validación/CRUD, RabbitMQ para `ItineraryCreatedEvent`. |
| Arquitectura hexagonal por servicio | Parcial | Itinerary tiene dominio, puertos, casos de uso e infraestructura; la separación no está igual de completa en Airport y Notification. |
| Patrón Adapter | Implementación visible, estructura parcial | `HttpAirportCatalog` adapta la consulta HTTP detrás del puerto. `normalize_airport` transforma el JSON de API Colombia, pero vive en `services/airport-service/main.py` y no en una clase adaptadora separada. |
| Jira / backlog / iteraciones | Verificar con el tablero | No se puede confirmar desde el repositorio cuántos sprints/iteraciones hay. Las 12 fases del README anterior no son un conteo de iteraciones. |
| Ramas y commits | Implementado | Hay ramas `feature/`, `fix/` y `docs/`; conservar `main` para integrar trabajo revisado. |
| Pull requests | Implementado como flujo | PR #1, #3 y #4 integrados; PR #2 cerrado sin merge por duplicidad. La rama `feature/modernizacion-frontend` todavía no tiene PR. |
| Pruebas unitarias | Parcial | Esta rama contiene el test fuente `services/airport-service/test_airport_coords.py` para normalización de coordenadas. No contiene la suite de 18 casos mencionada en un documento anterior. |
| Pruebas de carga | Ejemplo local implementado y ejecutado | `performance/locustfile.py`; ejecución observada con 10 usuarios, 96 requests y 0 fallos. Los POST crean datos persistentes; cifras son de una prueba local puntual. |
| Swagger / OpenAPI | Implementado parcialmente | Swagger de Itinerary en `http://localhost:8002/docs`, Notification en `http://localhost:8003/docs`. Algunas rutas de Airport se excluyen del esquema OpenAPI. |
| SonarQube | Análisis manual local | Último dashboard revisado: Quality Gate Passed, hallazgos abiertos, cobertura 0 % y avisos. Configuración adicional de `sonar.python.version`/`sonar.tests` no quedó aplicada: Pysonar rechazó los argumentos `-D` usados. |
| CI / build / pruebas automáticas | Pendiente | No se encontró `.github/workflows`; el análisis y las pruebas se ejecutan manualmente. |
| Despliegue continuo | Pendiente | El despliegue observado es local mediante Compose; no hay despliegue automático ni publicación a Azure. |
| Dockerfiles de servicios | Implementado | Cada uno de los tres servicios de aplicación tiene su Dockerfile. |
| Docker Compose por servicio | Parcial frente a requisito literal | Actualmente hay un Compose central que arranca servicios y dependencias; no hay un archivo Compose separado por servicio. |
| Diseño básico / separación de responsabilidades | Parcial/implementado | Microservicios con responsabilidades distintas, contratos HTTP, dominio/casos de uso en Itinerary y adaptadores. Documento formal sigue pendiente de integrar. |
| Observabilidad | Parcial | Compose provisiona OpenTelemetry Collector, Prometheus, Grafana y Jaeger. No afirmar integración completa de telemetría de aplicaciones sin validar exportación y dashboards. |
| Resiliencia | Parcial | Outbox, publicación con reintento y cola durable; no hay réplicas ni alta disponibilidad. Un contenedor detenido puede afectar la función que presta. |

## Evidencia local y comandos

### Compose y servicios

```powershell
docker compose up -d --build
docker compose ps
Invoke-RestMethod http://localhost:8000/health
```

El proceso local usa un Compose central. `docker compose down` conserva volúmenes; `docker compose down -v` elimina volúmenes y datos.

### Prueba unitaria presente

```powershell
py -m pytest services/airport-service/test_airport_coords.py
```

### Prueba de carga Locust

```powershell
py -m pip install -r requirements-load.txt
py -m locust -f performance/locustfile.py --host http://localhost:8000
```

Interfaz: `http://localhost:8089`. La ejecución observada de 10 usuarios no demuestra capacidad máxima del sistema.

### SonarQube

La instancia local se encontraba en `http://localhost:9000` y se ejecutó el scanner desde la carpeta del repositorio. No se debe subir el token. La pantalla de resultados y el log confirman un análisis exitoso anterior, con Quality Gate Passed y avisos de análisis. El intento reciente de agregar propiedades `-D` no fue aceptado por Pysonar, así que no se marca corregido.

## GitHub verificado

- `main` contiene la funcionalidad integrada hasta la modernización de tarjetas.
- PR #1 (`docs/docker-only-startup`), #3 (`fix/edicion-itinerario`) y #4 (`feature/tarjetas-itinerarios`) están integrados.
- PR #2 (`fix/handle-deleted-itinerary-while-editing`) se cerró sin integrarse; el cambio equivalente quedó en PR #3.
- `feature/modernizacion-frontend` está publicada en GitHub con un commit que todavía no tiene PR.
- Los archivos locales de Locust y esta documentación no se consideran en GitHub hasta quedar añadidos a un commit de rama y enviados.

## Pendientes antes de afirmar cumplimiento total

1. Incorporar el documento formal de arquitectura cuando el integrante lo termine.
2. Confirmar con el tablero Jira el número real de iteraciones/sprints.
3. Definir y agregar CI para pruebas/build en PR; implementar CD solo cuando exista un entorno de despliegue configurado.
4. Acordar con el docente si “Docker Compose por cada servicio” exige varios manifiestos separados o si acepta un Compose central.
5. Aumentar la suite unitaria fuente y automatizar su ejecución.
6. Configurar importación de cobertura y corregir los avisos del scanner con propiedades persistentes verificadas.
7. Completar y validar exportación de métricas/trazas desde los servicios al stack de observabilidad.
