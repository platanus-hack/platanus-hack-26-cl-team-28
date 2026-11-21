# Documentación del Censo 2024 en texto

Cada PDF de `data/censo2024/docs/` se convirtió a texto con `pdftotext -layout`. Los archivos largos conviene buscarlos con grep en vez de leerlos enteros.
Las tablas y fórmulas pierden formato en la conversión; ante la duda, abrir el PDF original.

| Archivo | Páginas | Caracteres | Contenido |
|---|---|---|---|
| `docs/261026_doc_conmutacion_laboral_cpv.txt` | 134 | 365 k | Documento de conmutación laboral (versión previa, 6 de noviembre de 2026). |
| `docs/Conmutacion_Laboral_cpv2024.txt` | 140 | 379 k | Documento de conmutación laboral (versión del 10 de noviembre de 2026). |
| `docs/Cuestionario-Viviendas-Colectivas-y-Personas-en-Situacion-de-Calle_CPV2024.txt` | 4 | 46 k | Cuestionario de viviendas colectivas y personas en situación de calle. |
| `docs/Cuestionario-Viviendas-Particulares_CPV2024.txt` | 8 | 98 k | Cuestionario de viviendas particulares (50 preguntas). |
| `docs/Ficha_metodologica_CPV2024.txt` | 3 | 12 k | Ficha metodológica: tipo de censo, población objetivo, período de levantamiento, modalidades. |
| `docs/Glosario-Caracteristicas-de-la-poblacion_final.txt` | 4 | 10 k | Glosario de características de la población. |
| `docs/Glosario_CPV2024-1.txt` | 4 | 12 k | Glosario general de los primeros resultados. |
| `docs/Glosario_CPV2024_Dashboard_DEGURBA.txt` | 1 | 2 k | Glosario del tablero DEGURBA. |
| `docs/Glosario_fecundidad_migracion_CPV2024.txt` | 3 | 6 k | Glosario de fecundidad y migración. |
| `docs/Glosario_viviendas_y_servicios-basicos_CPV2024.txt` | 4 | 12 k | Glosario de viviendas y servicios básicos. |
| `docs/Manual_Censal_CPV2024.txt` | 216 | 607 k | Manual del censista: instrucciones y definiciones operativas de cada pregunta. |
| `docs/Manual_uso_cartografia_CPV2024.txt` | 23 | 54 k | Manual de uso de la cartografía y de las bases agregadas (manzana-entidad, zona-localidad). |
| `docs/N1_Nota_tecnica_desempenio_operativo_CPV2024.txt` | 8 | 15 k | Nota técnica 1: desempeño operativo. |
| `docs/N2_Nota_tecnica_respuesta_modalidades_recoleccion_CPV2024.txt` | 5 | 10 k | Nota técnica 2: respuesta por modalidad de recolección. |
| `docs/N3_Nota_Tecnica_Comparacion_Poblacion_CPV2024.txt` | 6 | 10 k | Nota técnica 3: comparación de la población censada con proyecciones y censos previos. |
| `docs/N4_Nota_Tecnica_Ajuste_direcciones_CPV2024.txt` | 7 | 18 k | Nota técnica 4: ajuste de direcciones. |
| `docs/N5_Nota_Tecnica_indeterminacion_geografica_CPV2024.txt` | 9 | 24 k | Nota técnica 5: indeterminación geográfica en los datos agregados. |
| `docs/N6_Nota_tecnica_Tratamiento_no_respuesta_al_item.txt` | 8 | 19 k | Nota técnica 6: tratamiento de la no respuesta al ítem. |
| `docs/Presentacion_cartografia_base_manzana_entidad_CPV2024.txt` | 33 | 24 k | Presentación sobre cartografía y base manzana-entidad. |
| `docs/Presentacion_microdatos_CPV2024.txt` | 31 | 21 k | Presentación del INE sobre la base de microdatos. |
| `docs/Resultados_CPV2024_Aplicación_DEGURBA.txt` | 32 | 102 k | Resultados de aplicar el grado de urbanización DEGURBA al Censo 2024. |
| `docs/manual_uso_microdatos_censo2024.txt` | 114 | 395 k | Manual de uso de microdatos: estructura de las tablas, variables calculadas, control de divulgación, diccionario y fichas de 47 indicadores con código R. Es la referencia principal. |
| `docs/sintesis_resultados_censo2024.txt` | 99 | 262 k | Síntesis de resultados nacionales y regionales (publicación oficial de diciembre de 2025). |

Sin convertir: `Cs_Pb_Al_Cs_CPV2024.html` (reporte interactivo de entidades) y los dos diccionarios xlsx, ya volcados en `diccionario.md` y `diccionario-agregados.md`.

