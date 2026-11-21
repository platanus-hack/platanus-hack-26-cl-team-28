#!/usr/bin/env python3
"""Prepara y reúne lotes de la encuesta para contestarla con subagentes (por ejemplo, Claude Haiku).

Uso:
    uv run python -I scripts/lotes_agentes.py preparar PERSONAS POLITICA CARPETA [opciones]
    uv run python -I scripts/lotes_agentes.py reunir CARPETA RESULTADOS --modelo "claude-haiku-5-5 (subagentes, 8x100)"

"preparar" reparte a las personas en lotes y escribe, por cada política (un archivo, o cada
.md de una carpeta) y cada lote, un archivo con las instrucciones, la política, las preguntas
y los perfiles. Cada subagente lee un archivo y escribe sus respuestas en el que se le indica.
CARPETA/lotes.json lista los pares de entrada y salida.

Los lotes se arman al azar con una semilla fija y son los mismos para todas las variantes:
así un lote no coincide con una región y la diferencia entre variantes se mide dentro del
mismo grupo de personas.

"reunir" lee las respuestas, revisa que estén todas y bien formadas, y escribe un archivo de
resultados con el formato de scripts/probar_modelo.py, listo para scripts/comparar_variantes.py.

A diferencia del modelo local, aquí un mismo contexto contesta por muchas personas seguidas:
las respuestas de un lote no son independientes entre sí, y no hay probabilidades (logprobs).
Un subagente es más severo o más generoso que otro, y esa diferencia es del tamaño de la que
hay entre variantes. Con --juntas, cada subagente contesta todas las variantes para sus mismas
personas: su sesgo se cancela en la diferencia, a cambio de que ve las variantes lado a lado.
El orden en que se le presentan rota de un lote a otro.

Aquí no va la pregunta de control de probar_modelo.py: en estos modelos la primera respuesta
sí depende del perfil.

Opciones de preparar:
    --tamano N           personas por lote (por defecto 100)
    --semilla S          semilla del reparto en lotes (por defecto 1)
    --redaccion N        redacción de las instrucciones, como en probar_modelo.py
    --etiqueta TEXTO     agrega quién propone la política, por ejemplo "del Gobierno"
    --juntas             POLITICA es una carpeta y cada lote trae todas sus variantes
    --alternativas RUTA  en vez de la encuesta, una pregunta de alternativas (JSON). En la
                         mitad de los lotes las alternativas van en orden inverso
"""

import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import probar_modelo as encuesta  # noqa: E402
from probar_modelo import REDACCIONES, cargar_politicas  # noqa: E402

VARIAS = (
    "Vas a contestar la misma encuesta {n} veces, cada vez en el lugar de una persona distinta. "
    "Contesta a cada persona por separado, después de leer su perfil completo. No uses una regla fija "
    "ni un programa para generar las respuestas, y no ajustes una respuesta para que se parezca o se "
    "diferencie de las anteriores: lo que importa es lo que contestaría esa persona."
)
ESCALA = encuesta.ESCALA


VERSIONES = (
    "Hay {m} versiones de la misma propuesta, descritas abajo. Para cada persona, contesta la encuesta "
    "una vez por cada versión, pensando solo en esa versión, como si fuera la única propuesta en discusión."
)


def texto_juntas(variantes, personas, salida, args):
    """Un lote con todas las variantes: cada persona contesta la encuesta una vez por versión."""
    partes = [f"# Instrucciones\n\n{REDACCIONES[args.redaccion]}\n\n{VARIAS.format(n=len(personas))}\n\n{VERSIONES.format(m=len(variantes))}"]
    cola = f"\n\nEsta política es una propuesta {args.etiqueta}." if args.etiqueta else ""
    versiones = "\n\n".join(f"## Versión {nombre}\n\n{texto.strip()}{cola}" for nombre, texto in variantes)
    partes.append(f"# Tema de la encuesta, en varias versiones\n\n{versiones}")
    preguntas = encuesta.lineas_preguntas(encuesta.PREGUNTAS, encuesta.ESCALAS)
    partes.append(f"# Preguntas\n\n{ESCALA}\n\n{preguntas}")
    ejemplo = '{"id": "m123", "v": "' + variantes[0][0] + '", "r": [' + ", ".join(encuesta.CLAVES) + "]}"
    orden = ", ".join(nombre for nombre, _ in variantes)
    partes.append(
        "# Formato de la respuesta\n\n"
        f"Escribe el archivo `{salida}` con una línea por persona y versión, y nada más: las personas en el orden en que "
        f"aparecen abajo y, para cada persona, las versiones en este orden: {orden}. Cada línea es un JSON como `{ejemplo}`: "
        f"`id` es el identificador de la persona, `v` es la versión y `r` son sus {len(encuesta.CLAVES)} respuestas a esa versión, "
        f"enteros de 1 a 7 en el orden de las preguntas. Deben quedar exactamente {len(personas) * len(variantes)} líneas."
    )
    perfiles = "\n\n".join(f"## {p['id']}\n\n{encuesta.prosa_de(p)}" for p in personas)
    partes.append(f"# Personas\n\n{perfiles}")
    return "\n\n".join(partes) + "\n"


def texto_lote(politica, personas, salida, args, alternativas):
    partes = [f"# Instrucciones\n\n{REDACCIONES[args.redaccion]}\n\n{VARIAS.format(n=len(personas))}"]
    texto = politica.strip()
    if args.etiqueta:
        texto += f"\n\nEsta política es una propuesta {args.etiqueta}."
    partes.append(f"# Tema de la encuesta\n\n{texto}")
    if alternativas:
        opciones = "\n".join(f"{i}. {t}" for i, (_, t) in enumerate(alternativas["orden"], start=1))
        partes.append(f"# Pregunta\n\n{alternativas['pregunta']}\n{opciones}")
        ejemplo = '{"id": "m123", "r": 1}'
        valor = "el número de la alternativa que elige esa persona"
    else:
        preguntas = encuesta.lineas_preguntas(encuesta.PREGUNTAS, encuesta.ESCALAS)
        partes.append(f"# Preguntas\n\n{ESCALA}\n\n{preguntas}")
        ejemplo = '{"id": "m123", "r": [' + ", ".join(encuesta.CLAVES) + "]}"
        valor = f"sus {len(encuesta.CLAVES)} respuestas, enteros de 1 a 7 en el orden de las preguntas"
    partes.append(
        "# Formato de la respuesta\n\n"
        f"Escribe el archivo `{salida}` con una línea por persona, en el mismo orden en que aparecen abajo, "
        f"y nada más. Cada línea es un JSON como `{ejemplo}`: `id` es el identificador de la persona y `r` es {valor}. "
        f"Deben quedar exactamente {len(personas)} líneas."
    )
    perfiles = "\n\n".join(f"## {p['id']}\n\n{encuesta.prosa_de(p)}" for p in personas)
    partes.append(f"# Personas\n\n{perfiles}")
    return "\n\n".join(partes) + "\n"


def preparar(args):
    with open(args.personas, encoding="utf-8") as f:
        personas = [json.loads(linea) for linea in f if linea.strip()]
    random.Random(args.semilla).shuffle(personas)
    lotes = [personas[i : i + args.tamano] for i in range(0, len(personas), args.tamano)]
    pregunta = json.loads(args.alternativas.read_text(encoding="utf-8")) if args.alternativas else None
    manifiesto = []
    politicas = cargar_politicas(args.politica)
    if args.juntas:
        if politicas[0][0] is None:
            sys.exit("--juntas necesita una carpeta con una variante por archivo .md")
        carpeta = args.carpeta / "juntas"
        carpeta.mkdir(parents=True, exist_ok=True)
        for k, lote in enumerate(lotes, start=1):
            # El orden de presentación rota: cada variante va primera en la misma cantidad de lotes.
            giro = (k - 1) % len(politicas)
            variantes = politicas[giro:] + politicas[:giro]
            entrada, salida = carpeta / f"lote_{k:02d}.md", carpeta / f"lote_{k:02d}.jsonl"
            entrada.write_text(texto_juntas(variantes, lote, salida.resolve(), args), encoding="utf-8")
            manifiesto.append({
                "condicion": "juntas", "variante": None, "variantes": [nombre for nombre, _ in variantes], "lote": k,
                "entrada": str(entrada.resolve()), "salida": str(salida.resolve()), "ids": [p["id"] for p in lote],
                "alternativas": None, "redaccion": args.redaccion, "etiqueta": args.etiqueta,
            })
        politicas = []
    for variante, politica in politicas:
        condicion = variante or (args.alternativas.stem if pregunta else args.politica.stem)
        carpeta = args.carpeta / condicion
        carpeta.mkdir(parents=True, exist_ok=True)
        for k, lote in enumerate(lotes, start=1):
            alternativas = None
            if pregunta:
                # En los lotes pares las alternativas van al revés, para que no gane la que va primero.
                orden = list(pregunta["alternativas"].items())
                alternativas = {"pregunta": pregunta["pregunta"], "orden": orden[::-1] if k % 2 == 0 else orden}
            entrada, salida = carpeta / f"lote_{k:02d}.md", carpeta / f"lote_{k:02d}.jsonl"
            entrada.write_text(texto_lote(politica, lote, salida.resolve(), args, alternativas), encoding="utf-8")
            manifiesto.append({
                "condicion": condicion,
                "variante": variante,
                "lote": k,
                "entrada": str(entrada.resolve()),
                "salida": str(salida.resolve()),
                "ids": [p["id"] for p in lote],
                "alternativas": [clave for clave, _ in alternativas["orden"]] if alternativas else None,
                "redaccion": args.redaccion,
                "etiqueta": args.etiqueta,
            })
    ruta = args.carpeta / "lotes.json"
    previos = json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else []
    nuevas = {m["condicion"] for m in manifiesto}
    ruta.write_text(json.dumps([m for m in previos if m["condicion"] not in nuevas] + manifiesto, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(manifiesto)} lotes de hasta {args.tamano} personas en {args.carpeta} ({', '.join(sorted(nuevas))})")


def leer_lote(lote):
    """(respuestas válidas, problemas) de un archivo de respuestas.

    Las respuestas van por id de persona o, si el lote trae varias variantes, por (id, variante)."""
    ruta, problemas, vistos = Path(lote["salida"]), [], {}
    variantes = lote.get("variantes")
    esperadas = [(i, v) for i in lote["ids"] for v in variantes] if variantes else lote["ids"]
    if not ruta.exists():
        return {}, ["no existe el archivo de respuestas"]
    for n, linea in enumerate(ruta.read_text(encoding="utf-8").splitlines(), start=1):
        linea = linea.strip().strip("`")
        if not linea or not linea.startswith("{"):
            continue
        try:
            dato = json.loads(linea)
            r = dato["r"]
            if lote["alternativas"]:
                bien = type(r) is int and 1 <= r <= len(lote["alternativas"])
            else:
                bien = len(r) == len(encuesta.CLAVES) and all(type(v) is int and 1 <= v <= 7 for v in r)
        except (ValueError, KeyError, TypeError):
            bien = False
        llave = (dato.get("id"), dato.get("v")) if variantes and bien else dato.get("id") if bien else None
        if not bien:
            problemas.append(f"línea {n} mal formada")
        elif llave not in esperadas:
            problemas.append(f"línea {n}: {llave} no es de este lote")
        elif llave in vistos:
            problemas.append(f"línea {n}: {llave} repetido")
        else:
            vistos[llave] = r
    faltan = [i for i in esperadas if i not in vistos]
    if faltan:
        problemas.append(f"faltan {len(faltan)} respuestas")
    return vistos, problemas


def reunir(args):
    lotes = json.loads((args.carpeta / "lotes.json").read_text(encoding="utf-8"))
    if args.condicion:
        lotes = [m for m in lotes if m["condicion"] in args.condicion]
    escritos, con_problemas = 0, 0
    with open(args.resultados, "w", encoding="utf-8") as f:
        for lote in lotes:
            respuestas, problemas = leer_lote(lote)
            if problemas:
                con_problemas += 1
                print(f"  {lote['condicion']} lote {lote['lote']}: {'; '.join(problemas[:4])}")
            variantes = lote.get("variantes")
            for llave in [(i, v) for i in lote["ids"] for v in sorted(variantes)] if variantes else lote["ids"]:
                if llave not in respuestas:
                    continue
                r = respuestas[llave]
                id_persona, variante = llave if variantes else (llave, lote["variante"])
                registro = {"modelo": args.modelo, "perfil": "prosa", "redaccion": lote["redaccion"], "lote": lote["lote"], "id": id_persona, "valida": True}
                if variante:
                    registro["variante"] = variante
                if variantes:
                    registro["lugar"] = variantes.index(variante) + 1
                if lote["etiqueta"]:
                    registro["etiqueta"] = lote["etiqueta"]
                if not variante:
                    registro["pregunta" if lote["alternativas"] else "politica"] = lote["condicion"]
                if lote["alternativas"]:
                    registro["eleccion"] = lote["alternativas"][r - 1]
                else:
                    registro["respuestas"] = dict(zip(encuesta.CLAVES, r))
                f.write(json.dumps(registro, ensure_ascii=False) + "\n")
                escritos += 1
    esperados = sum(len(m["ids"]) * len(m.get("variantes") or [1]) for m in lotes)
    print(f"{escritos} de {esperados} respuestas en {args.resultados}; lotes con problemas: {con_problemas} de {len(lotes)}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="orden", required=True)
    p = sub.add_parser("preparar")
    p.add_argument("personas", type=Path)
    p.add_argument("politica", type=Path)
    p.add_argument("carpeta", type=Path)
    p.add_argument("--tamano", type=int, default=100)
    p.add_argument("--semilla", type=int, default=1)
    p.add_argument("--redaccion", type=int, choices=sorted(REDACCIONES), default=1)
    p.add_argument("--etiqueta")
    p.add_argument("--juntas", action="store_true")
    p.add_argument("--alternativas", type=Path)
    r = sub.add_parser("reunir")
    r.add_argument("carpeta", type=Path)
    r.add_argument("resultados", type=Path)
    r.add_argument("--modelo", required=True)
    r.add_argument("--condicion", action="append")
    args = ap.parse_args()
    preparar(args) if args.orden == "preparar" else reunir(args)


if __name__ == "__main__":
    main()
