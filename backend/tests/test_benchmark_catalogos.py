import json
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from correr_benchmark_luna import agregado, armar_lotes, leer_respuesta
from preparar_benchmark_catalogos import ordenar, reducir


class BenchmarkCatalogos(unittest.TestCase):
    def test_reduccion_preserva_masa_y_celdas_protegidas(self):
        d = {k: np.array([1, 1, 1, 1, 1, 1, 2, 2]) for k in (
            "region", "zona", "edad", "educacion", "sexo", "hogar", "viaje",
            "ocupacion", "laboral", "edad_fina", "comuna",
        )}
        d["id"] = np.arange(8)
        orden = ordenar(d)
        reps, pesos, bordes = reducir(d, orden, 4, 3)
        self.assertEqual(len(set(reps)), 4)
        self.assertEqual(pesos.sum(), len(d["id"]) * 3)
        for i, rep in enumerate(reps):
            miembros = orden[bordes[i]:bordes[i+1]]
            self.assertIn(rep, miembros)
            self.assertEqual(pesos[i], 3 * len(miembros))
            for k in ("region", "zona", "edad", "educacion"):
                self.assertTrue((d[k][miembros] == d[k][rep]).all())

    def test_ampliacion_reutiliza_lotes_anteriores(self):
        perfiles = {str(i): f"perfil {i}" for i in range(10)}
        muestra = lambda fin: {"ids": list(perfiles)[:fin], "perfil": perfiles}
        cat = {"muestras": {"1000": muestra(6), "2000": muestra(10)}}
        a = list(armar_lotes(cat, 1000, 2))
        b = list(armar_lotes(cat, 2000, 2))
        self.assertEqual(a, b[:len(a)])
        self.assertEqual(len(set(x for ids, _ in b for x in ids)), 10)

    def test_tres_niveles_conservan_los_prompts_y_bordes_de_ampliacion(self):
        perfiles = {str(i): f"perfil {i}" for i in range(12)}
        tamanos = {2000: 3, 5000: 7, 10000: 12}
        cat = {"muestras": {str(n): {"ids": list(perfiles)[:k], "perfil": perfiles}
                            for n, k in tamanos.items()}}
        primero, medio, final = [list(armar_lotes(cat, n, 2)) for n in tamanos]
        self.assertEqual(primero, medio[:len(primero)])
        self.assertEqual(medio, final[:len(medio)])
        self.assertEqual([len(ids) for ids, _ in final], [2, 1, 2, 2, 2, 2, 1])
        self.assertEqual(len({x for ids, _ in final for x in ids}), 12)

    def test_salida_rechaza_lotes_incompletos(self):
        ev = {"type":"item.completed", "item":{"type":"agent_message","text":"{\"r\":[1,2,3]}"}}
        self.assertEqual(leer_respuesta(json.dumps(ev), 3)[0], [1,2,3])
        with self.assertRaises(ValueError):
            leer_respuesta(json.dumps(ev), 4)

    def test_agregado_no_puntua_una_muestra_parcial(self):
        muestra = {"ids":["1","2","3"], "peso":[4,1,1], "peso_ipf":None}
        self.assertNotIn("mae_pp", agregado(muestra, {"1":1}, "peso"))
        d = agregado(muestra, {"1":1,"2":2,"3":3}, "peso")
        self.assertAlmostEqual(d["pct"][0], 100 * 4/6)
        self.assertIsNone(agregado(muestra, {}, "peso_ipf"))


if __name__ == "__main__":
    unittest.main()
