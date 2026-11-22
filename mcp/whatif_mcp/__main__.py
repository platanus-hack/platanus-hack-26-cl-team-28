"""Arranca el MCP aislado. La opción --con-web sirve para probar el historial en local."""

import argparse
import os
import sys
import threading
from pathlib import Path

import uvicorn
from starlette.responses import JSONResponse


def main():
    argumentos = argparse.ArgumentParser()
    argumentos.add_argument("--con-web", action="store_true", help="Arranca también una API web local para pruebas")
    opciones = argumentos.parse_args()
    raiz = Path(__file__).resolve().parents[2]
    sys.path.insert(0, os.environ.get("WHATIF_BACKEND", str(raiz / "backend")))

    from .protocolo import crear_mcp
    from .runtime import RuntimeAislado
    from .servicio import Servicio

    api = None
    enlace = os.environ.get("WHATIF_MCP_BIND", "127.0.0.1")
    if opciones.con_web:
        if enlace != "127.0.0.1":
            argumentos.error("--con-web solo admite MCP en loopback")
        from servidor import __main__ as web

        runtime = web
        api = web.Servidor(("127.0.0.1", int(os.environ.get("PUERTO", "8787"))), web.Manejador)
        hilo = threading.Thread(target=api.serve_forever, daemon=True)
        hilo.start()
    else:
        runtime = RuntimeAislado.desde_entorno()

    mcp = crear_mcp(Servicio(runtime))

    @mcp.custom_route("/healthz", methods=["GET"])
    async def salud(_):
        return JSONResponse({"estado": "ok", "inferencia": "cliente", "web_local": opciones.con_web})

    try:
        uvicorn.run(
            mcp.streamable_http_app(),
            host=enlace,
            port=int(os.environ.get("WHATIF_MCP_PORT", "8788")),
            workers=1,
            access_log=False,
            forwarded_allow_ips=os.environ.get("WHATIF_MCP_PROXY", "127.0.0.1"),
            limit_concurrency=100,
        )
    finally:
        if api is not None:
            api.shutdown()
            api.server_close()
            hilo.join()


if __name__ == "__main__":
    main()
