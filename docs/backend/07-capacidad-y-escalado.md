# 7. Capacidad y escalado

[Índice](README.md)

Cuánto aguanta el sistema, qué lo limita y qué hay que cambiar para que aguante más. Las cifras
marcadas como medidas se tomaron el 21 de noviembre de 2026.

## 7.1 Parámetros de partida

| Parámetro | Valor | Fuente |
|---|---|---|
| Máquina | 16 núcleos, 30 GB de memoria útil, sin memoria de intercambio, disco de 30 GB | `infra/main.tf`; medido en la máquina |
| Llamadas al modelo a la vez | 120 | `infra/ph26-motor.service` (`LLAMADAS`) |
| Personas por lote | 10 | Servicio (`LOTE`) |
| Tope de memoria del servicio | 27 GB | Servicio (`MemoryMax`) |
| Memoria de un proceso del modelo | 216 MB de pico aislado; unos 125 MB efectivos con 120 a la vez, porque comparten el código | Medido en local y en producción |
| Procesador de un proceso del modelo | 0,4 s de procesador por llamada mínima | Medido en local |
| Memoria del motor | 0,5 GB en reposo; 0,9 GB con 200.000 respuestas en memoria | Medido |
| Tokens por lote de 10 personas | Unos 9.700 de entrada y salida | Medido: 10,2 millones en 1.043 llamadas |

## 7.2 Mediciones

### Con el modelo real, en producción

| Escenario | Tiempo | Respuestas | Llamadas | Pico de memoria | Lotes fallidos |
|---|---|---|---|---|---|
| 1.000 agentes, una variante | 21 s | 1.000 de 1.000 | 137 | 13 GB | 0 |
| 10.000 agentes, una variante | 114 s | 9.990 de 10.000 | 1.043 | 15 GB | 1 de unos 1.000 |
| 10.000 agentes, antes del reparto común (150 llamadas a la vez, reintentos inmediatos) | 105 s | Unas 9.440 | | No medido | 5,6 % |

Rendimiento: unas 88 respuestas por segundo sostenidas en la simulación grande. La primera
respuesta llega cerca de los 6 segundos.

Cada medición es una sola corrida. La diferencia entre 105 y 114 segundos no es concluyente; lo que
sí cambió con claridad es la proporción de lotes que fallan.

### Con un motor falso, en local

Para medir la maquinaria del servidor sin gastar modelo se reemplazó el motor por uno que espera un
tiempo fijo y devuelve notas al azar. Mide colas, hilos, memoria y equidad; no mide al proveedor.

| Escenario | Resultado |
|---|---|
| 15 personas con 2.000 agentes a la vez, lotes de 1 s | Todas terminan en 22 s; nunca más de 150 llamadas simultáneas |
| 20 personas con 10.000 agentes a la vez (200.000 respuestas), lotes de 0,25 s | Todas terminan en 35 s; el motor usa 0,9 GB y 261 hilos |
| Una simulación de 100 agentes que llega 8 s después de las grandes | Termina en 2,1 s en el primer escenario: no espera detrás de las demás |
| `GET /api/estado` durante la carga | Mediana de 2 ms; peor caso de 6 ms |
| Simulaciones sobre el cupo de cola o de dirección | Rechazadas con 429 y mensaje; el servidor sigue respondiendo |

## 7.3 Dónde se va el tiempo de una simulación

Para 1.000 agentes y 21 segundos:

| Etapa | Tiempo | Notas |
|---|---|---|
| Sortear la muestra | 0,3 s, antes de simular | Inmediato si ya se pidió |
| Validar, registrar y abrir el flujo | Milisegundos | |
| Primeros lotes chicos | 3 a 6 s | 24 personas de a 2 y 40 de a 5, con prioridad |
| Lotes de 10 | Unos 8 s cada uno, 120 en paralelo | Estimado entre los 5 s medidos para un lote de 5 y los 13 s para uno de 20. La mayor parte es espera al modelo |
| Frases | En paralelo, hasta 30 llamadas por variante | No bloquean el resultado |
| Guardar historial | Menos de 1 s | Después del evento final |

## 7.4 Cuellos de botella, en el orden en que aparecen

1. **El límite de la suscripción del modelo.** Sobre unas 90 respuestas por segundo una sola cuenta
   empieza a rechazar llamadas. Es el techo real. Se sube agregando cuentas en `CLAUDE_TOKENS`: las
   llamadas se reparten entre ellas por turno.
2. **El procesador.** Cada llamada es un proceso que arranca un intérprete: con 120 a la vez la
   carga de la máquina llega a 12 de 16 núcleos. Más llamadas simultáneas no rinden más en esta
   máquina.
3. **La memoria.** Con 120 llamadas el pico es de 15 GB de 27. Hay espacio para unas 200, pero el
   procesador y la suscripción limitan antes.
4. **La tabla de agentes.** Las consultas van de a una. Una muestra nueva de 10.000 tarda 1 s; con
   muchas personas cambiando filtros a la vez se forma fila, acotada a 12 en espera.
5. **El servidor HTTP.** No es un límite en lo medido: responde en milisegundos con 200.000
   respuestas en curso.

## 7.5 Cómo se reparte la capacidad

La capacidad es fija y se reparte, no se multiplica. Con N simulaciones a la vez, cada una avanza a
1/N de la velocidad total.

| Situación | Respuestas en cola | Tiempo hasta que terminan todas, a 90 por segundo |
|---|---|---|
| 1 persona, 1.000 agentes | 1.000 | 21 s (medido) |
| 15 personas, 1.000 agentes cada una | 15.000 | Unos 3 minutos |
| 15 personas, 2.000 agentes cada una | 30.000 | Unos 6 minutos |
| 15 personas, 10.000 agentes cada una | 150.000 | Unos 28 minutos |
| Cola llena | 200.000 | Unos 37 minutos |

Las filas 2 a 5 son estimaciones a partir del rendimiento medido. En todos los casos cada persona
ve llegar respuestas desde los primeros segundos, porque los turnos van parejos, y una simulación
chica termina mucho antes que las grandes.

Lo que impide que la demanda bote el sistema:

- **Tope común de llamadas** (`LLAMADAS`): nunca hay más procesos del modelo que ese número, sin
  importar cuántas simulaciones haya.
- **Cola acotada** (`RESPUESTAS_EN_COLA`): sobre el tope, una simulación nueva recibe "intenta de
  nuevo en un minuto" en vez de sumarse a una espera de horas.
- **Detención por abandono**: quien se va deja de ocupar turnos.
- **Tope de memoria del servicio**: si todo lo anterior fallara, el sistema corta un proceso del
  modelo y el sitio sigue.

## 7.6 Cómo crecer

En orden de menor a mayor esfuerzo. Cada paso se justifica solo si el anterior ya no alcanza.

| Paso | Qué cambia | Qué logra | Costo |
|---|---|---|---|
| 1. Más cuentas del modelo | Agregar sesiones a `CLAUDE_TOKENS` | Sube el techo de 90 respuestas por segundo hasta donde dé el procesador | Minutos; una suscripción por cuenta |
| 2. Lotes más grandes | `LOTE` de 10 a 20 | La mitad de procesos para las mismas respuestas; cada lote tarda más (unos 13 s) | Minutos. Las respuestas de un lote no son independientes: afecta la comparación fina entre variantes |
| 3. Máquina más grande | Tipo de instancia en `infra/main.tf` y `LLAMADAS` en proporción | Más procesos a la vez | Recrear la máquina; el estado en memoria se pierde |
| 4. Llamar a la API en vez de la línea de comandos | `MOTOR=api` con una clave; el motor `ClaudeApi` ya existe | Elimina el proceso por llamada: desaparecen los cuellos 2 y 3 | Pago por uso; hay que medir sus límites de tasa |
| 5. Varias máquinas | Sacar del proceso el estado de las simulaciones y la cola de llamadas | Escala horizontal y simulaciones que sobreviven a un reinicio | Rediseño: ver abajo |

Para el paso 5, lo que hoy vive en la memoria de un proceso tendría que salir:

- **La cola de llamadas** a un servicio de colas, con trabajadores que escalan por largo de cola.
- **Los eventos de cada simulación** a un registro compartido, para que cualquier instancia pueda
  atender el flujo de eventos de cualquier simulación.
- **La caché y el historial** a una base de datos.
- **Las muestras** se pueden recalcular en cualquier instancia: el sorteo es determinista.

El motor quedaría sin estado y detrás de un balanceador. Nada de esto hace falta para la carga del
proyecto (S-01); está escrito para que la decisión sea informada si el supuesto deja de cumplirse.

## 7.7 Costo

| Concepto | Valor | Notas |
|---|---|---|
| Máquina | La tarifa por hora de una instancia de 16 núcleos | Corre solo durante el evento |
| Modelo | Suscripciones de Claude Code | Sin costo por llamada; el límite es la tasa |
| Equivalente por uso que informa el proveedor | 0,29 dólares por 1.000 agentes; 2,48 dólares por 10.000 | Medido; es lo que costaría el paso 4 de 7.6, no un cobro actual |

## 7.8 Qué no está medido

- La capacidad real con dos o más cuentas del modelo.
- El comportamiento con varias simulaciones grandes simultáneas con el modelo real: solo se midió
  con el motor falso.
- Simulaciones con varias variantes e iteraciones a tamaño máximo.
- La tasa de fallos por límite del proveedor en horario de alta demanda.
- El motor por API a esta escala.
