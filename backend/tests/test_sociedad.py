"""Los parámetros con que se elige a quiénes preguntar: catálogo, filtro y retrato.

    uv run python -m unittest tests.test_sociedad

Las pruebas con la tabla de agentes se saltan si falta DuckDB o `data/agentes/`.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from servidor import poblacion, sociedad

SIN = (sociedad.SIN_DATO,) * len(sociedad.CLAVES)


def rasgos(**opciones) -> tuple:
    """Una persona con las opciones dadas y sin dato en lo demás."""
    return tuple(opciones.get(clave, sociedad.SIN_DATO) for clave in sociedad.CLAVES)


class Catalogo(unittest.TestCase):
    def test_claves_unicas_y_con_opciones(self):
        self.assertEqual(len(set(sociedad.CLAVES)), len(sociedad.CLAVES))
        for p in sociedad.PARAMETROS:
            self.assertGreaterEqual(len(p.opciones), 2, p.clave)
            self.assertEqual(len(set(p.opciones)), len(p.opciones), p.clave)

    def test_limpiar_deja_solo_lo_que_filtra(self):
        pedido = {"region": [6, 6, 2], "genero": [0, 1], "educacion": [], "quintil": [9, -1, "x", 2.0, True], "politica": 3, "inventado": [1]}
        self.assertEqual(sociedad.limpiar(pedido), {"region": [2, 6], "quintil": [2]})
        self.assertEqual(sociedad.limpiar(None), {})

    def test_filtros_iguales_comparten_muestra(self):
        a = poblacion.limpiar({"region": [6, 2], "edadMin": 14, "genero": [1, 0]})
        b = poblacion.limpiar({"region": [2, 6, 6], "edadMax": 120})
        self.assertEqual(poblacion.identificador(a, 500), poblacion.identificador(b, 500))
        self.assertNotEqual(poblacion.identificador(a, 500), poblacion.identificador(poblacion.limpiar({"region": [2]}), 500))


class RetratoEnMemoria(unittest.TestCase):
    PERSONAS = [
        (rasgos(genero=0, trabajo=0), 30, 10),
        (rasgos(genero=0, trabajo=2), 70, 20),
        (rasgos(genero=1, trabajo=0), 40, 30),
        (rasgos(genero=1, trabajo=1), 16, 40),
        (rasgos(genero=1), 85, 50),
    ]

    def test_sin_filtros_cuenta_a_todos(self):
        retrato = sociedad.retrato_de(self.PERSONAS, {}, 14, 85)
        self.assertEqual(retrato["genero"], [30, 120])
        self.assertEqual(retrato["trabajo"], [40, 40, 20])
        self.assertEqual(sum(retrato["edad"]), 150)
        # Del tope en adelante es un solo tramo, el último.
        self.assertEqual(retrato["edad"][-1], 50)

    def test_cada_parametro_ignora_su_propio_filtro(self):
        retrato = sociedad.retrato_de(self.PERSONAS, {"genero": [0], "trabajo": [0]}, 14, 85)
        # Género: quienes trabajan, de cualquier género. Trabajo: las mujeres, en cualquier situación.
        self.assertEqual(retrato["genero"], [10, 30])
        self.assertEqual(retrato["trabajo"], [10, 0, 20])
        # Lo demás, solo quienes cumplen todo.
        self.assertEqual(sum(retrato["edad"]), 10)

    def test_la_edad_filtra_a_los_demas_pero_no_a_si_misma(self):
        retrato = sociedad.retrato_de(self.PERSONAS, {}, 18, 60)
        self.assertEqual(retrato["genero"], [10, 30])
        self.assertEqual(sum(retrato["edad"]), 150)
        self.assertEqual(retrato["edad"][16 - sociedad.EDAD_MINIMA], 40)

    def test_sin_dato_queda_fuera_al_filtrar(self):
        self.assertFalse(sociedad.coincide(rasgos(genero=1), {"trabajo": [0, 1, 2]}))
        self.assertTrue(sociedad.coincide(rasgos(genero=1), {"trabajo": [0]}, salvo="trabajo"))


class ArchivoDeRespaldo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fuente = poblacion.ArchivoFijo()

    def test_todos_traen_un_rasgo_por_parametro(self):
        for a in self.fuente.agentes:
            self.assertEqual(len(a.rasgos), len(sociedad.CLAVES))
            for p, opcion in zip(sociedad.PARAMETROS, a.rasgos):
                self.assertTrue(-1 <= opcion < len(p.opciones), (p.clave, opcion))

    def test_la_muestra_cumple_lo_elegido_y_cuadra_con_el_retrato(self):
        filtros = {"politica": [0, 1], "trabajo": [0], "edadMin": 30, "edadMax": 60}
        muestra = self.fuente.muestra(filtros, 5000)
        self.assertGreater(len(muestra.agentes), 0)
        for a in muestra.agentes:
            self.assertIn(a.rasgos[sociedad.POSICION["politica"]], (0, 1))
            self.assertEqual(a.rasgos[sociedad.POSICION["trabajo"]], 0)
            self.assertTrue(30 <= a.edad <= 60)
        self.assertEqual(sum(muestra.retrato["politica"][:2]), muestra.disponibles)
        self.assertEqual(muestra.retrato["trabajo"][0], muestra.disponibles)
        self.assertEqual(sum(muestra.retrato["edad"][30 - 14 : 60 - 14 + 1]), muestra.disponibles)
        self.assertEqual(muestra.publica()["dimensiones"], list(sociedad.CLAVES))

    def test_los_menores_no_tienen_opinion(self):
        opinion = [sociedad.POSICION[c] for c in ("politica", "gobierno", "voto", "confianza")]
        menores = [a for a in self.fuente.agentes if a.edad < 18]
        self.assertGreater(len(menores), 0)
        for a in menores:
            self.assertEqual([a.rasgos[k] for k in opinion], [-1] * 4)


class Tabla(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.tabla = poblacion.TablaAgentes()
        except (ImportError, FileNotFoundError) as error:
            raise unittest.SkipTest(f"sin tabla de agentes: {error}")

    def test_el_sql_y_el_perfil_dan_la_misma_opcion(self):
        """La tabla filtra con SQL y el archivo de respaldo con los grupos del perfil: deben coincidir."""
        perfiles, etiquetas, secciones = self.tabla._perfiles, self.tabla._etiquetas, self.tabla._secciones
        agentes = self.tabla.muestra({}, 2000).agentes + self.tabla.muestra({"edadMax": 17}, 300).agentes
        distintos = {}
        for a in agentes:
            _, grupos = perfiles.describir(a.fila, etiquetas, secciones, con_cep=True)
            esperado = sociedad.codigos(grupos, perfiles.datos_sueltos(a.fila, etiquetas, grupos))
            for clave, del_sql, del_perfil in zip(sociedad.CLAVES, a.rasgos, esperado):
                if del_sql != del_perfil:
                    distintos.setdefault(clave, []).append((a.id, del_sql, del_perfil))
        self.assertEqual(distintos, {})

    def test_el_retrato_de_la_tabla_es_el_de_la_definicion(self):
        """La consulta agrupada da lo mismo que contar persona por persona (en el nivel de 1.000, que es chico)."""
        nivel = max(self.tabla._niveles)
        peso = self.tabla._niveles[nivel]
        codigos = ", ".join(f"c_{c}" for c in sociedad.CLAVES)
        filas = self.tabla._con.execute(f"select {codigos}, edad, {peso} from rasgos where {peso} is not null").fetchall()
        personas = [(tuple(f[:-2]), f[-2], f[-1]) for f in filas]
        for filtros in ({}, {"region": [6], "genero": [1]}, {"politica": [0, 1], "gobierno": [0], "edadMin": 30, "edadMax": 70}, {"salud": [2], "menores": [0]}):
            with self.subTest(filtros=filtros):
                f = poblacion.limpiar({**filtros, "reduccion": nivel})
                muestra = self.tabla.muestra({**filtros, "reduccion": nivel}, 50)
                self.assertEqual(muestra.retrato, sociedad.retrato_de(personas, f["elegidos"], f["edadMin"], f["edadMax"]))

    def test_el_retrato_cuadra_con_las_personas_representadas(self):
        muestra = self.tabla.muestra({}, 10)
        self.assertEqual(sum(muestra.retrato["edad"]), muestra.representadas)
        self.assertEqual(sum(muestra.retrato["region"]), muestra.representadas)
        elegidas = self.tabla.muestra({"region": [6, 5], "voto": [1]}, 10)
        self.assertEqual(elegidas.retrato["region"][6] + elegidas.retrato["region"][5], elegidas.representadas)
        self.assertEqual(elegidas.retrato["voto"][1], elegidas.representadas)

    def test_cada_agente_cumple_lo_elegido(self):
        muestra = self.tabla.muestra({"nacionalidad": [1], "vivienda": [1], "confianza": [0]}, 400)
        self.assertGreater(len(muestra.agentes), 0)
        for a in muestra.agentes:
            self.assertEqual([a.rasgos[sociedad.POSICION[c]] for c in ("nacionalidad", "vivienda", "confianza")], [1, 1, 0])


if __name__ == "__main__":
    unittest.main()
