# 1. Contexto y requisitos

[Índice](README.md)

## 1.1 Contexto y objetivo

Hoy una política pública se prueba con la gente recién cuando ya está aprobada. What If Chile es un
ambiente de pruebas: permite escribir una propuesta, preguntarle a una muestra de personas simuladas
de todo el país y ver, antes de decidir, quiénes la apoyan, quiénes no y qué cambia entre versiones
de la misma idea.

El backend es la parte que hace esa pregunta. Su resultado esperado es que una persona escriba una
propuesta en la interfaz y vea las primeras respuestas en menos de 10 segundos, y el resultado
completo de 1.000 agentes en menos de 30.

Se mide con tres cosas: el tiempo hasta la primera respuesta y hasta el final de una simulación, la
proporción de agentes que responden, y la distancia entre el resultado simulado y encuestas reales
publicadas (esta última en `backend/data/pruebas/banco/README.md`).

## 1.2 Alcance

En alcance:

- El servidor HTTP (`backend/servidor/`): estado, muestra, simulaciones, documentos e historial.
- La selección de agentes desde la tabla de población.
- La comunicación con el modelo de lenguaje y la caché de respuestas.
- La infraestructura de producción (`infra/`): máquina, servidor web, servicio y despliegue.

Fuera de alcance:

- La construcción de la población (descarga del censo, imputación desde Casen y CEP, reducción a
  agentes). Está documentada en `backend/CLAUDE.md` y `backend/contexto/`.
- El método de encuesta y su validación (`backend/scripts/probar_modelo.py`,
  `backend/contexto/delphos/framework.md`). El servidor lo importa sin copiarlo.
- El frontend, documentado en `frontend/DESIGN.md` y `frontend/README.md`.
- Otros clientes del motor que el equipo pueda agregar, cada uno con su propia documentación.

Restricciones que dieron forma al diseño:

- Plazo de un fin de semana y un equipo de cinco personas.
- El modelo se paga con suscripciones de Claude Code, que solo se usan por su línea de comandos:
  cada llamada es un proceso del sistema operativo.
- Una sola máquina.
- El servidor debía poder correr en cualquier computador del equipo con Python y sin instalar un
  framework web.

Supuestos:

| ID | Supuesto | Estado |
|---|---|---|
| S-01 | La carga máxima es una sala de presentación: decenas de personas a la vez, no miles | No verificado; los topes del documento 7 acotan el daño si no se cumple |
| S-02 | Perder las simulaciones en curso al reiniciar el servidor es aceptable | Aceptado por el equipo; el historial y la caché sobreviven |
| S-03 | Las propuestas que se escriben no son datos personales ni confidenciales | Aceptado; el historial es común a todos los que entran |

## 1.3 Interesados

| Interesado | Qué le importa | Cómo participa |
|---|---|---|
| Quien presenta la demo | Que responda rápido y no se caiga frente al jurado | Usa la interfaz; opera la máquina |
| Público que prueba el sitio | Entender el resultado y que su pregunta se responda | Usa la interfaz sin cuenta |
| Equipo de método y datos | Que el servidor use el mismo método que el banco de pruebas | Mantiene `backend/scripts/` |
| Equipo de frontend | Un contrato estable de rutas y eventos | Consume la API |
| Quien paga la suscripción | Que nadie la gaste sin límite | Pone sus credenciales en la máquina |

## 1.4 Requisitos funcionales

El origen de cada requisito es la reunión de mentoría, el código existente o una decisión del equipo;
los flujos están en el [documento 4](04-flujos.md).

| ID | Requisito | Prioridad | Flujos | Reglas |
|---|---|---|---|---|
| RF-01 | Informar qué motor responde, cuánta población hay, la encuesta y los topes vigentes | obligatorio | F1 | |
| RF-02 | Filtrar la población por edad y por 13 parámetros, y sortear una muestra de hasta 10.000 agentes proporcional al país | obligatorio | F2 | RN-01, RN-02, RN-03 |
| RF-03 | Entregar junto a la muestra el retrato de la población: cuánta gente hay en cada opción de cada filtro | obligatorio | F2 | |
| RF-04 | Preguntar la encuesta a los agentes de la muestra para una o más variantes y transmitir cada respuesta apenas llega | obligatorio | F3 | RN-04, RN-05, RN-06, RN-07 |
| RF-05 | Pedir a algunas personas una frase que explique su respuesta | deseable | F3 | RN-08 |
| RF-06 | Redactar hasta tres variantes nuevas a partir de las objeciones y volver a preguntar | deseable | F4 | RN-09 |
| RF-07 | Leer un documento subido (texto, HTML, Word o PDF) y resumirlo si es largo | deseable | F5 | RN-10, RN-11 |
| RF-08 | No volver a preguntar lo ya respondido: misma política, mismo agente, mismo modelo y mismas instrucciones | obligatorio | F3 | RN-12 |
| RF-09 | Detener una simulación a pedido | obligatorio | F6 | |
| RF-10 | Guardar cada simulación terminada y permitir volver a verla | deseable | F7 | RN-13 |

## 1.5 Reglas de negocio

Los límites son inclusivos salvo que se diga otra cosa. La columna "Dónde" indica el archivo que la
aplica.

| ID | Regla | Dónde |
|---|---|---|
| RN-01 | Se simula desde los 14 años. La edad tiene tope en 85, que significa 85 o más | `sociedad.py`, `poblacion.py` |
| RN-02 | El mismo filtro y tamaño entregan siempre a las mismas personas (sorteo con semilla fija) | `poblacion.py` |
| RN-03 | Cada región, comuna y zona queda a menos de una persona de su parte exacta de la muestra | `poblacion.repartir` |
| RN-04 | La encuesta son cinco preguntas fijas; cada respuesta es un entero de 1 a 7. Un pedido no puede cambiarlas | `metodo.py`, `__main__.py` |
| RN-05 | La postura sale de la primera pregunta: 5 a 7 a favor, 4 sin decidir, 1 a 3 en contra | `corridas.postura` |
| RN-06 | Una simulación tiene hasta 8 casos, contando las variantes escritas y las que redacta el modelo | `__main__.LETRAS` |
| RN-07 | Una propuesta escrita tiene hasta 8.000 caracteres; con 8.001 se rechaza con mensaje | `__main__.LARGO_PROPUESTA` |
| RN-08 | Se piden frases a 2 personas por lote, en hasta 30 lotes por caso, y nunca cambian las notas | `corridas.py` |
| RN-09 | Hasta 3 iteraciones por simulación; no se itera si ningún caso tiene respuestas | `__main__.MAXIMO_ITERACIONES`, `corridas.correr` |
| RN-10 | Un documento pesa hasta 25 MB. Se leen hasta 400 páginas de un PDF y 3.000.000 de caracteres de texto | `__main__.py`, `documentos.py` |
| RN-11 | Un documento de hasta 3.500 caracteres se usa tal cual; uno más largo se resume en unas 220 palabras a partir de sus primeros 240.000 caracteres | `corridas.resumir_documento` |
| RN-12 | La clave de la caché es la huella de la política (sin mayúsculas ni espacios repetidos), el modelo con la versión de instrucciones, encuesta y filtro de perfil, y el agente | `corridas.Cache`, `motor.Motor.clave` |
| RN-13 | Se guardan en disco las últimas 200 simulaciones completas para volver a verlas; una simulación detenida deja solo su resumen | `historial.py` |
| RN-14 | Una simulación que nadie mira durante 90 segundos se detiene al empezar su siguiente lote | `corridas._revisar_abandono` |

## 1.6 Requisitos no funcionales

Los valores "medido" vienen del [documento 7](07-capacidad-y-escalado.md). El resto es el objetivo
que guía el diseño.

| ID | Atributo | Escenario y medida | Valor | Estado |
|---|---|---|---|---|
| RNF-01 | Latencia percibida | Tiempo desde que se pide la simulación hasta la primera respuesta en pantalla, con el modelo real | Hasta 10 s | Medido: 6 s con 1.000 agentes |
| RNF-02 | Tiempo de simulación | 1.000 agentes, una variante, sin caché | Hasta 30 s | Medido: 21 s |
| RNF-03 | Tiempo de simulación | 10.000 agentes, una variante, sin caché | Hasta 150 s | Medido: 114 s |
| RNF-04 | Completitud | Proporción de agentes que responden en una simulación de 10.000 | Al menos 99 % | Medido: 99,9 % |
| RNF-05 | Capacidad | Simulaciones grandes a la vez sin que el servidor deje de responder | 15 de 10.000 agentes | Medido con motor falso: 20 a la vez |
| RNF-06 | Latencia de la API | `GET /api/estado` mientras hay carga máxima | Hasta 50 ms | Medido: 6 ms en el peor caso |
| RNF-07 | Memoria | Pico de memoria del servicio con una simulación de 10.000 agentes | Bajo 27 GB | Medido: 15 GB |
| RNF-08 | Elegir a quiénes preguntar | Cambiar un filtro y recibir la muestra nueva | Hasta 1 s | Medido: 0,3 s con 2.000 agentes y 1 s con 10.000 |
| RNF-09 | Resistencia | Ningún pedido de un cliente sin cuenta puede botar el proceso ni agotar la memoria | Sin excepciones conocidas | Probado con 25 pedidos abusivos, documento 6 |
| RNF-10 | Recuperación | Tiempo en volver a responder tras una caída del proceso | Hasta 10 s | El servicio se reinicia a los 2 s; el arranque medido es de 1 s |
| RNF-11 | Portabilidad | El servidor arranca sin dependencias web: solo Python y, para la tabla de agentes, DuckDB | Cumple | Verificado en local y en producción |

No hay un objetivo de disponibilidad comprometido. El sistema corre en una sola máquina y una
simulación en curso se pierde si el proceso se reinicia (S-02).
