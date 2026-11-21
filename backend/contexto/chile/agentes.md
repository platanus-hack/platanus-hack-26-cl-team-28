# Tabla de agentes

`data/agentes/` tiene 1.546.322 agentes que representan a las 15.463.163 personas de 14 años o más de `data/chile/`: 1 de cada 10. Es la tabla que usa el motor del sitio para filtrar y sacar la muestra, y por eso se versiona (103 MB, un archivo por región). La escribe `scripts/reducir_poblacion.py`.

Cada fila es una persona real del censo, con todas sus columnas (las mismas de `data/chile/chile.parquet`), más a cuántas personas representa en cada nivel de reducción. Los niveles son anidados: quien representa a 1.000 es uno de los que representan a 100.

| Nivel | Columna | Agentes | Cómo se usa |
|---|---|---|---|
| 1 agente por cada 10 personas | `representa` | 1.546.322 | Todas las filas. |
| 1 agente por cada 100 personas | `representa_100` | 154.639 | Las filas donde `representa_100` no es nula. |
| 1 agente por cada 1.000 personas | `representa_1000` | 15.474 | Las filas donde `representa_1000` no es nula. |

Para una cifra de la población, cada fila se pondera por la columna de su nivel. En el sitio, el nivel se elige en el cajón de filtros («Clusterización»).

## Cómo se elige a cada agente

Hoy es provisorio: dentro de cada región las personas se ordenan por comuna, zona, sexo y tramo de edad, se agrupan de a 10, y de cada grupo se elige una al azar; el nivel siguiente hace lo mismo con los elegidos. El destino es que cada agente sea el arquetipo de un grupo de personas parecidas obtenido por clusterización; cuando ese proceso exista reemplaza a `grupos()` en el script, y las columnas pasan a traer el tamaño de cada cluster. El motor ya sortea la muestra en proporción a esas columnas, así que no hay que tocarlo.

## Comparación con la población completa

La suma de `representa` es exactamente la población en cada región. Por comuna, la mayor diferencia es de 11 personas (0,1 % en las comunas de 5.000 personas o más); 0 comunas quedaron sin ningún agente.

Diferencia máxima, en puntos porcentuales, entre la población completa y los agentes de cada nivel, ponderados:

| Dato | Categorías | 1 por cada 10 | 1 por cada 100 | 1 por cada 1.000 |
|---|---|---|---|---|
| Sexo | 2 | 0,00 | 0,01 | 0,01 |
| Edad en tramos de cinco años | 16 | 0,00 | 0,08 | 0,93 |
| Zona urbana o rural | 2 | 0,00 | 0,01 | 0,16 |
| Nivel educativo | 12 | 0,05 | 0,14 | 0,48 |
| Situación en la fuerza de trabajo | 3 | 0,00 | 0,15 | 0,25 |
| Decil de ingreso del hogar | 10 | 0,03 | 0,19 | 0,27 |
| Previsión de salud | 6 | 0,04 | 0,12 | 0,12 |
| Tipo de colegio de los menores | 5 | 0,11 | 0,40 | 0,61 |
| Posición política | 12 | 0,04 | 0,15 | 0,37 |
| Evaluación del gobierno | 5 | 0,01 | 0,23 | 0,60 |
| Confianza en el gobierno | 6 | 0,03 | 0,10 | 0,59 |

Lo que entra en el orden de los grupos (comuna, zona, sexo, edad) calza casi exacto; lo demás difiere por el azar de elegir a uno por grupo, que crece al reducir más: con menos agentes hay menos casos de cada tipo.

Fuentes: INE, Censo de Población y Vivienda 2024; Ministerio de Desarrollo Social y Familia, Encuesta Casen 2024; Centro de Estudios Públicos, Encuesta CEP N° 96.
