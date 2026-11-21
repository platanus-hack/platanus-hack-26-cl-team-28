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
| Decil de ingreso del hogar | 10 | 0,38 | — | código 10: 10,0 % en Casen y 9,6 % en la población |
| Pobreza por ingresos del hogar | 3 | 0,09 | — | código 2: 10,1 % en Casen y 10,1 % en la población |
| Vehículo en el hogar | 2 | 1,25 | — | código 1: 53,8 % en Casen y 52,5 % en la población |
| Alguien a quien pedir dinero | 5 | 0,66 | — | código 1: 48,5 % en Casen y 49,2 % en la población |
| Sin discriminación en el hogar | 2 | 0,06 | — | código 0: 19,3 % en Casen y 19,3 % en la población |
| Previsión de salud | 6 | 1,58 | 0,60 | código 2: 12,2 % en Casen y 11,6 % en la población |
| Grupo de Fonasa | 5 | 1,88 | 0,92 | código 1: 25,3 % en Casen y 24,4 % en la población |
| Categoría ocupacional de los ocupados | 9 | 9,65 | 0,55 | código 5: 50,3 % en Casen y 49,8 % en la población |
| Contrato de los asalariados | 3 | 1,11 | 0,82 | código 1: 87,0 % en Casen y 86,1 % en la población |
| Cotiza para pensión (15 años o más) | 3 | 4,96 | 0,41 | código 0: 59,0 % en Casen y 58,6 % en la población |
| Participación en organizaciones | 15 | 0,86 | 0,56 | código 15: 72,7 % en Casen y 72,1 % en la población |
| Tipo de colegio (14 a 17 años que asisten) | 5 | 0,47 | 0,81 | código 4: 4,7 % en Casen y 3,9 % en la población |

- ✔ distribuciones nacionales de lo imputado desde Casen: diferencia máxima de 1,25 puntos (hogares tal cual; personas a igual composición)


### Por región

Porcentaje de hogares en pobreza por ingresos e ingreso medio per cápita del hogar, en Casen y en la población. Casen es representativa por región.

| Región | Pobreza Casen % | Pobreza población % | Diferencia | Ingreso Casen $ | Ingreso población $ | Diferencia | Deciles 9 y 10 Casen % | Deciles 9 y 10 población % |
|---|---|---|---|---|---|---|---|---|
| Tarapacá | 19,9 | 20,0 | 0,06 | 682.508 | 698.805 | 2,4 % | 17,3 | 18,2 |
| Antofagasta | 15,5 | 15,8 | 0,24 | 806.071 | 810.383 | 0,5 % | 21,1 | 21,5 |
| Atacama | 17,9 | 17,9 | -0,09 | 692.229 | 676.238 | -2,3 % | 16,8 | 15,8 |
| Coquimbo | 20,3 | 20,6 | 0,24 | 628.364 | 619.968 | -1,3 % | 13,5 | 13,0 |
| Valparaíso | 17,9 | 17,7 | -0,17 | 676.484 | 683.757 | 1,1 % | 15,7 | 16,1 |
| Libertador General Bernardo O'Higgins | 17,9 | 17,1 | -0,76 | 634.667 | 624.546 | -1,6 % | 12,7 | 12,5 |
| Maule | 24,0 | 23,5 | -0,53 | 527.732 | 514.778 | -2,5 % | 8,4 | 7,8 |
| Biobío | 18,8 | 18,8 | 0,06 | 658.997 | 649.680 | -1,4 % | 14,4 | 14,2 |
| La Araucanía | 28,0 | 28,4 | 0,42 | 552.892 | 535.926 | -3,1 % | 10,6 | 9,9 |
| Los Lagos | 16,9 | 17,2 | 0,26 | 668.107 | 660.632 | -1,1 % | 15,3 | 15,1 |
| Aysén del General Carlos Ibáñez del Campo | 14,1 | 13,5 | -0,55 | 887.436 | 854.308 | -3,7 % | 25,1 | 23,8 |
| Magallanes y de la Antártica Chilena | 10,4 | 10,3 | -0,17 | 938.187 | 900.597 | -4,0 % | 26,1 | 24,9 |
| Metropolitana de Santiago | 12,8 | 12,5 | -0,23 | 980.298 | 977.950 | -0,2 % | 28,4 | 28,3 |
| Los Ríos | 22,2 | 22,3 | 0,02 | 626.302 | 615.380 | -1,7 % | 14,2 | 13,5 |
| Arica y Parinacota | 19,6 | 18,5 | -1,16 | 623.626 | 627.353 | 0,6 % | 13,2 | 13,0 |
| Ñuble | 24,5 | 24,5 | -0,01 | 551.152 | 548.430 | -0,5 % | 9,6 | 9,5 |

- ✔ pobreza de cada región: diferencia máxima de 1,16 puntos
- ✔ ingreso medio de cada región: diferencia máxima de 4,0 %


### Por comuna

Porcentaje de personas de 14 años o más en el quintil V de ingreso, en las comunas con al menos 300 casos en Casen. Casen no es representativa por comuna, así que no se exige que cada cifra calce, sino que se mantengan el orden y la distancia entre comunas: que la población no aplaste las diferencias entre, por ejemplo, Vitacura y La Pintana.

| Comuna | Región | Quintil V Casen % | Quintil V población % | Diferencia | Casos Casen |
|---|---|---|---|---|---|
| Vitacura | Metropolitana de Santiago | 88,2 | 85,3 | -2,9 | 371 |
| Las Condes | Metropolitana de Santiago | 72,3 | 70,7 | -1,6 | 1.280 |
| Providencia | Metropolitana de Santiago | 70,4 | 71,4 | 1,0 | 775 |
| Ñuñoa | Metropolitana de Santiago | 65,4 | 65,9 | 0,5 | 1.365 |
| La Reina | Metropolitana de Santiago | 57,9 | 51,4 | -6,5 | 374 |
| Lo Barnechea | Metropolitana de Santiago | 50,3 | 50,3 | -0,0 | 418 |
| San Miguel | Metropolitana de Santiago | 42,4 | 42,9 | 0,5 | 709 |
| Concón | Valparaíso | 40,1 | 37,7 | -2,4 | 585 |
| Panguipulli | Los Ríos | 1,9 | 3,5 | 1,5 | 590 |
| Molina | Maule | 1,8 | 3,6 | 1,8 | 635 |
| Cartagena | Valparaíso | 1,8 | 4,0 | 2,2 | 339 |
| Vicuña | Coquimbo | 1,6 | 3,8 | 2,2 | 318 |
| Cauquenes | Maule | 1,6 | 2,6 | 1,1 | 415 |
| Monte Patria | Coquimbo | 1,1 | 2,8 | 1,8 | 368 |
| Los Lagos | Los Ríos | 0,8 | 3,0 | 2,2 | 385 |
| Nacimiento | Biobío | 0,7 | 1,9 | 1,2 | 381 |

Están las ocho comunas con más y las ocho con menos quintil V según Casen, de 147 comparables.


- ✔ orden de las comunas por quintil V: correlación de 0,993 entre Casen y la población en 147 comunas
- ✔ distancia entre comunas por quintil V: pendiente de 0,96 (1 sería el mismo gradiente que Casen); error medio de 1,3 puntos


### Por edad

Porcentaje de personas que viven en hogares en pobreza por ingresos e ingreso medio per cápita de su hogar, según su edad. El ingreso se imputa al hogar, así que esta relación depende de que el emparejamiento distinga los hogares con niños de los hogares con adultos mayores.

| Edad | Pobreza Casen % | Pobreza población % | Diferencia | Ingreso Casen $ | Ingreso población $ | Diferencia |
|---|---|---|---|---|---|---|
| 14 a 17 | 24,2 | 23,6 | -0,58 | 473.144 | 481.534 | 1,8 % |
| 18 a 29 | 18,2 | 16,6 | -1,53 | 569.031 | 629.531 | 10,6 % |
| 30 a 44 | 14,5 | 15,7 | 1,28 | 784.973 | 739.286 | -5,8 % |
| 45 a 64 | 15,3 | 15,7 | 0,40 | 716.968 | 687.612 | -4,1 % |
| 65 o más | 12,4 | 13,7 | 1,33 | 661.347 | 656.293 | -0,8 % |

- ✔ pobreza de cada tramo de edad: diferencia máxima de 1,53 puntos


### Tipo de colegio de los menores

Porcentaje de los menores de 14 a 17 años que asisten a clases según el tipo de colegio, por quintil de ingreso de su hogar. El censo no pregunta el tipo de colegio: se imputa desde Casen según el decil del hogar, la región y la zona.

| Quintil | Público Casen % | Público población % | Subvencionado Casen % | Subvencionado población % | Pagado Casen % | Pagado población % | Delegada Casen % | Delegada población % |
|---|---|---|---|---|---|---|---|---|
| 1 | 45,0 | 45,8 | 49,7 | 49,0 | 1,0 | 0,9 | 4,3 | 4,3 |
| 2 | 39,8 | 41,1 | 52,7 | 51,6 | 2,1 | 1,9 | 5,4 | 5,3 |
| 3 | 34,7 | 35,1 | 56,5 | 56,4 | 4,1 | 4,1 | 4,7 | 4,4 |
| 4 | 24,7 | 25,0 | 56,3 | 56,1 | 17,5 | 17,4 | 1,5 | 1,5 |
| 5 | 9,8 | 9,9 | 31,3 | 31,4 | 58,6 | 58,4 | 0,3 | 0,4 |

- ✔ tipo de colegio por quintil de ingreso: diferencia máxima de 1,28 puntos; cada quintil tiene pocos casos en Casen, por eso la tolerancia es de 4


### Correlaciones

Correlación de Pearson entre pares de datos, en Casen y en la población. «Observado» es lo que viene del censo y «imputado», lo que viene de Casen. Las de dos datos observados no dependen de la imputación: difieren porque el censo y Casen no miden igual la educación ni el empleo.

| Tipo de par | Pares | Diferencia media | Diferencia máxima | Correlación media en Casen (valor absoluto) |
|---|---|---|---|---|
| imputado × observado | 83 | 0,018 | 0,097 | 0,098 |
| imputado × imputado | 66 | 0,017 | 0,081 | 0,146 |
| observado × observado | 21 | 0,010 | 0,032 | 0,094 |

Los 12 pares que más difieren:

| Par | Tipo | Casen | Población | Diferencia |
|---|---|---|---|---|
| escolaridad (15+) × vehículo en el hogar | imputado × observado | 0,222 | 0,125 | -0,097 |
| escolaridad (15+) × decil de ingreso | imputado × observado | 0,463 | 0,379 | -0,084 |
| vehículo en el hogar × isapre | imputado × imputado | 0,199 | 0,118 | -0,081 |
| decil de ingreso × cotiza para pensión | imputado × imputado | 0,421 | 0,348 | -0,073 |
| indígena × participa en organizaciones | imputado × observado | 0,084 | 0,011 | -0,073 |
| ocupado (15+) × decil de ingreso | imputado × observado | 0,378 | 0,311 | -0,066 |
| escolaridad (15+) × inseguridad alimentaria | imputado × observado | -0,145 | -0,082 | 0,062 |
| pobreza × cotiza para pensión | imputado × imputado | -0,232 | -0,171 | 0,060 |
| participa en organizaciones × discriminación en el hogar | imputado × imputado | 0,051 | -0,010 | -0,060 |
| escolaridad (15+) × isapre | imputado × observado | 0,345 | 0,289 | -0,057 |
| isapre × inseguridad alimentaria | imputado × imputado | -0,172 | -0,120 | 0,052 |
| ocupado (15+) × pobreza | imputado × observado | -0,198 | -0,148 | 0,051 |

Las relaciones más fuertes de la fuente, para ver que se conservan:

| Par | Tipo | Casen | Población | Diferencia |
|---|---|---|---|---|
| decil de ingreso × ingreso per cápita (log) | imputado × imputado | 0,763 | 0,781 | 0,018 |
| ocupado (15+) × cotiza para pensión | imputado × observado | 0,682 | 0,633 | -0,050 |
| cotiza para pensión × tiene contrato | imputado × imputado | 0,657 | 0,678 | 0,021 |
| decil de ingreso × pobreza | imputado × imputado | -0,542 | -0,544 | -0,002 |
| ingreso per cápita (log) × pobreza | imputado × imputado | -0,500 | -0,510 | -0,010 |
| escolaridad (15+) × decil de ingreso | imputado × observado | 0,463 | 0,379 | -0,084 |
| decil de ingreso × isapre | imputado × imputado | 0,437 | 0,399 | -0,038 |
| decil de ingreso × cotiza para pensión | imputado × imputado | 0,421 | 0,348 | -0,073 |
| ingreso per cápita (log) × isapre | imputado × imputado | 0,403 | 0,364 | -0,038 |
| ocupado (15+) × decil de ingreso | imputado × observado | 0,378 | 0,311 | -0,066 |
| escolaridad (15+) × cotiza para pensión | imputado × observado | 0,369 | 0,354 | -0,015 |
| edad × escolaridad (15+) | observado × observado | -0,354 | -0,322 | 0,032 |

- ✔ correlaciones imputado × imputado (Casen): diferencia media de 0,017 en 66 pares; máxima de 0,081
- ✔ correlaciones imputado × observado (Casen): diferencia media de 0,018 en 83 pares; máxima de 0,097


## 3. Contra la CEP

La Encuesta CEP N° 96 tiene 1.466 entrevistas a mayores de 18 años. Se pondera con `pond`.

### Distribuciones

Diferencia máxima, en puntos porcentuales, entre los adultos de la población y la CEP en cada opinión imputada: tal cual, y «a igual composición», con la CEP reponderada para que tenga la misma mezcla de sexo, edad, educación y religión que la población (celdas que cubren el 96,77 % de los adultos).

El censo tiene más católicos y menos personas sin religión que la CEP, y la religión es una llave del emparejamiento. Por eso, tal cual, la población confía algo más en la Iglesia católica que la CEP.

| Opinión | Categorías | Diferencia tal cual | A igual composición | Dónde queda la mayor diferencia |
|---|---|---|---|---|
| `inmigrantes_criminalidad` | 7 | 1,01 | 2,65 | código 2: 41,3 % en la CEP y 43,9 % en la población |
| `votaria_voluntario` | 4 | 2,32 | 2,54 | código 2: 33,7 % en la CEP y 31,2 % en la población |
| `empleados_publicos` | 7 | 1,80 | 2,42 | código 1: 41,8 % en la CEP y 39,4 % en la población |
| `confianza_universidades` | 6 | 3,22 | 2,20 | código 3: 29,9 % en la CEP y 27,7 % en la población |
| `confianza_iglesia_catolica` | 6 | 4,07 | 2,07 | código 4: 26,9 % en la CEP y 24,8 % en la población |
| `apoyo_democracia` | 5 | 0,49 | 1,93 | código 1: 51,7 % en la CEP y 53,6 % en la población |
| `libertades_o_seguridad` | 13 | 1,39 | 1,89 | código 7: 10,3 % en la CEP y 12,1 % en la población |
| `confianza_sindicatos` | 6 | 1,84 | 1,82 | código 4: 21,3 % en la CEP y 19,5 % en la población |
| `estado_burocracia` | 7 | 1,45 | 1,68 | código 2: 39,9 % en la CEP y 41,6 % en la población |
| `confianza_tribunales` | 6 | 1,04 | 1,58 | código 2: 18,4 % en la CEP y 20,0 % en la población |
| `hijos_carga_financiera` | 7 | 1,29 | 1,56 | código 1: 8,4 % en la CEP y 6,9 % en la población |
| `justifica_marchas` | 7 | 0,69 | 1,55 | código 1: 23,0 % en la CEP y 24,6 % en la población |
| `confianza_partidos` | 6 | 1,74 | 1,52 | código 4: 49,0 % en la CEP y 47,5 % en la población |
| `interes_politica` | 7 | 1,88 | 1,43 | código 3: 23,2 % en la CEP y 24,6 % en la población |
| `apertura_inmigracion` | 12 | 1,77 | 1,40 | código 1: 26,3 % en la CEP y 24,9 % en la población |
| `economia_personal_futuro` | 6 | 1,23 | 1,35 | código 3: 48,3 % en la CEP y 49,6 % en la población |
| `reducir_gasto_publico` | 7 | 2,42 | 1,34 | código 2: 25,0 % en la CEP y 26,4 % en la población |
| `ingresos_alcanzan` | 6 | 1,28 | 1,34 | código 2: 49,6 % en la CEP y 51,0 % en la población |
| `hijos_restringen_carrera` | 7 | 1,37 | 1,32 | código 2: 29,2 % en la CEP y 30,5 % en la población |
| `confianza_fuerzas_armadas` | 6 | 1,88 | 1,32 | código 3: 28,9 % en la CEP y 27,6 % en la población |
| `partido` | 15 | 1,38 | 1,30 | código 15: 52,2 % en la CEP y 53,5 % en la población |
| `economia_personal` | 7 | 1,31 | 1,29 | código 4: 23,4 % en la CEP y 24,7 % en la población |
| `economia_pais_futuro` | 5 | 1,16 | 1,29 | código 3: 31,6 % en la CEP y 30,3 % en la población |
| `rumbo_pais` | 5 | 2,01 | 1,28 | código 3: 25,7 % en la CEP y 24,5 % en la población |
| `inmigrantes_aporte` | 7 | 0,75 | 1,27 | código 3: 29,1 % en la CEP y 30,3 % en la población |
| `causa_delincuencia` | 14 | 1,14 | 1,25 | código 3: 11,2 % en la CEP y 12,5 % en la población |
| `confianza_empresas` | 6 | 2,16 | 1,24 | código 2: 24,8 % en la CEP y 26,1 % en la población |
| `clase_subjetiva` | 12 | 1,31 | 1,24 | código 4: 20,7 % en la CEP y 21,9 % en la población |
| `confianza_gobierno` | 6 | 0,76 | 1,20 | código 2: 19,3 % en la CEP y 20,5 % en la población |
| `confianza_carabineros` | 6 | 0,96 | 1,14 | código 2: 34,9 % en la CEP y 36,1 % en la población |
| `hijos_ideal` | 14 | 1,08 | 1,10 | código 3: 19,7 % en la CEP y 18,6 % en la población |
| `problema_3` | 19 | 0,94 | 1,09 | código 11: 5,3 % en la CEP y 6,4 % en la población |
| `confianza_municipalidades` | 6 | 0,90 | 0,94 | código 4: 15,9 % en la CEP y 14,9 % en la población |
| `confianza_sistema_pensiones` | 6 | 0,95 | 0,92 | código 4: 27,7 % en la CEP y 26,8 % en la población |
| `voto_segunda_vuelta_2025` | 6 | 0,96 | 0,92 | código 1: 31,9 % en la CEP y 32,8 % en la población |
| `confianza_redes_sociales` | 6 | 0,85 | 0,89 | código 2: 10,2 % en la CEP y 11,0 % en la población |
| `situacion_politica` | 7 | 1,04 | 0,89 | código 3: 34,5 % en la CEP y 33,7 % en la población |
| `fuente_noticias` | 9 | 0,72 | 0,88 | código 2: 37,6 % en la CEP y 36,8 % en la población |
| `preocupa_pension` | 13 | 1,02 | 0,83 | código 8: 7,4 % en la CEP y 8,3 % en la población |
| `problema_2` | 18 | 0,88 | 0,81 | código 10: 13,3 % en la CEP y 12,4 % en la población |
| `funciona_democracia` | 7 | 0,91 | 0,81 | código 1: 8,9 % en la CEP y 8,0 % en la población |
| `menos_estado_economia` | 7 | 1,20 | 0,80 | código 4: 38,6 % en la CEP y 39,4 % en la población |
| `confianza_congreso` | 6 | 0,55 | 0,78 | código 3: 53,0 % en la CEP y 53,7 % en la población |
| `economia_pais` | 7 | 1,60 | 0,75 | código 1: 13,2 % en la CEP y 12,4 % en la población |
| `confianza_television` | 6 | 1,15 | 0,74 | código 2: 11,7 % en la CEP y 12,4 % en la población |
| `responsabilidad_sustento` | 12 | 0,99 | 0,73 | código 1: 14,7 % en la CEP y 13,9 % en la población |
| `problema_1` | 18 | 1,09 | 0,71 | código 3: 33,0 % en la CEP y 33,7 % en la población |
| `posicion_politica` | 12 | 0,96 | 0,61 | código 3: 4,8 % en la CEP y 5,4 % en la población |
| `preocupa_enfermedad` | 11 | 1,23 | 0,60 | código 7: 5,9 % en la CEP y 6,5 % en la población |
| `justifica_fuerza_carabineros` | 7 | 1,36 | 0,57 | código 5: 16,7 % en la CEP y 16,1 % en la población |
| `confianza_sistema_salud` | 6 | 0,85 | 0,55 | código 3: 54,2 % en la CEP y 54,8 % en la población |
| `aprueba_gobierno` | 5 | 0,84 | 0,46 | código 2: 52,0 % en la CEP y 52,4 % en la población |
| `preocupa_deudas` | 13 | 0,46 | 0,43 | código 6: 4,4 % en la CEP y 4,0 % en la población |
| `aprueba_gobierno_anterior` | 5 | 1,21 | 0,27 | código 3: 6,6 % en la CEP y 6,9 % en la población |

- ✔ distribuciones de las 54 opiniones imputadas desde la CEP: diferencia máxima de 2,65 puntos a igual composición; 5 opiniones superan los 2 puntos y ninguna el margen de error de la CEP (2,8)


### Correlaciones

Entre opiniones, y entre cada opinión y la edad, el sexo y la educación. Como todas las opiniones de una persona vienen del mismo entrevistado, la relación entre ellas debe conservarse casi intacta. La relación con la edad, el sexo y la educación se conserva porque son llaves del emparejamiento.

| Tipo de par | Pares | Diferencia media | Diferencia máxima | Correlación media en CEP (valor absoluto) |
|---|---|---|---|---|
| opinión × llave | 48 | 0,019 | 0,082 | 0,093 |
| llave × llave | 3 | 0,027 | 0,054 | 0,106 |
| opinión × opinión | 120 | 0,017 | 0,052 | 0,165 |

Los 12 pares que más difieren:

| Par | Tipo | CEP | Población | Diferencia |
|---|---|---|---|---|
| educación (1 a 4) × votó por Kast | opinión × llave | -0,043 | -0,125 | -0,082 |
| educación (1 a 4) × aprueba al gobierno | opinión × llave | 0,008 | -0,058 | -0,066 |
| mujer × educación (1 a 4) | llave × llave | -0,035 | 0,019 | 0,054 |
| confianza en Carabineros × sustento: responsabilidad personal | opinión × opinión | 0,173 | 0,121 | -0,052 |
| votó por Kast × interés en la política | opinión × opinión | -0,186 | -0,236 | -0,050 |
| posición (1 izquierda a 10 derecha) × interés en la política | opinión × opinión | -0,103 | -0,151 | -0,048 |
| educación (1 a 4) × buena situación económica propia | opinión × llave | 0,194 | 0,240 | 0,045 |
| votó por Kast × buena situación económica propia | opinión × opinión | 0,014 | -0,030 | -0,044 |
| educación (1 a 4) × posición (1 izquierda a 10 derecha) | opinión × llave | -0,039 | -0,083 | -0,043 |
| educación (1 a 4) × aprueba al gobierno anterior | opinión × llave | 0,079 | 0,121 | 0,042 |
| confianza en los sindicatos × apertura a la inmigración | opinión × opinión | 0,110 | 0,069 | -0,040 |
| educación (1 a 4) × confianza en el gobierno | opinión × llave | 0,010 | -0,030 | -0,040 |

Las relaciones más fuertes de la fuente, para ver que se conservan:

| Par | Tipo | CEP | Población | Diferencia |
|---|---|---|---|---|
| aprueba al gobierno anterior × votó por Kast | opinión × opinión | -0,665 | -0,658 | 0,007 |
| aprueba al gobierno × votó por Kast | opinión × opinión | 0,658 | 0,672 | 0,014 |
| posición (1 izquierda a 10 derecha) × votó por Kast | opinión × opinión | 0,577 | 0,570 | -0,007 |
| aprueba al gobierno × confianza en el gobierno | opinión × opinión | 0,544 | 0,560 | 0,016 |
| votó por Kast × confianza en el gobierno | opinión × opinión | 0,524 | 0,525 | 0,001 |
| posición (1 izquierda a 10 derecha) × aprueba al gobierno | opinión × opinión | 0,522 | 0,503 | -0,019 |
| buena situación económica propia × los ingresos no alcanzan | opinión × opinión | -0,502 | -0,488 | 0,013 |
| posición (1 izquierda a 10 derecha) × aprueba al gobierno anterior | opinión × opinión | -0,469 | -0,450 | 0,019 |
| confianza en el gobierno × confianza en Carabineros | opinión × opinión | 0,455 | 0,466 | 0,011 |
| posición (1 izquierda a 10 derecha) × confianza en el gobierno | opinión × opinión | 0,450 | 0,424 | -0,025 |
| aprueba al gobierno × aprueba al gobierno anterior | opinión × opinión | -0,382 | -0,376 | 0,006 |
| confianza en el gobierno × confianza en las empresas | opinión × opinión | 0,377 | 0,360 | -0,017 |

- ✔ correlaciones opinión × opinión (CEP): diferencia media de 0,017 en 120 pares; máxima de 0,052
- ✔ correlaciones opinión × llave (CEP): diferencia media de 0,019 en 48 pares; máxima de 0,082


## 4. Entre Casen y la CEP: sin fuente con qué comparar

Ninguna encuesta mide a la vez el ingreso de Casen y las opiniones de la CEP. En la población esas relaciones existen solo a través de lo que ambas imputaciones comparten: sexo, edad, educación, zona, actividad y nivel socioeconómico. Son plausibles, pero no están validadas; se muestran para que se sepa qué hay.

| Par | Correlación en la población |
|---|---|
| decil de ingreso × posición (1 izquierda a 10 derecha) | -0,057 |
| decil de ingreso × aprueba al gobierno | -0,032 |
| decil de ingreso × los ingresos no alcanzan | -0,174 |
| decil de ingreso × buena situación económica propia | 0,186 |
| decil de ingreso × sustento: responsabilidad personal | 0,006 |
| isapre × posición (1 izquierda a 10 derecha) | -0,034 |
| isapre × aprueba al gobierno | -0,025 |
| isapre × los ingresos no alcanzan | -0,102 |
| isapre × buena situación económica propia | 0,117 |
| isapre × sustento: responsabilidad personal | 0,009 |
| cotiza para pensión × posición (1 izquierda a 10 derecha) | -0,055 |
| cotiza para pensión × aprueba al gobierno | -0,032 |
| cotiza para pensión × los ingresos no alcanzan | -0,110 |
| cotiza para pensión × buena situación económica propia | 0,100 |
| cotiza para pensión × sustento: responsabilidad personal | 0,039 |

## Resultado

Todas las comprobaciones pasan.

Fuentes: INE, Censo de Población y Vivienda 2024; Ministerio de Desarrollo Social y Familia, Encuesta Casen 2024; Centro de Estudios Públicos, Encuesta CEP N° 96.

