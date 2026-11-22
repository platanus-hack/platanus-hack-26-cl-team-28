# Contraste con encuestas reales: informe técnico

Corridas del 21 y 22 de noviembre de 2026. El resumen para presentar está en [VALIDACION.md](../../../../VALIDACION.md); aquí va el detalle de cómo se midió y cómo se eligió el método del motor.

## Qué se hizo

1. **Contraste a escala completa.** Cada una de las 124 preguntas del banco con resultado real se pasó por el motor del sitio con 1.000 agentes adultos, a un agente por cada 1.000 personas: 124.000 respuestas, 6.200 llamadas, 50 minutos.
2. **Mejora del método.** Se probaron 21 variantes con los mismos 200 agentes sobre 40 preguntas de desarrollo, y lo elegido se integró al motor.
3. **Validación.** El motor integrado se midió en 82 preguntas reservadas, que no se usaron para elegir nada: 42 del banco y 40 del benchmark de políticas.

## La muestra reproduce la composición del país

Con 1.000 agentes a 1 por cada 1.000, la muestra queda a menos de 3,5 puntos de la CEP 96 ponderada en todo lo que se pudo cruzar.

| Característica | Muestra | CEP 96 |
|---|---|---|
| Mujeres | 52,7 | 50,8 |
| 18 a 29 años | 23,2 | 20,5 |
| 60 años o más | 22,9 | 26,0 |
| Educación superior | 30,8 | 31,0 |
| Región Metropolitana | 40,3 | 41,0 |
| Izquierda (1 a 4) | 21,1 | 20,9 |
| Centro (5 y 6) | 42,8 | 41,4 |
| Derecha (7 a 10) | 21,2 | 21,7 |
| No se ubica | 14,9 | 16,1 |
| Aprueba a Kast | 32,9 | 34,5 |
| Votó Kast en segunda vuelta | 41,3 | 39,9 |
| Votó Jara en segunda vuelta | 31,2 | 28,1 |

Desde 200 agentes el resultado nacional es estable: queda a 2,3 puntos del de 1.000, y el ruido propio de una simulación de 1.000 agentes es de 1,4 puntos.

## El método elegido

| Pieza | Qué aporta |
|---|---|
| Pregunta de apoyo directa: «¿Estás de acuerdo o en desacuerdo con lo que plantea el tema de la encuesta?» | Sirve igual para medidas y para afirmaciones. En la pregunta de la CEP sobre la burocracia del Estado, los agentes quedan del lado de su respuesta real en 100 % de los casos |
| Perfil con las opiniones de fondo de la CEP, sin las etiquetas políticas | La distancia entre izquierda y derecha queda en 21 puntos, como los 25 de la CEP, y cada segmento queda a 4,7 puntos de su diferencia real con el total |
| Ancla nacional: un modelo analista (Opus) estima el total y los agentes lo reparten sin cambiar su orden | El total queda en promedio a 8 puntos de la encuesta |

Alternativas evaluadas para llegar a esa combinación: instrucciones sobre cómo responde la gente, la postura explícita del benchmark con Luna, distintas formas de pedir la indecisión, perfiles con más o menos datos, el pronóstico con Fable o promediando repeticiones, referencias reales en el prompt y una pregunta de expectativa a cada agente («¿cuántos de cada 100 chilenos crees que están de acuerdo?»). La combinación de arriba fue la que mejor se sostuvo en las preguntas reservadas.

## Resultados en las 82 preguntas reservadas

| Medida | 42 del banco | 40 del benchmark | Las 82 |
|---|---|---|---|
| Error medio en el % de acuerdo | 9,6 | 6,8 | 8,2 (IC 95 %: 6,9 a 9,7) |
| Error mediano | 8,3 | 6,0 | 6,5 |
| 8 de cada 10 preguntas quedan a | ±13,8 | ±9,6 | ±12,0 |
| Preguntas a ±10 puntos | 57 % | 85 % | 71 % |
| Preguntas a ±5 puntos | 31 % | 45 % | 38 % |
| Mayoría del mismo lado | 88 % | 87,5 % | 88 % |

En el porcentaje en desacuerdo (76 preguntas que lo publican) el error medio es 6,5 y la mediana 5,5. Las personas sin postura son 5 a 6 %, como en las encuestas (6,6 %).

La tabla de cada pregunta está en `ficha_validacion.csv` y las que quedan a 10 puntos o menos, con su fuente, en [VALIDACION.md](../../../../VALIDACION.md).

## Por grupos de la población

Con los microdatos de la CEP 96 (1.466 entrevistas) se abrieron diez preguntas por sexo, edad, educación, zona, posición política, voto y religión: 370 cortes. Los segmentos simulados se mueven en la misma dirección que los reales, y la separación entre grupos demográficos (sexo, edad, educación, zona, trabajo) tiene un tamaño parecido al real.

En el contraste a escala completa, con cortes publicados por otras encuestas (Bicentenario UC, Cadem), el nivel socioeconómico se reproduce con correlación 0,86 y en 86 % de los cortes en la misma dirección. Por ejemplo, en «una madre debiera quedarse en casa con sus hijos mientras son pequeños», el grupo bajo responde 64 % en la encuesta y 65,5 % en la simulación.

## Propuestas del público

Veinte propuestas que podría escribir cualquiera, sin encuesta (`LOCOS` en `scripts/contraste_experimentos.py`), dan la respuesta de sentido común: subir el IVA a 30 % queda en 6 % a favor, prohibir el pan en 4 %, duplicar el sueldo de los parlamentarios en 4 % y rebajarlo a la mitad en 88 %; bajar el precio de los medicamentos en 86 %, garantizar el agua potable en 88 % y la semana de cuatro días en 74 %.

## Archivos

| Archivo | Contenido |
|---|---|
| `respuestas.jsonl` | Las 124.000 respuestas del contraste a escala completa |
| `personas.jsonl` | Los 1.000 agentes con sus atributos |
| `casos.json` | Las preguntas con su resultado real |
| `ficha_validacion.csv` | Real y simulado en cada una de las 82 preguntas reservadas |
| `cep_cortes.csv` | Los 370 cortes de la CEP |
| `experimentos/` | Las respuestas de cada variante evaluada y los pronósticos del ancla |
| `analisis.txt`, `analisis_extra.txt`, `casos_resultado.csv`, `grupos_resumen.csv` | Tablas del contraste a escala completa |

Para repetir, desde `backend/`:

```sh
uv run python scripts/contraste_realidad.py correr --concurrencia 40          # contraste a escala completa
uv run python -I scripts/descargar_cep.py data/cep96                          # microdatos de la CEP
uv run python scripts/contraste_analisis.py > data/pruebas/realidad_1000/analisis.txt
uv run python scripts/contraste_experimentos.py correr integrado --casos rai  # el motor actual en las preguntas reservadas
uv run python scripts/contraste_ficha.py                                      # la ficha de validación
```

Fuentes: INE, Censo de Población y Vivienda 2024. Centro de Estudios Públicos, Encuesta CEP N° 96, abril-mayo 2026. Encuestas del banco `datos-pruebas/`.
