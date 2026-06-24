"""
seed.py — Idempotente (Ciclo 4)
Regla: si ya existen los usuarios demo, no borra ni duplica nada.
Corre python3 seed.py tantas veces como quieras; los datos manuales persisten.
"""
from database import obtener_conexion, inicializar_esquema
from werkzeug.security import generate_password_hash

USUARIOS_DEMO = [
    ("Profesor Demo", "profesor@demo.com", "prof123", "profesor"),
    ("Estudiante Demo", "estudiante@demo.com", "est123", "estudiante"),
]

QUIZ_DEMO = {
    "titulo": "Quiz de Prueba — Demo",
    "descripcion": "Cuestionario inicial para verificar la plataforma.",
    "preguntas": [
        {
            "tipo": "opcion_unica",
            "enunciado": "¿Cuál es la capital de Francia?",
            "puntos": 2.0,
            "opciones": [("a","Madrid",0), ("b","París",1), ("c","Roma",0)],
        },
        {
            "tipo": "verdadero_falso",
            "enunciado": "Python es un lenguaje compilado.",
            "puntos": 1.0,
            "opciones": [("v","Verdadero",0), ("f","Falso",1)],
        },
        {
            "tipo": "opcion_multiple",
            "enunciado": "¿Cuáles son lenguajes de programación?",
            "puntos": 3.0,
            "opciones": [("a","Python",1), ("b","HTML",0), ("c","JavaScript",1), ("d","CSS",0)],
        },
    ],
}


def sembrar():
    inicializar_esquema()
    conn = obtener_conexion()
    cur = conn.cursor()

    # ── Usuarios demo ──────────────────────────────────────────────────
    creados = 0
    ids = {}
    for nombre, email, pwd, rol in USUARIOS_DEMO:
        existe = cur.execute(
            "SELECT id FROM usuarios WHERE email = ?", (email,)
        ).fetchone()
        if existe:
            ids[rol] = existe["id"]
            print(f"  ↩  Usuario '{email}' ya existe, omitido.")
        else:
            cur.execute(
                "INSERT INTO usuarios (nombre, email, password_hash, rol) VALUES (?,?,?,?)",
                (nombre, email, generate_password_hash(pwd), rol),
            )
            ids[rol] = cur.lastrowid
            print(f"  ✅ Usuario '{email}' creado.")
            creados += 1

    # ── Quiz demo (solo si no existe ya un quiz con ese título exacto) ─
    profesor_id = ids.get("profesor")
    existe_quiz = cur.execute(
        "SELECT id FROM cuestionarios WHERE titulo = ?", (QUIZ_DEMO["titulo"],)
    ).fetchone()

    if existe_quiz:
        print(f"  ↩  Quiz demo ya existe (id={existe_quiz['id']}), omitido.")
    else:
        cur.execute(
            "INSERT INTO cuestionarios (titulo, descripcion, creado_por_id) VALUES (?,?,?)",
            (QUIZ_DEMO["titulo"], QUIZ_DEMO["descripcion"], profesor_id),
        )
        quiz_id = cur.lastrowid
        for p in QUIZ_DEMO["preguntas"]:
            cur.execute(
                "INSERT INTO preguntas (cuestionario_id, tipo, enunciado, puntos) VALUES (?,?,?,?)",
                (quiz_id, p["tipo"], p["enunciado"], p["puntos"]),
            )
            pid = cur.lastrowid
            cur.executemany(
                "INSERT INTO opciones (pregunta_id, clave, texto, es_correcta) VALUES (?,?,?,?)",
                [(pid, c, t, e) for c, t, e in p["opciones"]],
            )
        print(f"  ✅ Quiz demo creado (id={quiz_id}).")

    conn.commit()
    conn.close()

    total_users = obtener_conexion().execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]
    total_quiz  = obtener_conexion().execute("SELECT COUNT(*) FROM cuestionarios").fetchone()[0]
    total_int   = obtener_conexion().execute("SELECT COUNT(*) FROM intentos").fetchone()[0]

    print(f"\n  BD actual → {total_users} usuario(s) · {total_quiz} cuestionario(s) · {total_int} intento(s)")
    print("  Credenciales demo: profesor@demo.com/prof123 · estudiante@demo.com/est123")


if __name__ == "__main__":
    sembrar()
