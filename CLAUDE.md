# platanus-sociologia

Este proyecto tiene descargado el **Censo de Población y Vivienda 2024 de Chile** (INE), el último censo del país. Antes de buscar cifras en la web, consulta lo que hay aquí.

## Qué hay

| Ruta | Contenido |
|---|---|
| `contexto/censo2024/resumen.md` | Cifras nacionales y regionales ya calculadas y verificadas. Empieza por aquí. |
| `contexto/censo2024/diccionario.md` | Las 106 variables de los microdatos con sus categorías y conteos. |
| `contexto/censo2024/codigos-territoriales.md` | Regiones, comunas y países. |
| `contexto/censo2024/consultas.md` | Consultas de ejemplo y recetas de indicadores. |
| `contexto/censo2024/tabulados.md` | Índice de los 107 cuadros oficiales del INE (región y comuna). |
| `contexto/censo2024/diccionario-agregados.md` | Variables de los datos bajo el nivel comunal. |
| `contexto/censo2024/documentos.md` | Índice de manuales, notas técnicas y cuestionarios en texto (`docs/*.txt`). |
| `data/censo2024/microdatos/` | `personas`, `hogares` y `viviendas` en Parquet (18,5 M, 6,6 M y 7,7 M de filas). |
| `data/censo2024/agregados/` | Conteos por manzana-entidad, zona-localidad, entidad urbana y aldea (CSV). |
| `data/censo2024/tabulados_csv/` | Cada cuadro oficial como CSV, más su nota de presentación. |
| `data/censo2024/docs/` | PDF y xlsx originales. `MANIFEST.json` registra URL, md5 y fecha de cada descarga. |

`data/` no se versiona, salvo `data/pruebas/` (resultados de las pruebas de modelos, que no se pueden reconstruir). El resto se reconstruye con:

```sh
uv run python -I scripts/descargar_censo.py data/censo2024
uv run python -I scripts/construir_contexto.py data/censo2024 contexto/censo2024
```

El segundo script regenera `contexto/` y falla si los microdatos dejan de coincidir con las cifras oficiales.

## Casen 2024 y muestra del 1 %

Además del censo hay otras dos fuentes:

| Ruta | Contenido |
|---|---|
| `data/casen2024/casen_2024.parquet` | Encuesta Casen 2024 completa: 218.367 personas, 881 variables (ingresos, previsión, trabajo, salud, redes). El libro de códigos está en `data/casen2024/docs/`. Es una encuesta: toda estimación se pondera con `expr`, y es representativa por región y área, no por comuna. |
| `data/muestra/muestra.parquet` y `muestra.csv` | Muestra del 1 % de Chile en una sola tabla: 184.879 personas, cada una con los datos de su hogar y vivienda. Registros del censo con datos de Casen imputados por emparejamiento estadístico. |
| `data/muestra/personas.parquet` y `hogares.parquet` | La misma muestra separada en personas y hogares (65.965). Usa `hogares` para contar hogares. |
| `contexto/muestra/README.md` | Cómo se construyó la muestra, sus columnas y sus límites. Léelo antes de usarla. |
| `contexto/muestra/validacion.md` | Comparación de la muestra con el censo y de lo imputado con Casen. |

En la muestra cada fila vale por 100 personas y no hay ponderadores. Las columnas del censo son datos observados; las que vienen de Casen (decil de ingreso, previsión, etc.) son valores plausibles sorteados, no datos de esa persona. Se reconstruye con:

```sh
uv run python -I scripts/descargar_casen.py data/casen2024
uv run python -I scripts/construir_muestra.py data/censo2024 data/casen2024 data/muestra contexto/muestra
```

## Cómo consultar

```sh
uv run python -I scripts/consulta.py "select nombre_comuna, poblacion from comunas order by 2 desc limit 10"
```

`scripts/consulta.py` abre DuckDB con estas vistas: `personas`, `hogares`, `viviendas`, `etiquetas`, `comunas`, `territorios`, `territorios_especificos`, `manzana_entidad`, `zona_localidad`, `urbanos`, `aldeas`, `casen`, `muestra`, `muestra_personas`, `muestra_hogares`, `etiquetas_casen`. Muestra hasta 200 filas; `--todo` las muestra todas y `--csv` entrega CSV completo.

Si una cifra ya está en un tabulado oficial, cítala desde ahí (`data/censo2024/tabulados_csv/`) en vez de recalcularla.

## Reglas para no equivocarse

- **Llaves**: `viviendas(id_vivienda)`, `hogares(id_vivienda, id_hogar)`, `personas(id_vivienda, id_hogar, id_persona)`.
- **Operativos**: `tipo_operativo` vale 1 para personas en situación de calle, 2 para viviendas particulares y 3 para viviendas colectivas. Las tablas `viviendas` y `hogares` traen filas de relleno para los operativos 1 y 3. Para contar hogares usa `tipo_operativo = 2` (6.596.527). Para contar viviendas usa `tipo_operativo in (2, 3)` (7.642.716).
- **Valores especiales**: `-99` es no respuesta y se excluye del denominador de los porcentajes; `-66` es un valor suprimido por anonimización; `NULL` es no aplica. Nunca promedies una columna sin filtrar los negativos.
- **Edad**: tiene tope en 85 y vale `-66` en las 51 comunas con menos de 6.000 personas (`comuna_bajo_umbral = 1`). Para grupos de edad usa `edad_quinquenal` (0, 5, ..., 85), que está completa.
- **Geografía**: los microdatos llegan solo hasta comuna y área urbana o rural (`area`: 1 urbano, 2 rural). Bajo la comuna hay que usar los datos agregados. `comuna // 1000` es la región. Los códigos de región y provincia se pisan: al unir con `territorios` filtra por `nivel`.
- **Variables sensibles** (pueblo originario, afrodescendencia, lengua indígena, religión, género): se suprimen las categorías con menos de 50 casos en la comuna. Las versiones resumidas (`p28_autoid_pueblo`, `p29_afrodescendencia_rec`, `p30_lengua_indigena_rec`, `p31_religion_rec`) no tienen supresión; `div_genero` sí, en 1,28 M de registros.
- **Países**: solo se distinguen Argentina, Perú, Bolivia, Colombia, Venezuela y Haití; el resto va por continente.
- **Comparar con 2017**: el Censo 2024 es de derecho (residencia habitual) y los anteriores fueron de hecho. Lee `docs/N3_Nota_Tecnica_Comparacion_Poblacion_CPV2024.txt` antes de comparar.
- **Definiciones**: los indicadores oficiales (hacinamiento, déficit habitacional, tipología de hogar, migración interna, etc.) están definidos con código R en el capítulo 7 de `docs/manual_uso_microdatos_censo2024.txt`. Úsalas tal cual.
- **DuckDB 2.x en Python**: las relaciones ya no tienen `fetchone()`; usa `con.execute(sql).fetchall()`.

## Referencia y licencia

El levantamiento fue del 9 de marzo al 31 de julio de 2024. Los microdatos se publicaron el 4 de diciembre de 2025.

Los datos son del INE, bajo licencia CC BY-SA 4.0. Al publicar algo derivado, cita «Fuente: INE, Censo de Población y Vivienda 2024» e indica si hubo cambios.

Quedó sin descargar: la cartografía (GeoParquet, GPKG y GDB, 0,4 a 0,8 GB por formato), los microdatos en CSV y Redatam, y los xlsx por comuna, que repiten las bases agregadas. Todo está en `https://storage.googleapis.com/bktdescargascenso2024/`; para sumar algo, agrégalo a la lista de `scripts/descargar_censo.py`.
