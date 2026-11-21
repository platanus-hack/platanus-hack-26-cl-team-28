# Validación contra el banco de encuestas reales

Corridas del 21-11-2026 con `scripts/validar_banco.py`. Cada caso de `../../../../datos-pruebas/` es una pregunta de encuesta real con su porcentaje publicado. Aquí se le hace la misma pregunta a una muestra nacional de agentes adultos (la del sitio, sin filtros, desde los 18 años) con Claude por la CLI en lotes de 20, y se compara el porcentaje de acuerdo.

De los 140 casos del banco, 120 son comparables: de acuerdo o percepción, a población general, con porcentaje de acuerdo publicado. Se parten por familia en 78 de desarrollo (para iterar) y 42 de prueba (se miraron al final, solo con los métodos ya elegidos).

## Resultado

Error absoluto medio en puntos porcentuales entre el acuerdo simulado y el publicado. Agentes: Haiku, 100 por caso, salvo que se indique.

| Método | Desarrollo (78) | Prueba (42) | Mayoría del mismo lado, prueba |
|---|---|---|---|
| `sitio`: lo que hace hoy el motor (nota de 1 a 7, seis preguntas) | 17,9 | 16,3 | 55 % |
| Responder siempre 60 % | 15,9 | 16,1 | 64 % |
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

1. **El método actual no le gana a una constante.** Deja entre 10 y 40 % de notas 4 donde las encuestas tienen 3 a 6 % de «no sabe», y aplasta todo hacia el centro.
2. **Pedir probabilidades baja el error cerca de un tercio.** En vez de una nota de 1 a 7, el modelo estima la probabilidad de que la persona responda «de acuerdo» y la de «en desacuerdo». El porcentaje nacional es el promedio; la postura de cada agente se sortea con esas probabilidades. Además es estable: al repetir, 91 % de los agentes queda del mismo lado y el porcentaje de un caso cambia 2 puntos en promedio.
3. **Con un mismo modelo hay un techo, y no depende de cómo se pregunte.** Con Haiku, todas las variantes de probabilidades quedan entre 11 y 13 puntos y el pronóstico directo sin agentes llega a 10,7. No ayudó dar referencias reales, ni una nota de clima, ni promediar métodos, ni corregir a posteriori con una recta, por área, por tipo de pregunta o por fuente.
4. **Lo que sí rompe el techo es un modelo más grande.** Opus baja a 8,7 y 9,1 como pronóstico directo y a 9,3 como agente. Su error es parejo entre encuestas de 2022 y de octubre y noviembre de 2026 (8,0 a 8,4), así que no parece venir de recordar los resultados.
5. **Las noticias empeoran.** Una nota de 100 a 140 palabras escrita por Sonnet con búsqueda web (qué se propone, quién lo impulsa, a quién beneficia y a quién le cuesta, sin encuestas ni porcentajes) sube el error de 12,0 a 13,8, también en los casos de 2026. Las notas equilibran argumentos a favor y en contra y empujan las respuestas hacia el centro.
6. **Más o menos perfil no cambia el número nacional, pero sí el parecido persona a persona.** En cinco preguntas de la CEP el agente trae la respuesta real de su donante de la encuesta; ocultándola y pidiendo al modelo que la prediga (`individual`, 500 agentes), con las actitudes de la CEP en el perfil el modelo ordena bien a las personas (AUC 0,70) y con solo censo y Casen queda en azar (AUC 0,52). El nivel sale mal en los tres casos: el modelo pone a todos cerca de 45 a 50 %.
7. **El error está concentrado.** Con `probabilidad`, en casos con apoyo real de 40 a 70 % el error es de 7 puntos; sobre 85 % es de 22. Por tipo de pregunta (`rasgos`), las declaraciones de principios («es deber del Estado proteger la naturaleza») tienen sesgo de −19; beneficios y restricciones concretas, de −4 a −7. Por fecha: 18 puntos hasta 2023, 7 en 2025 y 9 en 2026.
8. **Más agentes no acercan a la encuesta.** Con `probabilidad` y 1.000 agentes por caso (`curva`), el error es 13,2 con 10 agentes, 12,3 con 100 y 12,2 con 200, 500 y 1.000. Desde 200 agentes el resultado nacional queda a menos de 1 punto del de 1.000.
9. **Lo que los agentes aportan son los cortes.** En 30 cortes publicados por edad, sexo y grupo socioeconómico (`segmentos`, 1.000 agentes), la diferencia de cada segmento con el total se correlaciona 0,81 con la real y va en la misma dirección en 86 % de los cortes que se alejan 3 puntos o más. La simulación mueve los segmentos menos que la realidad: 5,2 puntos en promedio contra 7,1.

## Qué se recomienda

**Ancla más agentes.** Un modelo grande estima el total nacional con una llamada (error de 9 puntos, sin sesgo) y los agentes de Haiku, con las actitudes de la CEP en el perfil y respondiendo con probabilidades, reparten ese total entre personas y grupos. `anclar()` suma a todos la misma constante en escala logit hasta que el promedio coincide con el ancla: el orden entre personas y las diferencias entre grupos no cambian (`segmentos probabilidad --ancla pronostico_opus` da la misma correlación de 0,81).

Lo que se puede afirmar con estos datos: el total nacional queda a unos 9 puntos de una encuesta real en preguntas que el sistema no había visto, del mismo lado de la mayoría en 88 % de los casos; los grupos se mueven en la dirección correcta en 86 % de los cortes; y la postura individual es estable (91 %) y ordena a las personas mejor que el azar (AUC 0,70).

## Lo que dice la literatura

El techo medido coincide con el estado del arte: Pew (septiembre de 2026), con gemelos digitales de panelistas reales, reporta 11,4 puntos de error con su mejor modelo, 16,0 con el perfil estándar y 13,7 al agregar actitudes reales del mismo panelista. Otros resultados que calzan con lo medido aquí:

- Pedir la distribución le gana al rol individual (Meister et al. 2025; Gong, Sanders y Schneier 2026), y la distribución directa subestima los consensos.
- Las actitudes previas del individuo mejoran la predicción más que la demografía (Hwang et al. 2023; Park et al. 2024).
- Razonar antes de responder no ayuda (Pew 2026; Gong et al. 2026).
- No hay evidencia publicada de que pasar noticias a los agentes mejore la predicción de encuestas.
- Con unas 100 respuestas humanas reales se puede corregir el sesgo de una simulación hasta dejarlo bajo 5,5 % (Krsteski et al. 2025): es el camino para dar garantías estadísticas.
- En Chile, González-Bustamante, Verelst y Cisternas (2025) probaron respuestas sintéticas contra la CEP 92.

Enlaces: Pew https://www.pewresearch.org/data-labs/2026/09/30/methodology-silicon-samples/ · Meister https://arxiv.org/abs/2411.05403 · Gong https://arxiv.org/html/2603.20229v1 · Hwang https://arxiv.org/abs/2305.14929 · Park https://arxiv.org/abs/2411.10109 · Krsteski https://arxiv.org/html/2510.11408v2 · González-Bustamante https://arxiv.org/abs/2509.09871

## Límites

- Los agentes se probaron con Haiku en todos los casos y con Sonnet y Opus solo en 26.
- Opus como agente cuesta unas 35 veces más por llamada que Haiku según la CLI.
- El parecido persona a persona se midió en cinco preguntas, todas de la CEP y contra respuestas imputadas desde un donante, no contra la persona del censo.
- El grupo socioeconómico de los cortes se aproximó con el quintil de ingreso imputado. Los cortes publicados son de cuatro preguntas, tres de ellas sobre roles familiares.
- Las encuestas van de 2014 a 2026 y los perfiles de los agentes describen 2026.
- `c704-bloqueo` (64 % de acuerdo con que los camioneros puedan bloquear carreteras) parece mal transcrito: todos los métodos dan entre 1 y 26 %. Hay que revisarlo contra la fuente. Las cifras de la tabla lo incluyen; `agudizar` y las referencias lo dejan fuera.
- Las respuestas de un lote no son independientes y, salvo `probabilidad`, cada caso se preguntó una sola vez por método.
- Dos de las 78 notas de noticias traen una frase del modelo sobre una instrucción que venía en los resultados de búsqueda.

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
