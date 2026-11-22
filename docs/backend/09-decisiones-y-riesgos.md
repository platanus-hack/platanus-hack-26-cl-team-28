# 9. Decisiones y riesgos

[Índice](README.md)

Cada decisión dice qué se eligió, qué se descartó y por qué, qué consecuencias trae y qué hecho
obligaría a revisarla. Los riesgos dicen cómo se notarían antes de que duelan.

## 9.1 Decisiones de arquitectura

### ADR-01. Un solo proceso con el estado en memoria

- **Estado:** vigente.
- **Contexto:** un equipo de cinco personas, un fin de semana, una máquina y una sala como carga
  esperada (S-01). El resultado tiene que verse en vivo.
- **Decisión:** un proceso de Python atiende HTTP y ejecuta las simulaciones en hilos. Las
  simulaciones en curso, sus eventos y las muestras viven en memoria.
- **Alternativas descartadas:** una API con cola y trabajadores aparte (más piezas que desplegar y
  vigilar, y un salto más entre la respuesta del modelo y el navegador); funciones sin servidor (el
  modelo se llama por una línea de comandos con sesión local y el flujo de eventos dura minutos).
- **Consecuencias:** despliegue trivial y flujo de eventos directo. A cambio, un reinicio pierde las
  simulaciones en curso y no se puede agregar una segunda máquina sin rediseñar.
- **Se revisa si:** hace falta más de una máquina, o las simulaciones deben sobrevivir a un reinicio.

### ADR-02. Servidor HTTP de la biblioteca estándar, sin framework

- **Estado:** vigente.
- **Contexto:** el servidor tenía que correr en el computador de cualquiera del equipo con solo
  Python, y la API son nueve rutas.
- **Decisión:** `http.server` con un hilo por conexión.
- **Alternativas descartadas:** un framework asíncrono (más rendimiento por conexión, que no es el
  cuello de botella, y una dependencia más para un equipo que no lo usaba).
- **Consecuencias:** cero dependencias web y código legible de punta a punta. A cambio, lo que un
  framework trae hecho hubo que escribirlo: validación, límites de tamaño, tiempos de espera, tope
  de conexiones y manejo de errores ([documento 6](06-seguridad.md)).
- **Se revisa si:** la API crece en rutas o aparece autenticación por usuario.

### ADR-03. El modelo se llama por la línea de comandos, un proceso por lote

- **Estado:** vigente en producción; la alternativa está implementada.
- **Contexto:** el equipo tenía suscripciones de Claude Code y no presupuesto de API. La suscripción
  solo se usa desde su línea de comandos.
- **Decisión:** cada lote lanza un proceso `claude -p` sin herramientas, con el pedido por la entrada
  estándar y la respuesta como JSON validado contra un esquema.
- **Alternativas descartadas para producción:** la API del proveedor (`ClaudeApi`, que existe y se
  elige con `MOTOR=api`): más rápida y sin proceso por llamada, pero con pago por uso.
- **Consecuencias:** costo por llamada nulo. A cambio, cada llamada cuesta unos 125 MB y 0,4 s de
  procesador, lo que convierte a la memoria y al procesador en límites y obliga al tope común del
  ADR-05.
- **Se revisa si:** hay presupuesto de API, o el techo de 90 respuestas por segundo no alcanza.

### ADR-04. Personas en lotes de 10 por llamada

- **Estado:** vigente.
- **Contexto:** preguntar de a una persona multiplica por diez las llamadas y los procesos.
- **Decisión:** 10 personas por llamada, con una instrucción que pide responder por separado. Los
  primeros 64 agentes van en lotes de 2 y de 5 para que haya respuestas a los pocos segundos.
- **Alternativas descartadas:** una persona por llamada (diez veces más procesos); lotes de 20 o 25
  (menos llamadas, pero cada una tarda más y la primera respuesta se atrasa).
- **Consecuencias:** las respuestas de un mismo lote no son independientes: en las pruebas, el
  promedio de un mismo texto cambió unos 0,16 puntos de un lote a otro. Sirve para la demo; para
  comparar variantes con rigor se usa el método del banco de pruebas, que hace responder todas las
  variantes al mismo lote.
- **Se revisa si:** el objetivo pasa de mostrar a medir diferencias chicas entre variantes.

### ADR-05. Reparto común de llamadas, con turnos por simulación

- **Estado:** vigente desde el 21 de noviembre de 2026. Reemplaza al grupo de hilos propio de cada
  simulación.
- **Contexto:** con un grupo de 150 hilos por simulación, quince simulaciones a la vez pedían más de
  2.000 procesos en una máquina de 30 GB (H-01).
- **Decisión:** un solo grupo de hilos, de tamaño `LLAMADAS`, atiende las tareas de todas las
  simulaciones tomando una de cada una por turno. Cada simulación tiene dos filas: la urgente, con
  sus primeros lotes, y el resto.
- **Alternativas descartadas:** un semáforo global sobre los grupos existentes (miles de hilos
  despertando en cada liberación y sin garantía de equidad); una cola única por orden de llegada
  (una simulación chica esperaría detrás de una de 10.000); un cupo fijo por simulación (desperdicia
  capacidad cuando hay una sola).
- **Consecuencias:** el número de procesos tiene techo, una simulación sola usa toda la capacidad y
  varias avanzan a la par. A cambio, con mucha demanda todas van más lentas en vez de fallar algunas.
- **Se revisa si:** se pasa a varias máquinas: el reparto se reemplaza por una cola externa.

### ADR-06. Rechazar con mensaje en vez de encolar sin límite

- **Estado:** vigente.
- **Contexto:** una cola sin tope convierte el exceso de demanda en esperas de horas y en memoria
  que crece.
- **Decisión:** cupos de simulaciones en curso y de respuestas en cola; lo que no cabe recibe un 429
  con un mensaje que la interfaz muestra.
- **Alternativas descartadas:** aceptar todo y dejar que espere; limitar solo por dirección (una
  sala entera comparte dirección, así que el límite por dirección tiene que ser holgado).
- **Consecuencias:** el servidor siempre responde y la espera máxima está acotada. A cambio, en un
  pico alguien tiene que reintentar.
- **Se revisa si:** los rechazos se vuelven frecuentes con uso legítimo: entonces falta capacidad
  ([documento 7](07-capacidad-y-escalado.md), sección 7.6).

### ADR-07. El método de encuesta se importa, no se copia

- **Estado:** vigente.
- **Contexto:** las instrucciones, la encuesta y el redactor de perfiles los mantiene otra parte del
  equipo en `backend/scripts/`, y cambian con cada prueba.
- **Decisión:** `metodo.py` carga esos módulos por ruta y expone lo que el servidor necesita.
- **Alternativas descartadas:** copiar el método al servidor (dos versiones que se desalinean sin
  que nadie lo note).
- **Consecuencias:** lo que se valida en el banco de pruebas es exactamente lo que usa el sitio, y la
  caché se invalida sola cuando cambia. A cambio, un cambio de firma allá impide que el servidor
  arranque; el despliegue lo detecta y vuelve atrás.
- **Se revisa si:** el método se estabiliza y conviene publicarlo como paquete.

### ADR-08. Los agentes se consultan con DuckDB dentro del proceso, desde archivos Parquet versionados

- **Estado:** vigente.
- **Contexto:** 1,5 millones de agentes con unas 230 columnas, que se filtran por 13 parámetros y se
  sortean con cuotas.
- **Decisión:** los archivos Parquet van en el repositorio (100 MB). Al partir se arma en memoria un
  resumen con una fila por agente y su opción en cada parámetro; filtros, sorteo y retrato se
  calculan sobre ese resumen, y solo se leen del disco los agentes elegidos.
- **Alternativas descartadas:** una base de datos aparte (otro servicio que instalar, cargar y
  respaldar para datos que no cambian); cargar todo en memoria con otra biblioteca (más memoria y
  más lento al partir).
- **Consecuencias:** clonar el repositorio basta para tener la población; un filtro tarda decenas de
  milisegundos. A cambio, las consultas van de a una y el repositorio pesa.
- **Se revisa si:** la población crece un orden de magnitud o hay muchos cambios de filtro
  simultáneos.

### ADR-09. Flujo de eventos del servidor al navegador

- **Estado:** vigente.
- **Contexto:** el navegador solo necesita recibir; lo único que envía es "detener".
- **Decisión:** un flujo `text/event-stream` por simulación, con eventos numerados y reanudación
  desde el último recibido.
- **Alternativas descartadas:** consultar cada cierto tiempo (latencia y pedidos de sobra);
  conexión bidireccional (más compleja, y no hay nada que enviar).
- **Consecuencias:** reconexión nativa del navegador y código simple. A cambio, cada persona mirando
  ocupa una conexión y un hilo mientras dura, lo que obliga a topes de flujos.
- **Se revisa si:** hay miles de personas mirando a la vez.

### ADR-10. Caché de respuestas como archivo al que solo se le agregan líneas

- **Estado:** vigente.
- **Contexto:** repetir una pregunta durante la demo no debe volver a gastar ni tardar.
- **Decisión:** un archivo JSONL con una línea por respuesta, cargado completo en memoria al partir.
  La clave incluye la versión de todo lo que lee el modelo.
- **Alternativas descartadas:** una base de datos embebida (más robusta, pero innecesaria para el
  volumen del proyecto).
- **Consecuencias:** implementación de pocas líneas y lectura instantánea. A cambio, no se compacta
  y crece sin límite en disco. Al partir se carga entero en memoria; el tope de 3 millones de filas
  solo frena las filas nuevas.
- **Se revisa si:** el archivo pasa de unos cientos de MB.

### ADR-11. Sin cuentas de usuario; el acceso se controla en el borde

- **Estado:** vigente.
- **Contexto:** el sitio es una demostración que debe poder abrirse a una sala sin fricción.
- **Decisión:** no hay registro ni sesión. Una clave común en el servidor web protege el sitio
  mientras no está abierto, y los cupos protegen la capacidad cuando lo está.
- **Alternativas descartadas:** cuentas con cupo por usuario (el control más preciso, pero fuera del
  plazo y contrario a "cualquiera entra y prueba").
- **Consecuencias:** cero fricción. A cambio, no se puede atribuir el uso ni separar el historial
  por persona, y los cupos por dirección son la única aproximación a "por usuario".
- **Se revisa si:** el sitio queda abierto de forma permanente.

### ADR-12. La configuración de la máquina vive en el repositorio y se instala con vuelta atrás

- **Estado:** vigente desde el 21 de noviembre de 2026.
- **Contexto:** el servidor web y el servicio se habían escrito una vez al crear la máquina; un
  cambio posterior exigía editarlos a mano.
- **Decisión:** `infra/Caddyfile` e `infra/ph26-motor.service` son la fuente; el despliegue los
  instala si cambiaron, valida antes de cargar, comprueba que el motor responda y restaura lo
  anterior si no.
- **Alternativas descartadas:** recrear la máquina en cada cambio (pierde el estado y la dirección).
- **Consecuencias:** la configuración se revisa como código y un error no deja el sitio caído.
- **Se revisa si:** se pasa a contenedores o a más de una máquina.

## 9.2 Riesgos técnicos

| ID | Riesgo | Impacto | Probabilidad | Señal temprana | Respuesta |
|---|---|---|---|---|---|
| RT-01 | Una sola máquina: su falla es la caída del sitio | Alto | Baja en un fin de semana | La máquina deja de responder | Recrear con Terraform ([documento 8](08-operacion.md), sección 8.7); no hay respaldo en caliente |
| RT-02 | El proveedor limita la cuenta durante la presentación | Alto | Media | Avisos de grupos que no alcanzan a responder | Varias cuentas en `CLAUDE_TOKENS`; los reintentos con espera absorben límites breves; la caché cubre las preguntas ya hechas |
| RT-03 | Un despliegue del backend corta las simulaciones en curso | Medio | Media si alguien hace push durante la demo | Simulaciones que terminan solas | Acordar no desplegar backend durante la presentación |
| RT-04 | Contenido ofensivo en el historial común o en las frases, con el sitio abierto | Medio, de reputación | Media | Aparece en pantalla | `HISTORIAL_OCULTO=1`; volver a poner la clave |
| RT-05 | La caché crece sin compactarse | Bajo | Baja en el plazo | Disco sobre 80 % | Vaciar la caché |
| RT-06 | Sin respaldos de caché e historial | Bajo | Baja | | Copia nocturna si el sitio sigue en uso |
| RT-07 | Un cambio en `backend/scripts/` rompe el arranque del servidor | Medio | Media | El despliegue queda en rojo | El despliegue vuelve a la versión anterior; correr el servidor en local antes de subir cambios al método |
| RT-08 | La máquina cambia de dirección si se detiene | Medio | Baja | El dominio deja de resolver al sitio | Actualizar el registro del dominio; no detener la instancia |
| RT-09 | Los cupos por dirección son holgados: una sola dirección puede ocupar buena parte de la cola | Medio | Baja con clave, media sin ella | Rechazos a otras personas | Bajar `CORRIDAS_POR_DIRECCION` y `RESPUESTAS_EN_COLA` al abrir sin clave |
| RT-10 | Las cifras de capacidad con varias simulaciones grandes reales no están medidas | Medio | | Simulaciones más lentas que lo estimado | La estimación del documento 7 es conservadora; medir antes de prometer |
| RT-11 | El resultado simulado se lee como predicción | Alto, de credibilidad | Media | Preguntas del jurado sobre exactitud | La interfaz muestra la comparación con encuestas reales tal como sale; el error medido está en `backend/data/pruebas/banco/README.md` |

## 9.3 Deuda conocida

- No hay monitoreo ni alertas.
- No hay pruebas automáticas de las rutas HTTP: la validación se probó con un programa de pedidos
  abusivos que no quedó en el repositorio. Sí hay pruebas del reparto, las tasas, los documentos, el
  historial, los parámetros de filtro y el sorteo.
- El servicio corre con el usuario por defecto de la imagen.
- La recuperación de la máquina desde cero no se ha ensayado.
- La compatibilidad de la API no tiene versión: el frontend y el motor se despliegan juntos.
