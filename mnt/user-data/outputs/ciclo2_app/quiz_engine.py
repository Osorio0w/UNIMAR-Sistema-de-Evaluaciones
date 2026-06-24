"""
quiz_engine.py
----------------
CICLO 1 - Motor de Cuestionarios (Núcleo Lógico)
Metodología: Espiral | Cuadrante 3 - Desarrollo y Verificación

Este módulo implementa la lógica de evaluación para los 3 tipos de
pregunta requeridos por la plataforma:

    1. Opción Única       (radio buttons)
    2. Verdadero / Falso   (caso particular de opción única)
    3. Opción Múltiple    (checkboxes)

Diseño: se usa una clase base abstracta (Pregunta) para que TODO el
motor pueda evaluar cualquier pregunta a través de un único contrato
(método evaluar()), sin importar su tipo concreto. Esto es polimorfismo
aplicado y facilita que en ciclos futuros agreguemos nuevos tipos
(ej. emparejamiento, respuesta corta) sin tocar el orquestador.

IMPORTANTE: este módulo NO depende de Flask, FastAPI ni de ninguna base
de datos. Es lógica pura de Python, probada de forma aislada, tal como
exige el primer giro de la espiral.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Set
from enum import Enum


class TipoPregunta(Enum):
    """Catálogo de tipos soportados en este ciclo."""
    UNICA = "opcion_unica"
    VERDADERO_FALSO = "verdadero_falso"
    MULTIPLE = "opcion_multiple"


@dataclass
class ResultadoEvaluacion:
    """
    Objeto de respuesta estandarizado. Usar un dataclass (en vez de un
    simple booleano) nos da margen para crecer: ya incluye 'puntaje'
    pensando en preguntas con peso distinto y retroalimentación para
    mostrar al usuario en el frontend.
    """
    es_correcta: bool
    puntaje: float          # 0.0 a 'puntos' de la pregunta
    retroalimentacion: str  # mensaje explicativo para el usuario


class Pregunta(ABC):
    """
    Clase base abstracta. Define el contrato que TODA pregunta debe
    cumplir. El MotorCuestionario solo conoce esta interfaz, nunca
    los detalles internos de cada subtipo (principio de sustitución
    de Liskov).
    """

    def __init__(self, id_pregunta: int, enunciado: str, puntos: float = 1.0):
        self.id_pregunta = id_pregunta
        self.enunciado = enunciado
        self.puntos = puntos

    @abstractmethod
    def evaluar(self, respuesta_usuario) -> ResultadoEvaluacion:
        """Evalúa la respuesta del usuario y retorna un ResultadoEvaluacion."""
        ...

    @abstractmethod
    def validar_formato_respuesta(self, respuesta_usuario) -> bool:
        """
        Valida que el TIPO de dato recibido sea el esperado, ANTES de
        intentar evaluar. Esto evita que datos corruptos o maliciosos
        (ej. un string donde se espera una lista) rompan la evaluación.
        """
        ...


class PreguntaOpcionUnica(Pregunta):
    """
    TIPO 1: Opción Única.
    La respuesta del usuario es UN único identificador de opción
    (ej: 'b'), simulando un grupo de radio buttons en el frontend.
    """

    def __init__(self, id_pregunta, enunciado, opciones: dict,
                 respuesta_correcta: str, puntos: float = 1.0):
        super().__init__(id_pregunta, enunciado, puntos)
        self.opciones = opciones  # ej: {'a': 'Madrid', 'b': 'París'}
        self.respuesta_correcta = respuesta_correcta

    def validar_formato_respuesta(self, respuesta_usuario) -> bool:
        return isinstance(respuesta_usuario, str) and respuesta_usuario in self.opciones

    def evaluar(self, respuesta_usuario) -> ResultadoEvaluacion:
        if not self.validar_formato_respuesta(respuesta_usuario):
            return ResultadoEvaluacion(
                False, 0.0,
                "Formato de respuesta inválido o la opción no existe."
            )
        es_correcta = respuesta_usuario == self.respuesta_correcta
        return ResultadoEvaluacion(
            es_correcta,
            self.puntos if es_correcta else 0.0,
            "¡Correcto!" if es_correcta else
            f"Incorrecto. La respuesta correcta era: "
            f"'{self.opciones[self.respuesta_correcta]}'"
        )


class PreguntaVerdaderoFalso(PreguntaOpcionUnica):
    """
    TIPO 2: Verdadero / Falso.
    Se modela como una ESPECIALIZACIÓN de Opción Única: matemáticamente
    es el mismo problema con exactamente 2 opciones fijas. Heredar en
    vez de reescribir evita duplicar lógica (riesgo de inconsistencias
    si luego cambiamos las reglas de opción única).
    """

    def __init__(self, id_pregunta, enunciado, respuesta_correcta: bool,
                 puntos: float = 1.0):
        opciones = {"v": "Verdadero", "f": "Falso"}
        correcta_str = "v" if respuesta_correcta else "f"
        super().__init__(id_pregunta, enunciado, opciones, correcta_str, puntos)


class PreguntaOpcionMultiple(Pregunta):
    """
    TIPO 3: Opción Múltiple (checkboxes).
    La respuesta del usuario es un CONJUNTO de identificadores.

    DECISIÓN DE PRODUCTO (Ciclo 1, Cuadrante 4 - confirmada con el usuario):
    El ESTÁNDAR del proyecto es "puntaje_parcial=True": se premian los
    aciertos y se penalizan los falsos positivos, en vez de calificar
    en bloque "todo o nada". Se deja el parámetro configurable por si
    una pregunta puntual necesita el modo estricto, pero el valor por
    defecto ahora refleja la decisión tomada para toda la plataforma.
    """

    def __init__(self, id_pregunta, enunciado, opciones: dict,
                 respuestas_correctas: Set[str], puntos: float = 1.0,
                 puntaje_parcial: bool = True):
        super().__init__(id_pregunta, enunciado, puntos)
        self.opciones = opciones
        self.respuestas_correctas = set(respuestas_correctas)
        self.puntaje_parcial = puntaje_parcial

    def validar_formato_respuesta(self, respuesta_usuario) -> bool:
        if not isinstance(respuesta_usuario, (list, set)):
            return False
        respuesta_set = set(respuesta_usuario)
        # Todas las opciones marcadas deben existir en el catálogo
        return respuesta_set.issubset(self.opciones.keys())

    def evaluar(self, respuesta_usuario) -> ResultadoEvaluacion:
        if not self.validar_formato_respuesta(respuesta_usuario):
            return ResultadoEvaluacion(
                False, 0.0,
                "Formato inválido: se esperaba una lista de opciones existentes."
            )

        respuesta_set = set(respuesta_usuario)

        # Caso borde: el usuario no marcó absolutamente nada
        if len(respuesta_set) == 0:
            return ResultadoEvaluacion(False, 0.0, "No se seleccionó ninguna opción.")

        if not self.puntaje_parcial:
            # --- Modo estricto: el set debe ser IDÉNTICO ---
            es_correcta = respuesta_set == self.respuestas_correctas
            return ResultadoEvaluacion(
                es_correcta,
                self.puntos if es_correcta else 0.0,
                "¡Correcto!" if es_correcta else
                "Incorrecto. Debes marcar TODAS las opciones correctas "
                "y NINGUNA incorrecta."
            )
        else:
            # --- Modo puntaje parcial: aciertos premian, errores penalizan ---
            aciertos = respuesta_set & self.respuestas_correctas
            errores = respuesta_set - self.respuestas_correctas
            total_correctas = len(self.respuestas_correctas)

            puntaje_bruto = (len(aciertos) - len(errores)) / total_correctas
            puntaje_final = max(0.0, puntaje_bruto) * self.puntos
            es_correcta = respuesta_set == self.respuestas_correctas

            return ResultadoEvaluacion(
                es_correcta,
                round(puntaje_final, 2),
                f"Aciertos: {len(aciertos)}/{total_correctas}. "
                f"Marcadas incorrectamente: {len(errores)}."
            )


class MotorCuestionario:
    """
    Orquestador del Ciclo 1. Recibe una lista de objetos Pregunta
    (de cualquier subtipo) y un diccionario de respuestas que simula
    el payload JSON que en un futuro ciclo llegará vía API REST.
    """

    def __init__(self, preguntas: List[Pregunta]):
        self.preguntas = {p.id_pregunta: p for p in preguntas}

    def evaluar_cuestionario(self, respuestas_usuario: dict) -> dict:
        resultados = {}
        puntaje_total = 0.0
        puntaje_maximo = 0.0

        for id_p, pregunta in self.preguntas.items():
            puntaje_maximo += pregunta.puntos
            respuesta = respuestas_usuario.get(id_p, None)

            if respuesta is None:
                resultados[id_p] = ResultadoEvaluacion(
                    False, 0.0, "Pregunta no respondida."
                )
                continue

            # Polimorfismo en acción: no nos importa si es Única, V/F o
            # Múltiple, el motor solo llama a .evaluar()
            resultado = pregunta.evaluar(respuesta)
            resultados[id_p] = resultado
            puntaje_total += resultado.puntaje

        return {
            "detalle": resultados,
            "puntaje_total": round(puntaje_total, 2),
            "puntaje_maximo": puntaje_maximo,
            "porcentaje": round((puntaje_total / puntaje_maximo) * 100, 1)
            if puntaje_maximo else 0
        }


# ======================================================================
# DEMOSTRACIÓN / PRUEBA DEL MOTOR  (Cuadrante 3 - Verificación)
# Simula un cuestionario y dos "peticiones" como las que enviaría
# el frontend en formato JSON.
# ======================================================================
if __name__ == "__main__":

    # --- 1. Definición de un cuestionario de prueba ---
    p1 = PreguntaOpcionUnica(
        id_pregunta=1,
        enunciado="¿Cuál es la capital de Francia?",
        opciones={"a": "Madrid", "b": "París", "c": "Roma"},
        respuesta_correcta="b",
        puntos=2.0
    )

    p2 = PreguntaVerdaderoFalso(
        id_pregunta=2,
        enunciado="Python es un lenguaje compilado.",
        respuesta_correcta=False,
        puntos=1.0
    )

    p3 = PreguntaOpcionMultiple(
        id_pregunta=3,
        enunciado="¿Cuáles de las siguientes son lenguajes de programación?",
        opciones={"a": "Python", "b": "HTML", "c": "JavaScript", "d": "CSS"},
        respuestas_correctas={"a", "c"},
        puntos=3.0
        # puntaje_parcial=True por defecto (estándar del proyecto)
    )

    motor = MotorCuestionario([p1, p2, p3])

    # --- 2. Simulación de payloads recibidos desde el frontend ---
    respuestas_caso_a = {  # Usuario responde TODO correctamente
        1: "b",
        2: "f",         # Falso es correcto
        3: ["a", "c"]   # marca exactamente las correctas
    }

    respuestas_caso_b = {  # Usuario comete errores típicos a probar
        1: "a",              # incorrecta
        2: "v",               # incorrecta
        3: ["a", "b", "c"]    # marcó una opción de más -> ahora recibe puntaje parcial
    }

    for nombre, respuestas in [
        ("CASO A (todo correcto)", respuestas_caso_a),
        ("CASO B (con errores típicos)", respuestas_caso_b),
    ]:
        print(f"\n{'=' * 55}\n{nombre}\n{'=' * 55}")
        resultado = motor.evaluar_cuestionario(respuestas)
        for id_p, r in resultado["detalle"].items():
            marca = "✅" if r.es_correcta else "❌"
            print(f"Pregunta {id_p}: {marca} (puntaje: {r.puntaje}) -> {r.retroalimentacion}")
        print(
            f"\nPUNTAJE TOTAL: {resultado['puntaje_total']}/{resultado['puntaje_maximo']} "
            f"({resultado['porcentaje']}%)"
        )
