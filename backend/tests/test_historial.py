import gzip
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from servidor import historial as modulo
from servidor.historial import Historial, resumen_de, vista_de


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


def corrida_con_eventos(identificador="0123456789ab", cancelada=False):
    """Una corrida de dos agentes con lo que la vista necesita: sus índices y los eventos que publicó."""
    eventos = [("inicio", {"casos": [{"letra": "A", "texto": "Algo"}]}), ("respuestas", {"caso": 0, "r": [[0, 6, "", [6]], [1, 2, "", [2]]]}), ("fin", {})]
    base = corrida([caso("A", "Algo", [6, 2])], agentes=2, cancelada=cancelada)
    base.id, base.eventos, base.agentes = identificador, eventos, [SimpleNamespace(indice=0), SimpleNamespace(indice=1)]
    return base


MUESTRA = SimpleNamespace(cuerpo=lambda: b'{"id": "m1", "agentes": [{"i": 0}, {"i": 1}]}')


class Vista(unittest.TestCase):
    def test_lleva_la_muestra_los_agentes_los_filtros_y_los_eventos(self):
        vista = json.loads(vista_de(corrida_con_eventos(), MUESTRA, {"tamano": 1000, "elegidos": {"region": [5]}}))
        self.assertEqual(vista["muestra"]["id"], "m1")
        self.assertEqual(vista["agentes"], [0, 1])
        self.assertEqual(vista["filtros"]["elegidos"], {"region": [5]})
        self.assertEqual([tipo for tipo, _ in vista["eventos"]], ["inicio", "respuestas", "fin"])

    def test_lo_que_no_son_filtros_no_se_guarda(self):
        self.assertIsNone(json.loads(vista_de(corrida_con_eventos(), MUESTRA, "x" * 10))["filtros"])
        self.assertIsNone(json.loads(vista_de(corrida_con_eventos(), MUESTRA, {"a": "x" * 5000}))["filtros"])

    def test_al_terminar_queda_la_vista_y_el_historial_lo_dice(self):
        with tempfile.TemporaryDirectory() as carpeta:
            historial = Historial(Path(carpeta))
            historial.guardar_al_terminar(corrida_con_eventos(), MUESTRA, {"tamano": 1000})
            self.assertTrue(historial.ultimas()[0]["vista"])
            self.assertEqual(json.loads(gzip.decompress(historial.vista("0123456789ab")))["agentes"], [0, 1])
            # Al volver a partir, el motor sigue sabiendo cuáles se pueden abrir.
            self.assertTrue(Historial(Path(carpeta)).ultimas()[0]["vista"])

    def test_sin_muestra_o_detenida_solo_queda_el_resumen(self):
        with tempfile.TemporaryDirectory() as carpeta:
            historial = Historial(Path(carpeta))
            historial.guardar_al_terminar(corrida_con_eventos("aaaaaaaaaaaa"))
            historial.guardar_al_terminar(corrida_con_eventos("bbbbbbbbbbbb", cancelada=True), MUESTRA)
            self.assertEqual([e["vista"] for e in historial.ultimas()], [False, False])
            self.assertIsNone(historial.vista("aaaaaaaaaaaa"))

    def test_solo_se_aceptan_identificadores_de_corrida(self):
        with tempfile.TemporaryDirectory() as carpeta:
            historial = Historial(Path(carpeta))
            self.assertIsNone(historial.vista("../corridas"))
            with self.assertRaises(ValueError):
                historial.guardar_vista("../fuera", b"{}")

    def test_se_botan_las_vistas_mas_antiguas(self):
        with tempfile.TemporaryDirectory() as carpeta:
            historial = Historial(Path(carpeta))
            guardadas, modulo.VISTAS_GUARDADAS = modulo.VISTAS_GUARDADAS, 2
            try:
                for k in range(3):
                    historial.guardar_vista(f"{k:012x}", b"{}")
            finally:
                modulo.VISTAS_GUARDADAS = guardadas
            self.assertIsNone(historial.vista(f"{0:012x}"))
            self.assertIsNotNone(historial.vista(f"{2:012x}"))


if __name__ == "__main__":
    unittest.main()
