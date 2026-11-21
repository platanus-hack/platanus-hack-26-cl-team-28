# Validación de la muestra del 1 %

Generado por `scripts/construir_muestra.py`. Todas las cifras se recalculan en cada ejecución.

## A. La muestra frente al censo completo

La muestra tiene 184.879 personas (1,000 % de 18.480.432) y 65.965 hogares (1,000 % de 6.596.527).
Para cada variable se compara la distribución porcentual en la muestra y en el censo, y se informa la mayor diferencia entre categorías, en puntos porcentuales.

| Variable | Categorías | Diferencia máxima (pp) |
|---|---|---|
| `personas.sexo` | 2 | 0,06 |
| `personas.region` | 16 | 0,03 |
| `personas.area` | 2 | 0,01 |
| `personas.edad_quinquenal` | 18 | 0,17 |
| `personas.cine11` | 13 | 0,28 |
| `personas.sit_fuerza_trabajo` | 5 | 0,08 |
| `personas.p23_est_civil` | 10 | 0,15 |
| `personas.p28_autoid_pueblo` | 3 | 0,13 |
| `personas.p25_lug_nacimiento` | 4 | 0,14 |
| `personas.p31_religion_rec` | 4 | 0,10 |
| `personas.tipo_operativo` | 3 | 0,00 |
| `hogares.region` | 16 | 0,00 |
| `hogares.tipologia_hogar` | 7 | 0,12 |
| `hogares.p12_tenencia_viv` | 10 | 0,14 |
| `hogares.p15d_serv_internet_fija` | 3 | 0,10 |

Por comuna, la muestra se aleja del 1 % exacto en 3,0 personas en promedio y en 15 como máximo. Comunas sin ninguna persona en la muestra: 1, de las más pequeñas del país.

## B. Los datos imputados frente a Casen

Las columnas comparan la distribución en la muestra con la de Casen 2024 ponderada. No tienen que coincidir exactamente: la imputación respeta la relación entre cada dato y las características de la persona o del hogar, y la población del censo no es idéntica a la que Casen expande (Casen se calibra a proyecciones de población y solo cubre viviendas particulares).

| Dato | Categoría | Muestra % | Casen % |
|---|---|---|---|
| Decil de ingreso (hogares) | I | 10,2 | 10,0 |
| Decil de ingreso (hogares) | II | 10,5 | 10,0 |
| Decil de ingreso (hogares) | III | 10,1 | 10,0 |
| Decil de ingreso (hogares) | IV | 9,9 | 10,0 |
| Decil de ingreso (hogares) | V | 10,1 | 10,0 |
| Decil de ingreso (hogares) | VI | 10,0 | 10,0 |
| Decil de ingreso (hogares) | VII | 10,3 | 10,2 |
| Decil de ingreso (hogares) | VIII | 9,5 | 9,8 |
| Decil de ingreso (hogares) | IX | 9,7 | 10,0 |
| Decil de ingreso (hogares) | X | 9,6 | 10,0 |
| Previsión de salud (personas) | Sistema Público FONASA | 84,1 | 82,6 |
| Previsión de salud (personas) | Isapre | 11,5 | 13,2 |
| Previsión de salud (personas) | FF.AA. y del Orden | 1,7 | 1,8 |
| Previsión de salud (personas) | Ninguno (particular) | 2,2 | 2,0 |
| Previsión de salud (personas) | Otro sistema | 0,2 | 0,2 |
| Grupo de Fonasa | Grupo A | 26,5 | 24,9 |
| Grupo de Fonasa | Grupo B | 42,7 | 42,8 |
| Grupo de Fonasa | Grupo C | 13,8 | 14,7 |
| Grupo de Fonasa | Grupo D | 13,4 | 14,0 |
| Hogar con vehículo | Sí | 52,4 | 53,8 |
| Hogar con vehículo | No | 47,6 | 46,2 |
| Pobreza por ingresos (personas) | Pobreza extrema | 7,0 | 6,9 |
| Pobreza por ingresos (personas) | Pobreza no extrema | 11,1 | 10,4 |
| Pobreza por ingresos (personas) | Fuera de la pobreza | 81,8 | 82,7 |
| Categoría ocupacional (ocupados) | Patrón(a) o empleador(a) | 5,0 | 3,2 |
| Categoría ocupacional (ocupados) | Trabajador(a) por cuenta propia | 28,9 | 19,9 |
| Categoría ocupacional (ocupados) | Empleado(a) u obrero(a) del sector público (G | 9,6 | 10,8 |
| Categoría ocupacional (ocupados) | Empleado(a) u obrero(a) de empresas públicas | 2,6 | 3,1 |
| Categoría ocupacional (ocupados) | Empleado(a) u obrero(a) del sector privado | 49,7 | 59,4 |
| Categoría ocupacional (ocupados) | Servicio doméstico puertas adentro | 0,1 | 0,1 |
| Categoría ocupacional (ocupados) | Servicio doméstico puertas afuera | 2,1 | 2,3 |
| Categoría ocupacional (ocupados) | FF.AA. y del Orden | 0,7 | 0,9 |
| Categoría ocupacional (ocupados) | Familiar no remunerado | 1,4 | 0,4 |
| Cotiza para pensión (15+) | No | 58,5 | 53,6 |
| Cotiza para pensión (15+) | Sí | 41,1 | 46,0 |
| Participa en organizaciones | Juntas de vecinos u otra organización territo | 6,1 | 5,7 |
| Participa en organizaciones | Club deportivo o recreativo | 6,5 | 6,4 |
| Participa en organizaciones | Organización religiosa o de iglesia | 7,0 | 6,7 |
| Participa en organizaciones | No participa en ninguna organización o grupo | 72,0 | 72,8 |
| Género (18+) | Masculino | 46,8 | 48,4 |
| Género (18+) | Femenino | 51,7 | 50,9 |
| Género (18+) | Transmasculino | 0,0 | 0,1 |
| Género (18+) | Transfemenino | 0,1 | 0,1 |
| Género (18+) | No binario | 0,1 | 0,2 |
| Género (18+) | Otro género. Especifique | 0,0 | 0,0 |
| Preocupación por falta de alimentos (hogares) | Sí | 29,2 | 29,2 |

| Promedio o mediana | Muestra | Casen |
|---|---|---|
| Hijos por hombre de 15+ (imputado) | 1,47 | 1,44 |
| Hijos por mujer de 15+ (censo vs. Casen) | 1,76 | 1,80 |
| Minutos de traslado al trabajo | 40,98 | 39,16 |
| Ingreso autónomo per cápita del hogar, mediana de hogares ($) | 355.875 | 365.000 |

### Coherencia entre datos imputados

Porcentaje de personas en Isapre según decil de ingreso del hogar. Ambos datos vienen de donantes distintos, así que esta tabla muestra si el encadenamiento conservó la relación:

| Decil | Muestra % | Casen % |
|---|---|---|
| 1 | 1,6 | 1,7 |
| 2 | 1,1 | 1,1 |
| 3 | 2,0 | 2,2 |
| 4 | 2,8 | 2,8 |
| 5 | 3,7 | 4,4 |
| 6 | 7,3 | 7,6 |
| 7 | 11,0 | 12,2 |
| 8 | 17,7 | 20,1 |
| 9 | 33,6 | 38,1 |
| 10 | 62,4 | 69,4 |

Hogares cuyos integrantes tienen sistemas de salud distintos: 12,4 % en la muestra y 13,4 % en Casen.

## C. Calidad del emparejamiento

El modelo que predice el ingreso per cápita del hogar explica el 34 % de la varianza del logaritmo del ingreso en Casen (R² ponderado).

Hogares según la clase dentro de la cual se buscó al donante (`nivel_match_hogar`):

| Nivel | Clase | Hogares | % |
|---|---|---|---|
| 1 | región, área, tamaño, composición por edad, origen de la jefatura | 64.076 | 97,1 |
| 2 | macrozona, área, tamaño, composición por edad, origen de la jefatura | 1.094 | 1,7 |
| 3 | área, tamaño, composición por edad, jefatura inmigrante | 691 | 1,0 |
| 4 | tamaño y composición por edad | 98 | 0,1 |
| 5 | tamaño | 6 | 0,0 |

Personas según el nivel de coincidencia con su donante (`nivel_match_persona`). Del 1 al 5 coinciden sexo, edad quinquenal, educación, actividad y discapacidad; del 6 en adelante la coincidencia es más gruesa:

| Nivel | Llaves | Personas | % |
|---|---|---|---|
| 1 | + decil, región, área, ocupación, parentesco, inmigrante | 60.658 | 33,1 |
| 2 | + decil, región, ocupación | 38.522 | 21,0 |
| 3 | + decil, macrozona | 51.632 | 28,1 |
| 4 | + decil | 20.925 | 11,4 |
| 5 | + quintil | 4.347 | 2,4 |
| 6 | sexo, edad decenal, educación en 3 tramos, actividad, discapacidad, decil | 2.539 | 1,4 |
| 7 | sexo, edad decenal, educación en 3 tramos, actividad, quintil | 2.532 | 1,4 |
| 8 | sexo, edad decenal, actividad | 1.455 | 0,8 |
| 9 | sexo, edad decenal, actividad (sin sistema de la jefatura) | 108 | 0,1 |
| 10 | sexo, grupo amplio de edad | 753 | 0,4 |
| 11 | cualquiera | 0 | 0,0 |

