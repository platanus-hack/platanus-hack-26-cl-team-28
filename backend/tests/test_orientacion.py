import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from servidor.orientacion import orientar, _cache
from servidor.corridas import Cache, Caso, Corrida
from servidor.motor import Consumo, Motor, Respuesta, ResultadoLote


class Orientacion(unittest.TestCase):
    def setUp(self):
        _cache.clear()
        self.motor = Mock()
        self.motor.clave.return_value = "prueba"

    def responder(self, resultados):
        self.motor.redactar.return_value = ({"orientaciones": resultados}, None)

    def test_preserva_cifras_y_negaciones_de_las_dos_alternativas(self):
        self.responder([{"tipo": "comparacion", "motivo": "Dos políticas", "propuestas": [
            "No subir el IVA del 19%", "Bajar el IVA a 18%"]}])
        resultado = orientar(self.motor, ["¿No subir el IVA del 19% o bajarlo a 18%?"])
        self.assertEqual(resultado[0]["propuestas"], ["No subir el IVA del 19%", "Bajar el IVA a 18%"])

    def test_no_acepta_una_comparacion_incompleta_ni_alternativas_duplicadas(self):
        for propuestas in [["A"], [" A ", "a"], ["A", ""], ["A", 3]]:
            with self.subTest(propuestas=propuestas):
                self.responder([{"tipo": "comparacion", "motivo": "", "propuestas": propuestas}])
                with self.assertRaises(ValueError):
                    orientar(self.motor, ["texto"])

    def test_no_trunca_silenciosamente_una_respuesta_incompleta(self):
        self.responder([{"tipo": "adecuada", "motivo": "", "propuestas": []}])
        with self.assertRaises(ValueError):
            orientar(self.motor, ["primera", "segunda"])

    def test_reutiliza_la_revision_solo_para_los_mismos_textos_y_motor(self):
        self.responder([{"tipo": "fuera", "motivo": "Preferencia deportiva", "propuestas": []}])
        orientar(self.motor, ["Colo Colo o la U"])
        orientar(self.motor, ["Colo Colo o la U"])
        self.assertEqual(self.motor.redactar.call_count, 1)
        self.motor.clave.return_value = "otro-modelo"
        orientar(self.motor, ["Colo Colo o la U"])
        self.assertEqual(self.motor.redactar.call_count, 2)


class ConsultaAB(unittest.TestCase):
    def test_consulta_las_mismas_personas_primero_a_luego_b_sin_mezclar_textos(self):
        llamadas = []
        prueba = self
        corrida = None

        class MotorPrueba(Motor):
            modelo = "prueba-ab"

            def responder(self, politica, agentes):
                if politica == "Bajar el IVA a 18%":
                    prueba.assertEqual(len(corrida.casos[0].respuestas), 3)
                    prueba.assertTrue(any(t == "caso_listo" and d["caso"] == 0 for t, d in corrida.eventos))
                llamadas.append((politica, [a.id for a in agentes]))
                return ResultadoLote([Respuesta(a.indice, [6 if politica.startswith("Subir") else 2, 4, 4, 4, 4]) for a in agentes], Consumo())

        agentes = [SimpleNamespace(id=f"p{k}", indice=k) for k in range(3)]
        with tempfile.TemporaryDirectory() as carpeta:
            corrida = Corrida(MotorPrueba(), Cache(Path(carpeta)), agentes,
                              [Caso("a", "A", "Subir el IVA a 20%"), Caso("b", "B", "Bajar el IVA a 18%")],
                              0, 20, 4, "ABCD", secuencial=True)
            corrida.correr()
            self.assertTrue(corrida.terminada)
            self.assertEqual(llamadas, [("Subir el IVA a 20%", ["p0", "p1", "p2"]),
                                       ("Bajar el IVA a 18%", ["p0", "p1", "p2"])])
            self.assertEqual([c.apoyo() for c in corrida.casos], [1, 0])
            self.assertFalse(any(t == "falla" for t, _ in corrida.eventos))


if __name__ == "__main__":
    unittest.main()
