"""Prueba de humo del contenedor. Solo biblioteca estándar y ninguna inferencia."""

import json
import sys
import time
from urllib.error import URLError
from urllib.request import Request, urlopen


def comprobar(base: str):
    for _ in range(30):
        try:
            with urlopen(base + "/healthz", timeout=2) as respuesta:
                assert json.load(respuesta) == {"estado": "ok", "inferencia": "cliente", "web_local": False}
                break
        except (URLError, TimeoutError):
            time.sleep(1)
    else:
        raise RuntimeError("El servicio MCP aislado no respondió")

    pedido = Request(base + "/mcp", json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": "estado", "arguments": {}},
    }).encode(), {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": "2025-11-25",
    })
    with urlopen(pedido, timeout=8) as respuesta:
        estado = json.load(respuesta)["result"]["structuredContent"]
    assert estado["inferencia"] == "cliente"
    assert estado["historial_visible_en_web"] is False
    assert estado["poblacion"]["agentes"] > 0


if __name__ == "__main__":
    comprobar(sys.argv[1])
