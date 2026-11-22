# Validación: qué tan cerca está What If Chile de la opinión real

What If Chile simula cómo respondería la población adulta de Chile a una propuesta de política pública. Es una aproximación a la opinión real, construida con datos oficiales de toda la población y contrastada con miles de entrevistas reales.

## En 30 segundos

- **Lo probamos contra la realidad:** 164 preguntas con resultado publicado (124 del banco de encuestas y 40 del benchmark de políticas), de 27 encuestas y 10 instituciones, con **29.854 entrevistas** detrás, más **1.466 entrevistas individuales** de la Encuesta CEP para comparar grupo a grupo.
- **82 de esas preguntas quedaron reservadas solo para medir:** no se usaron para elegir el método. En ellas el error medio es de **8,2 puntos** (mediana 6,5) y **7 de cada 10** quedan a ±10 puntos.
- **Reducimos el error a la mitad** frente a los mismos agentes sin calibrar (16,2 puntos) y quedamos cerca de lo que difieren las encuestas reales entre sí (5,2 puntos en promedio).
- **Acertamos qué piensa la mayoría en casi 9 de cada 10 preguntas** (88 %).
- **La población es Chile entero:** 15,5 millones de personas reales del Censo 2024, con datos de Casen y opiniones de la CEP, validada contra las tres fuentes. Una muestra de 1.000 agentes reproduce la composición del país a menos de 3,5 puntos.

## ¿8 puntos es mucho? Lo que difieren las encuestas reales entre sí

Una encuesta no es la verdad exacta: tiene margen de error (±3,7 puntos con 700 casos), y el resultado cambia con la redacción, la fecha y el método de cada encuestadora. En nuestro banco hay temas medidos por más de una encuestadora con meses de diferencia:

| Tema | Lo que midió cada encuesta (% de acuerdo) | Distancia entre ellas |
|---|---|---|
| Matrimonio igualitario | Cadem 77, UDP y Feedback 72, Ipsos 72, Bicentenario UC 68 | 9 puntos |
| Adopción por parejas del mismo sexo | Cadem 65, Ipsos 58, Bicentenario UC 53 | 12 puntos |
| Eutanasia | Cadem 75, UDP y Feedback 83 | 8 puntos |
| Cambio de identidad de género en adultos | Cadem 67, Bicentenario UC 60 | 7 puntos |
| Aborto en tres causales | Cadem 79, UDP y Feedback 78 | 1 punto |
| Igual acceso a servicios para inmigrantes regulares | CEP 71, Bicentenario UC 71 | 0 puntos |

En promedio, dos de estas mediciones difieren en **5,2 puntos**, con un máximo de **12**. El simulador:

| Distancia a la encuesta | Preguntas de validación |
|---|---|
| A 5 puntos o menos (cerca del margen de error de una encuesta) | 38 % |
| A 9 puntos o menos (lo que separa a las encuestadoras en matrimonio igualitario) | 66 % |
| A 12 puntos o menos (lo que separa a las encuestadoras en adopción) | 80 % |
| Mediana | 6,5 puntos |

Además, el resultado es estable. Son tres medidas distintas: agrupar la población a 1 agente por cada 1.000 personas mueve sus distribuciones menos de medio punto (tabla de más abajo); el error de muestreo de una simulación con 1.000 agentes es de 1,4 puntos; y repetir el pronóstico nacional lo mueve unos 2 puntos.

## Un ejemplo que se entiende solo

Cadem preguntó en junio de 2026 por construir una cárcel nueva cada vez más cerca de la casa de la persona. El simulador reproduce el efecto «sí, pero no en mi barrio» sin que nadie se lo explique:

| Construir una cárcel nueva… | Encuesta | Simulador |
|---|---|---|
| …ampliando la cárcel Santiago 1 | 61 % | 62 % |
| …en la región donde vive | 65 % | 56 % |
| …en la comuna donde vive | 30 % | 27 % |
| …en el barrio donde vive | 13 % | 13 % |

## Cómo construimos agentes que representan a Chile

Dedicamos el trabajo del fin de semana a revisar el estado del arte y a diseñar con cuidado de dónde sale cada agente, qué sabe de sí mismo y cómo se agrupa sin perder representatividad.

### Qué es una característica representativa y cómo la definimos

Un dato entra al perfil de un agente si cumple tres condiciones:

1. **Viene de una fuente que representa a todo el país:** el Censo 2024 (todas las personas), Casen 2024 (representativa por región) o la Encuesta CEP 96 (muestra probabilística nacional).
2. **Ayuda a predecir opiniones.** Lo medimos con las 1.466 entrevistas de la CEP: la demografía sola explica 4 % de la variación de las opiniones, el núcleo del perfil 16 % y el perfil completo 19 %, medido en personas que el modelo estadístico no vio. Por eso cada agente lleva, además de su edad, comuna, educación, trabajo, hogar e ingreso, sus opiniones de fondo sobre el Estado, la economía, la seguridad, la inmigración, la familia y la confianza en 15 instituciones.
3. **Se conserva al agrupar:** cada dato que importa se controla en cada nivel de reducción (tabla más abajo).

### De dónde sale cada agente

| Capa | Cómo se obtiene | Cómo se verificó |
|---|---|---|
| Censo 2024 (INE) | Cada agente es una persona real de 14 años o más del censo, con su comuna, edad, sexo, educación, trabajo, hogar y vivienda | Coincide con el censo en las 346 comunas y en cada cruce de comuna, zona, sexo, edad, estado civil, educación y actividad |
| Casen 2024 | Ingreso, previsión de salud, condiciones de trabajo y redes, tomados de un hogar o persona parecida de la encuesta | Diferencia máxima de 1,25 puntos con Casen a nivel nacional; las comunas quedan ordenadas igual por ingreso (correlación 0,993) |
| CEP N° 96 | 54 opiniones tomadas juntas de un entrevistado real parecido (sexo, edad, educación, zona, nivel socioeconómico, actividad y religión), para que sean coherentes entre sí | Diferencia máxima de 2,65 puntos con la CEP, dentro de su margen de error (2,8); las correlaciones entre opiniones se conservan (diferencia media de 0,017) |

### Cómo se agrupa sin perder representatividad

Los 15,5 millones de personas se agrupan en cuatro niveles anidados: un agente por cada 10, 100, 1.000 o 10.000 personas.

1. **Primero por perfil político**, que es lo que más pesa en una opinión: los entrevistados de la CEP se agrupan en 8 tipos y cada persona hereda el de su entrevistado.
2. **Después por territorio y demografía:** región, comuna, zona, sexo, tramo de edad y situación laboral, en grupos de 10.
3. **El representante de cada grupo no es el promedio ni uno al azar:** es la persona que mejor mantiene las proporciones de su región en perfil político, voto, evaluación del gobierno, sexo, edad, trabajo, educación y hogar.

Qué tanto se conserva la población en cada nivel (diferencia máxima con la población completa, en puntos porcentuales):

| Dato | 1 por cada 10 | 1 por cada 100 | 1 por cada 1.000 | 1 por cada 10.000 |
|---|---|---|---|---|
| Sexo | 0,00 | 0,00 | 0,00 | 0,06 |
| Edad en tramos de cinco años | 0,00 | 0,00 | 0,03 | 0,35 |
| Zona urbana o rural | 0,00 | 0,00 | 0,01 | 0,17 |
| Perfil político | 0,00 | 0,01 | 0,03 | 0,27 |
| Voto en la segunda vuelta de 2025 | 0,00 | 0,00 | 0,04 | 0,31 |
| Evaluación del gobierno | 0,00 | 0,01 | 0,03 | 0,29 |
| Nivel educativo | 0,03 | 0,11 | 0,27 | 0,58 |
| Decil de ingreso del hogar | 0,04 | 0,20 | 0,42 | 0,53 |
| Una opinión dentro de cualquier subgrupo filtrable (región, sexo y edad, ingreso, educación, posición política), desvío medio | 0,06 | 0,34 | 1,13 | 4,43 |

Con un agente por cada 1.000 personas, que es el nivel con que se hizo esta validación, todas las distribuciones quedan a menos de medio punto de la población real, una opinión dentro de un subgrupo se desvía en promedio 1,1 puntos y ningún subgrupo queda vacío.

### Cómo se elige la muestra de cada simulación

Cada simulación sortea sus agentes estratificando por región, comuna y zona, con cuotas proporcionales a las personas que representa cada uno. Una muestra de 1.000 adultos queda así:

| Característica | Muestra | Encuesta CEP 96 |
|---|---|---|
| Mujeres | 52,7 % | 50,8 % |
| Educación superior | 30,8 % | 31,0 % |
| Región Metropolitana | 40,3 % | 41,0 % |
| Izquierda / centro / derecha | 21,1 / 42,8 / 21,2 % | 20,9 / 41,4 / 21,7 % |
| Aprueba al gobierno | 32,9 % | 34,5 % |
| Votó Kast / Jara en 2025 | 41,3 / 31,2 % | 39,9 / 28,1 % |

## Cómo responde

1. **Cada agente responde la encuesta como su persona:** apoyo, justicia, confianza en el Estado, efectividad e influencia, de 1 a 7. Los agentes son Claude Haiku, por lotes y cientos en paralelo: 1.000 agentes en menos de un minuto (medición en `docs/backend/07-capacidad-y-escalado.md`).
2. **El agente responde desde sus opiniones de fondo, no desde su etiqueta política,** que es como responde la mayoría de la gente. Así la distancia entre personas de izquierda y de derecha queda en 21 puntos, como los 25 de la CEP.
3. **Un modelo analista (Claude Opus) estima el nivel nacional** con una sola llamada por propuesta. Los agentes reparten ese total sin cambiar su orden: quién apoya, en qué región, de qué edad o grupo, lo deciden los agentes.

### Qué aporta cada pieza

Cada pieza resuelve una parte distinta y se midió por separado en las 42 preguntas reservadas del banco:

| Versión | Error medio nacional | Mayoría del mismo lado | Distancia izquierda-derecha (CEP: 25) | Error por segmento CEP |
|---|---|---|---|---|
| Sitio anterior (agentes con etiqueta política, sin ancla) | 15,0 | 71 % | 51 puntos | 7,2 |
| Agentes nuevos, sin ancla | 16,8 | 74 % | 15 puntos | 4,2 |
| Agentes nuevos con ancla nacional (motor actual) | 9,6 | 88 % | 21 puntos | 4,7 |

El ancla corrige el nivel nacional. Los agentes deciden cómo se reparte entre regiones, edades y grupos, y por qué: sin etiquetas políticas, la polarización simulada bajó de 51 a 21 puntos, cerca de los 25 reales. Fuente: `backend/data/pruebas/realidad_1000/experimentos/validacion_final.txt`.

## Resultados

Medidos en 82 preguntas reservadas, que no se usaron para elegir el método:

| Medida | Resultado |
|---|---|
| Error mediano en el % de acuerdo | 6,5 puntos |
| Error medio | 8,2 puntos (intervalo de 95 %: 6,9 a 9,7) |
| 8 de cada 10 preguntas quedan a | ±12 puntos |
| Preguntas a ±10 puntos o menos | 71 % (58 de 82) |
| Preguntas a ±5 puntos o menos | 38 % (31 de 82) |
| Mayoría del mismo lado que la encuesta | 88 % |
| Error medio en el % en desacuerdo | 6,5 puntos |
| Personas sin postura | 5 a 6 %, como en las encuestas (6,6 %) |

**Sin ventaja por usar la CEP en el perfil:** los agentes llevan opiniones de la CEP 96, pero solo 4 de las 82 preguntas reservadas vienen de esa encuesta, y en ellas el error es mayor (16,3). Sin esas 4, el error medio de las otras 78 es de 7,8 puntos.

**Por grupos de la población**, con los microdatos de la CEP: los segmentos se mueven en la misma dirección que en la realidad, y cada segmento queda en promedio a 4,7 puntos de su diferencia real con el total.

### Comparado con otras formas de estimar

Error medio en el % de acuerdo, en puntos (menos es mejor):

| Método | Error | Fuente |
|---|---|---|
| Agentes de IA sin calibrar (el motor anterior del sitio) | 16,2 | Las mismas 82 preguntas, columna `err_antes` de `ficha_validacion.csv` |
| Responder siempre 60 % | 15,1 | Las mismas 82 preguntas |
| Pew Research Center, gemelos digitales (EE.UU.) | 11,4 | Su propio banco de preguntas; es una referencia, no una comparación en las mismas preguntas |
| **What If Chile** | **8,2** | Las 82 preguntas reservadas |
| Encuestas reales entre sí | 5,2 | Temas medidos por más de una encuestadora (tabla de arriba) |

What If Chile tiene 49 % menos error que los mismos agentes sin calibrar.

## Preguntas donde el simulador coincide con la encuesta

Todas son preguntas reservadas para validación, simuladas con el motor actual y 200 agentes sorteados del nivel de 1 agente por cada 1.000 personas. Las 82 preguntas, con su resultado real y simulado, están en `backend/data/pruebas/realidad_1000/ficha_validacion.csv`.

### A 5 puntos o menos (31 preguntas)

| Pregunta | Fuente | Encuesta real | Simulación | Diferencia |
|---|---|---|---|---|
| ¿Debería Chile prohibir las casas de apuestas o casinos que operan por internet? | Cadem, 2026-06 | 56 % | 56 % | 0 |
| Renovar cada seis meses el estado de excepción en la macrozona sur, en vez de cada 15 días | Cadem, 2023-03 | 69 % | 69 % | 0 |
| Permitir que menores de edad apuesten en plataformas de apuestas por internet | Cadem, 2026-06 | 5 % | 5 % | 0 |
| Construir una cárcel nueva en el barrio donde vive la persona encuestada | Cadem, 2026-06 | 13 % | 13 % | 0 |
| Cambiar la Constitución para reforzar las medidas de seguridad | Criteria, 2026-08 | 62 % | 62 % | 0 |
| Eliminar las contribuciones que pagan las viviendas en Chile | Activa Research, 2025-06 | 66 % | 66 % | 0 |
| Regularizar a inmigrantes en situación irregular con hijos nacidos en Chile y de nacionalidad chilena | Cadem, 2026-01 | 43 % | 42 % | -1 |
| Cobrar el CAE judicial o administrativamente a quienes ganen más de $3,5 millones al mes | Cadem, 2026-06 | 70 % | 69 % | -1 |
| Suspender temporalmente subsidios habitacionales a personas sancionadas por vandalismo o incivilidades | Cadem, 2026-06 | 62 % | 61 % | -1 |
| Ampliar la cárcel Santiago 1 para aumentar su capacidad penitenciaria | Cadem, 2026-06 | 61 % | 62 % | +1 |
| Suspender temporalmente el acceso a la licencia de conducir a personas sancionadas por vandalismo o incivilidades | Cadem, 2026-06 | 70 % | 72 % | +2 |
| Impedir temporalmente renovar el permiso de circulación a personas sancionadas por vandalismo o incivilidades | Cadem, 2026-06 | 65 % | 67 % | +2 |
| Poner un límite al monto de las remesas que pueden enviar al exterior las personas inmigrantes | Cadem, 2026-01 | 57 % | 55 % | -2 |
| Suspender temporalmente bonos o transferencias del Estado a personas sancionadas por vandalismo o incivilidades | Cadem, 2026-06 | 72 % | 70 % | -2 |
| Legalizar el uso recreativo de cannabis para mayores de 18 años | Cadem, 2024-06 | 47 % | 44 % | -2 |
| Aprobar un nuevo estado de excepción para la macrozona sur | Cadem, 2023-03 | 78 % | 75 % | -3 |
| Construir una cárcel nueva en la comuna donde vive la persona encuestada | Cadem, 2026-06 | 30 % | 27 % | -3 |
| Decretar un estado de excepción en la Región Metropolitana | Cadem, 2024-03 | 64 % | 67 % | +3 |
| Mantener un canal de televisión público en Chile | Activa Research, 2025-06 | 60 % | 63 % | +3 |
| Suspender temporalmente la Pensión Garantizada Universal a personas sancionadas por vandalismo o incivilidades | Cadem, 2026-06 | 55 % | 52 % | -4 |
| Permitir que parejas del mismo sexo adopten hijos | Universidad Diego Portales y Feedback Research, 2024-11 | 62 % | 58 % | -4 |
| Otorgar a parejas del mismo sexo los mismos derechos de adopción que a parejas heterosexuales | Ipsos, 2025 | 58 % | 54 % | -4 |
| Regular las casas de apuestas por internet y permitir su funcionamiento legal sujeto a fiscalización | Cadem, 2026-06 | 51 % | 55 % | +4 |
| Reconocer el matrimonio o una forma de reconocimiento legal a las parejas del mismo sexo | Ipsos, 2025 | 72 % | 68 % | -4 |
| Cobrar el CAE a quienes tienen capacidad de pago y mantienen el crédito impago | Cadem, 2026-03 | 70 % | 74 % | +4 |
| Permitir que las Fuerzas Armadas colaboren en labores contra bandas de narcotraficantes | Cadem, 2024-03 | 89 % | 84 % | -4 |
| Permitir a plataformas de apuestas patrocinar equipos de fútbol | Cadem, 2026-06 | 26 % | 30 % | +4 |
| Expresar acuerdo o desacuerdo con la eutanasia | Cadem, 2024-06 | 75 % | 70 % | -4 |
| Permitir apoyo militar en labores de seguridad ciudadana | Cadem, 2024-03 | 80 % | 76 % | -4 |
| Permitir a plataformas de apuestas patrocinar eventos deportivos | Cadem, 2026-06 | 27 % | 32 % | +5 |
| Suspender temporalmente los subsidios de arriendo a personas sancionadas por vandalismo o incivilidades | Cadem, 2026-06 | 66 % | 61 % | -5 |

### Entre 5 y 10 puntos (27 preguntas)

| Pregunta | Fuente | Encuesta real | Simulación | Diferencia |
|---|---|---|---|---|
| Permitir la colaboración de las Fuerzas Armadas con Carabineros y la PDI | Criteria, 2026-08 | 69 % | 74 % | +6 |
| Ofrecer un acuerdo de pago del CAE a quienes ganen menos de $3,5 millones al mes | Cadem, 2026-06 | 79 % | 73 % | -6 |
| Reducir de 45 a 40 horas la jornada de trabajo semanal | Cadem, 2023-04 | 71 % | 77 % | +6 |
| Permitir a plataformas de apuestas publicar anuncios en redes sociales | Cadem, 2026-06 | 27 % | 21 % | -6 |
| Autorizar la interceptación o el registro de comunicaciones | Criteria, 2026-08 | 44 % | 50 % | +6 |
| Autorizar la requisición de determinados bienes | Criteria, 2026-08 | 39 % | 45 % | +6 |
| Desplegar militares en el norte del país para frenar la inmigración irregular | Cadem, 2023-03 | 93 % | 87 % | -6 |
| Permitir a plataformas de apuestas anunciarse en televisión | Cadem, 2026-06 | 25 % | 18 % | -6 |
| Suspender temporalmente la gratuidad universitaria a personas sancionadas por vandalismo o incivilidades | Cadem, 2026-06 | 63 % | 70 % | +6 |
| Bloquear páginas de apuestas en línea que operan ilegalmente | Cadem, 2026-06 | 82 % | 76 % | -6 |
| Permitir el aborto por violación, riesgo vital de la mujer o inviabilidad fetal | Universidad Diego Portales y Feedback Research, 2024-11 | 78 % | 72 % | -6 |
| Estar a favor de que exista la pena de muerte en Chile | Universidad Diego Portales y Feedback Research, 2024-11 | 64 % | 58 % | -6 |
| Evaluar si tener hijos dificulta que una mujer trabaje | Pontificia Universidad Católica de Chile, 2026-07 | 71 % | 78 % | +7 |
| Reconocer el matrimonio entre personas del mismo sexo | Universidad Diego Portales y Feedback Research, 2024-11 | 72 % | 64 % | -8 |
| Suspender temporalmente becas o beneficios estudiantiles a personas sancionadas por vandalismo o incivilidades | Cadem, 2026-06 | 64 % | 72 % | +8 |
| Expulsar a toda persona inmigrante que haya ingresado irregularmente a Chile | Cadem, 2026-01 | 81 % | 73 % | -8 |
| Indicar si la vivienda donde vive la persona es demasiado pequeña para una familia numerosa | Pontificia Universidad Católica de Chile, 2026-07 | 45 % | 37 % | -8 |
| Permitir que militares protejan infraestructura crítica urbana sin declarar un Estado de Emergencia | Cadem, 2024-03 | 83 % | 75 % | -8 |
| Crear un estado de excepción constitucional para que el gobierno pueda aplicar medidas extraordinarias de seguridad por hasta 240 días | Criteria, 2026-08 | 55 % | 63 % | +8 |
| Establecer penas de cárcel por inmigración ilegal mediante una ley chilena | Cadem, 2026-01 | 74 % | 66 % | -8 |
| Restringir el derecho de reunión | Criteria, 2026-08 | 34 % | 43 % | +9 |
| Construir una cárcel nueva en la región donde vive la persona encuestada | Cadem, 2026-06 | 65 % | 56 % | -9 |
| Corregir la ley de jornada de 40 horas | Cadem, 2026-03 | 29 % | 38 % | +9 |
| Mantener el aborto permitido por inviabilidad fetal, riesgo vital materno o violación | Cadem, 2024-06 | 79 % | 70 % | -10 |
| Suspender temporalmente el acceso al pasaporte a personas sancionadas por vandalismo o incivilidades | Cadem, 2026-06 | 69 % | 60 % | -10 |
| Permitir controles de identidad y detenciones en pasos fronterizos no habilitados a militares desplegados en el norte | Cadem, 2023-03 | 96 % | 86 % | -10 |
| Permitir la eutanasia en Chile | Universidad Diego Portales y Feedback Research, 2024-11 | 83 % | 73 % | -10 |

## En qué se apoya el método

- **Las opiniones previas de la persona predicen mejor que la demografía** (Hwang et al. 2023; Park et al. 2024). Por eso cada agente lleva las actitudes de fondo de la CEP: con ellas el modelo distingue a quién está de acuerdo de quién no aun cuando se le oculta la respuesta real de esa persona (AUC de 0,70; el azar es 0,50).
- **Estimar la distribución de la población funciona mejor que pedir una sola respuesta por rol** (Meister et al. 2025; Gong, Sanders y Schneier 2026). El ancla nacional sigue esa idea.
- **Una simulación se puede calibrar contra datos humanos** hasta dejar el sesgo bajo 5,5 % con unas 100 respuestas reales (Krsteski et al. 2025). Por eso el método se mide y se elige contra un banco de 164 preguntas reales.
- **En Chile, las respuestas sintéticas ya se compararon con la CEP** (González-Bustamante, Verelst y Cisternas 2025).
- **La justicia y la efectividad percibidas son los determinantes más importantes de la aceptación de leyes e impuestos climáticos**, según un metaanálisis de 51 artículos y 119 mil participantes en 33 países: por eso la encuesta del simulador las pregunta junto al apoyo (`backend/contexto/metodo/framework.md`).

Enlaces: [Pew](https://www.pewresearch.org/data-labs/2026/09/30/methodology-silicon-samples/) · [Meister](https://arxiv.org/abs/2411.05403) · [Gong](https://arxiv.org/html/2603.20229v1) · [Hwang](https://arxiv.org/abs/2305.14929) · [Park](https://arxiv.org/abs/2411.10109) · [Krsteski](https://arxiv.org/html/2510.11408v2) · [González-Bustamante](https://arxiv.org/abs/2509.09871)

## Cómo se reproduce

Desde `backend/`:

```sh
uv run python scripts/contraste_ficha.py                                       # la tabla de resultados, sin llamar a ningún modelo
uv run python scripts/contraste_experimentos.py correr integrado --casos rai   # vuelve a preguntar a los agentes
uv run python -I scripts/validar_poblacion.py data/chile data/censo2024 data/casen2024 data/cep96 contexto/chile   # la población contra censo, Casen y CEP
```

Más detalle: el informe técnico y las respuestas de cada agente en `backend/data/pruebas/realidad_1000/`; la población en `backend/contexto/chile/validacion.md` y `agentes.md`; qué datos pesan en una opinión en `backend/contexto/metodo/influencia.md`.

Fuentes de datos: INE, Censo de Población y Vivienda 2024. Ministerio de Desarrollo Social y Familia, Encuesta Casen 2024. Centro de Estudios Públicos, Encuesta CEP N° 96, abril-mayo 2026.
