import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from servidor.historial import Historial, resumen_de


def caso(letra, texto, notas, documento=None, iteracion=None):
    respuestas = {i: SimpleNamespace(acuerdo=n) for i, n in enumerate(notas)}
    return SimpleNamespace(letra=letra, texto=texto, titulo="", documento=documento, iteracion=iteracion, respuestas=respuestas)


def corrida(casos, agentes=4, cancelada=False):
    return SimpleNamespace(
        id="abc123", casos=casos, agentes=list(range(agentes)), cancelada=cancelada, inicio=time.time(),
        motor=SimpleNamespace(describir=lambda: {"modelo": "claude-haiku"}),
        metricas=lambda: {"segundos": 12.5, "costo_usd": 0.05, "llamadas": 1, "tokens": 10},
        correr=lambda: None,
    )


class Resumen(unittest.TestCase):
    def test_cuenta_a_favor_en_contra_y_sin_decidir_por_variante(self):
        entrada = resumen_de(corrida([caso("A", " Rebajar el TAG ", [6, 5, 4, 2]), caso("B", "Otra", [1, 2, 3, 7])]))
        a, b = entrada["casos"]
        self.assertEqual((a["texto"], a["favor"], a["contra"], a["indecisa"], a["respondidas"]), ("Rebajar el TAG", 2, 1, 1, 4))
        self.assertEqual((b["favor"], b["contra"], b["indecisa"]), (1, 3, 0))
        self.assertTrue(entrada["completa"])
        self.assertEqual(entrada["agentes"], 4)
        self.assertRegex(entrada["hora"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\+00:00$")

    def test_sin_respuestas_no_queda_nada(self):
        self.assertIsNone(resumen_de(corrida([caso("A", "Algo", [])])))

    def test_detenida_o_incompleta_queda_marcada(self):
        self.assertFalse(resumen_de(corrida([caso("A", "Algo", [5, 5])]))["completa"])
        self.assertFalse(resumen_de(corrida([caso("A", "Algo", [5, 5, 5, 5])], cancelada=True))["completa"])

    def test_documento_y_variante_del_agente(self):
        entrada = resumen_de(corrida([caso("A", "", [5] * 4, documento={"nombre": "ley.pdf", "titulo": "Ley corta", "texto": "..."}), caso("B", "Mejorada", [5] * 4, iteracion={"de": "A"})]))
        self.assertEqual((entrada["casos"][0]["documento"], entrada["casos"][0]["titulo"]), ("ley.pdf", "Ley corta"))
        self.assertEqual([c["iteracion"] for c in entrada["casos"]], [False, True])


class Archivo(unittest.TestCase):
    def test_se_guarda_y_se_vuelve_a_leer_de_la_mas_nueva_a_la_mas_antigua(self):
        with tempfile.TemporaryDirectory() as carpeta:
            historial = Historial(Path(carpeta) / "historial")
            for k in range(3):
                historial.agregar({"id": str(k), "casos": []})
            historial.agregar(None)
            self.assertEqual([e["id"] for e in historial.ultimas()], ["2", "1", "0"])
            self.assertEqual([e["id"] for e in Historial(Path(carpeta) / "historial").ultimas(2)], ["2", "1"])

    def test_una_linea_danada_no_impide_leer_el_resto(self):
        with tempfile.TemporaryDirectory() as carpeta:
            archivo = Path(carpeta) / "corridas.jsonl"
            archivo.write_text('{"id": "a", "casos": []}\nesto no es json\n{"id": "b", "casos": []}\n', encoding="utf-8")
            self.assertEqual([e["id"] for e in Historial(Path(carpeta)).ultimas()], ["b", "a"])

    def test_guarda_al_terminar_la_corrida(self):
        with tempfile.TemporaryDirectory() as carpeta:
            historial = Historial(Path(carpeta))
            historial.guardar_al_terminar(corrida([caso("A", "Algo", [5, 5, 2, 4])]))
            self.assertEqual(historial.ultimas()[0]["casos"][0]["favor"], 2)


if __name__ == "__main__":
    unittest.main()
