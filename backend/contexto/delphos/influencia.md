# Qué datos del perfil pesan en una opinión política

Lo escribe `scripts/analizar_influencia.py`; no lo edites a mano. Es el respaldo del filtro de `scripts/filtro_perfil.py` (versión `5aaa3965`), que decide qué datos de cada persona lee el modelo: 102 en el perfil completo, 28 en el núcleo y 68 que solo van si la política toca su tema.

## A. Con personas reales: Encuesta CEP

Se tomaron 42 opiniones de la CEP (1.466 entrevistas) que **no** van en el perfil y se midió cuánto las predicen los datos que **sí** van. Si un dato no ayuda a predecir ninguna, entregárselo al modelo solo le suma texto.

### Por conjunto de datos

R² fuera de muestra, en porcentaje: cuánta de la variación de las opiniones se predice en personas que el modelo estadístico no vio (ridge, 5 pliegues, 3 particiones, ponderado). «Datos medibles» son los del conjunto que la CEP también pregunta.

| Conjunto | Datos medibles | R² medio | Del completo | Estado y gasto | Gobierno actual | Conflicto social | Inmigración | Protesta y orden | Familia | Otras confianzas | Figuras políticas |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Perfil completo | 62 | 19,4 | 100 % | 12,7 | 38,2 | 1,3 | 14,3 | 19,6 | 9,2 | 28,3 | 32,0 |
| Solo demografía | 10 | 4,2 | 22 % | -0,4 | 3,6 | 1,2 | 2,6 | 3,6 | 9,0 | 6,9 | 3,3 |
| Núcleo | 21 | 16,3 | 84 % | 12,2 | 38,0 | 2,2 | 4,8 | 13,4 | 7,6 | 16,9 | 32,8 |
| Núcleo + trabajo | 23 | 16,8 | 86 % | 12,0 | 37,7 | 2,4 | 4,6 | 13,3 | 8,0 | 20,4 | 33,0 |
| Núcleo + familia-derechos | 25 | 16,5 | 85 % | 12,4 | 37,8 | 1,7 | 4,1 | 12,9 | 11,3 | 16,2 | 32,3 |
| Núcleo + pensiones | 23 | 16,4 | 84 % | 11,9 | 37,7 | 2,1 | 4,8 | 13,4 | 7,6 | 18,5 | 32,6 |
| Núcleo + salud | 23 | 16,4 | 84 % | 12,0 | 38,3 | 2,6 | 4,7 | 13,0 | 7,7 | 17,8 | 32,5 |
| Núcleo + migracion | 24 | 17,4 | 89 % | 11,9 | 38,0 | 2,5 | 16,6 | 13,3 | 7,6 | 16,8 | 32,5 |
| Núcleo + seguridad-justicia | 28 | 18,5 | 95 % | 12,5 | 37,9 | 2,0 | 5,1 | 21,9 | 7,4 | 25,6 | 32,9 |
| Núcleo + economia-impuestos | 29 | 16,4 | 84 % | 12,5 | 37,9 | 2,7 | 5,5 | 12,7 | 7,0 | 18,1 | 32,9 |
| Núcleo + educacion | 22 | 16,6 | 86 % | 13,0 | 38,0 | 2,6 | 4,7 | 13,4 | 7,7 | 18,6 | 33,0 |
| Núcleo + regulacion-digital | 24 | 17,0 | 87 % | 12,1 | 37,9 | 2,3 | 5,0 | 13,2 | 7,8 | 21,5 | 33,2 |
| Núcleo + instituciones-elecciones | 28 | 16,8 | 87 % | 11,8 | 38,9 | 1,7 | 4,5 | 13,5 | 7,3 | 21,5 | 33,0 |
| Núcleo + bienestar-servicios | 22 | 16,5 | 85 % | 12,0 | 37,8 | 1,9 | 4,7 | 13,5 | 7,7 | 18,8 | 33,0 |
| Núcleo + pueblos-originarios | 22 | 16,2 | 84 % | 12,3 | 37,9 | 2,1 | 4,7 | 13,4 | 7,5 | 16,8 | 32,8 |

El núcleo conserva la mayor parte de lo que predice el perfil completo, y la demografía sola predice muy poco: lo que mueve una opinión es la posición política, el voto y la evaluación de los gobiernos. Cada tema recupera lo propio de su dominio (los datos de inmigración en «Inmigración», los de seguridad en «Protesta y orden»), que es para lo que existe.

### Por dato

Porcentaje de la varianza de las opiniones que explica cada dato por sí solo (eta² ajustado), en promedio y por dominio. Un dato que es varias columnas (`problemas`, `lugar`) toma la que más explica.

| Dato | Nivel en el filtro | Todas | Estado y gasto | Gobierno actual | Conflicto social | Inmigración | Protesta y orden | Familia | Otras confianzas | Figuras políticas |
|---|---|---|---|---|---|---|---|---|---|---|
| `voto_2025` | núcleo | 9,4 | 8,0 | 24,7 | 0,8 | 2,7 | 9,2 | 0,8 | 3,1 | 23,4 |
| `aprueba_gobierno` | núcleo | 8,6 | 7,5 | 30,4 | 1,3 | 1,2 | 7,3 | 0,6 | 2,1 | 20,4 |
| `posicion_politica` | núcleo | 8,0 | 5,3 | 18,1 | 1,5 | 2,5 | 8,0 | 1,8 | 3,1 | 19,4 |
| `confianza_gobierno` | núcleo | 7,5 | 6,6 | 22,8 | 1,9 | 0,3 | 5,3 | 0,9 | 8,5 | 15,6 |
| `aprueba_gobierno_anterior` | núcleo | 7,1 | 8,5 | 13,6 | 0,4 | 1,6 | 6,6 | 1,0 | 0,7 | 20,2 |
| `reducir_gasto` | núcleo | 6,7 | 8,1 | 17,6 | 1,2 | 1,9 | 6,0 | 1,1 | 2,4 | 15,9 |
| `partido` | núcleo | 6,2 | 4,7 | 11,1 | 1,6 | 2,3 | 5,7 | 1,2 | 2,9 | 15,8 |
| `confianza_fuerzas_armadas` | seguridad-justicia | 6,2 | 4,2 | 12,2 | 1,2 | 0,6 | 6,5 | 0,5 | 13,6 | 10,6 |
| `economia_pais_futuro` | economia-impuestos | 6,2 | 5,6 | 18,3 | 1,0 | 1,0 | 5,3 | 0,7 | 2,9 | 14,7 |
| `justifica_marchas` | seguridad-justicia | 5,5 | 3,0 | 8,9 | 1,4 | 3,0 | 9,8 | 3,3 | 1,6 | 9,6 |
| `situacion_politica` | instituciones-elecciones | 5,1 | 3,8 | 15,6 | 1,8 | 0,8 | 4,0 | 0,6 | 4,3 | 10,8 |
| `confianza_carabineros` | seguridad-justicia | 4,9 | 1,5 | 9,3 | 1,4 | 0,2 | 6,1 | 0,7 | 11,7 | 7,3 |
| `justifica_fuerza` | seguridad-justicia | 4,9 | 2,9 | 7,1 | 0,6 | 0,8 | 12,9 | 1,7 | 1,9 | 8,0 |
| `rumbo_pais` | núcleo | 3,4 | 3,0 | 11,3 | 1,2 | 0,2 | 3,0 | 0,5 | 2,0 | 7,1 |
| `problemas` | núcleo | 3,2 | 2,1 | 6,3 | 1,4 | 2,1 | 3,7 | 2,1 | 1,5 | 5,7 |
| `confianza_empresas` | trabajo, economia-impuestos | 3,1 | 2,6 | 4,8 | 2,3 | 0,4 | 2,2 | 1,2 | 8,0 | 3,8 |
| `apertura_inmigracion` | migracion | 3,0 | 2,4 | 3,6 | 1,8 | 9,0 | 1,8 | 1,8 | 1,4 | 3,5 |
| `responsabilidad_sustento` | núcleo | 2,7 | 1,5 | 4,1 | 1,4 | 0,8 | 3,1 | 2,0 | 2,1 | 4,9 |
| `libertades_seguridad` | seguridad-justicia | 2,6 | 1,6 | 4,2 | 1,5 | 2,9 | 2,5 | 2,1 | 1,3 | 4,3 |
| `apoyo_democracia` | instituciones-elecciones | 2,6 | 2,0 | 6,3 | 0,5 | 2,0 | 1,7 | 1,8 | 1,1 | 5,4 |
| `edad` | núcleo | 2,4 | 0,5 | 1,1 | 0,7 | 2,0 | 3,3 | 5,8 | 2,1 | 1,6 |
| `confianza_television` | regulacion-digital | 2,4 | 0,3 | 3,0 | 1,4 | 0,5 | 1,2 | 0,8 | 7,9 | 2,9 |
| `religion` | núcleo | 2,3 | 0,0 | 2,9 | 0,4 | 0,9 | 1,5 | 2,4 | 6,2 | 2,8 |
| `confianza_tribunales` | seguridad-justicia, instituciones-elecciones | 2,2 | 0,8 | 1,5 | 1,1 | 1,4 | 0,4 | 0,7 | 12,3 | 0,8 |
| `inmigrantes_criminalidad` | migracion | 2,2 | 1,4 | 1,9 | 0,8 | 10,2 | 1,4 | 0,9 | 0,4 | 2,3 |
| `causa_delincuencia` | seguridad-justicia | 2,1 | 2,9 | 2,3 | 0,7 | 1,9 | 1,9 | 1,0 | 0,3 | 5,0 |
| `confianza_sindicatos` | trabajo | 2,1 | 1,4 | 0,6 | 0,8 | 0,6 | 1,2 | 1,7 | 5,8 | 3,2 |
| `inmigrantes_aporte` | migracion | 2,1 | 1,2 | 1,0 | 0,9 | 11,9 | 0,5 | 1,3 | 0,6 | 1,4 |
| `confianza_sistema_pensiones` | pensiones | 2,0 | 1,1 | 2,5 | 0,8 | 0,3 | 1,2 | 0,5 | 7,2 | 2,2 |
| `economia_personal_futuro` | solo completo | 1,9 | 2,3 | 5,3 | 0,3 | 0,4 | 1,0 | 0,3 | 1,6 | 4,7 |
| `confianza_congreso` | núcleo | 1,9 | 1,4 | 2,0 | 0,8 | 1,0 | 0,2 | 0,6 | 9,4 | 1,1 |
| `fuente_noticias` | regulacion-digital | 1,9 | 0,2 | 1,8 | 0,6 | 2,6 | 1,9 | 2,8 | 1,9 | 2,1 |
| `confianza_iglesia_catolica` | solo completo | 1,9 | 1,2 | 3,0 | 0,9 | 0,3 | 1,1 | 0,9 | 4,9 | 2,7 |
| `interes_politica` | núcleo | 1,9 | 0,7 | 2,1 | 0,8 | 2,6 | 1,1 | 2,5 | 2,8 | 1,9 |
| `educacion` | núcleo | 1,8 | 0,8 | 1,5 | 0,7 | 3,1 | 0,4 | 5,2 | 1,2 | 0,9 |
| `hijos_ideal` | familia-derechos | 1,7 | 0,0 | 1,6 | 0,3 | 0,2 | 2,0 | 4,7 | 1,1 | 1,6 |
| `confianza_universidades` | educacion | 1,7 | 2,0 | 0,6 | 1,2 | 1,1 | 0,4 | 1,1 | 6,2 | 1,4 |
| `economia_pais` | economia-impuestos | 1,7 | 1,0 | 2,9 | 2,3 | 2,0 | 0,4 | 0,7 | 1,5 | 2,6 |
| `confianza_municipalidades` | instituciones-elecciones, bienestar-servicios | 1,6 | 0,2 | 0,5 | 0,4 | 1,4 | 0,4 | 1,4 | 6,7 | 1,4 |
| `hijos` | núcleo | 1,6 | 0,3 | 0,9 | 0,3 | 1,0 | 2,8 | 3,4 | 1,1 | 1,2 |
| `empleados_publicos` | economia-impuestos | 1,5 | 2,8 | 1,2 | 0,5 | 2,2 | 1,5 | 0,4 | 0,9 | 2,9 |
| `funciona_democracia` | instituciones-elecciones | 1,5 | 0,8 | 2,1 | 1,5 | 2,6 | 0,6 | 0,8 | 3,0 | 1,3 |
| `confianza_partidos` | instituciones-elecciones | 1,5 | 1,1 | 2,0 | 0,8 | 0,8 | 0,5 | 0,6 | 5,5 | 1,2 |
| `estado_civil` | familia-derechos | 1,4 | 0,4 | 1,4 | 0,7 | 0,4 | 2,4 | 2,9 | 0,8 | 1,0 |
| `hijos_carga` | familia-derechos | 1,3 | 1,0 | 0,4 | 0,6 | 0,1 | 0,8 | 4,8 | 0,5 | 0,8 |
| `hijos_carrera` | familia-derechos | 1,3 | 1,8 | 0,8 | 0,4 | 0,3 | 0,6 | 3,9 | 0,8 | 1,2 |
| `menos_estado` | núcleo | 1,3 | 1,9 | 0,4 | 0,2 | 2,6 | 0,7 | 2,1 | 1,2 | 1,6 |
| `confianza_redes_sociales` | regulacion-digital | 1,3 | 0,2 | 1,1 | 0,6 | 0,6 | 0,2 | 1,5 | 4,3 | 1,2 |
| `preocupa_pension` | pensiones | 1,2 | 0,7 | 0,9 | 1,2 | 2,2 | 0,9 | 1,0 | 1,3 | 1,5 |
| `confianza_sistema_salud` | salud | 1,1 | 0,2 | 0,4 | 0,9 | 1,4 | 0,1 | 0,6 | 4,5 | 0,6 |
| `clase_subjetiva` | solo completo | 1,0 | 0,6 | 1,6 | 1,2 | 1,4 | 0,8 | 0,7 | 1,4 | 0,8 |
| `estado_burocracia` | economia-impuestos | 0,9 | 1,1 | 0,5 | 1,0 | 1,2 | 0,4 | 1,3 | 0,8 | 1,0 |
| `preocupa_enfermedad` | salud | 0,9 | 1,0 | 1,0 | 1,4 | 1,1 | 0,3 | 0,6 | 0,5 | 1,2 |
| `economia_personal` | economia-impuestos | 0,8 | 0,6 | 0,5 | 0,8 | 1,6 | 0,4 | 0,5 | 1,6 | 0,7 |
| `ingresos_alcanzan` | economia-impuestos | 0,8 | 0,9 | 0,9 | 1,1 | 1,0 | 0,4 | 0,8 | 1,0 | 0,6 |
| `lugar` | núcleo | 0,7 | 0,5 | 0,3 | 0,5 | 0,5 | 0,2 | 0,8 | 0,4 | 1,4 |
| `preocupa_deudas` | economia-impuestos | 0,7 | 0,2 | 0,3 | 1,2 | 1,2 | 0,5 | 0,5 | 0,8 | 0,5 |
| `decil` | núcleo | 0,6 | 0,0 | 0,8 | 0,7 | 0,9 | 0,2 | 1,3 | 0,4 | 0,3 |
| `votaria_voluntario` | instituciones-elecciones | 0,6 | 0,4 | 0,7 | 0,4 | 0,7 | 0,4 | 0,6 | 1,3 | 0,3 |
| `genero` | núcleo | 0,5 | 0,3 | 0,3 | 1,5 | 0,1 | 0,9 | 0,4 | 0,1 | 0,4 |
| `situacion_laboral` | núcleo | 0,4 | 0,1 | 0,2 | 0,4 | 0,2 | 0,3 | 1,1 | 0,3 | 0,3 |
| `pueblo_originario` | pueblos-originarios | 0,1 | 0,1 | 0,1 | 0,0 | 0,1 | 0,1 | 0,3 | 0,1 | 0,2 |

Datos del perfil que la CEP no pregunta y por eso no aparecen (40): `colegio`, `conectividad`, `cotiza_pension`, `cuidados`, `discapacidad`, `discriminacion`, `educacion_padres`, `escolaridad`, `estudia`, `hacinamiento`, `hermanos`, `ingreso_pc`, `inseguridad_alimentaria`, `integrantes`, `lugar_trabajo`, `mayores_hogar`, `medio_transporte`, `menores_hogar`, `nacimiento_chile`, `nacimiento_extranjero`, `nacionalidad_chilena`, `nacionalidad_otra`, `ocupacion`, `organizacion`, `pobreza`, `prevision_salud`, `red_cuidado`, `red_dinero`, `red_trabajo`, `residencia_anterior`, `rol_hogar`, `rubro`, `sin_partido`, `sindicato`, `tenencia`, `tiempo_traslado`, `tipo_hogar`, `tipo_vivienda`, `vehiculo`, `vive_con_padres`. Son hechos del censo y de Casen; el filtro los deja como datos de tema, para cuando la política los toca directamente.

## B. Con lo que el modelo hizo

Claude Haiku, 800 personas, texto de validación de Sala Cuna (`data/pruebas/sala_cuna/resultados_validacion_actitudes_haiku55.jsonl`), con el perfil corto de entonces. Porcentaje de la varianza de cada respuesta que explica cada atributo por sí solo.

| Atributo del perfil | Media | p1 | p2 | p3 | p4 | p5 | p6 |
|---|---|---|---|---|---|---|---|
| Posición política | 27,8 | 41,0 | 36,9 | 36,7 | 4,9 | 26,0 | 21,3 |
| Evaluación del gobierno | 15,7 | 23,5 | 15,8 | 16,8 | 21,6 | 11,2 | 5,4 |
| Confianza en el gobierno | 14,4 | 9,6 | 5,0 | 6,3 | 61,7 | 3,6 | 0,0 |
| Situación laboral | 6,1 | 6,2 | 6,3 | 6,8 | 1,0 | 9,7 | 6,7 |
| Edad | 5,8 | 7,0 | 6,7 | 2,7 | 0,0 | 10,3 | 8,3 |
| Niños en el hogar | 5,8 | 9,1 | 7,3 | 5,0 | 0,0 | 7,1 | 6,1 |
| Nivel educacional | 1,9 | 1,3 | 1,7 | 0,0 | 0,0 | 4,4 | 4,0 |
| Estado civil | 1,7 | 2,3 | 1,4 | 0,4 | 0,6 | 3,4 | 2,3 |
| Tipo de transporte | 1,5 | 1,8 | 1,6 | 0,9 | 0,3 | 2,8 | 1,7 |
| Género | 1,4 | 2,0 | 1,5 | 2,0 | 0,5 | 1,1 | 1,1 |
| Previsión de salud | 1,1 | 1,0 | 0,7 | 1,6 | 0,0 | 1,5 | 1,7 |
| Vive con sus padres | 0,8 | 1,0 | 1,2 | 0,6 | 0,1 | 0,5 | 1,2 |
| Tramo socioeconómico | 0,7 | 0,8 | 0,5 | 2,7 | 0,0 | 0,0 | 0,0 |
| Tramo de ingreso del hogar | 0,6 | 0,8 | 0,7 | 2,2 | 0,0 | 0,0 | 0,0 |
| Región | 0,6 | 0,1 | 0,2 | 0,8 | 1,3 | 0,0 | 1,2 |
| Nacionalidad | 0,3 | 0,0 | 0,0 | 0,0 | 0,4 | 0,4 | 0,9 |
| Zona | 0,1 | 0,0 | 0,0 | 0,0 | 0,1 | 0,0 | 0,4 |
| Tipo de vivienda | 0,1 | 0,0 | 0,0 | 0,0 | 0,0 | 0,0 | 0,4 |
| Etnia | 0,0 | 0,0 | 0,0 | 0,1 | 0,0 | 0,1 | 0,0 |
| Hijos | 0,0 | 0,0 | 0,0 | 0,0 | 0,0 | 0,0 | 0,0 |

El modelo responde sobre todo con la posición política, la evaluación del gobierno y la confianza en el gobierno (que domina la pregunta 4, la de confianza en el Estado). Después vienen los datos que dicen si la medida toca a la persona: aquí, situación laboral, edad y niños en el hogar. El resto casi no se usa.

## Límites

- La parte A mide opiniones generales, no respuestas a una política concreta. Sirve para ordenar los datos, no para afirmar cuánto cambia una respuesta.
- Las palabras clave de los temas se ajustaron mirando `datos-pruebas/encuestas/`: que detecten bien el área de esos casos no prueba que lo hagan con textos nuevos.
- Qué cambia en las respuestas del modelo al usar el filtro se mide aparte, con `scripts/comparar_perfiles.py` (ver «Perfil filtrado contra perfil completo» en `servidor/README.md`). Hasta ahora hay un solo caso y un solo modelo.

Fuente: Centro de Estudios Públicos, Encuesta CEP N° 96, abril-mayo 2026.
