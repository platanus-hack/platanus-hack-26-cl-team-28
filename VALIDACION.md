# Validación: qué tan cerca está What If Chile de la opinión real

What If Chile simula cómo respondería la población adulta de Chile a una propuesta de política pública. Es una aproximación a la opinión real de la población, construida con datos oficiales y contrastada con encuestas publicadas. Este documento resume contra qué se comparó, a qué distancia quedan los resultados y en qué se apoya el método.

## En una frase

Contrastamos el simulador con **164 preguntas de 27 encuestas reales** de 10 entidades, que suman **unas 30 mil entrevistas** entre 2014 y 2026. En las preguntas que no usamos para ajustarlo, el porcentaje de acuerdo queda en promedio a **8 puntos** de la encuesta, a **±12 puntos en 8 de cada 10 preguntas**, y del **mismo lado de la mayoría en casi 9 de cada 10**.

## Cómo está construida la población

- **Censo 2024 (INE):** 15,5 millones de personas de 14 años o más, con su comuna, edad, sexo, educación, trabajo, hogar y vivienda. Cada agente es una persona real del censo que representa a un grupo de personas parecidas.
- **Casen 2024:** ingresos, previsión de salud, condiciones laborales y redes, imputados por emparejamiento estadístico.
- **Encuesta CEP N° 96 (abril-mayo 2026):** 54 opiniones de fondo sobre el Estado, la economía, la seguridad, la inmigración, la familia y la confianza en las instituciones, imputadas desde un entrevistado real parecido.
- La muestra que responde cada simulación reproduce la composición del país: con 1.000 agentes queda a menos de 3,5 puntos de la CEP en sexo, edad, educación, zona, región, posición política, evaluación del gobierno y voto.

## Cómo responde

1. **Cada agente responde la encuesta como su persona:** apoyo, justicia, confianza en el Estado, efectividad e influencia, de 1 a 7. Lo hace con Claude Haiku, en lotes de 20 personas, cientos en paralelo: 1.000 agentes en unos 40 segundos.
2. **Un modelo analista (Claude Opus) estima el nivel nacional** de la propuesta con una sola llamada. Los agentes reparten ese total entre ellos sin cambiar su orden: quién apoya, en qué región, de qué edad o grupo, lo deciden los agentes.
3. **El modelo lee las opiniones de fondo de cada persona, no su etiqueta política.** Así responde por lo que la persona piensa del tema y no por su bando, que es como responde la mayoría de la gente.

## Contra qué se comparó

| Fuente | Qué aporta |
|---|---|
| Banco del equipo (`datos-pruebas/`) | 120 preguntas de acuerdo y percepción con porcentaje publicado, en 14 áreas: pensiones, salud, migración, seguridad, medio ambiente, trabajo, vivienda, transporte, educación, regulación digital, instituciones, familia, economía y bienestar |
| Benchmark de políticas (`datos-pruebas/benchmark-politicas-chile.json`) | 40 preguntas más, de otras olas y encuestadoras |
| Votaciones y paneles | Plebiscitos constitucionales de 2022 y 2023 y dos paneles de opinión |
| Microdatos de la CEP 96 | 1.466 entrevistas individuales, para comparar 370 cortes por sexo, edad, educación, zona, posición política, voto y religión |

Las encuestas son de Cadem (17 levantamientos), Centro de Estudios Públicos, Encuesta Bicentenario UC, Criteria, Datavoz, Ipsos, Activa Research, Universidad Diego Portales y Feedback Research, y el Ministerio del Medio Ambiente.

## Resultados

Se midió en 82 preguntas reservadas: ninguna se usó para elegir el método.

| Medida | Resultado |
|---|---|
| Error medio en el % de acuerdo | 8,2 puntos (intervalo de 95 %: 6,9 a 9,7) |
| Error mediano | 6,5 puntos |
| 8 de cada 10 preguntas quedan a | ±12 puntos |
| Preguntas a ±10 puntos o menos | 71 % (58 de 82) |
| Preguntas a ±5 puntos o menos | 38 % (31 de 82) |
| Mayoría del mismo lado que la encuesta | 88 % |
| Error medio en el % en desacuerdo | 6,5 puntos |
| Personas sin postura | 5 a 6 %, como en las encuestas (6,6 %) |

**Por grupos de la población**, con los microdatos de la CEP: los segmentos se mueven en la misma dirección que en la realidad, la distancia entre personas de izquierda y de derecha queda en 21 puntos (en la encuesta, 25), y cada segmento queda en promedio a 4,7 puntos de su diferencia real con el total.

**Como referencia**, el Pew Research Center reportó en septiembre de 2026 un error de 11,4 puntos con su mejor modelo de gemelos digitales de panelistas reales de Estados Unidos.

## Preguntas donde el simulador coincide con la encuesta

Todas son preguntas reservadas para validación. La simulación es la del motor actual con 200 agentes.

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

- **Las opiniones previas de la persona predicen mejor que la demografía** (Hwang et al. 2023; Park et al. 2024). Por eso cada agente lleva las actitudes de fondo de la CEP, y con ellas el modelo distingue a quién está de acuerdo de quién no aun cuando se le oculta la respuesta real de esa persona (AUC de 0,70; el azar es 0,50).
- **Estimar la distribución de la población funciona mejor que pedir una sola respuesta por rol** (Meister et al. 2025; Gong, Sanders y Schneier 2026). El ancla nacional sigue esa idea.
- **Una simulación se puede calibrar contra datos humanos** hasta dejar el sesgo bajo 5,5 % con unas 100 respuestas reales (Krsteski et al. 2025). Por eso el método se mide y se elige contra un banco de 164 preguntas reales.
- **En Chile, las respuestas sintéticas ya se compararon con la CEP** (González-Bustamante, Verelst y Cisternas 2025).

Enlaces: [Pew](https://www.pewresearch.org/data-labs/2026/09/30/methodology-silicon-samples/) · [Meister](https://arxiv.org/abs/2411.05403) · [Gong](https://arxiv.org/html/2603.20229v1) · [Hwang](https://arxiv.org/abs/2305.14929) · [Park](https://arxiv.org/abs/2411.10109) · [Krsteski](https://arxiv.org/html/2510.11408v2) · [González-Bustamante](https://arxiv.org/abs/2509.09871)

## Cómo se reproduce

Desde `backend/`:

```sh
uv run python scripts/contraste_ficha.py          # la tabla de resultados, sin llamar a ningún modelo
uv run python scripts/contraste_experimentos.py correr integrado --casos rai   # vuelve a preguntar a los agentes
```

Las respuestas de cada agente, el detalle por pregunta (`ficha_validacion.csv`) y el informe técnico están en `backend/data/pruebas/realidad_1000/`.

Fuentes de datos: INE, Censo de Población y Vivienda 2024. Ministerio de Desarrollo Social y Familia, Encuesta Casen 2024. Centro de Estudios Públicos, Encuesta CEP N° 96, abril-mayo 2026.
