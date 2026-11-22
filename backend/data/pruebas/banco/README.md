# Validación contra el banco de encuestas reales

Este banco es el que permitió elegir el método del motor actual. Sus resultados finales, con las 164 preguntas y el error del motor en las reservadas para validar, están en [VALIDACION.md](../../../../VALIDACION.md).

Corridas del 21-11-2026 con `scripts/validar_banco.py`. Cada caso de `../../../../datos-pruebas/` es una pregunta de encuesta real con su porcentaje publicado. Aquí se le hace la misma pregunta a una muestra nacional de agentes adultos (la del sitio, sin filtros, desde los 18 años) con Claude por la CLI en lotes de 20, y se compara el porcentaje de acuerdo.

El banco tiene 140 casos; con los 4 que se agregaron aparte (plebiscitos y paneles) y las 40 preguntas del benchmark de políticas suman las 164 preguntas con resultado publicado. De los 140 casos, 120 son comparables: de acuerdo o percepción, a población general, con porcentaje de acuerdo publicado. Se parten por familia en 78 de desarrollo (para iterar) y 42 de prueba (se miraron al final, solo con los métodos ya elegidos).

## Resultado

Error absoluto medio en puntos porcentuales entre el acuerdo simulado y el publicado. Agentes: Haiku, 100 por caso, salvo que se indique.

| Método | Desarrollo (78) | Prueba (42) | Mayoría del mismo lado, prueba |
|---|---|---|---|
| `sitio`: el método inicial del motor (nota de 1 a 7, seis preguntas) | 17,9 | 16,3 | 55 % |
| `directa`: una sola pregunta | 16,6 | | |
| `encuestado`: instrucciones nuevas, seis preguntas | 17,4 | | |
| `directa_encuestado` | 14,3 | | |
| `probabilidad`: probabilidades en vez de nota | 12,0 | 11,4 | 81 % |
| `probabilidad` otra vez (`probabilidad_b`) | 12,3 | | |
| `probabilidad` con el «no sabe» a la mitad (`agudizar --k 1 --g 0.5`) | 11,0 | 10,9 | 83 % |
| `prob_encuestado` | 11,9 | 13,1 | 81 % |
| `prob_clima`: con una nota previa de cómo se ve el tema | 11,9 | | |
| `prob_referencias`: con diez resultados reales de otras preguntas | 11,9 | | |
| `prob_noticias`: con una nota de noticias buscada en la web | 13,8 | | |
| `prob_completo`, `prob_nucleo`, `prob_demografia`: más o menos perfil | 12,8, 12,7 y 12,6 | | |
| Pronóstico directo de Haiku, sin agentes | 10,7 | 10,6 | 83 % |
| Pronóstico directo de Sonnet, sin agentes | 11,1 | | |
| Pronóstico directo de Opus, sin agentes | 8,7 | 9,1 | 88 % |

En un subconjunto de 26 casos de desarrollo (`subconjunto.txt`), con otro modelo respondiendo por los agentes: Haiku 13,7, Sonnet 11,7 y Opus 9,3.

El piso de ruido, lo que erraría una simulación perfecta con 100 agentes contra una encuesta de 700 casos, es de 3,7 puntos.

## Qué se aprendió

1. **Pedir probabilidades en vez de una nota mejora el error cerca de un tercio**, y es estable: al repetir, 91 % de los agentes queda del mismo lado.
2. **Un modelo grande estima muy bien el nivel nacional**: Opus queda a 8,7 y 9,1 puntos, parejo entre encuestas de 2022 y de 2026.
3. **Las actitudes de la CEP en el perfil permiten ordenar a las personas**: con ellas el modelo distingue quién está de acuerdo aun cuando se le oculta la respuesta real (AUC 0,70).
4. **Los agentes reproducen las diferencias entre grupos**: en 30 cortes publicados por edad, sexo y grupo socioeconómico, la diferencia de cada segmento con el total se correlaciona 0,81 con la real y va en la misma dirección en 86 % de los cortes.
5. **Desde 200 agentes el resultado nacional es estable**: con el método de probabilidades queda a menos de 1 punto del de 1.000 (con el motor integrado, a 2,3 puntos; ver `../realidad_1000/INFORME.md`).

## Qué se recomienda

**Ancla más agentes.** Un modelo grande estima el total nacional con una llamada (error de unos 9 puntos en esta etapa, sin sesgo) y los agentes de Haiku, con las actitudes de la CEP en el perfil y respondiendo con probabilidades, reparten ese total entre personas y grupos. `anclar()` suma a todos la misma constante en escala logit hasta que el promedio coincide con el ancla: el orden entre personas y las diferencias entre grupos no cambian (`segmentos probabilidad --ancla pronostico_opus` da la misma correlación de 0,81).

Lo que se podía afirmar en esta etapa (el resultado final del motor integrado, 8,2 puntos en 82 preguntas reservadas, está en VALIDACION.md): el total nacional queda a unos 9 puntos de una encuesta real en preguntas que el sistema no había visto, del mismo lado de la mayoría en 88 % de los casos; los grupos se mueven en la dirección correcta en 86 % de los cortes; y la postura individual es estable (91 %) y ordena a las personas mejor que el azar (AUC 0,70).

## Lo que dice la literatura

Los resultados están en línea con el estado del arte: Pew (septiembre de 2026), con gemelos digitales de panelistas reales, reporta 11,4 puntos de error con su mejor modelo, 16,0 con el perfil estándar y 13,7 al agregar actitudes reales del mismo panelista. Otros resultados que calzan con lo medido aquí:

- Pedir la distribución le gana al rol individual (Meister et al. 2025; Gong, Sanders y Schneier 2026), y la distribución directa subestima los consensos.
- Las actitudes previas del individuo mejoran la predicción más que la demografía (Hwang et al. 2023; Park et al. 2024).
- Razonar antes de responder no ayuda (Pew 2026; Gong et al. 2026).
- No hay evidencia publicada de que pasar noticias a los agentes mejore la predicción de encuestas.
- Con unas 100 respuestas humanas reales se puede corregir el sesgo de una simulación hasta dejarlo bajo 5,5 % (Krsteski et al. 2025): es el camino para dar garantías estadísticas.
- En Chile, González-Bustamante, Verelst y Cisternas (2025) probaron respuestas sintéticas contra la CEP 92.

Enlaces: Pew https://www.pewresearch.org/data-labs/2026/09/30/methodology-silicon-samples/ · Meister https://arxiv.org/abs/2411.05403 · Gong https://arxiv.org/html/2603.20229v1 · Hwang https://arxiv.org/abs/2305.14929 · Park https://arxiv.org/abs/2411.10109 · Krsteski https://arxiv.org/html/2510.11408v2 · González-Bustamante https://arxiv.org/abs/2509.09871

## Cómo repetir

```sh
uv run python scripts/validar_banco.py casos
uv run python scripts/validar_banco.py correr probabilidad --parte desarrollo --personas 100
uv run python scripts/validar_banco.py informe sitio probabilidad pronostico_opus --parte prueba --personas 100 --detalle
uv run python scripts/validar_banco.py agudizar probabilidad --parte prueba --k 1 --g 0.5
uv run python scripts/validar_banco.py curva probabilidad
uv run python scripts/validar_banco.py segmentos probabilidad --ancla pronostico_opus
uv run python scripts/validar_banco.py individual oculto_completo oculto_tematico oculto_demografia
uv run python scripts/validar_banco.py pronostico --modelo opus --parte todo
uv run python scripts/validar_banco.py noticias --modelo sonnet --parte desarrollo
```

`correr` gasta: una llamada por lote y caso. Lo ya respondido no se vuelve a preguntar. Los métodos están en `scripts/metodos_banco.py`.
