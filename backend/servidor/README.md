# Motor de simulación

Servidor HTTP que hace responder a los agentes. Cada agente es una persona real de 14 años o más del Censo
2024, con datos de Casen y opiniones de la Encuesta CEP imputados (ver `contexto/chile/README.md`). Cada
agente lleva su comuna con su código INE (`cod_comuna`) y su centro (`contexto/geo/comunas_centroides.csv`); la
interfaz lo dibuja al azar dentro del polígono de su comuna (`frontend/src/datos/comunas.json`, que arma
`scripts/construir_comunas.py`).

    cd backend
    uv run python -m servidor                          # http://127.0.0.1:8787, con la tabla de agentes
    LOTE=20 CONCURRENCIA=50 uv run python -m servidor  # lo que se usa en la demo
    python3 -m servidor                                # sin DuckDB: solo biblioteca estándar y el archivo fijo

## De dónde salen los agentes

De `data/agentes/` (ver `contexto/chile/agentes.md`): 1.546.322 agentes que representan a las 15.463.163
personas de 14 años o más, uno por cada 10. Esa tabla está en el repositorio. En cada consulta, `poblacion.py`:

1. Elige el nivel de clusterización (`reduccion`): un agente por cada 10, 100, 1.000 o 10.000 personas. Los niveles
   vienen marcados en la tabla y son anidados.
2. Filtra con los filtros de la interfaz: el rango de edad y los parámetros de `sociedad.py` (región, género,
   educación, nacionalidad, situación laboral, niños en el hogar, vivienda, previsión de salud, ingreso, posición
   política, aprobación del gobierno, voto en 2025 y confianza en el gobierno). En cada parámetro se pueden elegir
   varias opciones; quien no tiene el dato (los menores de 18 no tienen opinión imputada) queda fuera al filtrar por él.
3. Sortea hasta el máximo pedido entre quienes los cumplen, estratificado por región, comuna y zona (urbana o
   rural). Cada estrato recibe una cuota proporcional a las personas que representan sus agentes filtrados, y
   dentro de él se sortea en proporción a cuántas personas representa cada uno. Las cuotas salen de un
   redondeo controlado (`repartir`): cada comuna, cada región y cada zona, dentro de su región y en el país,
   queda a menos de una persona de su parte exacta. Una muestra de 250 lleva así 101 personas de la
   Metropolitana, el 40 % del país, y 33 de zona rural, el 13 %, y no números que cambien de un sorteo a otro.
4. Arma el perfil de cada elegido con la misma función del banco de pruebas (`scripts/personas_muestra.py`)
   y le deja al agente su fila de la tabla, con la que después se escribe el perfil reducido que lee el modelo.

El sorteo es fijo: los mismos filtros dan siempre las mismas personas, así que la caché de respuestas sirve, y
con los tamaños de la interfaz hasta 2.000 (250, 500, 1.000 y 2.000; también ofrece 5.000 y 10.000, el tope de `MAXIMO_MUESTRA`, que no se midieron) cada muestra queda casi entera (sobre el 95 %) dentro de la
siguiente: lo que cambia son algunas comunas que pesan menos de una persona y entran en una y no en la otra. Filtrar una región y pedir 2.000 entrega 2.000 personas de esa
región, no las pocas que le tocarían en una muestra nacional.

Junto con la muestra va el **retrato** de la población: por parámetro, cuántas personas hay en cada opción entre
quienes cumplen los *demás* filtros (cada parámetro ignora el suyo), y cuántas de cada edad. La interfaz lo dibuja
en cada filtro, para que se vea cuánta gente suma o quita cada opción antes de tocarla.

`sociedad.py` define cada parámetro una sola vez: sus opciones, la expresión SQL que da la opción de cada agente en
la tabla y la función que la saca de un perfil ya escrito (para el archivo fijo). `tests/test_sociedad.py`
comprueba que ambas coincidan. Al partir, la tabla se resume en memoria (`rasgos`: una fila por agente con su
opción en cada parámetro; 0,3 s) y sobre ese resumen se filtra, se sortea y se saca el retrato (unos 20 ms; leerlo
de los archivos tardaba 450 ms). La edad llega hasta 85, que es «85 o más»: el censo la publica con ese tope.

Para que cambiar un filtro se sienta inmediato: solo se leen las columnas que el perfil usa, los agentes ya
armados se guardan (hasta 30.000) y una muestra ya pedida se devuelve sin recalcular. Un cambio de filtro
tarda entre 30 y 300 ms la primera vez y nada si se repite.

Cada agente representa a un grupo de personas parecidas en lo que más pesa en una opinión: primero su tipo
político, después su comuna, sexo y edad. De cada grupo se elige a quien mejor mantiene las proporciones de la
región. Lo hace `scripts/reducir_poblacion.py`; el servidor solo sortea según la columna del nivel elegido. Con
un agente por cada 10.000 personas quedan unos 1.550 en todo el país: un filtro deja pocos, y hay comunas sin
ninguno.

Si falta DuckDB o la tabla, se usan las 2.000 personas de
`data/pruebas/poblacion/al_azar_2000.jsonl`, filtradas en memoria.

## Motores

Se elige solo, en este orden, o con `MOTOR=local|api|claude`. Sin ninguno disponible el servidor no arranca
y lo dice; la interfaz queda entonces en su demostración, que sortea respuestas en el navegador.

| Motor | Cuándo | Velocidad |
|---|---|---|
| Modelo local | `LLAMA_URL` definida (llama-server de `scripts/servir_modelo.sh`). Una persona por llamada. | La del modelo local |
| API de Anthropic | `ANTHROPIC_API_KEY` definida y paquete `anthropic` instalado. Haiku 5.5 sin razonamiento previo. | La más rápida; para el despliegue |
| CLI de Claude Code | `claude` en el PATH con sesión iniciada. Haiku por `claude -p`, un proceso por lote. | 1.000 agentes en unos 30 s con 50 procesos (unos 7 GB de RAM) |

## Cómo responde un agente

El método es el de `scripts/probar_modelo.py`, y no está copiado: `metodo.py` importa de ese script las
instrucciones, las cinco preguntas con su escala (`PREGUNTAS`, `ESCALAS`) y la función que arma los mensajes. Si se cambian allá, el
servidor usa lo nuevo al reiniciar (y la caché se invalida sola).

El perfil general de cada persona son nueve secciones en segunda persona (quién es, educación y trabajo,
hogar, vivienda, situación económica, salud y redes, posición política, cómo ve el país y confianza en
instituciones): 102 datos, unos 1.100 tokens. El modelo no lo lee entero. `scripts/filtro_perfil.py` define
qué datos se le entregan, y `PERFIL` en el entorno elige el nivel:

| `PERFIL` | Qué lee el modelo de cada persona | Tokens |
|---|---|---|
| `tematico` (por defecto) | El núcleo más los datos de los temas que toca el texto de la política (hasta 3 temas, detectados por palabras clave). | 390 a 650 |
| `nucleo` | Los 28 datos que más pesan en una opinión política: quién es, trabajo, hogar, ingreso, posición, voto, evaluación de los gobiernos, rol del Estado y confianza en el gobierno y el Congreso. | unos 390 |
| `completo` | Todo, como antes del filtro. | unos 1.100 |

En Sala Cuna el filtro detecta `trabajo` y `familia-derechos` y entrega 42 datos, unos 515 tokens. El respaldo
de qué entra en cada nivel está en `contexto/delphos/influencia.md`. Los temas detectados viajan en cada caso
de los eventos `inicio` y `caso` (`temas`), y el nivel en `motor.perfil` de `/api/estado`. Con el archivo fijo
de 2.000 personas no hay filtro: esos perfiles vienen ya escritos y van completos.

Los menores de 18 no traen las secciones políticas, porque la CEP entrevista desde esa edad; traen el tipo de
colegio al que van. A la interfaz no viaja el perfil, solo un resumen corto (`atributos`).

Cada persona responde las preguntas de la encuesta con un entero de 1 a 7, sin texto. La interfaz clasifica
con la primera pregunta: 5 a 7 a favor, 4 indecisa, 1 a 3 en contra. El resultado de todas se ve en la
pantalla de resultados, y las notas de cada persona en su ficha.

### La encuesta es fija

Son cinco preguntas, las mismas en cada corrida. Cada una tiene su escala, y el modelo la lee al lado de la
pregunta («(1 = muy injusto, 7 = muy justo)»):

| Clave | Nombre | Pregunta | 1 | 7 |
|---|---|---|---|---|
| p1 | Apoyo | ¿Estarías de acuerdo con que se implemente esta política en tu región? | totalmente en desacuerdo | totalmente de acuerdo |
| p2 | Justicia | ¿Te parece justa la forma en que esta política reparte costos y beneficios? | muy injusto | muy justo |
| p3 | Confianza | ¿Confías en que el Estado chileno sea capaz de implementar bien esta política? | muy desconfiado | muy confiado |
| p4 | Efectividad | ¿Qué tan efectiva crees que es esta política en lograr lo que propone? | muy inefectivo | muy efectivo |
| p5 | Influencia | ¿Qué tan influyente es esta política en tu situación personal o la de tu hogar? | nada influyente | muy influyente |

- Están en `ENCUESTA` de `scripts/probar_modelo.py` y, para la interfaz, en `frontend/src/vivo/encuesta.ts`: si
  se cambian, hay que cambiarlas en los dos lugares. `GET /api/estado` entrega `preguntas`, `nombres` y `escalas`.
- La primera decide la postura de la persona y es la que se compara con Cadem. El índice de aceptación es la
  media de p1 a p4. Influencia no mide apoyo: la interfaz la muestra en tono neutro.
- `POST /api/corridas` no acepta otras preguntas: si el pedido trae `preguntas`, no se usan.
- La encuesta entra en el mensaje de sistema (`metodo.sistema_con_politica`) y en la clave de la caché
  (`Motor.clave`): si cambia una pregunta o una escala, lo ya respondido no se reutiliza.

Diferencias con el banco de pruebas, a propósito:

- **Lotes.** Con Claude van `LOTE` personas por llamada (20 en la demo), como en las pruebas con subagentes.
  `INSTRUCCION_LOTE` en `motor.py` es lo único que se agrega a las instrucciones: que vienen varias personas y
  que se respondan por separado. `LOTE=1` pregunta de a una. Un lote de 20 son unos 9.000 tokens de entrada
  con el perfil temático (7.000 con el núcleo, 20.000 con el completo).
- **Sin pregunta de control con Claude.** El banco parte la encuesta con una pregunta de control porque, en el
  modelo local, la primera respuesta casi no depende del perfil. Con Claude sí depende, así que no se usa.
- **Modelo local.** Con `LLAMA_URL=http://127.0.0.1:8080` el servidor usa llama-server con la misma función
  `encuestar` del script: una persona por llamada, con su gramática y su pregunta de control. Es el método del
  banco sin cambios, salvo que el perfil va filtrado igual que con Claude. El perfil completo necesita unos
  2.560 tokens de contexto por slot; con el filtro el prompt es menos de la mitad, pero la velocidad con el
  perfil reducido todavía no se ha medido.
- **Las respuestas de un lote no son independientes.** En las pruebas, el promedio de un mismo texto cambió
  unos 0,16 puntos (en la escala de 1 a 7) de un lote a otro. Para comparar variantes con rigor, el banco
  hace que el mismo subagente conteste todas (`scripts/lotes_agentes.py --juntas`); el servidor pregunta cada
  variante por separado, que es más rápido y sirve para la demo.

## Frases, iteraciones y documentos

- **Frases.** No son parte de la encuesta. Después de que un lote responde, a dos de sus personas se les pide,
  en una llamada aparte, la frase con que explicarían lo que ya respondieron (`SISTEMA_VOCES`). Las notas no
  se tocan. Llegan a la interfaz como evento `voces`. Con el modelo local no hay frases.
- **Iteraciones.** Al terminar las variantes escritas, un agente (Sonnet) toma la variante con más apoyo, las
  medias de las cinco preguntas (con su escala) y las frases disponibles, y redacta una versión nueva con un título corto y
  qué cambió. Se pregunta a los mismos agentes con el mismo método.
- **Documentos.** Un documento subido (`.txt`, `.md`, `.html`, `.docx` o `.pdf` con `pdftotext`) se lee entero;
  si pasa de 3.500 caracteres, Sonnet lo resume en unas 220 palabras y eso es lo que leen los agentes.

## Validación

Sin calibrar. Con el método anterior y 200 agentes, la rebaja del TAG dio 32 % a favor contra 55 % en Cadem
(octubre de 2026); con el perfil general todavía no se ha repetido. En Sala Cuna, con el perfil con opiniones
de la CEP, Haiku dio 55 % de acuerdo contra 72 a 74 % en Cadem y Criteria: trata la medida como de izquierda
(97 % de acuerdo en la izquierda y 17 % en la derecha). La interfaz muestra la comparación tal cual sale.

`datos-pruebas/`, en la raíz, tiene 140 casos con encuesta real publicada para ampliar esta comparación, y
`data/pruebas/sala_cuna/benchmarks.json` las cifras de Sala Cuna que usa `scripts/comparar_variantes.py`.

## Perfil filtrado contra perfil completo

`scripts/comparar_perfiles.py` pregunta a las mismas personas con el perfil completo, otra vez con el completo
(la repetición dice cuánto cambian las respuestas sin cambiar nada) y con el temático. En Sala Cuna, con Haiku y
200 personas (`data/pruebas/sala_cuna/resultados_ab_perfil_haiku.jsonl`, 21-11-2026):

- El índice de aceptación de cada texto no cambia más que al repetir la corrida (diferencias de -0,01 a +0,12,
  con intervalos que incluyen el cero), y el acuerdo con la iniciativa queda igual de lejos de las encuestas
  reales: 63 a 65 % contra 72 a 74 %.
- Las diferencias por posición política y por niños en el hogar se mantienen. La diferencia por edad pareció
  achicarse (entre los de 18 a 29 y los de 60 o más, de 0,41 a 0,26 puntos), pero la segunda corrida, más abajo,
  no lo repite.
- No es equivalente pregunta a pregunta (con la encuesta de entonces, de seis preguntas): p5 (cumpliría) baja 0,17, p6 (logrará lo que se propone) sube 0,13 y
  p4 (confianza en el Estado) sube 0,09; al repetir el completo, ninguna se mueve más de 0,03.
- Persona a persona, el índice con el temático se correlaciona 0,71 con el del completo; el completo consigo
  mismo, 0,78.
- Las variantes A a E difieren entre sí 0,10 puntos, lo mismo que el ruido: E queda primera y B última en las
  tres corridas, y el orden del medio cambia incluso entre las dos del perfil completo. Para ordenar variantes
  sigue haciendo falta el método del banco (`--juntas`).
- Los tokens de entrada por persona bajan de 1.715 a 856 y cada llamada tarda 17 s en vez de 20. El costo que
  informa la CLI no bajó (unos 0,30 dólares por 60 llamadas en ambos casos).

Es un caso y un modelo: no dice qué pasa en otros temas ni con el modelo local.

Para saber qué datos explican esos cambios se hizo una segunda corrida con el método del banco (40 subagentes
Haiku, lotes de 50, variante A): las mismas 400 personas con cinco recortes del perfil: completo, temático,
temático más inmigración y origen, temático más orden y Estado (`justifica_marchas`, `justifica_fuerza`,
`libertades_seguridad`, `menos_estado`, `estado_burocracia`) y temático más ambos grupos. Está en
`data/pruebas/sala_cuna/resultados_atribucion_perfil_haiku.jsonl`. Todo se mide dentro de cada lote, porque
cada lote lo contesta un subagente distinto y sus niveles no son comparables (entre lotes, el índice varía 0,2).

- **Edad e índice: no hay un efecto estable.** Por cada 10 años el índice baja 0,09 con el completo y 0,11 con
  el temático, al revés que en la primera corrida (0,09 y 0,06). Ninguna de las dos diferencias se distingue
  del ruido.
- **Edad y p5: sí.** Con el temático los mayores bajan más en «la cumplirías»: -0,20 por cada 10 años contra
  -0,05 con el completo (en la primera corrida, -0,15 contra -0,11). No lo explica un dato: inmigración y
  origen recuperan la mitad, orden y Estado algo menos, y los dos juntos cerca del 60 %.
- **`menos_estado`.** Quienes quieren menos Estado en la economía quedan 0,47 puntos bajo el resto con el
  perfil completo y solo 0,22 con el temático; al agregar el grupo de orden y Estado vuelven a 0,47. Es el
  cambio más claro y repetido en las dos corridas. Por eso `menos_estado` pasó al núcleo; las dos corridas de
  esta sección son anteriores (núcleo de 27 datos) y con el núcleo nuevo no se ha vuelto a medir.
- **Opiniones sobre inmigración.** Agregarlas al perfil corto pesa más que en el completo: quienes quieren
  restringirla quedan 0,56 bajo el resto, contra 0,43 con el completo y 0,35 con el temático.

## Caché

`data/cache/respuestas.jsonl` guarda las cinco notas (y la frase, si la tiene) por política, agente, modelo y versión de las instrucciones
y del filtro del perfil. Repetir una pregunta no vuelve a gastar y llega en segundos (la interfaz igual la muestra encenderse). Cambiar
las instrucciones, el nivel de `PERFIL` o la definición del filtro invalida la caché sola; las respuestas guardadas antes del filtro
se dieron con el perfil completo y se reutilizan solo con `PERFIL=completo`. `data/` no se versiona.

## Rutas

    GET  /api/estado                  motor, modelo, población disponible y la encuesta: preguntas, nombres y escalas
    POST /api/muestra                 {filtros, tamano}: filtra la población y sortea. `filtros` trae edadMin,
                                      edadMax, reduccion (10, 100, 1000 o 10000: el nivel de clusterización) y, por
                                      parámetro de `sociedad.py`, la lista de opciones elegidas: {"region": [5, 6],
                                      "voto": [1]}. Devuelve id, cuántos cumplen los filtros, a cuántas personas
                                      representan, el retrato, `dimensiones` (el orden de los parámetros) y los
                                      agentes elegidos, cada uno con `s`: su opción en cada parámetro
    GET  /api/agentes                 la muestra sin filtros, como lista (por compatibilidad)
    GET  /api/historial               las últimas 100 simulaciones, de la más nueva a la más antigua: hora, agentes,
                                      modelo y, por variante, el texto y cuántos quedaron a favor, en contra y sin decidir
    POST /api/documentos              cuerpo: el archivo; cabecera X-Nombre
    POST /api/corridas                {casos:[{id,letra,texto,documento?}], muestra:id, agentes?:[índices], iteraciones}.
                                      El evento `inicio` devuelve las preguntas con que corre
    GET  /api/corridas/<id>/eventos   text/event-stream
    POST /api/corridas/<id>/cancelar
