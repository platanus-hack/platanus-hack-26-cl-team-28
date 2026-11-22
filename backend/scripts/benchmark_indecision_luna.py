"""Compara la instrucción sobre la nota 4 de Luna sobre el perfil histórico.

Exploración previa con GPT-6 Luna, una de las configuraciones probadas antes de fijar el
método del sitio (Claude Haiku con ancla de Claude Opus; ver VALIDACION.md)."""
import argparse
import random
from concurrent.futures import ThreadPoolExecutor
from itertools import batched
from pathlib import Path
from tempfile import TemporaryDirectory

from benchmark_asociaciones import guardar, leer
from correr_benchmark_luna import MODELO, inferir, leer_json_respuesta
from servidor import metodo, motor
from servidor.corridas import postura


FRASE = "Una persona que se inclina aunque sea un poco hacia un lado responde 3 o 5, no 4."
BRAZOS = ("con_frase", "sin_frase")
POSTURA_EXPLICITA = "postura_explicita"
FORMATO_POSTURA = (
    "Para la primera pregunta, decide si la persona ya tiene una postura sobre esta política. "
    "Devuelve tiene_postura: true si tiene una postura a favor o en contra, aunque sea moderada. "
    "Devuelve tiene_postura: false si no ha formado una opinión, no sabe qué responder o ninguna "
    "de las dos posturas predomina. Si es true, devuelve apoyo con la nota 1, 2 o 3 para rechazo "
    "y 5, 6 o 7 para apoyo, según la intensidad. Si es false, devuelve apoyo: null. "
    "Contesta las otras cuatro preguntas con enteros del 1 al 7 según sus escalas."
)
LOTE = 25
NOTAS_CON_POSTURA = (1, 2, 3, 5, 6, 7)


def esquema_postura():
    ramas = []
    for tiene, apoyo in (
        (True, {"type": "integer", "enum": list(NOTAS_CON_POSTURA)}),
        (False, {"type": "null"}),
    ):
        campos = {
            "i": {"type": "integer"},
            "p": {"type": "array", "items": {"type": "integer", "enum": list(range(1, 8))}},
            "tiene_postura": {"type": "boolean", "enum": [tiene]},
            "apoyo": apoyo,
        }
        ramas.append({"type": "object", "properties": campos, "required": list(campos), "additionalProperties": False})
    return {
        "type": "object",
        "properties": {"r": {"type": "array", "items": {"anyOf": ramas}}},
        "required": ["r"],
        "additionalProperties": False,
    }


def sistemas(politica, postura_explicita=False):
    # Las preguntas del banco tal cual: el benchmark guardado se corrió con ellas.
    completo = metodo.sistema_del_banco(politica)
    if postura_explicita:
        formato = metodo.banco.FORMATO.format(n=5, claves="r1,r2,r3,r4,r5")
        if formato not in completo:
            raise ValueError("El formato de la encuesta cambió.")
        return {POSTURA_EXPLICITA: completo.replace(formato, FORMATO_POSTURA, 1)}
    if completo.count(FRASE) != 1:
        raise ValueError("El cuestionario debe contener exactamente una vez la frase a evaluar.")
    return dict(zip(BRAZOS, (completo, completo.replace(" " + FRASE, "", 1)), strict=True))


def leer_notas(salida, n):
    datos, uso = leer_json_respuesta(salida)
    filas = datos.get("r") if isinstance(datos, dict) else None
    if not isinstance(filas, list) or len(filas) != n:
        raise ValueError(f"Se esperaban {n} filas.")
    por_id = {}
    for fila in filas:
        if not isinstance(fila, dict):
            raise ValueError("Cada fila debe ser un objeto.")
        i, p = fila.get("i"), fila.get("p")
        if type(i) is not int or not 0 <= i < n or i in por_id or not motor.notas_validas(p, len(metodo.PREGUNTAS)):
            raise ValueError("Índice duplicado o notas de encuesta inválidas.")
        por_id[i] = p
    return [por_id[i] for i in range(n)], uso


def leer_postura_explicita(salida, n):
    datos, uso = leer_json_respuesta(salida)
    filas = datos.get("r") if isinstance(datos, dict) else None
    if not isinstance(filas, list) or len(filas) != n:
        raise ValueError(f"Se esperaban {n} filas de postura.")
    por_id = {}
    for fila in filas:
        if not isinstance(fila, dict):
            raise ValueError("Cada fila debe ser un objeto.")
        i, tiene, apoyo, resto = fila.get("i"), fila.get("tiene_postura"), fila.get("apoyo"), fila.get("p")
        if type(i) is not int or not 0 <= i < n or i in por_id or type(tiene) is not bool:
            raise ValueError("Índice o indicador de postura inválido.")
        if not motor.notas_validas(resto, len(metodo.PREGUNTAS) - 1):
            raise ValueError("Las cuatro notas restantes deben estar entre 1 y 7.")
        apoyo_valido = (type(apoyo) is int and apoyo in NOTAS_CON_POSTURA) if tiene else apoyo is None
        if "apoyo" not in fila or not apoyo_valido:
            raise ValueError("La primera nota debe corresponder al indicador de postura.")
        # Un null validado se normaliza a 4 solo para reutilizar el agregador histórico.
        por_id[i] = [apoyo if tiene else 4, *resto]
    return [por_id[i] for i in range(n)], uso


def preparar_lotes(plan, postura_explicita=False):
    ficha = plan["catalogos"]["1000"]["muestras"]["1000"]
    pesos = dict(zip(ficha["ids"], ficha["peso"], strict=True))
    if len(pesos) != 1000 or any(p <= 0 for p in pesos.values()):
        raise ValueError("Se necesitan los 1.000 medoides históricos y sus pesos positivos.")
    ids = list(pesos)
    random.Random(20261121).shuffle(ids)
    instruccion = motor.instruccion_lote(len(metodo.PREGUNTAS))
    if postura_explicita:
        instruccion = (
            "Vienen varias personas, numeradas. Responde la encuesta por separado como cada una, "
            "sin que una influya en otra. Para cada persona devuelve i (su número), tiene_postura "
            "(booleano sobre la primera pregunta), apoyo (nota de la primera pregunta, o null si "
            "tiene_postura es false) y p (las cuatro notas de las preguntas 2 a 5, en orden)."
        )
    lotes = []
    for grupo in batched(ids, LOTE):
        perfiles = "\n\n".join(f"## Persona {i}\n\n{ficha['perfil'][id_]}" for i, id_ in enumerate(grupo))
        solicitud = f"{instruccion}\n\n{perfiles}\n\nDevuelve solo el objeto JSON con la clave r."
        lotes.append((list(grupo), solicitud))
    return pesos, lotes


def ejecutar(casos, lotes, salida, concurrencia, intentos, postura_explicita=False):
    variantes = {c["id"]: sistemas(c["pregunta"], postura_explicita) for c in casos}
    interpretar = leer_postura_explicita if postura_explicita else leer_notas
    tareas = []
    for indice, (ids, solicitud) in enumerate(lotes, 1):
        for caso, instrucciones in variantes.items():
            for brazo, sistema in instrucciones.items():
                carpeta = salida / caso / brazo
                carpeta.mkdir(parents=True, exist_ok=True)
                tareas.append((indice, caso, brazo, carpeta, ids, f"{sistema}\n\n{solicitud}"))

    def responder(tarea):
        indice, caso, brazo, carpeta, ids, prompt = tarea
        try:
            datos, cache = inferir(
                ids, prompt, carpeta, trabajo, intentos, interpretar=interpretar, esquema_salida=esquema,
            )
        except RuntimeError as error:
            print(f"{caso} {brazo} lote {indice}: {error}", flush=True)
            return False
        print(f"{caso} {brazo} lote {indice}/{len(lotes)} · {datos['segundos']:.1f} s · {'caché' if cache else 'nuevo'}", flush=True)
        return True

    with TemporaryDirectory(prefix="luna-indecision-") as trabajo, ThreadPoolExecutor(max_workers=concurrencia) as pool:
        esquema = None
        if postura_explicita:
            esquema = Path(trabajo) / "esquema.json"
            guardar(esquema, esquema_postura())
        completados = sum(pool.map(responder, tareas))
    return completados == len(tareas)


def resumir(casos, pesos, salida, brazos=BRAZOS):
    resultados = {}
    masa = sum(pesos.values())
    for caso in casos:
        id_ = caso["id"]
        resultados[id_] = {}
        for brazo in brazos:
            respuestas = {}
            for archivo in (salida / id_ / brazo).glob("*.json"):
                lote = leer(archivo)
                for k, notas in zip(lote["ids"], lote["r"], strict=True):
                    if k in respuestas or not motor.notas_validas(notas, len(metodo.PREGUNTAS)):
                        raise ValueError(f"Respuesta repetida o inválida en {archivo}")
                    respuestas[k] = postura(notas[0])
            fila = {"validas": len(respuestas)}
            if respuestas.keys() == pesos.keys():
                fila["pct"] = [
                    100 * sum(peso for k, peso in pesos.items() if respuestas[k] == postura_) / masa
                    for postura_ in ("favor", "contra", "indecisa")
                ]
            resultados[id_][brazo] = fila
    guardar(salida / "resumen.json", resultados)
    return all("pct" in fila for brazos_caso in resultados.values() for fila in brazos_caso.values())


def identidad_diseno(diseno):
    return {
        "modelo": diseno["modelo"],
        "lote": diseno["lote"],
        "pesos": diseno["pesos"],
        "preguntas": diseno["preguntas"],
        "frase": diseno["frase"],
        "formato_postura": diseno.get("formato_postura"),
        "brazos": tuple(diseno.get("brazos", BRAZOS)),
        "casos": {c["id"]: c["pregunta"] for c in diseno["casos"]},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--panel", type=Path, default=Path("datos-pruebas/panel-cadem-perfil-base.json"))
    parser.add_argument("--salida", type=Path, required=True)
    parser.add_argument("--casos", nargs="+", required=True)
    parser.add_argument("--concurrencia", type=int, default=12)
    parser.add_argument("--intentos", type=int, default=3)
    parser.add_argument("--postura-explicita", action="store_true")
    parser.add_argument("--solo-resumen", action="store_true", help="Lee los lotes locales sin hacer inferencia.")
    args = parser.parse_args()
    if min(args.concurrencia, args.intentos) < 1 or len(set(args.casos)) != len(args.casos):
        parser.error("Concurrencia e intentos deben ser positivos y los casos deben ser únicos.")
    panel = {c["id"]: c for c in leer(args.panel)}
    casos = [panel[k] for k in args.casos]
    pesos, lotes = preparar_lotes(leer(args.plan), args.postura_explicita)
    brazos = (POSTURA_EXPLICITA,) if args.postura_explicita else BRAZOS
    diseno = {
        "modelo": MODELO, "frase": FRASE, "casos": casos, "pesos": pesos,
        "lote": LOTE, "preguntas": metodo.PREGUNTAS,
        "brazos": brazos,
        "formato_postura": FORMATO_POSTURA if args.postura_explicita else None,
    }
    archivo_diseno = args.salida / "diseno.json"
    if archivo_diseno.exists():
        if identidad_diseno(diseno) != identidad_diseno(leer(archivo_diseno)):
            parser.error("La salida tiene otro diseño. Usa un directorio distinto.")
    elif args.solo_resumen:
        parser.error("No hay un diseño guardado en ese directorio.")
    else:
        guardar(archivo_diseno, diseno)
    completas = args.solo_resumen or ejecutar(
        casos, lotes, args.salida, args.concurrencia, args.intentos, args.postura_explicita,
    )
    cobertura_completa = resumir(casos, pesos, args.salida, brazos)
    if not completas or not cobertura_completa:
        raise SystemExit("Hay lotes pendientes. Ejecuta el benchmark para completar la cobertura.")


if __name__ == "__main__":
    main()
