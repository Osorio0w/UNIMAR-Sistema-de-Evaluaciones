"""
database.py
----------------
CICLO 2 - Capa de Conexión a la Base de Datos
Metodología: Espiral | Cuadrante 3 - Desarrollo y Verificación

Usa el módulo `sqlite3` de la librería estándar de Python (sin ORM
externo) para garantizar que el proyecto corra en cualquier entorno
sin dependencias adicionales que instalar. La separación en
`repository.py` (siguiente archivo) hace que, si el equipo decide más
adelante migrar a SQLAlchemy u otro ORM, el cambio sea localizado:
solo cambiaría CÓMO se consulta, no la interfaz que usa el resto de
la aplicación (app.py y quiz_engine.py no se verían afectados).
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "quiz.db"

ESQUEMA_SQL = """
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    rol TEXT NOT NULL CHECK (rol IN ('estudiante', 'profesor'))
);

CREATE TABLE IF NOT EXISTS cuestionarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo TEXT NOT NULL,
    descripcion TEXT,
    creado_por_id INTEGER,
    FOREIGN KEY (creado_por_id) REFERENCES usuarios(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS preguntas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cuestionario_id INTEGER NOT NULL,
    tipo TEXT NOT NULL CHECK (tipo IN ('opcion_unica', 'verdadero_falso', 'opcion_multiple')),
    enunciado TEXT NOT NULL,
    puntos REAL NOT NULL DEFAULT 1.0,
    FOREIGN KEY (cuestionario_id) REFERENCES cuestionarios(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS opciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pregunta_id INTEGER NOT NULL,
    clave TEXT NOT NULL,
    texto TEXT NOT NULL,
    es_correcta INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (pregunta_id) REFERENCES preguntas(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS intentos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL,
    cuestionario_id INTEGER NOT NULL,
    puntaje_total REAL NOT NULL,
    puntaje_maximo REAL NOT NULL,
    porcentaje REAL NOT NULL,
    detalle_json TEXT NOT NULL,
    fecha TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    FOREIGN KEY (cuestionario_id) REFERENCES cuestionarios(id) ON DELETE CASCADE
);
"""


def obtener_conexion() -> sqlite3.Connection:
    """
    Abre una conexión a SQLite con configuración segura:
    - row_factory=sqlite3.Row -> permite acceder a columnas por nombre
      (fila["campo"]) en vez de por índice (fila[0]), mucho más legible.
    - PRAGMA foreign_keys=ON  -> SQLite NO valida llaves foráneas por
      defecto; hay que activarlo explícitamente en CADA conexión nueva.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def inicializar_esquema():
    """Crea las tablas si no existen. Operación idempotente (segura de repetir)."""
    conn = obtener_conexion()
    conn.executescript(ESQUEMA_SQL)
    conn.commit()
    conn.close()
