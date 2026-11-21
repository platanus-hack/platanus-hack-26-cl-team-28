import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from reducir_poblacion import DATOS, POLITICA, RAZON, elegir, reducir, tipos_politicos


def region_de_prueba(n, semilla=7):
    """Personas inventadas con todos los datos que usa la reducción; el tipo arrastra el voto y la aprobación."""
    rng = np.random.default_rng(semilla)
    tipo = rng.integers(0, 9, n)
    datos = {nombre: rng.integers(0, 4, n) for nombre in DATOS}
    datos |= {
        "tipo": tipo,
        "eje": tipo * 100 + rng.integers(0, 100, n),
        "comuna": rng.integers(0, 6, n),
        "zona": rng.integers(0, 2, n),
        "sexo": rng.integers(0, 2, n),
        "voto": np.where(rng.random(n) < 0.8, tipo % 3, rng.integers(0, 3, n)),
        "aprueba": np.where(rng.random(n) < 0.8, tipo % 2, rng.integers(0, 2, n)),
    }
    return datos


def reparto(valores, pesos=None):
    cuenta = np.bincount(valores, weights=pesos, minlength=int(valores.max()) + 1)
    return 100 * cuenta / cuenta.sum()


class TiposPoliticos(unittest.TestCase):
    def test_separa_dos_bloques_opuestos(self):
        bloque = np.repeat([0, 1], 20)
        respuestas = {dato: bloque * 2 + 1 for dato, _ in POLITICA}
        tipo, eje = tipos_politicos(respuestas, np.full(40, 100), k=2)
        self.assertEqual(len(set(tipo[:20])), 1)
        self.assertEqual(len(set(tipo[20:])), 1)
        self.assertNotEqual(tipo[0], tipo[-1])
        self.assertEqual(sorted(tipo.tolist())[0], 1)
        self.assertEqual(sorted(eje.tolist()), list(range(40)))

    def test_no_pide_mas_tipos_que_respuestas_distintas(self):
        respuestas = {dato: np.array([1, 1, 2, 2]) for dato, _ in POLITICA}
        tipo, _ = tipos_politicos(respuestas, np.ones(4), k=8)
        self.assertEqual(set(tipo.tolist()), {1, 2})


class Representantes(unittest.TestCase):
    def test_la_minoria_no_desaparece(self):
        # Cada grupo de 10 tiene 3 de la minoría: el más típico sería siempre de la mayoría.
        grupos = 200
        categorias = np.tile(np.array([0] * 7 + [1] * 3), grupos).reshape(-1, 1)
        elegidos = elegir(categorias, np.ones(len(categorias)), np.repeat(np.arange(grupos), RAZON))
        minoria = categorias[elegidos, 0].mean()
        self.assertAlmostEqual(minoria, 0.3, delta=0.01)

    def test_elige_uno_por_grupo_y_dentro_de_el(self):
        categorias = np.random.default_rng(1).integers(0, 5, (95, 3))
        grupo = np.arange(95) // RAZON
        elegidos = elegir(categorias, np.ones(95), grupo)
        self.assertEqual(grupo[elegidos].tolist(), list(range(10)))


class Reduccion(unittest.TestCase):
    def setUp(self):
        self.n = 60_003
        self.datos = region_de_prueba(self.n)
        self.niveles, self.parecido = reducir(self.datos, semilla=3)

    def test_cada_nivel_representa_a_todos_y_esta_dentro_del_anterior(self):
        anteriores, quedan = set(range(self.n)), self.n
        for elegidos, pesos in self.niveles:
            quedan = -(-quedan // RAZON)
            self.assertEqual(len(elegidos), quedan)
            self.assertEqual(len(set(elegidos.tolist())), quedan)
            self.assertEqual(int(pesos.sum()), self.n)
            self.assertLessEqual(set(elegidos.tolist()), anteriores)
            anteriores = set(elegidos.tolist())

    def test_los_pesos_son_parejos(self):
        for nivel, (_, pesos) in enumerate(self.niveles, start=1):
            self.assertEqual(int(pesos.max()), RAZON**nivel)
            self.assertLessEqual(int((pesos < RAZON**nivel).sum()), nivel)

    def test_lo_equilibrado_calza_con_la_poblacion(self):
        # Con 6.000 y 600 agentes calza casi exacto; con 60, cada agente ya vale 1,7 puntos.
        for (elegidos, pesos), tolerancia in zip(self.niveles, (0.2, 1, 5)):
            for dato in ("tipo", "voto", "sexo", "edad", "comuna"):
                diferencia = np.abs(reparto(self.datos[dato][elegidos], pesos) - reparto(self.datos[dato])).max()
                self.assertLess(diferencia, tolerancia, dato)

    def test_el_representante_comparte_el_tipo_politico(self):
        for cuenta in self.parecido[:2]:
            self.assertGreater(cuenta["tipo"] / self.n, 0.9)
        self.assertGreater(self.parecido[0]["comuna"] / self.n, 0.95)

    def test_es_reproducible(self):
        otra, _ = reducir(self.datos, semilla=3)
        for (a, pa), (b, pb) in zip(self.niveles, otra):
            self.assertTrue(np.array_equal(a, b) and np.array_equal(pa, pb))


if __name__ == "__main__":
    unittest.main()
