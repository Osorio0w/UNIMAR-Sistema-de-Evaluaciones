"""
auth.py
----------------
CICLO 4 - Autenticación básica y control de roles
Sesiones de Flask (cookie firmada) + contraseñas hasheadas (Werkzeug).
Roles: 'estudiante' y 'profesor'.
"""

from functools import wraps
from flask import session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

ROLES_VALIDOS = {"estudiante", "profesor"}

hash_password = generate_password_hash
verificar_password = check_password_hash  # uso: verificar_password(hash_guardado, password_plano)


def iniciar_sesion(usuario_id: int, rol: str):
    session["usuario_id"] = usuario_id
    session["rol"] = rol


def cerrar_sesion():
    session.clear()


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "usuario_id" not in session:
            return jsonify({"error": "Debes iniciar sesión"}), 401
        return f(*args, **kwargs)
    return wrapper


def requiere_rol(rol_requerido: str):
    def decorador(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if "usuario_id" not in session:
                return jsonify({"error": "Debes iniciar sesión"}), 401
            if session.get("rol") != rol_requerido:
                return jsonify({"error": f"Acción exclusiva para rol '{rol_requerido}'"}), 403
            return f(*args, **kwargs)
        return wrapper
    return decorador
