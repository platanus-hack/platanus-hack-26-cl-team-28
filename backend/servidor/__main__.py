"""Servidor HTTP del simulador. Solo biblioteca estándar (la API de Anthropic es opcional).

    cd backend && python3 -m servidor            # puerto 8787
    MOTOR=grabado python3 -m servidor            # sin red: repite una corrida real guardada

Rutas:
    GET  /api/estado                  motor, modelo y cuántos agentes hay
    GET  /api/agentes                 perfil y ubicación de cada agente
    POST /api/documentos              cuerpo: el archivo; cabecera X-Nombre. Devuelve texto o resumen
    POST /api/corridas                {casos:[{id,letra,texto,documento?}], agentes:[i], iteraciones}
    GET  /api/corridas/<id>/eventos   eventos de la corrida (text/event-stream)
    POST /api/corridas/<id>/cancelar
"""

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse

from .agentes import cargar_agentes
from .corridas import Cache, Caso, Corrida, resumir_documento
from .documentos import DocumentoIlegible, extraer_texto
from .metodo import PREGUNTAS
from .motor import elegir_motor

LETRAS = "ABCDEFGH"
MAXIMO_DOCUMENTO = 25 * 1024 * 1024
LOTE = int(os.environ.get("LOTE", "10"))
CONCURRENCIA = int(os.environ.get("CONCURRENCIA", "30"))
MAXIMO_ITERACIONES = 3

AGENTES = cargar_agentes()
MOTOR = elegir_motor(AGENTES)
CACHE = Cache()
CORRIDAS: dict[str, Corrida] = {}
AGENTES_PUBLICOS = json.dumps([a.publico() for a in AGENTES], ensure_ascii=False).encode()


class Manejador(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "ph26"

    def log_message(self, formato, *args):  # silencio salvo errores
        if args and str(args[1]).startswith(("4", "5")):
            super().log_message(formato, *args)

    def _json(self, codigo: int, datos, crudo: bytes | None = None) -> None:
        cuerpo = crudo if crudo is not None else json.dumps(datos, ensure_ascii=False).encode()
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(cuerpo)

    def _cuerpo(self) -> bytes:
        largo = int(self.headers.get("Content-Length") or 0)
        if largo > MAXIMO_DOCUMENTO:
            raise ValueError("El archivo pesa más de 25 MB")
        return self.rfile.read(largo)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Nombre")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        ruta = urlparse(self.path).path
        if ruta == "/api/estado":
            return self._json(200, {"motor": MOTOR.describir(), "agentes": len(AGENTES), "lote": LOTE, "concurrencia": CONCURRENCIA, "preguntas": PREGUNTAS})
        if ruta == "/api/agentes":
            return self._json(200, None, AGENTES_PUBLICOS)
        partes = ruta.strip("/").split("/")
        if len(partes) == 4 and partes[:2] == ["api", "corridas"] and partes[3] == "eventos":
            return self._eventos(partes[2])
        self._json(404, {"error": "No existe"})

    def do_POST(self):
        ruta = urlparse(self.path).path
        try:
            if ruta == "/api/documentos":
                return self._documento()
            if ruta == "/api/corridas":
                return self._crear_corrida()
            partes = ruta.strip("/").split("/")
            if len(partes) == 4 and partes[:2] == ["api", "corridas"] and partes[3] == "cancelar":
                corrida = CORRIDAS.get(partes[2])
                if corrida:
                    corrida.cancelada = True
                return self._json(200, {"ok": True})
        except DocumentoIlegible as error:
            return self._json(422, {"error": str(error)})
        except (ValueError, KeyError, TypeError) as error:
            return self._json(400, {"error": str(error)})
        except Exception as error:
            return self._json(500, {"error": f"{type(error).__name__}: {error}"[:300]})
        self._json(404, {"error": "No existe"})

    def _documento(self):
        nombre = unquote(self.headers.get("X-Nombre") or "documento.txt")
        texto = extraer_texto(nombre, self._cuerpo())
        documento, consumo = resumir_documento(MOTOR, nombre, texto)
        self._json(200, {**documento, "llamadas": consumo.llamadas, "costo_usd": round(consumo.costo_usd, 4)})

    def _crear_corrida(self):
        pedido = json.loads(self._cuerpo() or b"{}")
        casos = []
        for k, c in enumerate(pedido.get("casos", [])[: len(LETRAS)]):
            documento = c.get("documento")
            if documento and not documento.get("texto"):
                documento = None
            caso = Caso(id=str(c.get("id", k)), letra=c.get("letra") or LETRAS[k], texto=str(c.get("texto", "")), documento=documento)
            if caso.politica():
                casos.append(caso)
        if not casos:
            raise ValueError("Falta al menos una propuesta con texto")
        indices = pedido.get("agentes")
        elegidos = [AGENTES[i] for i in indices if 0 <= i < len(AGENTES)] if indices else AGENTES
        if not elegidos:
            raise ValueError("La muestra quedó vacía")
        iteraciones = 0 if MOTOR.grabado else max(0, min(MAXIMO_ITERACIONES, int(pedido.get("iteraciones", 0))))
        lote = max(1, min(25, int(pedido.get("lote", LOTE))))
        corrida = Corrida(MOTOR, CACHE, elegidos, casos, iteraciones, lote, CONCURRENCIA, LETRAS)
        CORRIDAS[corrida.id] = corrida
        threading.Thread(target=corrida.correr, daemon=True).start()
        self._json(201, {"id": corrida.id, "motor": MOTOR.describir(), "agentes": len(elegidos)})

    def _eventos(self, identificador: str):
        corrida = CORRIDAS.get(identificador)
        if not corrida:
            return self._json(404, {"error": "No existe esa corrida"})
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()
        visto = int(self.headers.get("Last-Event-ID") or -1) + 1
        try:
            while True:
                nuevos = corrida.esperar(visto)
                if not nuevos:
                    if corrida.terminada:
                        break
                    self.wfile.write(b": sigue\n\n")
                    self.wfile.flush()
                    continue
                for tipo, datos in nuevos:
                    bloque = f"id: {visto}\nevent: {tipo}\ndata: {json.dumps(datos, ensure_ascii=False)}\n\n"
                    self.wfile.write(bloque.encode())
                    visto += 1
                self.wfile.flush()
                if corrida.terminada and visto >= len(corrida.eventos):
                    break
        except (BrokenPipeError, ConnectionResetError):
            pass
        self.close_connection = True


def main():
    puerto = int(os.environ.get("PUERTO", "8787"))
    servidor = ThreadingHTTPServer(("127.0.0.1" if not os.environ.get("ABIERTO") else "0.0.0.0", puerto), Manejador)
    servidor.daemon_threads = True
    descripcion = MOTOR.describir()
    print(f"Simulador en http://127.0.0.1:{puerto} · {len(AGENTES)} agentes · motor {descripcion['nombre']} ({descripcion['modelo']})", flush=True)
    servidor.serve_forever()


if __name__ == "__main__":
    main()
