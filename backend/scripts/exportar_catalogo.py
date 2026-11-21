"""Materializa los representantes censales en el formato del servidor."""

import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import duckdb

from agrupar_catalogo import comparar, preparar


def exportar(con, firmas, masa, estrictos, viviendas, salida, tamano):
    if salida.exists():
        raise FileExistsError(f"El catálogo ya existe: {salida}")
    salida.parent.mkdir(parents=True, exist_ok=True)
    con.read_parquet(str(viviendas)).create_view("viviendas")
    elegibles = masa > 0
    con.register("seleccion", {"firma": firmas[elegibles], "n": masa[elegibles], "estrictos": estrictos[elegibles]})
    con.execute("""
        create temp table elegidos as
        select id_vivienda, id_hogar, id_persona, region, lugar <= estrictos as grupo_estricto
        from (
            select f.*, s.n, s.estrictos, row_number() over (
                partition by f.firma
                order by hash(f.id_vivienda, f.id_hogar, f.id_persona, 2024), f.id_vivienda, f.id_hogar, f.id_persona
            ) as lugar
            from firmas f join seleccion s using (firma)
        )
        where lugar <= n
    """)
    con.unregister("seleccion")
    regiones = con.execute("select region, count(*) from elegidos group by 1 order by 1").fetchall()
    assert sum(n for _, n in regiones) == int(masa.sum())
    with TemporaryDirectory(prefix=".catalogo-", dir=salida.parent) as temporal:
        carpeta = Path(temporal)
        for region, esperados in regiones:
            ruta = carpeta / f"region_{region:02d}.parquet"
            # El catálogo conserva atributos censales que no intervienen en el matching.
            con.execute(f"""
                copy (
                    with familias as (
                        select id_vivienda, id_hogar,
                               list(edad order by edad) filter (where edad between 0 and 17) as edades_menores,
                               list(edad order by edad) filter (where edad between 0 and 17 and parentesco in (5, 6)) as edades_hijos_jefatura,
                               bool_and(edad >= 0 or edad_quinquenal >= 20) as edades_menores_conocidas
                        from personas where tipo_operativo = 2 and region = {region}
                        group by 1, 2
                    )
                    select row_number() over (order by p.id_vivienda, p.id_hogar, p.id_persona)
                               + {region}::bigint * 10000000 as id_persona_muestra,
                           p.* exclude (id_vivienda, id_hogar, id_persona, edad),
                           case when p.edad >= 0 then p.edad else p.edad_quinquenal end as edad,
                           p.edad < 0 as edad_suprimida,
                           case when h.id_hogar is not null then p.id_vivienda * 100 + p.id_hogar end as id_hogar_muestra,
                           h.tipologia_hogar, h.p12_tenencia_viv, h.p15b_serv_compu,
                           h.p15d_serv_internet_fija, h.p15e_serv_internet_movil, h.p15f_serv_internet_satelital,
                           c.tamano as n_personas, c.mayores_65, f.edades_menores,
                           f.edades_hijos_jefatura, f.edades_menores_conocidas,
                           v.p2_tipo_vivienda, v.indice_hacinamiento,
                           null::integer as genero, null::integer as quintil_ingreso,
                           null::integer as posicion_politica, e.grupo_estricto, {tamano}::integer as representa
                    from elegidos e
                    join personas p using (region, id_vivienda, id_hogar, id_persona)
                    left join hogares h on h.id_vivienda = p.id_vivienda and h.id_hogar = p.id_hogar
                        and h.tipo_operativo = 2 and p.tipo_operativo = 2 and h.region = {region}
                    left join composicion c on c.id_vivienda = h.id_vivienda and c.id_hogar = h.id_hogar
                    left join familias f on f.id_vivienda = h.id_vivienda and f.id_hogar = h.id_hogar
                    left join viviendas v on v.id_vivienda = p.id_vivienda and v.region = {region}
                    where e.region = {region} and p.region = {region}
                ) to ? (format parquet, compression zstd)
            """, [str(ruta)])
            cantidad, ids, minimo, maximo = con.execute(
                "select count(*), count(distinct id_persona_muestra), min(representa), max(representa) from read_parquet(?)",
                [str(ruta)],
            ).fetchone()
            assert cantidad == esperados == ids and minimo == maximo == tamano
            print(f"Región {region:02d}: {cantidad:,} grupos de {tamano}", flush=True)
        manifiesto = {"tamano_grupo": tamano, "fuente": "Censo 2024", "agentes": int(masa.sum()),
                      "grupos_etapa_estricta": int(estrictos.sum()), "casen": False, "cep": False}
        (carpeta / "catalogo.json").write_text(json.dumps(manifiesto, ensure_ascii=False, indent=2) + "\n")
        carpeta.rename(salida)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("personas", type=Path)
    ap.add_argument("hogares", type=Path)
    ap.add_argument("viviendas", type=Path)
    ap.add_argument("salida", type=Path)
    ap.add_argument("--tamano", type=int, choices=(3, 5), default=3)
    args = ap.parse_args()
    with duckdb.connect(config={"threads": 4, "memory_limit": "1600MB", "preserve_insertion_order": False}) as con:
        firmas, original = preparar(con, args.personas, args.hogares)
        resultado, masa, estrictos = comparar(firmas, original, args.tamano)
        # La exportación une perfiles completos y necesita más margen que el agrupador.
        con.execute("set threads = 2")
        con.execute("set memory_limit = '3GB'")
        exportar(con, firmas, masa, estrictos, args.viviendas, args.salida, args.tamano)
        print(json.dumps(resultado, ensure_ascii=False))


if __name__ == "__main__":
    main()
