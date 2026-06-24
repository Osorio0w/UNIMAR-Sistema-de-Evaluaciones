"""
repository.py
----------------
CICLO 2 - Capa de Mapeo (Adaptador BD <-> Dominio)
Metodología: Espiral | Cuadrante 3 - Desarrollo y Verificación

Esta es la pieza CLAVE del Ciclo 2: traduce filas de SQLite a los
objetos de dominio definidos en quiz_engine.py (PreguntaOpcionUnica,
PreguntaVerdaderoFalso, PreguntaOpcionMultiple), y produce además una
versión "segura" de esos datos para enviar al frontend.

Por qué existe esta capa por separado:
- quiz_engine.py debe seguir siendo agnóstico de base de datos: no se
  modifica en este ciclo (regla dura de la metodología en espiral, no
  se toca código ya verificado en un ciclo anterior).
- app.py (Flask) no debe saber CÓMO se arma un objeto Pregunta a partir
  de filas SQL, solo pedirlo ya construido.

Mitiga el Riesgo R1 (integridad de datos): valida que las preguntas de
tipo 'opcion_unica' / 'verdadero_falso' tengan EXACTAMENTE una opción
correcta antes de construir el objeto de dominio, y que 'opcion_multiple'
tenga al menos una.
"""

from database import obtener_conexion
import json
from quiz_engine import (
    PreguntaOpcionUnica,
    PreguntaVerdaderoFalso,
    PreguntaOpcionMultiple,
)


class CuestionarioNoEncontrado(Exception):
    """Se lanza cuando se pide un cuestionario cuyo id no existe en la BD."""
    pass


class ErrorIntegridadPregunta(Exception):
    """
    Se lanza cuando los datos de una pregunta en la BD son inconsistentes
    con las reglas del dominio (ej. una opción única con 0 o 2 respuestas
    correctas). Es un error de DATOS, no de la lógica del estudiante.
    """
    pass


def _construir_pregunta_dominio(pregunta_row, opciones_rows):
    """Convierte una fila `preguntas` + sus filas `opciones` en un objeto de dominio."""
    opciones_dict = {op["clave"]: op["texto"] for op in opciones_rows}
    correctas = {op["clave"] for op in opciones_rows if op["es_correcta"]}
    tipo = pregunta_row["tipo"]
    pid = pregunta_row["id"]

    if tipo == "opcion_unica":
        if len(correctas) != 1:
            raise ErrorIntegridadPregunta(
                f"Pregunta {pid} (opcion_unica) debe tener EXACTAMENTE 1 "
                f"opción correcta, tiene {len(correctas)}."
            )
        return PreguntaOpcionUnica(
            id_pregunta=pid,
            enunciado=pregunta_row["enunciado"],
            opciones=opciones_dict,
            respuesta_correcta=next(iter(correctas)),
            puntos=pregunta_row["puntos"],
        )

    elif tipo == "verdadero_falso":
        if len(correctas) != 1:
            raise ErrorIntegridadPregunta(
                f"Pregunta {pid} (verdadero_falso) debe tener EXACTAMENTE 1 "
                f"opción correcta, tiene {len(correctas)}."
            )
        return PreguntaVerdaderoFalso(
            id_pregunta=pid,
            enunciado=pregunta_row["enunciado"],
            respuesta_correcta=(next(iter(correctas)) == "v"),
            puntos=pregunta_row["puntos"],
        )

    elif tipo == "opcion_multiple":
        if len(correctas) < 1:
            raise ErrorIntegridadPregunta(
                f"Pregunta {pid} (opcion_multiple) debe tener AL MENOS 1 "
                f"opción correcta, tiene 0."
            )
        return PreguntaOpcionMultiple(
            id_pregunta=pid,
            enunciado=pregunta_row["enunciado"],
            opciones=opciones_dict,
            respuestas_correctas=correctas,
            puntos=pregunta_row["puntos"],
            # puntaje_parcial=True por defecto (estándar del proyecto, Ciclo 1)
        )

    else:
        raise ErrorIntegridadPregunta(f"Pregunta {pid} tiene un tipo desconocido: '{tipo}'")


def obtener_cuestionario_raw(cuestionario_id: int):
    """
    Trae el cuestionario + sus preguntas + sus opciones en 3 consultas
    simples (deliberadamente, en vez de un único JOIN gigante, para que
    el SQL siga siendo fácil de leer en un proyecto universitario).
    Retorna None si el cuestionario no existe.
    """
    conn = obtener_conexion()
    try:
        cuestionario = conn.execute(
            "SELECT * FROM cuestionarios WHERE id = ?", (cuestionario_id,)
        ).fetchone()

        if cuestionario is None:
            return None

        preguntas = conn.execute(
            "SELECT * FROM preguntas WHERE cuestionario_id = ? ORDER BY id",
            (cuestionario_id,)
        ).fetchall()

        preguntas_con_opciones = []
        for p in preguntas:
            opciones = conn.execute(
                "SELECT * FROM opciones WHERE pregunta_id = ? ORDER BY clave",
                (p["id"],)
            ).fetchall()
            preguntas_con_opciones.append((p, opciones))

        return cuestionario, preguntas_con_opciones
    finally:
        conn.close()


def construir_preguntas_dominio(cuestionario_id: int):
    """Devuelve la lista de objetos Pregunta (quiz_engine) listos para ser evaluados."""
    resultado = obtener_cuestionario_raw(cuestionario_id)
    if resultado is None:
        raise CuestionarioNoEncontrado(f"No existe el cuestionario {cuestionario_id}")

    _, preguntas_con_opciones = resultado
    return [_construir_pregunta_dominio(p, ops) for p, ops in preguntas_con_opciones]


def serializar_cuestionario_publico(cuestionario_id: int) -> dict:
    """
    Versión SEGURA para enviar al frontend.

    Mitiga el Riesgo R3 (fuga de respuestas correctas): este dict NO
    incluye el campo `es_correcta` de ninguna opción. El estudiante
    jamás debe poder ver la respuesta correcta inspeccionando la
    pestaña de Red del navegador.
    """
    resultado = obtener_cuestionario_raw(cuestionario_id)
    if resultado is None:
        raise CuestionarioNoEncontrado(f"No existe el cuestionario {cuestionario_id}")

    cuestionario, preguntas_con_opciones = resultado
    return {
        "id": cuestionario["id"],
        "titulo": cuestionario["titulo"],
        "descripcion": cuestionario["descripcion"],
        "preguntas": [
            {
                "id": p["id"],
                "tipo": p["tipo"],
                "enunciado": p["enunciado"],
                "puntos": p["puntos"],
                "opciones": [{"clave": o["clave"], "texto": o["texto"]} for o in ops],
            }
            for p, ops in preguntas_con_opciones
        ],
    }


# ======================================================================
# CICLO 4 — Usuarios (autenticación)
# ======================================================================

def crear_usuario(nombre: str, email: str, password_hash: str, rol: str) -> int:
    conn = obtener_conexion()
    try:
        cur = conn.execute(
            "INSERT INTO usuarios (nombre, email, password_hash, rol) VALUES (?, ?, ?, ?)",
            (nombre, email, password_hash, rol),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def obtener_usuario_por_email(email: str):
    conn = obtener_conexion()
    try:
        return conn.execute("SELECT * FROM usuarios WHERE email = ?", (email,)).fetchone()
    finally:
        conn.close()


# ======================================================================
# CICLO 4 — Gestión múltiple de cuestionarios (reemplaza el ID hardcodeado)
# ======================================================================

def listar_cuestionarios() -> list:
    """Lista liviana (sin preguntas) para que el frontend deje de depender de un ID fijo."""
    conn = obtener_conexion()
    try:
        filas = conn.execute(
            "SELECT id, titulo, descripcion FROM cuestionarios ORDER BY id"
        ).fetchall()
        return [dict(f) for f in filas]
    finally:
        conn.close()


def crear_cuestionario(titulo: str, descripcion: str, preguntas: list, creado_por_id: int) -> int:
    """
    `preguntas`: lista de dicts
        {tipo, enunciado, puntos, opciones: [{clave, texto, es_correcta}, ...]}

    Reutiliza la MISMA regla de integridad que `_construir_pregunta_dominio`
    aplica al leer (Riesgo R1, Ciclo 2): no se permite guardar una pregunta
    de opción única/V-F sin exactamente 1 respuesta correcta, ni una de
    opción múltiple sin ninguna.
    """
    conn = obtener_conexion()
    try:
        cur = conn.execute(
            "INSERT INTO cuestionarios (titulo, descripcion, creado_por_id) VALUES (?, ?, ?)",
            (titulo, descripcion, creado_por_id),
        )
        cuestionario_id = cur.lastrowid

        for p in preguntas:
            correctas = sum(1 for o in p["opciones"] if o.get("es_correcta"))
            if p["tipo"] in ("opcion_unica", "verdadero_falso") and correctas != 1:
                raise ErrorIntegridadPregunta(
                    f"'{p['enunciado']}' debe tener EXACTAMENTE 1 opción correcta."
                )
            if p["tipo"] == "opcion_multiple" and correctas < 1:
                raise ErrorIntegridadPregunta(
                    f"'{p['enunciado']}' debe tener AL MENOS 1 opción correcta."
                )

            cur2 = conn.execute(
                "INSERT INTO preguntas (cuestionario_id, tipo, enunciado, puntos) VALUES (?, ?, ?, ?)",
                (cuestionario_id, p["tipo"], p["enunciado"], p.get("puntos", 1.0)),
            )
            pregunta_id = cur2.lastrowid
            conn.executemany(
                "INSERT INTO opciones (pregunta_id, clave, texto, es_correcta) VALUES (?, ?, ?, ?)",
                [
                    (pregunta_id, o["clave"], o["texto"], int(bool(o.get("es_correcta"))))
                    for o in p["opciones"]
                ],
            )

        conn.commit()
        return cuestionario_id
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ======================================================================
# CICLO 4 — Historial de intentos
# ======================================================================

def guardar_intento(usuario_id: int, cuestionario_id: int, resultado: dict):
    """`resultado` es el dict que retorna MotorCuestionario.evaluar_cuestionario()."""
    detalle_serializable = {
        str(id_p): {
            "es_correcta": r.es_correcta,
            "puntaje": r.puntaje,
            "retroalimentacion": r.retroalimentacion,
        }
        for id_p, r in resultado["detalle"].items()
    }
    conn = obtener_conexion()
    try:
        conn.execute(
            """INSERT INTO intentos
               (usuario_id, cuestionario_id, puntaje_total, puntaje_maximo, porcentaje, detalle_json)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                usuario_id,
                cuestionario_id,
                resultado["puntaje_total"],
                resultado["puntaje_maximo"],
                resultado["porcentaje"],
                json.dumps(detalle_serializable, ensure_ascii=False),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def listar_intentos(usuario_id: int = None) -> list:
    """Si usuario_id es None, devuelve TODOS los intentos (vista de profesor)."""
    conn = obtener_conexion()
    try:
        base_query = """
            SELECT i.id, i.usuario_id, u.nombre AS usuario_nombre,
                   i.cuestionario_id, c.titulo AS cuestionario_titulo,
                   i.puntaje_total, i.puntaje_maximo, i.porcentaje, i.fecha
            FROM intentos i
            JOIN usuarios u ON u.id = i.usuario_id
            JOIN cuestionarios c ON c.id = i.cuestionario_id
        """
        if usuario_id is not None:
            filas = conn.execute(
                base_query + " WHERE i.usuario_id = ? ORDER BY i.fecha DESC", (usuario_id,)
            ).fetchall()
        else:
            filas = conn.execute(base_query + " ORDER BY i.fecha DESC").fetchall()
        return [dict(f) for f in filas]
    finally:
        conn.close()
