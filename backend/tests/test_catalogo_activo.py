import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from servidor import poblacion


class CatalogoActivo(unittest.TestCase):
    def test_flag_indica_catalogo_exacto(self):
        with TemporaryDirectory() as d:
            carpetas = {n: Path(d) / str(n) for n in (3, 5)}
            for carpeta in carpetas.values():
                carpeta.mkdir()
                (carpeta / "catalogo.json").touch()
            for n in (3, 5):
                with self.subTest(n=n), patch.dict("os.environ", {"TAMANO_GRUPO": str(n)}), \
                        patch.object(poblacion, "CARPETAS_GRUPOS", carpetas), patch.object(poblacion, "TablaAgentes") as tabla:
                    poblacion.elegir_poblacion()
                    tabla.assert_called_once_with(carpetas[n], tamano_grupo=n)

    def test_flag_rechaza_niveles_fuera_del_experimento(self):
        with patch.dict("os.environ", {"TAMANO_GRUPO": "10"}):
            with self.assertRaisesRegex(ValueError, "3 o 5"):
                poblacion.elegir_poblacion()

    def test_flag_rechaza_replay_y_catalogo_faltante(self):
        with TemporaryDirectory() as d, patch.dict("os.environ", {"TAMANO_GRUPO": "5"}), \
                patch.object(poblacion, "CARPETAS_GRUPOS", {5: Path(d)}):
            with self.assertRaisesRegex(ValueError, "motor en vivo"):
                poblacion.elegir_poblacion(fija=True)
            with self.assertRaisesRegex(FileNotFoundError, "Falta el catálogo"):
                poblacion.elegir_poblacion()

    def test_mismos_filtros_identifican_muestras_distintas(self):
        filtros = poblacion.limpiar({})
        ids = {poblacion.identificador(filtros, 500, n) for n in (3, 5, None)}
        self.assertEqual(len(ids), 3)


if __name__ == "__main__":
    unittest.main()
