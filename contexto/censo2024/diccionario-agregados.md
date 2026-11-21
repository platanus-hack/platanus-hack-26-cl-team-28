# Datos agregados del Censo 2024 (bajo el nivel comunal)

Los microdatos solo llegan a comuna y área urbana o rural. Para territorios más pequeños el INE publica conteos ya agregados en `data/censo2024/agregados/`:

| Archivo | Unidad | Filas | Columnas | Suma de n_per |
|---|---|---|---|---|
| `Base_manzana_entidad_CPV24.csv` | manzanas (urbano) y entidades (rural); el nivel más fino | 197.032 | 212 | 18.480.432 |
| `Base_zona_localidad_CPV24.csv` | zonas censales (urbano) y localidades (rural) | 15.006 | 205 | 18.480.432 |
| `Base_urbanos_CPV24.csv` | entidades urbanas (ciudades y pueblos) | 848 | 204 | 16.018.474 |
| `Base_aldeas_CPV24.csv` | aldeas (entidades rurales concentradas) | 725 | 199 | 408.212 |

Las vistas `manzana_entidad`, `zona_localidad`, `urbanos` y `aldeas` de `scripts/consulta.py` ya entregan los conteos y promedios como números. Al leer los CSV directamente:

- Las celdas con `*` están suprimidas por secreto estadístico. Por eso muchas columnas numéricas llegan como texto: usar `try_cast(col as bigint)`.
- Los promedios usan coma decimal (`32,8`): usar `try_cast(replace(col, ',', '.') as double)`.
- `CONTENEDOR_COMUNAL = 1` marca filas que juntan, por comuna, a las personas que no se pudieron asignar a una unidad menor. No son un lugar real y vienen sin nombre. Están en `manzana_entidad`, `zona_localidad` y `urbanos`: inclúyelas para que los totales comunales cuadren y exclúyelas al buscar la unidad más poblada o al mapear.
- `zona_localidad` mezcla dos unidades. Las filas urbanas (`AREA_C = 1`) son zonas censales: no tienen nombre propio, se identifican por `DISTRITO` y `COD_ZONA` (o `ID_ZONA`), y `LOCALIDAD` es la ciudad que las contiene. Las filas rurales (`AREA_C = 2`) son localidades con nombre e `ID_LOCALIDAD`. `ID_ZONA` solo viene en las urbanas e `ID_LOCALIDAD` solo en las rurales.
- Un mismo nombre de localidad puede existir como urbana y como rural dentro de una comuna. Agrupa por `AREA_C` además de `LOCALIDAD`, o usa `urbanos` para el total de una ciudad.
- `CUT` es el código de comuna, el mismo que `comuna` en los microdatos.
- Las glosas de distritos, zonas, localidades y entidades están en la hoja `Glosas_variables_geográficas` de `data/censo2024/docs/diccionario_variables_glosas_censo2024.xlsx`.
- La nota técnica 5 y el manual de cartografía (en `docs/`) explican la indeterminación geográfica.

## Variables

No todas las variables están en las cuatro bases; las de identificación geográfica cambian según el nivel.

### Identificación geográfica

| Variable | Tipo | Descripción | Universo |
|---|---|---|---|
| `CONTENEDOR_COMUNAL` | Identificador | Registros asociados a nivel comuna sin vinculación a niveles menores a área urbana - rural (Valor: 1) | Todos los registros |
| `COD_REGION` | Identificador geográfico | Código de región | Todos los registros |
| `REGION` | Identificador geográfico | Región | Todos los registros |
| `PROVINCIA` | Identificador geográfico | Provincia | Todos los registros |
| `CUT` | Identificador geográfico | Código único territorial de comuna | Todos los registros |
| `COMUNA` | Identificador geográfico | Comuna | Todos los registros |
| `AREA_C` | Identificador geográfico | Tipo de estrato censal ( 1 Urbano - 2 Rural) | Todos los registros |
| `MANZENT` | Identificador geográfico | Código único identificador de manzana / entidad | Todos los registros |
| `DISTRITO` | Identificador geográfico | Distrito | Todos los registros |
| `COD_DISTRITO` | Identificador geográfico | Número de distrito | Todos los registros |
| `COD_LOCALIDAD` | Identificador geográfico | Código de localidad urbana/rural | Todos los registros |
| `COD_ZONA` | Identificador geográfico | Código de zonal censal | Todos los registros urbanos |
| `LOCALIDAD` | Identificador geográfico | Localidad | Todos los registros |
| `COD_ENTIDAD` | Identificador geográfico | Código de entidad poblada urbana/rural | Todos los registros |
| `COD_MANZANA` | Identificador geográfico | Código de manzana urbana/aldea | Todos los registros urbanos y aldea |
| `ENTIDAD` | Identificador geográfico | Entidad | Todos los registros |
| `TIPO_MZ` | Identificador geográfico | Tipo de manzana urbana/aldea | Todos los registros urbanos y aldea |
| `COD_CATEGORIA` | Identificador geográfico | Código de categoria de entidad | Todos los registros |
| `CATEGORIA` | Identificador geográfico | Categoría | Todos los registros |
| `ID_ENTIDAD` | Identificador geográfico | Identificador único de entidad agrupada (no considera división distrital) | Todos los registros |
| `ID_LOCALIDAD` | Identificador geográfico | Identificador único de localidad agrupada (no considera división distrital) | Todos los registros |
| `ID_DISTRITO` | Identificador geográfico | Identificador único de distrito | Todos los registros |
| `ID_ZONA` | Identificador geográfico | Identificador único de zona censal | Todos los registros urbanos |

### Características de la población

| Variable | Tipo | Descripción | Universo |
|---|---|---|---|
| `n_per` | Frecuencia | Personas | Personas censadas en viviendas particulares, colectivas y personas en situación de calle |
| `n_hombres` | Frecuencia | Hombres | Personas censadas en viviendas particulares, colectivas y personas en situación de calle |
| `n_mujeres` | Frecuencia | Mujeres | Personas censadas en viviendas particulares, colectivas y personas en situación de calle |
| `n_edad_0_5` | Frecuencia | Personas de 0 a 5 años | Personas censadas en viviendas particulares, colectivas y personas en situación de calle |
| `n_edad_6_13` | Frecuencia | Personas de 6 a 13 años | Personas censadas en viviendas particulares, colectivas y personas en situación de calle |
| `n_edad_14_17` | Frecuencia | Personas de 14 a 17 años | Personas censadas en viviendas particulares, colectivas y personas en situación de calle |
| `n_edad_18_24` | Frecuencia | Personas de 18 a 24 años | Personas censadas en viviendas particulares, colectivas y personas en situación de calle |
| `n_edad_25_44` | Frecuencia | Personas de 25 a 44 años | Personas censadas en viviendas particulares, colectivas y personas en situación de calle |
| `n_edad_45_59` | Frecuencia | Personas de 45 a 59 años | Personas censadas en viviendas particulares, colectivas y personas en situación de calle |
| `n_edad_60_mas` | Frecuencia | Personas de 60 años o más | Personas censadas en viviendas particulares, colectivas y personas en situación de calle |
| `prom_edad` | Promedio | Promedio de edad | Personas censadas en viviendas particulares, colectivas y personas en situación de calle |
| `n_inmigrantes` | Frecuencia | Personas inmigrantes internacionales (Lugar de nacimiento fuera de Chile) | Personas censadas en viviendas particulares, colectivas y personas en situación de calle |
| `n_nacionalidad` | Frecuencia | Personas con otra nacionalidad (no considera aquellos con doble nacionalidad) | Personas censadas en viviendas particulares, colectivas y personas en situación de calle |
| `n_pueblos_orig` | Frecuencia | Personas que son o se consideran pertenecientes a un pueblo originario | Personas censadas en viviendas particulares, colectivas y personas en situación de calle |
| `n_afrodescendencia` | Frecuencia | Personas que son o se consideran afrodescendientes | Personas censadas en viviendas particulares, colectivas y personas en situación de calle |
| `n_lengua_indigena` | Frecuencia | Personas que hablan o entienden alguna lengua indígena u originaria | Personas de 5 años o más |
| `n_religion` | Frecuencia | Personas que tienen una religión o credo | Personas de 15 años o más |
| `n_dificultad_ver` | Frecuencia | Personas con mucha dificultad o no pueden: Ver, aun usando anteojos | Personas de 5 años o más |
| `n_dificultad_oir` | Frecuencia | Personas con mucha dificultad o no pueden: Oír, aun usando un dispositivo auditivo | Personas de 5 años o más |
| `n_dificultad_mover` | Frecuencia | Personas con mucha dificultad o no pueden: Caminar o subir escaleras | Personas de 5 años o más |
| `n_dificultad_cogni` | Frecuencia | Personas con mucha dificultad o no pueden: Recordar o concentrarse | Personas de 5 años o más |
| `n_dificultad_cuidado` | Frecuencia | Personas con mucha dificultad o no pueden: Realizar tareas de cuidado personas, como bañarse o vestirse | Personas de 5 años o más |
| `n_dificultad_comunic` | Frecuencia | Personas con mucha dificultad o no pueden: Hablar o comunicarse usando su idioma habitual | Personas de 5 años o más |
| `n_discapacidad` | Frecuencia | Personas con discapacidad (declara mucha dificultad o imposibilidad para realizar algunas de las actividades del módulo de salud) | Personas de 5 años o más |
| `n_estcivcon_casado` | Frecuencia | Personas con estado civil o conyugal: Casado | Personas de 15 años o más |
| `n_estcivcon_conviviente` | Frecuencia | Personas con estado civil o conyugal: Conviviente o pareja sin acuerdo de unión civil | Personas de 15 años o más |
| `n_estcivcon_conv_civil` | Frecuencia | Personas con estado civil o conyugal: Conviviente civil (con acuerdo de unión civil) | Personas de 15 años o más |
| `n_estcivcon_anul_sep_div` | Frecuencia | Personas con estado civil o conyugal: Anulado, separado o divorciado | Personas de 15 años o más |
| `n_estcivcon_viudo` | Frecuencia | Personas con estado civil o conyugal: Viudo | Personas de 15 años o más |
| `n_estcivcon_soltero` | Frecuencia | Personas con estado civil o conyugal: Soltero | Personas de 15 años o más |
| `prom_escolaridad18` | Promedio | Promedio de escolaridad de personas de 18 años o más | Personas de 18 años o más |
| `n_asistencia_parv` | Frecuencia | Personas de 0 a 5 años que asisten a: Educación parvularia | Personas de 0 a 5 años |
| `n_asistencia_basica` | Frecuencia | Personas de 6 a 13 años que asisten a: Educación básica | Personas de 6 a 13 años |
| `n_asistencia_media` | Frecuencia | Personas de 14 a 17 años que asisten a: Educación media | Personas de 14 a 17 años |
| `n_asistencia_superior` | Frecuencia | Personas de 18 a 24 años que asisten a: Educación superior | Personas de 18 a 24 años |
| `n_cine_nunca_curso_primera_infancia` | Frecuencia | Personas con logro educacional más alto alcanzado (CINE11): Menor a primaria (incluye nunca cursó un programa educativo y Educación de la primera infancia) | Personas censadas en viviendas particulares, colectivas y personas en situación de calle |
| `n_cine_primaria` | Frecuencia | Personas con logro educacional más alto alcanzado (CINE11): Primaria (incluye Primaria en forma parcial, Educación primaria (nivel 1) y Educación primaria (nivel 2)) | Personas censadas en viviendas particulares, colectivas y personas en situación de calle |
| `n_cine_secundaria` | Frecuencia | Personas con logro educacional más alto alcanzado (CINE11): Secundaria (incluye Educación secundaria, con orientación general y con orientación vocacional) | Personas censadas en viviendas particulares, colectivas y personas en situación de calle |
| `n_cine_terciaria_maestria_doctorado` | Frecuencia | Personas con logro educacional más alto alcanzado (CINE11): Avanzado (incluye Educación terciaria de ciclo corto, con orientación vocacional, Grado de educación terciaria o nivel equivalente, Maestría y Nivel de doctorado o equivalente) | Personas censadas en viviendas particulares, colectivas y personas en situación de calle |
| `n_cine_especial_diferencial` | Frecuencia | Personas con logro educacional más alto alcanzado (CINE11): Educación especial o diferencial | Personas censadas en viviendas particulares, colectivas y personas en situación de calle |
| `n_analfabet` | Frecuencia | Personas de 15 años o más que no saben leer o escribir | Personas de 15 años o más |
| `n_ocupado` | Frecuencia | Personas de 15 años o más ocupadas | Personas de 15 años o más |
| `n_desocupado` | Frecuencia | Personas de 15 años o más desocupadas | Personas de 15 años o más |
| `n_fuera_fuerza_trabajo` | Frecuencia | Personas de 15 años o más fuera de la fuerza de trabajo | Personas de 15 años o más |
| `n_cise_rec_independientes` | Frecuencia | Personas de 15 años o más ocupadas independientes | Personas de 15 años o más ocupadas |
| `n_cise_rec_dependientes` | Frecuencia | Personas de 15 años o más ocupadas dependientes | Personas de 15 años o más ocupadas |
| `n_cise_rec_trabajador_no_remunerado` | Frecuencia | Personas de 15 años o más ocupadas trabajadores no remunerados | Personas de 15 años o más ocupadas |
| `n_ciuo_1` | Frecuencia | Personas ocupadas del grupo de CIUO: Directores, gerentes y administradores | Personas de 15 años o más ocupadas |
| `n_ciuo_2` | Frecuencia | Personas ocupadas del grupo de CIUO: Profesionales, científicos e intelectuales | Personas de 15 años o más ocupadas |
| `n_ciuo_3` | Frecuencia | Personas ocupadas del grupo de CIUO: Técnicos y profesionales de nivel medio | Personas de 15 años o más ocupadas |
| `n_ciuo_4` | Frecuencia | Personas ocupadas del grupo de CIUO: Personal de apoyo administrativo | Personas de 15 años o más ocupadas |
| `n_ciuo_5` | Frecuencia | Personas ocupadas del grupo de CIUO: Trabajadores de los servicios y vendedores de comercios y mercados | Personas de 15 años o más ocupadas |
| `n_ciuo_6` | Frecuencia | Personas ocupadas del grupo de CIUO: Agricultores y trabajadores calificados agropecuarios, forestales y pesqueros | Personas de 15 años o más ocupadas |
| `n_ciuo_7` | Frecuencia | Personas ocupadas del grupo de CIUO: Artesanos y operarios de oficios | Personas de 15 años o más ocupadas |
| `n_ciuo_8` | Frecuencia | Personas ocupadas del grupo de CIUO: Operadores de instalaciones, máquinas y ensambladores | Personas de 15 años o más ocupadas |
| `n_ciuo_9` | Frecuencia | Personas ocupadas del grupo de CIUO: Ocupaciones elementales | Personas de 15 años o más ocupadas |
| `n_ciuo_0` | Frecuencia | Personas ocupadas del grupo de CIUO: Ocupaciones de las fuerzas armadas | Personas de 15 años o más ocupadas |
| `n_caenes_A` | Frecuencia | Personas ocupadas en actividades de CAENES: Agricultura, ganadería, silvicultura y pesca | Personas de 15 años o más ocupadas |
| `n_caenes_B` | Frecuencia | Personas ocupadas en actividades de CAENES: Explotación de minas y canteras | Personas de 15 años o más ocupadas |
| `n_caenes_C` | Frecuencia | Personas ocupadas en actividades de CAENES: Industrias manufactureras | Personas de 15 años o más ocupadas |
| `n_caenes_D` | Frecuencia | Personas ocupadas en actividades de CAENES: Suministro de electricidad, gas, vapor y aire acondicionado | Personas de 15 años o más ocupadas |
| `n_caenes_E` | Frecuencia | Personas ocupadas en actividades de CAENES: Suministro de agua; evacuación de aguas residuales, gestión de desechos y descontaminación | Personas de 15 años o más ocupadas |
| `n_caenes_F` | Frecuencia | Personas ocupadas en actividades de CAENES: Construcción | Personas de 15 años o más ocupadas |
| `n_caenes_G` | Frecuencia | Personas ocupadas en actividades de CAENES: Comercio al por mayor y al por menor; reparación de vehículos automotores y motocicletas | Personas de 15 años o más ocupadas |
| `n_caenes_H` | Frecuencia | Personas ocupadas en actividades de CAENES: Transporte y almacenamiento | Personas de 15 años o más ocupadas |
| `n_caenes_I` | Frecuencia | Personas ocupadas en actividades de CAENES: Actividades de alojamiento y de servicio de comidas | Personas de 15 años o más ocupadas |
| `n_caenes_J` | Frecuencia | Personas ocupadas en actividades de CAENES: Información y comunicaciones | Personas de 15 años o más ocupadas |
| `n_caenes_K` | Frecuencia | Personas ocupadas en actividades de CAENES: Actividades financieras y de seguros | Personas de 15 años o más ocupadas |
| `n_caenes_L` | Frecuencia | Personas ocupadas en actividades de CAENES: Actividades inmobiliarias | Personas de 15 años o más ocupadas |
| `n_caenes_M` | Frecuencia | Personas ocupadas en actividades de CAENES: Actividades profesionales, científicas y técnicas | Personas de 15 años o más ocupadas |
| `n_caenes_N` | Frecuencia | Personas ocupadas en actividades de CAENES: Actividades de servicios administrativos y de apoyo | Personas de 15 años o más ocupadas |
| `n_caenes_O` | Frecuencia | Personas ocupadas en actividades de CAENES: Administración pública y defensa; planes de seguridad social de afiliación obligatoria | Personas de 15 años o más ocupadas |
| `n_caenes_P` | Frecuencia | Personas ocupadas en actividades de CAENES: Enseñanza | Personas de 15 años o más ocupadas |
| `n_caenes_Q` | Frecuencia | Personas ocupadas en actividades de CAENES: Actividades de atención de la salud humana y de asistencia social | Personas de 15 años o más ocupadas |
| `n_caenes_R` | Frecuencia | Personas ocupadas en actividades de CAENES: Actividades artísticas, de entretenimiento y recreativas | Personas de 15 años o más ocupadas |
| `n_caenes_S` | Frecuencia | Personas ocupadas en actividades de CAENES: Otras actividades de servicios | Personas de 15 años o más ocupadas |
| `n_caenes_T` | Frecuencia | Personas ocupadas en actividades de CAENES: Actividades de los hogares como empleadores; actividades no diferenciadas de los hogares como productores de bienes y servicios para uso propio | Personas de 15 años o más ocupadas |
| `n_caenes_U` | Frecuencia | Personas ocupadas en actividades de CAENES: Actividades de organizaciones y órganos extraterritoriales | Personas de 15 años o más ocupadas |
| `n_transporte_auto` | Frecuencia | Personas ocupadas fuera de su vivienda cuyo medio de transporte principal es: Auto particular | Personas de 15 años o más ocupadas que trabajan fuera de su vivienda |
| `n_transporte_publico` | Frecuencia | Personas ocupadas fuera de su vivienda cuyo medio de transporte principal es: transporte público | Personas de 15 años o más ocupadas que trabajan fuera de su vivienda |
| `n_transporte_camina` | Frecuencia | Personas ocupadas fuera de su vivienda cuyo medio de transporte principal es: Caminando | Personas de 15 años o más ocupadas que trabajan fuera de su vivienda |
| `n_transporte_bicicleta` | Frecuencia | Personas ocupadas fuera de su vivienda cuyo medio de transporte principal es: Bicicleta | Personas de 15 años o más ocupadas que trabajan fuera de su vivienda |
| `n_transporte_motocicleta` | Frecuencia | Personas ocupadas fuera de su vivienda cuyo medio de transporte principal es: Motocicleta | Personas de 15 años o más ocupadas que trabajan fuera de su vivienda |
| `n_transporte_cab_lan_bote` | Frecuencia | Personas ocupadas fuera de su vivienda cuyo medio de transporte principal es: Caballo, lancha o bote | Personas de 15 años o más ocupadas que trabajan fuera de su vivienda |
| `n_transporte_otros` | Frecuencia | Personas ocupadas fuera de su vivienda cuyo medio de transporte principal es: Otro medio | Personas de 15 años o más ocupadas que trabajan fuera de su vivienda |

### Características de los hogares

| Variable | Tipo | Descripción | Universo |
|---|---|---|---|
| `n_hog` | Frecuencia | Hogares | Hogares censados en viviendas particulares ocupadas con moradores presentes |
| `prom_per_hog` | Promedio | Promedio de personas por hogar | Hogares censados en viviendas particulares ocupadas con moradores presentes |
| `n_hog_unipersonales` | Frecuencia | Hogares unipersonales | Hogares censados en viviendas particulares ocupadas con moradores presentes |
| `n_hog_60` | Frecuencia | Hogares compuestos solo de personas de 60 años o más | Hogares censados en viviendas particulares ocupadas con moradores presentes |
| `n_hog_menores` | Frecuencia | Hogares con al menos una persona de 0 a 14 años | Hogares censados en viviendas particulares ocupadas con moradores presentes |
| `n_jefatura_mujer` | Frecuencia | Hogares con jefatura de hogar femenina | Hogares censados en viviendas particulares ocupadas con moradores presentes |
| `n_tenencia_propia_pagada` | Frecuencia | Hogares con tenencia de la vivienda: propia pagada | Hogares censados en viviendas particulares ocupadas con moradores presentes |
| `n_tenencia_propia_pagandose` | Frecuencia | Hogares con tenencia de la vivienda: propia pagándose | Hogares censados en viviendas particulares ocupadas con moradores presentes |
| `n_tenencia_arrendada_contrato` | Frecuencia | Hogares con tenencia de la vivienda: arrendada con contrato | Hogares censados en viviendas particulares ocupadas con moradores presentes |
| `n_tenencia_arrendada_sin_contrato` | Frecuencia | Hogares con tenencia de la vivienda: arrendada sin contrato | Hogares censados en viviendas particulares ocupadas con moradores presentes |
| `n_tenencia_cedida_trabajo` | Frecuencia | Hogares con tenencia de la vivienda: cedida por trabajo o servicio | Hogares censados en viviendas particulares ocupadas con moradores presentes |
| `n_tenencia_cedida_familiar` | Frecuencia | Hogares con tenencia de la vivienda: cedida por familiar u otro | Hogares censados en viviendas particulares ocupadas con moradores presentes |
| `n_tenencia_otro` | Frecuencia | Hogares con tenencia de la vivienda: otro (usufructo, ocupada de hecho, propiedad en sucesión o litigio) | Hogares censados en viviendas particulares ocupadas con moradores presentes |
| `n_comb_cocina_gas` | Frecuencia | Hogares con energía o combustible para cocinar: gas | Hogares censados en viviendas particulares ocupadas con moradores presentes |
| `n_comb_cocina_parafina` | Frecuencia | Hogares con energía o combustible para cocinar: parafina o pretróleo | Hogares censados en viviendas particulares ocupadas con moradores presentes |
| `n_comb_cocina_lena` | Frecuencia | Hogares con energía o combustible para cocinar: leña | Hogares censados en viviendas particulares ocupadas con moradores presentes |
| `n_comb_cocina_pellet` | Frecuencia | Hogares con energía o combustible para cocinar: pellet | Hogares censados en viviendas particulares ocupadas con moradores presentes |
| `n_comb_cocina_carbon` | Frecuencia | Hogares con energía o combustible para cocinar: carbón | Hogares censados en viviendas particulares ocupadas con moradores presentes |
| `n_comb_cocina_electricidad` | Frecuencia | Hogares con energía o combustible para cocinar: electricidad | Hogares censados en viviendas particulares ocupadas con moradores presentes |
| `n_comb_cocina_solar` | Frecuencia | Hogares con energía o combustible para cocinar: energía solar | Hogares censados en viviendas particulares ocupadas con moradores presentes |
| `n_comb_cocina_no_utiliza` | Frecuencia | Hogares con energía o combustible para cocinar: no utiliza fuente de energía | Hogares censados en viviendas particulares ocupadas con moradores presentes |
| `n_comb_calefaccion_gas` | Frecuencia | Hogares con energía o combustible para calefaccionar: gas | Hogares censados en viviendas particulares ocupadas con moradores presentes |
| `n_comb_calefaccion_parafina` | Frecuencia | Hogares con energía o combustible para calefaccionar: parafina o pretróleo | Hogares censados en viviendas particulares ocupadas con moradores presentes |
| `n_comb_calefaccion_lena` | Frecuencia | Hogares con energía o combustible para calefaccionar: leña | Hogares censados en viviendas particulares ocupadas con moradores presentes |
| `n_comb_calefaccion_pellet` | Frecuencia | Hogares con energía o combustible para calefaccionar: pellet | Hogares censados en viviendas particulares ocupadas con moradores presentes |
| `n_comb_calefaccion_carbon` | Frecuencia | Hogares con energía o combustible para calefaccionar: carbón | Hogares censados en viviendas particulares ocupadas con moradores presentes |
| `n_comb_calefaccion_electricidad` | Frecuencia | Hogares con energía o combustible para calefaccionar: electricidad | Hogares censados en viviendas particulares ocupadas con moradores presentes |
| `n_comb_calefaccion_otra` | Frecuencia | Hogares con energía o combustible para calefaccionar: otra | Hogares censados en viviendas particulares ocupadas con moradores presentes |
| `n_comb_calefaccion_no_utiliza` | Frecuencia | Hogares con energía o combustible para calefaccionar: no utiliza fuente de energía | Hogares censados en viviendas particulares ocupadas con moradores presentes |
| `n_serv_tel_movil` | Frecuencia | Hogares con disponibilidad equipos o servicios: teléfono móvil, celular o smartphone | Hogares censados en viviendas particulares ocupadas con moradores presentes |
| `n_serv_compu` | Frecuencia | Hogares con disponibilidad equipos o servicios: computador | Hogares censados en viviendas particulares ocupadas con moradores presentes |
| `n_serv_tablet` | Frecuencia | Hogares con disponibilidad equipos o servicios: tablet | Hogares censados en viviendas particulares ocupadas con moradores presentes |
| `n_serv_internet_fija` | Frecuencia | Hogares con disponibilidad equipos o servicios: internet fija | Hogares censados en viviendas particulares ocupadas con moradores presentes |
| `n_serv_internet_movil` | Frecuencia | Hogares con disponibilidad equipos o servicios: internet móvil | Hogares censados en viviendas particulares ocupadas con moradores presentes |
| `n_serv_internet_satelital` | Frecuencia | Hogares con disponibilidad equipos o servicios: internet por conexión satelital | Hogares censados en viviendas particulares ocupadas con moradores presentes |
| `n_internet` | Frecuencia | Hogares con acceso a internet | Hogares censados en viviendas particulares ocupadas con moradores presentes |

### Características de las viviendas

| Variable | Tipo | Descripción | Universo |
|---|---|---|---|
| `n_vp` | Frecuencia | Viviendas particulares | Viviendas particulares |
| `n_vp_ocupada` | Frecuencia | Viviendas particulares ocupadas | Viviendas particulares |
| `n_vp_desocupada` | Frecuencia | Viviendas particulares desocupadas | Viviendas particulares |
| `n_tipo_viv_casa` | Frecuencia | Viviendas con tipo de vivienda: casa | Viviendas particulares ocupadas con moradores presentes |
| `n_tipo_viv_depto` | Frecuencia | Viviendas con tipo de vivienda: departamento | Viviendas particulares ocupadas con moradores presentes |
| `n_tipo_viv_indigena` | Frecuencia | Viviendas con tipo de vivienda: vivienda tradicional indígena | Viviendas particulares ocupadas con moradores presentes |
| `n_tipo_viv_pieza` | Frecuencia | Viviendas con tipo de vivienda: pieza en casa antigua o conventillo | Viviendas particulares ocupadas con moradores presentes |
| `n_tipo_viv_mediagua` | Frecuencia | Viviendas con tipo de vivienda: mediagua, mejora, etc | Viviendas particulares ocupadas con moradores presentes |
| `n_tipo_viv_movil` | Frecuencia | Viviendas con tipo de vivienda: móvil | Viviendas particulares ocupadas con moradores presentes |
| `n_tipo_viv_otro` | Frecuencia | Viviendas con tipo de vivienda: otro tipo de vivienda | Viviendas particulares ocupadas con moradores presentes |
| `n_dormitorios_1` | Frecuencia | Número de viviendas con 1 dormitorio | Viviendas particulares ocupadas con moradores presentes |
| `n_dormitorios_2` | Frecuencia | Número de viviendas con 2 dormitorios | Viviendas particulares ocupadas con moradores presentes |
| `n_dormitorios_3` | Frecuencia | Número de viviendas con 3 dormitorios | Viviendas particulares ocupadas con moradores presentes |
| `n_dormitorios_4` | Frecuencia | Número de viviendas con 4 dormitorios | Viviendas particulares ocupadas con moradores presentes |
| `n_dormitorios_5` | Frecuencia | Número de viviendas con 5 dormitorios | Viviendas particulares ocupadas con moradores presentes |
| `n_dormitorios_6_o_mas` | Frecuencia | Número de viviendas con 6 dormitorios o más | Viviendas particulares ocupadas con moradores presentes |
| `n_viv_hacinadas` | Frecuencia | Viviendas hacinadas | Viviendas particulares ocupadas con moradores presentes |
| `n_viv_irrecuperables` | Frecuencia | Viviendas irrecuperables | Viviendas particulares ocupadas con moradores presentes |
| `n_hog_allegados` | Frecuencia | Hogares allegados | Viviendas particulares ocupadas con moradores presentes |
| `n_nucleos_hacinados_allegados` | Frecuencia | Núcleos hacinados allegados | Hogares censados en viviendas particulares ocupadas con moradores presentes |
| `n_viv_no_ampliables` | Frecuencia | Hogares que residen en viviendas hacinadas no ampliables | Hogares censados en viviendas particulares ocupadas con moradores presentes |
| `n_deficit_cuantitativo` | Frecuencia | Déficit habitacional cuantitativo | Viviendas particulares ocupadas con moradores presentes |
| `n_mat_paredes_hormigon` | Frecuencia | Viviendas con materialidad paredes: hormigón armado | Viviendas particulares ocupadas con moradores presentes |
| `n_mat_paredes_albanileria` | Frecuencia | Viviendas con materialidad paredes: albañilería | Viviendas particulares ocupadas con moradores presentes |
| `n_mat_paredes_tabique_forrado` | Frecuencia | Viviendas con materialidad paredes: tabique forrado por ambas caras | Viviendas particulares ocupadas con moradores presentes |
| `n_mat_paredes_tabique_sin_forro` | Frecuencia | Viviendas con materialidad paredes: tabique sin forro interior | Viviendas particulares ocupadas con moradores presentes |
| `n_mat_paredes_artesanal` | Frecuencia | Viviendas con materialidad paredes: adobe, barro, pirca, quincha u otro material artesanal | Viviendas particulares ocupadas con moradores presentes |
| `n_mat_paredes_precarios` | Frecuencia | Viviendas con materialidad paredes: materiales precarios o de desecho | Viviendas particulares ocupadas con moradores presentes |
| `n_mat_techo_tejas` | Frecuencia | Viviendas con materialidad techo: tejas o tejuelas de arcilla, metálicas, de cemento, de madera, asfálticas o plásticas | Viviendas particulares ocupadas con moradores presentes |
| `n_mat_techo_hormigon` | Frecuencia | Viviendas con materialidad techo: losa hormigón | Viviendas particulares ocupadas con moradores presentes |
| `n_mat_techo_zinc` | Frecuencia | Viviendas con materialidad techo: planchas metálicas de zinc, cobre, etc. | Viviendas particulares ocupadas con moradores presentes |
| `n_mat_techo_fibrocemento` | Frecuencia | Viviendas con materialidad techo: planchas de fibrocemento tipo pizarreño | Viviendas particulares ocupadas con moradores presentes |
| `n_mat_techo_fonolita` | Frecuencia | Viviendas con materialidad techo: fonolita o plancha de fieltro embreado | Viviendas particulares ocupadas con moradores presentes |
| `n_mat_techo_paja` | Frecuencia | Viviendas con materialidad techo: paja, coirón, totora o caña | Viviendas particulares ocupadas con moradores presentes |
| `n_mat_techo_precarios` | Frecuencia | Viviendas con materialidad techo: materiales precarios o de desecho | Viviendas particulares ocupadas con moradores presentes |
| `n_mat_techo_sin_cubierta` | Frecuencia | Viviendas con materialidad techo: sin cubierta sólida de techo | Viviendas particulares ocupadas con moradores presentes |
| `n_mat_piso_radier_con_revestimiento` | Frecuencia | Viviendas con materialidad piso: parquet, piso flotante, cerámico, madera, alfombra, flexit, cubrepiso u otro similar: sobre radier o vigas de madera | Viviendas particulares ocupadas con moradores presentes |
| `n_mat_piso_radier_sin_revestimiento` | Frecuencia | Viviendas con materialidad piso: radier sin revestimiento | Viviendas particulares ocupadas con moradores presentes |
| `n_mat_piso_baldosa_cemento` | Frecuencia | Viviendas con materialidad piso: baldosa de cemento | Viviendas particulares ocupadas con moradores presentes |
| `n_mat_piso_capa_cemento` | Frecuencia | Viviendas con materialidad piso: capa de cemento sobre tierra | Viviendas particulares ocupadas con moradores presentes |
| `n_mat_piso_tierra` | Frecuencia | Viviendas con materialidad piso: tierra | Viviendas particulares ocupadas con moradores presentes |
| `n_fuente_agua_publica` | Frecuencia | Viviendas cuya fuente de agua es: red pública | Viviendas particulares ocupadas con moradores presentes |
| `n_fuente_agua_pozo` | Frecuencia | Viviendas cuya fuente de agua es: pozo o noria | Viviendas particulares ocupadas con moradores presentes |
| `n_fuente_agua_camion` | Frecuencia | Viviendas cuya fuente de agua es: camión aljibe | Viviendas particulares ocupadas con moradores presentes |
| `n_fuente_agua_rio` | Frecuencia | Viviendas cuya fuente de agua es: río, vertiente, estero, canal, etc | Viviendas particulares ocupadas con moradores presentes |
| `n_distrib_agua_llave` | Frecuencia | Viviendas con sistema de distribución: llave dentro de la vivienda | Viviendas particulares ocupadas con moradores presentes |
| `n_distrib_agua_llave_fuera` | Frecuencia | Viviendas con sistema de distribución: con llave dentro del sitio, fuera de la vivienda | Viviendas particulares ocupadas con moradores presentes |
| `n_distrib_agua_acarreo` | Frecuencia | Viviendas con sistema de distribución: no tiene sistema, la acarrea | Viviendas particulares ocupadas con moradores presentes |
| `n_serv_hig_alc_dentro` | Frecuencia | Viviendas con servicio higiénico: dentro de la vivienda, conectado al alcantarillado | Viviendas particulares ocupadas con moradores presentes |
| `n_serv_hig_alc_fuera` | Frecuencia | Viviendas con servicio higiénico: fuera de la vivienda, conectado al alcantarillado | Viviendas particulares ocupadas con moradores presentes |
| `n_serv_hig_fosa` | Frecuencia | Viviendas con servicio higiénico: conectado a una fosa séptica | Viviendas particulares ocupadas con moradores presentes |
| `n_serv_hig_pozo` | Frecuencia | Viviendas con servicio higiénico: conectado a pozo negro | Viviendas particulares ocupadas con moradores presentes |
| `n_serv_hig_acequia_canal` | Frecuencia | Viviendas con servicio higiénico: en un cajón sobre acequia o canal | Viviendas particulares ocupadas con moradores presentes |
| `n_serv_hig_cajon_otro` | Frecuencia | Viviendas con servicio higiénico: en un cajón conectado a otro sistema | Viviendas particulares ocupadas con moradores presentes |
| `n_serv_hig_bano_quimico` | Frecuencia | Viviendas con servicio higiénico: baño químico | Viviendas particulares ocupadas con moradores presentes |
| `n_serv_hig_bano_seco` | Frecuencia | Viviendas con servicio higiénico: conectado a baño seco | Viviendas particulares ocupadas con moradores presentes |
| `n_serv_hig_no_tiene` | Frecuencia | Viviendas con servicio higiénico: no tiene servicio higiénico | Viviendas particulares ocupadas con moradores presentes |
| `n_fuente_elect_publica` | Frecuencia | Viviendas con electricidad: red pública | Viviendas particulares ocupadas con moradores presentes |
| `n_fuente_elect_diesel` | Frecuencia | Viviendas con electricidad: generador diésel o bencina | Viviendas particulares ocupadas con moradores presentes |
| `n_fuente_elect_solar` | Frecuencia | Viviendas con electricidad: placa solar | Viviendas particulares ocupadas con moradores presentes |
| `n_fuente_elect_eolica` | Frecuencia | Viviendas con electricidad: energía eólica | Viviendas particulares ocupadas con moradores presentes |
| `n_fuente_elect_otro` | Frecuencia | Viviendas con electricidad: otro | Viviendas particulares ocupadas con moradores presentes |
| `n_fuente_elect_no_tiene` | Frecuencia | Viviendas con electricidad: no tiene energía eléctrica | Viviendas particulares ocupadas con moradores presentes |
| `n_basura_servicios` | Frecuencia | Viviendas con eliminación de basura: la recogen los servicios de aseo | Viviendas particulares ocupadas con moradores presentes |
| `n_basura_entierra` | Frecuencia | Viviendas con eliminación de basura: la entierra o la quema | Viviendas particulares ocupadas con moradores presentes |
| `n_basura_eriazo` | Frecuencia | Viviendas con eliminación de basura: la deja en terreno eriazo, quebrada o zanja | Viviendas particulares ocupadas con moradores presentes |
| `n_basura_rio` | Frecuencia | Viviendas con eliminación de basura: la tira al río, laguna o mar | Viviendas particulares ocupadas con moradores presentes |
| `n_basura_otro` | Frecuencia | Viviendas con eliminación de basura: otro | Viviendas particulares ocupadas con moradores presentes |

