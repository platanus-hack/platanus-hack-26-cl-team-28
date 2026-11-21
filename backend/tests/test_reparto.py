"""El reparto de la muestra entre regiones, comunas y zonas (`poblacion.repartir`).

    uv run python -m unittest tests.test_reparto

Las pruebas con la tabla de agentes se saltan si falta DuckDB o `data/agentes/`.
"""

import random
import sys
import unittest
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from servidor import poblacion
from servidor.poblacion import repartir


def estratos_al_azar(semilla: int, regiones: int = 16) -> dict:
    """Regiones con comunas de tamaños muy distintos, cada una con zona urbana y a veces rural."""
    azar = random.Random(semilla)
    estratos = {}
    for r in range(1, regiones + 1):
        for c in range(azar.randint(1, 40)):
            for zona in (1, 2) if azar.random() < 0.8 else (1,):
                personas = int(azar.lognormvariate(9, 2)) + 1
                estratos[(r, r * 1000 + c, zona)] = (max(1, personas // 10), personas)
    return estratos


def cuota_exacta(tamano: int, estratos: dict, nivel) -> dict:
    total = sum(p for _, p in estratos.values())
    exacta = defaultdict(float)
    for clave, (_, p) in estratos.items():
        exacta[nivel(clave)] += tamano * p / total
    return exacta


def sumar(cuotas: dict, nivel) -> dict:
    suma = defaultdict(int)
    for clave, c in cuotas.items():
        suma[nivel(clave)] += c
    return suma


NIVELES = {
    "región": lambda k: k[0],
    "comuna": lambda k: k[1],
    "estrato": lambda k: k,
    "zona en la región": lambda k: (k[0], k[2]),
    "zona en el país": lambda k: k[2],
}


class Reparto(unittest.TestCase):
    def test_proporcional_en_cada_nivel(self):
        for semilla in range(20):
            estratos = estratos_al_azar(semilla)
            for tamano in (1, 7, 50, 250, 500, 1000, 2000):
                cuotas = repartir(tamano, estratos)
                assert sum(cuotas.values()) == tamano
                for nombre, nivel in NIVELES.items():
                    exacta, obtenida = cuota_exacta(tamano, estratos, nivel), sumar(cuotas, nivel)
                    for clave, valor in exacta.items():
                        self.assertLess(abs(obtenida[clave] - valor), 1, (semilla, tamano, nombre, clave))

    def test_la_muestra_chica_queda_casi_entera_en_la_del_doble(self):
        # Estos estratos son más disparejos que los de la tabla, con muchos más que pesan menos
        # de una persona: ahí es donde la muestra chica y la grande pueden no calzar.
        for tamano in (125, 250, 500, 1000):
            fuera = 0
            for semilla in range(20):
                estratos = estratos_al_azar(semilla)
                chica, grande = repartir(tamano, estratos), repartir(2 * tamano, estratos)
                fuera += sum(max(0, chica[k] - grande[k]) for k in estratos)
            self.assertLessEqual(fuera / 20, 0.08 * tamano, tamano)

    def test_siempre_la_misma(self):
        estratos = estratos_al_azar(3)
        self.assertEqual(repartir(500, estratos), repartir(500, dict(reversed(list(estratos.items())))))

    def test_ningun_estrato_pasa_de_sus_disponibles(self):
        estratos = {(1, 1, 1): (2, 900), (1, 2, 1): (50, 50), (2, 3, 1): (50, 50)}
        cuotas = repartir(20, estratos)
        assert cuotas[(1, 1, 1)] == 2
        assert sum(cuotas.values()) == 20
        assert abs(cuotas[(1, 2, 1)] - cuotas[(2, 3, 1)]) <= 1

    def test_sin_suficientes_entran_todos(self):
        estratos = {(1, 1, 1): (3, 30), (1, 1, 2): (4, 10), (2, 2, 1): (0, 0)}
        assert repartir(100, estratos) == {(1, 1, 1): 3, (1, 1, 2): 4, (2, 2, 1): 0}
        assert sum(repartir(0, estratos).values()) == 0

    def test_sin_personas_reparte_por_disponibles(self):
        cuotas = repartir(10, {(1, 1, 1): (30, 0), (2, 2, 1): (10, 0)})
        assert sum(cuotas.values()) == 10
        assert cuotas[(1, 1, 1)] in (7, 8)


class Tabla(unittest.TestCase):
    """La muestra que sale de verdad de la tabla de agentes."""

    @classmethod
    def setUpClass(cls):
        try:
            cls.tabla = poblacion.TablaAgentes()
        except (ImportError, FileNotFoundError) as error:
            raise unittest.SkipTest(f"sin tabla de agentes: {error}")

    def estratos_de(self, agentes) -> list[tuple]:
        ids = [int(a.id[1:]) for a in agentes]
        return self.tabla._con.execute(
            "select region, comuna, area from rasgos where id_persona_muestra in (select unnest(?::bigint[]))", [ids]
        ).fetchall()

    def test_proporcional_en_cada_nivel(self):
        for filtros in ({}, {"quintil": [4]}, {"edadMin": 18, "edadMax": 29}):
            f = poblacion.limpiar(filtros)
            conteo = self.tabla._con.execute(
                f"select region, comuna, area, sum(representa) from rasgos where {self.tabla._condiciones(f, 'representa')} group by all"
            ).fetchall()
            estratos = {(r, c, z): (0, p) for r, c, z, p in conteo}
            for tamano in (250, 1000):
                elegidos = defaultdict(int)
                for e in self.estratos_de(self.tabla.muestra(filtros, tamano).agentes):
                    elegidos[e] += 1
                for nombre, nivel in NIVELES.items():
                    exacta, obtenida = cuota_exacta(tamano, estratos, nivel), sumar(elegidos, nivel)
                    for clave, valor in exacta.items():
                        self.assertLess(abs(obtenida[clave] - valor), 1, (filtros, tamano, nombre, clave))

    def test_la_de_250_queda_casi_entera_en_la_de_500(self):
        chica = {a.id for a in self.tabla.muestra({}, 250).agentes}
        grande = {a.id for a in self.tabla.muestra({}, 500).agentes}
        self.assertGreaterEqual(len(chica & grande), 0.95 * len(chica))


if __name__ == "__main__":
    unittest.main()
