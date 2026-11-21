# Validación de la población completa

`data/chile/` tiene 15.463.163 personas de 14 años o más y 6.596.527 hogares: todos los registros del Censo 2024 desde esa edad, con datos imputados desde Casen 2024 y, para los 14.466.767 adultos, opiniones imputadas desde la Encuesta CEP N° 96. Los menores de 14 no son filas, pero siguen contados en su hogar. Este documento lo escribe `scripts/validar_poblacion.py` y compara esa población con sus tres fuentes.

En las tablas, la población se cuenta persona por persona (cada fila vale 1) y las encuestas se ponderan con su factor de expansión. Una distribución pasa si ninguna categoría difiere en más de 2 puntos porcentuales (2,8 en las opiniones, que es el margen de error que declara la CEP); un conjunto de correlaciones pasa si la diferencia media no supera 0,05.

## 1. Contra el censo

Lo que viene del censo no se imputa: debe estar todo y sin cambios.

- ✔ nadie bajo la edad mínima: la persona más joven tiene 14 años
- ✔ personas de 15 años o más: 15.205.784 en la población y 15.205.784 en los microdatos
- ✔ personas de 14 años: 255.344 en la población y 255.344 en los microdatos, en las comunas donde el censo publica la edad exacta
- ✔ hogares: 6.596.527 en la población, 6.596.527 en los microdatos y 6.596.527 en las cifras oficiales por comuna
- ✔ los hogares conservan a todos sus integrantes: suman 18.339.655 personas, igual que el censo; con las 140.777 fuera de hogares son las 18.480.432 de las cifras oficiales
- ✔ menores de 14 contados en su hogar: 3.011.830 menores de 14 que no son filas: es la diferencia entre los integrantes de los hogares y las personas de 14 o más que viven en ellos. Las edades de 4.006.076 menores de 18 quedan guardadas en su hogar
- ✔ personas de 15 o más, hombres y hogares de cada comuna: 346 de 346 comunas coinciden con el censo
- ✔ cruce de comuna, zona, sexo, edad, estado civil, educación y actividad (15 o más): 0 celdas distintas respecto de los microdatos
- ✔ identificador de persona: 0 vacíos y 0 repetidos
- ✔ edad: ninguna suprimida; en 127.686 personas de comunas pequeñas se sorteó dentro de su tramo de cinco años
- ✔ todos los hogares y sus integrantes tienen datos de Casen: 0 hogares sin decil y 0 personas sin previsión
- ✔ todos los adultos tienen opiniones de la CEP: 14.466.767 adultos, 0 sin datos


## 2. Contra Casen

Casen 2024 tiene 218.260 personas en 78.654 hogares. Se pondera con `expr`. Las personas se comparan desde los 14 años.

### Distribuciones

Diferencia máxima, en puntos porcentuales, entre la población y Casen en cada dato imputado. Los datos del hogar se comparan tal cual. Los de la persona se comparan además «a igual composición»: con Casen reponderada para que tenga, como la población, la misma mezcla de sexo, edad, escolaridad, actividad y relación laboral (independiente o dependiente). Esas celdas cubren el 99,47 % de la población.

El censo registra menos ocupados y más independientes que Casen, y la imputación respeta lo que dice el censo de cada persona. Por eso, tal cual, la población tiene menos empleados del sector privado y menos cotizantes que Casen; a igual composición la diferencia desaparece.

| Dato | Categorías | Diferencia tal cual | A igual composición | Dónde queda la mayor diferencia |
|---|---|---|---|---|
| Decil de ingreso del hogar | 10 | 0,47 | — | código 10: 10,0 % en Casen y 9,5 % en la población |
| Pobreza por ingresos del hogar | 3 | 0,60 | — | código 3: 83,0 % en Casen y 82,4 % en la población |
| Vehículo en el hogar | 2 | 1,29 | — | código 1: 53,8 % en Casen y 52,5 % en la población |
| Alguien a quien pedir dinero | 5 | 0,63 | — | código 3: 15,6 % en Casen y 15,0 % en la población |
| Sin discriminación en el hogar | 2 | 0,09 | — | código 0: 19,3 % en Casen y 19,4 % en la población |
| Previsión de salud | 6 | 1,52 | 0,57 | código 1: 83,3 % en Casen y 83,8 % en la población |
| Grupo de Fonasa | 5 | 2,11 | 0,69 | código 1: 25,3 % en Casen y 24,6 % en la población |
| Categoría ocupacional de los ocupados | 9 | 9,71 | 0,62 | código 5: 50,3 % en Casen y 49,7 % en la población |
| Contrato de los asalariados | 3 | 0,94 | 0,66 | código 1: 87,0 % en Casen y 86,3 % en la población |
| Cotiza para pensión (15 años o más) | 3 | 4,92 | 0,44 | código 1: 40,6 % en Casen y 41,0 % en la población |
| Participación en organizaciones | 15 | 0,90 | 0,60 | código 15: 72,7 % en Casen y 72,1 % en la población |
| Tipo de colegio (14 a 17 años que asisten) | 5 | 0,35 | 0,74 | código 4: 4,7 % en Casen y 3,9 % en la población |

- ✔ distribuciones nacionales de lo imputado desde Casen: diferencia máxima de 1,29 puntos (hogares tal cual; personas a igual composición)


### Por región

Porcentaje de hogares en pobreza por ingresos e ingreso medio per cápita del hogar, en Casen y en la población. Casen es representativa por región.

| Región | Pobreza Casen % | Pobreza población % | Diferencia | Ingreso Casen $ | Ingreso población $ | Diferencia | Deciles 9 y 10 Casen % | Deciles 9 y 10 población % |
|---|---|---|---|---|---|---|---|---|
| Tarapacá | 19,9 | 20,6 | 0,75 | 682.508 | 702.167 | 2,9 % | 17,3 | 18,1 |
| Antofagasta | 15,5 | 16,3 | 0,77 | 806.071 | 829.380 | 2,9 % | 21,1 | 21,5 |
| Atacama | 17,9 | 18,8 | 0,87 | 692.229 | 676.856 | -2,2 % | 16,8 | 16,0 |
| Coquimbo | 20,3 | 21,2 | 0,87 | 628.364 | 621.032 | -1,2 % | 13,5 | 13,2 |
| Valparaíso | 17,9 | 18,1 | 0,29 | 676.484 | 682.727 | 0,9 % | 15,7 | 15,8 |
| Libertador General Bernardo O'Higgins | 17,9 | 17,5 | -0,31 | 634.667 | 629.447 | -0,8 % | 12,7 | 12,4 |
| Maule | 24,0 | 24,0 | 0,01 | 527.732 | 519.457 | -1,6 % | 8,4 | 8,1 |
| Biobío | 18,8 | 19,6 | 0,84 | 658.997 | 643.335 | -2,4 % | 14,4 | 13,8 |
| La Araucanía | 28,0 | 29,4 | 1,41 | 552.892 | 541.447 | -2,1 % | 10,6 | 10,0 |
| Los Lagos | 16,9 | 18,0 | 1,05 | 668.107 | 666.114 | -0,3 % | 15,3 | 15,2 |
| Aysén del General Carlos Ibáñez del Campo | 14,1 | 14,2 | 0,12 | 887.436 | 881.905 | -0,6 % | 25,1 | 24,4 |
| Magallanes y de la Antártica Chilena | 10,4 | 10,8 | 0,36 | 938.187 | 925.728 | -1,3 % | 26,1 | 25,7 |
| Metropolitana de Santiago | 12,8 | 13,1 | 0,28 | 980.298 | 970.571 | -1,0 % | 28,4 | 27,8 |
| Los Ríos | 22,2 | 22,9 | 0,65 | 626.302 | 620.910 | -0,9 % | 14,2 | 13,6 |
| Arica y Parinacota | 19,6 | 19,4 | -0,23 | 623.626 | 635.789 | 2,0 % | 13,2 | 13,6 |
| Ñuble | 24,5 | 24,9 | 0,44 | 551.152 | 555.048 | 0,7 % | 9,6 | 9,7 |

- ✔ pobreza de cada región: diferencia máxima de 1,41 puntos
- ✔ ingreso medio de cada región: diferencia máxima de 2,9 %


### Por edad

Porcentaje de personas que viven en hogares en pobreza por ingresos e ingreso medio per cápita de su hogar, según su edad. El ingreso se imputa al hogar, así que esta relación depende de que el emparejamiento distinga los hogares con niños de los hogares con adultos mayores.

| Edad | Pobreza Casen % | Pobreza población % | Diferencia | Ingreso Casen $ | Ingreso población $ | Diferencia |
|---|---|---|---|---|---|---|
| 14 a 17 | 24,2 | 24,4 | 0,16 | 473.144 | 477.820 | 1,0 % |
| 18 a 29 | 18,2 | 17,3 | -0,87 | 569.031 | 624.647 | 9,8 % |
| 30 a 44 | 14,5 | 16,2 | 1,77 | 784.973 | 747.077 | -4,8 % |
| 45 a 64 | 15,3 | 16,5 | 1,19 | 716.968 | 683.082 | -4,7 % |
| 65 o más | 12,4 | 13,9 | 1,50 | 661.347 | 662.688 | 0,2 % |

- ✔ pobreza de cada tramo de edad: diferencia máxima de 1,77 puntos


### Tipo de colegio de los menores

Porcentaje de los menores de 14 a 17 años que asisten a clases según el tipo de colegio, por quintil de ingreso de su hogar. El censo no pregunta el tipo de colegio: se imputa desde Casen según el decil del hogar, la región y la zona.

| Quintil | Público Casen % | Público población % | Subvencionado Casen % | Subvencionado población % | Pagado Casen % | Pagado población % | Delegada Casen % | Delegada población % |
|---|---|---|---|---|---|---|---|---|
| 1 | 45,0 | 45,9 | 49,7 | 48,9 | 1,0 | 0,9 | 4,3 | 4,3 |
| 2 | 39,8 | 40,9 | 52,7 | 51,8 | 2,1 | 2,0 | 5,4 | 5,4 |
| 3 | 34,7 | 34,7 | 56,5 | 56,7 | 4,1 | 4,1 | 4,7 | 4,5 |
| 4 | 24,7 | 24,9 | 56,3 | 56,3 | 17,5 | 17,3 | 1,5 | 1,5 |
| 5 | 9,8 | 10,2 | 31,3 | 31,7 | 58,6 | 57,8 | 0,3 | 0,4 |

- ✔ tipo de colegio por quintil de ingreso: diferencia máxima de 1,03 puntos; cada quintil tiene pocos casos en Casen, por eso la tolerancia es de 4


### Correlaciones

Correlación de Pearson entre pares de datos, en Casen y en la población. «Observado» es lo que viene del censo y «imputado», lo que viene de Casen. Las de dos datos observados no dependen de la imputación: difieren porque el censo y Casen no miden igual la educación ni el empleo.

| Tipo de par | Pares | Diferencia media | Diferencia máxima | Correlación media en Casen (valor absoluto) |
|---|---|---|---|---|
| imputado × observado | 83 | 0,015 | 0,073 | 0,098 |
| imputado × imputado | 66 | 0,015 | 0,071 | 0,146 |
| observado × observado | 21 | 0,010 | 0,032 | 0,094 |

Los 12 pares que más difieren:

| Par | Tipo | Casen | Población | Diferencia |
|---|---|---|---|---|
| indígena × participa en organizaciones | imputado × observado | 0,084 | 0,010 | -0,073 |
| vehículo en el hogar × isapre | imputado × imputado | 0,199 | 0,128 | -0,071 |
| participa en organizaciones × discriminación en el hogar | imputado × imputado | 0,051 | -0,010 | -0,060 |
| escolaridad (15+) × decil de ingreso | imputado × observado | 0,463 | 0,406 | -0,057 |
| decil de ingreso × cotiza para pensión | imputado × imputado | 0,421 | 0,365 | -0,056 |
| escolaridad (15+) × vehículo en el hogar | imputado × observado | 0,222 | 0,170 | -0,052 |
| escolaridad (15+) × isapre | imputado × observado | 0,345 | 0,294 | -0,052 |
| pobreza × cotiza para pensión | imputado × imputado | -0,232 | -0,182 | 0,050 |
| ocupado (15+) × cotiza para pensión | imputado × observado | 0,682 | 0,635 | -0,047 |
| vehículo en el hogar × tiene contrato | imputado × imputado | 0,108 | 0,063 | -0,045 |
| isapre × inseguridad alimentaria | imputado × imputado | -0,172 | -0,127 | 0,045 |
| pobreza × cuida a un dependiente | imputado × imputado | 0,004 | 0,049 | 0,045 |

Las relaciones más fuertes de la fuente, para ver que se conservan:

| Par | Tipo | Casen | Población | Diferencia |
|---|---|---|---|---|
| decil de ingreso × ingreso per cápita (log) | imputado × imputado | 0,763 | 0,761 | -0,002 |
| ocupado (15+) × cotiza para pensión | imputado × observado | 0,682 | 0,635 | -0,047 |
| cotiza para pensión × tiene contrato | imputado × imputado | 0,657 | 0,675 | 0,018 |
| decil de ingreso × pobreza | imputado × imputado | -0,542 | -0,550 | -0,009 |
| ingreso per cápita (log) × pobreza | imputado × imputado | -0,500 | -0,508 | -0,008 |
| escolaridad (15+) × decil de ingreso | imputado × observado | 0,463 | 0,406 | -0,057 |
| decil de ingreso × isapre | imputado × imputado | 0,437 | 0,407 | -0,030 |
| decil de ingreso × cotiza para pensión | imputado × imputado | 0,421 | 0,365 | -0,056 |
| ingreso per cápita (log) × isapre | imputado × imputado | 0,403 | 0,359 | -0,044 |
| ocupado (15+) × decil de ingreso | imputado × observado | 0,378 | 0,341 | -0,036 |
| escolaridad (15+) × cotiza para pensión | imputado × observado | 0,369 | 0,356 | -0,013 |
| edad × escolaridad (15+) | observado × observado | -0,354 | -0,322 | 0,032 |

- ✔ correlaciones imputado × imputado (Casen): diferencia media de 0,015 en 66 pares; máxima de 0,071
- ✔ correlaciones imputado × observado (Casen): diferencia media de 0,015 en 83 pares; máxima de 0,073


## 3. Contra la CEP

La Encuesta CEP N° 96 tiene 1.466 entrevistas a mayores de 18 años. Se pondera con `pond`.

### Distribuciones

Diferencia máxima, en puntos porcentuales, entre los adultos de la población y la CEP en cada opinión imputada: tal cual, y «a igual composición», con la CEP reponderada para que tenga la misma mezcla de sexo, edad, educación y religión que la población (celdas que cubren el 96,77 % de los adultos).

El censo tiene más católicos y menos personas sin religión que la CEP, y la religión es una llave del emparejamiento. Por eso, tal cual, la población confía algo más en la Iglesia católica que la CEP.

| Opinión | Categorías | Diferencia tal cual | A igual composición | Dónde queda la mayor diferencia |
|---|---|---|---|---|
| `inmigrantes_criminalidad` | 7 | 1,02 | 2,63 | código 2: 41,3 % en la CEP y 43,9 % en la población |
| `votaria_voluntario` | 4 | 2,26 | 2,48 | código 2: 33,7 % en la CEP y 31,3 % en la población |
| `empleados_publicos` | 7 | 1,82 | 2,46 | código 1: 41,8 % en la CEP y 39,3 % en la población |
| `confianza_universidades` | 6 | 3,18 | 2,15 | código 3: 29,9 % en la CEP y 27,8 % en la población |
| `confianza_iglesia_catolica` | 6 | 4,07 | 2,07 | código 4: 26,9 % en la CEP y 24,8 % en la población |
| `libertades_o_seguridad` | 13 | 1,40 | 1,90 | código 7: 10,3 % en la CEP y 12,2 % en la población |
| `apoyo_democracia` | 5 | 0,51 | 1,89 | código 1: 51,7 % en la CEP y 53,6 % en la población |
| `confianza_sindicatos` | 6 | 1,79 | 1,77 | código 4: 21,3 % en la CEP y 19,5 % en la población |
| `estado_burocracia` | 7 | 1,42 | 1,65 | código 2: 39,9 % en la CEP y 41,5 % en la población |
| `confianza_tribunales` | 6 | 1,08 | 1,62 | código 2: 18,4 % en la CEP y 20,0 % en la población |
| `hijos_carga_financiera` | 7 | 1,29 | 1,55 | código 1: 8,4 % en la CEP y 6,9 % en la población |
| `justifica_marchas` | 7 | 0,70 | 1,55 | código 1: 23,0 % en la CEP y 24,6 % en la población |
| `confianza_partidos` | 6 | 1,74 | 1,52 | código 4: 49,0 % en la CEP y 47,5 % en la población |
| `interes_politica` | 7 | 1,89 | 1,45 | código 3: 23,2 % en la CEP y 24,6 % en la población |
| `reducir_gasto_publico` | 7 | 2,49 | 1,41 | código 2: 25,0 % en la CEP y 26,4 % en la población |
| `apertura_inmigracion` | 12 | 1,72 | 1,39 | código 1: 26,3 % en la CEP y 24,9 % en la población |
| `confianza_fuerzas_armadas` | 6 | 1,90 | 1,34 | código 3: 28,9 % en la CEP y 27,6 % en la población |
| `economia_personal_futuro` | 6 | 1,20 | 1,32 | código 3: 48,3 % en la CEP y 49,6 % en la población |
| `partido` | 15 | 1,38 | 1,31 | código 15: 52,2 % en la CEP y 53,5 % en la población |
| `economia_pais_futuro` | 5 | 1,17 | 1,30 | código 3: 31,6 % en la CEP y 30,3 % en la población |
| `rumbo_pais` | 5 | 2,05 | 1,30 | código 3: 25,7 % en la CEP y 24,4 % en la población |
| `hijos_restringen_carrera` | 7 | 1,39 | 1,29 | código 2: 29,2 % en la CEP y 30,4 % en la población |
| `ingresos_alcanzan` | 6 | 1,23 | 1,29 | código 2: 49,6 % en la CEP y 50,9 % en la población |
| `causa_delincuencia` | 14 | 1,07 | 1,28 | código 3: 11,2 % en la CEP y 12,5 % en la población |
| `clase_subjetiva` | 12 | 1,33 | 1,26 | código 4: 20,7 % en la CEP y 22,0 % en la población |
| `confianza_gobierno` | 6 | 0,82 | 1,26 | código 2: 19,3 % en la CEP y 20,6 % en la población |
| `inmigrantes_aporte` | 7 | 0,74 | 1,25 | código 3: 29,1 % en la CEP y 30,3 % en la población |
| `economia_personal` | 7 | 1,26 | 1,25 | código 4: 23,4 % en la CEP y 24,6 % en la población |
| `confianza_empresas` | 6 | 2,12 | 1,20 | código 2: 24,8 % en la CEP y 26,0 % en la población |
| `hijos_ideal` | 14 | 1,08 | 1,14 | código 3: 19,7 % en la CEP y 18,6 % en la población |
| `problema_3` | 19 | 0,93 | 1,09 | código 11: 5,3 % en la CEP y 6,4 % en la población |
| `confianza_carabineros` | 6 | 0,91 | 1,05 | código 2: 34,9 % en la CEP y 36,0 % en la población |
| `confianza_municipalidades` | 6 | 0,90 | 0,93 | código 4: 15,9 % en la CEP y 14,9 % en la población |
| `voto_segunda_vuelta_2025` | 6 | 0,94 | 0,89 | código 1: 31,9 % en la CEP y 32,8 % en la población |
| `situacion_politica` | 7 | 1,05 | 0,88 | código 3: 34,5 % en la CEP y 33,7 % en la población |
| `confianza_sistema_pensiones` | 6 | 0,90 | 0,87 | código 4: 27,7 % en la CEP y 26,8 % en la población |
| `confianza_redes_sociales` | 6 | 0,85 | 0,86 | código 2: 10,2 % en la CEP y 11,0 % en la población |
| `fuente_noticias` | 9 | 0,73 | 0,86 | código 2: 37,6 % en la CEP y 36,8 % en la población |
| `funciona_democracia` | 7 | 0,92 | 0,82 | código 1: 8,9 % en la CEP y 8,0 % en la población |
| `preocupa_pension` | 13 | 1,01 | 0,81 | código 8: 7,4 % en la CEP y 8,2 % en la población |
| `problema_2` | 18 | 0,88 | 0,80 | código 10: 13,3 % en la CEP y 12,4 % en la población |
| `menos_estado_economia` | 7 | 1,15 | 0,78 | código 4: 38,6 % en la CEP y 39,3 % en la población |
| `confianza_television` | 6 | 1,17 | 0,76 | código 2: 11,7 % en la CEP y 12,4 % en la población |
| `confianza_congreso` | 6 | 0,52 | 0,75 | código 3: 53,0 % en la CEP y 53,7 % en la población |
| `economia_pais` | 7 | 1,55 | 0,74 | código 1: 13,2 % en la CEP y 12,4 % en la población |
| `responsabilidad_sustento` | 12 | 0,99 | 0,70 | código 1: 14,7 % en la CEP y 14,0 % en la población |
| `problema_1` | 18 | 1,05 | 0,67 | código 9: 11,1 % en la CEP y 10,4 % en la población |
| `confianza_sistema_salud` | 6 | 0,93 | 0,63 | código 3: 54,2 % en la CEP y 54,9 % en la población |
| `justifica_fuerza_carabineros` | 7 | 1,34 | 0,60 | código 5: 16,7 % en la CEP y 16,1 % en la población |
| `posicion_politica` | 12 | 1,02 | 0,59 | código 3: 4,8 % en la CEP y 5,4 % en la población |
| `preocupa_enfermedad` | 11 | 1,23 | 0,57 | código 7: 5,9 % en la CEP y 6,5 % en la población |
| `aprueba_gobierno` | 5 | 0,84 | 0,45 | código 2: 52,0 % en la CEP y 52,4 % en la población |
| `preocupa_deudas` | 13 | 0,47 | 0,44 | código 6: 4,4 % en la CEP y 4,0 % en la población |
| `aprueba_gobierno_anterior` | 5 | 1,21 | 0,30 | código 3: 6,6 % en la CEP y 6,9 % en la población |

- ✔ distribuciones de las 54 opiniones imputadas desde la CEP: diferencia máxima de 2,63 puntos a igual composición; 5 opiniones superan los 2 puntos y ninguna el margen de error de la CEP (2,8)


### Correlaciones

Entre opiniones, y entre cada opinión y la edad, el sexo y la educación. Como todas las opiniones de una persona vienen del mismo entrevistado, la relación entre ellas debe conservarse casi intacta. La relación con la edad, el sexo y la educación se conserva porque son llaves del emparejamiento.

| Tipo de par | Pares | Diferencia media | Diferencia máxima | Correlación media en CEP (valor absoluto) |
|---|---|---|---|---|
| opinión × llave | 48 | 0,020 | 0,083 | 0,093 |
| opinión × opinión | 120 | 0,017 | 0,054 | 0,165 |
| llave × llave | 3 | 0,027 | 0,054 | 0,106 |

Los 12 pares que más difieren:

| Par | Tipo | CEP | Población | Diferencia |
|---|---|---|---|---|
| educación (1 a 4) × votó por Kast | opinión × llave | -0,043 | -0,126 | -0,083 |
| educación (1 a 4) × aprueba al gobierno | opinión × llave | 0,008 | -0,058 | -0,066 |
| confianza en Carabineros × sustento: responsabilidad personal | opinión × opinión | 0,173 | 0,119 | -0,054 |
| mujer × educación (1 a 4) | llave × llave | -0,035 | 0,019 | 0,054 |
| votó por Kast × interés en la política | opinión × opinión | -0,186 | -0,236 | -0,050 |
| posición (1 izquierda a 10 derecha) × interés en la política | opinión × opinión | -0,103 | -0,152 | -0,049 |
| educación (1 a 4) × buena situación económica propia | opinión × llave | 0,194 | 0,243 | 0,048 |
| educación (1 a 4) × posición (1 izquierda a 10 derecha) | opinión × llave | -0,039 | -0,083 | -0,044 |
| votó por Kast × buena situación económica propia | opinión × opinión | 0,014 | -0,030 | -0,044 |
| educación (1 a 4) × aprueba al gobierno anterior | opinión × llave | 0,079 | 0,121 | 0,042 |
| confianza en los sindicatos × apertura a la inmigración | opinión × opinión | 0,110 | 0,069 | -0,040 |
| educación (1 a 4) × confianza en el gobierno | opinión × llave | 0,010 | -0,029 | -0,040 |

Las relaciones más fuertes de la fuente, para ver que se conservan:

| Par | Tipo | CEP | Población | Diferencia |
|---|---|---|---|---|
| aprueba al gobierno anterior × votó por Kast | opinión × opinión | -0,665 | -0,659 | 0,006 |
| aprueba al gobierno × votó por Kast | opinión × opinión | 0,658 | 0,671 | 0,013 |
| posición (1 izquierda a 10 derecha) × votó por Kast | opinión × opinión | 0,577 | 0,570 | -0,008 |
| aprueba al gobierno × confianza en el gobierno | opinión × opinión | 0,544 | 0,559 | 0,016 |
| votó por Kast × confianza en el gobierno | opinión × opinión | 0,524 | 0,525 | 0,001 |
| posición (1 izquierda a 10 derecha) × aprueba al gobierno | opinión × opinión | 0,522 | 0,503 | -0,019 |
| buena situación económica propia × los ingresos no alcanzan | opinión × opinión | -0,502 | -0,488 | 0,013 |
| posición (1 izquierda a 10 derecha) × aprueba al gobierno anterior | opinión × opinión | -0,469 | -0,450 | 0,018 |
| confianza en el gobierno × confianza en Carabineros | opinión × opinión | 0,455 | 0,468 | 0,012 |
| posición (1 izquierda a 10 derecha) × confianza en el gobierno | opinión × opinión | 0,450 | 0,425 | -0,025 |
| aprueba al gobierno × aprueba al gobierno anterior | opinión × opinión | -0,382 | -0,376 | 0,006 |
| confianza en el gobierno × confianza en las empresas | opinión × opinión | 0,377 | 0,361 | -0,017 |

- ✔ correlaciones opinión × opinión (CEP): diferencia media de 0,017 en 120 pares; máxima de 0,054
- ✔ correlaciones opinión × llave (CEP): diferencia media de 0,020 en 48 pares; máxima de 0,083


## 4. Entre Casen y la CEP: sin fuente con qué comparar

Ninguna encuesta mide a la vez el ingreso de Casen y las opiniones de la CEP. En la población esas relaciones existen solo a través de lo que ambas imputaciones comparten: sexo, edad, educación, zona, actividad y nivel socioeconómico. Son plausibles, pero no están validadas; se muestran para que se sepa qué hay.

| Par | Correlación en la población |
|---|---|
| decil de ingreso × posición (1 izquierda a 10 derecha) | -0,058 |
| decil de ingreso × aprueba al gobierno | -0,033 |
| decil de ingreso × los ingresos no alcanzan | -0,180 |
| decil de ingreso × buena situación económica propia | 0,192 |
| decil de ingreso × sustento: responsabilidad personal | 0,008 |
| isapre × posición (1 izquierda a 10 derecha) | -0,034 |
| isapre × aprueba al gobierno | -0,024 |
| isapre × los ingresos no alcanzan | -0,104 |
| isapre × buena situación económica propia | 0,119 |
| isapre × sustento: responsabilidad personal | 0,010 |
| cotiza para pensión × posición (1 izquierda a 10 derecha) | -0,055 |
| cotiza para pensión × aprueba al gobierno | -0,032 |
| cotiza para pensión × los ingresos no alcanzan | -0,113 |
| cotiza para pensión × buena situación económica propia | 0,102 |
| cotiza para pensión × sustento: responsabilidad personal | 0,040 |

## Resultado

Todas las comprobaciones pasan.

Fuentes: INE, Censo de Población y Vivienda 2024; Ministerio de Desarrollo Social y Familia, Encuesta Casen 2024; Centro de Estudios Públicos, Encuesta CEP N° 96.

