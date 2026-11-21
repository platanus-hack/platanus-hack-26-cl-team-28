"""Formas de preguntar que se comparan en scripts/validar_banco.py.

Cada método dice qué lee el modelo: las instrucciones, cómo se presenta el caso, las preguntas,
cuánto del perfil y la instrucción del lote. `sitio` no define nada: es lo que hace hoy el
motor (servidor/metodo.py y servidor/motor.py), y `armar` lo comprueba contra esas funciones.

Lo que se cambie aquí tiene que poder llevarse al motor: instrucciones (REDACCIONES en
probar_modelo.py), preguntas de la encuesta, nivel del perfil o instrucción del lote.
"""

import filtro_perfil as filtro
import probar_modelo as banco

from servidor import metodo, motor


def tema_del_caso(caso):
    """El caso como lo escribiría alguien en el sitio: la medida y, si lo hay, su encuadre."""
    texto = caso["enunciado"].strip()
    if caso.get("contexto"):
        texto += f"\n\nContexto: {caso['contexto'].strip()}"
    return texto


def pregunta_directa(caso):
    return ["¿Estás de acuerdo o en desacuerdo con esto?"]


# Dos cosas que el método del sitio hace distinto de una persona encuestada: se queda al medio
# (cerca de 20 % de notas 4, contra 3 a 6 % de «no sabe» en Cadem) y contesta por posición
# política lo que la gente contesta por conveniencia y sentido común.
ENCUESTADO = (
    "Vas a contestar una encuesta poniéndote en el lugar de una persona real que vive en Chile. "
    "Responde como lo haría esa persona según su perfil (su situación, sus intereses y su forma "
    "de pensar), no como un asistente ni como un experto neutral.\n\n"
    "Cómo contesta la gente una encuesta:\n"
    "- Toma posición. Aunque no conozca el detalle, casi nadie se queda al medio: responde con su "
    "primera impresión. El 4 es solo para quien de verdad no tiene opinión, y son pocos.\n"
    "- Frente a una medida concreta pesa primero si le sirve o le perjudica a ella y a los suyos, y "
    "si le parece de sentido común. Lo que entrega un beneficio claro o pone orden suele gustar a "
    "gente de todos los sectores políticos, y lo que quita algo o cuesta plata suele disgustar a todos.\n"
    "- La posición política pesa en los temas que dividen por valores o cuando la medida lleva el "
    "sello de un gobierno o de un sector. La mayoría de la gente se interesa poco en política y no "
    "razona como militante.\n"
    "- Las personas difieren entre sí: usa toda la escala."
)

# En vez de una nota, la probabilidad de cada respuesta. El agregado es el promedio de esas
# probabilidades, y la postura de cada persona en el mapa se sortea con ellas (Monte Carlo).
PREDICTOR = (
    "Vas a estimar cómo contestaría una encuesta una persona real que vive en Chile, según su perfil "
    "(su situación, sus intereses y su forma de pensar). No opines tú ni des la respuesta de un experto "
    "neutral: predice lo que respondería esa persona. Las personas reales difieren entre sí."
)
FORMATO_PROBABILIDAD = (
    "No elijas una respuesta: estima qué tan probable es que esa persona, si le hicieran esta "
    "pregunta en una encuesta, responda cada alternativa. Entrega dos enteros de 0 a 100: la "
    "probabilidad de que responda «de acuerdo» y la de que responda «en desacuerdo». Lo que falte "
    "para 100 es la probabilidad de que no sepa o no responda, que en las encuestas suele ser baja."
)


def lote_probabilidad(n):
    return (
        "Vienen varias personas, numeradas. Estima por separado para cada una, sin que una influya en otra. "
        "Para cada persona devuelve `i` (su número) y `p` (dos enteros de 0 a 100: probabilidad de «de acuerdo» "
        "y probabilidad de «en desacuerdo»)."
    )


def leer_probabilidades(datos, agentes):
    """[(agente, [% de acuerdo, % en desacuerdo])] de lo que devolvió el modelo."""
    salida, vistos = [], set()
    for fila in datos.get("r", []):
        k, p = fila.get("i"), fila.get("p")
        if not isinstance(k, int) or not 0 <= k < len(agentes) or k in vistos:
            continue
        if not (isinstance(p, list) and len(p) == 2 and all(type(v) is int and 0 <= v <= 100 for v in p) and sum(p) <= 100):
            continue
        vistos.add(k)
        salida.append((agentes[k], p))
    return salida


# Las probabilidades con lo que se sabe de cómo contesta la gente, y sin promediar: quien ve bien
# una medida la apoya casi seguro; las probabilidades intermedias son para quien de verdad duda.
PREDICTOR_ENCUESTADO = (
    PREDICTOR + "\n\n"
    "Cómo contesta la gente una encuesta:\n"
    "- Toma posición con su primera impresión, aunque no conozca el detalle. Si a esa persona la medida "
    "le parece bien, su probabilidad de decir «de acuerdo» es alta (85 a 98); si le parece mal, es baja "
    "(2 a 15). Las probabilidades intermedias son solo para quien de verdad tiene motivos en ambos sentidos.\n"
    "- Frente a una medida concreta pesa primero si le sirve o le perjudica a ella y a los suyos, y "
    "si le parece de sentido común. Lo que entrega un beneficio claro, protege o pone orden suele gustar a "
    "gente de todos los sectores políticos, y lo que quita algo o cuesta plata suele disgustar a todos.\n"
    "- La posición política pesa en los temas que dividen por valores o cuando la medida lleva el "
    "sello de un gobierno o de un sector. La mayoría de la gente se interesa poco en política y no "
    "razona como militante."
)

SISTEMA_CLIMA = (
    "Eres analista de opinión pública en Chile. Te entregan una medida o una afirmación que se va a "
    "consultar en una encuesta. Describe en dos o tres frases cómo la recibe la gente común en Chile: si es "
    "de las que casi todos apoyan o casi todos rechazan sin importar su sector político, o si divide, y por "
    "qué línea divide (posición política, edad, religión, bolsillo, vivir en regiones). No des porcentajes "
    "ni cites encuestas."
)
ESQUEMA_CLIMA = {"type": "object", "properties": {"clima": {"type": "string"}}, "required": ["clima"], "additionalProperties": False}
_climas = None


def tema_con_clima(caso):
    """El caso más una nota de cómo se ve el tema en Chile, escrita antes por un modelo redactor
    (`validar_banco.py clima`). Es contexto para todos los agentes por igual; no trae cifras."""
    global _climas
    if _climas is None:
        import json
        from pathlib import Path

        ruta = Path(__file__).resolve().parent.parent / "data" / "pruebas" / "banco" / "clima.jsonl"
        _climas = {f["caso"]: f["clima"] for f in map(json.loads, ruta.read_text(encoding="utf-8").splitlines())} if ruta.exists() else {}
    return f"{tema_del_caso(caso)}\n\nCómo se ve este tema en Chile: {_climas[caso['id']]}"


# Casos del banco que no se usan como referencia: la cifra publicada parece mal transcrita.
DUDOSOS = {"c704-bloqueo"}
_reservas = None


def referencias_para(caso, del_area=4, generales=6):
    """Resultados reales de otras preguntas, para que el modelo sepa cómo responde Chile de verdad.

    Salen solo de las familias de desarrollo y nunca de la familia del caso: así un caso de prueba
    no se apoya en otro de prueba ni en sus parientes. Van hasta `del_area` de su misma área y
    `generales` del resto, repartidas de menor a mayor acuerdo."""
    global _reservas
    if _reservas is None:
        import validar_banco

        _reservas = [c for c in validar_banco.cargar_casos() if c["parte"] == "desarrollo" and c["id"] not in DUDOSOS]
    otros = sorted((c for c in _reservas if c["familia"] != caso["familia"]), key=lambda c: (c["real_acuerdo"], c["id"]))

    def repartidas(lista, k):
        if len(lista) <= k:
            return list(lista)
        return [lista[round(i * (len(lista) - 1) / (k - 1))] for i in range(k)]

    cercanas = repartidas([c for c in otros if c["area"] == caso.get("area")], del_area)
    usadas = {c["id"] for c in cercanas}
    return cercanas + repartidas([c for c in otros if c["id"] not in usadas and c["area"] != caso.get("area")], generales)


def tema_con_referencias(caso):
    filas = "\n".join(f"- {c['enunciado'].strip()} → {c['real_acuerdo']:.0f} % de acuerdo" for c in referencias_para(caso))
    return (
        f"{tema_del_caso(caso)}\n\n# Referencias\n\nResultados reales de encuestas en Chile sobre otras preguntas. "
        f"No son sobre este tema: sirven para saber cuánto apoyo suelen tener distintos tipos de medidas.\n{filas}"
    )


METODOS = {
    # Lo que hace el sitio: las seis preguntas del banco sobre «esta política», perfil temático.
    "sitio": {},
    # Una sola pregunta, como la de la encuesta real, en vez de seis sobre «esta política en tu región».
    "directa": {"preguntas": pregunta_directa},
    # Las seis preguntas del sitio con instrucciones nuevas.
    "encuestado": {"instrucciones": ENCUESTADO},
    # Ambos cambios.
    "directa_encuestado": {"preguntas": pregunta_directa, "instrucciones": ENCUESTADO},
    # Probabilidades en vez de una nota, con las instrucciones del sitio.
    "prob_encuestado": {"preguntas": pregunta_directa, "instrucciones": PREDICTOR_ENCUESTADO, "formato": FORMATO_PROBABILIDAD, "lote": lote_probabilidad, "probabilidades": True},
    # Probabilidades, con una nota previa de cómo se ve el tema en Chile.
    "prob_clima": {"tema": tema_con_clima, "preguntas": pregunta_directa, "instrucciones": PREDICTOR, "formato": FORMATO_PROBABILIDAD, "lote": lote_probabilidad, "probabilidades": True},
    # Probabilidades, con resultados reales de otras preguntas como referencia.
    "prob_referencias": {"tema": tema_con_referencias, "tema_filtro": tema_del_caso, "preguntas": pregunta_directa, "instrucciones": PREDICTOR, "formato": FORMATO_PROBABILIDAD, "lote": lote_probabilidad, "probabilidades": True},
    "probabilidad": {"preguntas": pregunta_directa, "instrucciones": PREDICTOR, "formato": FORMATO_PROBABILIDAD, "lote": lote_probabilidad, "probabilidades": True},
}


def armar(m, caso, agentes):
    """(sistema, prompt, cuántas respuestas por persona, cuál se compara con la encuesta)."""
    texto = m.get("tema", tema_del_caso)(caso)
    preguntas = m["preguntas"](caso) if "preguntas" in m else list(banco.PREGUNTAS)
    instrucciones = m.get("instrucciones", banco.REDACCIONES[1])
    formato = m.get("formato", banco.FORMATO).format(n=len(preguntas), claves=",".join(f"r{i}" for i in range(1, len(preguntas) + 1)))
    lista = "\n".join(f"{i}. {p}" for i, p in enumerate(preguntas, start=1))
    sistema = f"{instrucciones}\n\n{formato}\n\n# Tema de la encuesta\n\n{texto}\n\n# Preguntas\n\n{lista}"
    nivel = m.get("nivel", "tematico")
    datos = filtro.datos_para(metodo.tema_de(m.get("tema_filtro", lambda c: texto)(caso), preguntas), nivel)
    if datos is not None and m.get("datos_extra"):
        datos = frozenset(datos | set(m["datos_extra"]))
    if datos is not None and m.get("datos_menos"):
        datos = frozenset(datos - set(m["datos_menos"]))
    n = len(preguntas)
    # Numeradas desde 0 dentro del lote, como en `motor.prompt_lote`.
    personas = "\n\n".join(f"## Persona {k}\n\n{metodo.perfil(a, datos)}" for k, a in enumerate(agentes))
    lote = m.get("lote", motor.instruccion_lote)(n)
    prompt = f"{lote}\n\n{personas}"
    if not m:
        assert sistema == metodo.sistema_con_politica(texto), "el método `sitio` dejó de ser el del motor"
    return sistema, prompt, n, m.get("cual", 0)
