# Validación contra el banco de encuestas reales

Corridas del 21-11-2026 con `scripts/validar_banco.py`. Cada caso de `../../../../datos-pruebas/` es una pregunta de encuesta real con su porcentaje publicado. Aquí se le hace la misma pregunta a una muestra nacional de agentes adultos (la del sitio, sin filtros, desde los 18 años) con Claude Haiku por la CLI en lotes de 20, y se compara el porcentaje de acuerdo.

De los 140 casos del banco, 120 son comparables: de acuerdo o percepción, a población general, con porcentaje de acuerdo publicado. Se parten por familia en 78 de desarrollo (para iterar) y 42 de prueba (se miraron una sola vez, al final).

## Resultado

Error absoluto medio en puntos porcentuales entre el acuerdo simulado y el publicado, con 100 agentes por caso.

| Método | Desarrollo (78) | Prueba (42) | Mayoría del mismo lado, prueba |
|---|---|---|---|
| `sitio`: lo que hace hoy el motor | 17,9 | 16,3 | 55 % |
| Responder siempre 60 % | 15,9 | 16,1 | 64 % |
| `directa`: una sola pregunta | 16,6 | | |
| `encuestado`: instrucciones nuevas, seis preguntas | 17,4 | | |
| `directa_encuestado` | 14,3 | | |
| `probabilidad`: probabilidades en vez de nota | 12,0 | 11,4 | 81 % |
| `probabilidad` con el «no sabe» a la mitad (`agudizar --k 1 --g 0.5`) | 11,0 | 10,9 | 83 % |
| `prob_encuestado` | 11,9 | 13,1 | 81 % |
| `prob_clima`: con una nota previa de cómo se ve el tema | 11,9 | | |
| `prob_referencias`: con diez resultados reales de otras preguntas | 11,9 | | |
| Pronóstico directo de Haiku, sin agentes | 10,7 | 10,6 | 83 % |
| Pronóstico directo de Sonnet, sin agentes | 11,1 | | |

El piso de ruido, lo que erraría una simulación perfecta con 100 agentes contra una encuesta de 700 casos, es de 3,7 puntos.

## Qué se aprendió

1. **El método actual no le gana a una constante.** Deja entre 10 y 40 % de notas 4 donde las encuestas tienen 3 a 6 % de «no sabe», y aplasta todo hacia el centro: casi nada pasa de 80 % de acuerdo aunque la encuesta real dé 95.
2. **Pedir probabilidades baja el error cerca de un tercio.** En vez de una nota de 1 a 7, el modelo estima la probabilidad de que la persona responda «de acuerdo» y la de «en desacuerdo». El porcentaje nacional es el promedio; la postura de cada agente se sortea con esas probabilidades.
3. **Hay un techo cerca de 11 puntos y no depende de cómo se pregunte.** Las cuatro variantes de probabilidades empatan, un modelo solo estimando el porcentaje nacional sin agentes llega al mismo lugar, y promediar métodos no mejora. Tampoco ayudó dar referencias reales ni corregir a posteriori con una recta. El límite es lo que el modelo sabe de la opinión chilena.
4. **El error está concentrado.** Con `probabilidad`, en casos con apoyo real de 40 a 70 % el error es de 7 puntos; sobre 85 % es de 22. Las enmiendas constitucionales de 2023 y las preguntas ambientales de 2017 y 2018 concentran el error grande; en medidas de 2025 y 2026 el error es de 6 a 7. En la prueba aparece además que subestima el apoyo a temas valóricos liberales (matrimonio igualitario: 77 real, 52 simulado).
5. **Más agentes no acercan a la encuesta.** Con `probabilidad` y 1.000 agentes por caso (`curva`), el error es 13,2 con 10 agentes, 12,3 con 100 y 12,2 con 200, 500 y 1.000. Lo que domina es el sesgo del método. Desde 200 agentes el resultado nacional queda a menos de 1 punto del de 1.000.
6. **Lo que los agentes sí aportan son los cortes.** En 30 cortes publicados por edad, sexo y grupo socioeconómico (`segmentos`, 1.000 agentes), la diferencia de cada segmento con el total se correlaciona 0,81 con la real y va en la misma dirección en 86 % de los cortes que se alejan 3 puntos o más. La simulación mueve los segmentos menos que la realidad: 5,2 puntos en promedio contra 7,1.

## Límites

- Un solo modelo (Haiku) para los agentes. El pronóstico directo de Sonnet no fue mejor que el de Haiku.
- El grupo socioeconómico de los cortes se aproximó con el quintil de ingreso imputado.
- Las encuestas van de 2014 a 2026 y los perfiles de los agentes describen 2026.
- `c704-bloqueo` (64 % de acuerdo con que los camioneros puedan bloquear carreteras) parece mal transcrito: todos los métodos dan entre 1 y 26 %. Hay que revisarlo contra la fuente. Las cifras de la tabla lo incluyen; `agudizar` lo deja fuera.
- Las respuestas de un lote no son independientes y cada caso se preguntó una sola vez por método.

## Cómo repetir

```sh
uv run python scripts/validar_banco.py casos
uv run python scripts/validar_banco.py correr probabilidad --parte desarrollo --personas 100
uv run python scripts/validar_banco.py informe sitio probabilidad --parte prueba --personas 100 --detalle
uv run python scripts/validar_banco.py agudizar probabilidad --parte prueba --k 1 --g 0.5
uv run python scripts/validar_banco.py curva probabilidad
uv run python scripts/validar_banco.py segmentos probabilidad
uv run python scripts/validar_banco.py pronostico --modelo haiku --parte prueba
```

`correr` gasta: una llamada por lote y caso. La corrida de 1.000 agentes en 78 casos fueron unas 3.700 llamadas. Lo ya respondido no se vuelve a preguntar. Los métodos están en `scripts/metodos_banco.py`.
