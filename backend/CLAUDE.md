# platanus-sociologia

Todo lo de este archivo es relativo a `backend/`: corre los comandos desde esta carpeta.

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

## Casen 2024, CEP y muestra del 1 %

Además del censo hay otras fuentes:

| Ruta | Contenido |
|---|---|
| `data/casen2024/casen_2024.parquet` | Encuesta Casen 2024 completa: 218.367 personas, 881 variables (ingresos, previsión, trabajo, salud, redes). El libro de códigos está en `data/casen2024/docs/`. Es una encuesta: toda estimación se pondera con `expr`, y es representativa por región y área, no por comuna. |
| `data/muestra/muestra.parquet` y `muestra.csv` | Muestra del 1 % de Chile en una sola tabla: 184.879 personas, cada una con los datos de su hogar y vivienda. Registros del censo con datos de Casen imputados por emparejamiento estadístico. |
| `data/muestra/personas.parquet` y `hogares.parquet` | La misma muestra separada en personas y hogares (65.965). Usa `hogares` para contar hogares. |
| `contexto/muestra/README.md` | Cómo se construyó la muestra, sus columnas y sus límites. Léelo antes de usarla. |
| `contexto/muestra/validacion.md` | Comparación de la muestra con el censo y de lo imputado con Casen. |
| `data/cep96/cep96.parquet` | Encuesta CEP N° 96 (abril-mayo 2026): 1.466 entrevistas, 151 variables (posición política, partido, evaluación del gobierno, confianza en instituciones). Se pondera con `pond`. El diccionario, el manual y el cuestionario están en `data/cep96/docs/`. |
| `data/muestra/actitudes.parquet` | 54 opiniones de la CEP imputadas a los 144.528 adultos de la muestra: política, economía, rol del Estado, seguridad, inmigración, familia y confianza en 15 instituciones. Se une por `id_persona_muestra`. |
| `contexto/muestra/actitudes.md` | Cómo se imputaron las actitudes, sus columnas, sus límites y la comparación con la CEP. |
| `data/chile/chile.parquet` | Población completa de 14 años o más: 15.463.163 personas del censo, una por fila, con su hogar, su vivienda, lo imputado desde Casen y, los 14,5 M de adultos, sus opiniones de la CEP. También separada en `personas`, `hogares` (todos, con la composición del hogar) y `actitudes`. Mismas columnas y llaves que la muestra. |
| `contexto/chile/README.md` y `validacion.md` | Qué es la población completa, sus límites, y su comparación con el censo, Casen y la CEP (distribuciones y correlaciones). |
| `data/agentes/region_NN.parquet` | Tabla de agentes: 1.546.322 personas que representan a las 15,5 M. Trae cuatro niveles anidados de clusterización: `representa` (1 agente por cada 10 personas, todas las filas), `representa_100`, `representa_1000` y `representa_10000` (no nulas solo en quienes quedan en ese nivel). Mismas columnas que `chile.parquet`, más `tipo_politico` (1 a 8; nulo en los menores de 18). **Sí se versiona** (unos 100 MB): es la que filtra el motor del sitio. `contexto/chile/agentes.md` la describe y la compara con la población completa. |

En la muestra cada fila vale por 100 personas y no hay ponderadores. Las columnas del censo son datos observados; las que vienen de Casen (decil de ingreso, previsión, etc.) son valores plausibles sorteados, no datos de esa persona. Se reconstruye con:

```sh
uv run python -I scripts/descargar_casen.py data/casen2024
uv run python -I scripts/construir_muestra.py data/censo2024 data/casen2024 data/muestra contexto/muestra
uv run python -I scripts/descargar_cep.py data/cep96
uv run python -I scripts/imputar_cep.py data/muestra data/cep96 contexto/muestra
uv run python -I scripts/construir_poblacion.py data/censo2024 data/casen2024 data/cep96 data/chile
uv run python -I scripts/validar_poblacion.py data/chile data/censo2024 data/casen2024 data/cep96 contexto/chile
uv run python -I scripts/reducir_poblacion.py data/chile data/agentes contexto/chile
```

Cada agente de la tabla representa a un grupo de 10 personas parecidas (y, en los niveles siguientes, a 10 representantes del nivel anterior). Los grupos se forman primero por tipo político, que es lo que más pesa en una opinión: los 1.466 entrevistados de la CEP se agrupan en 8 tipos y cada persona hereda el de su entrevistado. Hasta 1 por cada 100 cada grupo es además de una sola comuna; desde 1 por cada 1.000 ya no. El representante no es el más típico del grupo (eso borra a las minorías) ni uno al azar: es quien mejor mantiene las proporciones de la región. El orden de cada nivel está en `ORDENES` y lo que se equilibra en `EQUILIBRAR`, en `reducir_poblacion.py`; `contexto/chile/agentes.md` trae la comparación con la población. Con 1 agente por cada 10.000 personas quedan unos 1.550 en el país: sirve por región, no por comuna.

La población completa usa las mismas funciones de imputación que la muestra (`imputar_casen` en `construir_muestra.py` y el emparejamiento de `imputar_cep.py`): un cambio en el método vale para ambas. `validar_poblacion.py` termina con error si algo deja de calzar; córrelo después de cualquier cambio en la imputación. La población conserva la composición del censo, que tiene menos ocupados y más independientes que Casen: no la "corrijas" hacia la encuesta.

Las actitudes imputadas tampoco son datos de esa persona: son las de un entrevistado de la CEP con su mismo sexo, edad, educación, zona, nivel socioeconómico, actividad y religión. Al publicar algo derivado, cita también «Centro de Estudios Públicos, Encuesta CEP N° 96, abril-mayo 2026».

## Delphos: simulación de respuestas de la población

El proyecto es Delphos (Platanus Hack 2026, track Simulaciones). `contexto/delphos/framework.md` es el documento de contexto: capas del agente, encuesta, variantes A a E de Sala Cuna Universal, validación y benchmarks. Léelo antes de cambiar la encuesta o los perfiles.

El sistema debe servir para estimar respuestas en muchos contextos, no solo en uno. Por eso el perfil de cada persona es general y rico en contexto, y lo propio de un caso (textos, preguntas, cifras reales) vive en la carpeta del caso. No pongas en los scripts ni en el perfil nada que solo sirva para un tema. `data/pruebas/README.md` explica la estructura de un caso y cómo se corre.

El modelo no lee el perfil entero: `scripts/filtro_perfil.py` define qué datos se le entregan (un núcleo de 28 que va siempre, más los de los temas que toca el texto). Es el único lugar donde se decide eso. Un dato nuevo del perfil necesita su clave en `DATOS` de ese archivo y, en `personas_muestra.py`, escribirse solo si `q("clave")`; si no entra al núcleo ni a un tema, solo va con el perfil completo.

| Ruta | Contenido |
|---|---|
| `scripts/personas_muestra.py` | Saca personas de 14 años o más de la muestra o de la población completa y arma su perfil general en nueve secciones: identidad, trabajo, hogar, vivienda, economía, salud y redes, política, visión del país y confianza en instituciones. `--por-region K` estratifica y deja un `peso`; `--secciones` elige cuáles van; `--sin-actitudes` deja fuera lo imputado desde la CEP; `--filtro nucleo` y `--temas a,b` escriben el perfil reducido. |
| `scripts/filtro_perfil.py` | El filtro de datos del perfil: catálogo de los 102 datos, el núcleo, los 15 temas con sus palabras clave y `datos_para(texto, nivel)`. Sin argumentos muestra el catálogo; con archivos de texto, los temas que detecta en cada uno. |
| `scripts/analizar_influencia.py` | Mide con la CEP y con una corrida guardada qué datos pesan en una opinión política y escribe `contexto/delphos/influencia.md`, el respaldo del filtro. |
| `scripts/comparar_perfiles.py` | Pregunta a las mismas personas con el perfil completo (dos veces, para tener la vara del ruido) y con el filtrado, por el camino del sitio, y compara: índice por texto, coincidencia persona a persona y diferencias por grupo. `correr` gasta (3 llamadas por lote y texto); `informe` no. |
| `scripts/servir_modelo.sh` | Levanta `llama-server` con un modelo local en la GPU NVIDIA. |
| `scripts/construir_comunas.py` | Arma desde la cartografía del censo los polígonos simplificados de las comunas (`../frontend/src/datos/comunas.json`) y las regiones como unión de ellas (`regions` de `geografia.json`), con los que el mapa del sitio dibuja a cada persona dentro de su comuna: dentro del límite urbano (una ciudad o pueblo elegido según su población) si vive en zona urbana, y en el resto de la comuna si vive en zona rural. Valida que estén las 345 comunas de `contexto/geo/comunas_centroides.csv`. |
| `scripts/probar_modelo.py` | Aplica la encuesta con el modelo local. La encuesta es fija (`ENCUESTA`): apoyo, justicia, confianza, efectividad e influencia, de 1 a 7 y cada una con su escala, que va al lado de la pregunta en el prompt. Si el texto es una carpeta, corre cada `.md` como variante con las mismas personas y semilla. `--abiertas N` pide justificaciones y preguntas abiertas a una submuestra. |
| `scripts/lotes_agentes.py` | Para contestar la encuesta con subagentes (Claude Haiku): `preparar` arma lotes de personas con la política y las preguntas, y `reunir` junta las respuestas en un archivo de resultados. Con `--juntas`, cada subagente contesta todas las variantes para sus mismas personas. |
| `scripts/comparar_variantes.py` | Ranking de variantes con diferencias pareadas, efecto de cada atributo, desglose por región y grupo, validación contra `benchmarks.json` y coincidencia entre corridas. |
| `data/pruebas/poblacion/` | Los perfiles generales del banco de pruebas, comunes a todos los casos. `al_azar_2000.jsonl` es el respaldo del sitio cuando no puede leer la tabla de agentes. |
| `servidor/` | El motor del sitio (ver `servidor/README.md`). Saca a los agentes de `data/agentes/`: filtra y sortea en `servidor/poblacion.py`, con una cuota por región, comuna y zona proporcional a las personas que representa (si cambias el reparto, corre `uv run python -m unittest tests.test_reparto`). Los parámetros por los que se filtra (región, trabajo, posición política…) están en `servidor/sociedad.py`, cada uno con su expresión SQL sobre la tabla y su equivalente desde los grupos del perfil; si agregas o cambias uno, hazlo también en `frontend/src/vivo/sociedad.ts` (mismas claves y mismo orden de opciones) y corre `uv run python -m unittest tests.test_sociedad`. No copia el método: `servidor/metodo.py` importa de `scripts/probar_modelo.py` las preguntas, `mensajes`, `prosa_de` y `encuestar`. Si cambias sus firmas, ajusta ese archivo y prueba que el servidor arranque con un motor real (`MOTOR=claude python3 -m servidor`, en otro puerto con `PUERTO`). Ya no hay corrida grabada: sin motor no arranca. Si cambias una pregunta o una escala, cámbiala también en `frontend/src/vivo/encuesta.ts`. |
| `../datos-pruebas/` | Banco de referencias externas del equipo: 140 casos con encuesta real publicada, cortes por segmento y resultados observados. Sirve para validar; no lo mezcles con `data/pruebas/`, que son las corridas de los modelos. |
| `data/pruebas/sala_cuna/` | El caso de Sala Cuna: variantes (`variantes/`, con `atributos.json`), textos de validación, `benchmarks.json` y resultados. Sus `personas_*.jsonl` son los perfiles cortos con que se hicieron las corridas hasta el 21-11-2026. |

Reglas de este análisis:

- Desde el 21-11-2026 las instrucciones aclaran que el 4 es solo para quien no tiene opinión (`ESCALA` en `probar_modelo.py`): sin eso el modelo se refugia en el centro. Con Haiku y 200 personas, el 4 en la primera pregunta bajó de 44 % a 5 % en la rebaja del TAG y de 33 % a 3 % en la del diésel, y el resultado del diésel quedó en 71 % a favor y 26 % en contra (Cadem: 66 y 26). Los resultados anteriores a esa fecha no la tienen: no compares con ellos la proporción de indecisos.
- En el modelo local, la primera respuesta casi no depende del perfil, sea cual sea la pregunta, y las siguientes se anclan en ella. Por eso `probar_modelo.py` parte con una pregunta de control («¿Entiendes las instrucciones de esta encuesta?»), que se guarda en `control` y no entra en ningún indicador; `--sin-control` la quita. Los resultados anteriores al 21-11-2026 no la tienen: en ellos, para p1 usa las probabilidades del modelo (`distribuciones`), no la respuesta sorteada.
- Con subagentes por lotes, las respuestas de un lote no son independientes: el índice de una misma variante cambia unos 0,16 puntos de un lote a otro, tanto como la diferencia entre variantes. `comparar_variantes.py` remuestrea lotes completos cuando los resultados traen `lote`. Para comparar variantes con subagentes usa `--juntas`.
- 5 a 7 es el lado alto de la escala de cada pregunta y 1 a 3 el bajo; en p1, de acuerdo y en desacuerdo. El índice de aceptación es la media de p1 a p4 (apoyo, justicia, confianza y efectividad); p5 (influencia) no entra. Los resultados anteriores al cambio de encuesta (21-11-2026) tienen otras preguntas en p2 a p6 y una sola escala de acuerdo: solo p1 se compara.
- Se afirma ranking y dirección, no porcentajes, y solo si se mantiene entre modelos y redacciones.
- Los perfiles no traen valores de Schwartz ni personalidad: ninguna fuente los mide. No se inventan.
- Se simula desde los 14 años. Los menores de 14 no son filas de `data/chile/` ni reciben perfil, pero cuentan en la composición de su hogar (`edades_menores`, `menores_de_14`). Los de 14 a 17 no tienen opiniones de la CEP, que entrevista desde los 18; su perfil trae el tipo de colegio (`dependencia_colegio`, imputado desde Casen). La muestra del 1 % conserva todas las edades.
- Un perfil completo son unos 1.200 tokens. En el modelo local eso exige unos 2.560 tokens de contexto por slot (`scripts/servir_modelo.sh` ya lo pide) y baja la velocidad; con subagentes, lotes de 20 a 25 personas.
- El motor del sitio entrega el perfil filtrado (`PERFIL=tematico` por defecto: 390 a 650 tokens). La demografía sola predice 4 % de las opiniones de la CEP, el núcleo 16 % y el perfil completo 19 % (`contexto/delphos/influencia.md`). Se comparó con el perfil completo en un solo caso y un solo modelo (Sala Cuna, Haiku, 200 personas, 21-11-2026; `scripts/comparar_perfiles.py informe data/pruebas/sala_cuna/resultados_ab_perfil_haiku.jsonl`): el índice de aceptación y las diferencias por posición política y por niños en el hogar no cambian más que al repetir la corrida, pero no es equivalente: p5 baja 0,17, p6 sube 0,13 y p4 sube 0,09 (con la encuesta de entonces: p5 cumpliría, p6 logrará lo que se propone, p4 confianza). Una segunda corrida con subagentes (400 personas, cinco recortes del perfil; `data/pruebas/sala_cuna/resultados_atribucion_perfil_haiku.jsonl`) mostró que el filtro no cambia de forma estable la diferencia por edad en el índice (el signo se invierte entre las dos corridas), que sí hace bajar más p5 a los mayores, y que quitar `menos_estado` reduce a la mitad la distancia entre quienes quieren menos Estado y el resto; por eso ese dato pasó al núcleo después de esas corridas (las dos se hicieron con el núcleo de 27, sin él). No afirmes que da los mismos resultados en otros temas ni con el modelo local, donde tampoco se ha medido la velocidad. `PERFIL=completo` vuelve al perfil de antes. Las poblaciones de `data/pruebas/poblacion/` siguen completas.

## Cómo consultar

```sh
uv run python -I scripts/consulta.py "select nombre_comuna, poblacion from comunas order by 2 desc limit 10"
```

`scripts/consulta.py` abre DuckDB con estas vistas: `personas`, `hogares`, `viviendas`, `etiquetas`, `comunas`, `territorios`, `territorios_especificos`, `manzana_entidad`, `zona_localidad`, `urbanos`, `aldeas`, `casen`, `muestra`, `muestra_personas`, `muestra_hogares`, `etiquetas_casen`, `muestra_actitudes`, `etiquetas_cep`, `cep`, `chile`, `chile_personas`, `chile_hogares`, `chile_actitudes`, `agentes`. Muestra hasta 200 filas; `--todo` las muestra todas y `--csv` entrega CSV completo.

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

La cartografía (GeoParquet, unos 800 MB) se baja aparte, con `scripts/descargar_censo.py data/censo2024 --cartografia`: de cada región quedan solo las capas comunal y de límite urbano, en `data/censo2024/cartografia/`. Después, `uv run python -I scripts/construir_comunas.py data/censo2024/cartografia ../frontend/src/datos` regenera los polígonos del mapa. Al publicar el mapa, cita «Fuente: INE, Censo de Población y Vivienda 2024, cartografía (geometría simplificada)».

Quedó sin descargar: la cartografía en GPKG y GDB, las demás capas de la cartografía (manzanas, entidades, zonas), los microdatos en CSV y Redatam, y los xlsx por comuna, que repiten las bases agregadas. Todo está en `https://storage.googleapis.com/bktdescargascenso2024/`; para sumar algo, agrégalo a la lista de `scripts/descargar_censo.py`.
