#!/usr/bin/env python3
"""Contraste del pipeline del sitio con las encuestas reales: 1.000 agentes, 1 por cada 1.000.

Uso:
    uv run python scripts/contraste_realidad.py correr [--concurrencia 32] [--solo ID,ID]

Cada caso del banco (../datos-pruebas) pasa, uno por uno, por el camino exacto del motor del
sitio: `ClaudeCodigo.responder(texto, lote)` con Haiku, lotes de 20, perfil temático y las cinco
preguntas vigentes. La muestra es la que entrega el sitio con edad mínima 18 y reducción 1.000
(un agente por cada 1.000 personas), tamaño 1.000. No pasa por la caché del servidor.

Guarda en data/pruebas/realidad_1000/: `respuestas.jsonl` (una fila por agente y caso, más una
por llamada) y `personas.jsonl` (atributos y fila de cada agente). Si se corta, sigue donde quedó.
"""

import argparse
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "scripts"))

SALIDA = RAIZ / "data" / "pruebas" / "realidad_1000"
BANCO = RAIZ.parent / "datos-pruebas"
FILTROS = {"edadMin": 18, "reduccion": 1000}
TAMANO = 1000
LOTE = 20

# Casos fuera de los 120 comparables que igual tienen una lectura de acuerdo y desacuerdo.
EXTRA = {
    "servel22-constitucion": ("Apruebo", "Rechazo"),
    "servel23-constitucion": ("A favor", "En contra"),
    "cm26-ciudadania": ("De acuerdo", None),
}


def casos_todos():
    import validar_banco as vb

    casos = vb.cargar_casos()
    for c in casos:
        c["grupo"] = "comparable"
    vistos = {c["id"] for c in casos}
    for archivo in sorted((BANCO / "encuestas").glob("*.jsonl")):
        for linea in archivo.read_text(encoding="utf-8").splitlines():
            if not linea.strip():
                continue
            c = json.loads(linea)
            if c["id"] in EXTRA and c["id"] not in vistos:
                a, d = EXTRA[c["id"]]
                c.update(area=archivo.stem, real_acuerdo=c["respuestas"][a], real_desacuerdo=c["respuestas"].get(d) if d else None,
                         real_neutro=None, parte="extra", grupo="extra")
                casos.append(c)
    # La pregunta del panel de validación que no está en el banco.
    for p in json.loads((BANCO / "panel-validacion-postura.json").read_text(encoding="utf-8")):
        if p["id"] not in vistos and p["id"] not in EXTRA:
            casos.append({"id": p["id"], "familia": p["familia"], "tipo": "acuerdo", "enunciado": p["pregunta"], "fuente_id": p["fuente"],
                          "area": "seguridad-justicia", "real_acuerdo": p["referencia_pct"][0], "real_desacuerdo": p["referencia_pct"][1],
                          "real_neutro": None, "parte": "extra", "grupo": "extra", "respuestas": {}})
    return casos


def agentes():
    from servidor.poblacion import TablaAgentes

    return TablaAgentes().muestra(FILTROS, TAMANO).agentes


def correr(args):
    import metodos_banco
    from servidor import metodo, motor

    casos = casos_todos()
    if args.solo:
        casos = [c for c in casos if c["id"] in args.solo]
    gente = agentes()
    SALIDA.mkdir(parents=True, exist_ok=True)
    (SALIDA / "personas.jsonl").write_text(
        "".join(json.dumps({"agente": a.id, "orden": a.indice, "edad": a.edad, "genero": a.genero, "quintil": a.quintil,
                            "educacion": a.educacion, "politica": a.politica, "region": a.region, "comuna": a.comuna,
                            "grupos": a.atributos, "fila": a.fila}, ensure_ascii=False, default=str) + "\n" for a in gente),
        encoding="utf-8")
    (SALIDA / "casos.json").write_text(json.dumps(casos, ensure_ascii=False, indent=1), encoding="utf-8")
    ruta = SALIDA / "respuestas.jsonl"
    hechos = set()
    if ruta.exists():
        for linea in ruta.read_text(encoding="utf-8").splitlines():
            f = json.loads(linea)
            if "notas" in f:
                hechos.add((f["caso"], f["agente"]))
    cli = motor.ClaudeCodigo()
    cerrojo = threading.Lock()
    salida = open(ruta, "a", encoding="utf-8")
    por_indice = {a.indice: a for a in gente}

    tareas = []
    for caso in casos:
        for k in range(0, len(gente), LOTE):
            faltan = [a for a in gente[k:k + LOTE] if (caso["id"], a.id) not in hechos]
            if faltan:
                tareas.append((caso, k // LOTE, faltan))
    print(f"{len(casos)} casos x {len(gente)} agentes; motor {cli.clave()} perfil {metodo.NIVEL}; faltan {len(tareas)} llamadas", flush=True)

    def una(caso, k, lote):
        texto = metodos_banco.tema_del_caso(caso)
        ultimo = None
        for _ in range(3):
            try:
                inicio = time.perf_counter()
                r = cli.responder(texto, lote)
                filas = [{"caso": caso["id"], "agente": por_indice[x.agente].id, "lote": k, "notas": x.respuestas} for x in r.respuestas]
                filas.append({"caso": caso["id"], "lote": k, "llamada": True, "segundos": round(time.perf_counter() - inicio, 1),
                              "tokens_entrada": r.consumo.tokens_entrada, "tokens_salida": r.consumo.tokens_salida,
                              "costo_usd": r.consumo.costo_usd, "temas": metodo.temas_de(texto)})
                with cerrojo:
                    for f in filas:
                        salida.write(json.dumps(f, ensure_ascii=False) + "\n")
                    salida.flush()
                return len(r.respuestas), len(lote)
            except Exception as e:  # una llamada caída no detiene la corrida
                ultimo = e
        print(f"  fallo {caso['id']} lote {k}: {str(ultimo)[:200]}", flush=True)
        return 0, len(lote)

    inicio = time.perf_counter()
    bien = total = 0
    with ThreadPoolExecutor(max_workers=args.concurrencia) as grupo:
        futuros = [grupo.submit(una, *t) for t in tareas]
        for j, f in enumerate(as_completed(futuros), start=1):
            b, t = f.result()
            bien += b
            total += t
            if j % 50 == 0 or j == len(futuros):
                print(f"  {j}/{len(futuros)} llamadas, {bien}/{total} respuestas, {time.perf_counter() - inicio:.0f} s", flush=True)
    salida.close()


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="orden", required=True)
    c = sub.add_parser("correr")
    c.add_argument("--concurrencia", type=int, default=32)
    c.add_argument("--solo", type=lambda t: set(t.split(",")))
    args = ap.parse_args()
    correr(args)


if __name__ == "__main__":
    main()
