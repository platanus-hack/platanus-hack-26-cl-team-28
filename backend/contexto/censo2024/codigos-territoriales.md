# Códigos territoriales del Censo 2024

Generado desde el diccionario de variables del INE. Los mismos datos están en CSV para unirlos en consultas:

- `comunas.csv`: una fila por comuna con sus nombres de provincia y región, población, viviendas y hogares.
- `territorios.csv`: código, nivel (`region`, `provincia`, `comuna`) y nombre.
- `territorios_especificos.csv`: códigos de las variables `*_esp` (comunas y países o continentes).

Los códigos se repiten entre niveles (11 es la región de Aysén y también la provincia de Iquique), así que al unir con `territorios.csv` hay que filtrar por `nivel`.
El código de comuna es RRPCC: `comuna // 1000` da la región y `comuna // 100` la provincia.

## Regiones

| Código | Región |
|---|---|
| 1 | Tarapacá |
| 2 | Antofagasta |
| 3 | Atacama |
| 4 | Coquimbo |
| 5 | Valparaíso |
| 6 | Libertador General Bernardo O'Higgins |
| 7 | Maule |
| 8 | Biobío |
| 9 | La Araucanía |
| 10 | Los Lagos |
| 11 | Aysén del General Carlos Ibáñez del Campo |
| 12 | Magallanes y de la Antártica Chilena |
| 13 | Metropolitana de Santiago |
| 14 | Los Ríos |
| 15 | Arica y Parinacota |
| 16 | Ñuble |

## Comunas

Bajo umbral = comuna con menos de 6.000 personas censadas, donde el INE suprime más detalle (ver `CLAUDE.md`).

| Comuna | Nombre | Provincia | Región | Población | Bajo umbral |
|---|---|---|---|---|---|
| 1101 | Iquique | Iquique | Tarapacá | 199.587 |  |
| 1107 | Alto Hospicio | Iquique | Tarapacá | 142.086 |  |
| 1401 | Pozo Almonte | Del Tamarugal | Tarapacá | 16.878 |  |
| 1402 | Camiña | Del Tamarugal | Tarapacá | 1.335 | sí |
| 1403 | Colchane | Del Tamarugal | Tarapacá | 790 | sí |
| 1404 | Huara | Del Tamarugal | Tarapacá | 2.858 | sí |
| 1405 | Pica | Del Tamarugal | Tarapacá | 6.272 |  |
| 2101 | Antofagasta | Antofagasta | Antofagasta | 401.096 |  |
| 2102 | Mejillones | Antofagasta | Antofagasta | 14.084 |  |
| 2103 | Sierra Gorda | Antofagasta | Antofagasta | 1.472 | sí |
| 2104 | Taltal | Antofagasta | Antofagasta | 12.097 |  |
| 2201 | Calama | El Loa | Antofagasta | 166.334 |  |
| 2202 | Ollagüe | El Loa | Antofagasta | 256 | sí |
| 2203 | San Pedro de Atacama | El Loa | Antofagasta | 9.843 |  |
| 2301 | Tocopilla | Tocopilla | Antofagasta | 25.400 |  |
| 2302 | María Elena | Tocopilla | Antofagasta | 4.834 | sí |
| 3101 | Copiapó | Copiapó | Atacama | 168.831 |  |
| 3102 | Caldera | Copiapó | Atacama | 18.805 |  |
| 3103 | Tierra Amarilla | Copiapó | Atacama | 11.846 |  |
| 3201 | Chañaral | Chañaral | Atacama | 12.345 |  |
| 3202 | Diego de Almagro | Chañaral | Atacama | 11.397 |  |
| 3301 | Vallenar | Huasco | Atacama | 54.222 |  |
| 3302 | Alto del Carmen | Huasco | Atacama | 4.788 | sí |
| 3303 | Freirina | Huasco | Atacama | 7.577 |  |
| 3304 | Huasco | Huasco | Atacama | 9.369 |  |
| 4101 | La Serena | Elqui | Coquimbo | 250.141 |  |
| 4102 | Coquimbo | Elqui | Coquimbo | 263.719 |  |
| 4103 | Andacollo | Elqui | Coquimbo | 11.566 |  |
| 4104 | La Higuera | Elqui | Coquimbo | 4.335 | sí |
| 4105 | Paihuano | Elqui | Coquimbo | 4.649 | sí |
| 4106 | Vicuña | Elqui | Coquimbo | 28.047 |  |
| 4201 | Illapel | Choapa | Coquimbo | 32.009 |  |
| 4202 | Canela | Choapa | Coquimbo | 9.639 |  |
| 4203 | Los Vilos | Choapa | Coquimbo | 22.879 |  |
| 4204 | Salamanca | Choapa | Coquimbo | 27.823 |  |
| 4301 | Ovalle | Limarí | Coquimbo | 118.696 |  |
| 4302 | Combarbalá | Limarí | Coquimbo | 12.954 |  |
| 4303 | Monte Patria | Limarí | Coquimbo | 29.997 |  |
| 4304 | Punitaqui | Limarí | Coquimbo | 12.076 |  |
| 4305 | Río Hurtado | Limarí | Coquimbo | 4.334 | sí |
| 5101 | Valparaíso | Valparaíso | Valparaíso | 284.938 |  |
| 5102 | Casablanca | Valparaíso | Valparaíso | 29.876 |  |
| 5103 | Concón | Valparaíso | Valparaíso | 48.294 |  |
| 5104 | Juan Fernández | Valparaíso | Valparaíso | 904 | sí |
| 5105 | Puchuncaví | Valparaíso | Valparaíso | 22.539 |  |
| 5107 | Quintero | Valparaíso | Valparaíso | 35.754 |  |
| 5109 | Viña del Mar | Valparaíso | Valparaíso | 334.871 |  |
| 5201 | Isla de Pascua | Isla de Pascua | Valparaíso | 4.800 | sí |
| 5301 | Los Andes | Los Andes | Valparaíso | 63.440 |  |
| 5302 | Calle Larga | Los Andes | Valparaíso | 16.597 |  |
| 5303 | Rinconada | Los Andes | Valparaíso | 11.855 |  |
| 5304 | San Esteban | Los Andes | Valparaíso | 20.112 |  |
| 5401 | La Ligua | Petorca | Valparaíso | 39.270 |  |
| 5402 | Cabildo | Petorca | Valparaíso | 20.015 |  |
| 5403 | Papudo | Petorca | Valparaíso | 7.561 |  |
| 5404 | Petorca | Petorca | Valparaíso | 10.206 |  |
| 5405 | Zapallar | Petorca | Valparaíso | 7.980 |  |
| 5501 | Quillota | Quillota | Valparaíso | 96.753 |  |
| 5502 | Calera | Quillota | Valparaíso | 50.631 |  |
| 5503 | Hijuelas | Quillota | Valparaíso | 19.286 |  |
| 5504 | La Cruz | Quillota | Valparaíso | 24.939 |  |
| 5506 | Nogales | Quillota | Valparaíso | 22.136 |  |
| 5601 | San Antonio | San Antonio | Valparaíso | 96.770 |  |
| 5602 | Algarrobo | San Antonio | Valparaíso | 16.076 |  |
| 5603 | Cartagena | San Antonio | Valparaíso | 24.599 |  |
| 5604 | El Quisco | San Antonio | Valparaíso | 18.971 |  |
| 5605 | El Tabo | San Antonio | Valparaíso | 16.260 |  |
| 5606 | Santo Domingo | San Antonio | Valparaíso | 13.171 |  |
| 5701 | San Felipe | San Felipe de Aconcagua | Valparaíso | 80.413 |  |
| 5702 | Catemu | San Felipe de Aconcagua | Valparaíso | 13.760 |  |
| 5703 | Llaillay | San Felipe de Aconcagua | Valparaíso | 25.484 |  |
| 5704 | Panquehue | San Felipe de Aconcagua | Valparaíso | 7.269 |  |
| 5705 | Putaendo | San Felipe de Aconcagua | Valparaíso | 17.336 |  |
| 5706 | Santa María | San Felipe de Aconcagua | Valparaíso | 15.134 |  |
| 5801 | Quilpué | Marga Marga | Valparaíso | 162.559 |  |
| 5802 | Limache | Marga Marga | Valparaíso | 56.145 |  |
| 5803 | Olmué | Marga Marga | Valparaíso | 19.778 |  |
| 5804 | Villa Alemana | Marga Marga | Valparaíso | 139.571 |  |
| 6101 | Rancagua | Cachapoal | Libertador General Bernardo O'Higgins | 257.744 |  |
| 6102 | Codegua | Cachapoal | Libertador General Bernardo O'Higgins | 13.955 |  |
| 6103 | Coinco | Cachapoal | Libertador General Bernardo O'Higgins | 7.916 |  |
| 6104 | Coltauco | Cachapoal | Libertador General Bernardo O'Higgins | 21.373 |  |
| 6105 | Doñihue | Cachapoal | Libertador General Bernardo O'Higgins | 21.925 |  |
| 6106 | Graneros | Cachapoal | Libertador General Bernardo O'Higgins | 35.938 |  |
| 6107 | Las Cabras | Cachapoal | Libertador General Bernardo O'Higgins | 27.554 |  |
| 6108 | Machalí | Cachapoal | Libertador General Bernardo O'Higgins | 60.875 |  |
| 6109 | Malloa | Cachapoal | Libertador General Bernardo O'Higgins | 13.882 |  |
| 6110 | Mostazal | Cachapoal | Libertador General Bernardo O'Higgins | 27.394 |  |
| 6111 | Olivar | Cachapoal | Libertador General Bernardo O'Higgins | 13.901 |  |
| 6112 | Peumo | Cachapoal | Libertador General Bernardo O'Higgins | 14.243 |  |
| 6113 | Pichidegua | Cachapoal | Libertador General Bernardo O'Higgins | 20.363 |  |
| 6114 | Quinta de Tilcoco | Cachapoal | Libertador General Bernardo O'Higgins | 13.558 |  |
| 6115 | Rengo | Cachapoal | Libertador General Bernardo O'Higgins | 63.620 |  |
| 6116 | Requínoa | Cachapoal | Libertador General Bernardo O'Higgins | 29.508 |  |
| 6117 | San Vicente | Cachapoal | Libertador General Bernardo O'Higgins | 49.559 |  |
| 6201 | Pichilemu | Cardenal Caro | Libertador General Bernardo O'Higgins | 19.847 |  |
| 6202 | La Estrella | Cardenal Caro | Libertador General Bernardo O'Higgins | 4.609 | sí |
| 6203 | Litueche | Cardenal Caro | Libertador General Bernardo O'Higgins | 8.852 |  |
| 6204 | Marchihue | Cardenal Caro | Libertador General Bernardo O'Higgins | 8.715 |  |
| 6205 | Navidad | Cardenal Caro | Libertador General Bernardo O'Higgins | 8.885 |  |
| 6206 | Paredones | Cardenal Caro | Libertador General Bernardo O'Higgins | 7.228 |  |
| 6301 | San Fernando | Colchagua | Libertador General Bernardo O'Higgins | 75.585 |  |
| 6302 | Chépica | Colchagua | Libertador General Bernardo O'Higgins | 15.668 |  |
| 6303 | Chimbarongo | Colchagua | Libertador General Bernardo O'Higgins | 37.258 |  |
| 6304 | Lolol | Colchagua | Libertador General Bernardo O'Higgins | 7.791 |  |
| 6305 | Nancagua | Colchagua | Libertador General Bernardo O'Higgins | 18.723 |  |
| 6306 | Palmilla | Colchagua | Libertador General Bernardo O'Higgins | 13.060 |  |
| 6307 | Peralillo | Colchagua | Libertador General Bernardo O'Higgins | 12.493 |  |
| 6308 | Placilla | Colchagua | Libertador General Bernardo O'Higgins | 9.438 |  |
| 6309 | Pumanque | Colchagua | Libertador General Bernardo O'Higgins | 4.559 | sí |
| 6310 | Santa Cruz | Colchagua | Libertador General Bernardo O'Higgins | 41.209 |  |
| 7101 | Talca | Talca | Maule | 232.131 |  |
| 7102 | Constitución | Talca | Maule | 47.004 |  |
| 7103 | Curepto | Talca | Maule | 9.519 |  |
| 7104 | Empedrado | Talca | Maule | 3.990 | sí |
| 7105 | Maule | Talca | Maule | 61.081 |  |
| 7106 | Pelarco | Talca | Maule | 9.229 |  |
| 7107 | Pencahue | Talca | Maule | 9.181 |  |
| 7108 | Río Claro | Talca | Maule | 14.276 |  |
| 7109 | San Clemente | Talca | Maule | 47.380 |  |
| 7110 | San Rafael | Talca | Maule | 11.230 |  |
| 7201 | Cauquenes | Cauquenes | Maule | 42.798 |  |
| 7202 | Chanco | Cauquenes | Maule | 9.446 |  |
| 7203 | Pelluhue | Cauquenes | Maule | 8.578 |  |
| 7301 | Curicó | Curicó | Maule | 159.968 |  |
| 7302 | Hualañé | Curicó | Maule | 10.775 |  |
| 7303 | Licantén | Curicó | Maule | 6.892 |  |
| 7304 | Molina | Curicó | Maule | 48.949 |  |
| 7305 | Rauco | Curicó | Maule | 11.266 |  |
| 7306 | Romeral | Curicó | Maule | 17.233 |  |
| 7307 | Sagrada Familia | Curicó | Maule | 19.427 |  |
| 7308 | Teno | Curicó | Maule | 30.113 |  |
| 7309 | Vichuquén | Curicó | Maule | 4.716 | sí |
| 7401 | Linares | Linares | Maule | 96.744 |  |
| 7402 | Colbún | Linares | Maule | 22.637 |  |
| 7403 | Longaví | Linares | Maule | 33.299 |  |
| 7404 | Parral | Linares | Maule | 45.323 |  |
| 7405 | Retiro | Linares | Maule | 22.310 |  |
| 7406 | San Javier | Linares | Maule | 49.559 |  |
| 7407 | Villa Alegre | Linares | Maule | 17.919 |  |
| 7408 | Yerbas Buenas | Linares | Maule | 20.035 |  |
| 8101 | Concepción | Concepción | Biobío | 230.375 |  |
| 8102 | Coronel | Concepción | Biobío | 123.648 |  |
| 8103 | Chiguayante | Concepción | Biobío | 85.822 |  |
| 8104 | Florida | Concepción | Biobío | 12.958 |  |
| 8105 | Hualqui | Concepción | Biobío | 25.795 |  |
| 8106 | Lota | Concepción | Biobío | 39.980 |  |
| 8107 | Penco | Concepción | Biobío | 48.971 |  |
| 8108 | San Pedro de La paz | Concepción | Biobío | 150.992 |  |
| 8109 | Santa Juana | Concepción | Biobío | 14.947 |  |
| 8110 | Talcahuano | Concepción | Biobío | 147.322 |  |
| 8111 | Tomé | Concepción | Biobío | 56.907 |  |
| 8112 | Hualpén | Concepción | Biobío | 87.731 |  |
| 8201 | Lebu | Arauco | Biobío | 25.246 |  |
| 8202 | Arauco | Arauco | Biobío | 37.163 |  |
| 8203 | Cañete | Arauco | Biobío | 34.640 |  |
| 8204 | Contulmo | Arauco | Biobío | 5.905 | sí |
| 8205 | Curanilahue | Arauco | Biobío | 31.119 |  |
| 8206 | Los Álamos | Arauco | Biobío | 21.950 |  |
| 8207 | Tirúa | Arauco | Biobío | 10.208 |  |
| 8301 | Los Ángeles | Biobío | Biobío | 219.441 |  |
| 8302 | Antuco | Biobío | Biobío | 4.373 | sí |
| 8303 | Cabrero | Biobío | Biobío | 31.256 |  |
| 8304 | Laja | Biobío | Biobío | 23.706 |  |
| 8305 | Mulchén | Biobío | Biobío | 29.036 |  |
| 8306 | Nacimiento | Biobío | Biobío | 26.140 |  |
| 8307 | Negrete | Biobío | Biobío | 10.723 |  |
| 8308 | Quilaco | Biobío | Biobío | 4.440 | sí |
| 8309 | Quilleco | Biobío | Biobío | 9.700 |  |
| 8310 | San Rosendo | Biobío | Biobío | 3.575 | sí |
| 8311 | Santa Bárbara | Biobío | Biobío | 14.075 |  |
| 8312 | Tucapel | Biobío | Biobío | 15.729 |  |
| 8313 | Yumbel | Biobío | Biobío | 23.170 |  |
| 8314 | Alto Biobío | Biobío | Biobío | 6.016 |  |
| 9101 | Temuco | Cautín | La Araucanía | 292.518 |  |
| 9102 | Carahue | Cautín | La Araucanía | 24.957 |  |
| 9103 | Cunco | Cautín | La Araucanía | 19.177 |  |
| 9104 | Curarrehue | Cautín | La Araucanía | 7.733 |  |
| 9105 | Freire | Cautín | La Araucanía | 26.164 |  |
| 9106 | Galvarino | Cautín | La Araucanía | 12.710 |  |
| 9107 | Gorbea | Cautín | La Araucanía | 14.148 |  |
| 9108 | Lautaro | Cautín | La Araucanía | 41.936 |  |
| 9109 | Loncoche | Cautín | La Araucanía | 25.158 |  |
| 9110 | Melipeuco | Cautín | La Araucanía | 6.796 |  |
| 9111 | Nueva Imperial | Cautín | La Araucanía | 33.988 |  |
| 9112 | Padre Las Casas | Cautín | La Araucanía | 80.656 |  |
| 9113 | Perquenco | Cautín | La Araucanía | 7.438 |  |
| 9114 | Pitrufquén | Cautín | La Araucanía | 27.041 |  |
| 9115 | Pucón | Cautín | La Araucanía | 32.321 |  |
| 9116 | Saavedra | Cautín | La Araucanía | 12.877 |  |
| 9117 | Teodoro Schmidt | Cautín | La Araucanía | 15.639 |  |
| 9118 | Toltén | Cautín | La Araucanía | 10.041 |  |
| 9119 | Vilcún | Cautín | La Araucanía | 31.575 |  |
| 9120 | Villarrica | Cautín | La Araucanía | 67.737 |  |
| 9121 | Cholchol | Cautín | La Araucanía | 13.167 |  |
| 9201 | Angol | Malleco | La Araucanía | 53.022 |  |
| 9202 | Collipulli | Malleco | La Araucanía | 24.303 |  |
| 9203 | Curacautín | Malleco | La Araucanía | 18.536 |  |
| 9204 | Ercilla | Malleco | La Araucanía | 7.730 |  |
| 9205 | Lonquimay | Malleco | La Araucanía | 10.247 |  |
| 9206 | Los Sauces | Malleco | La Araucanía | 7.348 |  |
| 9207 | Lumaco | Malleco | La Araucanía | 9.253 |  |
| 9208 | Purén | Malleco | La Araucanía | 12.184 |  |
| 9209 | Renaico | Malleco | La Araucanía | 10.686 |  |
| 9210 | Traiguén | Malleco | La Araucanía | 18.873 |  |
| 9211 | Victoria | Malleco | La Araucanía | 34.464 |  |
| 10101 | Puerto Montt | Llanquihue | Los Lagos | 277.040 |  |
| 10102 | Calbuco | Llanquihue | Los Lagos | 36.474 |  |
| 10103 | Cochamó | Llanquihue | Los Lagos | 4.199 | sí |
| 10104 | Fresia | Llanquihue | Los Lagos | 12.320 |  |
| 10105 | Frutillar | Llanquihue | Los Lagos | 22.554 |  |
| 10106 | Los Muermos | Llanquihue | Los Lagos | 17.162 |  |
| 10107 | Llanquihue | Llanquihue | Los Lagos | 18.088 |  |
| 10108 | Maullín | Llanquihue | Los Lagos | 15.063 |  |
| 10109 | Puerto Varas | Llanquihue | Los Lagos | 52.942 |  |
| 10201 | Castro | Chiloé | Los Lagos | 46.997 |  |
| 10202 | Ancud | Chiloé | Los Lagos | 40.949 |  |
| 10203 | Chonchi | Chiloé | Los Lagos | 16.078 |  |
| 10204 | Curaco de Vélez | Chiloé | Los Lagos | 3.662 | sí |
| 10205 | Dalcahue | Chiloé | Los Lagos | 14.894 |  |
| 10206 | Puqueldón | Chiloé | Los Lagos | 4.048 | sí |
| 10207 | Queilén | Chiloé | Los Lagos | 5.690 | sí |
| 10208 | Quellón | Chiloé | Los Lagos | 28.460 |  |
| 10209 | Quemchi | Chiloé | Los Lagos | 8.409 |  |
| 10210 | Quinchao | Chiloé | Los Lagos | 7.678 |  |
| 10301 | Osorno | Osorno | Los Lagos | 166.455 |  |
| 10302 | Puerto Octay | Osorno | Los Lagos | 8.865 |  |
| 10303 | Purranque | Osorno | Los Lagos | 19.542 |  |
| 10304 | Puyehue | Osorno | Los Lagos | 11.712 |  |
| 10305 | Río Negro | Osorno | Los Lagos | 13.874 |  |
| 10306 | San Juan de la Costa | Osorno | Los Lagos | 7.776 |  |
| 10307 | San Pablo | Osorno | Los Lagos | 10.883 |  |
| 10401 | Chaitén | Palena | Los Lagos | 4.025 | sí |
| 10402 | Futaleufú | Palena | Los Lagos | 3.062 | sí |
| 10403 | Hualaihué | Palena | Los Lagos | 9.480 |  |
| 10404 | Palena | Palena | Los Lagos | 1.903 | sí |
| 11101 | Coyhaique | Coyhaique | Aysén del General Carlos Ibáñez del Campo | 57.823 |  |
| 11102 | Lago Verde | Coyhaique | Aysén del General Carlos Ibáñez del Campo | 779 | sí |
| 11201 | Aysén | Aysén | Aysén del General Carlos Ibáñez del Campo | 23.170 |  |
| 11202 | Cisnes | Aysén | Aysén del General Carlos Ibáñez del Campo | 5.137 | sí |
| 11203 | Guaitecas | Aysén | Aysén del General Carlos Ibáñez del Campo | 1.598 | sí |
| 11301 | Cochrane | Capitán Prat | Aysén del General Carlos Ibáñez del Campo | 3.458 | sí |
| 11302 | O'Higgins | Capitán Prat | Aysén del General Carlos Ibáñez del Campo | 647 | sí |
| 11303 | Tortel | Capitán Prat | Aysén del General Carlos Ibáñez del Campo | 505 | sí |
| 11401 | Chile Chico | General Carrera | Aysén del General Carlos Ibáñez del Campo | 4.905 | sí |
| 11402 | Río Ibáñez | General Carrera | Aysén del General Carlos Ibáñez del Campo | 2.723 | sí |
| 12101 | Punta Arenas | Magallanes | Magallanes y de la Antártica Chilena | 132.363 |  |
| 12102 | Laguna Blanca | Magallanes | Magallanes y de la Antártica Chilena | 269 | sí |
| 12103 | Río Verde | Magallanes | Magallanes y de la Antártica Chilena | 102 | sí |
| 12104 | San Gregorio | Magallanes | Magallanes y de la Antártica Chilena | 241 | sí |
| 12201 | Cabo de Hornos | Antártica Chilena | Magallanes y de la Antártica Chilena | 1.750 | sí |
| 12202 | Antártica | Antártica Chilena | Magallanes y de la Antártica Chilena | 60 | sí |
| 12301 | Porvenir | Tierra del Fuego | Magallanes y de la Antártica Chilena | 6.809 |  |
| 12302 | Primavera | Tierra del Fuego | Magallanes y de la Antártica Chilena | 431 | sí |
| 12303 | Timaukel | Tierra del Fuego | Magallanes y de la Antártica Chilena | 157 | sí |
| 12401 | Natales | Última Esperanza | Magallanes y de la Antártica Chilena | 24.152 |  |
| 12402 | Torres del Paine | Última Esperanza | Magallanes y de la Antártica Chilena | 203 | sí |
| 13101 | Santiago | Santiago | Metropolitana de Santiago | 438.856 |  |
| 13102 | Cerrillos | Santiago | Metropolitana de Santiago | 85.041 |  |
| 13103 | Cerro Navia | Santiago | Metropolitana de Santiago | 127.250 |  |
| 13104 | Conchalí | Santiago | Metropolitana de Santiago | 121.587 |  |
| 13105 | El Bosque | Santiago | Metropolitana de Santiago | 155.257 |  |
| 13106 | Estación Central | Santiago | Metropolitana de Santiago | 181.049 |  |
| 13107 | Huechuraba | Santiago | Metropolitana de Santiago | 101.808 |  |
| 13108 | Independencia | Santiago | Metropolitana de Santiago | 116.943 |  |
| 13109 | La Cisterna | Santiago | Metropolitana de Santiago | 103.157 |  |
| 13110 | La Florida | Santiago | Metropolitana de Santiago | 374.836 |  |
| 13111 | La Granja | Santiago | Metropolitana de Santiago | 112.022 |  |
| 13112 | La Pintana | Santiago | Metropolitana de Santiago | 175.421 |  |
| 13113 | La Reina | Santiago | Metropolitana de Santiago | 89.870 |  |
| 13114 | Las Condes | Santiago | Metropolitana de Santiago | 296.134 |  |
| 13115 | Lo Barnechea | Santiago | Metropolitana de Santiago | 112.620 |  |
| 13116 | Lo Espejo | Santiago | Metropolitana de Santiago | 87.295 |  |
| 13117 | Lo Prado | Santiago | Metropolitana de Santiago | 91.290 |  |
| 13118 | Macul | Santiago | Metropolitana de Santiago | 123.800 |  |
| 13119 | Maipú | Santiago | Metropolitana de Santiago | 503.635 |  |
| 13120 | Ñuñoa | Santiago | Metropolitana de Santiago | 241.467 |  |
| 13121 | Pedro Aguirre Cerda | Santiago | Metropolitana de Santiago | 96.062 |  |
| 13122 | Peñalolén | Santiago | Metropolitana de Santiago | 236.478 |  |
| 13123 | Providencia | Santiago | Metropolitana de Santiago | 143.974 |  |
| 13124 | Pudahuel | Santiago | Metropolitana de Santiago | 227.820 |  |
| 13125 | Quilicura | Santiago | Metropolitana de Santiago | 205.624 |  |
| 13126 | Quinta Normal | Santiago | Metropolitana de Santiago | 129.351 |  |
| 13127 | Recoleta | Santiago | Metropolitana de Santiago | 154.615 |  |
| 13128 | Renca | Santiago | Metropolitana de Santiago | 143.622 |  |
| 13129 | San Joaquín | Santiago | Metropolitana de Santiago | 95.602 |  |
| 13130 | San Miguel | Santiago | Metropolitana de Santiago | 150.829 |  |
| 13131 | San Ramón | Santiago | Metropolitana de Santiago | 76.002 |  |
| 13132 | Vitacura | Santiago | Metropolitana de Santiago | 86.420 |  |
| 13201 | Puente Alto | Cordillera | Metropolitana de Santiago | 568.086 |  |
| 13202 | Pirque | Cordillera | Metropolitana de Santiago | 29.060 |  |
| 13203 | San José de Maipo | Cordillera | Metropolitana de Santiago | 17.441 |  |
| 13301 | Colina | Chacabuco | Metropolitana de Santiago | 173.293 |  |
| 13302 | Lampa | Chacabuco | Metropolitana de Santiago | 145.160 |  |
| 13303 | Tiltil | Chacabuco | Metropolitana de Santiago | 19.742 |  |
| 13401 | San Bernardo | Maipo | Metropolitana de Santiago | 306.371 |  |
| 13402 | Buin | Maipo | Metropolitana de Santiago | 116.969 |  |
| 13403 | Calera de Tango | Maipo | Metropolitana de Santiago | 25.491 |  |
| 13404 | Paine | Maipo | Metropolitana de Santiago | 78.828 |  |
| 13501 | Melipilla | Melipilla | Metropolitana de Santiago | 136.325 |  |
| 13502 | Alhué | Melipilla | Metropolitana de Santiago | 7.768 |  |
| 13503 | Curacaví | Melipilla | Metropolitana de Santiago | 35.165 |  |
| 13504 | María Pinto | Melipilla | Metropolitana de Santiago | 15.352 |  |
| 13505 | San Pedro | Melipilla | Metropolitana de Santiago | 11.108 |  |
| 13601 | Talagante | Talagante | Metropolitana de Santiago | 76.429 |  |
| 13602 | El Monte | Talagante | Metropolitana de Santiago | 37.497 |  |
| 13603 | Isla de Maipo | Talagante | Metropolitana de Santiago | 39.274 |  |
| 13604 | Padre Hurtado | Talagante | Metropolitana de Santiago | 81.243 |  |
| 13605 | Peñaflor | Talagante | Metropolitana de Santiago | 94.402 |  |
| 14101 | Valdivia | Valdivia | Los Ríos | 170.043 |  |
| 14102 | Corral | Valdivia | Los Ríos | 5.501 | sí |
| 14103 | Lanco | Valdivia | Los Ríos | 16.876 |  |
| 14104 | Los Lagos | Valdivia | Los Ríos | 21.431 |  |
| 14105 | Máfil | Valdivia | Los Ríos | 8.074 |  |
| 14106 | Mariquina | Valdivia | Los Ríos | 22.973 |  |
| 14107 | Paillaco | Valdivia | Los Ríos | 19.802 |  |
| 14108 | Panguipulli | Valdivia | Los Ríos | 35.098 |  |
| 14201 | La Unión | Ranco | Los Ríos | 38.907 |  |
| 14202 | Futrono | Ranco | Los Ríos | 15.635 |  |
| 14203 | Lago Ranco | Ranco | Los Ríos | 10.527 |  |
| 14204 | Río Bueno | Ranco | Los Ríos | 33.363 |  |
| 15101 | Arica | Arica | Arica y Parinacota | 241.653 |  |
| 15102 | Camarones | Arica | Arica y Parinacota | 861 | sí |
| 15201 | Putre | Parinacota | Arica y Parinacota | 1.547 | sí |
| 15202 | General Lagos | Parinacota | Arica y Parinacota | 508 | sí |
| 16101 | Chillán | Diguillín | Ñuble | 190.382 |  |
| 16102 | Bulnes | Diguillín | Ñuble | 23.863 |  |
| 16103 | Chillán Viejo | Diguillín | Ñuble | 32.688 |  |
| 16104 | El Carmen | Diguillín | Ñuble | 13.186 |  |
| 16105 | Pemuco | Diguillín | Ñuble | 8.930 |  |
| 16106 | Pinto | Diguillín | Ñuble | 12.502 |  |
| 16107 | Quillón | Diguillín | Ñuble | 19.165 |  |
| 16108 | San Ignacio | Diguillín | Ñuble | 17.405 |  |
| 16109 | Yungay | Diguillín | Ñuble | 18.680 |  |
| 16201 | Quirihue | Itata | Ñuble | 11.746 |  |
| 16202 | Cobquecura | Itata | Ñuble | 5.495 | sí |
| 16203 | Coelemu | Itata | Ñuble | 15.895 |  |
| 16204 | Ninhue | Itata | Ñuble | 5.763 | sí |
| 16205 | Portezuelo | Itata | Ñuble | 5.203 | sí |
| 16206 | Ránquil | Itata | Ñuble | 6.508 |  |
| 16207 | Trehuaco | Itata | Ñuble | 6.124 |  |
| 16301 | San Carlos | Punilla | Ñuble | 55.847 |  |
| 16302 | Coihueco | Punilla | Ñuble | 29.766 |  |
| 16303 | Ñiquén | Punilla | Ñuble | 12.797 |  |
| 16304 | San Fabián | Punilla | Ñuble | 5.245 | sí |
| 16305 | San Nicolás | Punilla | Ñuble | 15.099 |  |

## Códigos específicos que no son comunas

Usados en `p24_lug_resid5_esp`, `p25_lug_nacimiento_esp`, `p27_nacionalidad_esp` y `p44_lug_trab_esp`.

| Código | Territorio |
|---|---|
| 2 | África |
| 5 | Otros países de América del Sur |
| 9 | Oceanía |
| 10 | Antártica (continente) |
| 13 | Otros países de América Central y El Caribe |
| 21 | América del Norte |
| 32 | Argentina |
| 68 | Bolivia (Estado Plurinacional de) |
| 142 | Asia |
| 150 | Europa |
| 152 | Chile |
| 170 | Colombia |
| 332 | Haití |
| 604 | Perú |
| 862 | Venezuela (República Bolivariana de) |
| 998 | Varias comunas o países |
| 1000 | Tarapacá |
| 2000 | Antofagasta |
| 3000 | Atacama |
| 4000 | Coquimbo |
| 5000 | Valparaíso |
| 6000 | Libertador General Bernardo O'Higgins |
| 7000 | Maule |
| 8000 | Biobío |
| 9000 | La Araucanía |
| 10000 | Los Lagos |
| 11000 | Aysén del General Carlos Ibáñez del Campo |
| 12000 | Magallanes y de la Antártica Chilena |
| 13000 | Metropolitana de Santiago |
| 14000 | Los Ríos |
| 15000 | Arica y Parinacota |
| 16000 | Ñuble |

