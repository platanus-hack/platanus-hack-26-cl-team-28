# GPT Luna con postura explícita para simulación de políticas públicas

## Qué se probó y qué queda disponible

La configuración usa **GPT Luna (`gpt-6-luna`)**, 1.000 medoides de adultos en Chile, sus pesos poblacionales y el perfil **Base histórica + hogar + justicia**. Cada ficha responde cinco preguntas sobre una política. Para comparar apoyo frente a Cadem usamos solo la primera. Las cuatro restantes recogen justicia, confianza, efectividad e influencia.

La PR comparte el ejecutor reproducible, el esquema de respuesta, la preparación del perfil y los paneles con sus preguntas y referencias. Se usa desde el benchmark de backend con acceso a Luna y un catálogo preparado localmente. La selección de motores del servidor web se sigue manejando desde su configuración habitual. [Motores del servidor](../servidor/README.md)

## Perfil de los 1.000 arquetipos

- **Base censal.** Cada ficha representa un grupo de la población adulta. El texto combina tramo de edad, sexo, ubicación y área urbana o rural, educación, situación laboral, ocupación, transporte y tipo de hogar cuando el catálogo tiene esos datos. El peso proviene de la agrupación que produjo el medoide.
- **Finanzas del hogar.** Se añade un donante de la Encuesta de Bienestar Social 2023. Se usan dificultad para llegar a fin de mes, capacidad para cubrir tres meses de gastos básicos tras perder ingresos y deuda no hipotecaria. El conjunto de donantes completos tiene **11.177 registros**. La asociación usa región, tramo de edad, educación, actividad y sexo, y amplía la celda cuando falta respaldo suficiente.
- **Justicia distributiva.** La ficha recibe una de dos prioridades reproducibles por ID. Una prioriza la proporción con lo aportado y la otra reducir diferencias de acceso. Es una imputación experimental. Su prevalencia en Chile quedó abierta.
- **Agregación.** Una ficha aporta su peso íntegro a su categoría. Las tasas se calculan sumando pesos por categoría y dividiendo por la masa total. Las preguntas pesan lo mismo en el error medio. Las dos preguntas de Bicentenario UC se evaluaron con los **665 arquetipos urbanos**, renormalizando sus pesos al universo de la encuesta. [EBS 2023](https://observatorio.ministeriodesarrollosocial.gob.cl/encuesta-bienestar-social-2023) · [Bicentenario UC 2025](https://encuestabicentenario.uc.cl/content/uploads/2025/11/Bicentenario-2025_Resultados.pdf)

## Qué cambia en el prompt

Separamos **tener una postura** de **medir su dirección e intensidad**. Una persona con una inclinación moderada puede tener postura. Si todavía no ha formado una opinión, no sabe qué responder o ninguna posición predomina, se clasifica como indecisa. El prompt deja que la indecisión varíe por política y por perfil.

| Campo de salida | Regla |
|---|---|
| `i` | Índice de la ficha dentro del lote |
| `tiene_postura` | Booleano que se refiere únicamente a la primera pregunta |
| `apoyo` | Si tiene postura, 1–3 para rechazo o 5–7 para aceptación. En caso contrario, `null` |
| `p` | Cuatro notas para las preguntas 2–5, en orden y entre 1 y 7 |

El primer formato guardaba las cinco notas en un arreglo. Algunos lotes devolvían simultáneamente `tiene_postura: true` y un 4. El formato final coloca `apoyo` fuera del arreglo y usa un esquema JSON con una rama por valor del indicador. El parser también verifica índices, longitud, rango de notas y coherencia de los dos campos. En los lotes archivados la indecisión se normaliza a 4 para reutilizar el agregador.

La corrida A/B previa comparó un cuestionario 1–7 con la frase «Una persona que se inclina aunque sea un poco hacia un lado responde 3 o 5, no 4» y el mismo cuestionario sin esa frase. En diez preguntas, retirar la frase bajó el error de **10,42 a 9,81 pp** y subió la indecisión de **12,1% a 14,0%**. Sin contribuciones a la primera vivienda, el cambio en error fue **+0,01 pp**. Eso motivó separar la postura y la intensidad.

## Resultados del panel de diez preguntas Cadem

El error medio en tres categorías es el promedio de las diferencias absolutas en apoyo, rechazo e indecisión, calculado por pregunta. La última columna cuenta si coincide el lado más votado. La tercera categoría de Cadem puede incluir neutralidad y no respuesta. La pregunta directa histórica recogía una decisión de tres opciones. Las comparaciones temáticas usan el instrumento y la muestra de la app.

| Variante | Aceptación | Rechazo | Indecisión | Error medio | Mayoría correcta |
|---|---:|---:|---:|---:|---:|
| Cadem | 57,6% | 36,4% | 6,0% | — | — |
| **Base + hogar + justicia con postura explícita** | **61,0%** | **33,3%** | **5,8%** | **7,68 pp** | **8/10** |
| Base histórica + hogar + justicia, pregunta directa | 53,5% | 46,0% | 0,6% | 7,25 pp | 7/10 |
| Base histórica + hogar + justicia + actitudes | 56,4% | 43,2% | 0,4% | 8,76 pp | 7/10 |
| Base histórica sola | 55,7% | 43,2% | 1,1% | 9,22 pp | 7/10 |
| Escala 1–7 sin frase | 56,5% | 29,5% | 14,0% | 9,81 pp | 8/10 |
| Escala 1–7 con frase | 60,2% | 27,7% | 12,1% | 10,42 pp | 9/10 |
| Temático actual | 49,0% | 40,1% | 10,9% | 12,33 pp | 6/10 |
| Tres temas por arquetipo | 51,0% | 38,3% | 10,7% | 12,67 pp | 5/10 |

La postura explícita quedó en **6,5% de indecisión** en las primeras cinco preguntas y en **5,0%** en las otras cinco. Es la mejor de las variantes con escala 1–7 para el error en las tres categorías. La pregunta directa conserva el menor error total por **0,43 pp**. Jornadas de 40 horas y pensiones concentran el mayor exceso de apoyo de esta variante. [Panel de preguntas](../../datos-pruebas/panel-cadem-perfil-base.json)

## Siete preguntas adicionales

Se ejecutó la misma configuración de Luna con siete preguntas que no habían entrado al panel de diez. En las cinco nuevas de Cadem, el error medio fue **11,03 pp**, la indecisión fue **5,1% frente a 5,4%** y coincidió el lado más votado en **5 de 5 casos**. Dar el mismo peso a cada una de las cuatro fuentes de Cadem de esta tanda arroja **10,56 pp**. Una referencia constante que predice para todos los casos el promedio observado de las diez preguntas iniciales obtiene **12,72 pp**.

Los dos ítems de Bicentenario UC publicaron el porcentaje combinado de acuerdo y muy de acuerdo. En ellos se midió solo el error de apoyo, que promedió **19,51 pp**. Esta ampliación usa referencias ya públicas y comparte una ola Cadem y un proceso constitucional con el panel previo. La prueba prospectiva queda pendiente. [Panel adicional y fuentes](../../datos-pruebas/panel-validacion-postura.json)

## Resultados por pregunta

Las tripletas están en orden **aceptación / rechazo / indecisión**, en porcentajes. En las dos filas UC se indica el apoyo observado y el resto de la estimación de Luna se muestra para inspección. El error de esas filas usa una sola categoría.

| Pregunta | Encuesta | Luna | Error |
|---|---:|---:|---:|
| Regularización por empleo formal | 61,0 / 33,0 / 6,0 | 56,7 / 41,7 / 1,6 | 5,81 pp |
| Convenio de pago del CAE | 79,0 / 16,0 / 5,0 | 82,5 / 12,3 / 5,1 | 2,45 pp |
| Aprobación de la reforma de pensiones | 65,0 / 30,0 / 5,0 | 91,1 / 4,5 / 4,4 | 17,41 pp |
| Eliminar contribuciones a la primera vivienda | 60,0 / 26,0 / 14,0 | 67,9 / 24,5 / 7,7 | 5,24 pp |
| Acortar plazos de permisos ambientales | 54,0 / 35,0 / 11,0 | 40,4 / 46,1 / 13,6 | 9,09 pp |
| Reducir el impuesto a empresas | 38,0 / 56,0 / 6,0 | 33,1 / 60,7 / 6,3 | 3,27 pp |
| Cannabis recreativo desde los 18 años | 47,0 / 52,0 / 1,0 | 51,9 / 44,0 / 4,2 | 5,36 pp |
| Jornada laboral de 40 horas | 71,0 / 23,0 / 6,0 | 96,8 / 1,8 / 1,3 | 17,21 pp |
| Umbral electoral del 5% | 54,0 / 41,0 / 5,0 | 52,1 / 36,3 / 11,5 | 4,37 pp |
| Objeción de conciencia médica | 47,0 / 52,0 / 1,0 | 37,1 / 61,0 / 1,8 | 6,59 pp |
| Registro de Vándalos e Incivilidades | 67,0 / 28,0 / 5,0 | 59,3 / 34,7 / 6,0 | 5,13 pp |
| Toque de queda en la reforma de seguridad | 47,0 / 46,0 / 7,0 | 66,4 / 22,2 / 11,4 | 15,86 pp |
| Acceso igualitario a cargos electivos | 77,0 / 23,0 / 0,0 | 86,5 / 10,5 / 3,1 | 8,35 pp |
| Bloquear apuestas online ilegales | 82,0 / 11,0 / 7,0 | 100,0 / 0,0 / 0,0 | 12,00 pp |
| Permitir auspicio de eventos deportivos por sitios de apuestas | 27,0 / 65,0 / 8,0 | 9,3 / 85,7 / 5,0 | 13,81 pp |
| Prohibir celulares con redes sociales en colegios | 78,0 / — / — | 99,5 / 0,5 / 0,0 | 21,53 pp |
| Prohibir redes sociales a menores de 15 con verificación de edad | 73,0 / — / — | 90,5 / 2,7 / 6,8 | 17,50 pp |

## Tests y verificaciones

| Verificación | Resultado |
|---|---|
| Suite de backend contra la rama actualizada desde `main` | **59 tests aprobados** |
| Contrato de respuesta de postura explícita | Se probaron el indicador verdadero y falso, orden de las fichas, rechazo de notas contradictorias, filas repetidas o incompletas y contenido del prompt |
| Regeneración de Base + hogar + justicia con los insumos originales | El plan regenerado coincidió con el plan que se usó en las corridas |
| Reproducción desde lotes archivados | El resumen de las tandas de **5 + 5 + 7 preguntas** coincidió con los resultados de las corridas. La reproducción usó `--solo-resumen` |
| Prueba de integración con Luna desde la rama de la PR | Un lote nuevo de **25 fichas** para jornada de 40 horas pasó el esquema de salida y el parser |
| Validación de los datos de inferencia | **680 lotes × 25 fichas**. Cada pregunta cubre los 1.000 IDs una sola vez, con los pesos originales |
| Chequeo del diff | `git diff --check` sin incidencias |

## Reproducir el benchmark

Desde la raíz, con Python 3.14 y las dependencias de backend. Ejecutar el modelo requiere Codex CLI con acceso a `gpt-6-luna`. Para el paso de preparación se necesita el catálogo de 1.000 medoides de transporte y el archivo Stata público de EBS 2023. El directorio `CATALOGO` contiene `plan-luna.json`, `diseno.json` y `variables-medoides_transporte.npz`, que genera `benchmark_neyman_catalogos.py preparar` con `--agrupaciones medoides_transporte --arquetipos 1000`.

```bash
export PYTHONPATH=backend:backend/scripts

uv run --project backend python backend/scripts/benchmark_asociaciones.py preparar \
  --origen "$CATALOGO" --ebs "$MICRODATOS_EBS" --salida "$PLANES_LUNA"

uv run --project backend python backend/scripts/benchmark_indecision_luna.py \
  --plan "$PLANES_LUNA/plan-asociado_justicia.json" \
  --panel datos-pruebas/panel-cadem-perfil-base.json \
  --salida "$CORRIDA_CADEM" --postura-explicita --concurrencia 16 \
  --casos c629-regularizacion-empleo c663-cae-convenio c577-congreso \
          c625-contribuciones c638-seia c638-empresas c543-marihuana \
          c483-jornada c505-umbral c594-objecion

uv run --project backend python backend/scripts/benchmark_indecision_luna.py \
  --plan "$PLANES_LUNA/plan-asociado_justicia.json" \
  --panel datos-pruebas/panel-validacion-postura.json \
  --salida "$CORRIDA_ADICIONAL" --postura-explicita --concurrencia 16 \
  --casos c661-registro-incivilidades cseg26-toque c511-paridad \
          c663-apuestas-bloqueo c663-apuestas-eventos \
          uc25-celulares-colegios uc25-verificacion
```

Cada salida incluye `diseno.json`, los lotes reanudables por huella de prompt y `resumen.json`. Repetir el mismo comando reusa los lotes válidos. Agregar `--solo-resumen` recalcula los agregados desde la caché local. Los microdatos y los lotes por ficha quedan en el entorno que ejecuta el benchmark. Para inspeccionar el protocolo ver [ejecutor de Luna](../scripts/benchmark_indecision_luna.py) y [preparación del perfil](../scripts/benchmark_asociaciones.py).

## Decisión y pendientes

Para seguir evaluando respuestas en escala 1–7, usar **Base histórica + hogar + justicia con postura explícita**. En las dos tandas Cadem cumplió la meta de **2–8% de indecisión media**, pero la segunda mostró mayor error y posturas demasiado extremas en algunas políticas. El caso de las apuestas ilegales llegó a **100% de apoyo simulado frente a 82% observado**. Para una comparación centrada solo en error global de las diez preguntas iniciales, la pregunta directa sigue siendo la referencia.

Las primeras 17 preguntas fijaron la configuración de referencia. La ampliación que sigue documenta su desempeño en un panel más amplio.

## Ampliación a 111 preguntas chilenas

Como configuración de referencia para el benchmark con escala 1–7, mantenemos **GPT-6 Luna con Base histórica + hogar + justicia y postura explícita**. En el panel comparativo de diez preguntas dio el menor error de las variantes que conservaron esa escala y estimó 5,8% sin postura frente a 6,0% publicado. La pregunta directa obtuvo el menor error absoluto del panel, 7,25 pp frente a 7,68 pp, con 0,6% de indecisión simulada. La ampliación evalúa una sola configuración.

La corrida del 21 de noviembre de 2026 completó **111 preguntas de 19 levantamientos**, con muestras publicadas de 701 a 7.601 personas. Fueron **4.440 lotes y 111.000 respuestas simuladas**. El error medio en las tres categorías fue **12,19 pp**. Luna coincidió con el lado más votado en **95 de 109** preguntas con una diferencia numérica, frente a **88 de 109** al predecir siempre mayoría a favor. El apoyo medio fue **66,7% frente a 63,0%** y la tercera categoría **5,3% frente a 5,5%**. En las 16 preguntas con la tercera categoría publicada explícitamente, fue **7,1% frente a 12,0%**. Se reprodujeron los porcentajes desde las exportaciones individuales.

Hubo 14 inversiones de mayoría. Diez ocurrieron con una brecha publicada de más de 20 pp. Entre las discrepancias con diferencias de contexto documentadas están la prohibición de la leña, comparada con una encuesta de 2017–2018, y el cierre de fronteras, consultado por Cadem dentro de una batería de seguridad. En la ley miscelánea, el prompt presentó sus objetivos de reconstrucción y reactivación y el estudio documentó un debate más amplio sobre quién se beneficiaría y posibles recortes. La actualidad y el orden de una encuesta pueden influir en la opinión observada. Aún queda medir ese efecto manteniendo fijos el modelo, la muestra y la agregación. En casos con enunciados similares, como aborto por dificultades económicas, la causa de la discrepancia queda abierta. [MMA](https://mma.gob.cl/wp-content/uploads/2018/03/Informe-Final-Encuesta-Nacional-de-Medio-Ambiente-2018.pdf) · [Cadem](https://www.biobiochile.cl/static/documentos/2024/03/encuesta-cadem.pdf) · [Datavoz](https://datavoz.cl/gps-ciudadano-de-datavoz-llego-el-momento-la-primera-cuenta-publica-al-nuevo-gobierno/)

El JSON del benchmark guarda la pregunta, la fuente, la ficha muestral y los resultados por caso. Para la siguiente prueba, comparar el prompt original con una versión que reproduzca el marco del cuestionario y otra que añada noticias contemporáneas verificadas. Usar antecedentes disponibles al momento de la encuesta y mantener los porcentajes publicados fuera del prompt. Para medir generalización antes de calibrar, reservar olas y familias completas y, cuando sea posible, registrar las predicciones antes de publicar los porcentajes de referencia. [Resultados del benchmark](../../datos-pruebas/benchmark-politicas-chile.json) · [Auditoría del contexto](../../datos-pruebas/contexto-benchmark-luna.md)
