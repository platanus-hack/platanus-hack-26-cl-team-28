# Muestra del 1 % de la población de Chile

`data/muestra/personas.parquet` tiene 184.879 personas y `data/muestra/hogares.parquet` tiene 65.965 hogares. Son registros reales y anonimizados del Censo 2024, sorteados para representar al país, a los que se agregaron datos imputados desde la Encuesta Casen 2024.

**Cada fila representa a 100 personas.** No hay ponderadores: un porcentaje calculado en la muestra estima el del país.

**Los datos imputados no son de esa persona.** Son un valor plausible, sorteado entre personas u hogares de Casen parecidos. Sirven para estudiar distribuciones y relaciones, no para afirmar nada de un registro en particular. `validacion.md` muestra cuánto se parecen a la fuente.

## Cómo se construyó

1. **Sorteo.** Se ordenaron los hogares del censo por región, comuna, área y tamaño, y se tomó 1 de cada 100. Así cada comuna y cada tamaño de hogar pesan lo que deben. Los hogares entran completos, con todos sus integrantes. Aparte se tomó 1 de cada 100 personas en viviendas colectivas y en situación de calle (1.408 personas).
2. **Edad.** En las 51 comunas donde el censo solo publica el tramo quinquenal, la edad exacta se sorteó según la distribución de su región, sexo y tramo.
3. **Familia.** Hijos, hermanos y educación de los padres se dedujeron del parentesco dentro del hogar. Solo existen para quienes viven juntos.
4. **Hogares.** Con Casen se ajustó un modelo del ingreso per cápita según región, área, tamaño, características de la jefatura, ocupados, educación, tenencia, tipo de vivienda, hacinamiento, internet y el nivel de su comuna (la escolaridad media de sus adultos en el censo, en tramos de medio año). El emparejamiento va en dos etapas. Primero, el orden: cada hogar recibe un ingreso tentativo de un hogar de Casen de su misma comuna y composición por edad (con menores de 18, con mayores de 65, con ambos o con ninguno), el que ocupa su misma posición relativa según el ingreso predicho; si Casen tiene menos de 10 hogares así en la comuna, se busca en su región. Después, la calibración: dentro de cada combinación de región, área, tamaño y composición por edad, los hogares se ordenan por ese ingreso tentativo, los de Casen por su ingreso real, y cada hogar recibe el donante que ocupa su misma posición relativa (con un margen aleatorio de 7 vecinos). Así cada comuna conserva la distribución de ingresos que Casen observa en ella, y cada región queda igual a Casen aunque Casen no sea representativa por comuna. Con un solo emparejamiento, por el ingreso predicho, las diferencias entre comunas de una misma región se aplastaban: Vitacura quedaba con 54 % de quintil V y Cerro Navia con 5 %, cuando Casen da 88 % y 3 %. Se empareja por posición y no por valor porque el censo registra algo menos de empleo y educación que Casen. De ese donante se copian ingresos, vehículos, redes de apoyo, inseguridad alimentaria y discriminación.
5. **Personas.** A cada persona se le sorteó un donante de Casen del mismo sexo, edad, educación, actividad y discapacidad, y en lo posible del mismo decil, región, ocupación y parentesco. El decil es el que se imputó a su hogar en el paso anterior, y los integrantes de un hogar se emparejan además por el sistema de salud de su jefatura. De ese donante se copian previsión, datos del trabajo, participación y cuidados.
6. **Sorteos aparte.** El tiempo de traslado, el género, los hijos de quienes el censo no pregunta y el tipo de colegio de los menores tienen cada uno su propio emparejamiento, con las llaves que más les importan.

La semilla del sorteo está fija (`SEMILLA = 2024`), así que volver a ejecutar el script produce la misma muestra.

## Columnas

Las columnas del censo conservan su nombre y sus códigos; están descritas en `contexto/censo2024/diccionario.md`. `hogares` trae además las columnas de la vivienda. Las etiquetas de las columnas imputadas están en `etiquetas_casen.csv`.

Identificadores: `id_persona_muestra`, `id_hogar_muestra` (une ambas tablas; es nulo para personas fuera de hogares) y las llaves originales del censo.

**Tabla única.** `data/muestra/muestra.parquet` y `data/muestra/muestra.csv` tienen todo junto: una fila por persona, con las columnas de su hogar y su vivienda repetidas en cada integrante. Para contar hogares o viviendas en esa tabla hay que quedarse con una fila por `id_hogar_muestra` (por ejemplo `parentesco = 1`), o usar `hogares.parquet`. Las personas fuera de hogares tienen vacías las columnas del hogar. `casen_folio_donante_hogar` es el donante del hogar y `casen_folio_donante` el de la persona.

### Edad y familia (en `personas`)

| Columna | Origen | Contenido |
|---|---|---|
| `edad` | Censo; imputada donde `edad_imputada = 1` | Edad en años, tope 85. En 1.531 personas de comunas pequeñas se sorteó dentro de su tramo quinquenal. |
| `hijos_total` | Censo o Casen, según `hijos_origen` | Hijos nacidos vivos. Observado para mujeres de 15+ (78.602 casos); imputado para hombres y para mujeres sin respuesta (80.055). |
| `hijos_en_hogar` | Derivado del hogar censal | Hijos que viven en el hogar. Solo para la jefatura y su pareja. |
| `hermanos_en_hogar` | Derivado del hogar censal | Hermanos que viven en el hogar. Solo para hijos de la jefatura, la jefatura y sus hermanos. |
| `esc_padre`, `esc_madre` | Derivado del hogar censal | Años de escolaridad del padre y la madre, solo si viven en el mismo hogar (33 % de las personas tiene dato de la madre). |
| `cine11_padre`, `cine11_madre` | Derivado del hogar censal | Nivel educativo del padre y la madre (códigos de `cine11`). |
| `vive_con_padre`, `vive_con_madre` | Derivado del hogar censal | 1 si el padre o la madre vive en el hogar. En ese caso su tramo socioeconómico es el decil del hogar. |

### Imputadas desde Casen por persona (en `personas`)

| Columna | Contenido |
|---|---|
| `decil_ingreso`, `quintil_ingreso` | Decil y quintil de ingreso autónomo per cápita del hogar (copiado de `hogares`). |
| `prevision_salud` | Sistema de salud: -88 No sabe; 1 Sistema Público FONASA; 2 Isapre; 3 FF.AA. y del Orden; 4 Ninguno (particular); 5 Otro sistema. |
| `fonasa_grupo` | Grupo de Fonasa: -88 No sabe grupo; 1 Grupo A; 2 Grupo B; 3 Grupo C; 4 Grupo D. |
| `categoria_ocupacional` | Solo ocupados: 1 Patrón(a) o empleador(a); 2 Trabajador(a) por cuenta propia; 3 Empleado(a) u obrero(a) del sector público (Gobierno Central o Municipal); 4 Empleado(a) u obrero(a) de empresas públicas; 5 Empleado(a) u obrero(a) del sector privado; 6 Servicio doméstico puertas adentro; 7 Servicio doméstico puertas afuera; 8 FF.AA. y del Orden; 9 Familiar no remunerado. |
| `tiene_contrato` | Solo ocupados asalariados: 1 sí, 0 no. |
| `cotiza_pension` | 15 años o más: cotizó el mes pasado en un sistema de pensiones (1 sí, 0 no). |
| `sindicato` | Solo ocupados: pertenece a un sindicato (1 sí, 2 no). |
| `participa_organizacion` | Organización en que participó en los últimos 12 meses: 1 Juntas de vecinos u otra organización territorial (comité de aguas, comité de allegados, otros); 2 Club deportivo o recreativo; 3 Organización religiosa o de iglesia; 4 Agrupaciones culturales, artísticas o patrimoniales; 5 Grupos de identidad cultural (asociaciones indígenas, círculos de inmigrantes, otros); 6 Agrupaciones juveniles o de estudiantes (scout, centros de alumnos, otros); 7 Agrupaciones de mujeres; 8 Agrupaciones de adulto mayor (club de adulto mayor, asistentes de centros de día, otros); 9 Grupos de voluntariado; 10 Grupos de autoayuda en salud; 11 Agrupación ideológica (partido político); 12 Agrupación corporativa (sindicato, asociación gremial, colegio profesional, otros); 13 Centro de padres y apoderados; 14 Otra; 15 No participa en ninguna organización o grupo. |
| `dependencia_grado` | 15 años o más: 0 no dependiente, 1 severa, 2 moderada, 3 leve. |
| `es_cuidador` | 1 si cuida a un integrante del hogar con dependencia. |
| `tiempo_traslado_min` | Minutos de viaje al trabajo, para ocupados que se trasladan. Se emparejó por el medio de transporte declarado en el censo (`p45_medio_transporte`). |
| `dependencia_colegio` | Tipo de colegio de quienes tienen entre 6 y 17 años y asisten a clases: 1 municipal, 2 particular subvencionado, 3 particular pagado, 4 corporación de administración delegada, 5 servicio local de educación. Se emparejó por el decil del hogar, la región, la zona y la etapa (6 a 13 o 14 a 17 años). |
| `genero` | 18 años o más: -99 Prefiere no responder; -88 No sabe; 1 Masculino; 2 Femenino; 3 Transmasculino; 4 Transfemenino; 5 No binario; 6 Otro género. Especifique. |
| `nivel_match_persona` | Qué tan fino fue el emparejamiento (1 el mejor, 11 el peor). Ver `validacion.md`. |
| `casen_folio_donante`, `casen_id_persona_donante` | Identifican a la persona de Casen de la que se copiaron los datos. |

### Imputadas desde Casen por hogar (en `hogares`)

| Columna | Contenido |
|---|---|
| `decil_ingreso`, `quintil_ingreso` | Decil y quintil nacional de ingreso autónomo per cápita. Es el tramo socioeconómico. |
| `ingreso_autonomo_pc`, `ingreso_total_pc` | Ingreso mensual per cápita del hogar, en pesos de noviembre de 2024. El total por hogar es este valor por `n_personas`. |
| `pobreza_ingresos` | 1 Pobreza extrema; 2 Pobreza no extrema; 3 Fuera de la pobreza. |
| `tiene_vehiculo`, `n_vehiculos` | El hogar tiene vehículo de uso particular o laboral (1 sí, 2 no) y cuántos. |
| `red_*` (9 columnas) | El hogar conoce a alguien que pueda ayudar con: cuidado en enfermedad, cuidado de dependientes, vehículo, dinero, trámites, tecnología, reparaciones, conseguir trabajo, consejo. -88 No sabe; 1 Sí, alguien fuera del hogar; 2 Sí, alguien dentro del hogar; 3 Ambas; 4 No conoce. |
| `inseg_alim_*` (8 columnas) e `inseg_alim_n` | Experiencias de inseguridad alimentaria en los últimos 12 meses (1 sí, 2 no) y cuántas de las ocho ocurrieron. |
| `discrim_*` (21 columnas) | Alguien del hogar fue discriminado en los últimos 12 meses por ese motivo (1 sí, 0 no). `discrim_ninguna = 1` si no hubo. |
| `nivel_match_hogar` | Clase en la que se encontró al hogar donante (1 la más específica). |
| `casen_folio_donante` | Hogar de Casen del que se copiaron los datos. |

## Límites

- **Personas fuera de hogares.** Las 1.408 personas en viviendas colectivas o en situación de calle no tienen datos de Casen, porque esa encuesta solo cubre viviendas particulares.
- **No respuesta del censo.** Los `-99` y `-66` del censo se conservan tal cual, salvo la edad.
- **Comunas.** Casen no es representativa por comuna. El ingreso de cada comuna sigue la distribución que Casen observa en ella (ver el paso 4), así que hereda su ruido: en las comunas con pocos casos en Casen es una estimación débil, y en las que no alcanzan 10 hogares por composición se usa la de su región. Los demás datos imputados son fiables por región y por grupos sociales, no para comparar comunas entre sí.
- **Relaciones no medidas.** Una relación entre dos datos imputados por separado (por ejemplo, tiempo de traslado y participación en organizaciones) solo refleja lo que ambos comparten con la edad, la educación, el ingreso y las demás llaves.
- **Familia fuera del hogar.** No hay hermanos ni educación de los padres para quienes no viven con ellos. Casen 2024 tampoco lo pregunta.
- **Discriminación.** Los motivos se copian del hogar donante, que coincide en si la jefatura es inmigrante o indígena, pero no en todo lo demás.
- **Fechas.** El censo se levantó entre marzo y julio de 2024 y Casen entre noviembre de 2024 y febrero de 2025.
- **No incluye** tendencia política ni valores, que ninguna de las dos fuentes mide.

## Uso

```sh
uv run python -I scripts/consulta.py "select decil_ingreso, round(100 * avg((prevision_salud = 2)::int), 1) as pct_isapre from muestra_personas group by 1 order by 1"
```

Las vistas `muestra` (tabla única), `muestra_personas` y `muestra_hogares` están disponibles en `scripts/consulta.py`. Para reconstruir:

```sh
uv run python -I scripts/descargar_casen.py data/casen2024
uv run python -I scripts/construir_muestra.py data/censo2024 data/casen2024 data/muestra contexto/muestra
```

Fuentes: INE, Censo de Población y Vivienda 2024; Ministerio de Desarrollo Social y Familia, Encuesta Casen 2024.

