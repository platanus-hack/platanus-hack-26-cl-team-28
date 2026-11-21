# Tabla de agentes

`data/agentes/` tiene 1.546.322 agentes que representan a las 15.463.163 personas de 14 años o más de `data/chile/`: 1 de cada 10. Es la tabla que usa el motor del sitio para filtrar y sacar la muestra, y por eso se versiona (103 MB, un archivo por región). La escribe `scripts/reducir_poblacion.py`; este informe también, no lo edites a mano.

Cada fila es una persona real del censo, con todas sus columnas (las mismas de `data/chile/chile.parquet`), más su tipo político (`tipo_politico`) y a cuántas personas representa en cada nivel de reducción. Los niveles son anidados: quien representa a 1.000 es uno de los que representan a 100.

| Nivel | Columna | Agentes | Cómo se usa |
|---|---|---|---|
| 1 agente por cada 10 personas | `representa` | 1.546.322 | Todas las filas. |
| 1 agente por cada 100 personas | `representa_100` | 154.639 | Las filas donde `representa_100` no es nula. |
| 1 agente por cada 1.000 personas | `representa_1000` | 15.474 | Las filas donde `representa_1000` no es nula. |
| 1 agente por cada 10.000 personas | `representa_10000` | 1.558 | Las filas donde `representa_10000` no es nula. |

Para una cifra de la población, cada fila se pondera por la columna de su nivel. En el sitio, el nivel se elige en el cajón de filtros («Clusterización»).

## Cómo se agrupa

Lo que más pesa en una opinión es la política; la demografía pesa poco (`contexto/delphos/influencia.md`). La reducción agrupa primero por eso:

1. **Tipos políticos.** Todas las opiniones de una persona vienen de un mismo entrevistado de la Encuesta CEP, y hay 1.466. Se agrupan en 8 tipos según su voto, su evaluación de los dos gobiernos, su posición política, su confianza en el gobierno, su opinión sobre reducir el gasto público y su partido, cada dato con el peso que tiene para predecir las demás opiniones. Cada persona hereda el tipo de su entrevistado. Los menores de 18 años no tienen opiniones y quedan sin tipo.
2. **Grupos de 10.** En cada nivel, los integrantes se ordenan y se cortan de a 10; el nivel siguiente agrupa a los representantes del anterior. El orden cambia con el nivel (el eje político es el lugar del entrevistado entre un extremo político y el otro):

   | Nivel | Orden |
   |---|---|
   | 1 por cada 10 | región, comuna, zona, tipo político, sexo, tramo de edad, eje político, situación laboral |
   | 1 por cada 100 | región, comuna, zona, tipo político, sexo, tramo de edad, eje político, situación laboral |
   | 1 por cada 1.000 | región, zona, tipo político, sexo, tramo de edad, eje político, situación laboral, comuna |
   | 1 por cada 10.000 | región, tipo político, tramo de edad, sexo, eje político, zona, situación laboral |

   Mientras hay gente suficiente, cada grupo es de una sola comuna y de un solo tipo político. En los niveles más reducidos no alcanza para ambas cosas y se prefiere el tipo político.
3. **Representante por equilibrio.** Los grupos se recorren llevando la cuenta de qué categorías van quedando con menos peso del que les corresponde en la región, y de cada grupo se toma al integrante que mejor lo compensa. Se equilibran: tipo político, voto en 2025, evaluación del gobierno, posición política, confianza en el gobierno, sexo, tramo de edad, situación laboral, educación, niños en el hogar, quintil de ingreso, zona, comuna, edad en tramos de cinco años, tipo de colegio de los menores, sexo con tramo de edad, tipo político con tramo de edad. No se usa el integrante más típico del grupo (el medoide), porque elige siempre a la mayoría y hace desaparecer a las minorías.

## Los tipos políticos

Numerados a lo largo del eje que más separa a los entrevistados. Porcentajes sobre las personas de 18 años o más de cada tipo.

| Tipo | % de los adultos | Votó por Jara | Votó por Kast | Aprueba al gobierno | Aprueba al gobierno anterior | Posición media (1 izquierda, 10 derecha) | Sin posición | Confía en el gobierno |
|---|---|---|---|---|---|---|---|---|
| 1 | 18,5 | 2 | 90 | 89 | 9 | 7,8 | 13 | 96 |
| 2 | 10,3 | 0 | 91 | 84 | 12 | 5,0 | 0 | 60 |
| 3 | 8,2 | 1 | 94 | 60 | 8 | 7,6 | 15 | 0 |
| 4 | 11,0 | 13 | 17 | 18 | 8 | 5,4 | 48 | 7 |
| 5 | 10,7 | 15 | 22 | 8 | 15 | 5,0 | 0 | 4 |
| 6 | 13,1 | 12 | 15 | 8 | 13 | 4,9 | 44 | 12 |
| 7 | 12,2 | 85 | 3 | 1 | 91 | 4,1 | 7 | 0 |
| 8 | 15,9 | 86 | 1 | 1 | 91 | 3,3 | 5 | 9 |

## Cuánto se parece cada persona a quien la representa

Porcentaje de las personas que coinciden con su representante en cada dato.

| Dato | 1 por cada 10 | 1 por cada 100 | 1 por cada 1.000 | 1 por cada 10.000 |
|---|---|---|---|---|
| Tipo político | 99,9 | 98,9 | 98,6 | 96,9 |
| Evaluación del gobierno | 97,2 | 89,0 | 86,3 | 80,0 |
| Voto en 2025 | 95,8 | 84,5 | 80,6 | 72,0 |
| Situación laboral | 87,1 | 69,8 | 66,3 | 59,9 |
| Tramo de edad | 99,2 | 93,2 | 91,4 | 85,5 |
| Sexo | 99,8 | 97,9 | 97,3 | 83,9 |
| Comuna | 100,0 | 99,9 | 27,7 | 13,5 |

## Comparación con la población completa

La suma de cada columna es exactamente la población en cada región. Diferencia máxima, en puntos porcentuales, entre la población completa y los agentes de cada nivel, ponderados. «Se equilibra» dice si el dato entra en la elección del representante.

| Dato | Se equilibra | Categorías | 1 por cada 10 | 1 por cada 100 | 1 por cada 1.000 | 1 por cada 10.000 |
|---|---|---|---|---|---|---|
| Sexo | sí | 2 | 0,00 | 0,00 | 0,00 | 0,06 |
| Edad en tramos de cinco años | sí | 16 | 0,00 | 0,00 | 0,03 | 0,35 |
| Zona urbana o rural | sí | 2 | 0,00 | 0,00 | 0,01 | 0,17 |
| Situación en la fuerza de trabajo | sí | 3 | 0,00 | 0,00 | 0,01 | 0,26 |
| Tipo político | sí | 8 | 0,00 | 0,01 | 0,03 | 0,27 |
| Voto en la segunda vuelta de 2025 | sí | 6 | 0,00 | 0,00 | 0,04 | 0,31 |
| Posición política | sí | 12 | 0,01 | 0,05 | 0,19 | 0,39 |
| Evaluación del gobierno | sí | 5 | 0,00 | 0,01 | 0,03 | 0,29 |
| Confianza en el gobierno | sí | 6 | 0,00 | 0,01 | 0,02 | 0,33 |
| Nivel educativo | no | 12 | 0,03 | 0,11 | 0,27 | 0,58 |
| Decil de ingreso del hogar | no | 10 | 0,04 | 0,20 | 0,42 | 0,53 |
| Previsión de salud | no | 6 | 0,02 | 0,04 | 0,07 | 0,63 |
| Tipo de colegio de los menores | sí | 5 | 0,00 | 0,03 | 0,29 | 2,39 |
| Apertura a la inmigración | no | 12 | 0,02 | 0,08 | 0,26 | 0,67 |
| Justifica las marchas | no | 7 | 0,01 | 0,08 | 0,17 | 1,98 |
| Confianza en Carabineros | no | 6 | 0,03 | 0,11 | 0,17 | 1,05 |

Por comuna y por subgrupo. El desvío en subgrupos es la diferencia media de una opinión (`aprueba_gobierno`, `voto_segunda_vuelta_2025`, `apertura_inmigracion`, `justifica_marchas`, `confianza_carabineros`) dentro de cada subgrupo que se puede filtrar en el sitio (región, sexo y edad, quintil de ingreso, educación, posición política).

| Medida | 1 por cada 10 | 1 por cada 100 | 1 por cada 1.000 | 1 por cada 10.000 |
|---|---|---|---|---|
| Comunas sin ningún agente | 0 | 0 | 11 | 68 |
| Error medio de la población por comuna (comunas de 5.000 personas o más), % | 0,0 | 0,2 | 2,7 | 28,0 |
| Desvío medio de una opinión dentro de un subgrupo, puntos | 0,06 | 0,34 | 1,13 | 4,43 |
| Subgrupos sin ningún agente | 0 | 0 | 0 | 0 |

Lo que se equilibra calza casi exacto mientras hay agentes suficientes; lo demás difiere por lo que no explica el grupo, y más cuanto más se reduce: con menos agentes hay menos casos de cada tipo. Lo que aplica a pocas personas, como el tipo de colegio de los menores, es lo que más se desvía en los niveles más reducidos. Con 1 agente por cada 10.000 personas no hay agentes para todas las comunas: en ese nivel el mapa vale por región, y un filtro deja pocos agentes.

Fuentes: INE, Censo de Población y Vivienda 2024; Ministerio de Desarrollo Social y Familia, Encuesta Casen 2024; Centro de Estudios Públicos, Encuesta CEP N° 96.
