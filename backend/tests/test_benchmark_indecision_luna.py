import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from benchmark_indecision_luna import FRASE, POSTURA_EXPLICITA, leer_postura_explicita, sistemas


def salida_luna(filas):
    mensaje = {"type": "agent_message", "text": json.dumps({"r": filas})}
    return json.dumps({"type": "item.completed", "item": mensaje})


class BenchmarkIndecisionLuna(unittest.TestCase):
    def test_separa_postura_de_intensidad_y_conserva_el_orden(self):
        filas = [
            {"i": 1, "tiene_postura": False, "apoyo": None, "p": [2, 3, 4, 5]},
            {"i": 0, "tiene_postura": True, "apoyo": 3, "p": [5, 3, 3, 4]},
        ]
        respuestas, _ = leer_postura_explicita(salida_luna(filas), 2)
        self.assertEqual(respuestas, [[3, 5, 3, 3, 4], [4, 2, 3, 4, 5]])

    def test_rechaza_indicadores_contradictorios(self):
        for tiene, apoyo in ((True, 4), (True, None), (False, 3), (0, None)):
            with self.subTest(tiene=tiene, apoyo=apoyo):
                fila = {"i": 0, "tiene_postura": tiene, "apoyo": apoyo, "p": [2, 3, 4, 5]}
                with self.assertRaises(ValueError):
                    leer_postura_explicita(salida_luna([fila]), 1)

    def test_rechaza_filas_repetidas_o_incompletas(self):
        fila = {"i": 0, "tiene_postura": True, "apoyo": 6, "p": [2, 3, 4, 5]}
        with self.assertRaises(ValueError):
            leer_postura_explicita(salida_luna([fila, fila]), 2)
        with self.assertRaises(ValueError):
            leer_postura_explicita(salida_luna([{**fila, "p": [2, 3, 4]}]), 1)

    def test_prompt_explica_postura_y_preserva_tema_y_preguntas(self):
        tema = "Una política de prueba."
        texto = sistemas(tema, postura_explicita=True)[POSTURA_EXPLICITA]
        self.assertIn(tema, texto)
        self.assertIn("tiene_postura: false", texto)
        self.assertIn("Si es false, devuelve apoyo: null", texto)
        self.assertNotIn(FRASE, texto)
        self.assertIn("¿Estarías de acuerdo con que se implemente esta política en tu región?", texto)
