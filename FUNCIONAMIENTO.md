# Funcionamiento actual del proyecto

Documento del estado del código al 22 de noviembre de 2026. Describe las funcionalidades implementadas y cómo se validan los resultados contra encuestas reales.

## 1. Propósito y alcance

El proyecto explora cómo podrían reaccionar habitantes de Chile ante una propuesta de política pública. Permite preparar una o varias versiones, seleccionar una muestra de agentes, hacerles una encuesta y visualizar respuestas y diferencias entre versiones. Los agentes tienen perfiles construidos a partir de registros censales anonimizados y atributos imputados de encuestas; sus respuestas las produce un modelo de lenguaje (Claude Haiku), con el total nacional anclado por un modelo analista (Claude Opus).

**Los resultados son una aproximación a la opinión real de la población, validada contra encuestas publicadas.** En 82 preguntas reservadas para validación, el porcentaje de acuerdo queda en promedio a 8,2 puntos de la encuesta (mediana 6,5), 7 de cada 10 preguntas quedan a ±10 puntos y la mayoría queda del mismo lado en 88 %. El detalle está en [VALIDACION.md](VALIDACION.md).

## 2. Componentes y recorrido de datos

```text
Censo 2024 + Casen 2024 + CEP 96
              ↓ preparación, imputación y reducción
      Parquet de agentes por región
              ↓ filtros y muestra
Interfaz React → servidor HTTP Python → motor elegido
       ↑               ↓                    ↓
       └──── eventos de respuestas ── modelo o caché
              ↓
       mapa y resultados
```

- `frontend/`: aplicación React, TypeScript y Vite. Usa un mapa de Chile dibujado en canvas y un cliente HTTP/SSE en `src/vivo/`.
- `backend/servidor/`: API HTTP basada en la biblioteca estándar de Python; usa DuckDB para consultar la población de Parquet y puede conectarse a distintos motores.
- `backend/scripts/`: construcción y validación de datos, preparación de perfiles, pruebas y comparaciones de modelos.
- `backend/contexto/`: diccionarios, fuentes, metodología y validaciones de las poblaciones.
- `backend/data/agentes/`: tablas regionales reducidas usadas por el servidor; `backend/data/pruebas/` contiene muestras y resultados de experimentos.
- `datos-pruebas/`: banco independiente de referencias y resultados publicados para ampliar la evaluación.

## 3. Uso desde la interfaz principal

La ruta normal abre el diseño principal «Chile se abre».

1. **Preparar propuestas.** Se escribe una propuesta y se pueden agregar variantes o adjuntar documentos. La interfaz admite hasta seis variantes escritas; el servidor admite hasta ocho casos identificados con letras A–H, incluidas las iteraciones. Hay ejemplos disponibles en el selector de muestra.
2. **Elegir personas.** Se configura el tamaño de la muestra: de 250 a 10.000 agentes, con 1.000 inicialmente. La interfaz ofrece filtros por región, comuna, edad, género, educación, ingreso, trabajo, posición política y otros parámetros de la sociedad. Se puede elegir la reducción de 1 agente por 10, 100, 1.000 o 10.000 personas.
3. **La encuesta.** Es fija y la misma para toda propuesta: apoyo, justicia, confianza en el Estado, efectividad e influencia en el hogar, de 1 a 7. Así los resultados son comparables entre propuestas y con la validación. La primera pregunta determina la postura mostrada en el mapa.
4. **Iniciar.** El navegador envía los casos, la muestra, los índices de agentes elegidos y la cantidad de iteraciones. El servidor responde con un identificador y transmite eventos conforme llegan los lotes.
5. **Explorar.** Los puntos se animan y se agrupan según su respuesta. Se pueden cambiar las variantes, acercar el mapa, consultar fichas y ver notas por pregunta y algunas frases. Durante y después de la corrida, los filtros restringen la vista a personas de la muestra ya consultada; no generan respuestas nuevas.
6. **Detener o volver.** Se puede cancelar una corrida o volver a preparar. La cancelación marca la corrida como cancelada; el trabajo ya iniciado puede tardar en terminar.

El mapa ubica a los agentes alrededor del centro de su comuna, con puntos visuales adicionales para representar densidad. No son ubicaciones domiciliarias y varios puntos del mismo agente comparten respuesta. La interfaz muestra conteos y porcentajes de agentes que respondieron, no resultados de una encuesta humana.

## 4. Datos y población

La población de referencia comprende 15.463.163 personas de 14 años o más del Censo 2024. La tabla reducida incluida en `backend/data/agentes/` contiene 1.546.322 agentes, uno por cada diez personas, y marcas de reducciones anidadas de 100, 1.000 y 10.000. Cada agente es una persona real del censo que representa a su grupo de personas parecidas: no es un promedio inventado. Se elige la que mejor mantiene las proporciones de su región (`backend/contexto/chile/agentes.md`).

El censo aporta características observadas, por ejemplo edad, sexo, comuna, educación, actividad y vivienda. Casen aporta por imputación variables como ingresos, salud y condiciones laborales. La CEP aporta por imputación posición política, evaluaciones y confianza institucional a los adultos. Las variables imputadas corresponden a donantes similares: **no son afirmaciones sobre la persona censada individual**. Algunas edades y otras variables también se imputan o derivan cuando la fuente no las publica directamente. Los menores de 14 no son agentes, aunque integran la composición del hogar; los de 14 a 17 sí pueden ser agentes y no reciben opiniones CEP.

Para una consulta, `poblacion.py` limpia filtros, selecciona el nivel de reducción, filtra los Parquet y sortea hasta el tamaño pedido según la representación de los agentes. El sorteo es determinista para los mismos filtros y sus muestras son anidadas por tamaño. El servidor conserva hasta 60 muestras recientes en memoria y memoriza perfiles construidos. La API permite hasta 10.000 agentes por muestra (`MAXIMO_MUESTRA`). Si faltan DuckDB o las tablas, se utiliza el archivo fijo de 2.000 perfiles de prueba.

La población de origen y su validación están descritas en `backend/contexto/chile/README.md`, `agentes.md` y `validacion.md`. La tabla completa de origen y los insumos necesarios para reconstruirla pueden no estar presentes en el repositorio; la tabla reducida es la que usa normalmente el sitio.

## 5. Perfil y método de respuesta

El servidor reutiliza las instrucciones y preguntas del banco en `backend/scripts/probar_modelo.py` mediante `servidor/metodo.py`. El perfil general reúne datos demográficos, hogar, educación, trabajo, economía, salud y, para adultos, política y confianza. `PERFIL` define cuánto recibe el modelo:

| Valor | Contenido |
| --- | --- |
| `tematico` | Predeterminado: núcleo de datos y hasta tres temas detectados por palabras clave en la propuesta y las preguntas. |
| `nucleo` | Conjunto reducido de atributos considerados relevantes para opiniones políticas. |
| `completo` | Perfil completo disponible. |

El archivo fijo contiene perfiles ya escritos y se envía completo. La interfaz recibe un resumen de atributos, no el perfil completo usado en el prompt.

Las cinco preguntas miden apoyo («¿Estás de acuerdo o en desacuerdo con lo que plantea el tema de la encuesta?»), justicia en el reparto de costos y beneficios, confianza en que el Estado la implemente bien, efectividad esperada e influencia en el hogar. Se responde cada una con un entero de 1 a 7. Para la primera pregunta: 1–3 se cuenta en contra, 4 como indecisión y 5–7 a favor. El modelo lee las opiniones de fondo de cada persona (rol del Estado, inmigración, seguridad, confianza en instituciones) y no su etiqueta política, para que responda por lo que piensa del tema.

Además, un modelo analista (Claude Opus, `ANCLA`) estima con una sola llamada el nivel nacional de cada propuesta, y los agentes reparten ese total entre ellos sin cambiar su orden: quién apoya y en qué región o grupo lo deciden los agentes. Corre a la par de los primeros lotes.

En Claude se envían perfiles en lotes; el modelo local consulta una persona por llamada e incluye una pregunta de control. Las variantes escritas se procesan en paralelo, y el servidor intenta recuperar respuestas faltantes y reintenta errores de lote. Puede haber respuestas ausentes; un aviso informa fallos y los porcentajes deben leerse sobre quienes efectivamente respondieron.

Las frases se solicitan por separado después de las notas a un máximo de dos personas por lote, buscando incluir apoyo y otras posturas cuando hay disponibles. Son explicaciones generadas, no citas de personas reales; no cambian las notas. El modelo local no genera estas frases.

## 6. Motores

La selección automática ocurre al iniciar el servidor, en este orden:

| Motor | Selección | Comportamiento |
| --- | --- | --- |
| Modelo local | `LLAMA_URL` configurada, o `MOTOR=local` junto con esa URL | Consulta un `llama-server` compatible, para desarrollo sin red. Responde la encuesta; no redacta iteraciones ni resume documentos largos. `TEMPERATURA` controla la temperatura. |
| API de Anthropic | Credencial `ANTHROPIC_API_KEY` y paquete `anthropic` disponibles, o `MOTOR=api` | Haiku responde; Opus ancla el nivel nacional; Sonnet redacta resúmenes e iteraciones. |
| Claude Code | CLI `claude` disponible con sesión iniciada, o `MOTOR=claude` | Lo mismo por la CLI. Es el motor del sitio publicado. |

Si no hay ningún motor disponible, el servidor no arranca: no repite respuestas guardadas. El motor en uso se ve en la interfaz y en `GET /api/estado`.

Si el navegador no logra conectar con el servidor, la interfaz entra en una **demostración** sin modelo, que se identifica como tal en pantalla.

## 7. Iteraciones y documentos

Si se activan iteraciones y el motor permite redactar, al finalizar las variantes iniciales el servidor selecciona la de mayor proporción de apoyo, espera las frases disponibles y solicita una nueva versión que conserve el objetivo y responda a objeciones. Incluye medias de las preguntas y frases de apoyo y de quienes no apoyaron. Luego consulta la nueva versión a los mismos agentes; el proceso puede repetirse hasta tres veces, sujeto al límite total de ocho casos. No garantiza mejora ni factibilidad de la propuesta. El modo local no implementa redacción.

Se aceptan archivos de texto, Markdown, HTML, DOCX y PDF. Para PDF se necesita `pdftotext` instalado y texto extraíble; no hay OCR. El límite de carga es 25 MB y se requieren al menos 40 caracteres legibles. Con motores que redactan, los textos de más de 3.500 caracteres se resumen antes de consultar a los agentes; al resumidor se le pasan como máximo los primeros 400.000 caracteres. Los documentos cortos se conservan. Con el motor local, un documento largo produce error porque ese motor no implementa redacción. Un resumen puede omitir detalles relevantes.

## 8. Resultados, comparación y validación

La interfaz muestra conteos, porcentajes, respuestas por pregunta, cambios entre variantes y fichas de agentes. Cuando hay una referencia incorporada compatible y se conserva la primera pregunta original, puede mostrar comparaciones con encuestas publicadas; no se muestra esa comparación en demostración ni al filtrar la vista. La coincidencia temática y las diferencias de pregunta, universo, fecha y método deben revisarse antes de comparar.

El motor se validó contra 164 preguntas de 27 encuestas reales de 10 entidades (unas 30 mil entrevistas, 2014 a 2026) y contra los microdatos de la Encuesta CEP 96 (1.466 entrevistas). En las 82 preguntas reservadas para validación: error medio de 8,2 puntos en el porcentaje de acuerdo, 71 % de las preguntas a ±10 puntos, 38 % a ±5, y la mayoría del mismo lado en 88 %. Por grupos, los segmentos se mueven en la misma dirección que en la realidad. Resultados, preguntas y método: [VALIDACION.md](VALIDACION.md) y `backend/data/pruebas/realidad_1000/`.

`datos-pruebas/` reúne el banco de evaluación: 140 casos en 14 áreas, cortes por segmentos, resultados observados, referencias y el benchmark de políticas.

## 9. API y transmisión de eventos

La API escucha por defecto en `127.0.0.1:8787` y devuelve JSON. No envía cabeceras CORS: el sitio la llama desde su mismo origen. Los límites de uso y la protección del sitio publicado están en `docs/backend/06-seguridad.md`.

| Método y ruta | Función |
| --- | --- |
| `GET /api/estado` | Motor y modelo, población, lote, concurrencia, preguntas y límites. |
| `POST /api/muestra` | Recibe `{filtros, tamano}` y devuelve identificador, disponibles, personas representadas y agentes. |
| `GET /api/agentes` | Muestra predeterminada sin filtros; ruta de compatibilidad. |
| `POST /api/documentos` | Cuerpo binario y cabecera `X-Nombre`; devuelve texto procesado, título y consumo. |
| `POST /api/corridas` | Recibe `casos`, `muestra`, opcionalmente índices `agentes`, `iteraciones`, `lote` y `preguntas`; devuelve ID y detalles. |
| `GET /api/corridas/<id>/eventos` | Flujo Server-Sent Events de la corrida. |
| `POST /api/corridas/<id>/cancelar` | Solicita cancelar la corrida. |
| `GET /api/historial` | Resumen de las últimas simulaciones terminadas; `vista` indica si se puede volver a ver. |
| `GET /api/historial/<id>` | Simulación guardada completa (muestra, filtros de la interfaz y eventos), para volver a mostrarla. |

Los eventos son `inicio`, `respuestas`, `voces`, `caso_listo`, `redactando`, `caso`, `aviso`, `fin` y `falla`. Los lotes de respuestas incluyen índice del agente, nota principal, frase y notas completas, además de métricas de llamadas, tokens, costo informado y tiempo. El cliente convierte `falla` en error de aplicación. El flujo conserva eventos en memoria para reconexión mientras exista el proceso; corridas y muestras no son persistentes. Lo que sí queda en disco al terminar una corrida es su resumen (`backend/data/historial/corridas.jsonl`) y, si no se detuvo, una copia comprimida de su muestra, sus filtros y sus eventos (`backend/data/historial/vistas/`, las últimas 200), con la que el historial la vuelve a mostrar.

La caché `backend/data/cache/respuestas.jsonl` persiste respuestas por política normalizada, identidad del agente y clave del modelo/método/preguntas/perfil. Repetir una consulta compatible reutiliza respuestas; al cambiar instrucciones, filtro o preguntas se modifica la clave. El archivo contiene datos derivados de las consultas y debe tratarse de acuerdo con el uso que se dé a la aplicación. No es una base de resultados ni un historial de corridas completo.

## 10. Inicio y configuración

Requisitos: Node y npm para el frontend; Python y preferentemente `uv` para el backend; dependencias del proyecto instalables desde `backend/pyproject.toml`. El proyecto declara Python 3.14 o superior. Para usar API de Anthropic hace falta instalar su paquete opcional y configurar la credencial; para el modelo local hace falta levantar un servidor compatible. PDF requiere `pdftotext`.

```bash
# Desde la raíz: arranca ambos servicios; Ctrl+C los detiene
./iniciar.sh
```

Por separado:

```bash
cd backend
uv run python -m servidor
```

```bash
cd frontend
npm install
npm run dev
```

Vite sirve la interfaz en `http://127.0.0.1:5280` y reenvía `/api` al puerto 8787. `npm run preview` usa el puerto 5281. Para una compilación contra otra API, se puede definir `VITE_API` con su URL base al compilar. `python3 -m servidor` sin dependencias puede usar la población fija.

Variables principales del servidor:

| Variable | Función |
| --- | --- |
| `MOTOR` | `local`, `api` o `claude`; si se omite, selección automática. |
| `LLAMA_URL` | URL del servidor de modelo local. |
| `ANTHROPIC_API_KEY` | Credencial de API de Anthropic. |
| `PERFIL` | `tematico`, `nucleo` o `completo`. |
| `ANCLA` | Modelo analista que estima el nivel nacional; Opus por defecto. |
| `LOTE` | Personas por lote; el servidor usa 10 por defecto y `iniciar.sh` establece 20. La API limita el valor a 1–25. |
| `CONCURRENCIA` | Número de trabajadores; 30 por defecto en el servidor y 50 desde `iniciar.sh`. |
| `TEMPERATURA` | Temperatura del motor local; 1.0 por defecto. |
| `PUERTO` | Puerto HTTP; 8787 por defecto. |
| `ABIERTO` | Si tiene valor, escucha en todas las interfaces en lugar de solo localhost. |
| `VITE_API` | Base de API para el frontend en compilación. |

## 11. Desarrollo y comprobación

```bash
cd frontend
npm test
npm run build
```

Las pruebas de Vitest cubren partes del dominio, agrupación del mapa y encuesta. El repositorio también incluye scripts de construcción y validación de población, perfiles y modelos; sus detalles y requisitos están en `backend/contexto/`, `backend/data/pruebas/README.md` y `backend/servidor/README.md`. Ejecutar un experimento con un proveedor externo puede consumir recursos o generar costos. La documentación aquí describe el comportamiento observado en el código, no certifica que todas las combinaciones de motores y dependencias se hayan ejecutado en este entorno.
