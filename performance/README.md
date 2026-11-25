# Prueba de carga local con Locust

Este simulador representa usuarios que consultan aeropuertos e itinerarios y, ocasionalmente, crean un itinerario mediante el gateway (`http://localhost:8000`). Los itinerarios creados quedan guardados en la base de datos y generan los eventos normales de la aplicación. Usa solo el entorno local de Docker; no lo apuntes a producción.

## 1. Asegura que la aplicación esté levantada

Desde la carpeta raíz del proyecto:

```powershell
docker compose up -d
```

## 2. Instala Locust una vez

```powershell
py -m pip install -r requirements-load.txt
```

## 3. Inicia Locust

Desde la carpeta raíz del proyecto:

```powershell
py -m locust -f performance/locustfile.py --host http://localhost:8000
```

Abre `http://localhost:8089`. Para una primera demostración usa:

- **Number of users:** 5
- **Spawn rate:** 1 usuario por segundo
- **Host:** `http://localhost:8000`

Pulsa **Start** y déjalo correr alrededor de un minuto. Luego pulsa **Stop** para cerrar la medición. Locust muestra solicitudes, fallos, tiempos de respuesta y solicitudes por segundo.

## Qué hace cada usuario simulado

- Consulta la lista de itinerarios con `GET /api/itineraries`.
- Consulta aeropuertos con `GET /api/airports`.
- Revisa la salud del gateway con `GET /health`.
- En una parte de sus interacciones, crea un itinerario con `POST /api/itineraries`.

La pausa aleatoria de 1 a 3 segundos entre tareas evita que cada usuario envíe solicitudes continuamente. Empieza con pocos usuarios y sube gradualmente si quieres comparar resultados.

## Datos que genera

Los `POST` exitosos crean registros de prueba persistentes. Al terminar, puedes identificarlos por el nombre `Carga Locust ...` y eliminarlos desde la interfaz o con el endpoint `DELETE /api/itineraries/{id}`. No borres datos que no reconozcas.
