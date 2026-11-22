# Documentación del backend de What If Chile

Documentación de arquitectura del motor de simulación: qué hace, cómo está construido, qué garantiza,
cómo se protege, cuánto aguanta y cómo se opera. Describe el sistema tal como está en `main`; cada
afirmación sale del código, de una medición o de una prueba, y lo que no está medido se dice.

## Ficha

| Campo | Valor |
|---|---|
| Proyecto | What If Chile, equipo 28, Platanus Hack 2026, track Simulaciones |
| Alcance | `backend/servidor/`, `infra/` y lo que el servidor usa de `backend/scripts/` y `backend/data/` |
| Versión y fecha | v1, 21 de noviembre de 2026 |
| Estado | Describe lo desplegado en producción a esa fecha |
| Repositorio | Este mismo; las rutas de los documentos son relativas a su raíz |

## Mapa de lectura

| Documento | Responde |
|---|---|
| [1. Contexto y requisitos](01-contexto-y-requisitos.md) | Qué problema resuelve, qué queda fuera, qué debe hacer (RF), con qué reglas (RN) y con qué números (RNF) |
| [2. Arquitectura](02-arquitectura.md) | Estilo elegido y por qué, contexto, contenedores, módulos, patrones y despliegue |
| [3. Dominio y datos](03-dominio-y-datos.md) | Agente, muestra, corrida, caso y respuesta; estados; qué se guarda, dónde y por cuánto tiempo |
| [4. Flujos](04-flujos.md) | Los siete flujos de punta a punta, paso a paso, con sus errores |
| [5. API](05-api.md) | Rutas, cuerpos, eventos del flujo en vivo y códigos de error |
| [6. Seguridad](06-seguridad.md) | Modelo de amenazas, controles por capa, auditoría del 21 de noviembre y riesgo residual |
| [7. Capacidad y escalado](07-capacidad-y-escalado.md) | Mediciones, cuellos de botella, topes y qué hacer para crecer |
| [8. Operación](08-operacion.md) | Despliegue, variables, salud, registros y qué hacer ante cada incidente |
| [9. Decisiones y riesgos](09-decisiones-y-riesgos.md) | Las decisiones de arquitectura con sus alternativas descartadas, y los riesgos técnicos vigentes |

Para un recorrido rápido: la sección 1 del documento 1, los diagramas del documento 2 y la tabla de
mediciones del documento 7.

## El sistema en una página

What If Chile pregunta una encuesta fija de cinco preguntas a personas simuladas de Chile y muestra,
en vivo, cómo responde cada una a una o más versiones de una política pública.

- **Los agentes** son 1.546.322 registros del Censo 2024 que representan a los 15.463.163
  habitantes de 14 años o más, con datos de la encuesta Casen y opiniones de la Encuesta CEP
  imputados. Viven en archivos Parquet dentro del repositorio.
- **El servidor** es un proceso de Python que usa solo la biblioteca estándar para HTTP y DuckDB para
  consultar los agentes. Filtra y sortea la muestra, reparte a las personas en lotes, hace
  responder cada lote a un modelo de lenguaje y transmite las respuestas al navegador por un flujo
  de eventos.
- **El modelo** es Claude Haiku para la encuesta, Claude Opus como analista que ancla el total
  nacional (`backend/servidor/ancla.py`) y Claude Sonnet para redactar variantes y resumir documentos. En producción se llama por la línea de comandos de Claude Code, un proceso por lote.
- **La máquina** es una sola instancia de 16 núcleos y 30 GB con Caddy delante. Todo el estado de
  una simulación en curso está en la memoria del servidor; en disco quedan la caché de respuestas y
  el historial.

Lo que el sistema promete y lo que no:

- Una respuesta simulada no es una respuesta observada: es una aproximación validada. En 82 preguntas
  reservadas, el porcentaje de acuerdo queda en promedio a 8,2 puntos de la encuesta real y la mayoría
  queda del mismo lado en 88 % ([VALIDACION.md](../../VALIDACION.md)).
- Con 1.000 agentes una simulación termina en unos 21 segundos y con 10.000 en unos 114 segundos
  (medido en producción, documento 7).
- El servidor no se cae por exceso de pedidos: comparte un número fijo de llamadas al modelo entre
  todas las simulaciones y rechaza con un mensaje lo que no cabe (documentos 6 y 7).

## Convenciones

- Los identificadores son estables y no se reutilizan: `RF` requisito funcional, `RN` regla de
  negocio, `RNF` requisito no funcional, `S` supuesto, `I` invariante, `F` flujo, `ADR` decisión de
  arquitectura, `RT` riesgo técnico, `A` amenaza, `C` control, `H` hallazgo de la auditoría y `RS`
  riesgo residual.
- En el código, una simulación se llama **corrida** y cada versión de la política, **caso**; la
  interfaz las muestra como simulación y variante. Aquí se usan los nombres del código cuando se
  habla de módulos y los de la interfaz cuando se habla de lo que ve una persona.
- "Medido" significa que hay un número obtenido en la fecha indicada. "Estimado" es un cálculo a
  partir de mediciones. "No verificado" es lo que nadie ha comprobado todavía.
- Los diagramas están en Mermaid y se dibujan al ver el archivo en GitHub.
