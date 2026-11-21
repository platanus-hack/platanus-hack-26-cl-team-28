# Motor de simulación

Servidor HTTP que hace responder a los agentes. Cada agente es una persona de la muestra del 1 % del Censo 2024
(con datos de Casen imputados, ver `contexto/muestra/README.md`); hoy se usan las 2.000 de
`data/pruebas/sala_cuna/personas_2000.jsonl`, ubicadas en el centro de su comuna
(`contexto/geo/comunas_centroides.csv`).

    cd backend
    python3 -m servidor                          # http://127.0.0.1:8787, solo biblioteca estándar
    LOTE=20 CONCURRENCIA=50 python3 -m servidor  # lo que se usa en la demo: 1.000 agentes en unos 30 s

## Motores

Se elige solo, en este orden, o con `MOTOR=local|api|claude|grabado`:

| Motor | Cuándo | Velocidad |
|---|---|---|
| Modelo local | `LLAMA_URL` definida (llama-server de `scripts/servir_modelo.sh`). Una persona por llamada. | La del modelo local |
| API de Anthropic | `ANTHROPIC_API_KEY` definida y paquete `anthropic` instalado. Haiku 5.5 sin razonamiento previo. | La más rápida; para el despliegue |
| CLI de Claude Code | `claude` en el PATH con sesión iniciada. Haiku por `claude -p`, un proceso por lote. | 1.000 agentes en unos 30 s con 50 procesos (unos 7 GB de RAM) |
| Corrida grabada | Sin red ni credenciales. Repite respuestas reales de Haiku 5.5 a la política de sala cuna. | Inmediata; se rotula "Corrida grabada" |

## Cómo responde un agente

El método es el de `scripts/probar_modelo.py`, y no está copiado: `metodo.py` importa de ese script las
instrucciones (`SISTEMA`), las cinco preguntas (`PREGUNTAS`) y el formato del perfil. Si se cambian allá, el
servidor usa lo nuevo al reiniciar (y la caché se invalida sola).

Cada persona responde las cinco preguntas con un entero de 1 a 7, sin texto. La interfaz clasifica con la
primera pregunta ("¿Estarías de acuerdo con que se implemente esta política en tu región?"): 5 a 7 a favor,
4 indecisa, 1 a 3 en contra. Las otras cuatro se ven en la ficha de cada persona.

Diferencias con el banco de pruebas, a propósito:

- **Lotes.** Con Claude van `LOTE` personas por llamada (20 en la demo), como en las pruebas con subagentes
  (`resultados_haiku55_2000_20x100`). `INSTRUCCION_LOTE` en `motor.py` es lo único que se agrega a las
  instrucciones: que vienen varias personas y que se respondan por separado. `LOTE=1` pregunta de a una.
- **Modelo local.** Con `LLAMA_URL=http://127.0.0.1:8080` el servidor usa llama-server con la misma función
  `encuestar` del script: una persona por llamada, con su gramática. Es el método del banco sin cambios.

## Frases, iteraciones y documentos

- **Frases.** No son parte de la encuesta. Después de que un lote responde, a dos de sus personas se les pide,
  en una llamada aparte, la frase con que explicarían lo que ya respondieron (`SISTEMA_VOCES`). Las notas no
  se tocan. Llegan a la interfaz como evento `voces`. Con el modelo local no hay frases.
- **Iteraciones.** Al terminar las variantes escritas, un agente (Sonnet) toma la variante con más apoyo, las
  medias de las cinco preguntas y las frases disponibles, y redacta una versión nueva con un título corto y
  qué cambió. Se pregunta a los mismos agentes con el mismo método.
- **Documentos.** Un documento subido (`.txt`, `.md`, `.html`, `.docx` o `.pdf` con `pdftotext`) se lee entero;
  si pasa de 3.500 caracteres, Sonnet lo resume en unas 220 palabras y eso es lo que leen los agentes.

## Validación

Sin calibrar. Con estas instrucciones y 200 agentes, la rebaja del TAG dio 32 % a favor contra 55 % en Cadem
(octubre de 2026). La interfaz muestra la comparación tal cual sale.

## Caché

`data/cache/respuestas.jsonl` guarda las cinco notas (y la frase, si la tiene) por política, agente, modelo y versión de las instrucciones.
Repetir una pregunta no vuelve a gastar y llega en segundos (la interfaz igual la muestra encenderse). Cambiar
las instrucciones invalida la caché sola. `data/` no se versiona.

## Rutas

    GET  /api/estado                  motor, modelo, cuántos agentes hay y las preguntas de la encuesta
    GET  /api/agentes                 perfil y ubicación de cada agente
    POST /api/documentos              cuerpo: el archivo; cabecera X-Nombre
    POST /api/corridas                {casos:[{id,letra,texto,documento?}], agentes:[índices], iteraciones}
    GET  /api/corridas/<id>/eventos   text/event-stream
    POST /api/corridas/<id>/cancelar
