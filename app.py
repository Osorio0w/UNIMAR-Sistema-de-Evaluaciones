"""
app.py — Ciclos 2/3/4
Endpoints:
  POST /auth/registro          -> Crea usuario (estudiante o profesor)
  POST /auth/login             -> Inicia sesión, guarda cookie de sesión
  POST /auth/logout            -> Cierra sesión
  GET  /auth/me                -> Devuelve datos de la sesión activa

  GET  /cuestionarios          -> Lista todos los cuestionarios (requiere login)
  POST /cuestionarios          -> Crea un cuestionario (solo profesor)
  GET  /cuestionario/<id>      -> Preguntas del cuestionario, sin respuestas (requiere login)
  POST /evaluar/<id>           -> Evalúa y guarda intento si hay sesión activa

  GET  /historial              -> Mis intentos (estudiante) o todos (profesor)
"""

import sqlite3
from flask import Flask, jsonify, request, render_template, session
from repository import (
    construir_preguntas_dominio,
    serializar_cuestionario_publico,
    CuestionarioNoEncontrado,
    ErrorIntegridadPregunta,
    crear_usuario,
    obtener_usuario_por_email,
    listar_cuestionarios,
    crear_cuestionario,
    guardar_intento,
    listar_intentos,
)
from quiz_engine import MotorCuestionario
from auth import (
    hash_password,
    verificar_password,
    iniciar_sesion,
    cerrar_sesion,
    login_required,
    requiere_rol,
    ROLES_VALIDOS,
)

app = Flask(__name__)
app.secret_key = "dev-secret-cambiar-por-variable-de-entorno-en-produccion"


@app.route("/auth/registro", methods=["POST"])
def registro():
    body = request.get_json(silent=True) or {}
    nombre, email, password, rol = (
        body.get("nombre"), body.get("email"), body.get("password"), body.get("rol"),
    )
    if not all([nombre, email, password, rol]):
        return jsonify({"error": "Faltan campos: nombre, email, password, rol"}), 400
    if rol not in ROLES_VALIDOS:
        return jsonify({"error": "rol debe ser 'estudiante' o 'profesor'"}), 400

    try:
        usuario_id = crear_usuario(nombre, email, hash_password(password), rol)
    except sqlite3.IntegrityError:
        return jsonify({"error": "Ese email ya está registrado"}), 409

    iniciar_sesion(usuario_id, rol)
    return jsonify({"id": usuario_id, "nombre": nombre, "rol": rol}), 201


@app.route("/auth/login", methods=["POST"])
def login():
    body = request.get_json(silent=True) or {}
    email, password = body.get("email"), body.get("password")
    usuario = obtener_usuario_por_email(email) if email else None

    if usuario is None or not verificar_password(usuario["password_hash"], password or ""):
        return jsonify({"error": "Credenciales inválidas"}), 401

    iniciar_sesion(usuario["id"], usuario["rol"])
    return jsonify({"id": usuario["id"], "nombre": usuario["nombre"], "rol": usuario["rol"]})


@app.route("/auth/logout", methods=["POST"])
def logout():
    cerrar_sesion()
    return jsonify({"ok": True})


@app.route("/auth/me", methods=["GET"])
def me():
    if "usuario_id" not in session:
        return jsonify({"autenticado": False})
    return jsonify({"autenticado": True, "id": session["usuario_id"], "rol": session["rol"]})


@app.route("/", methods=["GET"])
def index():
    """
    CICLO 3: sirve la interfaz HTML que consume los endpoints de abajo.
    No contiene lógica de negocio, solo entrega la plantilla; toda la
    interactividad vive en static/js/app.js.
    """
    return render_template("index.html")


@app.route("/cuestionarios", methods=["GET"])
@login_required
def get_cuestionarios():
    """Lista liviana de todos los cuestionarios disponibles."""
    return jsonify(listar_cuestionarios())


@app.route("/cuestionarios", methods=["POST"])
@requiere_rol("profesor")
def post_cuestionario():
    """
    Crea un cuestionario completo (con preguntas y opciones) en una sola llamada.
    Payload esperado:
    {
      "titulo": "...",
      "descripcion": "...",
      "preguntas": [
        {
          "tipo": "opcion_unica",
          "enunciado": "...",
          "puntos": 2.0,
          "opciones": [
            {"clave": "a", "texto": "...", "es_correcta": false},
            {"clave": "b", "texto": "...", "es_correcta": true}
          ]
        }
      ]
    }
    """
    body = request.get_json(silent=True) or {}
    titulo = body.get("titulo")
    preguntas = body.get("preguntas")
    if not titulo or not isinstance(preguntas, list) or len(preguntas) == 0:
        return jsonify({"error": "Se requieren 'titulo' y al menos una pregunta en 'preguntas'"}), 400

    try:
        nuevo_id = crear_cuestionario(
            titulo=titulo,
            descripcion=body.get("descripcion", ""),
            preguntas=preguntas,
            creado_por_id=session["usuario_id"],
        )
    except ErrorIntegridadPregunta as e:
        return jsonify({"error": str(e)}), 422

    return jsonify({"id": nuevo_id, "titulo": titulo}), 201


@app.route("/cuestionario/<int:cuestionario_id>", methods=["GET"])
@login_required
def obtener_cuestionario(cuestionario_id):
    """Devuelve el cuestionario para que el frontend lo renderice (sin respuestas)."""
    try:
        data = serializar_cuestionario_publico(cuestionario_id)
        return jsonify(data)
    except CuestionarioNoEncontrado:
        return jsonify({"error": "Cuestionario no encontrado"}), 404


@app.route("/evaluar/<int:cuestionario_id>", methods=["POST"])
@login_required
def evaluar_cuestionario(cuestionario_id):
    """Evalúa las respuestas y guarda el intento en el historial del usuario."""
    body = request.get_json(silent=True)
    if body is None or "respuestas" not in body:
        return jsonify({"error": "Se esperaba un JSON con la clave 'respuestas'"}), 400

    try:
        respuestas_usuario = {int(k): v for k, v in body["respuestas"].items()}
    except (ValueError, AttributeError, TypeError):
        return jsonify({"error": "Formato de 'respuestas' inválido"}), 400

    try:
        preguntas_dominio = construir_preguntas_dominio(cuestionario_id)
    except CuestionarioNoEncontrado:
        return jsonify({"error": "Cuestionario no encontrado"}), 404
    except ErrorIntegridadPregunta as e:
        return jsonify({"error": f"Error de integridad de datos: {e}"}), 500

    motor = MotorCuestionario(preguntas_dominio)
    resultado = motor.evaluar_cuestionario(respuestas_usuario)

    # Guardar intento — funciona para ambos roles; el profesor también puede
    # responder cuestionarios para verificarlos.
    guardar_intento(session["usuario_id"], cuestionario_id, resultado)

    return jsonify({
        "cuestionario_id": cuestionario_id,
        "puntaje_total": resultado["puntaje_total"],
        "puntaje_maximo": resultado["puntaje_maximo"],
        "porcentaje": resultado["porcentaje"],
        "detalle": {
            str(id_p): {
                "es_correcta": r.es_correcta,
                "puntaje": r.puntaje,
                "retroalimentacion": r.retroalimentacion,
            }
            for id_p, r in resultado["detalle"].items()
        },
    })


@app.route("/historial", methods=["GET"])
@login_required
def historial():
    """
    Estudiante: devuelve solo sus propios intentos.
    Profesor: devuelve todos los intentos de todos los usuarios.
    """
    uid = None if session["rol"] == "profesor" else session["usuario_id"]
    return jsonify(listar_intentos(uid))


if __name__ == "__main__":
    app.run(debug=True)
