# Resumen del Censo 2024 de Chile

Cifras calculadas por `scripts/construir_contexto.py` desde los microdatos, con las definiciones del manual del INE.
Al generarlas se comprobó que población por sexo y región, grupos de edad, operativos, viviendas, hogares y tenencia coinciden con los tabulados oficiales.
Los porcentajes excluyen la no respuesta (`-99`) del denominador, como hace el INE.

## País

| Indicador | Valor |
|---|---|
| Población censada | 18.480.432 |
| Hombres | 8.967.033 (48,5 %) |
| Mujeres | 9.513.399 (51,5 %) |
| Hombres por cada 100 mujeres | 94,3 |
| Población urbana | 16.018.474 (86,7 %) |
| Población rural | 2.461.958 (13,3 %) |
| 0 a 14 años | 3.274.648 (17,7 %) |
| 15 a 64 años | 12.618.546 (68,3 %) |
| 65 años o más | 2.587.238 (14,0 %) |
| Índice de envejecimiento (65+ por cada 100 de 0 a 14) | 79,0 |
| Relación de dependencia total | 46,5 |
| Mediana de edad (sin las 51 comunas con edad suprimida) | 36 |
| Personas en viviendas particulares | 18.339.655 |
| Personas en viviendas colectivas | 119.027 |
| Personas en situación de calle | 21.750 |
| Viviendas censadas | 7.642.716 (7.638.396 particulares y 4.320 colectivas) |
| Hogares censados | 6.596.527 |
| Personas por hogar | 2,8 |
| Hogares unipersonales | 21,8 % |
| Hogares con jefatura mujer | 49,9 % |
| Hogares con acceso a internet | 93,2 % |
| Hogares en vivienda propia (pagada o pagándose) | 61,1 % |
| Población nacida fuera de Chile | 1.608.650 (8,8 %) |
| Se considera perteneciente a un pueblo indígena u originario | 2.105.863 (11,5 %) |
| Se considera afrodescendiente | 174.190 (0,9 %) |
| Años de escolaridad promedio, toda la población con dato | 10,4 |
| Años de escolaridad promedio, 18 años o más | 12,1 |
| Alfabetización, 15 años o más | 97,8 % |
| Personas de 5 años o más con discapacidad | 1.950.388 (11,1 %) |

## Regiones

El orden es por código; la numeración no sigue la geografía (15 es Arica y Parinacota, 13 la Metropolitana, 16 Ñuble).

| Cód. | Región | Población | % país | % urbana | Índice envej. | % nacida fuera | Viviendas | Hogares |
|---|---|---|---|---|---|---|---|---|
| 1 | Tarapacá | 369.806 | 2,0 | 95,8 | 43,9 | 23,2 | 143.253 | 121.511 |
| 2 | Antofagasta | 635.416 | 3,4 | 97,6 | 49,3 | 19,7 | 231.829 | 213.747 |
| 3 | Atacama | 299.180 | 1,6 | 89,4 | 63,7 | 8,5 | 139.531 | 103.057 |
| 4 | Coquimbo | 832.864 | 4,5 | 80,2 | 77,6 | 5,4 | 372.785 | 292.567 |
| 5 | Valparaíso | 1.896.053 | 10,3 | 89,5 | 98,6 | 5,3 | 914.075 | 701.072 |
| 6 | Libertador General Bernardo O'Higgins | 987.228 | 5,3 | 73,1 | 83,1 | 5,0 | 407.970 | 350.372 |
| 7 | Maule | 1.123.008 | 6,1 | 71,4 | 83,9 | 3,8 | 486.650 | 406.964 |
| 8 | Biobío | 1.613.059 | 8,7 | 86,6 | 84,1 | 2,9 | 660.778 | 579.170 |
| 9 | La Araucanía | 1.010.423 | 5,5 | 67,2 | 83,0 | 2,1 | 481.228 | 373.360 |
| 10 | Los Lagos | 890.284 | 4,8 | 71,0 | 75,8 | 4,0 | 404.142 | 332.395 |
| 11 | Aysén del General Carlos Ibáñez del Campo | 100.745 | 0,5 | 77,0 | 66,2 | 3,9 | 52.294 | 39.964 |
| 12 | Magallanes y de la Antártica Chilena | 166.537 | 0,9 | 92,9 | 87,1 | 6,6 | 76.607 | 63.062 |
| 13 | Metropolitana de Santiago | 7.400.741 | 40,0 | 96,2 | 76,2 | 13,1 | 2.764.749 | 2.599.621 |
| 14 | Los Ríos | 398.230 | 2,2 | 67,5 | 89,2 | 1,9 | 183.479 | 148.643 |
| 15 | Arica y Parinacota | 244.569 | 1,3 | 90,4 | 65,0 | 14,9 | 88.501 | 80.620 |
| 16 | Ñuble | 512.289 | 2,8 | 66,0 | 97,6 | 2,1 | 234.845 | 190.402 |

## Distribuciones nacionales

### Estado civil o conyugal

`personas.p23_est_civil`. Fuera del porcentaje: no responde 54.127, no aplica 3.274.648.

| Valor | Categoría | Casos | % |
|---|---|---|---|
| 1 | Casado/a | 4.608.520 | 30,4 |
| 2 | Conviviente o pareja sin acuerdo de unión civil | 2.638.561 | 17,4 |
| 3 | Conviviente civil (con acuerdo de unión civil) | 133.624 | 0,9 |
| 4 | Anulado/a | 16.450 | 0,1 |
| 5 | Separado/a | 462.915 | 3,1 |
| 6 | Divorciado/a | 482.427 | 3,2 |
| 7 | Viudo/a | 740.311 | 4,9 |
| 8 | Soltero/a | 6.068.849 | 40,1 |

### Nivel educativo alcanzado (CINE 2011)

`personas.cine11`. Fuera del porcentaje: no responde 121.963.

| Valor | Categoría | Casos | % |
|---|---|---|---|
| 1 | 01: Nunca cursó un programa educativo | 552.698 | 3,0 |
| 2 | 02: Educación de la primera infancia (incluye la forma parcial) | 821.251 | 4,5 |
| 3 | 03: Primaria en forma parcial (sin conclusión del nivel) | 2.122.256 | 11,6 |
| 4 | 10: Educación primaria (nivel 1) | 1.192.382 | 6,5 |
| 5 | 14: Educación primaria (nivel 2), con orientación general | 3.362.035 | 18,3 |
| 6 | 24: Educación secundaria, con orientación general | 4.371.768 | 23,8 |
| 7 | 25: Educación secundaria, con orientación vocacional | 1.568.048 | 8,5 |
| 8 | 35: Educación terciaria de ciclo corto, con orientación vocacional | 1.412.112 | 7,7 |
| 9 | 46: Grado de educación terciaria o nivel equivalente, con orientación no especificada | 2.545.699 | 13,9 |
| 10 | 56: Nivel de maestría, especialización o equivalente, con orientación no especificada | 277.835 | 1,5 |
| 11 | 64: Nivel de doctorado o equivalente, con orientación académica | 31.694 | 0,2 |
| 12 | 98: Educación especial o diferencial | 100.691 | 0,5 |

### Situación en la fuerza de trabajo (15 años o más)

`personas.sit_fuerza_trabajo`. Fuera del porcentaje: no responde 89.526, no aplica 3.274.648.

| Valor | Categoría | Casos | % |
|---|---|---|---|
| 1 | Ocupado | 8.277.501 | 54,8 |
| 2 | Desocupado | 777.920 | 5,1 |
| 3 | Fuera de la fuerza de trabajo | 6.060.837 | 40,1 |

### Situación en el empleo (personas ocupadas)

`personas.p40_cise_rec`. Fuera del porcentaje: no responde 3.458, no aplica 10.202.931.

| Valor | Categoría | Casos | % |
|---|---|---|---|
| 1 | Independiente | 2.794.082 | 33,8 |
| 2 | Dependiente | 5.352.532 | 64,7 |
| 3 | Trabajador/a familiar o personal no remunerado en un negocio de un integrante de su familia | 127.429 | 1,5 |

### Medio de transporte al trabajo

`personas.p45_medio_transporte`. Fuera del porcentaje: no responde 1.266, no aplica 11.845.169.

| Valor | Categoría | Casos | % |
|---|---|---|---|
| 1 | Auto particular | 2.341.926 | 35,3 |
| 2 | Transporte público (bus, micro, metro, tren, taxi, colectivo) | 2.793.070 | 42,1 |
| 3 | Caminando | 677.171 | 10,2 |
| 4 | Bicicleta (incluye scooter) | 254.215 | 3,8 |
| 5 | Motocicleta | 95.687 | 1,4 |
| 6 | Caballo, lancha o bote | 6.348 | 0,1 |
| 7 | Otro | 465.580 | 7,0 |

### Religión o credo

`personas.p31_religion_rec`. Fuera del porcentaje: no responde 87.515, no aplica 3.274.648.

| Valor | Categoría | Casos | % |
|---|---|---|---|
| 1 | Sí | 11.214.961 | 74,2 |
| 2 | No | 3.903.308 | 25,8 |

### Pueblo indígena u originario al que pertenece

`personas.p28_pueblo_pert`. Fuera del porcentaje: no responde 2.395, suprimido 21.470, no aplica 16.374.569.

| Valor | Categoría | Casos | % |
|---|---|---|---|
| 1 | Mapuche | 1.621.748 | 77,9 |
| 2 | Aymara | 175.353 | 8,4 |
| 3 | Rapa Nui | 4.383 | 0,2 |
| 4 | Atacameño o Lickanantay | 33.686 | 1,6 |
| 5 | Quechua | 43.779 | 2,1 |
| 6 | Colla | 20.075 | 1,0 |
| 7 | Diaguita | 150.692 | 7,2 |
| 8 | Kawésqar | 868 | 0,0 |
| 9 | Yagán | 397 | 0,0 |
| 10 | Chango | 10.244 | 0,5 |
| 11 | Selk’nam | 143 | 0,0 |
| 12 | Otro | 20.630 | 1,0 |

### Tipología de hogar

`hogares.tipologia_hogar`, filtro `tipo_operativo = 2`.

| Valor | Categoría | Casos | % |
|---|---|---|---|
| 1 | Unipersonal | 1.437.648 | 21,8 |
| 2 | Nuclear monoparental | 985.912 | 14,9 |
| 3 | Nuclear pareja sin hijos | 940.030 | 14,3 |
| 4 | Nuclear pareja con hijos | 1.796.839 | 27,2 |
| 5 | Extenso | 945.125 | 14,3 |
| 6 | Compuesto | 112.706 | 1,7 |
| 7 | Sin núcleo | 378.267 | 5,7 |

### Tenencia de la vivienda

`hogares.p12_tenencia_viv`, filtro `tipo_operativo = 2`. Fuera del porcentaje: no responde 1.096.

| Valor | Categoría | Casos | % |
|---|---|---|---|
| 1 | Propia pagada | 3.120.238 | 47,3 |
| 2 | Propia pagándose | 910.247 | 13,8 |
| 3 | Arrendada con contrato | 1.229.328 | 18,6 |
| 4 | Arrendada sin contrato | 498.871 | 7,6 |
| 5 | Cedida por trabajo o servicio | 90.697 | 1,4 |
| 6 | Cedida por familiar u otro | 511.118 | 7,7 |
| 7 | Usufructo: solo uso y goce | 61.019 | 0,9 |
| 8 | Ocupada de hecho | 57.788 | 0,9 |
| 9 | Propiedad en sucesión o litigio | 116.125 | 1,8 |

### Tipo de vivienda particular

`viviendas.p2_tipo_vivienda`, filtro `tipo_operativo = 2`.

| Valor | Categoría | Casos | % |
|---|---|---|---|
| 1 | Casa | 5.937.284 | 77,7 |
| 3 | Departamento | 1.579.970 | 20,7 |
| 5 | Vivienda tradicional indígena (ruka u otras) | 1.967 | 0,0 |
| 6 | Pieza en casa antigua o en conventillo | 51.305 | 0,7 |
| 7 | Mediagua, mejora, vivienda de emergencia, rancho o choza | 27.490 | 0,4 |
| 8 | Móvil (carpa, casa rodante o similar) | 1.557 | 0,0 |
| 9 | Otro tipo de vivienda particular | 38.823 | 0,5 |

### Estado de ocupación de las viviendas particulares

`viviendas.p3b_estado_ocupacion`, filtro `tipo_operativo = 2`.

| Valor | Categoría | Casos | % |
|---|---|---|---|
| 1 | Moradores presentes | 6.408.172 | 83,9 |
| 2 | Moradores ausentes | 208.084 | 2,7 |
| 6 | Otras razones de no entrevista | 114.207 | 1,5 |
| 7 | En venta o arriendo | 173.315 | 2,3 |
| 8 | Vivienda de temporada (veraneo o de uso temporal) | 476.135 | 6,2 |
| 9 | Abandonada | 97.052 | 1,3 |
| 10 | Otra razón de desocupación | 161.431 | 2,1 |

### Índice de hacinamiento

`viviendas.indice_hacinamiento`, filtro `tipo_operativo = 2`. Fuera del porcentaje: no responde 1.034, no aplica 1.230.224.

| Valor | Categoría | Casos | % |
|---|---|---|---|
| 1 | Vivienda sin hacinamiento | 6.039.952 | 94,3 |
| 2 | Vivienda con hacinamiento medio | 330.955 | 5,2 |
| 3 | Vivienda con hacinamiento crítico | 36.231 | 0,6 |

