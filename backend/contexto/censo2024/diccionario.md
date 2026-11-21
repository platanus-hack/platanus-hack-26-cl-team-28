# Diccionario de variables de los microdatos del Censo 2024

Generado por `scripts/construir_contexto.py` desde `data/censo2024/docs/diccionario_variables_censo2024.xlsx` (INE).
La columna Casos es el conteo publicado por el INE, verificado contra los Parquet al generar este archivo.

Valores especiales en todas las tablas:

- `-99`: no responde. El INE lo excluye de los denominadores al calcular porcentajes.
- `-66`: valor suprimido por anonimización.
- `NULL` (NA): la pregunta no aplica a esa unidad.

## viviendas

`viviendas_censo2024.parquet`: 7.664.466 filas, 25 columnas. Llave: `id_vivienda`.

- `id_vivienda` (INTEGER): Llave identificadora de la vivienda o de la entrevista. Rango 1:7664466; Válidos. Universo: Todos los registros.
- `region` (INTEGER): Región. Rango 1:16; Ver diccionario códigos territoriales. Universo: Todos los registros.
- `provincia` (INTEGER): Provincia. Rango 11:163; Ver diccionario códigos territoriales. Universo: Todos los registros.
- `comuna` (INTEGER): Comuna. Rango 1101:16305; Ver diccionario códigos territoriales. Universo: Todos los registros.

### `area`: Área urbana o rural

INTEGER. Universo: Todos los registros.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | Urbano | 6.365.998 |
| 2 | Rural | 1.298.468 |


### `tipo_operativo`: Tipo de operativo

INTEGER. Universo: Todos los registros.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | Persona en situación de calle | 21.750 |
| 2 | Vivienda particular | 7.638.396 |
| 3 | Vivienda colectiva | 4.320 |


### `p2_tipo_vivienda`: 2. Tipo de vivienda particular

INTEGER. Universo: Todas las viviendas particulares.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | Casa | 5.937.284 |
| 3 | Departamento | 1.579.970 |
| 5 | Vivienda tradicional indígena (ruka u otras) | 1.967 |
| 6 | Pieza en casa antigua o en conventillo | 51.305 |
| 7 | Mediagua, mejora, vivienda de emergencia, rancho o choza | 27.490 |
| 8 | Móvil (carpa, casa rodante o similar) | 1.557 |
| 9 | Otro tipo de vivienda particular | 38.823 |
| NA | No aplica | 26.070 |


### `p3a_estado_ocupacion`: 3a. Estado de ocupación de la vivienda

INTEGER. Universo: Todas las viviendas particulares.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | Ocupada | 6.730.463 |
| 2 | Desocupada | 907.933 |
| NA | No aplica | 26.070 |


### `p3b_estado_ocupacion`: 3b. Estado de ocupación de la vivienda (detalle)

INTEGER. Universo: Todas las viviendas particulares.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | Moradores presentes | 6.408.172 |
| 2 | Moradores ausentes | 208.084 |
| 6 | Otras razones de no entrevista | 114.207 |
| 7 | En venta o arriendo | 173.315 |
| 8 | Vivienda de temporada (veraneo o de uso temporal) | 476.135 |
| 9 | Abandonada | 97.052 |
| 10 | Otra razón de desocupación | 161.431 |
| NA | No aplica | 26.070 |


### `p4a_mat_paredes`: 4a. ¿Cuál es el material de construcción en las paredes exteriores?

INTEGER. Universo: Todas las viviendas particulares ocupadas con moradores presentes.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | Hormigón armado | 1.499.949 |
| 2 | Albañilería: bloque de cemento, ladrillo o piedra | 2.754.185 |
| 3 | Tabique forrado por ambas caras (madera o acero) | 1.854.738 |
| 4 | Tabique sin forro interior (madera u otro) | 176.313 |
| 5 | Adobe, barro, pirca, quincha u otro material artesanal | 106.790 |
| 6 | Materiales precarios o de desecho: cartón, sacos, trozos de latas o plásticos, etc. | 14.752 |
| -99 | No respuesta | 1.445 |
| NA | No aplica | 1.256.294 |


### `p4b_mat_techo`: 4b. ¿Cuál es el material de construcción en la cubierta del techo?

INTEGER. Universo: Todas las viviendas particulares ocupadas con moradores presentes.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | Tejas o tejuelas de arcilla, metálicas, de cemento, de madera, asfálticas o plásticas | 1.069.613 |
| 2 | Losa hormigón | 958.191 |
| 3 | Planchas metálicas de zinc, cobre, etc | 3.658.013 |
| 4 | Planchas de fibrocemento tipo pizarreño | 699.395 |
| 5 | Fonolita o plancha de fieltro embreado | 10.847 |
| 6 | Paja, coirón, totora o caña | 1.090 |
| 7 | Materiales precarios o de desecho: cartón, sacos, trozos de latas o plásticos, etc | 6.800 |
| 8 | Sin cubierta sólida de techo | 1.872 |
| -99 | No respuesta | 2.351 |
| NA | No aplica | 1.256.294 |


### `p4c_mat_piso`: 4c. ¿Cuál es el material de construcción en el piso?

INTEGER. Universo: Todas las viviendas particulares ocupadas con moradores presentes.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | Parquet, piso flotante, cerámico, madera, alfombra, flexit, cubrepiso u otro similar; sobre radier o vigas de madera | 6.036.357 |
| 2 | Radier sin revestimiento | 145.177 |
| 3 | Baldosa de cemento | 143.611 |
| 4 | Capa de cemento sobre tierra | 63.853 |
| 5 | Tierra | 17.010 |
| -99 | No respuesta | 2.164 |
| NA | No aplica | 1.256.294 |


### `p5_num_dormitorios`: 5. ¿Cuántas piezas de esta vivienda se usan exclusivamente como dormitorio?

INTEGER. Universo: Todas las viviendas particulares ocupadas con moradores presentes.

| Valor | Etiqueta | Casos |
|---|---|---|
| 0 | 0 | 36.835 |
| 1 | 1 | 1.575.168 |
| 2 | 2 | 2.419.639 |
| 3 | 3 | 1.785.285 |
| 4 | 4 | 451.532 |
| 5 | 5 | 100.036 |
| 6 | 6 o más | 38.643 |
| -99 | No respuesta | 1.034 |
| NA | No aplica | 1.256.294 |


### `p6_fuente_agua`: 6. El agua que usa esta vivienda proviene principalmente de:

INTEGER. Universo: Todas las viviendas particulares ocupadas con moradores presentes.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | Red pública | 5.914.136 |
| 2 | Pozo o noria | 263.309 |
| ​3 | Camión aljibe | 131.141 |
| ​4 | Río, vertiente, estero, canal, lago, agua lluvia, etc. | 98.243 |
| -99 | No respuesta | 1.343 |
| NA | No aplica | 1.256.294 |


### `p7_distrib_agua`: 7. ¿Cuál es el sistema de distribución del agua en esta vivienda?

INTEGER. Universo: Todas las viviendas particulares ocupadas con moradores presentes.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | Con llave dentro de la vivienda | 6.196.815 |
| 2 | Con llave dentro del sitio, pero fuera de la vivienda | 160.098 |
| 3 | No tiene sistema, la acarrea | 49.617 |
| -99 | No respuesta | 1.642 |
| NA | No aplica | 1.256.294 |


### `p8_serv_hig`: 8. El servicio higiénico (WC) principal de esta vivienda es o está:

INTEGER. Universo: Todas las viviendas particulares ocupadas con moradores presentes.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | Dentro de la vivienda, conectado a una red de alcantarillado | 5.344.651 |
| 2 | Fuera de la vivienda, conectado a una red de alcantarillado | 104.723 |
| 3 | Conectado a una fosa séptica | 767.214 |
| 4 | Conectado a pozo negro (letrina sanitaria o cajón) | 164.499 |
| 5 | En un cajón sobre acequia o canal | 3.868 |
| 6 | En un cajón conectado a otro sistema | 2.310 |
| 7 | Baño químico | 2.141 |
| 8 | Conectado a baño seco | 2.443 |
| 9 | No tiene servicio higiénico | 14.794 |
| -99 | No respuesta | 1.529 |
| NA | No aplica | 1.256.294 |


### `p9_fuente_elect`: 9. La electricidad de esta vivienda proviene principalmente de:

INTEGER. Universo: Todas las viviendas particulares ocupadas con moradores presentes.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | Red pública | 6.316.147 |
| 2 | Generador con diésel o bencina | 16.021 |
| 3 | Placa solar | 32.343 |
| 4 | Energía eólica (viento) | 695 |
| 5 | Otro | 16.430 |
| 6 | No tiene energía eléctrica | 24.917 |
| -99 | No respuesta | 1.619 |
| NA | No aplica | 1.256.294 |


### `p10_basura`: 10. ¿Cuál es el principal medio de eliminación de basura de esta vivienda?

INTEGER. Universo: Todas las viviendas particulares ocupadas con moradores presentes.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | La recogen los servicios de aseo | 6.221.171 |
| 2 | La entierra y/o quema | 111.904 |
| 3 | La deja en terreno eriazo, quebrada o zanja | 14.058 |
| 4 | La tira al río, laguna o mar | 1.009 |
| 5 | Otro | 58.798 |
| -99 | No respuesta | 1.232 |
| NA | No aplica | 1.256.294 |


### `p11a_num_personas`: 11. ¿Cuántas personas residen habitualmente en esta vivienda?

INTEGER. Universo: Todas las viviendas particulares ocupadas con moradores presentes.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1:60 |  | 6.408.172 |
| NA |  | 1.256.294 |


### `p11b_comparte_gasto`: 11.1. De las personas que residen habitualmente en esta vivienda, ¿todas comparten los gastos para alimentación?

INTEGER. Universo: Todas las viviendas particulares ocupadas con moradores presentes.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | Sí | 4.965.946 |
| 2 | No | 153.693 |
| NA |  | 2.544.827 |


### `p11c_num_hogar`: 11.2. ¿Cuántos grupos tienen gastos separados de alimentación?

INTEGER. Universo: Todas las viviendas particulares ocupadas con moradores presentes.

| Valor | Etiqueta | Casos |
|---|---|---|
| 2:26 |  | 153.693 |
| NA |  | 7.510.773 |

- `cant_per` (INTEGER): Número de personas censadas en la vivienda. Rango 0:5806; . Universo: Todos los registros.

### `cant_hog`: Número de hogares censados en la vivienda particular

INTEGER. Universo: Todas las viviendas particulares.

| Valor | Etiqueta | Casos |
|---|---|---|
| 0:26 |  | 7.638.396 |
| NA | No aplica | 26.070 |


### `indice_hacinamiento`: Índice de hacinamiento

INTEGER. Universo: Todas las viviendas particulares ocupadas con moradores presentes.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | Vivienda sin hacinamiento | 6.039.952 |
| 2 | Vivienda con hacinamiento medio | 330.955 |
| 3 | Vivienda con hacinamiento crítico | 36.231 |
| -99 | No respuesta | 1.034 |
| NA | No aplica | 1.256.294 |


### `comuna_bajo_umbral`: Comuna con menos de 6.000 personas censadas

INTEGER. Universo: Todos los registros.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | Sí | 99.321 |
| 2 | No | 7.565.145 |


## hogares

`hogares_censo2024.parquet`: 6.622.597 filas, 18 columnas. Llave: `id_vivienda, id_hogar`.

- `id_vivienda` (INTEGER): Llave identificadora de la vivienda o de la entrevista. Rango 1:7664466; Válidos. Universo: Todos los registros.
- `id_hogar` (INTEGER): Llave identificadora de hogar. Rango 0:26; Válidos. Universo: Todos los registros.
- `region` (INTEGER): Región. Rango 1:16; Ver diccionario códigos territoriales. Universo: Todos los registros.
- `provincia` (INTEGER): Provincia. Rango 11:163; Ver diccionario códigos territoriales. Universo: Todos los registros.
- `comuna` (INTEGER): Comuna. Rango 1101:16305; Ver diccionario códigos territoriales. Universo: Todos los registros.

### `area`: Área urbana o rural

INTEGER. Universo: Todos los registros.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | Urbano | 5.733.950 |
| 2 | Rural | 888.647 |


### `tipo_operativo`: Tipo de operativo

INTEGER. Universo: Todos los registros.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | Persona en Situación de Calle | 21.750 |
| 2 | Vivienda Particular | 6.596.527 |
| 3 | Vivienda Colectiva | 4.320 |


### `p12_tenencia_viv`: 12. La vivienda que ocupa este hogar es:

INTEGER. Universo: Todos los hogares.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | Propia pagada | 3.120.238 |
| 2 | Propia pagándose | 910.247 |
| 3 | Arrendada con contrato | 1.229.328 |
| 4 | Arrendada sin contrato | 498.871 |
| 5 | Cedida por trabajo o servicio | 90.697 |
| 6 | Cedida por familiar u otro | 511.118 |
| 7 | Usufructo: solo uso y goce | 61.019 |
| 8 | Ocupada de hecho | 57.788 |
| 9 | Propiedad en sucesión o litigio | 116.125 |
| -99 | No respuesta | 1.096 |
| NA | No aplica | 26.070 |


### `p13_comb_cocina`: 13. ¿Cuál es la principal fuente de energía o combustible que utilizan para cocinar?

INTEGER. Universo: Todos los hogares.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | Gas | 5.780.274 |
| 2 | Parafina o petróleo | 3.832 |
| 3 | Leña | 339.220 |
| 4 | Pellet | 1.960 |
| 5 | Carbón | 1.520 |
| 6 | Electricidad | 439.520 |
| 7 | Energía solar (ej. cocina u horno solar) | 639 |
| 8 | No utiliza fuente de energía o combustible para cocinar | 28.860 |
| -99 | No respuesta | 702 |
| NA | No aplica | 26.070 |


### `p14_comb_calefaccion`: 14. ¿Cuál es la principal fuente de energía o combustible que utilizan para calefaccionar?

INTEGER. Universo: Todos los hogares.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | Gas | 1.688.313 |
| 2 | Parafina o petróleo | 680.755 |
| 3 | Leña | 1.606.997 |
| 4 | Pellet | 137.853 |
| 5 | Carbón | 13.426 |
| 6 | Electricidad | 1.283.687 |
| 7 | Otra | 24.691 |
| 8 | No utiliza fuente de energía o combustible para calefaccionar | 1.159.827 |
| -99 | No respuesta | 978 |
| NA | No aplica | 26.070 |


### `p15a_serv_tel_movil`: 15. Este hogar, ¿dispone de teléfono móvil, celular o smartphone?

INTEGER. Universo: Todos los hogares.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | Sí | 6.475.071 |
| 2 | No | 119.949 |
| -99 | No respuesta | 1.507 |
| NA | No aplica | 26.070 |


### `p15b_serv_compu`: 15. Este hogar, ¿dispone de computador (escritorio o portátil)?

INTEGER. Universo: Todos los hogares.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | Sí | 3.621.619 |
| 2 | No | 2.964.123 |
| -99 | No respuesta | 10.785 |
| NA | No aplica | 26.070 |


### `p15c_serv_tablet`: 15. Este hogar, ¿dispone de tablet?

INTEGER. Universo: Todos los hogares.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | Sí | 1.645.321 |
| 2 | No | 4.939.222 |
| -99 | No respuesta | 11.984 |
| NA | No aplica | 26.070 |


### `p15d_serv_internet_fija`: 15. Este hogar, ¿dispone de internet fija?

INTEGER. Universo: Todos los hogares.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | Sí | 4.250.122 |
| 2 | No | 2.338.834 |
| -99 | No respuesta | 7.571 |
| NA | No aplica | 26.070 |


### `p15e_serv_internet_movil`: 15. Este hogar, ¿dispone de internet móvil desde un celular, tablet o BAM?

INTEGER. Universo: Todos los hogares.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | Sí | 5.734.118 |
| 2 | No | 854.837 |
| -99 | No respuesta | 7.572 |
| NA | No aplica | 26.070 |


### `p15f_serv_internet_satelital`: 15. Este hogar, ¿dispone de internet por conexión satelital?

INTEGER. Universo: Todos los hogares.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | Sí | 288.473 |
| 2 | No | 6.293.135 |
| -99 | No respuesta | 14.919 |
| NA | No aplica | 26.070 |


### `tipologia_hogar`: Tipología de hogar

INTEGER. Universo: Todos los hogares.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | Unipersonal | 1.437.648 |
| 2 | Nuclear monoparental | 985.912 |
| 3 | Nuclear pareja sin hijos | 940.030 |
| 4 | Nuclear pareja con hijos | 1.796.839 |
| 5 | Extenso | 945.125 |
| 6 | Compuesto | 112.706 |
| 7 | Sin núcleo | 378.267 |
| NA | No aplica | 26.070 |


### `comuna_bajo_umbral`: Comuna con menos de 6.000 personas censadas

INTEGER. Universo: Todos los registros.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | Sí | 60.761 |
| 2 | No | 6.561.836 |


## personas

`personas_censo2024.parquet`: 18.480.432 filas, 63 columnas. Llave: `id_vivienda, id_hogar, id_persona`.

- `id_vivienda` (INTEGER): Llave identificadora de la vivienda o de la entrevista. Rango 1:7664466; Válidos. Universo: Todos los registros.
- `id_hogar` (INTEGER): Llave identificadora de hogar. Rango 0:26; Válidos. Universo: Todos los registros.
- `id_persona` (INTEGER): Llave identificadora de persona. Rango 0:5806; Válidos. Universo: Todos los registros.
- `region` (INTEGER): Región. Rango 1:16; Ver diccionario códigos territoriales. Universo: Todos los registros.
- `provincia` (INTEGER): Provincia. Rango 11:163; Ver diccionario códigos territoriales. Universo: Todos los registros.
- `comuna` (INTEGER): Comuna. Rango 1101:16305; Ver diccionario códigos territoriales. Universo: Todos los registros.

### `area`: Área urbana o rural

INTEGER. Universo: Todos los registros.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | Urbano | 16.018.474 |
| 2 | Rural | 2.461.958 |


### `tipo_operativo`: Tipo de operativo

INTEGER. Universo: Todos los registros.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | Persona en situación de calle | 21.750 |
| 2 | Vivienda particular | 18.339.655 |
| 3 | Vivienda colectiva | 119.027 |


### `parentesco`: 19. ¿Qué relación de parentesco tiene con la jefa o jefe de hogar?

INTEGER. Universo: Todas las personas.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | Jefe/a de hogar | 6.596.527 |
| 2 | Esposo/a o cónyuge | 2.090.815 |
| 3 | Conviviente por unión civil | 61.672 |
| 4 | Conviviente de hecho o pareja | 1.226.712 |
| 5 | Hijo/a | 5.861.272 |
| 6 | Hijo/a del cónyuge, conviviente o pareja | 200.617 |
| 7 | Hermano/a | 281.643 |
| 8 | Padre/Madre | 247.279 |
| 9 | Cuñado/a | 59.280 |
| 10 | Suegro/a | 73.702 |
| 11 | Yerno/Nuera | 193.892 |
| 12 | Nieto/a | 853.354 |
| 13 | Abuelo/a | 10.030 |
| 14 | Otro Pariente | 330.270 |
| 15 | No Pariente​ | 236.858 |
| 16 | Servicio doméstico puertas adentro | 15.732 |
| 17 | Persona en vivienda colectiva | 119.027 |
| 19 | Persona en operativo calle | 21.750 |


### `sexo`: 20. ¿Cuál es su sexo?

INTEGER. Universo: Todas las personas.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | Hombre | 8.967.033 |
| 2 | Mujer | 9.513.399 |


### `edad`: 21. ¿Cuántos años cumplidos tiene?

INTEGER. Universo: Todas las personas.

| Valor | Etiqueta | Casos |
|---|---|---|
| 0:85 | Válidos | 18.329.233 |
| -66 | Valor suprimido por anonimización | 151.199 |


### `edad_quinquenal`: Edad en quinquenios

INTEGER. Universo: Todas las personas.

| Valor | Etiqueta | Casos |
|---|---|---|
| 0 | 0-4 | 870.693 |
| 5 | 5-9 | 1.147.515 |
| 10 | 10-14 | 1.256.440 |
| 15 | 15-19 | 1.219.347 |
| 20 | 20-24 | 1.273.193 |
| 25 | 25-29 | 1.383.669 |
| 30 | 30-34 | 1.527.489 |
| 35 | 35-39 | 1.408.198 |
| 40 | 40-44 | 1.270.493 |
| 45 | 45-49 | 1.151.776 |
| 50 | 50-54 | 1.173.352 |
| 55 | 55-59 | 1.133.239 |
| 60 | 60-64 | 1.077.790 |
| 65 | 65-69 | 870.801 |
| 70 | 70-74 | 646.241 |
| 75 | 75-79 | 477.186 |
| 80 | 80-84 | 317.424 |
| 85 | 85 o más | 275.586 |


### `p23_est_civil`: 23. ¿Cuál es su estado conyugal o civil actual?

INTEGER. Universo: Personas de 15 años o más.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | Casado/a | 4.608.520 |
| 2 | Conviviente o pareja sin acuerdo de unión civil | 2.638.561 |
| 3 | Conviviente civil (con acuerdo de unión civil) | 133.624 |
| 4 | Anulado/a | 16.450 |
| 5 | Separado/a | 462.915 |
| 6 | Divorciado/a | 482.427 |
| 7 | Viudo/a | 740.311 |
| 8 | Soltero/a | 6.068.849 |
| -99 | No respuesta | 54.127 |
| NA | No aplica | 3.274.648 |


### `p24_lug_resid5`: 24. ¿En qué comuna o país vivía en abril de 2019?

INTEGER. Universo: Todas las personas.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | Aún no nacía | 870.693 |
| 2 | En esta comuna | 14.426.941 |
| 3 | En otra comuna | 2.442.116 |
| 4 | En otro país | 604.170 |
| -99 | No respuesta | 136.512 |


### `p24_lug_resid5_esp`: Lugar específico de residencia hace 5 años

INTEGER. Universo: Personas de 5 años o más.

| Valor | Etiqueta | Casos |
|---|---|---|
| 2:16305 | Ver diccionario códigos territoriales específicos | 17.466.038 |
| -99 | No respuesta en país de residencia hace 5 años | 141.242 |
| NA | No aplica | 870.693 |
| -66 | Valor suprimido por anonimización | 2.459 |


### `p25_lug_nacimiento`: 25. Cuándo nació, ¿en qué comuna o país vivía su madre?

INTEGER. Universo: Todas las personas.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | En esta comuna | 9.457.200 |
| 2 | En otra comuna | 7.301.521 |
| 3 | En otro país | 1.608.650 |
| -99 | No respuesta | 113.061 |


### `p25_lug_nacimiento_rec`: Nació en Chile

INTEGER. Universo: Todas las personas.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | Sí | 16.758.721 |
| 2 | No | 1.608.650 |
| -99 | No respuesta | 113.061 |


### `p25_lug_nacimiento_esp`: Lugar específico de nacimiento

INTEGER. Universo: Todas las personas.

| Valor | Etiqueta | Casos |
|---|---|---|
| 2:16305 | Ver diccionario códigos territoriales específicos | 18.191.426 |
| -99 | No respuesta | 137.807 |
| -66 | Valor suprimido por anonimización | 151.199 |


### `p26_llegada_periodo`: 26. ¿En qué año llegó a vivir a Chile?

INTEGER. Universo: Personas que nacieron en otro país.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | Entre 2023 y 2024 | 188.790 |
| 2 | Entre 2020 y 2022 | 366.878 |
| 3 | Entre 2017 y 2019 | 533.689 |
| 4 | Entre 2014 y 2016 | 190.158 |
| 5 | Entre 2010 y 2013 | 111.485 |
| 6 | Entre 2000 y 2009 | 121.553 |
| 7 | Entre 1990 y 1999 | 54.026 |
| 8 | Antes de 1990 | 36.811 |
| -99 | No respuesta | 5.260 |
| NA | No aplica | 16.871.782 |


### `p27_nacionalidad`: 27. ¿Cuál es su nacionalidad?

INTEGER. Universo: Todas las personas.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | Chilena​ (exclusivamente) | 16.500.963 |
| 2 | Chilena y otra (doble nacionalidad) | 242.909 |
| 3 | Otra nacionalidad | 1.484.478 |
| -99 | No respuesta | 100.883 |
| -66 | Valor suprimido por anonimización | 151.199 |


### `p27_nacionalidad_esp`: País de nacionalidad

INTEGER. Universo: Todas las personas.

| Valor | Etiqueta | Casos |
|---|---|---|
| 2:862 | Ver diccionario códigos territoriales específicos | 18.226.433 |
| -99 | No respuesta | 102.800 |
| -66 | Valor suprimido por anonimización | 151.199 |


### `p27_nacionalidad_rec`: Nacionalidad chilena

INTEGER. Universo: Todas las personas.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | Sí | 16.889.540 |
| 2 | No | 1.489.385 |
| -99 | No respuesta | 101.507 |


### `p28_autoid_pueblo`: 28. ¿Es o se considera perteneciente a algún pueblo indígena u originario?

INTEGER. Universo: Todas las personas.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | Sí | 2.105.863 |
| 2 | No | 16.267.072 |
| -99 | No respuesta | 107.497 |


### `p28_pueblo_pert`: 28. ¿A cuál?

INTEGER. Universo: Todas las personas que son o se consideran de algún pueblo indígena u originario.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | Mapuche | 1.621.748 |
| 2 | Aymara | 175.353 |
| 3 | Rapa Nui | 4.383 |
| 4 | Atacameño o Lickanantay | 33.686 |
| 5 | Quechua | 43.779 |
| 6 | Colla | 20.075 |
| 7 | Diaguita | 150.692 |
| 8 | Kawésqar | 868 |
| 9 | Yagán | 397 |
| 10 | Chango | 10.244 |
| 11 | Selk’nam | 143 |
| 12 | Otro | 20.630 |
| -99 | No respuesta | 2.395 |
| -66 | Valor suprimido por anonimización | 21.470 |
| NA | No aplica | 16.374.569 |


### `p29_afrodescendencia`: 29. De acuerdo con sus antepasados, tradiciones y cultura, es o se considera:

INTEGER. Universo: Todas las personas.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | Afrodescendiente | 90.254 |
| 2 | Afrochileno/a | 35.711 |
| 3 | Negro/a | 11.771 |
| 4 | Del Pueblo Tribal Afrodescendiente Chileno | 10.066 |
| 5 | Moreno/a de Azapa | 6.162 |
| 6 | Negro/a de la Chimba | 1.463 |
| 7 | Ninguna de las anteriores | 18.195.851 |
| -99 | No respuesta | 110.391 |
| -66 | Valor suprimido por anonimización | 18.763 |


### `p29_afrodescendencia_rec`: Afrodescendencia

INTEGER. Universo: Todas las personas.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | Sí | 174.190 |
| 2 | No | 18.195.851 |
| -99 | No respuesta | 110.391 |


### `p30_lengua_indigena`: 30. ¿Habla o entiende una de las siguientes lenguas indígenas u originarias?

INTEGER. Universo: Personas de 5 años o más.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | Mapuzugún (lengua mapuche) | 380.780 |
| 2 | Aymara | 60.080 |
| 3 | Quechua | 37.837 |
| 4 | Rapa Nui | 6.376 |
| 5 | Ckunza | 2.541 |
| 6 | Kawésqar | 546 |
| 7 | Yagán | 710 |
| 8 | Otra lengua indígena de Chile | 17.604 |
| 9 | No habla ni entiende ninguna lengua indígena de Chile | 16.996.225 |
| -99 | No respuesta | 103.050 |
| -66 | Valor suprimido por anonimización | 3.990 |
| NA | No aplica | 870.693 |


### `p30_lengua_indigena_rec`: Habla o entiende alguna lengua originaria

INTEGER. Universo: Personas de 5 años o más.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | Sí | 510.464 |
| 2 | No | 16.996.225 |
| -99 | No respuesta | 103.050 |
| NA | No aplica | 870.693 |


### `p31_religion`: 31. ¿Cuál es su religión o credo?

INTEGER. Universo: Personas de 15 años o más.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | Católica | 8.168.578 |
| 2 | Evangélica o Protestante | 2.466.199 |
| 5 | Iglesia de Jesucristo de los Santos de los Últimos Días | 91.796 |
| 10 | Testigo de Jehová | 112.688 |
| 12 | Ninguna | 3.903.308 |
| 999 | Otra religión o credo | 363.305 |
| -99 | No respuesta | 87.515 |
| -66 | Valor suprimido por anonimización | 12.395 |
| NA | No aplica | 3.274.648 |


### `p31_religion_rec`: Tiene religión o credo

INTEGER. Universo: Personas de 15 años o más.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | Sí | 11.214.961 |
| 2 | No | 3.903.308 |
| -99 | No respuesta | 87.515 |
| NA | No aplica | 3.274.648 |


### `p32a_dificultad_ver`: 32. ¿Tiene dificultad para ver, aun usando anteojos o lentes?

INTEGER. Universo: Personas de 5 años o más.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | No, sin dificultad | 13.905.057 |
| 2 | Sí, algo de dificultad | 2.758.800 |
| 3 | Sí, mucha dificultad | 795.335 |
| 4 | No puede hacerlo | 51.667 |
| -99 | No respuesta | 98.880 |
| NA | No aplica | 870.693 |


### `p32b_dificultad_oir`: 32. ¿Tiene dificultad para oír, aun usando un dispositivo auditivo

INTEGER. Universo: Personas de 5 años o más.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | No, sin dificultad | 16.144.858 |
| 2 | Sí, algo de dificultad | 964.940 |
| 3 | Sí, mucha dificultad | 357.490 |
| 4 | No puede hacerlo | 41.580 |
| -99 | No respuesta | 100.871 |
| NA | No aplica | 870.693 |


### `p32c_dificultad_mover`: 32. ¿Tiene dificultad para caminar o subir escaleras?

INTEGER. Universo: Personas de 5 años o más.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | No, sin dificultad | 15.289.715 |
| 2 | Sí, algo de dificultad | 1.307.950 |
| 3 | Sí, mucha dificultad | 759.016 |
| 4 | No puede hacerlo | 149.696 |
| -99 | No respuesta | 103.362 |
| NA | No aplica | 870.693 |


### `p32d_dificultad_cogni`: 32. ¿Tiene dificultad para recordar o concentrarse?

INTEGER. Universo: Personas de 5 años o más.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | No, sin dificultad | 15.198.358 |
| 2 | Sí, algo de dificultad | 1.808.201 |
| 3 | Sí, mucha dificultad | 424.594 |
| 4 | No puede hacerlo | 73.643 |
| -99 | No respuesta | 104.943 |
| NA | No aplica | 870.693 |


### `p32e_dificultad_cuidado`: 32. ¿Tiene dificultad para realizar tareas de cuidado personal, como bañarse o vestirse?

INTEGER. Universo: Personas de 5 años o más.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | No, sin dificultad | 16.880.403 |
| 2 | Sí, algo de dificultad | 324.960 |
| 3 | Sí, mucha dificultad | 155.590 |
| 4 | No puede hacerlo | 146.513 |
| -99 | No respuesta | 102.273 |
| NA | No aplica | 870.693 |


### `p32f_dificultad_comunic`: 32. ¿Tiene dificultad para hablar o comunicarse usando su idioma habitual, por ejemplo, entender o ser entendido por otras personas?

INTEGER. Universo: Personas de 5 años o más.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | No, sin dificultad | 17.002.154 |
| 2 | Sí, algo de dificultad | 307.637 |
| 3 | Sí, mucha dificultad | 127.428 |
| 4 | No puede hacerlo | 72.283 |
| -99 | No respuesta | 100.237 |
| NA | No aplica | 870.693 |


### `discapacidad`: Discapacidad

INTEGER. Universo: Personas de 5 años o más.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | Con discapacidad | 1.950.388 |
| 2 | Sin discapacidad | 15.561.356 |
| -99 | No respuesta | 97.995 |
| NA | No aplica | 870.693 |


### `p33_edu_asiste`: 33. ¿Asiste actualmente a la educación formal? Incluye educación parvularia, especial, básica, media y superior

INTEGER. Universo: Todas las personas.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | Sí | 5.106.338 |
| 2 | No | 13.274.483 |
| -99 | No respuesta | 99.611 |


### `asistencia_parv`: Asistencia a nivel de educación parvularia o preescolar

INTEGER. Universo: Personas de 0 a 5 años.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | Sí | 555.041 |
| 2 | No | 506.360 |
| -99 | No respuesta | 9.544 |
| -66 | Valor suprimido por anonimización | 8.430 |
| NA | No aplica | 17.401.057 |


### `asistencia_basica`: Asistencia a nivel de educación básica

INTEGER. Universo: Personas de 6 a 13 años.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | Sí | 1.822.358 |
| 2 | No | 87.531 |
| -99 | No respuesta | 12.922 |
| -66 | Valor suprimido por anonimización | 15.076 |
| NA | No aplica | 16.542.545 |


### `asistencia_media`: Asistencia a nivel de educación media

INTEGER. Universo: Personas de 14 a 17 años.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | Sí | 858.688 |
| 2 | No | 123.361 |
| -99 | No respuesta | 6.645 |
| -66 | Valor suprimido por anonimización | 7.975 |
| NA | No aplica | 17.483.763 |


### `asistencia_superior`: Asistencia a nivel de educación superior

INTEGER. Universo: Personas de 18 a 24 años.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | Sí | 808.427 |
| 2 | No | 921.756 |
| -99 | No respuesta | 12.225 |
| -66 | Valor suprimido por anonimización | 10.849 |
| NA | No aplica | 16.727.175 |


### `p37_alfabet`: 37. ¿Sabe leer y escribir?

INTEGER. Universo: Personas de 5 años o más.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | Sí | 16.769.140 |
| 2 | No | 725.905 |
| -99 | No respuesta | 114.694 |
| NA |  | 870.693 |


### `escolaridad`: Años de escolaridad

INTEGER. Universo: Todas las personas.

| Valor | Etiqueta | Casos |
|---|---|---|
| 0:24 | Válidos | 18.348.374 |
| -99 | No respuesta | 132.058 |


### `cine11`: Logro educativo de acuerdo con la Clasificación Internacional Normalizada de la Educación

INTEGER. Universo: Todas las personas.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | 01: Nunca cursó un programa educativo | 552.698 |
| 2 | 02: Educación de la primera infancia (incluye la forma parcial) | 821.251 |
| 3 | 03: Primaria en forma parcial (sin conclusión del nivel) | 2.122.256 |
| 4 | 10: Educación primaria (nivel 1) | 1.192.382 |
| 5 | 14: Educación primaria (nivel 2), con orientación general | 3.362.035 |
| 6 | 24: Educación secundaria, con orientación general | 4.371.768 |
| 7 | 25: Educación secundaria, con orientación vocacional | 1.568.048 |
| 8 | 35: Educación terciaria de ciclo corto, con orientación vocacional | 1.412.112 |
| 9 | 46: Grado de educación terciaria o nivel equivalente, con orientación no especificada | 2.545.699 |
| 10 | 56: Nivel de maestría, especialización o equivalente, con orientación no especificada | 277.835 |
| 11 | 64: Nivel de doctorado o equivalente, con orientación académica | 31.694 |
| 12 | 98: Educación especial o diferencial | 100.691 |
| -99 | No respuesta | 121.963 |


### `sit_fuerza_trabajo`: Situación en la fuerza de trabajo

INTEGER. Universo: Personas de 15 años o más.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | Ocupado | 8.277.501 |
| 2 | Desocupado | 777.920 |
| 3 | Fuera de la fuerza de trabajo | 6.060.837 |
| -99 | No respuesta | 89.526 |
| NA | No aplica | 3.274.648 |


### `p40_cise_rec`: 40. ¿Trabajó cómo…?

INTEGER. Universo: Personas ocupadas.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | Independiente | 2.794.082 |
| 2 | Dependiente | 5.352.532 |
| 3 | Trabajador/a familiar o personal no remunerado en un negocio de un integrante de su familia | 127.429 |
| -99 | No respuesta | 3.458 |
| NA | No aplica | 10.202.931 |


### `depend_econ_deficit_hab`: Dependencia económica

INTEGER. Universo: Todas las personas.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | Económicamente independiente | 10.417.681 |
| 2 | Económicamente dependiente | 7.970.061 |
| -99 | No respuesta | 92.690 |


### `cod_ciuo`: CIUO-08.CL a 1 dígito

INTEGER. Universo: Personas ocupadas.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | Directores, gerentes y administradores | 383.706 |
| 2 | Profesionales, científicos e intelectuales | 1.490.307 |
| 3 | Técnicos y profesionales de nivel medio | 884.233 |
| 4 | Personal de apoyo administrativo | 518.314 |
| 5 | Trabajadores de los servicios y vendedores de comercios y mercados | 1.622.622 |
| 6 | Agricultores y trabajadores calificados agropecuarios, forestales y pesqueros | 224.291 |
| 7 | Artesanos y operarios de oficios | 1.038.385 |
| 8 | Operadores de instalaciones, máquinas y ensambladores | 662.440 |
| 9 | Ocupaciones elementales | 1.132.704 |
| 0 | Ocupaciones de las fuerza armadas | 24.165 |
| 999 | Respuesta no codificable | 275.787 |
| -99 | No respuesta | 20.547 |
| NA | No aplica | 10.202.931 |


### `cod_caenes`: CAENES a 1 dígito

VARCHAR. Universo: Personas ocupadas.

| Valor | Etiqueta | Casos |
|---|---|---|
| A | Agricultura, ganadería, silvicultura y pesca | 484.597 |
| B | Explotación de minas y canteras | 275.517 |
| C | Industrias manufactureras | 637.429 |
| D | Suministro de electricidad, gas, vapor y aire acondicionado | 85.063 |
| E | Suministro de agua; evacuación de aguas residuales, gestión de desechos y descontaminación | 60.844 |
| F | Construcción | 640.645 |
| G | Comercio al por mayor y al por menor; reparación de vehículos automotores y motocicletas | 1.365.418 |
| H | Transporte y almacenamiento | 558.899 |
| I | Actividades de alojamiento y de servicio de comidas | 390.006 |
| J | Información y comunicaciones | 169.467 |
| K | Actividades financieras y de seguros | 158.834 |
| L | Actividades inmobiliarias | 74.536 |
| M | Actividades profesionales, científicas y técnicas | 315.654 |
| N | Actividades de servicios administrativos y de apoyo | 324.195 |
| O | Administración pública y defensa; planes de seguridad social de afiliación obligatoria | 378.190 |
| P | Enseñanza | 702.416 |
| Q | Actividades de atención de la salud humana y de asistencia social | 671.212 |
| R | Actividades artísticas, de entretenimiento y recreativas | 94.624 |
| S | Otras actividades de servicios | 241.797 |
| T | Actividades de los hogares como empleadores; actividades no diferenciadas de los hogares como productores de bienes y servicios para uso propio | 215.173 |
| U | Actividades de organizaciones y órganos extraterritoriales | 2.917 |
| 999 | Respuesta no codificable | 406.001 |
| -99 | No respuesta | 24.067 |
| NA | No aplica | 10.202.931 |


### `p44_lug_trab`: 44. ¿En qué comuna o país se ubica su trabajo?

INTEGER. Universo: Personas ocupadas.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | En su comuna, en la vivienda donde reside | 1.637.632 |
| 2 | En su comuna, fuera de la vivienda donde reside | 3.311.492 |
| 3 | En otra comuna | 2.856.674 |
| 4 | En otro país | 6.751 |
| 5 | Varias comunas o países | 460.346 |
| -99 | No respuesta | 4.606 |
| NA | No aplica | 10.202.931 |


### `p44_lug_trab_esp`: Lugar de trabajo

INTEGER. Universo: Personas ocupadas.

| Valor | Etiqueta | Casos |
|---|---|---|
| 2:16305 | Ver diccionario códigos territoriales específicos | 8.268.472 |
| -99 | No respuesta | 9.029 |
| NA | No aplica | 10.202.931 |


### `p45_medio_transporte`: 45. ¿Cuál es el medio de transporte principal que utiliza para dirigirse a su lugar de trabajo?

INTEGER. Universo: Personas ocupadas que no trabajan en la vivienda donde residen.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | Auto particular | 2.341.926 |
| 2 | Transporte público (bus, micro, metro, tren, taxi, colectivo) | 2.793.070 |
| 3 | Caminando | 677.171 |
| 4 | Bicicleta (incluye scooter) | 254.215 |
| 5 | Motocicleta | 95.687 |
| 6 | Caballo, lancha o bote | 6.348 |
| 7 | Otro | 465.580 |
| -99 | No respuesta | 1.266 |
| NA | No aplica | 11.845.169 |


### `p46a_tot_hijs_nac`: 46. ¿Cuántas hijas e hijos nacidos vivos ha tenido en total?

INTEGER. Universo: Mujeres de 15 años o más.

| Valor | Etiqueta | Casos |
|---|---|---|
| 0:23 | Válidos | 7.862.575 |
| -99 | No respuesta | 44.706 |
| NA | No aplica | 10.573.151 |


### `p46b_hijas_nac`: 46. Del total de hijas e hijos nacidos vivos, ¿cuántas son mujeres?

INTEGER. Universo: Mujeres de 15 años o más.

| Valor | Etiqueta | Casos |
|---|---|---|
| 0:22 | Válidos | 5.570.891 |
| -99 | No respuesta | 2.085 |
| NA | No aplica | 12.907.456 |


### `p46c_hijos_nac`: 46. Del total de hijas e hijos nacidos vivos, ¿cuántos son hombres?

INTEGER. Universo: Mujeres de 15 años o más.

| Valor | Etiqueta | Casos |
|---|---|---|
| 0:22 | Válidos | 5.570.891 |
| -99 | No respuesta | 2.085 |
| NA | No aplica | 12.907.456 |


### `p47a_tot_hijs_sobrev`: 47. ¿Cuántas hijas e hijos están vivos actualmente?

INTEGER. Universo: Mujeres de 15 años o más que han tenido hijos nacidos vivos.

| Valor | Etiqueta | Casos |
|---|---|---|
| 0:22 | Válidos | 5.569.843 |
| -99 | No respuesta | 3.133 |
| NA | No aplica | 12.907.456 |


### `p47b_hijas_sobrev`: 47. Del total de hijas e hijos que se encuentran vivos, ¿cuántas son mujeres?

INTEGER. Universo: Mujeres de 15 años o más que han tenido hijos nacidos vivos.

| Valor | Etiqueta | Casos |
|---|---|---|
| 0:15 | Válidos | 5.475.748 |
| -99 | No respuesta | 58.447 |
| NA | No aplica | 12.946.237 |


### `p47c_hijos_sobrev`: 47. Del total de hijas e hijos que se encuentran vivos, ¿cuántos son hombres?

INTEGER. Universo: Mujeres de 15 años o más que han tenido hijos nacidos vivos.

| Valor | Etiqueta | Casos |
|---|---|---|
| 0:19 | Válidos | 5.475.748 |
| -99 | No respuesta | 58.447 |
| NA | No aplica | 12.946.237 |


### `p48_anio_nac_uh`: 48. ¿En qué mes y año nació su última hija o hijo nacido vivo? Año

INTEGER. Universo: Mujeres de 15 años o más que han tenido hijos nacidos vivos.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1934:2024 | Válidos | 5.354.481 |
| -99 | No responde | 218.495 |
| NA | No aplica | 12.907.456 |


### `p48_mes_nac_uh`: 48. ¿En qué mes y año nació su última hija o hijo nacido vivo? Mes

INTEGER. Universo: Mujeres de 15 años o más que han tenido hijos nacidos vivos.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | Enero | 459.083 |
| 2 | Febrero | 410.413 |
| 3 | Marzo | 455.275 |
| 4 | Abril | 436.463 |
| 5 | Mayo | 443.334 |
| 6 | Junio | 441.553 |
| 7 | Julio | 431.142 |
| 8 | Agosto | 445.898 |
| 9 | Septiembre | 457.217 |
| 10 | Octubre | 452.482 |
| 11 | Noviembre | 434.750 |
| 12 | Diciembre | 444.343 |
| -99 | No respuesta | 261.023 |
| NA | No aplica | 12.907.456 |


### `div_genero`: Diversidades de género

INTEGER. Universo: Personas de 18 años o más.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | Sí | 64.101 |
| 2 | No | 12.983.214 |
| 3 | No clasificable | 143.512 |
| -66 | Valor suprimido por anonimización | 1.275.674 |
| NA | No aplica | 4.013.931 |


### `comuna_bajo_umbral`: Comuna con menos de 6.000 personas censadas

INTEGER. Universo: Todos los registros.

| Valor | Etiqueta | Casos |
|---|---|---|
| 1 | Sí | 151.199 |
| 2 | No | 18.329.233 |


