# Consultas de ejemplo sobre el Censo 2024

Todas se ejecutan con `uv run python -I scripts/consulta.py "<sql>"` desde la raíz del proyecto y fueron probadas contra los datos. El dialecto es DuckDB.

## Población por comuna, con nombres

`comunas` ya trae población, viviendas y hogares, así que no hace falta tocar los microdatos:

```sql
select nombre_comuna, nombre_region, poblacion, viviendas, hogares
from comunas
order by poblacion desc
limit 10;
```

## Frecuencia de una variable con sus etiquetas

`etiquetas` tiene una fila por tabla, variable y valor. El filtro `> 0` deja fuera la no respuesta (`-99`) y lo suprimido (`-66`).

```sql
select e.etiqueta, count(*) as hogares,
       round(100.0 * count(*) / sum(count(*)) over (), 1) as pct
from hogares h
join etiquetas e
  on e.tabla = 'hogares' and e.variable = 'p12_tenencia_viv' and e.valor = h.p12_tenencia_viv
where h.tipo_operativo = 2 and h.p12_tenencia_viv > 0
group by all
order by hogares desc;
```

## Indicador por región, excluyendo la no respuesta

Porcentaje de población nacida fuera de Chile (indicador `mig01` del manual):

```sql
select t.nombre as region,
       round(100.0 * count(*) filter (where p25_lug_nacimiento = 3) / count(*), 1) as pct_nacida_fuera
from personas p
join territorios t on t.nivel = 'region' and t.codigo = p.region
where p25_lug_nacimiento <> -99
group by 1
order by 2 desc;
```

## Cruce de vivienda, hogar y persona

Personas de 15 años o más de la comuna de Santiago que viven en hogares extensos, por sexo (ejemplo del manual del INE; da 21.650 hombres y 29.354 mujeres):

```sql
select p.sexo, count(*) as personas
from viviendas v
join hogares h using (id_vivienda)
join personas p using (id_vivienda, id_hogar)
where v.comuna = 13101 and h.tipologia_hogar = 5 and p.edad >= 15
group by 1
order by 1;
```

Las tres tablas repiten `region`, `provincia`, `comuna`, `area` y `tipo_operativo`, así que muchas veces el cruce no es necesario.

## Pirámide de edad de una comuna

```sql
select edad_quinquenal,
       count(*) filter (where sexo = 1) as hombres,
       count(*) filter (where sexo = 2) as mujeres
from personas
where comuna = 5101
group by 1
order by 1;
```

## Tamaño de los hogares

Los hogares solo existen en viviendas particulares (`tipo_operativo = 2`):

```sql
with tam as (
  select id_vivienda, id_hogar, count(*) as personas
  from personas
  where tipo_operativo = 2
  group by all
)
select personas, count(*) as hogares
from tam
group by 1
order by 1;
```

## Migración interna: de dónde llegó la población de una región

`p24_lug_resid5_esp` es la comuna de residencia cinco años antes (o un código de país). Personas que hoy viven en Los Lagos y hace cinco años vivían en otra región:

```sql
select o.nombre_region as origen, count(*) as personas
from personas p
join comunas o on o.comuna = p.p24_lug_resid5_esp
where p.region = 10 and o.region <> 10
group by 1
order by 2 desc;
```

## Bajo el nivel comunal: zonas y manzanas

Las vistas de datos agregados ya convierten los conteos (`n_*`) y promedios (`prom_*`) a número y dejan como `NULL` las celdas suprimidas.

Zonas censales y localidades más pobladas de una comuna:

```sql
select AREA_C, DISTRITO, LOCALIDAD, ID_ZONA, ID_LOCALIDAD, n_per, prom_edad, prom_escolaridad18
from zona_localidad
where CUT = 13101 and CONTENEDOR_COMUNAL = 0
order by n_per desc
limit 10;
```

Ciudades y pueblos de una comuna:

```sql
select ENTIDAD, CATEGORIA, n_per
from urbanos
where CUT = 5101 and CONTENEDOR_COMUNAL = 0
order by n_per desc;
```

En `manzana_entidad`, `zona_localidad` y `urbanos`, las filas con `CONTENEDOR_COMUNAL = 1` reúnen a las personas de la comuna que no se pudieron ubicar en una unidad menor. Hay que incluirlas para que los totales comunales cuadren y excluirlas al buscar la unidad más poblada o al mapear. `diccionario-agregados.md` explica cómo se distinguen zonas urbanas y localidades rurales.

## Leer un tabulado oficial

Los encabezados son los del INE, con espacios y tildes, así que van entre comillas dobles:

```sql
select "Comuna", "Población censada", "65 años o más", "Índice de envejecimiento"
from read_csv('data/censo2024/tabulados_csv/D2_2.csv')
where "Código comuna" = 14101 and "Sexo" = 'Total Comuna';
```

La fila con código 0 es el total país. Antes de usar un cuadro, mira sus columnas en `tabulados.md` y su nota en `data/censo2024/tabulados_csv/<prefijo>_nota.txt`.

## Desde Python

```python
import duckdb

con = duckdb.connect()
filas = con.execute("""
    select region, count(*)
    from 'data/censo2024/microdatos/personas_censo2024.parquet'
    group by 1 order by 1
""").fetchall()
```
