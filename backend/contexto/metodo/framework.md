# What If Chile: documento de contexto y framework

Proyecto para Platanus Hack 2026, track Simulaciones. Versión del 21-11-2026.

Es el documento de diseño con que partió el proyecto: reúne la revisión de la literatura y las decisiones iniciales. El método que usa hoy el sitio, ya medido contra encuestas reales, está en [VALIDACION.md](../../../VALIDACION.md) y [FUNCIONAMIENTO.md](../../../FUNCIONAMIENTO.md); donde este documento difiera (por ejemplo, los perfiles no llevan valores de Schwartz porque ninguna fuente chilena los mide), manda lo de esos dos.

Este documento reúne el framework de What If Chile: qué problema resuelve, cómo se caracterizan los agentes, qué se les pregunta, cómo se diseñan las variantes de una ley, cómo se valida y calibra el modelo, y quiénes son los usuarios. Cada afirmación empírica lleva su fuente, numerada entre corchetes, con el listado completo al final. Lo que es una decisión de diseño del equipo, y no un hallazgo de la literatura, está marcado como **Decisión de diseño**.

---

## 1. Qué es What If Chile

What If Chile simula cómo reacciona la población chilena a distintas versiones (A a E) de un proyecto de ley en tramitación, región por región y perfil por perfil, para identificar qué versión maximiza la satisfacción o minimiza la disconformidad antes de que se vote.

Funciona en cuatro pasos:

1. **Proyecto real.** Se toma un proyecto en tramitación en el Congreso.
2. **Variantes A a E.** Se generan versiones que cambian sus atributos clave, con un núcleo fijo.
3. **Chile sintético.** Agentes LLM con el perfil de cada región responden la misma encuesta frente a cada variante.
4. **Decisión.** Se obtiene un ranking de variantes, un mapa regional y las objeciones principales.

### El problema
- Chile no evalúa sistemáticamente si sus leyes funcionan. La Comisión Nacional de Evaluación y Productividad (CNEP) advirtió en mayo de 2026 que el Estado no tiene un sistema institucionalizado para revisar si las leyes y regulaciones cumplen sus objetivos una vez implementadas [1].
- El principal instrumento de evaluación previa, el Informe de Impacto Regulatorio (IIR), es obligatorio para los proyectos de ley desde julio de 2019 [2], pero según la CNEP todavía no se consolida como una herramienta para contrastar de manera sistemática lo que se diseñó con lo que pasó después [3].
- Las plataformas de participación del Congreso juntan opiniones que nadie procesa. El Senador Virtual reunió 289 proyectos, 136.229 usuarios y 83.907 comentarios hasta diciembre de 2018, con escaso impacto, sin personas ni recursos asignados a procesar la información [4]. En su sucesor, el Congreso Virtual, varios proyectos ya aprobados no reflejan en su historial la contribución ciudadana hecha en la plataforma [5].

---

## 2. Estado del arte: simulación de opinión pública con LLM

### 2.1 Trabajos de referencia
- **"Silicon samples" (Argyle et al.).** Es el trabajo fundacional: propuso usar LLM condicionados con perfiles demográficos como muestras sintéticas de humanos, a partir de encuestas de EE.UU. [6].
- **AgentSociety (Tsinghua).** Simulador a gran escala: más de 10 mil agentes y 5 millones de interacciones. Uno de sus casos fue el efecto de políticas de renta básica universal. El código es abierto [7].
- **Agentes construidos desde encuestas reales.** Un trabajo de 2026 sobre movilidad propone construir los agentes desde poblaciones empíricas derivadas de encuestas, en vez de personas inventadas a mano, para estudiar cómo se forman las preferencias frente a una política [8].
- **Protocolo argentino de stress test pre-legislativo (Lerer, 2026).** Es lo más parecido a What If Chile. Fija la obligación central de una norma ficticia y varía tres rasgos de implementación (complejidad regulatoria, consistencia de la fiscalización y salvaguardas procesales), lo que da ocho brazos experimentales. Registra cada etapa del texto legal como una "ola" inmutable. Su línea base no usa LLM de frontera, y el propio autor la declara no apta para decisiones legales hasta validarla con un piloto humano [9].
- **CivicSim (Berkeley, 2026).** Prototipo que condiciona la postura de cada agente a su perfil demográfico y a datos históricos de encuestas de su grupo [10].
- **Productos comerciales.** Simile (simulación de personas reales con consentimiento, para productos y precios) [11], Artificial Societies (audiencias sintéticas de clientes, ciudadanos e inversionistas) [12] y MiroFish (impacto de regulaciones con agentes por grupo de interés, sin comparación de variantes lado a lado) [13].

### 2.2 En Chile
- **Estudio de la UDP (González-Bustamante, Verelst y Cisternas, 2025).** Compara respuestas sintéticas generadas con LLM contra la encuesta CEP. Se aproximan a la opinión pública chilena, pero la coincidencia varía bastante según la pregunta. Les fue mejor en las preguntas de confianza (F1 y accuracy sobre 0,90), y la coincidencia fue mayor en el grupo de 45 a 59 años. Los autores advierten que los encuestados sintéticos pueden reproducir estereotipos y sesgos [14].
- No encontramos ninguna herramienta que tome proyectos chilenos en tramitación, genere variantes y compare su aceptación por región.

### 2.3 Qué diferencia a What If Chile
1. Compara variantes de una misma ley, no una política fija.
2. Usa proyectos chilenos reales en tramitación.
3. Desagrega por región, con calibración en datos chilenos (CASEN, Censo, CEP).
4. Cierra el ciclo: las objeciones de los agentes alimentan la siguiente versión.

---

## 3. Caracterización de los agentes

### 3.1 Qué determina el apoyo a una ley según la literatura

El hallazgo central: los rasgos "objetivos" de una persona, como la edad o tener hijos, pesan menos de lo que se cree. Lo que más predice el apoyo son sus actitudes de fondo y lo que piensa de la ley en sí.

| Rango | Factor | Evidencia | Uso en What If Chile |
|---|---|---|---|
| 1 | Justicia y efectividad percibidas de la ley | En un metaanálisis de 15 variables, 89 bases de datos, 51 artículos y 33 países (119.465 participantes), fueron los determinantes más importantes de la aceptación de leyes e impuestos climáticos [15] | No es un rasgo del agente: es su reacción a cada variante. Se mide en la encuesta |
| 2 | Ideología e identificación partidaria | Las medidas de interés propio tuvieron muy poco efecto en las preferencias de política; las actitudes simbólicas (ideología, identificación partidaria) tuvieron efectos grandes [16]. Se mantiene en 30 años de datos [17] | Rasgo central del agente |
| 3 | Quién propone la ley | Las personas apoyan más una propuesta si la apoya su partido [18]. El efecto es mayor con partidos polarizados, y se debilita cuando el tema le importa personalmente a la persona [19] | Rasgo (evaluación del gobierno, partido) y condición experimental (con o sin etiqueta) |
| 4 | Valores | La autotrascendencia y la conservación guían la opinión en todas las áreas de política; la autopromoción y la apertura al cambio pesan bastante menos [20] | Valores de Schwartz, con más peso en esas dos dimensiones |
| 5 | Confianza en el Estado | Se relaciona de forma débil a moderada con el voto, las preferencias de política y el cumplimiento (61 estudios, más de 3,6 millones de observaciones) [21]. En impuestos al carbono, la gente confía poco en que el gobierno use bien lo recaudado [22] | Rasgo del agente; pesa más en políticas con costo visible |
| 6 | Afectación directa | El interés propio suele tener efectos débiles, pero importa cuando se mide el interés que la persona percibe en la política [23] | Variable calculada para cada ley |
| 7 | Demografía y personalidad | Influyen sobre todo de forma indirecta, a través de las anteriores [16][17] | Base de la población; dan variedad y coherencia al razonamiento |

### 3.2 Arquitectura del agente

**Decisión de diseño:** cada agente tiene cuatro capas. La cuarta se calcula para cada ley.

**Capa 1. Quién es (perfil sociodemográfico).** Se muestrea por región desde la CASEN y el Censo 2024.
- Edad, género, nacionalidad, región y comuna, zona urbana o rural.
- Tramo socioeconómico, nivel educacional propio, ocupación y situación laboral (dependiente, independiente, casa particular, no trabaja).
- Estado civil, hijos (cuántos y de qué edades), hermanos.
- Nivel educacional y tramo socioeconómico de los padres.
- Tipo de vivienda, transporte (público o privado), previsión de salud.
- Etnia: se conserva por representatividad, con peso bajo salvo que la ley la toque directamente.

**Capa 2. Cómo es (personalidad, Big Five).** Apertura, responsabilidad, extraversión, amabilidad y neuroticismo.
- No es un predictor fuerte del apoyo a una ley (ver 3.1). Su función es darle variedad y coherencia al razonamiento de cada agente.
- Método recomendado: el de Nemotron-Personas (NVIDIA). Se muestrea un puntaje T por rasgo (media 50, desviación 10, recortado entre 20 y 80), se agrupa en una etiqueta ("muy bajo", "bajo", "promedio", "alto", "muy alto") y se traduce a una descripción en prosa. Trabajar con descripciones en vez de puntajes produce narrativas más matizadas y coherentes [24].
- Se descarta el MBTI: divide en dos rasgos que son continuos, tiene baja confiabilidad al repetir el test y casi no se usa en la psicología académica.

**Capa 3. Qué valora (valores y política).**
- Valores de Schwartz, con mayor peso en autotrascendencia y conservación [20].
- Ideología (eje izquierda-derecha) e identificación partidaria, por separado.
- Evaluación del gobierno actual (aprueba o desaprueba). Cadem la mide cada semana, así que es fácil de calibrar.
- Confianza institucional: en el gobierno, el Congreso y el Estado en general. Calibrable con la encuesta CEP y el Latinobarómetro.

**Capa 4. Cómo lo afecta esta ley (afectación directa).** Se calcula para cada proyecto a partir de las capas anteriores. Para Sala Cuna Universal:
- Tiene hijos menores de dos años, o planea tenerlos.
- Situación laboral: dependiente con contrato indefinido (cambia su seguro de cesantía), independiente (pagaría 0,3%), trabajadora de casa particular (cambia su fecha de ingreso).
- Es empleador, y el tamaño de su empresa (sobre 100.000 UF de ingresos al año).
- Tramo del Registro Social de Hogares (define si recibe ayuda para el copago).
- Si hay una sala cuna cercana.

### 3.3 Cómo se le entrega el perfil al LLM
- **Prosa, no números.** Cada atributo se traduce a lenguaje natural ("eres curioso y estás dispuesto a probar cosas nuevas"), siguiendo el método de Nemotron-Personas [24].
- **Población estadísticamente fundada.** Los agentes se construyen desde distribuciones reales y no se inventan a mano, como proponen [8] y [10].

---

## 4. Encuesta a los agentes

Regla: la encuesta es fija. Son cinco preguntas cerradas, todas de 1 a 7, y cada una con su propia escala, que el modelo lee al lado de la pregunta.

### 4.1 Preguntas cerradas
1. **Apoyo.** ¿Estarías de acuerdo con que se implemente esta política en tu región? (1 = totalmente en desacuerdo, 7 = totalmente de acuerdo)
2. **Justicia.** ¿Te parece justa la forma en que esta política reparte costos y beneficios? (1 = muy injusto, 7 = muy justo)
3. **Confianza.** ¿Confías en que el Estado chileno sea capaz de implementar bien esta política? (1 = muy desconfiado, 7 = muy confiado)
4. **Efectividad.** ¿Qué tan efectiva crees que es esta política en lograr lo que propone? (1 = muy inefectivo, 7 = muy efectivo)
5. **Influencia.** ¿Qué tan influyente es esta política en tu situación personal o la de tu hogar? (1 = nada influyente, 7 = muy influyente)

La pregunta 2 mide justicia percibida y la 4 efectividad percibida, los dos determinantes más fuertes [15]. La 3 mide confianza [21]. La 5 no mide apoyo: dice cuánto le toca la política a la persona, para separar a quienes opinan con algo en juego de quienes opinan de lejos.

Los resultados anteriores a esta encuesta (hasta el 21-11-2026) usaban otras preguntas y una sola escala de acuerdo: p2 era satisfacción, p5 cumplimiento y p6 «¿va a lograr lo que se propone?». Solo p1 es la misma pregunta con la misma escala. No compares esos archivos clave a clave con los nuevos.

### 4.2 Preguntas abiertas
1. ¿Cómo crees que esta política afectaría tu situación personal o la de tu hogar?
2. ¿Cómo crees que afectaría a tu comunidad o región?
3. ¿Qué cambiarías de esta política para apoyarla más, o cuál es tu principal preocupación?
4. ¿Qué estarías dispuesto a hacer frente a esta política?

La efectividad percibida, el otro determinante principal [15], ya es la pregunta cerrada 4.

### 4.3 Métricas
- **Índice de aceptación:** promedio de las preguntas cerradas 1 a 4 (apoyo, justicia, confianza y efectividad), por variante, región y perfil. Influencia no entra.
- **Justificación breve** (1 o 2 frases) después de cada respuesta cerrada, para auditar la coherencia de cada agente con su perfil.
- **Medición antes y después:** las preguntas 1 y 4 se hacen también antes de mostrar la política, como línea base.

---

## 5. Diseño de las variantes: caso Sala Cuna Universal

### 5.1 Estado del proyecto
El Senado lo despachó en septiembre de 2026 y la Cámara lo devolvió el 18 de noviembre con cambios. El Senado solo puede aprobar o rechazar esos cambios; si rechaza alguno, el proyecto va a comisión mixta. Las normas de financiamiento requieren un quórum de 78 votos [26].

Núcleo común: ambas versiones eliminan la regla que obliga a dar sala cuna solo a las empresas con 20 o más trabajadoras [26].

### 5.2 Diferencias entre las versiones reales [26]

| Atributo | Versión Senado (sep 2026) | Versión Cámara (nov 2026) |
|---|---|---|
| Financiamiento | Fondo sin ingresos permanentes: rentabilidad, multas y garantía del Estado | Cotización de 0,3% del empleador, compensada con una rebaja de la cotización al seguro de cesantía de 2,4% a 2,1% en contratos indefinidos |
| Independientes | Fecha de ingreso, sin monto de cotización | Pagan 0,3% de la renta imponible en la declaración anual |
| Copago | Las familias pagan la diferencia | Suplemento solidario: 50% de la diferencia para el 40% más vulnerable del RSH y 30% para el tramo hasta el 60%, desde el mes 18 |
| Tope al copago | No hay | El Gobierno se comprometió a un tope de 20% en un proyecto aparte |
| Transición de empresas | Todas dejan de estar obligadas en el mes 12 | Las grandes (más de 100.000 UF) siguen hasta el mes 48 |
| Trabajadoras de casa particular | Entran en el mes 24 | Entran en el mes 12 |
| Titularidad del derecho | El niño o niña | El trabajador o trabajadora |

### 5.3 Variantes A a E

**Decisión de diseño:** se fija el núcleo y se varían tres atributos (financiamiento, copago y transición), para saber qué atributo explica una diferencia. Es la lógica factorial del protocolo de Lerer [9].

| Variante | Financiamiento | Copago | Transición |
|---|---|---|---|
| A · Senado | Fondo sin cotización | Sin ayuda | Todas salen en el mes 12 |
| B · Cámara | Cotización 0,3% | Suplemento solidario | Grandes hasta el mes 48 |
| C · Cámara + tope | Cotización 0,3% | Suplemento y tope de 20% | Grandes hasta el mes 48 |
| D · Sin copago | Cotización 0,3% | El fondo cubre todo | Grandes hasta el mes 48 |
| E · Híbrida | Fondo sin cotización | Suplemento solidario | Todas salen en el mes 12 |

A y B son textos reales, C es un compromiso del Gobierno, y D y E son variantes de contraste.

### 5.4 Con y sin etiqueta de quién propone
**Decisión de diseño:** cada variante se corre dos veces.
1. **Sin etiqueta:** el texto solo. Mide el efecto del contenido.
2. **Con etiqueta:** "propuesta del Gobierno" o "propuesta de la oposición". Mide cómo se recibirá en la realidad, dado el efecto de la señal partidaria [18][19].

Si una variante gana en las dos condiciones, el resultado es sólido. Si solo gana sin etiqueta, la política es buena pero necesita comunicarse bien.

---

## 6. Validación y calibración

### 6.1 Sesgos conocidos de los LLM
- Las predicciones de los LLM se correlacionan fuerte con los efectos reales en humanos, pero sobreestiman sistemáticamente su tamaño [27].
- En un experimento con datos reales, las respuestas de LLM sin calibrar recuperaron solo un 39% del efecto observado en humanos [28].
- Reproducir el resultado agregado o acertar el signo no basta para reemplazar a encuestados humanos [29].

### 6.2 Cómo corregirlos
- **Calibración con una muestra humana pequeña.** Las estimaciones poblacionales se pueden corregir hasta quedar dentro de un 5% de sesgo con apenas unas 100 respuestas humanas, cerca del 1% de una encuesta completa [30]. En otro estudio, un modelo calibrado con el 10% de las regiones estimó un efecto de −65 ±10 puntos base, frente a −60 ±8 del experimento humano completo [31].
- **Robustez.** **Decisión de diseño:** correr todo con 2 o 3 modelos y varias redacciones del prompt, y reportar el resultado solo si el ranking se mantiene.
- **Qué se afirma.** **Decisión de diseño:** ranking y dirección ("la C supera a la A en todas las regiones"), no porcentajes exactos.

### 6.3 Benchmarks para validar contra datos reales
Para comparar, las respuestas de 5 a 7 cuentan como "de acuerdo" y las de 1 a 3 como "en desacuerdo".

**Sala Cuna Universal (validación directa):**
- 72% de acuerdo con la iniciativa (Cadem, mayo 2026) [32]; 74% de aprobación y 8% en desacuerdo, igual en hombres y mujeres (Criteria, junio 2026) [33].
- 68% quiere que el Congreso lo apruebe de manera urgente, y 84% está de acuerdo con extender el derecho a madres dependientes, independientes, de casa particular y a los padres [34].
- 62% cree que debe ser un derecho de los niños y 32% un beneficio laboral de la madre [35]. Valida directamente el atributo de titularidad.
- 48% prefiere aprobarlo ahora como está y 39% seguir debatiendo, aunque se postergue [36].
- En 2023, 89% creía que las salas cuna deben financiarse con impuestos generales del Estado [37]. Es el dato más cercano para contrastar con la cotización de 0,3%.

**Techo histórico de aprobación:**

| Política | % de acuerdo | Fuente |
|---|---|---|
| Segundo retiro del 10% de las AFP | 87% (11% en desacuerdo) | Cadem, nov 2020 [38] |
| Aprobación en la Cámara del primer retiro | 86% | Cadem, jul 2020 [39] |
| Subir la PGU a $250 mil | 86% (12% en contra) | Cadem, ene 2025 [40] |
| Primer retiro del 10% | 83% | Cadem, jul 2020 [41] |
| 40 horas | 75% (Cadem, 2019) [42]; 74,2% a favor, 8,6% en contra (Pulso Ciudadano, mar 2023) [43] | |
| PGU, proyecto original | 70% | Cadem, dic 2021 [44] |
| Reforma de pensiones, ya aprobada | 65% (30% en desacuerdo) | Cadem, feb 2025 [45] |

**Piso:**
- Megarreforma del gobierno actual: 44% de acuerdo y 50% en desacuerdo (Cadem, mayo 2026) [46].
- Postergar la edad de jubilación: 78% en desacuerdo (Cadem, junio 2024) [47].

**Uso de los benchmarks:**
1. Antes de comparar variantes, preguntarle al Chile sintético lo mismo que Cadem y Criteria, y verificar que se acerca al 72–74% general y al 62/32 de titularidad.
2. Usar el rango real (de 44% a 87%) como prueba de sanidad. Si el modelo le da más de 90% a todo, está sesgado hacia el acuerdo.

### 6.4 La satisfacción no es el único objetivo
El techo histórico son los retiros de las AFP, muy populares pero dañinos para el ahorro previsional. **Decisión de diseño:** la satisfacción se presenta como un objetivo junto a otros (costo fiscal, personas beneficiadas), no como el único criterio para elegir una variante.

---

## 7. Usuarios

| Segmento | Por qué le sirve What If Chile | Evidencia |
|---|---|---|
| **Principal: el Ejecutivo que diseña la ley** (Segpres y el ministerio a cargo) | Redacta las indicaciones y negocia los votos. Ya está obligado a anticipar el impacto en la sociedad, pero el IIR no mide la aceptación | IIR obligatorio desde 2019 [2], revisado por la Segpres antes del ingreso al Congreso [48] |
| **Institucional: CNEP y la futura Agencia para la Calidad de las Políticas Públicas** (Boletín 16.799-05) | What If Chile sirve como componente previo (¿la aceptarán y cumplirán?) y como punto de comparación una vez implementada la ley (¿pasó lo predicho?) | La CNEP reconoce el vacío [1][3]; el proyecto de la Agencia se discute desde 2024 [49] e incluye evaluar políticas por su eficacia y coordinar la evaluación previa [50] |
| **Técnico: asesorías del Congreso** (comisiones, Biblioteca del Congreso) | Muestra representativa y síntesis de objeciones, en vez de opiniones autoseleccionadas que nadie procesa | [4][5] |
| **Público: la ciudadanía** | "¿Cómo me afecta esta ley?" según su perfil y región. Versión gratuita y abierta | En septiembre, 76% sabía que el Senado había aprobado Sala Cuna Universal [51] |
| **Otros** | Centros de estudio, ONG, gremios, gobiernos regionales y encuestadoras | Por validar |

El Congreso no es el usuario que decide: un ranking no cambia votos. Su uso es técnico.

**Pendiente:** todo lo anterior prueba que existe la necesidad, no que estas instituciones vayan a comprar. Conviene validarlo con entrevistas a asesores legislativos o a personas que hayan trabajado en la Segpres o la CNEP.

---

## 8. Fuentes de datos para calibrar

| Uso | Fuente |
|---|---|
| Perfil sociodemográfico por región | CASEN, Censo 2024 |
| Actitudes, confianza e ideología | Encuesta CEP [14], Latinobarómetro |
| Aprobación del gobierno y de políticas | Cadem Plaza Pública, Criteria |
| Seguimiento de proyectos de ley | Senado, Cámara y parlamento.ai [52] |
| Método de personas sintéticas | Nemotron-Personas (NVIDIA) [24] |

---

## Referencias

1. Ex-Ante (2026). "Comisión para la Productividad: Chile tiene más de 400 mil normas, pero no evalúa si funcionan". https://www.ex-ante.cl/comision-para-la-productividad-chile-tiene-mas-de-400-mil-normas-pero-no-evalua-si-funcionan/
2. Pauta (2019). "La novedad de los proyectos de ley: ahora tendrán un Informe Regulatorio". https://www.pauta.cl/economia/2019/04/23/la-novedad-de-los-proyectos-de-ley-ahora-tendran-un-informe-regulatorio.html
3. CNEP (2026). Comunicado de prensa, 8 de mayo: "Guía para la Evaluación Ex Post de Regulaciones". https://media-front.elmostrador.cl/2026/05/COMUNICADO-PRENSA-COMISIÓN-NACIONAL-DE-EVALUACIÓN-Y-PRODUCTIVAD-VIERNES-8-DE-MAYO-2026.docx
4. Hermosilla, M. P. "Inteligencia artificial y participación ciudadana", ParlAmericas. https://www.parlamericas.org/uploads/documents/MariaPazHermosilla_inteligencial_artificial.pp_.pdf
5. Open Government Partnership. "Participación Ciudadana en el Congreso Virtual (CL0081)". https://www.opengovpartnership.org/es/members/chile/commitments/CL0081/
6. Piao, J. et al. "From Individual to Society: A Survey on Social Simulation Driven by LLM-based Agents" (revisión que describe el aporte de Argyle et al.). https://arxiv.org/pdf/2412.03563
7. Piao, J. et al. (2025). "AgentSociety: Large-Scale Simulation of LLM-Driven Generative Agents". https://arxiv.org/abs/2502.08691 · Código: https://github.com/tsinghua-fib-lab/agentsociety/
8. "From Survey Personas to LLM Agents: A Generative Agent-based Simulation of Mobility Policy Preference Dynamics" (2026). https://arxiv.org/pdf/2608.07519
9. Lerer, A. (2026). "Eight Billion Synthetic People Are Still Not Evidence". https://adrianlerer.substack.com/p/eight-billion-synthetic-people-are · Código: github.com/adrianlerer/prelegislative-sim-to-real-argentina
10. UC Berkeley School of Information (2026). "CivicSim: Synthetic Personas for Inclusive Policy Testing". https://www.ischool.berkeley.edu/programs/mims/projects/2026/civicsim-synthetic-personas-inclusive-policy-testing
11. Enterprise DNA (2026). "Simile, which builds AI simulations of consented real people". https://enterprisedna.co/resources/ai-pulse/ai-pulse-2026-08-05-simile-which-builds-ai-simulations-of-consented-real-people/
12. Artificial Societies. https://societies.ai/solutions
13. MiroFish. "Policy Impact Simulation with AI". https://mirofish.us/use-cases/policy-impact-simulation
14. González-Bustamante, B., Verelst, N. y Cisternas, C. (2025). "Emulating Public Opinion: A Proof-of-Concept of AI-Generated Synthetic Survey Responses for the Chilean Case". https://arxiv.org/abs/2509.09871
15. Bergquist, M. et al. (2022). "Meta-analyses of fifteen determinants of public opinion about climate change taxes and laws". Nature Climate Change. https://dx.doi.org/10.1038/s41558-022-01297-6
16. Sears, D. O., Lau, R. R., Tyler, T. R. y Allen, H. M. (1980). "Self-Interest vs. Symbolic Politics in Policy Attitudes and Presidential Voting". American Political Science Review. https://www.cambridge.org/core/journals/american-political-science-review/issue/9FB8AE69D8D7055A3B0C7392045A28A8
17. (2009). "Self-Interest, Symbolic Attitudes, and Support for Public Policy: A Multilevel Analysis". Political Psychology. https://works.bepress.com/caroline_heldman/3
18. "Can Awareness Disrupt Partisan Bias In Policy Evaluation?" (2026). Journal of Politics blog. https://ubwp.buffalo.edu/jopblog/?p=538
19. Mullinix, K., resumido en LSE USAPP (2017). "Political parties shape public opinion, but their influence is limited". https://blogs.lse.ac.uk/usappblog/2017/04/18/political-parties-shape-public-opinion-but-their-influence-is-limited/
20. Goren, P. et al. "A Unified Theory of Value-Based Reasoning and Public Opinion". https://ore.exeter.ac.uk/repository/bitstream/10871/21586/1/A%20Unified%20Theory%20of%20Value-Based%20Reasoning%20and%20Public%20Opinion.pdf
21. Devine, D. (2024). "Does Political Trust Matter? A Meta-analysis on the Consequences of Trust". Political Behavior. https://link.springer.com/article/10.1007/s11109-024-09916-y
22. Maestre-Andrés, S., Drews, S. y van den Bergh, J. (2019). "Perceived fairness and public acceptability of carbon pricing: a review of the literature". Climate Policy. https://research.vu.nl/en/publications/perceived-fairness-and-public-acceptability-of-carbon-pricing-a-r/
23. Petrow, G. A. y Vercellotti, T. "How Our Life Experiences Affect Our Politics: The Roles of Vested Interest and Affect in Shaping Policy Preferences". https://core.ac.uk/download/232759761.pdf
24. Meyer, Y. y Corneil, D. (NVIDIA). "Designing Nemotron-Personas". https://docs.nvidia.com/nemo/datadesigner/v0.9.3/dev-notes/designing-nemotron-personas.md
25. "When and Why Do People Accept Public-Policy Interventions? An Integrative Public-Policy-Acceptance Framework". Perspectives on Psychological Science. https://www.psychologicalscience.org/journals/perspectives/17456916231180580/
26. Emol (18-11-2026). "Con financiamiento y sin el derecho de los niños: así vuelve al Senado la Sala Cuna Universal". https://www.emol.com/noticias/Economia/2026/11/18/1217493/sala-cuna-tercer-tramite-senado.html
27. "Consequential Behaviour and Representational Fairness in the Validation of Synthetic Research" (2026), que cita a Ashokkumar et al. (2026). https://arxiv.org/pdf/2609.27690
28. Persson, J. (2026). "Statistical Foundations of LLM-based A/B Testing: A Surrogacy Framework for Human Causal Inference". https://arxiv.org/pdf/2606.17165
29. "Multi-dimensional Bias in Modeling Multi-dimensional Preferences: Evaluating the Ability of Synthetic Agents to Replace Human Participants in Conjoint Experiments" (2026). https://arxiv.org/pdf/2609.04243
30. "Valid Survey Simulations with Limited Human Data" (2025). https://arxiv.org/html/2510.11408v2
31. "Agentic Economic Modeling" (2025). https://arxiv.org/html/2510.25743v1
32. G5 Noticias (31-05-2026), sobre Cadem. https://g5noticias.cl/2026/05/31/cadem-semanal-presidente-kast-cierra-el-mes-con-un-promedio-de-39-3pts-de-aprobacion-y-56-4pts-de-desaprobacion/
33. Ex-Ante (2026), sobre Criteria. https://www.ex-ante.cl/?p=360602
34. Ex-Ante (2026), sobre Cadem. https://www.ex-ante.cl/?p=377567
35. BioBioChile (16-09-2026), sobre Cadem. https://www.biobiochile.cl/noticias/nacional/chile/2026/09/16/61-desaprueba-el-gobierno-de-jose-antonio-kast-y-solo-un-35-lo-respalda-segun-cadem.shtml
36. Meganoticias (20-09-2026), sobre Cadem. https://www.meganoticias.cl/nacional/532078-cadem-aprobacion-proyecto-sala-cuna-universal-kast-ministro-quiroz-20-09-2026.html
37. Radio Agricultura (26-12-2023), sobre Cadem. https://www.radioagricultura.cl/economia/2023/12/26/encuesta-cadem-89-prefiere-financiar-las-salas-cunas-con-impuestos-generales/
38. Meganoticias (nov 2020), sobre Cadem. https://www.meganoticias.cl/nacional/318458-encuesta-cadem-primer-retiro-fondos-pensiones-afp-jdx14.html
39. Meganoticias (jul 2020), sobre Cadem. https://www.meganoticias.cl/nacional/308110-encuesta-cadem-retiro-10-fondos-pensiones-afp-proyecto-coronavirus-jdx14.html
40. Meganoticias (19-01-2025), sobre Cadem. https://www.meganoticias.cl/nacional/473239-cadem-reforma-de-pensiones-gobierno-gabriel-boric-congreso-aprueba-desaprueba-fds01-19-01-2025.html
41. BioBioChile (06-07-2020), sobre Cadem. https://www.biobiochile.cl/noticias/nacional/chile/2020/07/06/amp/cadem-83-esta-de-acuerdo-en-retirar-10-de-las-afp-colegio-medico-la-institucion-mejor-evaluada.shtml
42. El Ciudadano (2019), sobre Cadem. https://www.elciudadano.com/?p=621479
43. T13 (25-03-2023), sobre Pulso Ciudadano. https://www.t13.cl/noticia/politica/pulso-ciudadano-74-2-esta-favor-ley-40-horas-laborales-25-3-2023
44. Meganoticias (12-12-2021), sobre Cadem. https://www.meganoticias.cl/nacional/361185-encuesta-cadem-pension-garantizada-universal-aprobacion-fondos-de-pensiones-12-12-2021.html
45. Meganoticias (02-02-2025), sobre Cadem. https://www.meganoticias.cl/nacional/474584-cadem-aprobacion-reforma-pensiones-congreso-nacional-pgu-menor-comision-fds01-02-02-2025.html
46. BioBioChile (14-05-2026), sobre Cadem. https://www.biobiochile.cl/noticias/nacional/chile/2026/05/14/cadem-ningun-area-del-gobierno-supera-el-50-de-aprobacion-y-megarreforma-presenta-mas-desacuerdo.shtml
47. Meganoticias (09-06-2024), sobre Cadem. https://www.meganoticias.cl/nacional/449688-encuesta-cadem-pensiones-reforma-previsional-atrasar-edad-de-jubilacion-fondos-afp-fds01-09-06-2024.html
48. OCDE. "Chile: Evaluation Report" (política regulatoria). https://t4.oecd.org/gov/regulatory-policy/Chile-Evaluation-Full-Report-web.pdf
49. Centro de Políticas Públicas UC (2026). "Modernizar el Estado. Una agenda prioritaria de corto plazo". https://politicaspublicas.uc.cl/web/content/uploads/2026/04/Modernizar-el-Estado.-Una-agenda-prioritaria-de-corto-plazo.pdf
50. Ministerio de Hacienda. "Cámara aprobó el proyecto que crea la Agencia para la Calidad de las Políticas Públicas y la Productividad". https://www.hacienda.cl/noticias-y-eventos/noticias/camara-aprobo-el-proyecto-que-crea-la-agencia-para-la-calidad-de-las-politicas
51. Pauta (17-09-2026), sobre Cadem. https://www.pauta.cl/actualidad/2026/09/17/cadem-87-cree-que-la-sala-cuna-universal-ayudaria-a-que-mas-mujeres-puedan-trabajar.html
52. parlamento.ai, ficha del boletín 16821-19. https://parlamento.ai/cl/bill/16821-19
