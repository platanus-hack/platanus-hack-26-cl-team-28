import itertools
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from benchmark_neyman_catalogos import medoid, repartir, viajes_rm


class BenchmarkNeyman(unittest.TestCase):
    def test_medoide_resuelve_distancia_mixta(self):
        d = {
            "edad_fina": np.array([20, 70, 30, 65, 45]),
            "comuna": np.array([13101, 13101, 13102, 13101, 13102]),
            "sexo": np.array([1, 2, 1, 1, 1]),
            "laboral": np.array([1, 1, 3, 1, 1]),
            "ocupacion": np.zeros(5),
            "viaje": np.array([1, 1, 0, 1, 1]),
            "hogar": np.array([2, 4, 4, 2, 2]),
        }
        campos = [k for k in d if k != "edad_fina"]
        i = np.arange(5)
        edad = d["edad_fina"]
        dist = np.abs(edad[:, None] - edad[None, :]) / 70
        for k in campos:
            dist += d[k][:, None] != d[k][None, :]
        total = dist.sum(axis=1)
        self.assertAlmostEqual(total[medoid(d, i)], total.min())

    def test_cuotas_con_restricciones_minimizan_varianza_objetivo(self):
        cap = np.array([2, 6, 8])
        piso = np.array([1, 3, 1])
        prioridad = np.array([6., 11., 8.])
        q = repartir(9, cap, prioridad, piso)
        candidatos = [np.array(c) for c in itertools.product(*[range(a,b+1) for a,b in zip(piso,cap)])
                      if sum(c) == 9]
        self.assertAlmostEqual(np.sum(prioridad**2/q), min(np.sum(prioridad**2/x) for x in candidatos))

    def test_proteccion_transporte_solo_en_rm(self):
        d = {"region": np.array([13, 13, 13, 5, 6]), "viaje": np.array([1, 2, 3, 1, 2])}
        np.testing.assert_array_equal(viajes_rm(d), [1, 2, 0, 0, 0])


if __name__ == "__main__":
    unittest.main()
