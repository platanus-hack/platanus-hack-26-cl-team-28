# Pruebas de simulación

Aquí viven la población simulada, que es la misma para todo, y una carpeta por caso.

## Población

`poblacion/` tiene los perfiles que lee el modelo. Son generales: describen a cada persona con todo lo que se sabe de ella y no miran qué se le va a preguntar. Los escribe `scripts/personas_muestra.py`.

| Archivo | Contenido |
|---|---|
| `poblacion/regiones_50.jsonl` | 800 personas de 14 años o más, 50 por región, con `peso` para cifras nacionales. |
| `poblacion/al_azar_2000.jsonl` | 2.000 personas de 14 años o más al azar: cada una vale lo mismo, así que los porcentajes salen sin ponderar. Es la que usa el motor del sitio. |

Cerca del 7 % son menores de 14 a 17 años. Su perfil no trae política ni opiniones, porque la CEP entrevista desde los 18, y sí el tipo de colegio al que van. Con `--edad-minima 18` salen solo adultos.

Salen de la muestra del 1 %. Para más personas por región se usa el mismo script con otro `--por-region` (los primeros 50 de cada región siguen siendo los mismos), sobre la muestra o sobre la población completa (`data/chile/chile.parquet`).

Cada línea trae `perfil` (el texto por secciones que lee el modelo), `grupos` (categorías para desagregar), `datos` (edad, género, región, comuna, zona, quintil y educación, sueltos) y `peso`.

Un perfil completo son unos 4.200 caracteres (cerca de 1.200 tokens), en nueve secciones. Con `--secciones` se puede generar uno más corto.

## Un caso

Un caso es cualquier cosa sobre la que se quiera estimar una respuesta: un proyecto de ley, una medida municipal, una pregunta de opinión. Es una carpeta con esta forma; todo es opcional salvo un texto:

| Ruta | Contenido |
|---|---|
| `variantes/*.md` | Una versión por archivo. Se comparan entre sí con las mismas personas. |
| `variantes/atributos.json` | Qué valor tiene cada variante en cada atributo, para medir el efecto de cada uno. |
| `validacion/*.md` | Textos sobre los que hay encuestas reales. |
| `validacion/*.json` | Preguntas de alternativas sobre las que hay encuestas reales. |
| `benchmarks.json` | Las cifras reales: `cerradas` por nombre de texto y `alternativas` por nombre de pregunta. |
| `encuesta.json` | Preguntas propias del caso: `{"preguntas": [...], "indice": [1, 2]}`. La escala es de 1 a 7. Sin este archivo se usan seis preguntas sobre una política. |
| `resultados_*.jsonl` | Lo que contestó cada modelo. No se puede reconstruir. |

## Cómo se corre

Con el modelo local (necesita la GPU):

```sh
scripts/servir_modelo.sh qwen4
uv run python -I scripts/probar_modelo.py data/pruebas/poblacion/regiones_50.jsonl data/pruebas/CASO/variantes
```

Con subagentes (por ejemplo Claude Haiku), sin GPU:

```sh
uv run python -I scripts/lotes_agentes.py preparar data/pruebas/poblacion/regiones_50.jsonl data/pruebas/CASO/variantes LOTES --juntas --tamano 20
# cada subagente lee LOTES/juntas/lote_NN.md y escribe lote_NN.jsonl
uv run python -I scripts/lotes_agentes.py reunir LOTES data/pruebas/CASO/resultados_variantes_haiku.jsonl --modelo "claude-haiku-5-5 (subagentes)"
```

Y la comparación, igual para ambos:

```sh
uv run python -I scripts/comparar_variantes.py data/pruebas/poblacion/regiones_50.jsonl data/pruebas/CASO/resultados_*.jsonl
```

Para validar contra más encuestas reales está `datos-pruebas/`, en la raíz del repositorio: 140 casos con sus porcentajes publicados, que se pueden convertir en textos de `validacion/` y entradas de `benchmarks.json`.

## Casos

- `sala_cuna/`: proyecto de Sala Cuna Universal, variantes A a E. Sus resultados hasta el 21-11-2026 se hicieron con perfiles más cortos (`sala_cuna/personas_*.jsonl`), no con los de `poblacion/`. Eran solo adultos: 731 de las 800 personas de `poblacion/regiones_50.jsonl` son las mismas, y con `--edad-minima 18` lo son todas. Sus ingresos imputados pueden diferir, porque el emparejamiento de hogares se corrigió después (ahora distingue hogares con niños y con adultos mayores).
- `personas.jsonl`, `politica_ejemplo.md` y `resultados_Qwen*.jsonl` en esta carpeta son las primeras pruebas de velocidad, con atributos de relleno sorteados al azar.
