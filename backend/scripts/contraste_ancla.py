#!/usr/bin/env python3
"""Mini experimentos sobre el ancla nacional: el pronóstico directo de un modelo grande, sin agentes.

Uso: uv run python scripts/contraste_ancla.py NOMBRE --modelo opus [--referencias] [--repeticiones 3] [--casos dev|prueba|todos]
Guarda cada pronóstico en data/pruebas/realidad_1000/experimentos/ancla_NOMBRE.jsonl (una fila por caso y repetición).
"""
import argparse, json, sys, threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ)); sys.path.insert(0, str(RAIZ / "scripts"))
import contraste_experimentos as ex  # noqa: E402
import metodos_banco, validar_banco as vb  # noqa: E402
from servidor import motor  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("nombre"); ap.add_argument("--modelo", default="opus"); ap.add_argument("--referencias", action="store_true")
ap.add_argument("--repeticiones", type=int, default=1); ap.add_argument("--casos", default="dev"); ap.add_argument("--concurrencia", type=int, default=10)
ap.add_argument("--sistema", default="base")
args = ap.parse_args()

SISTEMAS = {
    "base": vb.SISTEMA_PRONOSTICO,
    # Con lo aprendido del contraste: los modelos subestiman los consensos y sobrestiman lo disputado por sector.
    "calibrado": vb.SISTEMA_PRONOSTICO + (
        " Ten presente cómo responde la gente en Chile: la mayoría se interesa poco en política y juzga por conveniencia y sentido común, "
        "así que muchas medidas reúnen apoyos de 80 % o más (o rechazos igual de amplios) en todos los sectores a la vez; no acerques tus "
        "estimaciones a 50 % por prudencia. Lo que divide por mitades es lo que lleva el sello de un gobierno o toca valores en disputa."),
}
casos = ex.elegir_casos(args.casos)
ruta = ex.SALIDA / f"ancla_{args.nombre}.jsonl"
hechos = {}
if ruta.exists():
    for l in ruta.read_text().splitlines():
        f = json.loads(l); hechos[f["caso"]] = hechos.get(f["caso"], 0) + 1
cli = motor.ClaudeCodigo(modelo=args.modelo)
cerrojo = threading.Lock()

def una(par):
    caso, k = par
    tema = metodos_banco.tema_con_referencias(caso) if args.referencias else metodos_banco.tema_del_caso(caso)
    for _ in range(3):
        try:
            datos, _c = cli._llamar(cli._modelo, SISTEMAS[args.sistema], tema, vb.ESQUEMA_PRONOSTICO)
            with cerrojo, open(ruta, "a") as f:
                f.write(json.dumps({"caso": caso["id"], "rep": k, "prob": [int(datos["acuerdo"]), int(datos["desacuerdo"])]}) + "\n")
            return 1
        except Exception as e:
            ultimo = e
    print("fallo", caso["id"], str(ultimo)[:120]); return 0

tareas = [(c, k) for c in casos.values() for k in range(hechos.get(c["id"], 0), args.repeticiones)]
with ThreadPoolExecutor(args.concurrencia) as g:
    print(args.nombre, sum(g.map(una, tareas)), "de", len(tareas))
