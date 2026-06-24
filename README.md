# Ciclo 2 + Ciclo 3 — Motor de Cuestionarios, Persistencia y Frontend

## Estructura
```
ciclo2_app/
├── quiz_engine.py        # Ciclo 1 - NO modificado, lógica de evaluación pura
├── database.py           # Ciclo 2 - Conexión SQLite + esquema de tablas
├── repository.py         # Ciclo 2 - Adaptador: filas SQL <-> objetos de quiz_engine.py
├── seed.py                # Ciclo 2 - Pobla la BD con un cuestionario de prueba
├── app.py                 # Ciclo 2/3 - API Flask + ruta que sirve el frontend
├── templates/
│   └── index.html         # Ciclo 3 - Interfaz (Tailwind CSS vía CDN)
└── static/js/
    └── app.js              # Ciclo 3 - Lógica de interacción (fetch a la API)
```

## Cómo correrlo

```bash
# 1. Instalar Flask (única dependencia externa; sqlite3 viene con Python)
pip install flask

# 2. Crear y sembrar la base de datos
python3 seed.py

# 3. Levantar el servidor
python3 app.py
```

Abre **http://127.0.0.1:5000/** en el navegador: ahí está la interfaz completa
(formulario de preguntas → calificación → vista de resultados).

## Endpoints de la API (siguen disponibles para pruebas con curl/Postman)

### `GET /cuestionario/<id>`
Devuelve las preguntas **sin** indicar cuál opción es correcta.

### `POST /evaluar/<id>`
Recibe y evalúa las respuestas del usuario.

```bash
curl -X POST http://127.0.0.1:5000/evaluar/1 \
  -H "Content-Type: application/json" \
  -d '{"respuestas": {"1": "b", "2": "f", "3": ["a", "c"]}}'
```

## Notas de diseño (para tu informe académico)

- **Sin ORM externo a propósito**: se usó `sqlite3` de la librería estándar
  para que el proyecto corra sin dependencias adicionales más allá de Flask.
  La capa `repository.py` aísla todo el SQL, así que migrar a SQLAlchemy en
  el futuro no afectaría a `app.py` ni a `quiz_engine.py`.
- **`quiz_engine.py` no fue tocado** desde el Ciclo 1: se reutiliza tal cual.
- **`app.py` solo recibió una ruta nueva** (`GET /`) en el Ciclo 3; los
  endpoints `/cuestionario` y `/evaluar` verificados en el Ciclo 2 no se
  modificaron.
- **Frontend vanilla JS, sin build step**: no requiere npm/webpack, solo
  Tailwind vía CDN. Ideal para un entregable universitario que se debe
  poder ejecutar en cualquier máquina sin configuración adicional.
- **Toda la lógica de calificación vive en el servidor**: el JS del
  frontend solo arma el payload y muestra la respuesta; nunca decide por
  sí mismo si una respuesta es correcta.

