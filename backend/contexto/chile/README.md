# Población completa de Chile, de 14 años o más

`data/chile/` tiene a las 15.463.163 personas de 14 años o más y los 6.596.527 hogares del Censo 2024, uno por uno, con lo que el censo no pregunta imputado desde la Encuesta Casen 2024 y, para los 14.466.767 adultos, sus opiniones imputadas desde la Encuesta CEP N° 96. Es lo mismo que la muestra del 1 % (`data/muestra/`), sin sortear: cada fila es una persona.

| Archivo | Filas | Contenido |
|---|---|---|
| `chile.parquet` | 15.463.163 | Todo junto: una fila por persona de 14 o más con su hogar, su vivienda, lo imputado desde Casen y sus opiniones (229 columnas, 0,9 GB). |
| `personas.parquet` | 15.463.163 | Lo del censo y lo imputado desde Casen por persona de 14 o más. |
| `hogares.parquet` | 6.596.527 | Todos los hogares, con su vivienda, su composición y lo imputado desde Casen. |
| `actitudes.parquet` | 14.466.767 | Las opiniones de la CEP de cada persona de 18 años o más. |

## Menores de 14 y menores de edad

- **Los 3.017.269 menores de 14 años no son filas.** Siguen contando en su hogar: `hogares` trae `n_personas` (todos los integrantes), `menores_de_14`, `edades_menores` (lista con la edad de cada menor de 18), `edades_hijos_jefatura`, `mayores_65` y `dependientes`. Así el perfil de una madre sigue diciendo que vive con un niño de 3 años.
- **Los 996.396 menores de 14 a 17 años sí son filas**, sin opiniones: la CEP entrevista desde los 18.
- **Tipo de colegio:** `dependencia_colegio` dice a qué tipo de colegio va cada menor de 14 a 17 que asiste a clases (1 municipal, 2 particular subvencionado, 3 particular pagado, 4 administración delegada, 5 servicio local de educación). El censo no lo pregunta: se imputa desde Casen según el decil del hogar, la región y la zona.
- **El identificador de persona** se asigna sobre todas las personas del censo, así que no es correlativo.

Las columnas son las de la muestra: están descritas en `contexto/muestra/README.md` (censo y Casen) y `contexto/muestra/actitudes.md` (CEP). Las llaves también se llaman igual, `id_persona_muestra` e `id_hogar_muestra`, para que los mismos scripts sirvan con la muestra y con la población.

`data/agentes/` es la versión reducida que usa el motor del sitio: 1 de cada 10 personas, agrupadas por tipo político, comuna, sexo y edad, con la columna `representa` y las de los niveles más reducidos (1 por cada 100, 1.000 y 10.000). Esa sí está en el repositorio; ver `agentes.md`.

## Qué es dato y qué es imputado

- **Del censo (observado):** edad, sexo, comuna, parentesco, educación, actividad, vivienda y todo lo demás que pregunta el cuestionario. Es el registro real y anonimizado de esa persona.
- **De Casen (imputado):** ingresos, pobreza, previsión de salud, categoría ocupacional, contrato, cotización, redes de apoyo, inseguridad alimentaria, discriminación. Es el valor de un hogar o una persona parecida de Casen.
- **De la CEP (imputado):** posición política, evaluación del gobierno, confianza en instituciones y las demás opiniones. Son las de un entrevistado parecido.

Lo imputado sirve para que el conjunto se parezca a Chile, no para afirmar nada de una persona en particular. Entre 18 millones de filas hay solo 78.654 hogares de Casen y 1.466 entrevistados de la CEP repetidos muchas veces: la variedad de lo imputado es la de las encuestas.

## Validación

`validacion.md` compara la población con sus tres fuentes. En resumen:

- **Censo:** están todas las personas de 14 años o más y todos los hogares de las 346 comunas, ningún dato observado cambió y los hogares conservan a sus 18.339.655 integrantes.
- **Casen:** las distribuciones de lo imputado calzan a 1,3 puntos porcentuales en el país; la pobreza calza a 1,4 puntos en cada región y a 1,8 en cada tramo de edad; el tipo de colegio calza a 1,0 punto en cada quintil de ingreso; las correlaciones difieren en promedio 0,015.
- **CEP:** las 54 opiniones calzan dentro del margen de error de la encuesta (2,8 puntos) y las correlaciones entre opiniones difieren en promedio 0,017.

## Límites

- **La composición es la del censo.** El censo registra menos ocupados y más trabajadores independientes que Casen, y más católicos que la CEP. La imputación respeta lo que el censo dice de cada persona, así que la población tiene, por ejemplo, 49,7 % de empleados del sector privado entre los ocupados, cuando Casen dice 59,4 %.
- **Entre Casen y la CEP no hay validación posible.** Ninguna fuente mide a la vez el ingreso y las opiniones. Esa relación existe solo a través del sexo, la edad, la educación, la zona, la actividad y el nivel socioeconómico.
- **Bajo la región, lo imputado es débil.** Casen es representativa por región y la CEP solo del país. Lo del censo sí vale por comuna. El ingreso es la excepción: cada hogar toma primero un ingreso tentativo de un hogar de Casen de su misma comuna, y después se calibra con su región, así que el quintil V de cada comuna calza con Casen (correlación de 0,99 en las 147 comunas con al menos 300 casos; `validacion.md`, «Por comuna») y cada región sigue igual a Casen. Hereda el ruido de Casen: en las comunas con pocos casos es una estimación débil, y en las que no tienen 10 hogares de una composición se usa la distribución de su región.
- **Fechas distintas.** El censo es de marzo a julio de 2024, Casen de noviembre de 2024 a febrero de 2025 y la CEP de abril y mayo de 2026.
- **Personas fuera de hogares** (viviendas colectivas y situación de calle): no tienen datos de Casen.

## Uso

```sh
uv run python -I scripts/consulta.py "select region, round(100 * avg((aprueba_gobierno = 1)::int), 1) from chile where edad >= 18 and aprueba_gobierno > 0 group by 1 order by 1"
uv run python -I scripts/consulta.py "select dependencia_colegio, count(*) from chile where edad between 14 and 17 group by 1 order by 1"
uv run python -I scripts/personas_muestra.py data/chile/chile.parquet data/pruebas/poblacion/regiones_500.jsonl --por-region 500
```

Las vistas `chile`, `chile_personas`, `chile_hogares` y `chile_actitudes` están en `scripts/consulta.py`. Para reconstruir y volver a validar (unos 4 minutos):

```sh
uv run python -I scripts/construir_poblacion.py data/censo2024 data/casen2024 data/cep96 data/chile
uv run python -I scripts/validar_poblacion.py data/chile data/censo2024 data/casen2024 data/cep96 contexto/chile
```

Fuentes: INE, Censo de Población y Vivienda 2024; Ministerio de Desarrollo Social y Familia, Encuesta Casen 2024; Centro de Estudios Públicos, Encuesta CEP N° 96, abril-mayo 2026.
