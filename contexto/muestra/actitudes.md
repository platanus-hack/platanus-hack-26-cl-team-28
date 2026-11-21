# Actitudes políticas imputadas desde la Encuesta CEP

`data/muestra/actitudes.parquet` tiene una fila por cada persona de 18 años o más de la muestra del 1 % (144.528 personas), con actitudes copiadas de un entrevistado parecido de la Encuesta CEP N° 96 (abril-mayo de 2026, 1.466 entrevistas presenciales).
Se une a la muestra por `id_persona_muestra`.

**No son las opiniones de esa persona.** Son las de un entrevistado de la CEP con su mismo perfil, sorteado al azar. Sirven para que la población sintética tenga la misma mezcla de posiciones que el país y la misma relación con la edad, la educación, la religión y el nivel socioeconómico. No sirven para afirmar nada de un registro en particular.

## Cómo se construyó

Cada persona recibe un donante de la CEP de su misma celda, sorteado con probabilidad proporcional a su ponderador (`pond`). Las celdas se definen por las llaves de la tabla; si una celda tiene menos de 3 donantes, se pasa al nivel siguiente.

| Nivel | Llaves | Personas | % |
|---|---|---|---|
| 1 | sexo, edad7, educ4, macro, nse3, activ, rel4 | 25.084 | 17,4 |
| 2 | sexo, edad7, educ4, macro, nse3, rel4 | 18.582 | 12,9 |
| 3 | sexo, edad7, educ4, nse3, rel4 | 57.632 | 39,9 |
| 4 | sexo, edad7, educ4, rel4 | 28.749 | 19,9 |
| 5 | sexo, edad7, educ4 | 13.083 | 9,1 |
| 6 | sexo, edad3, educ4 | 492 | 0,3 |
| 7 | sexo, edad3 | 906 | 0,6 |
| 8 | (ninguna) | 0 | 0,0 |

- `edad7`: 18-24, 25-34, 35-44, 45-54, 55-64, 65-74 y 75 o más. `edad3`: 18-34, 35-54 y 55 o más.
- `educ4`: nivel completo (menos que media, media, técnica, universitaria). En el censo sale de `cine11`.
- `macro`: macrozona (norte, centro, Región Metropolitana, sur, austral), la misma de la imputación de Casen.
- `nse3`: en la CEP, el grupo socioeconómico (D y E; C3; C2 y ABC1). En la muestra, el decil de ingreso cortado para dejar la misma proporción de personas en cada tramo: deciles 1 a 1, 2 a 6 y 7 a 10. Son medidas distintas del nivel socioeconómico; se empareja por posición relativa.
- `activ`: trabaja, busca trabajo o está fuera de la fuerza de trabajo.
- `rel4`: católica, evangélica, ninguna u otra. En el censo sale de `p31_religion`, que viene suprimida en algunos registros.

Todas las columnas de una persona vienen del mismo donante. La semilla está fija (`SEMILLA`).

## Columnas

Los códigos son los de la CEP: `-8` es no sabe y `-9` es no contesta. Las etiquetas están en `etiquetas_cep.csv`.

| Columna | Variable CEP | Contenido |
|---|---|---|
| `posicion_politica` | `iden_pol_2` | Escala de 1 (izquierda) a 10 (derecha). |
| `partido` | `iden_pol_3` | Partido con el que más se identifica o simpatiza. |
| `aprueba_gobierno` | `eval_gob_1` | Aprueba o desaprueba cómo el presidente conduce el gobierno (José Antonio Kast, en abril-mayo de 2026). |
| `confianza_gobierno` | `confianza_6_i` | Confianza en el gobierno. |
| `confianza_congreso` | `confianza_6_k` | Confianza en el Congreso. |
| `confianza_municipalidades` | `confianza_6_o` | Confianza en las municipalidades. |
| `responsabilidad_sustento` | `pobreza_63` | De 1 (el sustento económico de las personas es responsabilidad del Estado) a 10 (de las personas mismas). |
| `interes_politica` | `interes_pol_1_b` | Cuán interesado está en la política. |
| `voto_segunda_vuelta_2025` | `elec_pres_155` | Voto en la segunda vuelta presidencial de diciembre de 2025. Nulo para quien dijo no haber votado. |
| `aprueba_gobierno_anterior` | `eval_gob_63` | Independientemente de su posición política, ¿usted aprueba o desaprueba la forma como Gabriel Boric condujo su gobierno? |
| `votaria_voluntario` | `elec_part_10` | ¿Habría Ud. concurrido a votar de no haber sido obligatorio? |
| `fuente_noticias` | `interes_pol_27` | ¿De dónde obtiene la mayor parte de las noticias sobre temas políticos? Por favor, seleccione la fuente más importante. |
| `problema_1` | `percepcion_1_a` | A continuación le mostraré una serie de problemas que tiene nuestro país. ¿Cuáles son los tres problemas a los que debería dedicar mayor esfuerzo en solucionar el gobierno? INDIQUE SOLO 3. (Primera mencion) |
| `problema_2` | `percepcion_1_b` | A continuación le mostraré una serie de problemas que tiene nuestro país. ¿Cuáles son los tres problemas a losque debería dedicar mayor esfuerzo en solucionar el gobierno? INDIQUE SOLO 3. (Segunda mencion) |
| `problema_3` | `percepcion_1_c` | A continuación le mostraré una serie de problemas que tiene nuestro país. ¿Cuáles son los tres problemas a losque debería dedicar mayor esfuerzo en solucionar el gobierno? INDIQUE SOLO 3. (Tercera mencion) |
| `rumbo_pais` | `percepcion_4` | ¿Ud. cree que en el momento actual Chile está: progresando, estancado o en decadencia? |
| `situacion_politica` | `percepcion_38` | ¿Cómo calificaría Ud. la actual situación política en Chile: muy buena, buena, ni buena ni mala, mala o muy mala? |
| `apoyo_democracia` | `democracia_21` | ¿Con cuál de las siguientes frases está UD. más de acuerdo? [LA DEMOCRACIA SIEMPRE ES PREFERIBLE A OTRA FORMA DE GOBIERNO … EN ALGUNAS CIRCUNSTANCIAS, UN RÉGIMEN AUTORITARIO PUEDE SER PREFERIBLE… A LA GENTE COMO UNO, LE DA LO MISMO UN REGIMEN DEMOCRATICO QUE UNO AUTORITARIO] |
| `funciona_democracia` | `democracia_20` | ¿Qué tan bien o qué tan mal cree Ud. que funciona la democracia en Chile? |
| `economia_pais` | `percepcion_2` | De acuerdo a la siguiente escala, ¿cómo calificaría Ud. la actual situación económica del país? |
| `economia_pais_futuro` | `percepcion_3` | ¿Ud. piensa que en los próximos 12 meses la situación económica del país mejorará, no cambiará o empeorará? |
| `economia_personal` | `percepcion_5` | De acuerdo a esta escala, ¿cómo calificaría usted SU actual situación económica? |
| `economia_personal_futuro` | `percepcion_6` | Y, pensando en el futuro, ¿cómo cree que será su situación económica en un año más? |
| `ingresos_alcanzan` | `bienestar_21` | Considerando todos los ingresos percibidos por su familia, esto es, todos los ingresos que reciben ustedes, ¿cuál de las frases que aparecen en esta tarjeta cree Ud. que se ajusta mejor a su situación de ingresos? |
| `preocupa_deudas` | `bienestar_13_a` | Considerando la misma escala, en términos generales, en una escala de 0 a 10, donde 0 es nada preocupado y 10 muy preocupado, ¿cuán preocupado está usted las siguientes situaciones? Pagar sus deudas. |
| `preocupa_enfermedad` | `bienestar_13_c` | Considerando la misma escala, en términos generales, en una escala de 0 a 10, donde 0 es nada preocupado y 10 muy preocupado, ¿cuán preocupado está usted las siguientes situaciones? Enfrentar alguna enfermedad grave y no ser capaz de pagar los costos no cubiertos por el sistema de salud. |
| `preocupa_pension` | `bienestar_13_h` | Considerando la misma escala, en términos generales, en una escala de 0 a 10, donde 0 es nada preocupado y 10 muy preocupado, ¿cuán preocupado está usted las siguientes situaciones? Tener una pensión adecuada al momento de jubilarse [en la vejez]. |
| `clase_subjetiva` | `educacion_104_a` | En nuestra sociedad, hay grupos que tienden a ubicarse en los niveles más altos y grupos que tienden a ubicarse en los niveles más bajos. Usando la siguiente escala que va desde el nivel más alto al más bajo, ¿dónde ubicaría a las siguientes personas? USTED |
| `menos_estado_economia` | `democracia_33_a` | A continuación voy a leerle varias afirmaciones. Después de cada uno de ellas me gustaría que me dijera si usted está muy de acuerdo, de acuerdo, ni de acuerdo ni en desacuerdo, en desacuerdo o muy en desacuerdo con la frase. Este país estará mejor mientras menos participe el Estado en la economía. |
| `estado_burocracia` | `democracia_33_d` | A continuación voy a leerle varias afirmaciones. Después de cada uno de ellas me gustaría que me dijera si usted está muy de acuerdo, de acuerdo, ni de acuerdo ni en desacuerdo, en desacuerdo o muy en desacuerdo con la frase. La intervención del Estado lleva a demasiada burocracia y muchos problemas. |
| `reducir_gasto_publico` | `rol_gobierno_31` | ¿Qué tan de acuerdo o en desacuerdo está usted con la estrategia del gobierno de reducir el gasto público para mejorar la situación de las finanzas públicas? |
| `empleados_publicos` | `rol_gobierno_28` | En su opinión, el número de empleados públicos en Chile es: |
| `libertades_o_seguridad` | `democracia_38` | ¿Dónde se ubicaría Ud. en esta escala, en que 0 significa “Se deben garantizar todas las libertades públicas y privadas, aunque eso impida controlar la delincuencia” y 10 significa que “Se deben suprimir todas las libertades públicas y privadas para controlar la delincuencia”? |
| `causa_delincuencia` | `seguridad_37_a` | Ahora, hablando sobre la delincuencia en Chile, ¿cuáles cree Ud. que son sus tres principales causas? (Primera mención) |
| `justifica_marchas` | `ciudadania_29_a` | Me gustaría preguntarle sobre acciones que la gente hace para protestar contra algo que le parece injusto. ¿Con qué frecuencia usted justificaría o no justificaría las siguientes acciones? Participar de una marcha como forma de protesta |
| `justifica_fuerza_carabineros` | `ciudadania_30_b` | Ahora, me gustaría preguntarle sobre conductas de Carabineros. ¿Con qué frecuencia usted justificaría o no las siguientes acciones para controlar la violencia en manifestaciones? Que Carabineros use la fuerza contra un manifestante violento |
| `apertura_inmigracion` | `iden_nacional_16` | Pensando en las políticas que debe tener Chile con respecto a la inmigración, en una escala del 1 al 10, donde 1 es prohibir toda inmigración y 10 es permitir libremente toda inmigración. Donde su ubicaría Ud |
| `inmigrantes_criminalidad` | `iden_nacional_8_a` | Existen distintas opiniones acerca de los inmigrantes de otros países que viven en Chile. Por inmigrantes nos referimos a los extranjeros que vienen a establecerse en Chile. ¿Cuán de acuerdo o en desacuerdo está Ud. con las siguientes afirmaciones? Los inmigrantes elevan los índices de criminalidad. |
| `inmigrantes_aporte` | `iden_nacional_8_l` | Existen distintas opiniones acerca de los inmigrantes. Por inmigrantes nos referimos a los extranjeros que vienen a establecerse en Chile. ¿Cuán de acuerdo o en desacuerdo está Ud. con las siguientes afirmaciones? Los inmigrantes son un aporte para la economía de Chile |
| `hijos_ideal` | `mtf_84` | Y pensando en el número ideal de hijos ¿cuántos hijos hubiera querido o quisiera tener? |
| `hijos_carga_financiera` | `mtf_46_d` | ¿Cuán de acuerdo o en desacuerdo está usted con las siguientes afirmaciones? Los hijos son una carga financiera para sus padres. |
| `hijos_restringen_carrera` | `mtf_46_e` | ¿Cuán de acuerdo o en desacuerdo está usted con las siguientes afirmaciones? Tener hijos restringe las posibilidades de trabajo y carrera de uno o ambos padres. |
| `confianza_fuerzas_armadas` | `confianza_6_c` | A continuación le voy a leer los nombres de algunas instituciones. De acuerdo con las alternativas de la tarjeta, ¿podría usted decirme cuánta confianza tiene en cada una de ellas? Veamos… LAS FUERZAS ARMADAS |
| `confianza_carabineros` | `confianza_6_h` | A continuación le voy a leer los nombres de algunas instituciones. De acuerdo con las alternativas de la tarjeta, ¿podría usted decirme cuánta confianza tiene en cada una de ellas? Veamos… LOS CARABINEROS |
| `confianza_tribunales` | `confianza_6_d` | A continuación le voy a leer los nombres de algunas instituciones. De acuerdo con las alternativas de la tarjeta, ¿podría usted decirme cuánta confianza tiene en cada una de ellas? Veamos… LOS TRIBUNALES DE JUSTICIA |
| `confianza_partidos` | `confianza_6_j` | A continuación le voy a leer los nombres de algunas instituciones. De acuerdo con las alternativas de la tarjeta, ¿podría usted decirme cuánta confianza tiene en cada una de ellas? Veamos… LOS PARTIDOS POLITICOS |
| `confianza_empresas` | `confianza_6_s` | A continuación le voy a leer los nombres de algunas instituciones. De acuerdo con las alternativas de la tarjeta, ¿podría usted decirme cuánta confianza tiene en cada una de ellas? Veamos… LAS EMPRESAS PRIVADAS |
| `confianza_sindicatos` | `confianza_6_g` | A continuación le voy a leer los nombres de algunas instituciones. De acuerdo con las alternativas de la tarjeta, ¿podría usted decirme cuánta confianza tiene en cada una de ellas? Veamos… LOS SINDICATOS |
| `confianza_sistema_salud` | `confianza_6_ab` | A continuación le voy a leer los nombres de algunas instituciones. De acuerdo con las alternativas de la tarjeta, ¿podría usted decirme cuánta confianza tiene en cada una de ellas? Veamos… El sistema de salud |
| `confianza_sistema_pensiones` | `confianza_6_ac` | A continuación, le voy a leer los nombres de algunas instituciones. De acuerdo con las alternativas de la tarjeta, ¿cuánta confianza tiene Ud. en cada una de ellas? El sistema de pensiones |
| `confianza_television` | `confianza_6_f` | A continuación le voy a leer los nombres de algunas instituciones. De acuerdo con las alternativas de la tarjeta, ¿podría usted decirme cuánta confianza tiene en cada una de ellas? Veamos… LA TELEVISION |
| `confianza_redes_sociales` | `confianza_6_x` | A continuación le voy a leer los nombres de algunas instituciones. De acuerdo con las alternativas de la tarjeta, ¿podría usted decirme cuánta confianza tiene en cada una de ellas? Veamos… REDES SOCIALES COMO WHATSAPP, FACEBOOK, TWITTER O INSTAGRAM |
| `confianza_iglesia_catolica` | `confianza_6_a` | A continuación le voy a leer los nombres de algunas instituciones. De acuerdo con las alternativas de la tarjeta, ¿podría usted decirme cuánta confianza tiene en cada una de ellas? Veamos… LA IGLESIA CATOLICA |
| `confianza_universidades` | `confianza_6_m` | A continuación le voy a leer los nombres de algunas instituciones. De acuerdo con las alternativas de la tarjeta, ¿podría usted decirme cuánta confianza tiene en cada una de ellas? Veamos… LAS UNIVERSIDADES |
| `nivel_match_cep` |  | Nivel en que se encontró al donante (1 el más específico). |
| `cep_id_donante` | `id_bu` | Entrevistado de la CEP del que se copiaron los datos. |

## Límites

- **Solo se conserva lo que explican las llaves.** La relación entre una actitud y cualquier otro dato de la muestra (comuna, previsión, tipo de vivienda, hijos) existe solo a través del sexo, la edad, la educación, la zona, el nivel socioeconómico, la actividad y la religión.
- **Regiones.** La CEP tiene 1.466 casos: es representativa del país, no de cada región. La región entra como macrozona.
- **Fechas.** El censo es de marzo a julio de 2024 y la CEP de abril y mayo de 2026. La evaluación del gobierno es la de ese momento.
- **Personas fuera de hogares** (viviendas colectivas y situación de calle): no tienen decil, así que se emparejan sin nivel socioeconómico. La CEP no las cubre.
- **Coyuntura.** Varias opiniones son del momento de la encuesta (situación económica, rumbo del país, problemas prioritarios, evaluación del gobierno): describen abril y mayo de 2026.
- **No incluye** valores de Schwartz ni personalidad: la CEP no los mide. Lo más cercano son `responsabilidad_sustento`, `menos_estado_economia` y `libertades_o_seguridad`.

## Validación

Porcentaje de cada respuesta en la CEP (ponderada) y en la muestra con los datos imputados. Deben parecerse; la diferencia que queda viene de que la muestra tiene otra composición por edad, educación y zona que la CEP ponderada.

### `posicion_politica`

| Respuesta | CEP % | Muestra % |
|---|---|---|
| No contesta | 6,4 | 5,9 |
| No sabe | 9,7 | 10,5 |
| 1 Izquierda | 7,4 | 7,6 |
| 2 | 1,7 | 1,6 |
| 3 | 5,1 | 5,3 |
| 4 | 6,7 | 6,3 |
| 5 | 32,5 | 33,5 |
| 6 | 8,9 | 8,3 |
| 7 | 6,5 | 6,7 |
| 8 | 4,9 | 4,7 |
| 9 | 1,3 | 1,0 |
| 10 Derecha | 8,9 | 8,5 |

### `partido`

| Respuesta | CEP % | Muestra % |
|---|---|---|
| No contesta | 1,8 | 1,2 |
| No sabe | 1,6 | 2,3 |
| Democracia Cristiana | 6,3 | 6,0 |
| Partido Comunista | 4,1 | 4,1 |
| Partido Por la Democracia | 1,1 | 1,1 |
| Partido Socialista | 6,8 | 6,1 |
| Renovación Nacional | 3,9 | 4,5 |
| Unión Demócrata Independiente | 2,1 | 2,2 |
| Otros | 0,3 | 0,1 |
| Ninguno | 52,1 | 53,7 |
| Partido de la Gente | 6,8 | 6,0 |
| Partido Republicano | 6,4 | 5,7 |
| Partido Liberal | 1,3 | 1,7 |
| Frente Amplio | 2,8 | 3,2 |
| Partido Nacional Libertario | 2,6 | 2,2 |

### `aprueba_gobierno`

| Respuesta | CEP % | Muestra % |
|---|---|---|
| No contesta | 1,0 | 1,1 |
| No sabe | 4,2 | 4,2 |
| Aprueba | 34,5 | 34,4 |
| Desaprueba | 51,6 | 52,3 |
| No aprueba ni desaprueba | 8,8 | 8,0 |

### `confianza_gobierno`

| Respuesta | CEP % | Muestra % |
|---|---|---|
| No contesta | 0,5 | 0,4 |
| No sabe | 0,5 | 0,5 |
| Mucha confianza | 8,1 | 7,8 |
| Bastante confianza | 19,7 | 20,4 |
| Poca confianza | 44,0 | 44,4 |
| Nada de confianza | 27,1 | 26,5 |

### `confianza_congreso`

| Respuesta | CEP % | Muestra % |
|---|---|---|
| No contesta | 0,5 | 0,3 |
| No sabe | 1,6 | 1,7 |
| Mucha confianza | 1,7 | 1,5 |
| Bastante confianza | 11,3 | 11,3 |
| Poca confianza | 53,2 | 53,7 |
| Nada de confianza | 31,7 | 31,4 |

### `confianza_municipalidades`

| Respuesta | CEP % | Muestra % |
|---|---|---|
| No contesta | 0,2 | 0,1 |
| No sabe | 0,7 | 0,9 |
| Mucha confianza | 6,9 | 7,7 |
| Bastante confianza | 26,6 | 27,5 |
| Poca confianza | 49,7 | 49,1 |
| Nada de confianza | 15,8 | 14,8 |

### `responsabilidad_sustento`

| Respuesta | CEP % | Muestra % |
|---|---|---|
| No contesta | 0,7 | 0,4 |
| No sabe | 0,7 | 0,6 |
| 1 La principal responsabilidad está en el Estado | 14,2 | 14,0 |
| 2 | 1,5 | 1,4 |
| 3 | 4,0 | 4,0 |
| 4 | 6,4 | 6,5 |
| 5 | 21,0 | 22,0 |
| 6 | 11,6 | 12,2 |
| 7 | 10,8 | 10,2 |
| 8 | 5,8 | 5,9 |
| 9 | 1,8 | 1,6 |
| 10 La principal responsabilidad está en las personas | 21,6 | 21,1 |

### `interes_politica`

| Respuesta | CEP % | Muestra % |
|---|---|---|
| No contesta | 0,6 | 0,3 |
| No sabe | 0,1 | 0,0 |
| Muy interesado | 8,7 | 8,0 |
| Bastante interesado | 9,9 | 10,1 |
| Algo interesado | 22,7 | 24,5 |
| No muy interesado | 16,7 | 16,6 |
| Nada interesado | 41,3 | 40,5 |

### `voto_segunda_vuelta_2025`

| Respuesta | CEP % | Muestra % |
|---|---|---|
| No contesta | 7,6 | 6,8 |
| No sabe | 0,7 | 0,5 |
| No aplica | 11,8 | 12,0 |
| Jeannette Jara | 28,1 | 28,7 |
| José Antonio Kast | 39,9 | 40,7 |
| Votó en blanco | 3,1 | 2,9 |
| Votó nulo | 8,9 | 8,4 |

### `aprueba_gobierno_anterior`

| Respuesta | CEP % | Muestra % |
|---|---|---|
| No contesta | 1,0 | 0,9 |
| No sabe | 1,8 | 2,2 |
| Aprueba | 32,8 | 33,2 |
| Desaprueba | 57,9 | 56,8 |
| No aprueba ni desaprueba | 6,5 | 6,9 |

### `votaria_voluntario`

| Respuesta | CEP % | Muestra % |
|---|---|---|
| No contesta | 0,4 | 0,6 |
| No sabe | 0,5 | 0,6 |
| Si | 65,5 | 67,4 |
| No | 33,5 | 31,3 |

### `fuente_noticias`

| Respuesta | CEP % | Muestra % |
|---|---|---|
| No contesta | 0,8 | 0,3 |
| No sabe | 0,2 | 0,1 |
| Redes sociales (por ejemplo, Whatsapp, Facebook, Tiktok, Instagram, Youtube, Twitter/X) | 32,9 | 32,6 |
| Televisión (incluye aplicaciones de TV o acceso online) | 36,5 | 36,7 |
| Diarios en formato impreso u online | 4,1 | 4,3 |
| Radio y podcasts (incluye radio por internet o acceso vía internet) | 9,6 | 10,1 |
| Sitios web | 8,2 | 7,5 |
| Otro | 1,2 | 1,2 |
| De ninguna parte | 6,6 | 7,2 |

### `problema_1`

| Respuesta | CEP % | Muestra % |
|---|---|---|
| No sabe | 0,0 | 0,0 |
| Pensiones | 7,3 | 7,8 |
| Corrupción | 4,7 | 4,3 |
| Delincuencia, asaltos y robos | 32,6 | 33,8 |
| Derechos humanos | 0,7 | 0,7 |
| Educación | 7,8 | 7,5 |
| Empleo | 3,7 | 4,1 |
| Pobreza | 3,0 | 3,0 |
| Protección del medio ambiente | 1,0 | 0,7 |
| Narcotráfico | 10,2 | 10,4 |
| Salud | 13,8 | 12,8 |
| Sueldos | 2,3 | 2,0 |
| Transporte público | 1,7 | 1,5 |
| Vivienda | 2,7 | 2,7 |
| Inmigración | 1,9 | 1,9 |
| Desigualdad | 2,0 | 2,3 |
| Alzas de precios, inflación | 1,3 | 1,5 |
| Violencia | 3,1 | 3,0 |

### `problema_2`

| Respuesta | CEP % | Muestra % |
|---|---|---|
| No contesta | 0,0 | 0,0 |
| No aplica | 0,0 | 0,0 |
| Pensiones | 4,7 | 4,2 |
| Corrupción | 3,9 | 4,1 |
| Delincuencia, asaltos y robos | 14,4 | 13,8 |
| Derechos humanos | 1,4 | 1,5 |
| Educación | 10,6 | 11,4 |
| Empleo | 6,8 | 6,5 |
| Pobreza | 6,6 | 7,1 |
| Protección del medio ambiente | 1,2 | 1,8 |
| Narcotráfico | 11,4 | 10,5 |
| Salud | 12,7 | 12,4 |
| Sueldos | 4,7 | 5,2 |
| Transporte público | 1,9 | 1,9 |
| Vivienda | 3,7 | 4,4 |
| Inmigración | 5,2 | 5,0 |
| Desigualdad | 2,8 | 2,6 |
| Alzas de precios, inflación | 2,8 | 2,9 |
| Violencia | 5,2 | 4,5 |

### `problema_3`

| Respuesta | CEP % | Muestra % |
|---|---|---|
| No contesta | 0,0 | 0,2 |
| No sabe | 0,0 | 0,1 |
| No aplica | 0,0 | 0,0 |
| Pensiones | 6,5 | 7,0 |
| Corrupción | 5,3 | 5,9 |
| Delincuencia, asaltos y robos | 9,6 | 8,9 |
| Derechos humanos | 1,0 | 1,0 |
| Educación | 10,1 | 9,5 |
| Empleo | 7,3 | 6,9 |
| Pobreza | 6,8 | 6,8 |
| Protección del medio ambiente | 2,3 | 2,4 |
| Narcotráfico | 6,7 | 6,9 |
| Salud | 15,5 | 16,3 |
| Sueldos | 5,6 | 6,5 |
| Transporte público | 1,5 | 1,8 |
| Vivienda | 4,8 | 4,3 |
| Inmigración | 6,1 | 5,5 |
| Desigualdad | 3,7 | 3,8 |
| Alzas de precios, inflación | 3,0 | 2,8 |
| Violencia | 4,0 | 3,5 |

### `rumbo_pais`

| Respuesta | CEP % | Muestra % |
|---|---|---|
| No contesta | 0,1 | 0,1 |
| No sabe | 1,7 | 1,9 |
| Progresando | 18,4 | 18,0 |
| Estancado | 53,5 | 55,5 |
| En decadencia | 26,2 | 24,4 |

### `situacion_politica`

| Respuesta | CEP % | Muestra % |
|---|---|---|
| No contesta | 0,5 | 0,4 |
| No sabe | 2,3 | 2,7 |
| Muy buena | 0,7 | 0,7 |
| Buena | 10,8 | 11,1 |
| Ni buena ni mala | 34,1 | 33,6 |
| Mala | 36,3 | 37,2 |
| Muy mala | 15,3 | 14,3 |

### `apoyo_democracia`

| Respuesta | CEP % | Muestra % |
|---|---|---|
| No contesta | 0,9 | 0,7 |
| No sabe | 3,5 | 4,0 |
| La democracia siempre es preferible | 53,5 | 53,5 |
| A veces un régimen autoritario puede ser preferible | 14,5 | 14,2 |
| Da lo mismo un régimen democrático que uno autoritario | 27,6 | 27,6 |

### `funciona_democracia`

| Respuesta | CEP % | Muestra % |
|---|---|---|
| No contesta | 0,6 | 0,5 |
| No sabe | 1,9 | 2,1 |
| Muy mal | 9,0 | 7,9 |
| Mal | 17,6 | 17,8 |
| Regular | 50,1 | 50,6 |
| Bien | 17,9 | 18,2 |
| Muy bien | 3,0 | 2,8 |

### `economia_pais`

| Respuesta | CEP % | Muestra % |
|---|---|---|
| No contesta | 0,2 | 0,1 |
| No sabe | 0,2 | 0,2 |
| Muy mala | 13,7 | 12,5 |
| Mala | 31,7 | 31,8 |
| Ni buena, ni mala | 43,4 | 45,3 |
| Buena | 10,4 | 9,8 |
| Muy buena | 0,4 | 0,3 |

### `economia_pais_futuro`

| Respuesta | CEP % | Muestra % |
|---|---|---|
| No contesta | 0,1 | 0,1 |
| No sabe | 2,8 | 3,8 |
| Mejorará | 32,3 | 33,2 |
| No cambiará | 33,3 | 32,6 |
| Empeorará | 31,5 | 30,4 |

### `economia_personal`

| Respuesta | CEP % | Muestra % |
|---|---|---|
| No contesta | 0,0 | 0,1 |
| No sabe | 0,0 | 0,0 |
| Muy mala | 2,9 | 2,9 |
| Mala | 18,3 | 17,6 |
| Ni buena, ni mala | 53,7 | 53,2 |
| Buena | 23,4 | 24,6 |
| Muy buena | 1,7 | 1,6 |

### `economia_personal_futuro`

| Respuesta | CEP % | Muestra % |
|---|---|---|
| No sabe | 0,8 | 1,1 |
| Mucho mejor | 7,8 | 7,1 |
| Mejor | 30,5 | 30,5 |
| Igual | 48,4 | 49,2 |
| Peor | 10,4 | 10,2 |
| Mucho peor | 2,0 | 1,8 |

### `ingresos_alcanzan`

| Respuesta | CEP % | Muestra % |
|---|---|---|
| No contesta | 0,2 | 0,1 |
| No sabe | 0,0 | 0,0 |
| Les alcanza bien, pueden ahorrar | 13,1 | 13,3 |
| Les alcanza justo, sin grandes dificultades | 49,7 | 50,9 |
| No les alcanza, tienen algunas dificultades | 28,7 | 28,3 |
| No les alcanza, tienen grandes dificultades | 8,3 | 7,4 |

### `preocupa_deudas`

| Respuesta | CEP % | Muestra % |
|---|---|---|
| No contesta | 0,0 | 0,0 |
| No sabe | 0,1 | 0,1 |
| Nada preocupado | 7,5 | 7,2 |
| 1 | 1,5 | 1,3 |
| 2 | 2,6 | 2,8 |
| 3 | 1,6 | 1,6 |
| 4 | 2,0 | 2,4 |
| 5 | 7,7 | 7,5 |
| 6 | 3,9 | 3,9 |
| 7 | 6,5 | 6,4 |
| 8 | 10,2 | 9,9 |
| 9 | 5,1 | 5,1 |
| Muy preocupado | 51,4 | 51,8 |

### `preocupa_enfermedad`

| Respuesta | CEP % | Muestra % |
|---|---|---|
| Nada preocupado | 3,1 | 2,8 |
| 1 | 1,0 | 0,9 |
| 2 | 0,7 | 0,8 |
| 3 | 1,6 | 1,9 |
| 4 | 2,0 | 1,9 |
| 5 | 4,6 | 3,4 |
| 6 | 2,7 | 2,6 |
| 7 | 6,2 | 6,3 |
| 8 | 7,9 | 9,1 |
| 9 | 6,1 | 5,7 |
| Muy preocupado | 64,1 | 64,7 |

### `preocupa_pension`

| Respuesta | CEP % | Muestra % |
|---|---|---|
| No contesta | 0,2 | 0,2 |
| No sabe | 0,3 | 0,2 |
| Nada preocupado | 5,9 | 4,8 |
| 1 | 1,1 | 1,3 |
| 2 | 0,8 | 1,2 |
| 3 | 1,9 | 2,1 |
| 4 | 2,1 | 1,7 |
| 5 | 6,2 | 6,0 |
| 6 | 3,7 | 3,6 |
| 7 | 7,3 | 6,9 |
| 8 | 7,8 | 8,3 |
| 9 | 5,6 | 5,8 |
| Muy preocupado | 57,3 | 57,7 |

### `clase_subjetiva`

| Respuesta | CEP % | Muestra % |
|---|---|---|
| No contesta | 0,3 | 0,3 |
| No sabe | 0,3 | 0,2 |
| Nivel más bajo | 4,8 | 5,1 |
| 2 | 6,3 | 5,6 |
| 3 | 12,0 | 11,7 |
| 4 | 20,6 | 22,0 |
| 5 | 35,2 | 35,1 |
| 6 | 11,5 | 11,9 |
| 7 | 5,0 | 4,5 |
| 8 | 2,2 | 1,9 |
| 9 | 0,4 | 0,5 |
| Nivel más alto | 1,4 | 1,3 |

### `menos_estado_economia`

| Respuesta | CEP % | Muestra % |
|---|---|---|
| No contesta | 0,9 | 0,6 |
| No sabe | 2,8 | 3,2 |
| Muy de acuerdo | 4,6 | 4,0 |
| De acuerdo | 19,6 | 20,4 |
| Ni de acuerdo ni en desacuerdo | 24,3 | 22,8 |
| En desacuerdo | 38,6 | 39,7 |
| Muy en desacuerdo | 9,2 | 9,4 |

### `estado_burocracia`

| Respuesta | CEP % | Muestra % |
|---|---|---|
| No contesta | 0,5 | 0,5 |
| No sabe | 2,1 | 2,4 |
| Muy de acuerdo | 12,1 | 11,5 |
| De acuerdo | 40,1 | 41,6 |
| Ni de acuerdo ni en desacuerdo | 24,9 | 25,0 |
| En desacuerdo | 16,6 | 15,9 |
| Muy en desacuerdo | 3,6 | 3,1 |

### `reducir_gasto_publico`

| Respuesta | CEP % | Muestra % |
|---|---|---|
| No contesta | 1,2 | 0,8 |
| No sabe | 2,8 | 3,3 |
| Muy de acuerdo | 10,2 | 8,9 |
| De acuerdo | 23,9 | 26,5 |
| Ni de acuerdo ni en desacuerdo | 20,6 | 18,2 |
| En desacuerdo | 28,5 | 29,2 |
| Muy en desacuerdo | 12,8 | 13,0 |

### `empleados_publicos`

| Respuesta | CEP % | Muestra % |
|---|---|---|
| No contesta | 0,3 | 0,2 |
| No sabe | 2,8 | 2,8 |
| Demasiado alto | 40,7 | 39,5 |
| Alto | 25,7 | 27,4 |
| Adecuado | 15,4 | 15,0 |
| Bajo | 12,2 | 12,2 |
| Demasiado bajo | 2,8 | 2,8 |

### `libertades_o_seguridad`

| Respuesta | CEP % | Muestra % |
|---|---|---|
| No contesta | 1,0 | 1,0 |
| No sabe | 1,3 | 1,2 |
| Se deben garantizar las libertades públicas y privadas, aunque eso impida controlar la delincuencia | 6,0 | 5,6 |
| 1 | 1,8 | 1,9 |
| 2 | 2,1 | 2,0 |
| 3 | 3,4 | 3,9 |
| 4 | 6,5 | 5,9 |
| 5 | 25,7 | 24,9 |
| 6 | 10,3 | 10,0 |
| 7 | 10,8 | 12,4 |
| 8 | 6,0 | 5,5 |
| 9 | 1,9 | 1,9 |
| Se deben suprimir las libertades públicas y privadas para controlar la delincuencia | 23,2 | 23,8 |

### `causa_delincuencia`

| Respuesta | CEP % | Muestra % |
|---|---|---|
| No contesta | 0,4 | 0,2 |
| No sabe | 0,2 | 0,2 |
| La inmigración irregular | 17,7 | 18,0 |
| La falta de condenas o bajas penas que reciben los delincuentes | 25,2 | 26,3 |
| La pobreza y falta de oportunidades | 11,8 | 12,4 |
| La pérdida de valores en la sociedad | 3,7 | 3,2 |
| La crisis de la familia | 2,5 | 2,4 |
| El consumo de drogas y alcohol | 10,0 | 9,1 |
| Las restricciones de las policías | 1,0 | 1,0 |
| La falta de capacitación de las policías | 2,1 | 2,5 |
| La desigualdad | 5,9 | 5,5 |
| La validación de la violencia durante el estallido social | 4,5 | 4,5 |
| Las bandas de narcotráfico | 14,1 | 14,0 |
| Otra | 0,8 | 0,7 |

### `justifica_marchas`

| Respuesta | CEP % | Muestra % |
|---|---|---|
| No contesta | 0,3 | 0,0 |
| No sabe | 0,1 | 0,1 |
| Siempre | 23,9 | 24,6 |
| Casi siempre | 11,0 | 10,8 |
| A veces | 25,8 | 25,9 |
| Casi nunca | 9,7 | 9,4 |
| Nunca | 29,2 | 29,2 |

### `justifica_fuerza_carabineros`

| Respuesta | CEP % | Muestra % |
|---|---|---|
| No contesta | 0,5 | 0,3 |
| No sabe | 0,4 | 0,1 |
| Siempre | 31,6 | 30,2 |
| Casi siempre | 15,0 | 15,4 |
| A veces | 28,8 | 29,8 |
| Casi nunca | 7,7 | 8,1 |
| Nunca | 16,0 | 16,1 |

### `apertura_inmigracion`

| Respuesta | CEP % | Muestra % |
|---|---|---|
| No contesta | 0,3 | 0,3 |
| No sabe | 0,7 | 0,7 |
| Prohibir toda inmigración | 26,0 | 24,9 |
| 2 | 6,3 | 6,2 |
| 3 | 13,3 | 12,9 |
| 4 | 9,6 | 11,4 |
| 5 | 23,0 | 23,3 |
| 6 | 7,1 | 6,7 |
| 7 | 4,5 | 4,8 |
| 8 | 2,1 | 2,6 |
| 9 | 0,9 | 0,7 |
| Permitir libremente toda inmigración | 6,1 | 5,6 |

### `inmigrantes_criminalidad`

| Respuesta | CEP % | Muestra % |
|---|---|---|
| No contesta | 0,5 | 0,6 |
| No sabe | 0,6 | 0,5 |
| Muy de acuerdo | 24,0 | 23,1 |
| De acuerdo | 43,1 | 43,8 |
| Ni de acuerdo ni en desacuerdo | 16,8 | 17,2 |
| En desacuerdo | 11,2 | 11,3 |
| Muy en desacuerdo | 3,7 | 3,5 |

### `inmigrantes_aporte`

| Respuesta | CEP % | Muestra % |
|---|---|---|
| No contesta | 0,2 | 0,2 |
| No sabe | 0,9 | 1,0 |
| Muy de acuerdo | 7,0 | 7,0 |
| De acuerdo | 29,2 | 29,6 |
| Ni de acuerdo ni en desacuerdo | 30,6 | 30,2 |
| En desacuerdo | 25,9 | 26,6 |
| Muy en desacuerdo | 6,1 | 5,4 |

### `hijos_ideal`

| Respuesta | CEP % | Muestra % |
|---|---|---|
| No contesta | 0,2 | 0,2 |
| 0 | 10,6 | 10,3 |
| 1 | 15,6 | 15,2 |
| 2 | 37,9 | 39,0 |
| 3 | 18,9 | 18,5 |
| 4 | 8,6 | 8,1 |
| 5 | 3,5 | 4,0 |
| 6 | 2,3 | 2,0 |
| 7 | 0,6 | 0,8 |
| 8 | 0,7 | 0,6 |
| 10 | 0,6 | 0,5 |
| 12 | 0,4 | 0,6 |
| 18 | 0,0 | 0,0 |
| 20 | 0,1 | 0,0 |

### `hijos_carga_financiera`

| Respuesta | CEP % | Muestra % |
|---|---|---|
| No contesta | 0,4 | 0,4 |
| No sabe | 0,2 | 0,1 |
| Muy en desacuerdo | 8,2 | 6,8 |
| En desacuerdo | 34,0 | 34,4 |
| Ni de acuerdo ni en desacuerdo | 16,7 | 17,1 |
| De acuerdo | 31,8 | 32,2 |
| Muy de acuerdo | 8,7 | 9,0 |

### `hijos_restringen_carrera`

| Respuesta | CEP % | Muestra % |
|---|---|---|
| No contesta | 0,2 | 0,1 |
| No sabe | 0,4 | 0,3 |
| Muy en desacuerdo | 4,8 | 4,2 |
| En desacuerdo | 29,2 | 30,8 |
| Ni de acuerdo ni en desacuerdo | 19,4 | 17,7 |
| De acuerdo | 36,9 | 38,2 |
| Muy de acuerdo | 9,1 | 8,7 |

### `confianza_fuerzas_armadas`

| Respuesta | CEP % | Muestra % |
|---|---|---|
| No contesta | 0,4 | 0,3 |
| No sabe | 1,1 | 0,9 |
| Mucha confianza | 22,6 | 23,6 |
| Bastante confianza | 34,8 | 35,6 |
| Poca confianza | 29,5 | 27,6 |
| Nada de confianza | 11,6 | 12,0 |

### `confianza_carabineros`

| Respuesta | CEP % | Muestra % |
|---|---|---|
| No contesta | 0,1 | 0,0 |
| No sabe | 0,2 | 0,1 |
| Mucha confianza | 22,8 | 21,9 |
| Bastante confianza | 35,5 | 35,7 |
| Poca confianza | 31,3 | 32,1 |
| Nada de confianza | 10,1 | 10,1 |

### `confianza_tribunales`

| Respuesta | CEP % | Muestra % |
|---|---|---|
| No contesta | 0,2 | 0,1 |
| No sabe | 1,3 | 1,3 |
| Mucha confianza | 5,5 | 4,7 |
| Bastante confianza | 19,0 | 20,1 |
| Poca confianza | 48,4 | 48,2 |
| Nada de confianza | 25,7 | 25,6 |

### `confianza_partidos`

| Respuesta | CEP % | Muestra % |
|---|---|---|
| No contesta | 0,6 | 0,4 |
| No sabe | 1,1 | 1,5 |
| Mucha confianza | 0,8 | 1,0 |
| Bastante confianza | 5,4 | 5,9 |
| Poca confianza | 42,9 | 43,4 |
| Nada de confianza | 49,2 | 47,7 |

### `confianza_empresas`

| Respuesta | CEP % | Muestra % |
|---|---|---|
| No contesta | 0,5 | 0,4 |
| No sabe | 2,7 | 3,1 |
| Mucha confianza | 6,4 | 6,4 |
| Bastante confianza | 25,3 | 25,8 |
| Poca confianza | 44,3 | 42,3 |
| Nada de confianza | 20,7 | 22,0 |

### `confianza_sindicatos`

| Respuesta | CEP % | Muestra % |
|---|---|---|
| No contesta | 0,5 | 0,6 |
| No sabe | 4,3 | 5,0 |
| Mucha confianza | 5,5 | 6,5 |
| Bastante confianza | 22,9 | 21,9 |
| Poca confianza | 45,5 | 46,3 |
| Nada de confianza | 21,3 | 19,7 |

### `confianza_sistema_salud`

| Respuesta | CEP % | Muestra % |
|---|---|---|
| No contesta | 0,2 | 0,1 |
| No sabe | 0,1 | 0,1 |
| Mucha confianza | 6,3 | 6,6 |
| Bastante confianza | 24,1 | 23,5 |
| Poca confianza | 53,9 | 54,9 |
| Nada de confianza | 15,4 | 14,7 |

### `confianza_sistema_pensiones`

| Respuesta | CEP % | Muestra % |
|---|---|---|
| No contesta | 0,4 | 0,3 |
| No sabe | 1,2 | 1,4 |
| Mucha confianza | 4,1 | 4,9 |
| Bastante confianza | 13,3 | 13,2 |
| Poca confianza | 53,3 | 53,3 |
| Nada de confianza | 27,7 | 26,8 |

### `confianza_television`

| Respuesta | CEP % | Muestra % |
|---|---|---|
| No contesta | 0,1 | 0,0 |
| No sabe | 0,3 | 0,4 |
| Mucha confianza | 3,1 | 2,8 |
| Bastante confianza | 11,5 | 12,3 |
| Poca confianza | 48,4 | 48,9 |
| Nada de confianza | 36,7 | 35,5 |

### `confianza_redes_sociales`

| Respuesta | CEP % | Muestra % |
|---|---|---|
| No contesta | 0,3 | 0,3 |
| No sabe | 2,1 | 2,4 |
| Mucha confianza | 3,5 | 3,3 |
| Bastante confianza | 10,6 | 11,0 |
| Poca confianza | 46,7 | 47,1 |
| Nada de confianza | 36,7 | 36,0 |

### `confianza_iglesia_catolica`

| Respuesta | CEP % | Muestra % |
|---|---|---|
| No contesta | 0,7 | 0,6 |
| No sabe | 0,9 | 0,7 |
| Mucha confianza | 11,2 | 13,8 |
| Bastante confianza | 18,8 | 19,0 |
| Poca confianza | 39,4 | 41,0 |
| Nada de confianza | 28,9 | 24,9 |

### `confianza_universidades`

| Respuesta | CEP % | Muestra % |
|---|---|---|
| No contesta | 0,3 | 0,1 |
| No sabe | 1,9 | 2,0 |
| Mucha confianza | 18,6 | 18,6 |
| Bastante confianza | 42,6 | 44,9 |
| Poca confianza | 31,0 | 27,6 |
| Nada de confianza | 5,7 | 6,7 |

### Por grupo

Posición política media (de 1 a 10, entre quienes se ubican) y porcentaje que aprueba al gobierno, en la CEP y en la muestra.

| Grupo | Casos CEP | Posición CEP | Posición muestra | Aprueba CEP % | Aprueba muestra % |
|---|---|---|---|---|---|
| sexo: Hombre | 536 | 5,38 | 5,33 | 36,3 | 37,9 |
| sexo: Mujer | 930 | 5,45 | 5,40 | 32,6 | 31,3 |
| edad3: 18 a 34 | 374 | 5,12 | 5,06 | 27,8 | 30,2 |
| edad3: 35 a 54 | 477 | 5,57 | 5,50 | 40,0 | 38,7 |
| edad3: 55 o más | 615 | 5,55 | 5,54 | 34,5 | 34,1 |
| educ4: Menos que media completa | 476 | 5,63 | 5,68 | 32,1 | 35,3 |
| educ4: Media completa | 579 | 5,38 | 5,35 | 34,8 | 35,4 |
| educ4: Técnica completa | 158 | 5,27 | 5,19 | 39,0 | 36,6 |
| educ4: Universitaria completa | 251 | 5,35 | 5,10 | 34,8 | 29,9 |
| nse3: Bajo | 238 | 5,43 | 5,71 | 31,0 | 33,7 |
| nse3: Medio | 791 | 5,40 | 5,41 | 34,6 | 35,4 |
| nse3: Alto | 437 | 5,43 | 5,21 | 35,7 | 32,9 |
| rel4: Católica | 717 | 5,66 | 5,51 | 39,1 | 37,0 |
| rel4: Evangélica | 275 | 5,76 | 5,74 | 43,6 | 40,6 |
| rel4: Ninguna | 404 | 4,88 | 4,78 | 25,0 | 25,3 |
| rel4: Otra | 52 | 5,62 | 5,58 | 17,5 | 32,4 |

Fuentes: Centro de Estudios Públicos, Encuesta CEP N° 96, abril-mayo 2026; INE, Censo de Población y Vivienda 2024.
