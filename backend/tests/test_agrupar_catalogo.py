import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from agrupar_catalogo import ANCHO, DESPLAZAMIENTOS, comparar


def firma(atributos):
    estrato = ((((13101 * 3 + 1) * 4 + 2) * 5 + 1) * 11) + 1
    return (estrato << ANCHO) | sum(k << bit for k, bit in zip(atributos, DESPLAZAMIENTOS))


class AgrupacionesFijas(unittest.TestCase):
    def test_cierre_sin_grupos_parciales(self):
        firmas = np.array([firma([2, 6, 4, 5, 1, 1, 3, 2])], dtype=np.uint64)
        for n, esperados in [(10, (10, 3)), (5, (10, 3)), (3, (12, 1))]:
            with self.subTest(tamano=n):
                m, grupos, estrictos = comparar(firmas, np.array([13], dtype=np.int32), n)
                self.assertEqual((m["personas_representadas"], m["remanente"]), esperados)
                self.assertEqual(grupos[0] * n, esperados[0])
                self.assertEqual(estrictos[0], grupos[0])

    def test_ocupados_necesitan_siete_de_ocho_coincidencias(self):
        base = [2, 6, 4, 5, 1, 1, 3, 2]
        for otra, esperados in [([*base[:-1], 3], 1), ([*base[:-2], 4, 3], 0)]:
            with self.subTest(otra=otra):
                firmas = np.array(sorted(map(firma, (base, otra))), dtype=np.uint64)
                m, _, _ = comparar(firmas, np.array([2, 1], dtype=np.int32), 3)
                self.assertEqual(m["grupos"], 1)
                self.assertEqual(m["grupos_que_cumplen_80_y_estrato"], esperados)


if __name__ == "__main__":
    unittest.main()
