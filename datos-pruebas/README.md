# Datos de prueba de What If Chile

Banco de referencias externas para evaluar respuestas de agentes sobre políticas y temas públicos en Chile. La edición inicial contiene **140 casos en 14 áreas**, **54 cortes de segmento**, **5 resultados observados** y **20 recursos de ampliación**. Las fuentes citadas en los casos cubren 2014–2026.

| Archivo | Contenido |
| --- | --- |
| `encuestas/*.jsonl` | Un caso por línea, agrupado por área. Incluye acuerdo, preferencias, percepciones, satisfacción y dos resultados de votaciones reales. |
| `fuentes.json` | 28 fichas con URL, período, método, población, tamaño muestral publicado y enlaces a microdatos o tabulados cuando están identificados. |
| `segmentacion.jsonl` | Resultados publicados por región, zona, edad, sexo o grupo socioeconómico. Se enlazan con `caso_id`. |
| `resultados-observados.jsonl` | Indicadores de estudios y registros administrativos tras aplicar medidas. Incluye diseño, ventana, población y unidad. |
| `fuentes-ampliacion.jsonl` | Catálogo de archivos de encuestas, bases públicas, buscadores de proyectos, evaluaciones y papers metodológicos. |
| [`benchmark-politicas-chile.json`](benchmark-politicas-chile.json) | Exploración previa: resultados agregados de GPT-6 Luna en 111 preguntas, con referencias publicadas, porcentajes simulados, datos muestrales y métricas. |

## Cómo leer un caso

- `id` identifica el ítem dentro del banco. El archivo indica su área.
- `familia` agrupa ítems relacionados. Úsala junto con `fuente_id` y una revisión temática para evitar comparar variantes de una misma medida en conjuntos distintos.
- `enunciado` resume el ítem en lenguaje para el simulador. `contexto` conserva el encuadre cuando está registrado. Para una réplica estricta, toma el texto, el orden y las alternativas del cuestionario original indicado en `localizador`.
- `tipo` distingue `acuerdo`, `preferencia`, `efecto_percibido`, `percepcion`, `satisfaccion` y `voto_observado`. Un efecto percibido es un juicio de la persona encuestada. Los efectos medidos tienen su propio indicador y unidad.
- `respuestas` contiene **porcentajes publicados**, de 0 a 100, por categoría. Algunos comunicados solo publican parte de la distribución. `resto_informado_por_fuente` indica qué alternativas completan el total cuando la fuente lo especifica sin desglosarlas. Un resto de «No responde» se conserva como tal. Las cifras publicadas pueden diferir de 100 por redondeo.
- `segmento` modifica el universo de un caso. En los cortes de `segmentacion.jsonl`, la fuente es la del caso padre. `n_total` corresponde al estudio completo y puede diferir del denominador de un ítem o corte. Un `null` indica que el tamaño no se ha transcrito.
- `uso` conserva la exposición conocida del equipo. `calibracion_previa` marca TAG, diésel y condena en casa. `relacionado_con_calibracion` marca sus baterías y variantes cercanas. `candidato` admite selección posterior para desarrollo o evaluación. Las referencias son públicas y la exposición del modelo durante entrenamiento se desconoce.

Para interpretar las diferencias entre Luna y las encuestas, consulta la [auditoría de contexto del benchmark de 111 preguntas](contexto-benchmark-luna.md). Registra qué marco de la encuesta y qué antecedentes contemporáneos recibió el modelo en los casos revisados.

En el JSON del benchmark, `casos` contiene los resultados por pregunta y `metricas` contiene los resúmenes globales y por fuente. Las claves `archivos` y `sha256_archivos` identifican los archivos comprimidos de votos simulados y perfiles de la exportación local.

## Consultas sin enviar referencias al modelo

Este ejemplo extrae solo información del lado de la pregunta. Es útil al separar la generación de la corrección.

```sh
jq -c 'select(.tipo == "acuerdo" and .uso == "candidato")
  | {id, familia, enunciado, contexto, segmento}' encuestas/vivienda.jsonl
```

Para revisar qué publicó la fuente, por ejemplo en la rebaja del TAG:

```sh
jq 'select(.id == "c698-tag") | {respuestas, fuente_id, localizador}' encuestas/transporte.jsonl
jq '.["cadem-698"]' fuentes.json
```

Los enlaces apuntan a informes, cuestionarios o bases de sus respectivas entidades. La carpeta contiene resultados agregados y referencias a las bases, en UTF-8.
