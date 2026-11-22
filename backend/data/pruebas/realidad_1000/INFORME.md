# Contraste del pipeline del sitio con las encuestas reales

Corrida del 21-11-2026. 1.000 agentes adultos, un agente por cada 1.000 personas, 124 preguntas con resultado real publicado.

## Resumen

1. **En el porcentaje nacional, el pipeline del sitio no le gana a responder siempre 60 %.** Su error medio es de 14,9 puntos (intervalo de 95 %: 11,7 a 17,7) contra 15,9 de la constante. Deja la mayoría del mismo lado que la encuesta en 71 % de los casos, y la constante en 73 %.
2. **El error no es ruido ni falta de agentes.** Con 1.000 agentes el ruido propio de la simulación es de 1,4 puntos y una simulación perfecta erraría 1,7. Con 200 agentes el resultado ya queda a 2,3 puntos del de 1.000.
3. **El error tiene forma.** Subestimamos lo que en Chile es consenso (apoyo real sobre 80 %: sesgo de 21 puntos hacia abajo) y sobrestimamos lo que la gente rechaza (apoyo real de 35 a 50 %: 9,5 puntos hacia arriba).
4. **La causa principal es que los agentes responden por posición política mucho más que las personas.** En las diez preguntas de la CEP, donde tenemos microdatos reales, la distancia entre izquierda y derecha es de 22 puntos en la realidad y de 51 en la simulación. En los 120 casos del banco la brecha simulada promedia 61 puntos.
5. **Las personas en que más diferimos son las de derecha y las de izquierda**, es decir quienes votaron por Kast o por Jara y quienes aprueban o desaprueban al gobierno. Después vienen, con menos distancia, las personas con educación básica, de zona rural, mayores de 60 y evangélicas, a quienes la simulación hace rechazar medidas ambientales y de derechos que en la realidad tienen mayoría amplia.
6. **Lo que sí funciona es la dirección de los cortes.** En la CEP, 85 % de los segmentos que se alejan del total lo hacen hacia el mismo lado que en la realidad, y el centro político, el sexo, la zona y el nivel socioeconómico quedan bien ordenados.
7. **Hay dos defectos del instrumento, además del sesgo político.** La primera pregunta («¿Estarías de acuerdo con que se implemente esta política en tu región?») invierte las respuestas cuando el caso es una afirmación y no una medida. Y los agentes casi nunca quedan indecisos: 0,1 % contra 6,6 % en las encuestas.

## Qué se hizo

- **Camino exacto del sitio.** Cada caso pasó por `ClaudeCodigo.responder`, el mismo código que usa el servidor: Haiku por la CLI, lotes de 20 personas, perfil temático y las cinco preguntas vigentes. No se usó la caché.
- **Muestra.** La que entrega el sitio con edad mínima 18 y reducción 1.000, tamaño 1.000. Salen de 14.480 agentes disponibles que representan a 14,5 millones de adultos.
- **Casos.** Los 120 comparables del banco (acuerdo o percepción, población general, con porcentaje publicado) más cuatro aparte: los plebiscitos de 2022 y 2023, el panel de ciudadanía del proyecto misceláneo y el registro de incivilidades.
- **Casos fuera.** Quedan 16 sin correr: satisfacción con servicios, preferencias entre tres o más alternativas, efectos percibidos de la jornada de 40 horas y universos especiales. La pregunta de acuerdo del sitio no mide eso.
- **Resultado de la corrida.** 124.000 respuestas de 124.000 pedidas, 6.200 llamadas, 50 minutos, ningún lote fallido. La CLI informa un costo equivalente de 32,5 dólares.
- **Comparación.** Se cuenta como «de acuerdo» la nota 5 a 7 en la primera pregunta, igual que el sitio, y se compara con el porcentaje de acuerdo publicado.

### La muestra se parece a la población

Comparada con la CEP 96 ponderada, la muestra de 1.000 queda a menos de 3,5 puntos en todo lo que se pudo cruzar.

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

La reducción a 1 por cada 1.000 no es la fuente del error: la composición es correcta.

## 1. Nivel nacional

| Medida | Pipeline del sitio | Responder siempre 60 % |
|---|---|---|
| Error absoluto medio | 14,9 | 15,9 |
| Sesgo (simulado menos real) | 5,0 hacia abajo | 0,7 hacia abajo |
| Correlación con lo real | 0,54 | sin correlación |
| Casos a 5 puntos o menos | 22 % | 22 % |
| Casos a 10 puntos o menos | 40 % | 39 % |
| Mayoría del mismo lado | 71 % | 73 % |

- En los 42 casos de prueba, que no se usaron para ajustar nada, el error es de 14,4. En los 78 de desarrollo, 15,1.
- Sin `c704-bloqueo`, cuya cifra parece mal transcrita, el error es de 14,5.
- En desacuerdo el sesgo es de 11,7 puntos hacia arriba: como casi nadie queda indeciso, todo el que no apoya rechaza.
- Corregir con una recta ajustada en las otras familias no ayuda: 14,5.

### Contra los métodos que ya estaban medidos

Mismos 120 casos. Los otros métodos se corrieron con otra muestra, así que la comparación es orientativa.

| Método | Error medio | Sesgo | Mismo lado |
|---|---|---|---|
| Pipeline anterior del sitio, 6 preguntas, 100 agentes | 17,4 | 14,4 abajo | 58 % |
| **Pipeline actual, 1.000 agentes a 1 por 1.000** | **14,9** | **5,0 abajo** | **71 %** |
| Probabilidades con Haiku | 11,9 | 7,3 abajo | 77 % |
| Pronóstico directo de Haiku, sin agentes | 10,7 | 2,4 abajo | 81 % |
| Pronóstico directo de Opus, sin agentes | 8,9 | 0,2 abajo | 85 % |

El cambio de instrucciones para que haya menos indecisos mejoró el pipeline (de 17,4 a 14,9 y de 58 % a 71 % del mismo lado), pero sigue 3 puntos detrás del método de probabilidades y 6 detrás de Opus. Los errores del pipeline actual y del anterior se correlacionan 0,93: se equivocan en los mismos casos.

### Cuántos agentes hacen falta

| Agentes | Error contra encuestas | Distancia al resultado con 1.000 |
|---|---|---|
| 10 | 19,0 | 11,7 |
| 50 | 15,8 | 5,1 |
| 100 | 15,4 | 3,5 |
| 200 | 15,1 | 2,3 |
| 500 | 15,0 | 1,2 |
| 1.000 | 14,9 | 0 |

Más agentes dan un número más estable, no uno más cercano a la realidad. Los 1.000 sirven para abrir por segmentos, no para el total.

### Dónde se concentra el error

**Según el apoyo real.** El error crece con el consenso.

| Apoyo real | Casos | Error medio | Sesgo | Real | Simulado |
|---|---|---|---|---|---|
| 0 a 35 % | 15 | 10,0 | 7,7 arriba | 26,3 | 33,9 |
| 35 a 50 % | 18 | 11,3 | 9,5 arriba | 43,5 | 53,0 |
| 50 a 65 % | 36 | 11,9 | 3,7 abajo | 58,0 | 54,3 |
| 65 a 80 % | 30 | 16,6 | 10,6 abajo | 72,4 | 61,9 |
| 80 a 100 % | 21 | 24,0 | 20,9 abajo | 87,8 | 66,9 |

**Según el tipo de pregunta.**

| Tipo | Casos | Error medio | Sesgo | Mismo lado |
|---|---|---|---|---|
| Declaración de principios | 11 | 23,8 | 23,8 abajo | 91 % |
| Valórica (familia, sexualidad, vida y muerte) | 23 | 17,1 | 10,1 abajo | 26 % |
| Restricción o prohibición | 33 | 15,2 | 4,3 abajo | 82 % |
| Institucional | 12 | 14,1 | sin sesgo | 83 % |
| Beneficio concreto | 30 | 11,7 | sin sesgo | 83 % |
| Percepción | 11 | 9,8 | 4,9 arriba | 64 % |

Las valóricas son el peor resultado cualitativo: en 17 de 23 la simulación deja la mayoría del lado contrario. Chile aparece más conservador de lo que es.

**Según el área.**

| Área | Casos | Error medio | Sesgo |
|---|---|---|---|
| Medio ambiente | 9 | 22,2 | 20,1 abajo |
| Instituciones y elecciones | 10 | 19,9 | 15,2 abajo |
| Familia y derechos | 16 | 18,5 | 14,9 abajo |
| Salud | 9 | 17,2 | 5,6 abajo |
| Trabajo | 5 | 15,8 | 6,0 arriba |
| Economía e impuestos | 8 | 14,6 | sin sesgo |
| Seguridad y justicia | 7 | 13,1 | sin sesgo |
| Migración | 16 | 13,0 | 8,9 abajo |
| Transporte | 8 | 11,9 | 3,0 abajo |
| Educación | 6 | 11,6 | 4,1 arriba |
| Pensiones | 7 | 11,5 | 7,4 arriba |
| Regulación digital | 13 | 10,3 | 4,5 arriba |
| Vivienda | 6 | 9,9 | 3,4 arriba |

**Según la fecha de la encuesta.** 2026: 11,8 (60 casos). 2025: 12,4 (24). 2023: 20,7 (20). 2024: 22,7 (9). 2017: 33,8 (4). Los perfiles describen a la gente de 2026 y las encuestas antiguas son las de enmiendas constitucionales y temas valóricos, así que fecha y tipo de pregunta vienen mezclados.

### Los casos extremos

Donde más subestimamos:

| Caso | Real | Simulado |
|---|---|---|
| Elegir régimen de salud, educación y pensiones | 93 | 52 |
| Eutanasia | 75 | 37 |
| Prohibir bolsas plásticas | 95 | 59 |
| Restringir vehículos contaminantes | 89 | 54 |
| Inmigrantes regulares con acceso a beneficios sociales | 71 | 37 |
| Prohibir leña | 81 | 48 |
| Reconocimiento constitucional de pueblos indígenas | 86 | 55 |
| Matrimonio de parejas del mismo sexo | 77 | 48 |
| Sala cuna sin costo | 93 | 64 |

Donde más sobrestimamos:

| Caso | Real | Simulado |
|---|---|---|
| Cobrar el CAE impago con embargo bancario | 54 | 92 |
| Traslado a la AFP de menor comisión | 66 | 95 |
| Objeción de conciencia individual e institucional | 40 | 66 |
| La familia queda desatendida si la mujer trabaja jornada completa | 32 | 57 |
| La vivienda es demasiado pequeña para tener más hijos | 45 | 69 |
| Prohibir casas de apuestas en línea | 56 | 79 |
| Subsidio a empresas por cotizaciones | 48 | 69 |
| Condenados con enfermedad terminal terminan en su casa | 33 | 53 |

### Casos aparte

| Caso | Real | Simulado |
|---|---|---|
| Plebiscito 2022, Apruebo | 38,1 | 45,8 |
| Plebiscito 2023, A favor | 44,2 | 51,3 |
| Proyecto misceláneo, panel de ciudadanía | 42 | 48,6 |
| Registro de vándalos e incivilidades | 67 | 51,4 |

En 2022 acierta el lado ganador. En 2023 no: da ganador al «A favor» por 1,3 puntos.

### Las otras cuatro preguntas

No hay dato real con qué compararlas, pero la corrida muestra cómo se comportan:

- **Justicia (p2) y efectividad (p4) repiten la primera.** Persona a persona se correlacionan 0,87 y 0,82 con el apoyo, y 0,92 entre casos. Aportan poca información nueva.
- **Confianza en el Estado (p3) no se mueve.** Promedia 3,16 con una desviación de 0,10 entre los 120 casos. Responde al perfil de la persona, no a la política.
- **Influencia (p5) es la única independiente.** Se correlaciona 0,19 con el apoyo.

## 2. En qué tipo de personas diferimos

Hay tres fuentes, de la más sólida a la menos.

### 2.1 Diez preguntas de la CEP 96 con microdatos reales

Se bajaron los microdatos de la CEP 96 (1.466 entrevistas) y se abrieron diez preguntas del banco por las mismas características que tienen los agentes: 370 cortes de segmento por pregunta. Los totales recalculados coinciden con los publicados.

Como la CEP ofrece «ni de acuerdo ni en desacuerdo» (13 a 31 %) y el sitio no deja indecisos, se compara sobre quienes toman posición.

**Cuánto separa cada característica a la gente.** Diferencia media de cada segmento con el total nacional, en puntos.

| Característica | Real | Simulada | Simulada sobre real | Misma dirección |
|---|---|---|---|---|
| Voto en segunda vuelta 2025 | 6,8 | 13,8 | 2,0 veces | 95 % |
| Evaluación del gobierno | 7,1 | 14,0 | 2,0 veces | 95 % |
| Posición política | 7,7 | 14,9 | 1,9 veces | 86 % |
| Sexo | 2,5 | 3,2 | 1,3 veces | 100 % |
| Educación | 5,8 | 6,8 | 1,2 veces | 87 % |
| Zona urbana o rural | 2,5 | 3,0 | 1,2 veces | 100 % |
| Situación laboral | 3,5 | 4,1 | 1,2 veces | 100 % |
| Interés en política | 6,3 | 6,8 | 1,1 veces | 92 % |
| Religión | 4,8 | 5,2 | 1,1 veces | 61 % |
| Edad | 5,3 | 5,1 | 1,0 veces | 84 % |
| Macrozona | 3,3 | 2,1 | 0,6 veces | 57 % |

La demografía se mueve en la magnitud correcta. Lo político se mueve el doble. Religión y macrozona no se ordenan bien (correlación de 0,1 con lo real).

**Brecha entre izquierda y derecha, pregunta por pregunta.** Acuerdo de la izquierda menos acuerdo de la derecha.

| Pregunta | Real | Simulada |
|---|---|---|
| Inmigrantes regulares con igual acceso a educación pública | 7 | 59 |
| La inmigración eleva la criminalidad | 16 a favor de la derecha | 50 a favor de la derecha |
| El gobierno gasta demasiado en inmigrantes | 16 derecha | 61 derecha |
| Seleccionar inmigrantes por nivel educativo | 20 derecha | 60 derecha |
| Los inmigrantes quitan empleos | 19 derecha | 47 derecha |
| Menos Estado en la economía | 12 derecha | 45 derecha |
| Tomas de colegios y universidades | 40 izquierda | 72 izquierda |
| Los inmigrantes aportan a la economía | 18 izquierda | 34 izquierda |
| Reducir el gasto público | 60 derecha | 61 derecha |
| La intervención estatal genera burocracia | 9 derecha | 24 izquierda |

Solo en una pregunta, el recorte del gasto, la realidad está tan dividida como la simulación. Es la única con el sello explícito del gobierno.

El ejemplo más claro es el acceso de inmigrantes regulares a la educación pública. En la realidad lo apoya 79 % de la derecha y 86 % de la izquierda. En la simulación, 13 % de la derecha y 72 % de la izquierda.

**Error por segmento, promedio de las diez preguntas.** La segunda columna es lo que distingue a ese grupo: cuánto erra su distancia con el total, descontado el error que comparten todos.

| Segmento | Error en acuerdo | Error propio del grupo |
|---|---|---|
| Izquierda (1 a 4) | 16,9 | 16,7 |
| Derecha (7 a 10) | 20,1 | 14,8 |
| Votó Jara | 17,5 | 14,4 |
| Votó Kast | 18,5 | 12,5 |
| Aprueba a Kast | 18,0 | 11,4 |
| Desaprueba a Kast | 15,5 | 7,9 |
| Educación básica o menos | 10,4 | 6,7 |
| 60 años o más | 11,9 | 5,1 |
| Sur | 14,6 | 5,4 |
| Rural | 14,2 | 4,5 |
| Centro (5 y 6) | 14,5 | 3,0 |
| No se ubica | 15,7 | 4,0 |
| Interés bajo o nulo en política | 13,3 | 2,8 |
| Mujeres | 13,6 | 1,9 |
| Hombres | 14,4 | 2,0 |
| Urbana | 14,0 | 0,6 |

Hay un error común de unos 14 puntos que afecta a todos por igual (el nivel nacional). Encima de eso, izquierda y derecha suman 15 a 17 puntos propios. Centro, no ubicados, mujeres, hombres y zona urbana casi no tienen error propio.

**Advertencia sobre esta fuente.** Los agentes traen opiniones imputadas desde la misma CEP 96. En cinco de las diez preguntas el perfil incluía literalmente la respuesta del donante, y en las otras cinco incluía opiniones vecinas del mismo tema. La buena dirección de los cortes está ayudada por eso. Separando: con la respuesta en el perfil la correlación es 0,69 y sin ella 0,72, así que el resultado no depende de la filtración directa, pero sí de tener actitudes reales cercanas.

### 2.2 Cortes publicados por otras encuestas

Son 34 cortes por edad, sexo y nivel socioeconómico de cinco preguntas (Bicentenario UC y Cadem), sin relación con la fuente de los perfiles.

| Dimensión | Cortes | Correlación con lo real | Misma dirección |
|---|---|---|---|
| Nivel socioeconómico | 9 | 0,86 | 86 % |
| Edad | 19 | 0,26 | 53 % |
| Todos sin región | 34 | 0,49 | 64 % |

- **El nivel socioeconómico funciona.** En «una madre debiera quedarse en casa con sus hijos pequeños» el grupo bajo da 64 % real y 65,5 % simulado.
- **La edad no.** En «la familia queda desatendida cuando la mujer trabaja jornada completa», la realidad va de 16 % entre los de 18 a 34 a 46 % entre los de 55 o más. La simulación da 60 % en los jóvenes y 54 % en los mayores: al revés y 44 puntos arriba en los jóvenes.
- **Las regiones no se pueden leer con 1.000 agentes.** En la prohibición de bolsas plásticas todas las regiones reales están entre 91 y 97 %. La simulación va de 39 % en Ñuble (28 agentes) a 67 % en Atacama (15 agentes): es ruido de muestras chicas sobre un nivel 36 puntos más bajo.

### 2.3 Los 120 casos, sin cortes reales

Aquí no hay dato real por segmento. Se mide cuánto se aleja cada grupo de agentes del resultado nacional real y en cuántos casos su respuesta es incompatible con él.

**Si el país fuera solo ese grupo de agentes.**

| Grupo | Error contra el total real | Mismo lado | Rechaza consensos reales |
|---|---|---|---|
| Derecha (7 a 10) | 36,2 | 48 % | 48 % |
| Aprueba a Kast | 32,0 | 52 % | 45 % |
| Votó Kast | 30,9 | 53 % | 45 % |
| Izquierda (1 a 4) | 28,4 | 63 % | 36 % |
| Votó Jara | 26,3 | 65 % | 32 % |
| Evangélica | 20,2 | 68 % | 23 % |
| Educación básica o menos | 20,1 | 64 % | 29 % |
| Rural | 18,8 | 64 % | 26 % |
| 60 años o más | 17,9 | 69 % | 23 % |
| Hombres | 16,1 | 65 % | 26 % |
| Mujeres | 15,1 | 74 % | 10 % |
| Centro (5 y 6) | 14,9 | 73 % | 6 % |
| 18 a 29 años | 14,2 | 77 % | 3 % |
| Educación superior | 14,1 | 75 % | 10 % |
| Total simulado | 14,9 | 71 % | |

«Rechaza consensos reales» es el porcentaje de los 31 casos con apoyo real de 75 % o más en que ese grupo de agentes queda bajo 50 %. Con un apoyo real de 75 % o más es aritméticamente difícil que un grupo de un quinto del país esté bajo 50 %, y con 90 % es imposible.

**Ejemplos de consensos reales que un polo simulado rechaza.**

| Caso | Real | Izquierda | Centro | Derecha |
|---|---|---|---|---|
| Prohibir bolsas plásticas | 95 | 92 | 64 | 14 |
| Sala cuna sin costo | 93 | 94 | 66 | 25 |
| Deber del Estado de proteger la naturaleza | 92 | 96 | 69 | 23 |
| Reconocimiento de pueblos indígenas | 86 | 96 | 57 | 14 |
| Matrimonio de parejas del mismo sexo | 77 | 89 | 49 | 7 |
| Elegir régimen de salud, educación y pensiones | 93 | 14 | 52 | 93 |
| Derecho de propiedad | 83 | 19 | 65 | 98 |
| Reducir diputados de 155 a 138 | 86 | 23 | 73 | 97 |
| Expulsar a quienes entren clandestinamente | 88 | 28 | 64 | 89 |
| Ampliar atribuciones de Gendarmería | 85 | 26 | 74 | 98 |

En los 120 casos, la brecha simulada entre izquierda y derecha supera los 40 puntos en 102. Solo en 11 es menor a 10.

**El sesgo no es simétrico.** De los 120 casos, en 60 la simulación hace que la izquierda apoye más y en 47 que apoye más la derecha.

| En la simulación | Casos | Error medio | Sesgo | Izquierda | Centro | Derecha |
|---|---|---|---|---|---|---|
| La izquierda apoya más | 60 | 16,7 | 9,8 abajo | 86 | 54 | 18 |
| La derecha apoya más | 47 | 11,8 | 2,3 abajo | 20 | 57 | 88 |
| Transversal | 13 | 17,3 | 7,2 arriba | 69 | 71 | 71 |

Cuando una medida suena progresista (ambiental, de derechos, social), los agentes de derecha la rechazan en bloque y los de centro quedan en 54 %, y el total se cae 10 puntos bajo la realidad. Cuando suena de derecha el efecto existe pero es menor.

**Las preguntas valóricas.** En las 23, el apoyo real promedia 55 % y el simulado 45 %. Por grupo de agentes: evangélicos 29 %, educación básica 34 %, 60 años o más 36 %, rurales 37 %, católicos 41 %, sin religión 64 %, izquierda 76 %, derecha 17 %. La simulación trata a los mayores, a los menos educados y a los religiosos como opositores a eutanasia, matrimonio igualitario y aborto en tres causales, que en las encuestas tienen 75 a 79 % de apoyo.

**Medio ambiente.** Real 77 %, simulado 57 %. Derecha 25 %, rurales 41 %, educación básica 43 %, hombres 50 %, mujeres 62 %.

## 3. Dos defectos del instrumento

### 3.1 La primera pregunta invierte las afirmaciones

En cinco preguntas de la CEP el agente trae la respuesta real de su donante, y el modelo la leyó en el perfil. Debería acertar casi siempre.

| Pregunta | Acierta el lado |
|---|---|
| Reducir el gasto público | 100 % |
| Menos Estado en la economía | 89 % |
| Los inmigrantes aportan a la economía | 87 % |
| La inmigración eleva la criminalidad | 86 % |
| La intervención estatal genera demasiada burocracia | 23 % |

En burocracia acierta 23 %: responde al revés. Quien cree que el Estado genera burocracia lee «¿estarías de acuerdo con que se implemente esta política?» y contesta que no, porque entiende que la política es la intervención estatal. La pregunta del sitio supone que el texto es una medida. Con una afirmación o una percepción mide otra cosa.

### 3.2 No hay indecisos

De las 124.000 respuestas, 0,1 % son nota 4. En las encuestas, lo que no es acuerdo ni desacuerdo promedia 6,6 %, y en la CEP llega a 31 %. La instrucción «quien se inclina aunque sea un poco responde 3 o 5» eliminó la indecisión en vez de reducirla. Por eso el desacuerdo simulado queda 11,7 puntos sobre el real.

## 4. Qué conviene hacer

1. **No mostrar el porcentaje nacional como predicción.** Hoy no supera a una constante. Lo que se puede afirmar es la dirección de los grupos.
2. **Bajar el peso de la posición política.** Es la causa principal y es medible: la brecha debería quedar cerca de 22 puntos y está en 51. Opciones ya probadas en el banco: el método de probabilidades (11,9) y anclar el total con un pronóstico directo de Opus (8,9) dejando que los agentes repartan ese total entre grupos.
3. **Cambiar la primera pregunta** por una directa sobre el texto («¿Estás de acuerdo o en desacuerdo con esto?»). Resuelve la inversión en afirmaciones.
4. **Devolver la indecisión.** Quitar la frase que empuja a 3 o 5, o separar «tiene postura» de la intensidad, como en la prueba con postura explícita.
5. **Revisar si justicia y efectividad justifican su costo.** Repiten el apoyo. Confianza en el Estado no distingue políticas.
6. **Para el total nacional bastan 200 agentes.** Los 1.000 solo se justifican para abrir por segmentos, y no alcanzan para regiones.
7. **En la demo, mostrar con cuidado edad, religión y región.** Posición política va en la dirección correcta pero exagerada al doble. Nivel socioeconómico, sexo, zona y educación son los cortes más confiables.

## 5. Límites de este contraste

- **Un solo modelo y una sola pasada.** Haiku por la CLI, cada caso una vez. El efecto de lote medido es nulo (varianza entre lotes igual a la binomial), así que repetir cambiaría poco el total.
- **Texto de los casos.** Los agentes leen el enunciado resumido del banco, no el cuestionario original.
- **Fechas.** Las encuestas van de 2014 a 2026 y los perfiles describen 2026.
- **Cortes reales escasos.** Fuera de la CEP hay 34 cortes de cinco preguntas, tres de ellas sobre roles familiares.
- **La CEP no es una prueba independiente.** Los perfiles salen de ella.
- **El grupo socioeconómico** de los cortes publicados se aproximó con el quintil de ingreso imputado.
- **`c704-bloqueo`** (64 % de acuerdo con que los camioneros puedan bloquear carreteras) da 4,4 % simulado. La cifra del banco parece mal transcrita y conviene revisarla contra la fuente.

## 6. Archivos

Todo está en `backend/data/pruebas/realidad_1000/`.

| Archivo | Contenido |
|---|---|
| `respuestas.jsonl` | Las 124.000 respuestas (cinco notas por agente y caso) y una fila por llamada |
| `personas.jsonl` | Los 1.000 agentes con sus atributos y su fila de la tabla |
| `casos.json` | Los 124 casos con su resultado real |
| `casos_resultado.csv` | Real, simulado y diferencia por caso |
| `cep_cortes.csv` | Los 370 cortes de la CEP, real y simulado |
| `grupos_resumen.csv` | Cada grupo de agentes contra el total real en los 120 casos |
| `analisis.txt` y `analisis_extra.txt` | Todas las tablas, incluido el detalle caso por caso |

Para repetir, desde `backend/`:

```sh
uv run python scripts/contraste_realidad.py correr --concurrencia 40
uv run python -I scripts/descargar_cep.py data/cep96
uv run python scripts/contraste_analisis.py > data/pruebas/realidad_1000/analisis.txt
uv run python scripts/contraste_extra.py > data/pruebas/realidad_1000/analisis_extra.txt
```

`correr` gasta: 50 llamadas por caso. Lo ya respondido no se vuelve a preguntar.

Fuentes: INE, Censo de Población y Vivienda 2024. Centro de Estudios Públicos, Encuesta CEP N° 96, abril y mayo de 2026. Encuestas del banco `datos-pruebas/`.

## 7. Arreglo: experimentos, lo que se integró y su validación (22-11-2026)

Después del contraste se probaron 21 variantes del método con los mismos 200 agentes (tomados al azar de los 1.000) sobre 40 casos de desarrollo, y lo elegido se validó en dos conjuntos que no se usaron para ajustar nada: los 42 casos de prueba del banco y 40 preguntas que Rai agregó en su benchmark con Luna, de otras olas y otras encuestadoras. Los agentes fueron siempre Haiku.

### Qué se probó

| Idea | Resultado | Decisión |
|---|---|---|
| Pregunta de apoyo directa | Corrige la inversión en afirmaciones: en burocracia el lado correcto pasa de 20 % a 100 % | Integrada |
| Perfil sin etiquetas políticas (posición, partido, voto, aprobación) | La brecha izquierda-derecha baja de 57 a 21 puntos en prueba; en la CEP queda en 15 a 21 contra 25 real. El número nacional no cambia | Integrada |
| Ancla: pronóstico nacional de un modelo y reparto entre agentes | El error nacional baja de 15,0 a 9,6 en prueba y de 17,5 a 6,8 en las preguntas nuevas | Integrada |
| Instrucción sobre cómo responde la gente | En desarrollo bajaba el error de 13,0 a 10,5; en prueba lo sube a 16,7 porque Haiku se va al extremo | Descartada |
| Postura explícita de Rai (primero si tiene postura, después intensidad) | Con Luna daba 5 % de indecisos; con Haiku da 18 a 27 % y el error sube a 17 | Descartada con Haiku |
| Quitar la frase que empuja a 3 o 5 | 17 % de indecisos, error de 17,4 | Descartada |
| Perfil solo demográfico | 31 % de indecisos con postura explícita, error de 16 | Descartada |
| Mejorar el ancla: Fable, promedio de tres, instrucción calibrada, referencias reales, recalibración | Todas quedan entre 7,5 y 8,6 en desarrollo; ninguna mejora en validación | Se deja un pronóstico simple |
| Mezclar el ancla con el resultado de los agentes | Igual o peor que el ancla sola en error medio | Se deja el ancla completa |

### Validación del motor integrado

Con el reparto tal como lo hace el servidor, por lotes y en orden de llegada (`scripts/contraste_final.py`).

| Conjunto | Método | Error medio | A 5 puntos o menos | A 10 puntos o menos | Mismo lado |
|---|---|---|---|---|---|
| 42 de prueba | Sitio anterior | 15,0 | 19 % | 40 % | 71 % |
| 42 de prueba | Motor nuevo, ancla de Haiku | 11,0 | 26 % | 55 % | 81 % |
| 42 de prueba | Motor nuevo, ancla de Opus | 9,6 | 31 % | 57 % | 88 % |
| 40 nuevas | Sitio anterior | 17,5 | 7,5 % | 25 % | 62,5 % |
| 40 nuevas | Luna (benchmark de Rai) | 14,0 | 17,5 % | 42,5 % | 92,5 % |
| 40 nuevas | Motor nuevo, ancla de Haiku | 9,0 | 30 % | 62,5 % | 85 % |
| 40 nuevas | Motor nuevo, ancla de Opus | 6,8 | 45 % | 85 % | 87,5 % |

En los casos de prueba, además: la distancia entre izquierda y derecha en la CEP queda en 21 puntos (real 25, antes 51), el error de los segmentos frente a su total baja de 7,2 a 4,7, y hay 6 % de personas sin postura (en las encuestas, 6,6 %; antes 0,1 %).

### Lo que el arreglo no logra

- **No todos los casos que ya salían bien se conservan.** Con ancla de Opus, de los 8 casos de prueba que estaban a 5 puntos o menos, 6 siguen ahí y 1 queda a más de 10. En las preguntas nuevas, de 3 queda 1. En total mejoran 58 casos y empeoran 15.
- **El ancla tiene techo.** Un pronóstico directo queda a 7 a 9 puntos de la encuesta y no bajó con nada de lo probado. Lo que falta parece estar en lo que el modelo no ve: el orden y la batería del cuestionario original y el momento en que se preguntó, que es lo que documenta la auditoría de contexto de Rai. Eso no se midió aquí.
- **El número nacional ahora lo decide el pronóstico, no los agentes.** Los agentes aportan quién apoya y quién no. Al comparar variantes de una misma propuesta, la diferencia entre sus totales es la diferencia entre dos pronósticos, que varían unos 2 puntos al repetirlos.
- **Con corridas chicas el reparto en vivo es menos fino:** con 200 agentes el total queda a 1 punto del pronóstico en promedio; con 1.000, a 0,2.

Para repetir:

```sh
uv run python scripts/contraste_experimentos.py correr VARIANTE --casos dev|prueba|rai
uv run python scripts/contraste_experimentos.py informe --casos dev --ancla pronostico_opus
uv run python scripts/contraste_ancla.py pronostico_opus --modelo opus --casos rai
uv run python scripts/contraste_final.py
```

Las respuestas de cada variante están en `experimentos/`.
