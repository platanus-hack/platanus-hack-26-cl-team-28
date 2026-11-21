# Motor de simulación

Servidor HTTP que hace responder a los agentes. Cada agente es una persona real de 14 años o más del Censo
2024, con datos de Casen y opiniones de la Encuesta CEP imputados (ver `contexto/chile/README.md`), ubicada en
el centro de su comuna (`contexto/geo/comunas_centroides.csv`).

    cd backend
    uv run python -m servidor                          # http://127.0.0.1:8787, con la tabla de agentes
    LOTE=20 CONCURRENCIA=50 uv run python -m servidor  # lo que se usa en la demo
    python3 -m servidor                                # sin DuckDB: solo biblioteca estándar y el archivo fijo

## De dónde salen los agentes

De `data/agentes/` (ver `contexto/chile/agentes.md`): 1.546.322 agentes que representan a las 15.463.163
personas de 14 años o más, uno por cada 10. Esa tabla está en el repositorio. En cada consulta, `poblacion.py`:

1. Filtra la tabla con los filtros de la interfaz (región, edad, género, ingreso, educación, posición política).
2. Sortea hasta el máximo pedido entre quienes los cumplen, en proporción a cuántas personas representa cada uno.
3. Arma el perfil de cada elegido con la misma función del banco de pruebas (`scripts/personas_muestra.py`).

El sorteo es fijo: los mismos filtros dan siempre las mismas personas, así que la caché de respuestas sirve, y
la muestra de 250 está contenida en la de 2.000. Filtrar una región y pedir 2.000 entrega 2.000 personas de esa
región, no las pocas que le tocarían en una muestra nacional.

Hoy cada agente es una persona elegida al azar dentro de un grupo de 10 parecidas. Más adelante será el
arquetipo de un cluster; eso se cambia en `scripts/reducir_poblacion.py` y el servidor no se toca, porque ya
sortea según la columna `representa`.

Si falta DuckDB o la tabla, y siempre con la corrida grabada, se usan las 2.000 personas de
`data/pruebas/poblacion/al_azar_2000.jsonl`, filtradas en memoria.

## Motores

Se elige solo, en este orden, o con `MOTOR=local|api|claude|grabado`:

| Motor | Cuándo | Velocidad |
|---|---|---|
| Modelo local | `LLAMA_URL` definida (llama-server de `scripts/servir_modelo.sh`). Una persona por llamada. | La del modelo local |
| API de Anthropic | `ANTHROPIC_API_KEY` definida y paquete `anthropic` instalado. Haiku 5.5 sin razonamiento previo. | La más rápida; para el despliegue |
| CLI de Claude Code | `claude` en el PATH con sesión iniciada. Haiku por `claude -p`, un proceso por lote. | 1.000 agentes en unos 30 s con 50 procesos (unos 7 GB de RAM) |
| Corrida grabada | Sin red ni credenciales. Repite respuestas reales de Haiku 5.5 a la política de sala cuna. | Inmediata; se rotula "Corrida grabada" |

## Cómo responde un agente

El método es el de `scripts/probar_modelo.py`, y no está copiado: `metodo.py` importa de ese script las
instrucciones, las seis preguntas (`PREGUNTAS`) y la función que arma los mensajes. Si se cambian allá, el
servidor usa lo nuevo al reiniciar (y la caché se invalida sola).

Lo que lee el modelo de cada persona es su perfil general: nueve secciones en segunda persona (quién es,
educación y trabajo, hogar, vivienda, situación económica, salud y redes, posición política, cómo ve el país
y confianza en instituciones), unos 1.100 tokens. No depende del tema, así que sirve para cualquier propuesta.
Los menores de 18 no traen las secciones políticas, porque la CEP entrevista desde esa edad; traen el tipo de
colegio al que van. A la interfaz no viaja el perfil completo, solo un resumen corto (`atributos`).

Cada persona responde las seis preguntas con un entero de 1 a 7, sin texto. La interfaz clasifica con la
primera pregunta ("¿Estarías de acuerdo con que se implemente esta política en tu región?"): 5 a 7 a favor,
4 indecisa, 1 a 3 en contra. Las otras cinco se ven en la ficha de cada persona.

Diferencias con el banco de pruebas, a propósito:

- **Lotes.** Con Claude van `LOTE` personas por llamada (20 en la demo), como en las pruebas con subagentes.
  `INSTRUCCION_LOTE` en `motor.py` es lo único que se agrega a las instrucciones: que vienen varias personas y
  que se respondan por separado. `LOTE=1` pregunta de a una. Con el perfil general, un lote de 20 son unos
  22.000 tokens de entrada.
- **Sin pregunta de control con Claude.** El banco parte la encuesta con una pregunta de control porque, en el
  modelo local, la primera respuesta casi no depende del perfil. Con Claude sí depende, así que no se usa.
- **Modelo local.** Con `LLAMA_URL=http://127.0.0.1:8080` el servidor usa llama-server con la misma función
  `encuestar` del script: una persona por llamada, con su gramática y su pregunta de control. Es el método del
  banco sin cambios. El perfil general necesita unos 2.560 tokens de contexto por slot.
- **Las respuestas de un lote no son independientes.** En las pruebas, el promedio de un mismo texto cambió
  unos 0,16 puntos (en la escala de 1 a 7) de un lote a otro. Para comparar variantes con rigor, el banco
  hace que el mismo subagente conteste todas (`scripts/lotes_agentes.py --juntas`); el servidor pregunta cada
  variante por separado, que es más rápido y sirve para la demo.

## Frases, iteraciones y documentos

- **Frases.** No son parte de la encuesta. Después de que un lote responde, a dos de sus personas se les pide,
  en una llamada aparte, la frase con que explicarían lo que ya respondieron (`SISTEMA_VOCES`). Las notas no
  se tocan. Llegan a la interfaz como evento `voces`. Con el modelo local no hay frases.
- **Iteraciones.** Al terminar las variantes escritas, un agente (Sonnet) toma la variante con más apoyo, las
  medias de las seis preguntas y las frases disponibles, y redacta una versión nueva con un título corto y
  qué cambió. Se pregunta a los mismos agentes con el mismo método.
- **Documentos.** Un documento subido (`.txt`, `.md`, `.html`, `.docx` o `.pdf` con `pdftotext`) se lee entero;
  si pasa de 3.500 caracteres, Sonnet lo resume en unas 220 palabras y eso es lo que leen los agentes.

## Corrida grabada

La grabación (`data/pruebas/sala_cuna/resultados_haiku55_2000_20x100.jsonl`) es anterior al perfil general:
Haiku respondió cinco preguntas, con el perfil corto de entonces, y solo había adultos. Se repite tal cual:
el servidor informa cinco preguntas y responden 1.856 de los 2.000 agentes; los menores de 18 y quienes
entraron después no tienen respuesta. Para volver a grabar con el método actual hay que hacer una corrida en
vivo con todos los agentes y guardar sus respuestas con el formato de ese archivo.

## Validación

Sin calibrar. Con el método anterior y 200 agentes, la rebaja del TAG dio 32 % a favor contra 55 % en Cadem
(octubre de 2026); con el perfil general todavía no se ha repetido. En Sala Cuna, con el perfil con opiniones
de la CEP, Haiku dio 55 % de acuerdo contra 72 a 74 % en Cadem y Criteria: trata la medida como de izquierda
(97 % de acuerdo en la izquierda y 17 % en la derecha). La interfaz muestra la comparación tal cual sale.

`datos-pruebas/`, en la raíz, tiene 140 casos con encuesta real publicada para ampliar esta comparación, y
`data/pruebas/sala_cuna/benchmarks.json` las cifras de Sala Cuna que usa `scripts/comparar_variantes.py`.

## Caché

`data/cache/respuestas.jsonl` guarda las seis notas (y la frase, si la tiene) por política, agente, modelo y versión de las instrucciones.
Repetir una pregunta no vuelve a gastar y llega en segundos (la interfaz igual la muestra encenderse). Cambiar
las instrucciones invalida la caché sola. `data/` no se versiona.

## Rutas

    GET  /api/estado                  motor, modelo, población disponible y las preguntas de la encuesta
    POST /api/muestra                 {filtros, tamano}: filtra la población y sortea. Devuelve id, cuántos cumplen
                                      los filtros, a cuántas personas representan y los agentes elegidos
    GET  /api/agentes                 la muestra sin filtros, como lista (por compatibilidad)
    POST /api/documentos              cuerpo: el archivo; cabecera X-Nombre
    POST /api/corridas                {casos:[{id,letra,texto,documento?}], muestra:id, agentes?:[índices], iteraciones}
    GET  /api/corridas/<id>/eventos   text/event-stream
    POST /api/corridas/<id>/cancelar
