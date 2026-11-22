"""El ancla: el pronóstico nacional y su reparto entre los agentes (servidor/ancla.py y corridas.py)."""

import random
import sys
import tempfile
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from servidor import ancla  # noqa: E402
from servidor.corridas import Cache, Caso, Corrida  # noqa: E402
from servidor.motor import Consumo, Motor, Respuesta, ResultadoLote  # noqa: E402


class Persona:
    def __init__(self, k):
        self.indice, self.id = k, f"p{k}"
        self.atributos, self.comuna = {}, "x"


class MotorFalso(Motor):
    """Responde notas fijas por persona y pronostica lo que se le diga."""

    modelo = "falso"

    def __init__(self, pronostico=(70.0, 20.0), falla=False):
        self.modelo_ancla = "grande"
        self._pronostico, self._falla = pronostico, falla
        self.pronosticos = 0

    def responder(self, politica, agentes):
        azar = random.Random(len(politica))
        return ResultadoLote([Respuesta(a.indice, [random.Random(a.indice).choice([1, 2, 3, 5, 6, 7]), 4, 3, 4, 2]) for a in agentes], Consumo(llamadas=1))

    def pronosticar(self, politica):
        self.pronosticos += 1
        if self._falla:
            raise RuntimeError("sin modelo")
        return self._pronostico, Consumo(llamadas=1)


class Limpiar(unittest.TestCase):
    def test_valores(self):
        self.assertEqual(ancla.limpiar({"acuerdo": 60, "desacuerdo": 30}), (60.0, 30.0))
        a, d = ancla.limpiar({"acuerdo": 80, "desacuerdo": 40})
        self.assertAlmostEqual(a + d, 100)
        self.assertIsNone(ancla.limpiar({"acuerdo": 130, "desacuerdo": 5}))
        self.assertIsNone(ancla.limpiar({"acuerdo": 0, "desacuerdo": 0}))
        self.assertIsNone(ancla.limpiar({}))

    def test_apagado(self):
        import os
        previo = os.environ.get("ANCLA")
        try:
            for valor in ("", "no", "0"):
                os.environ["ANCLA"] = valor
                self.assertEqual(ancla.modelo(), "")
            os.environ["ANCLA"] = "Haiku"
            self.assertEqual(ancla.modelo(), "haiku")
        finally:
            os.environ.pop("ANCLA", None) if previo is None else os.environ.__setitem__("ANCLA", previo)


class Repartir(unittest.TestCase):
    def notas(self, n, semilla=3):
        azar = random.Random(semilla)
        return [(f"p{k}", [azar.choice([1, 2, 3, 3, 5, 5, 6, 7]), azar.randint(1, 7), 3, azar.randint(1, 7), 2]) for k in range(n)]

    def test_total_sigue_al_pronostico_por_lotes(self):
        gente = self.notas(1000)
        for acuerdo, desacuerdo in ((90, 7), (55, 40), (20, 70), (50, 50)):
            reparto = ancla.Reparto(acuerdo, desacuerdo)
            finales = []
            for k in range(0, 1000, 20):
                finales += reparto.repartir(gente[k:k + 20])
            favor = 100 * sum(v >= 5 for v in finales) / 1000
            contra = 100 * sum(v <= 3 for v in finales) / 1000
            self.assertLess(abs(favor - acuerdo), 4)
            self.assertLess(abs(contra - desacuerdo), 4)

    def test_conserva_el_orden(self):
        """Nadie que puntúa más bajo queda a favor mientras alguien que puntúa más alto queda en contra."""
        gente = self.notas(400)
        reparto = ancla.Reparto(60, 30)
        finales = reparto.repartir(gente)
        puntajes = [ancla.puntaje(i, n) for i, n in gente]
        favor = [p for p, v in zip(puntajes, finales) if v >= 5]
        contra = [p for p, v in zip(puntajes, finales) if v <= 3]
        medio = [p for p, v in zip(puntajes, finales) if v == 4]
        self.assertGreater(min(favor), max(contra))
        self.assertTrue(all(max(contra) < p < min(favor) for p in medio))

    def test_no_cambia_la_nota_si_ya_esta_del_lado(self):
        reparto = ancla.Reparto(50, 50)
        finales = reparto.repartir([("a", [7, 4, 4, 4, 4]), ("b", [1, 4, 4, 4, 4])])
        self.assertEqual(finales, [7, 1])

    def test_mueve_lo_minimo(self):
        reparto = ancla.Reparto(100, 0)
        self.assertEqual(reparto.repartir([("a", [2, 4, 4, 4, 4]), ("b", [6, 4, 4, 4, 4])]), [5, 6])
        reparto = ancla.Reparto(0, 100)
        self.assertEqual(reparto.repartir([("a", [2, 4, 4, 4, 4]), ("b", [6, 4, 4, 4, 4])]), [2, 3])


class EnLaCorrida(unittest.TestCase):
    def correr(self, motor, n=200, cache=None):
        carpeta = tempfile.mkdtemp()
        cache = cache or Cache(Path(carpeta))
        agentes = [Persona(k) for k in range(n)]
        corrida = Corrida(motor, cache, agentes, [Caso("a", "A", "Una propuesta de prueba")], 0, 20, 4, "ABCDEFGH")
        hilo = threading.Thread(target=corrida.correr)
        hilo.start()
        hilo.join(60)
        self.assertTrue(corrida.terminada)
        return corrida, cache

    def test_reparte_y_guarda_las_notas_originales(self):
        corrida, cache = self.correr(MotorFalso((70.0, 20.0)))
        caso = corrida.casos[0]
        self.assertEqual(len(caso.respuestas), 200)
        self.assertLess(abs(caso.apoyo() * 100 - 70), 5)
        listo = next(d for t, d in corrida.eventos if t == "caso_listo")
        self.assertEqual(listo["ancla"], [70.0, 20.0])
        # La caché trae lo que respondió el modelo, no lo repartido.
        huella = Cache.huella(caso.politica())
        for agente in corrida.agentes:
            notas, _ = cache.buscar(huella, corrida.clave, agente)
            self.assertEqual(notas[0], random.Random(agente.indice).choice([1, 2, 3, 5, 6, 7]))
        self.assertTrue(all(r.respuestas[1:] == [4, 3, 4, 2] for r in caso.respuestas.values()))
        # Repetir la pregunta sale de la caché, no vuelve a pronosticar y da el mismo total.
        motor2 = MotorFalso((10.0, 80.0))
        otra, _ = self.correr(motor2, cache=cache)
        self.assertEqual(motor2.pronosticos, 0)
        self.assertLess(abs(otra.casos[0].apoyo() * 100 - 70), 5)

    def test_sin_pronostico_sigue_sin_ancla(self):
        corrida, _ = self.correr(MotorFalso(falla=True))
        caso = corrida.casos[0]
        self.assertEqual(len(caso.respuestas), 200)
        self.assertIsNone(caso.ancla)
        crudo = sum(random.Random(k).choice([1, 2, 3, 5, 6, 7]) >= 5 for k in range(200)) / 200
        self.assertAlmostEqual(caso.apoyo(), crudo)
        self.assertIsNone(next(d for t, d in corrida.eventos if t == "caso_listo")["ancla"])


if __name__ == "__main__":
    unittest.main()
