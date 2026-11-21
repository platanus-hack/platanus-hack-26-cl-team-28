#!/usr/bin/env python3
"""Mide qué datos del perfil pesan en una opinión política y escribe contexto/delphos/influencia.md.

Uso:
    uv run python -I scripts/analizar_influencia.py data/cep96 data/pruebas/sala_cuna contexto/delphos

Es el respaldo del filtro de scripts/filtro_perfil.py: córrelo cuando cambie la CEP, el perfil o
el filtro, y revisa que el núcleo siga explicando casi lo mismo que el perfil completo.

Hace dos mediciones:

A. Con personas reales (Encuesta CEP). Toma las opiniones de la CEP que NO van en el perfil
   (deuda pública, combustibles, promesas del presidente, inmigración, protesta, familia,
   confianza en otras instituciones, figuras políticas) y mide cuánto las predicen los datos
   que SÍ van. Por dato: eta² ajustado, es decir, la parte de la varianza de la opinión que
   explica ese dato solo. Por conjunto de datos (perfil completo, núcleo, núcleo más un tema):
   R² fuera de muestra de una regresión ridge sobre las categorías, con 5 pliegues y 3
   particiones. Todo ponderado con `pond`.

B. Con lo que el modelo hizo. Toma una corrida guardada (Haiku, 800 personas, Sala Cuna) y
   mide cuánto de sus respuestas explica cada atributo del perfil con que respondió.

Límites: A mide opiniones generales, no respuestas a una política concreta, y solo puede evaluar
los datos que la CEP también pregunta (ninguno de vivienda, salud, redes ni transporte). Por eso
los hechos del censo y de Casen no se descartan por esta medición: quedan como datos de tema.
"""

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import filtro_perfil  # noqa: E402
from imputar_cep import DE_LA_CEP, estandarizar_cep  # noqa: E402

LAMBDA = 100.0
PARTICIONES = (11, 12, 13)
MINIMO_CATEGORIA = 15

# Columna de actitudes -> dato del filtro, cuando no se llaman igual.
RENOMBRES = {
    "voto_segunda_vuelta_2025": "voto_2025", "menos_estado_economia": "menos_estado", "reducir_gasto_publico": "reducir_gasto",
    "libertades_o_seguridad": "libertades_seguridad", "justifica_fuerza_carabineros": "justifica_fuerza",
    "hijos_restringen_carrera": "hijos_carrera", "hijos_carga_financiera": "hijos_carga",
    "problema_1": "problemas", "problema_2": "problemas", "problema_3": "problemas",
}
# Opiniones de la CEP que no van en el perfil, por dominio: lo que se intenta predecir.
OBJETIVOS = {
    "Estado y gasto": ["rol_gobierno_30", "rol_gobierno_33"],
    "Gobierno actual": ["eval_gob_61", "eval_gob_62", "pp_congreso_61_b"],
    "Conflicto social": ["pobreza_39_a", "pobreza_39_g", "pobreza_39_m", "pobreza_39_h", "pobreza_39_e", "pobreza_39_n"],
    "Inmigración": ["iden_nacional_8_c", "iden_nacional_8_e", "iden_nacional_8_i", "iden_nacional_8_m"],
    "Protesta y orden": ["ciudadania_29_b", "ciudadania_29_c", "ciudadania_29_f", "educacion_84_a", "ciudadania_30_a", "ciudadania_30_c"],
    "Familia": ["mtf_46_a", "mtf_46_c", "mtf_46_f", "mtf_46_g", "mtf_46_h", "mtf_46_i", "mtf_46_j"],
    "Otras confianzas": ["confianza_6_b", "confianza_6_e", "confianza_6_n", "confianza_6_p", "confianza_6_r"],
    "Figuras políticas": None,  # todas las eval_act_pol_1_*
}


def numero(x, decimales=1):
    return f"{x:.{decimales}f}".replace(".", ",")


def tabla_md(encabezado, filas):
    lineas = ["| " + " | ".join(encabezado) + " |", "|" + "---|" * len(encabezado)]
    return "\n".join(lineas + ["| " + " | ".join(str(c) for c in fila) + " |" for fila in filas])


def predictores(cep):
    """{dato del filtro: [columnas categóricas]} con lo que la CEP sabe de cada entrevistado."""
    d = estandarizar_cep(cep)
    crudos = {
        "edad": [d["edad7"]], "genero": [d["sexo"]], "lugar": [d["macro"], cep["zona_u_r"]], "religion": [d["rel4"]],
        "educacion": [d["educ4"]], "situacion_laboral": [d["activ"]], "decil": [d["nse3"]], "hijos": [cep["mtf_60"].clip(upper=4)],
        "estado_civil": [cep["estado_civil_g"].where(cep["estado_civil_g"] > 0, 99)],
        "pueblo_originario": [cep["info_enc_58"].where(cep["info_enc_58"] > 0, 99)],
    }
    demograficos = list(crudos)
    for variable, columna in DE_LA_CEP.items():
        serie = cep[variable].astype("float64").fillna(-7)  # nulo es «no aplica» (por ejemplo, no votó)
        crudos.setdefault(RENOMBRES.get(columna, columna), []).append(serie.where(serie >= -7, -8))  # no sabe y no contesta, juntos
    sobran = set(crudos) - set(filtro_perfil.DATOS)
    if sobran:
        sys.exit(f"Datos de la CEP sin clave en filtro_perfil.DATOS: {sorted(sobran)}")
    limpios = {}
    for dato, series in crudos.items():
        limpios[dato] = []
        for serie in series:
            serie = pd.Series(np.asarray(serie), dtype="float64")
            conteo = serie.value_counts()
            limpios[dato].append(serie.where(serie.map(conteo) >= MINIMO_CATEGORIA, -77).to_numpy())  # categorías chicas, juntas
    return limpios, demograficos, d["pond"].to_numpy()


def objetivos(cep):
    columnas, dominios, nombres = [], [], []
    for dominio, variables in OBJETIVOS.items():
        for variable in variables or [v for v in cep.columns if v.startswith("eval_act_pol_1_")]:
            serie = cep[variable].astype("float64")
            if variable.startswith("eval_act_pol"):
                serie = serie.where(serie <= 5)  # 6 es «no lo conoce»
            serie = serie.where(serie >= 0)
            if serie.notna().sum() > len(cep) / 2 and serie.std() > 0:
                columnas.append(serie.to_numpy()), dominios.append(dominio), nombres.append(variable)
    return np.column_stack(columnas), np.array(dominios), nombres


def eta2_ajustado(x, y, w):
    """Parte de la varianza de y que explican las categorías de x, descontando el número de categorías."""
    ok = ~np.isnan(y)
    x, y, w = x[ok], y[ok], w[ok]
    media = np.average(y, weights=w)
    total = np.sum(w * (y - media) ** 2)
    niveles = np.unique(x)
    entre = sum(w[x == nivel].sum() * (np.average(y[x == nivel], weights=w[x == nivel]) - media) ** 2 for nivel in niveles)
    return max(0.0, 1 - (1 - entre / total) * (len(y) - 1) / (len(y) - len(niveles)))


def r2_fuera_de_muestra(matrices, datos, Y, w):
    """R² por objetivo de una ridge sobre las categorías de `datos`, promediado en las particiones."""
    n = len(w)
    A = np.column_stack([np.ones(n)] + [m for dato in datos for m in matrices[dato]])
    observado, raiz = ~np.isnan(Y), np.sqrt(w)[:, None]
    salida = []
    for semilla in PARTICIONES:
        pliegue = np.random.default_rng(semilla).permutation(n) % 5
        error, total = np.zeros(Y.shape[1]), np.zeros(Y.shape[1])
        for k in range(5):
            entrena, prueba = pliegue != k, pliegue == k
            medias = np.array([np.average(Y[entrena, j][observado[entrena, j]], weights=w[entrena][observado[entrena, j]]) for j in range(Y.shape[1])])
            centrado = np.where(observado, Y - medias, 0.0)
            At = A[entrena] * raiz[entrena]
            castigo = LAMBDA * np.eye(A.shape[1])
            castigo[0, 0] = 0
            coeficientes = np.linalg.solve(At.T @ At + castigo, At.T @ (centrado[entrena] * raiz[entrena]))
            vistos, pesos = observado[prueba], w[prueba][:, None]
            error += np.sum(np.where(vistos, pesos * (centrado[prueba] - A[prueba] @ coeficientes) ** 2, 0), axis=0)
            total += np.sum(np.where(vistos, pesos * centrado[prueba] ** 2, 0), axis=0)
        salida.append(100 * (1 - error / total))
    return np.mean(salida, axis=0)


def nivel_de(dato):
    if dato in filtro_perfil.NUCLEO:
        return "núcleo"
    temas = [tema for tema, definicion in filtro_perfil.TEMAS.items() if dato in definicion["datos"]]
    return ", ".join(temas) if temas else "solo completo"


def parte_cep(carpeta):
    cep = pd.read_parquet(carpeta / "cep96.parquet")
    series, demograficos, w = predictores(cep)
    w = w / w.mean()
    Y, dominios, nombres = objetivos(cep)
    orden_dominios = list(OBJETIVOS)

    # Cada dato por separado.
    solo = {dato: np.array([max(eta2_ajustado(x, Y[:, j], w) for x in columnas) for j in range(Y.shape[1])]) for dato, columnas in series.items()}
    filas = []
    for dato in sorted(solo, key=lambda d: -solo[d].mean()):
        filas.append([f"`{dato}`", nivel_de(dato), numero(100 * solo[dato].mean())] + [numero(100 * solo[dato][dominios == d].mean()) for d in orden_dominios])
    tabla_datos = tabla_md(["Dato", "Nivel en el filtro", "Todas"] + orden_dominios, filas)

    # Conjuntos de datos.
    matrices = {dato: [pd.get_dummies(pd.Series(x).astype(str)).to_numpy(dtype="float64") for x in columnas] for dato, columnas in series.items()}
    medibles = list(series)
    conjuntos = [("Perfil completo", medibles), ("Solo demografía", demograficos), ("Núcleo", [d for d in medibles if d in filtro_perfil.NUCLEO])]
    for tema in filtro_perfil.TEMAS:
        del_tema = [d for d in medibles if d in filtro_perfil.datos_de_temas([tema])]
        if len(del_tema) > len(conjuntos[2][1]):
            conjuntos.append((f"Núcleo + {tema}", del_tema))
    resultados = [(nombre, datos, r2_fuera_de_muestra(matrices, datos, Y, w)) for nombre, datos in conjuntos]
    completo = resultados[0][2].mean()
    filas = [[nombre, len(datos), numero(r.mean()), f"{numero(100 * r.mean() / completo, 0)} %"] + [numero(r[dominios == d].mean()) for d in orden_dominios] for nombre, datos, r in resultados]
    tabla_conjuntos = tabla_md(["Conjunto", "Datos medibles", "R² medio", "Del completo"] + orden_dominios, filas)
    no_medibles = sorted(set(filtro_perfil.DATOS) - set(medibles))
    return len(cep), len(nombres), tabla_datos, tabla_conjuntos, no_medibles, resultados


def parte_modelo(carpeta):
    """Cuánto de las respuestas de una corrida guardada explica cada atributo del perfil corto de entonces."""
    personas, resultados = carpeta / "personas_regiones_50_actitudes.jsonl", carpeta / "resultados_validacion_actitudes_haiku55.jsonl"
    if not personas.exists() or not resultados.exists():
        return None
    atributos = {}
    for linea in open(personas, encoding="utf-8"):
        persona = json.loads(linea)
        suyos = dict(persona.get("grupos") or persona.get("atributos") or {})
        suyos.pop("Comuna", None)
        if "años" in str(suyos.get("Edad")):
            suyos["Edad"] = int(re.search(r"\d+", suyos["Edad"]).group()) // 15  # tramos de 15 años
        atributos[persona["id"]] = suyos
    filas = [json.loads(linea) for linea in open(resultados, encoding="utf-8")]
    filas = [r for r in filas if r.get("valida") and r.get("respuestas") and not r.get("repeticion") and r["id"] in atributos]
    claves = sorted(filas[0]["respuestas"])
    pesos = np.ones(len(filas))
    salida = []
    for atributo in sorted({a for r in filas for a in atributos[r["id"]]}):
        grupos = defaultdict(int)
        valores = [str(atributos[r["id"]].get(atributo, "(sin dato)")) for r in filas]
        for v in valores:
            grupos[v] += 1
        if not 2 <= len(grupos) <= 40:
            continue
        codigos = np.array([list(grupos).index(v) for v in valores], dtype="float64")
        etas = [100 * eta2_ajustado(codigos, np.array([r["respuestas"][c] for r in filas], dtype="float64"), pesos) for c in claves]
        salida.append((np.mean(etas), atributo, etas))
    salida.sort(reverse=True)
    tabla = tabla_md(["Atributo del perfil", "Media"] + claves, [[a, numero(m)] + [numero(e) for e in etas] for m, a, etas in salida])
    return len(filas), tabla


def main():
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    carpeta_cep, carpeta_caso, carpeta_salida = (Path(a) for a in sys.argv[1:])
    entrevistas, n_objetivos, tabla_datos, tabla_conjuntos, no_medibles, resultados = parte_cep(carpeta_cep)
    modelo = parte_modelo(carpeta_caso)
    de_tema = {dato for definicion in filtro_perfil.TEMAS.values() for dato in definicion["datos"]}

    partes = [f"""# Qué datos del perfil pesan en una opinión política

Lo escribe `scripts/analizar_influencia.py`; no lo edites a mano. Es el respaldo del filtro de `scripts/filtro_perfil.py` (versión `{filtro_perfil.VERSION}`), que decide qué datos de cada persona lee el modelo: {len(filtro_perfil.DATOS)} en el perfil completo, {len(filtro_perfil.NUCLEO)} en el núcleo y {len(de_tema - filtro_perfil.NUCLEO)} que solo van si la política toca su tema.

## A. Con personas reales: Encuesta CEP

Se tomaron {n_objetivos} opiniones de la CEP ({f"{entrevistas:,}".replace(",", ".")} entrevistas) que **no** van en el perfil y se midió cuánto las predicen los datos que **sí** van. Si un dato no ayuda a predecir ninguna, entregárselo al modelo solo le suma texto.

### Por conjunto de datos

R² fuera de muestra, en porcentaje: cuánta de la variación de las opiniones se predice en personas que el modelo estadístico no vio (ridge, 5 pliegues, 3 particiones, ponderado). «Datos medibles» son los del conjunto que la CEP también pregunta.

{tabla_conjuntos}

El núcleo conserva la mayor parte de lo que predice el perfil completo, y la demografía sola predice muy poco: lo que mueve una opinión es la posición política, el voto y la evaluación de los gobiernos. Cada tema recupera lo propio de su dominio (los datos de inmigración en «Inmigración», los de seguridad en «Protesta y orden»), que es para lo que existe.

### Por dato

Porcentaje de la varianza de las opiniones que explica cada dato por sí solo (eta² ajustado), en promedio y por dominio. Un dato que es varias columnas (`problemas`, `lugar`) toma la que más explica.

{tabla_datos}

Datos del perfil que la CEP no pregunta y por eso no aparecen ({len(no_medibles)}): {', '.join(f'`{d}`' for d in no_medibles)}. Son hechos del censo y de Casen; el filtro los deja como datos de tema, para cuando la política los toca directamente.
"""]
    if modelo:
        n, tabla = modelo
        partes.append(f"""## B. Con lo que el modelo hizo

Claude Haiku, {n} personas, texto de validación de Sala Cuna (`data/pruebas/sala_cuna/resultados_validacion_actitudes_haiku55.jsonl`), con el perfil corto de entonces. Porcentaje de la varianza de cada respuesta que explica cada atributo por sí solo.

{tabla}

El modelo responde sobre todo con la posición política, la evaluación del gobierno y la confianza en el gobierno (que domina la pregunta 4, la de confianza en el Estado). Después vienen los datos que dicen si la medida toca a la persona: aquí, situación laboral, edad y niños en el hogar. El resto casi no se usa.
""")
    partes.append("""## Límites

- La parte A mide opiniones generales, no respuestas a una política concreta. Sirve para ordenar los datos, no para afirmar cuánto cambia una respuesta.
- Las palabras clave de los temas se ajustaron mirando `datos-pruebas/encuestas/`: que detecten bien el área de esos casos no prueba que lo hagan con textos nuevos.
- Qué cambia en las respuestas del modelo al usar el filtro se mide aparte, con `scripts/comparar_perfiles.py` (ver «Perfil filtrado contra perfil completo» en `servidor/README.md`). Hasta ahora hay un solo caso y un solo modelo.

Fuente: Centro de Estudios Públicos, Encuesta CEP N° 96, abril-mayo 2026.
""")
    carpeta_salida.mkdir(parents=True, exist_ok=True)
    salida = carpeta_salida / "influencia.md"
    salida.write_text("\n".join(partes), encoding="utf-8")
    print(f"{salida}: {n_objetivos} opiniones de la CEP, {len(resultados)} conjuntos de datos")
    for nombre, datos, r in resultados:
        print(f"  {nombre:<34} {len(datos):>3} datos  R² {r.mean():5.1f} %")


if __name__ == "__main__":
    main()
