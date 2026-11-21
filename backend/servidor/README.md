# Motor de simulación

Servidor HTTP que hace responder a los agentes. Cada agente es una persona de la muestra del 1 % del Censo 2024
(con datos de Casen imputados, ver `contexto/muestra/README.md`); hoy se usan las 2.000 de
`data/pruebas/sala_cuna/personas_2000.jsonl`, ubicadas en el centro de su comuna
(`contexto/geo/comunas_centroides.csv`).

    cd backend
    python3 -m servidor                          # http://127.0.0.1:8787, solo biblioteca estándar
    LOTE=20 CONCURRENCIA=50 python3 -m servidor  # lo que se usa en la demo: 1.000 agentes en unos 30 s

## Motores

Se elige solo, en este orden, o con `MOTOR=api|claude|grabado`:

| Motor | Cuándo | Velocidad |
|---|---|---|
| API de Anthropic | `ANTHROPIC_API_KEY` definida y paquete `anthropic` instalado. Haiku 5.5 sin razonamiento previo. | La más rápida; para el despliegue |
| CLI de Claude Code | `claude` en el PATH con sesión iniciada. Haiku por `claude -p`, un proceso por lote. | 1.000 agentes en unos 30 s con 50 procesos (unos 7 GB de RAM) |
| Corrida grabada | Sin red ni credenciales. Repite respuestas reales de Haiku 5.5 a la política de sala cuna. | Inmediata; se rotula "Corrida grabada" |

## Cómo responde un agente

Se le pasan lotes de `LOTE` perfiles con la política (`motor.py`, `SISTEMA` e `INSTRUCCION_LOTE`). Por cada
persona devuelve su acuerdo de 1 a 7 y una frase en primera persona. Las instrucciones se calibraron con tres
encuestas Cadem de octubre y noviembre de 2026 (`frontend/src/vivo/validacion.ts`): con 334 agentes, el apoyo
simulado quedó a 1, 8 y 6 puntos del real. Ojo: se midió sobre los mismos casos con que se ajustó la
instrucción; un caso nuevo puede fallar más.

## Iteraciones y documentos

- Si se piden iteraciones, al terminar las variantes escritas un agente (Sonnet) toma la variante con más apoyo y
  las frases de quienes no la apoyan, y redacta una versión nueva con un título corto y qué cambió. Se pregunta
  a los mismos agentes.
- Un documento subido (`.txt`, `.md`, `.html`, `.docx` o `.pdf` con `pdftotext`) se lee entero; si pasa de 3.500
  caracteres, Sonnet lo resume en unas 220 palabras y eso es lo que leen los agentes.

## Caché

`data/cache/respuestas.jsonl` guarda cada respuesta por política, agente, modelo y versión de las instrucciones.
Repetir una pregunta no vuelve a gastar y llega en segundos (la interfaz igual la muestra encenderse). Cambiar
las instrucciones invalida la caché sola. `data/` no se versiona.

## Rutas

    GET  /api/estado                  motor, modelo y cuántos agentes hay
    GET  /api/agentes                 perfil y ubicación de cada agente
    POST /api/documentos              cuerpo: el archivo; cabecera X-Nombre
    POST /api/corridas                {casos:[{id,letra,texto,documento?}], agentes:[índices], iteraciones}
    GET  /api/corridas/<id>/eventos   text/event-stream
    POST /api/corridas/<id>/cancelar
