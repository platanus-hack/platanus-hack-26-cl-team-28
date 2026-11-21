#!/usr/bin/env python3
"""Genera los archivos de contexto del Censo 2024 desde los datos descargados.

Uso:
    uv run python -I scripts/construir_contexto.py data/censo2024 contexto/censo2024

Lee lo que dejó descargar_censo.py y escribe, en la carpeta de contexto:
diccionario.md, etiquetas.csv, codigos-territoriales.md, comunas.csv,
territorios.csv, territorios_especificos.csv, diccionario-agregados.md,
tabulados.md, documentos.md, resumen.md y docs/*.txt.
También convierte cada hoja de los tabulados a CSV en <datos>/tabulados_csv/.
Termina con código 1 si alguna verificación contra las cifras oficiales falla.
"""

import csv
import re
import subprocess
import sys
from pathlib import Path

import duckdb
import openpyxl

TABLAS = {
    "viviendas": ("tabla_viviendas", "id_vivienda"),
    "hogares": ("tabla_hogares", "id_vivienda, id_hogar"),
    "personas": ("tabla_personas", "id_vivienda, id_hogar, id_persona"),
}

DOCUMENTOS = {
    "manual_uso_microdatos_censo2024": "Manual de uso de microdatos: estructura de las tablas, variables calculadas, control de divulgación, diccionario y fichas de 47 indicadores con código R. Es la referencia principal.",
    "sintesis_resultados_censo2024": "Síntesis de resultados nacionales y regionales (publicación oficial de diciembre de 2025).",
    "Ficha_metodologica_CPV2024": "Ficha metodológica: tipo de censo, población objetivo, período de levantamiento, modalidades.",
    "Presentacion_microdatos_CPV2024": "Presentación del INE sobre la base de microdatos.",
    "Cuestionario-Viviendas-Particulares_CPV2024": "Cuestionario de viviendas particulares (50 preguntas).",
    "Cuestionario-Viviendas-Colectivas-y-Personas-en-Situacion-de-Calle_CPV2024": "Cuestionario de viviendas colectivas y personas en situación de calle.",
    "Manual_Censal_CPV2024": "Manual del censista: instrucciones y definiciones operativas de cada pregunta.",
    "Glosario_CPV2024-1": "Glosario general de los primeros resultados.",
    "Glosario_fecundidad_migracion_CPV2024": "Glosario de fecundidad y migración.",
    "Glosario_viviendas_y_servicios-basicos_CPV2024": "Glosario de viviendas y servicios básicos.",
    "Glosario-Caracteristicas-de-la-poblacion_final": "Glosario de características de la población.",
    "N1_Nota_tecnica_desempenio_operativo_CPV2024": "Nota técnica 1: desempeño operativo.",
    "N2_Nota_tecnica_respuesta_modalidades_recoleccion_CPV2024": "Nota técnica 2: respuesta por modalidad de recolección.",
    "N3_Nota_Tecnica_Comparacion_Poblacion_CPV2024": "Nota técnica 3: comparación de la población censada con proyecciones y censos previos.",
    "N4_Nota_Tecnica_Ajuste_direcciones_CPV2024": "Nota técnica 4: ajuste de direcciones.",
    "N5_Nota_Tecnica_indeterminacion_geografica_CPV2024": "Nota técnica 5: indeterminación geográfica en los datos agregados.",
    "N6_Nota_tecnica_Tratamiento_no_respuesta_al_item": "Nota técnica 6: tratamiento de la no respuesta al ítem.",
    "Manual_uso_cartografia_CPV2024": "Manual de uso de la cartografía y de las bases agregadas (manzana-entidad, zona-localidad).",
    "Presentacion_cartografia_base_manzana_entidad_CPV2024": "Presentación sobre cartografía y base manzana-entidad.",
    "Conmutacion_Laboral_cpv2024": "Documento de conmutación laboral (versión del 10 de noviembre de 2026).",
    "261026_doc_conmutacion_laboral_cpv": "Documento de conmutación laboral (versión previa, 6 de noviembre de 2026).",
    "Resultados_CPV2024_Aplicación_DEGURBA": "Resultados de aplicar el grado de urbanización DEGURBA al Censo 2024.",
    "Glosario_CPV2024_Dashboard_DEGURBA": "Glosario del tablero DEGURBA.",
}


def miles(n):
    return f"{n:,}".replace(",", ".")


def pct(num, den):
    return f"{num / den * 100:.1f}".replace(".", ",") if den else "s/d"


def dec(x, d=1):
    return f"{x:.{d}f}".replace(".", ",")


def celda(x):
    if x is None:
        return ""
    if isinstance(x, float) and x.is_integer():
        x = int(x)
    return re.sub(r"\s+", " ", str(x)).strip().replace("|", "\\|")


def entero(x):
    """Convierte '7.664.466', 7664466 o 7664466.0 a int; None si no es entero."""
    if isinstance(x, bool) or x is None:
        return None
    if isinstance(x, (int, float)):
        return int(x) if float(x).is_integer() else None
    s = str(x).strip().replace(".", "")
    return int(s) if re.fullmatch(r"-?\d+", s) else None


def leer_hoja(ruta, hoja):
    wb = openpyxl.load_workbook(ruta, read_only=True, data_only=True)
    filas = [tuple(f) for f in wb[hoja].iter_rows(values_only=True)]
    wb.close()
    return filas


def tabla_md(encabezado, filas):
    lineas = ["| " + " | ".join(encabezado) + " |", "|" + "---|" * len(encabezado)]
    lineas += ["| " + " | ".join(celda(c) for c in f) + " |" for f in filas]
    return "\n".join(lineas)


def escribir_csv(ruta, encabezado, filas):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(encabezado)
        w.writerows(filas)


class Constructor:
    def __init__(self, datos, salida):
        self.datos, self.salida = datos, salida
        self.con = duckdb.connect()
        self.fallas = []
        self.etiquetas = {}  # (tabla, variable) -> {valor: etiqueta}
        self.parquet = {t: (datos / "microdatos" / f"{t}_censo2024.parquet").as_posix() for t in TABLAS}

    def q(self, sql):
        return self.con.execute(sql).fetchall()

    def comprobar(self, nombre, obtenido, esperado):
        ok = obtenido == esperado
        print(f"  {'OK   ' if ok else 'FALLA'} {nombre}: {obtenido}" + ("" if ok else f" (esperado {esperado})"))
        if not ok:
            self.fallas.append(nombre)

    # ---------- diccionario de microdatos ----------
    def diccionario(self):
        xlsx = self.datos / "docs" / "diccionario_variables_censo2024.xlsx"
        md = [
            "# Diccionario de variables de los microdatos del Censo 2024",
            "",
            "Generado por `scripts/construir_contexto.py` desde `data/censo2024/docs/diccionario_variables_censo2024.xlsx` (INE).",
            "La columna Casos es el conteo publicado por el INE, verificado contra los Parquet al generar este archivo.",
            "",
            "Valores especiales en todas las tablas:",
            "",
            "- `-99`: no responde. El INE lo excluye de los denominadores al calcular porcentajes.",
            "- `-66`: valor suprimido por anonimización.",
            "- `NULL` (NA): la pregunta no aplica a esa unidad.",
            "",
        ]
        filas_etiquetas = []
        categorias_ok = categorias_mal = 0
        for tabla, (hoja, llave) in TABLAS.items():
            filas = leer_hoja(xlsx, hoja)[1:]
            variables = {}
            for f in filas:
                if f[1]:
                    variables.setdefault(str(f[1]).strip(), []).append(f)
            columnas = {c[0]: c[1] for c in self.q(f"describe select * from '{self.parquet[tabla]}'")}
            n = self.q(f"select count(*) from '{self.parquet[tabla]}'")[0][0]
            solo_parquet = [c for c in columnas if c not in variables]
            solo_dicc = [v for v in variables if v not in columnas]
            self.comprobar(f"columnas de {tabla} iguales al diccionario", (solo_parquet, solo_dicc), ([], []))

            md += [f"## {tabla}", "", f"`{tabla}_censo2024.parquet`: {miles(n)} filas, {len(columnas)} columnas. Llave: `{llave}`.", ""]
            for var, cats in variables.items():
                desc = celda(cats[0][2])
                universos = list(dict.fromkeys(celda(c[6]) for c in cats if c[6]))
                tipo = columnas.get(var, "?")
                if len(cats) == 1 and entero(cats[0][3]) is None:
                    md.append(
                        f"- `{var}` ({tipo}): {desc}. Rango {celda(cats[0][3])}; {celda(cats[0][4])}. Universo: {'; '.join(universos)}."
                    )
                    continue
                reales = dict(self.q(f"select {var}, count(*) from '{self.parquet[tabla]}' group by 1")) if var in columnas else {}
                md += ["", f"### `{var}`: {desc}", "", f"{tipo}. Universo: {'; '.join(universos)}.", ""]
                cuerpo = []
                for c in cats:
                    valor, etiqueta, casos = c[3], celda(c[4]), entero(c[7])
                    v = entero(valor)
                    es_na = str(valor).strip().upper() == "NA"
                    cuerpo.append((celda(valor), etiqueta, miles(casos) if casos is not None else celda(c[7])))
                    if v is None and not es_na:
                        continue  # fila de rango, no una categoría
                    self.etiquetas.setdefault((tabla, var), {})[v] = etiqueta
                    filas_etiquetas.append((tabla, var, "" if es_na else v, etiqueta, casos))
                    if casos is not None and tipo != "VARCHAR":
                        if reales.get(v, 0) == casos:
                            categorias_ok += 1
                        else:
                            categorias_mal += 1
                            print(f"    conteo distinto {tabla}.{var}={valor}: diccionario {casos}, parquet {reales.get(v, 0)}")
                md += [tabla_md(["Valor", "Etiqueta", "Casos"], cuerpo), ""]
            md.append("")
        self.comprobar("categorías cuyo conteo difiere del diccionario", categorias_mal, 0)
        print(f"        ({categorias_ok} categorías coinciden con el diccionario del INE)")
        (self.salida / "diccionario.md").write_text("\n".join(md) + "\n", encoding="utf-8")
        escribir_csv(self.salida / "etiquetas.csv", ["tabla", "variable", "valor", "etiqueta", "casos"], filas_etiquetas)

    # ---------- territorios ----------
    def territorios(self):
        xlsx = self.datos / "docs" / "diccionario_variables_censo2024.xlsx"
        filas = [(entero(f[0]), celda(f[1]), celda(f[2])) for f in leer_hoja(xlsx, "codigos_territoriales")[1:] if f[0] is not None]
        nivel = {"Región": "region", "Provincia": "provincia", "Comuna": "comuna"}
        regiones = {c: n for c, d, n in filas if d == "Región"}
        provincias = {c: n for c, d, n in filas if d == "Provincia"}
        comunas = {c: n for c, d, n in filas if d == "Comuna"}
        self.comprobar("regiones, provincias y comunas en el diccionario", (len(regiones), len(provincias), len(comunas)), (16, 56, 346))
        self.regiones = regiones
        escribir_csv(self.salida / "territorios.csv", ["codigo", "nivel", "nombre"], [(c, nivel[d], n) for c, d, n in filas])

        P, H, V = (f"'{self.parquet[t]}'" for t in ("personas", "hogares", "viviendas"))
        pob = {
            r[0]: r[1:]
            for r in self.q(
                f"""select comuna, count(*), count(*) filter (where sexo = 1), count(*) filter (where sexo = 2),
                           count(*) filter (where area = 1), count(*) filter (where area = 2), min(comuna_bajo_umbral)
                    from {P} group by 1"""
            )
        }
        viv = dict(self.q(f"select comuna, count(*) from {V} where tipo_operativo in (2, 3) group by 1"))
        hog = dict(self.q(f"select comuna, count(*) from {H} where tipo_operativo = 2 group by 1"))
        filas_comunas = []
        for c, nombre in sorted(comunas.items()):
            p = pob[c]
            filas_comunas.append(
                (c, nombre, c // 100, provincias[c // 100], c // 1000, regiones[c // 1000], *p[:5], viv.get(c, 0), hog.get(c, 0), int(p[5] == 1))
            )
        escribir_csv(
            self.salida / "comunas.csv",
            ["comuna", "nombre_comuna", "provincia", "nombre_provincia", "region", "nombre_region", "poblacion",
             "hombres", "mujeres", "poblacion_urbana", "poblacion_rural", "viviendas", "hogares", "bajo_umbral"],
            filas_comunas,
        )
        self.comprobar("suma de población de comunas.csv", sum(f[6] for f in filas_comunas), 18480432)

        esp = [(entero(f[0]), celda(f[1])) for f in leer_hoja(xlsx, "cod_territoriales_especificos")[1:] if f[0] is not None]
        escribir_csv(self.salida / "territorios_especificos.csv", ["codigo", "nombre"], esp)
        no_comunas = [(c, n) for c, n in esp if c not in comunas]

        md = [
            "# Códigos territoriales del Censo 2024",
            "",
            "Generado desde el diccionario de variables del INE. Los mismos datos están en CSV para unirlos en consultas:",
            "",
            "- `comunas.csv`: una fila por comuna con sus nombres de provincia y región, población, viviendas y hogares.",
            "- `territorios.csv`: código, nivel (`region`, `provincia`, `comuna`) y nombre.",
            "- `territorios_especificos.csv`: códigos de las variables `*_esp` (comunas y países o continentes).",
            "",
            "Los códigos se repiten entre niveles (11 es la región de Aysén y también la provincia de Iquique), así que al unir con `territorios.csv` hay que filtrar por `nivel`.",
            "El código de comuna es RRPCC: `comuna // 1000` da la región y `comuna // 100` la provincia.",
            "",
            "## Regiones",
            "",
            tabla_md(["Código", "Región"], sorted(regiones.items())),
            "",
            "## Comunas",
            "",
            "Bajo umbral = comuna con menos de 6.000 personas censadas, donde el INE suprime más detalle (ver `CLAUDE.md`).",
            "",
            tabla_md(
                ["Comuna", "Nombre", "Provincia", "Región", "Población", "Bajo umbral"],
                [(f[0], f[1], f[3], f[5], miles(f[6]), "sí" if f[13] else "") for f in filas_comunas],
            ),
            "",
            "## Códigos específicos que no son comunas",
            "",
            "Usados en `p24_lug_resid5_esp`, `p25_lug_nacimiento_esp`, `p27_nacionalidad_esp` y `p44_lug_trab_esp`.",
            "",
            tabla_md(["Código", "Territorio"], no_comunas),
            "",
        ]
        (self.salida / "codigos-territoriales.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    # ---------- datos agregados ----------
    def agregados(self):
        xlsx = self.datos / "docs" / "diccionario_variables_glosas_censo2024.xlsx"
        filas = [f for f in leer_hoja(xlsx, "Dicionario")[1:] if f[1]]
        bases = []
        for nombre, que in [
            ("manzana_entidad", "manzanas (urbano) y entidades (rural); el nivel más fino"),
            ("zona_localidad", "zonas censales (urbano) y localidades (rural)"),
            ("urbanos", "entidades urbanas (ciudades y pueblos)"),
            ("aldeas", "aldeas (entidades rurales concentradas)"),
        ]:
            f = (self.datos / "agregados" / f"Base_{nombre}_CPV24.csv").as_posix()
            n, per = self.q(f"select count(*), sum(try_cast(n_per as bigint)) from read_csv('{f}', all_varchar = true)")[0]
            ncols = len(self.q(f"describe select * from read_csv('{f}', all_varchar = true)"))
            bases.append((f"`Base_{nombre}_CPV24.csv`", que, miles(n), ncols, miles(per)))
        md = [
            "# Datos agregados del Censo 2024 (bajo el nivel comunal)",
            "",
            "Los microdatos solo llegan a comuna y área urbana o rural. Para territorios más pequeños el INE publica conteos ya agregados en `data/censo2024/agregados/`:",
            "",
            tabla_md(["Archivo", "Unidad", "Filas", "Columnas", "Suma de n_per"], bases),
            "",
            "Las vistas `manzana_entidad`, `zona_localidad`, `urbanos` y `aldeas` de `scripts/consulta.py` ya entregan los conteos y promedios como números. Al leer los CSV directamente:",
            "",
            "- Las celdas con `*` están suprimidas por secreto estadístico. Por eso muchas columnas numéricas llegan como texto: usar `try_cast(col as bigint)`.",
            "- Los promedios usan coma decimal (`32,8`): usar `try_cast(replace(col, ',', '.') as double)`.",
            "- `CONTENEDOR_COMUNAL = 1` marca filas que juntan, por comuna, a las personas que no se pudieron asignar a una unidad menor. No son un lugar real y vienen sin nombre. Están en `manzana_entidad`, `zona_localidad` y `urbanos`: inclúyelas para que los totales comunales cuadren y exclúyelas al buscar la unidad más poblada o al mapear.",
            "- `zona_localidad` mezcla dos unidades. Las filas urbanas (`AREA_C = 1`) son zonas censales: no tienen nombre propio, se identifican por `DISTRITO` y `COD_ZONA` (o `ID_ZONA`), y `LOCALIDAD` es la ciudad que las contiene. Las filas rurales (`AREA_C = 2`) son localidades con nombre e `ID_LOCALIDAD`. `ID_ZONA` solo viene en las urbanas e `ID_LOCALIDAD` solo en las rurales.",
            "- Un mismo nombre de localidad puede existir como urbana y como rural dentro de una comuna. Agrupa por `AREA_C` además de `LOCALIDAD`, o usa `urbanos` para el total de una ciudad.",
            "- `CUT` es el código de comuna, el mismo que `comuna` en los microdatos.",
            "- Las glosas de distritos, zonas, localidades y entidades están en la hoja `Glosas_variables_geográficas` de `data/censo2024/docs/diccionario_variables_glosas_censo2024.xlsx`.",
            "- La nota técnica 5 y el manual de cartografía (en `docs/`) explican la indeterminación geográfica.",
            "",
            "## Variables",
            "",
            "No todas las variables están en las cuatro bases; las de identificación geográfica cambian según el nivel.",
            "",
        ]
        tematica = None
        cuerpo = []
        for f in filas:
            if celda(f[0]) != tematica:
                if cuerpo:
                    md += [tabla_md(["Variable", "Tipo", "Descripción", "Universo"], cuerpo), ""]
                tematica, cuerpo = celda(f[0]), []
                md += [f"### {tematica}", ""]
            cuerpo.append((f"`{celda(f[1])}`", f[2], f[3], f[4]))
        md += [tabla_md(["Variable", "Tipo", "Descripción", "Universo"], cuerpo), ""]
        (self.salida / "diccionario-agregados.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    # ---------- tabulados oficiales ----------
    def tabulados(self):
        destino = self.datos / "tabulados_csv"
        destino.mkdir(exist_ok=True)
        md = [
            "# Tabulados oficiales del Censo 2024",
            "",
            "Cifras publicadas por el INE. Son la referencia para contrastar cualquier cálculo hecho con los microdatos.",
            "Los xlsx originales están en `data/censo2024/tabulados/`; cada hoja se convirtió a CSV en `data/censo2024/tabulados_csv/` (encabezado en la primera fila, sin título ni notas al pie).",
            "La nota de presentación de cada archivo, con sus definiciones, quedó en `<prefijo>_nota.txt` en la misma carpeta.",
            "",
        ]
        self.tab = {}
        for xlsx in sorted((self.datos / "tabulados").glob("*.xlsx")):
            prefijo = re.match(r"[A-Z]\d+", xlsx.name).group(0)
            wb = openpyxl.load_workbook(xlsx, read_only=True, data_only=True)
            md += [f"## {prefijo}: `{xlsx.name}`", ""]
            for ws in wb.worksheets:
                filas = [tuple(f) for f in ws.iter_rows(values_only=True)]
                llenas = lambda f: [x for x in f if x not in (None, "")]
                if ws.title == "Nota":
                    texto = [celda(llenas(f)[0]) for f in filas if llenas(f)]
                    (destino / f"{prefijo}_nota.txt").write_text("\n".join(texto) + "\n", encoding="utf-8")
                    fecha = next((t for t in texto if t.lower().startswith("fecha de publicación")), "")
                    if fecha:
                        md += [fecha, ""]
                    continue
                ih = next(i for i, f in enumerate(filas) if len(llenas(f)) >= 3)
                titulo = next(celda(llenas(f)[0]) for f in filas[:ih] if llenas(f))
                ancho = max(i for i, x in enumerate(filas[ih]) if x not in (None, "")) + 1
                encabezado = [celda(x) for x in filas[ih][:ancho]]
                cuerpo = filas[ih + 1 :]
                notas = []
                while cuerpo and len(llenas(cuerpo[-1])) < 3:
                    pie = cuerpo.pop()
                    if llenas(pie):
                        notas.insert(0, celda(llenas(pie)[0]))
                cuerpo = [[("" if x is None else int(x) if isinstance(x, float) and x.is_integer() else x) for x in f[:ancho]] for f in cuerpo]
                nombre = f"{prefijo}_{ws.title}.csv"
                escribir_csv(destino / nombre, encabezado, cuerpo)
                self.tab[nombre] = (encabezado, cuerpo)
                titulo = re.sub(r"^\d+\.\s*", "", titulo)
                md.append(f"- `{nombre}` ({miles(len(cuerpo))} filas): {titulo} Columnas: {'; '.join(encabezado)}.")
                md += [f"  - Nota: {n}" for n in notas if not n.startswith("Fuente:")]
            md.append("")
            wb.close()
        (self.salida / "tabulados.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    # ---------- documentos ----------
    def documentos(self):
        destino = self.salida / "docs"
        destino.mkdir(exist_ok=True)
        filas = []
        for pdf in sorted((self.datos / "docs").glob("*.pdf")):
            txt = destino / (pdf.stem + ".txt")
            subprocess.run(["pdftotext", "-layout", pdf.as_posix(), txt.as_posix()], check=True)
            info = subprocess.run(["pdfinfo", pdf.as_posix()], capture_output=True, text=True).stdout
            paginas = re.search(r"Pages:\s+(\d+)", info)
            filas.append((f"`docs/{txt.name}`", paginas.group(1) if paginas else "?", miles(len(txt.read_text(encoding="utf-8", errors="replace")) // 1000) + " k", DOCUMENTOS.get(pdf.stem, "")))
            if pdf.stem not in DOCUMENTOS:
                print(f"    sin descripción: {pdf.name}")
        md = [
            "# Documentación del Censo 2024 en texto",
            "",
            "Cada PDF de `data/censo2024/docs/` se convirtió a texto con `pdftotext -layout`. Los archivos largos conviene buscarlos con grep en vez de leerlos enteros.",
            "Las tablas y fórmulas pierden formato en la conversión; ante la duda, abrir el PDF original.",
            "",
            tabla_md(["Archivo", "Páginas", "Caracteres", "Contenido"], filas),
            "",
            "Sin convertir: `Cs_Pb_Al_Cs_CPV2024.html` (reporte interactivo de entidades) y los dos diccionarios xlsx, ya volcados en `diccionario.md` y `diccionario-agregados.md`.",
            "",
        ]
        (self.salida / "documentos.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    # ---------- resumen ----------
    def frecuencia(self, tabla, var, filtro="true", titulo=None):
        """Tabla de frecuencias con etiquetas. El % excluye -99, -66 y NULL, como hace el INE."""
        filas = self.q(f"select {var}, count(*) from '{self.parquet[tabla]}' where {filtro} group by 1 order by 1")
        etiquetas = self.etiquetas.get((tabla, var), {})
        validos = sum(n for v, n in filas if v is not None and v >= 0)
        cuerpo = [(v, etiquetas.get(v, "?"), miles(n), pct(n, validos)) for v, n in filas if v is not None and v >= 0]
        fuera = {-99: "no responde", -66: "suprimido", None: "no aplica"}
        resto = [f"{fuera[v]} {miles(n)}" for v, n in filas if v in fuera]
        return [
            f"### {titulo or var}",
            "",
            f"`{tabla}.{var}`" + (f", filtro `{filtro}`" if filtro != "true" else "") + (f". Fuera del porcentaje: {', '.join(resto)}." if resto else "."),
            "",
            tabla_md(["Valor", "Categoría", "Casos", "%"], cuerpo),
            "",
        ]

    def resumen(self):
        P, H, V = (f"'{self.parquet[t]}'" for t in ("personas", "hogares", "viviendas"))
        total, hombres, mujeres, urbana, e0_14, e15_64, e65 = self.q(
            f"""select count(*), count(*) filter (where sexo = 1), count(*) filter (where sexo = 2),
                       count(*) filter (where area = 1), count(*) filter (where edad_quinquenal < 15),
                       count(*) filter (where edad_quinquenal between 15 and 64), count(*) filter (where edad_quinquenal >= 65)
                from {P}"""
        )[0]
        operativo = dict(self.q(f"select tipo_operativo, count(*) from {P} group by 1"))
        viv = dict(self.q(f"select tipo_operativo, count(*) from {V} group by 1"))
        hogares = self.q(f"select count(*) from {H} where tipo_operativo = 2")[0][0]
        unipersonales = self.q(
            f"select count(*) from (select 1 from {P} where tipo_operativo = 2 group by id_vivienda, id_hogar having count(*) = 1)"
        )[0][0]
        jefas = self.q(f"select count(*) filter (where sexo = 2), count(*) from {P} where parentesco = 1 and tipo_operativo = 2")[0]
        internet = self.q(
            f"""select count(*) filter (where p15d_serv_internet_fija = 1 or p15e_serv_internet_movil = 1 or p15f_serv_internet_satelital = 1), count(*)
                from {H} where tipo_operativo = 2
                  and (p15d_serv_internet_fija <> -99 or p15e_serv_internet_movil <> -99 or p15f_serv_internet_satelital <> -99)"""
        )[0]
        inmig = self.q(f"select count(*) filter (where p25_lug_nacimiento = 3), count(*) from {P} where p25_lug_nacimiento <> -99")[0]
        pueblos = self.q(f"select count(*) filter (where p28_autoid_pueblo = 1), count(*) from {P} where p28_autoid_pueblo <> -99")[0]
        afro = self.q(f"select count(*) filter (where p29_afrodescendencia_rec = 1), count(*) from {P} where p29_afrodescendencia_rec <> -99")[0]
        escolaridad = self.q(f"select avg(escolaridad) from {P} where escolaridad <> -99")[0][0]
        # En las 51 comunas con edad suprimida (-66) solo se conoce el tramo quinquenal: ahí se cuenta desde los 20.
        escolaridad18 = self.q(
            f"select avg(escolaridad) from {P} where escolaridad <> -99 and (edad >= 18 or (edad = -66 and edad_quinquenal >= 20))"
        )[0][0]
        alfabet = self.q(f"select count(*) filter (where p37_alfabet = 1), count(*) from {P} where edad_quinquenal >= 15 and p37_alfabet <> -99")[0]
        disc = self.q(f"select count(*) filter (where discapacidad = 1), count(*) from {P} where discapacidad in (1, 2)")[0]
        mediana = self.q(f"select median(edad) from {P} where edad >= 0")[0][0]

        # Verificación contra cifras oficiales publicadas por el INE
        d1 = {entero(f[0]): f for f in self.tab["D1_1.csv"][1]}
        d2 = self.tab["D2_1.csv"][1][0]
        d3 = self.tab["D3_1.csv"][1][0]
        self.comprobar("población, hombres y mujeres del país igual a D1", (total, hombres, mujeres), tuple(d1[0][2:5]))
        self.comprobar("grupos de edad del país igual a D2", (e0_14, e15_64, e65), tuple(d2[4:7]))
        self.comprobar("índice de envejecimiento igual a D2", round(e65 / e0_14 * 100, 1), float(d2[7]))
        self.comprobar("población por operativo igual a D3", (operativo[2], operativo[3], operativo[1]), tuple(d3[3:6]))
        self.comprobar("viviendas censadas igual a la cifra oficial", viv[2] + viv[3], 7642716)
        self.comprobar("hogares censados igual a la cifra oficial", hogares, 6596527)
        tenencia = self.q(f"select count(*) filter (where p12_tenencia_viv in (1, 2)), count(*) from {H} where p12_tenencia_viv > 0")[0]
        self.comprobar("hogares en vivienda propia igual a 61,1 %", round(tenencia[0] / tenencia[1] * 100, 1), 61.1)
        p7 = next(f for f in self.tab["P7_3.csv"][1] if entero(f[0]) == 0 and "Total" in str(f[2]))
        self.comprobar("escolaridad promedio (total y 18+) igual a P7", (round(escolaridad, 1), round(escolaridad18, 1)), (float(p7[3]), float(p7[4])))

        regiones = self.q(
            f"""select region, count(*), count(*) filter (where sexo = 1), count(*) filter (where sexo = 2),
                       count(*) filter (where area = 1), count(*) filter (where edad_quinquenal >= 65),
                       count(*) filter (where edad_quinquenal < 15), count(*) filter (where p25_lug_nacimiento = 3),
                       count(*) filter (where p25_lug_nacimiento <> -99)
                from {P} group by 1 order by 1"""
        )
        viv_reg = dict(self.q(f"select region, count(*) from {V} where tipo_operativo in (2, 3) group by 1"))
        hog_reg = dict(self.q(f"select region, count(*) from {H} where tipo_operativo = 2 group by 1"))
        malas = [r[0] for r in regiones if tuple(r[1:4]) != tuple(d1[r[0]][2:5])]
        self.comprobar("regiones cuya población por sexo difiere de D1", malas, [])
        cuerpo_reg = [
            (r[0], self.regiones[r[0]], miles(r[1]), pct(r[1], total), pct(r[4], r[1]), dec(r[5] / r[6] * 100), pct(r[7], r[8]),
             miles(viv_reg[r[0]]), miles(hog_reg[r[0]]))
            for r in regiones
        ]

        md = [
            "# Resumen del Censo 2024 de Chile",
            "",
            "Cifras calculadas por `scripts/construir_contexto.py` desde los microdatos, con las definiciones del manual del INE.",
            "Al generarlas se comprobó que población por sexo y región, grupos de edad, operativos, viviendas, hogares y tenencia coinciden con los tabulados oficiales.",
            "Los porcentajes excluyen la no respuesta (`-99`) del denominador, como hace el INE.",
            "",
            "## País",
            "",
            tabla_md(
                ["Indicador", "Valor"],
                [
                    ("Población censada", miles(total)),
                    ("Hombres", f"{miles(hombres)} ({pct(hombres, total)} %)"),
                    ("Mujeres", f"{miles(mujeres)} ({pct(mujeres, total)} %)"),
                    ("Hombres por cada 100 mujeres", dec(hombres / mujeres * 100)),
                    ("Población urbana", f"{miles(urbana)} ({pct(urbana, total)} %)"),
                    ("Población rural", f"{miles(total - urbana)} ({pct(total - urbana, total)} %)"),
                    ("0 a 14 años", f"{miles(e0_14)} ({pct(e0_14, total)} %)"),
                    ("15 a 64 años", f"{miles(e15_64)} ({pct(e15_64, total)} %)"),
                    ("65 años o más", f"{miles(e65)} ({pct(e65, total)} %)"),
                    ("Índice de envejecimiento (65+ por cada 100 de 0 a 14)", dec(e65 / e0_14 * 100)),
                    ("Relación de dependencia total", dec((e0_14 + e65) / e15_64 * 100)),
                    ("Mediana de edad (sin las 51 comunas con edad suprimida)", dec(mediana, 0)),
                    ("Personas en viviendas particulares", miles(operativo[2])),
                    ("Personas en viviendas colectivas", miles(operativo[3])),
                    ("Personas en situación de calle", miles(operativo[1])),
                    ("Viviendas censadas", f"{miles(viv[2] + viv[3])} ({miles(viv[2])} particulares y {miles(viv[3])} colectivas)"),
                    ("Hogares censados", miles(hogares)),
                    ("Personas por hogar", dec(operativo[2] / hogares)),
                    ("Hogares unipersonales", f"{pct(unipersonales, hogares)} %"),
                    ("Hogares con jefatura mujer", f"{pct(jefas[0], jefas[1])} %"),
                    ("Hogares con acceso a internet", f"{pct(*internet)} %"),
                    ("Hogares en vivienda propia (pagada o pagándose)", f"{pct(*tenencia)} %"),
                    ("Población nacida fuera de Chile", f"{miles(inmig[0])} ({pct(*inmig)} %)"),
                    ("Se considera perteneciente a un pueblo indígena u originario", f"{miles(pueblos[0])} ({pct(*pueblos)} %)"),
                    ("Se considera afrodescendiente", f"{miles(afro[0])} ({pct(*afro)} %)"),
                    ("Años de escolaridad promedio, toda la población con dato", dec(escolaridad)),
                    ("Años de escolaridad promedio, 18 años o más", dec(escolaridad18)),
                    ("Alfabetización, 15 años o más", f"{pct(*alfabet)} %"),
                    ("Personas de 5 años o más con discapacidad", f"{miles(disc[0])} ({pct(*disc)} %)"),
                ],
            ),
            "",
            "## Regiones",
            "",
            "El orden es por código; la numeración no sigue la geografía (15 es Arica y Parinacota, 13 la Metropolitana, 16 Ñuble).",
            "",
            tabla_md(["Cód.", "Región", "Población", "% país", "% urbana", "Índice envej.", "% nacida fuera", "Viviendas", "Hogares"], cuerpo_reg),
            "",
            "## Distribuciones nacionales",
            "",
        ]
        md += self.frecuencia("personas", "p23_est_civil", titulo="Estado civil o conyugal")
        md += self.frecuencia("personas", "cine11", titulo="Nivel educativo alcanzado (CINE 2011)")
        md += self.frecuencia("personas", "sit_fuerza_trabajo", titulo="Situación en la fuerza de trabajo (15 años o más)")
        md += self.frecuencia("personas", "p40_cise_rec", titulo="Situación en el empleo (personas ocupadas)")
        md += self.frecuencia("personas", "p45_medio_transporte", titulo="Medio de transporte al trabajo")
        md += self.frecuencia("personas", "p31_religion_rec", titulo="Religión o credo")
        md += self.frecuencia("personas", "p28_pueblo_pert", titulo="Pueblo indígena u originario al que pertenece")
        md += self.frecuencia("hogares", "tipologia_hogar", "tipo_operativo = 2", titulo="Tipología de hogar")
        md += self.frecuencia("hogares", "p12_tenencia_viv", "tipo_operativo = 2", titulo="Tenencia de la vivienda")
        md += self.frecuencia("viviendas", "p2_tipo_vivienda", "tipo_operativo = 2", titulo="Tipo de vivienda particular")
        md += self.frecuencia("viviendas", "p3b_estado_ocupacion", "tipo_operativo = 2", titulo="Estado de ocupación de las viviendas particulares")
        md += self.frecuencia("viviendas", "indice_hacinamiento", "tipo_operativo = 2", titulo="Índice de hacinamiento")
        (self.salida / "resumen.md").write_text("\n".join(md) + "\n", encoding="utf-8")


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    datos, salida = Path(sys.argv[1]), Path(sys.argv[2])
    salida.mkdir(parents=True, exist_ok=True)
    c = Constructor(datos, salida)
    for paso in (c.diccionario, c.territorios, c.agregados, c.tabulados, c.documentos, c.resumen):
        print(f"{paso.__name__}:")
        paso()
    if c.fallas:
        sys.exit(f"\n{len(c.fallas)} verificaciones fallaron: {c.fallas}")
    print("\nContexto generado y todas las verificaciones pasaron.")


if __name__ == "__main__":
    main()
