import gzip
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.request import urlopen
from uuid import uuid4

from starlette.testclient import TestClient

from servidor.motor import Motor

# La API web local se puede probar sin login ni binario de Claude.
with patch("servidor.motor.elegir_motor", return_value=Motor()):
    from servidor import __main__ as web

from servidor.historial import Historial
from whatif_mcp.protocolo import crear_mcp
from whatif_mcp.runtime import RuntimeAislado
from whatif_mcp.servicio import Servicio


class Integracion(unittest.TestCase):
    def setUp(self):
        self.carpeta = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.historial = Historial(self.carpeta / "web")
        self.enterContext(patch.object(web, "HISTORIAL", self.historial))
        self.enterContext(patch.object(web, "HISTORIAL_OCULTO", False))
        self.enterContext(patch.object(web, "CORRIDAS", {}))
        self.enterContext(patch.object(web, "ORIGEN", {}))
        self.runtime = web
        self.conectar(web)

    def conectar(self, runtime):
        self.runtime = runtime
        self.servicio = Servicio(runtime)
        self.mcp = self.enterContext(TestClient(crear_mcp(self.servicio).streamable_http_app(),
                                                base_url="http://localhost:8788"))

    def iniciar_web(self):
        api = web.Servidor(("127.0.0.1", 0), web.Manejador)
        hilo = threading.Thread(target=api.serve_forever, daemon=True)
        hilo.start()
        self.addCleanup(api.server_close)
        self.addCleanup(api.shutdown)

        def pedir(ruta):
            with urlopen(f"http://127.0.0.1:{api.server_port}/api/{ruta}", timeout=5) as respuesta:
                return json.load(respuesta)

        return pedir

    def rpc(self, metodo, params=None, **headers):
        cabeceras = {"Accept": "application/json, text/event-stream", "MCP-Protocol-Version": "2025-11-25", **headers}
        return self.mcp.post("/mcp", headers=cabeceras, json={
            "jsonrpc": "2.0", "id": 1, "method": metodo, "params": params or {},
        })

    def llamar(self, herramienta, argumentos=None, error=False):
        respuesta = self.rpc("tools/call", {"name": herramienta, "arguments": argumentos or {}})
        self.assertEqual(respuesta.status_code, 200, respuesta.text)
        datos = respuesta.json()["result"]
        self.assertEqual(datos.get("isError", False), error, datos)
        return datos["content"][0]["text"] if error else datos["structuredContent"]

    def pedido(self, **campos):
        return {"solicitud": str(uuid4()), "propuestas": [{"texto": "Subsidiar el transporte público."}],
                "publicar_en_historial": True, "filtros": {"tamano": 3, "elegidos": {"region": [13]}},
                **campos}

    @staticmethod
    def acceso(corrida):
        return {k: corrida[k] for k in ("id", "acceso")}

    def esperar_lote(self, corrida):
        hasta = time.monotonic() + 6
        while time.monotonic() < hasta:
            lotes = self.llamar("trabajo", self.acceso(corrida))["lotes"]
            if lotes:
                return lotes[0]
            time.sleep(0.02)
        self.fail("No apareció un lote")

    def resolver(self, corrida, puntaje=6):
        args = self.acceso(corrida)
        entregas = []
        hasta = time.monotonic() + 8
        while time.monotonic() < hasta:
            avance = self.llamar("trabajo", {**args, "entregas": entregas})
            if avance["estado"] not in ("en_curso", "guardando"):
                return avance
            entregas = []
            for lote in avance["lotes"]:
                self.assertNotIn("sistema", lote)
                self.assertNotIn("system", lote)
                entrada = lote["entrada"]
                tipo = lote["tipo"]
                self.assertNotIn("Escribe una versión mejorada", str(entrada))
                if tipo == "redaccion":
                    salida = {"titulo": "Mejora", "texto": "Extender el subsidio rural", "cambio": "Incluye zonas rurales"}
                else:
                    personas = entrada["personas"]
                    for persona in personas:
                        self.assertLessEqual(set(persona), {"i", "rasgos", "notas"})
                    if tipo == "voces":
                        salida = {"r": [{"i": p["i"], "f": "Me sirve porque viajo a diario."} for p in personas]}
                    else:
                        self.assertEqual(len(entrada["encuesta"]), len(web.metodo.PREGUNTAS))
                        salida = {"r": [{"i": p["i"], "p": [puntaje] * len(entrada["encuesta"])} for p in personas]}
                entregas.append({"lote": lote["lote"], "salida": salida})
            if not entregas:
                time.sleep(0.02)
        self.fail("La corrida no terminó")

    def test_protocolo_sin_clave_y_validacion(self):
        inicio = self.rpc("initialize", {"protocolVersion": "2025-11-25", "capabilities": {},
                                         "clientInfo": {"name": "test", "version": "1"}})
        self.assertEqual(inicio.json()["result"]["serverInfo"]["name"], "What If Chile")
        herramientas = self.rpc("tools/list").json()["result"]["tools"]
        self.assertEqual({t["name"] for t in herramientas}, {"estado", "simular", "trabajo", "consultar", "cancelar"})
        self.assertNotIn("Anthropic-Key", json.dumps(herramientas))
        self.assertEqual(self.llamar("estado")["inferencia"], "cliente")
        self.assertEqual(self.rpc("tools/list", Origin="https://otro.example").status_code, 403)
        self.assertEqual(self.rpc("tools/list", Host="otro.example").status_code, 421)
        for pedido in (
            self.pedido(publicar_en_historial=False),
            self.pedido(propuestas=[{"texto": "  "}]),
            self.pedido(filtros={"tamano": 0}),
            self.pedido(filtros={"edadMin": 40, "edadMax": 20}),
            self.pedido(filtros={"elegidos": {"inventado": [1]}}),
            self.pedido(propuestas=[{"texto": "ley"}] * 8, iteraciones=1),
        ):
            self.llamar("simular", pedido, error=True)

    def test_corrida_iteraciones_historial_y_reproduccion_en_web_local(self):
        pedir_web = self.iniciar_web()
        pedido = self.pedido(iteraciones=1, propuestas=[
            {"texto": "Subsidiar el transporte público."},
            {"documento": {"nombre": "/ruta/ley.txt", "titulo": "Ley propuesta", "texto": "Plan de ciclovías."}},
        ])
        corrida = self.llamar("simular", pedido)
        resultado = self.resolver(corrida)
        self.assertEqual(resultado["estado"], "completa")
        self.assertTrue(resultado["visible_en_web"])
        self.assertEqual([c["respondidas"] for c in resultado["casos"]], [3, 3, 3])
        self.assertEqual(resultado["casos"][1]["documento"], "ley.txt")
        self.assertTrue(resultado["casos"][2]["iteracion"])
        self.assertEqual(resultado["casos"][0]["resultados_encuesta"][0]["conteos_notas_1_a_7"], [0, 0, 0, 0, 0, 3, 0])
        self.assertEqual(self.llamar("simular", pedido), corrida)
        self.assertIn("otros parámetros", self.llamar("simular", {**pedido, "iteraciones": 0}, error=True))

        lista = pedir_web("historial")["corridas"]
        self.assertEqual([(e["id"], e["vista"]) for e in lista], [(corrida["id"], True)])
        vista = pedir_web(f'historial/{corrida["id"]}')
        self.assertEqual(vista["filtros"]["elegidos"], {"region": [13]})
        self.assertTrue(all(a["region"] == 13 for a in vista["muestra"]["agentes"]))
        self.assertTrue({"inicio", "respuestas", "voces", "caso", "fin"} <= {t for t, _ in vista["eventos"]})

    def test_servicio_aislado_guarda_y_no_escribe_en_web(self):
        aislado = RuntimeAislado(self.carpeta / "mcp")
        self.conectar(aislado)
        corrida = self.llamar("simular", self.pedido())
        resultado = self.resolver(corrida, puntaje=3)
        self.assertEqual(resultado["casos"][0]["contra"], 3)
        self.assertTrue(resultado["en_historial"])
        self.assertFalse(resultado["visible_en_web"])
        self.assertEqual(self.historial.ultimas(), [])
        self.assertEqual(web.CORRIDAS, {})
        persistida = gzip.decompress(aislado.HISTORIAL.vista(corrida["id"])).decode()
        self.assertNotIn(corrida["acceso"], persistida)
        self.assertIn("resultados declarados", resultado["modelo"])
        aislado.HISTORIAL = Historial(self.carpeta / "mcp")
        aislado.CORRIDAS.clear()
        self.assertEqual(self.llamar("consultar", self.acceso(corrida)),
                         {k: v for k, v in resultado.items() if k not in {"lotes", "recibidos"}})

    def test_validacion_entregas_reintento_y_cancelacion(self):
        primera = self.llamar("simular", self.pedido())
        segunda = self.llamar("simular", self.pedido())
        lote = self.esperar_lote(primera)
        self.llamar("trabajo", {"id": segunda["id"], "acceso": primera["acceso"]}, error=True)
        entrega = {"lote": lote["lote"], "salida": {"r": [{"i": 0, "p": [9]}]}}
        self.llamar("trabajo", {**self.acceso(primera), "entregas": [entrega]}, error=True)
        self.assertEqual(self.esperar_lote(primera)["lote"], lote["lote"])
        entrega["salida"] = {"r": [{"i": p["i"], "p": [6] * len(web.metodo.PREGUNTAS)}
                                   for p in lote["entrada"]["personas"]]}
        for _ in range(2):
            respuesta = self.llamar("trabajo", {**self.acceso(primera), "entregas": [entrega]})
            self.assertEqual(respuesta["recibidos"], [lote["lote"]])
        self.assertEqual(self.llamar("cancelar", self.acceso(segunda))["estado"], "cancelando")
        self.assertEqual(self.resolver(primera)["estado"], "completa")
        self.assertEqual(self.resolver(segunda)["estado"], "cancelada")

    def test_limite_compartido_en_web_local(self):
        with patch.object(web.limites, "CORRIDAS_A_LA_VEZ", 0):
            self.assertIn("muchas simulaciones", self.llamar("simular", self.pedido(), error=True))
        self.assertEqual(web.CORRIDAS, {})

    def test_inactividad_libera_una_corrida(self):
        with patch("whatif_mcp.motor.INACTIVIDAD", 0.01):
            corrida = self.llamar("simular", self.pedido())
            time.sleep(0.025)
            self.assertEqual(self.resolver(corrida)["estado"], "cancelada")
