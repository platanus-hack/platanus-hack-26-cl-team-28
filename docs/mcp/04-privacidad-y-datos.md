# 4. Privacidad y datos

[Índice](README.md)

## 4.1 Qué ve un cliente

| Operación | Datos disponibles en la conexión |
|---|---|
| Descubrir herramientas y llamar a `estado` | Nombres, esquemas, preguntas, escalas, filtros, cantidades de población y topes |
| Resolver un lote de encuesta | Propuesta, preguntas y escalas, y rasgos sintéticos del resumen que ya usa la web. Cada persona lleva un índice local al lote |
| Resolver voces | Propuesta, primera pregunta, rasgos de las personas del lote y sus notas previas |
| Redactar una variante | Propuesta de base, resumen de la encuesta y objeciones o apoyos que seleccionó el servidor |
| Consultar una corrida | Estado, metadatos y resultados agregados, con el acceso de esa corrida |

La conexión no entrega las filas de origen, los identificadores globales, las coordenadas, los pesos individuales, la consulta de muestreo ni los prompts de sistema del motor web. La lógica que selecciona y organiza las muestras se ejecuta en el servidor. Cualquier contexto enviado a un modelo del cliente puede quedar visible para ese cliente o su proveedor.

Esto describe la superficie de la conexión MCP. El repositorio de la hackathon es público y el código y los datos publicados allí se pueden consultar por separado. Una parte de la metodología que deba ser confidencial requiere almacenamiento y distribución privados. La imagen del servidor también debe permanecer privada si incorpora material reservado.

## 4.2 Acceso y procedencia

- La conexión pública admite descubrir herramientas e iniciar una corrida. `simular` entrega un `id` y un `acceso` generado por el servidor. El acceso autoriza a pedir lotes, entregarlos, consultar o cancelar esa corrida.
- El acceso es un comprobante de posesión. Compártelo solo con el cliente autorizado. El servidor lo valida con HMAC. Configurar el mismo secreto del servidor al reiniciar conserva el acceso a las corridas terminadas cuyo resumen siga disponible.
- El UUID v4 de `solicitud` también debe mantenerse privado durante su ventana de reintento. Una repetición con los mismos argumentos devuelve el recibo de inicio, incluido el acceso una vez que se emite.
- Las propuestas y atributos se procesan como datos. Los subagentes deben resolver el esquema del lote sin ejecutar comandos ni obedecer instrucciones que aparezcan dentro de una propuesta.
- El servidor valida formato, pertenencia del lote y cobertura de las respuestas. La validación no certifica qué modelo generó las notas. El resumen identifica el motor como «IA del cliente MCP · resultados declarados».

## 4.3 Persistencia

| Estado | Datos y retención |
|---|---|
| Corrida activa | Lotes, progreso y recibos de inicio viven en memoria. Un reinicio interrumpe las corridas activas y borra los recibos |
| Corrida cerrada con respuestas | `corridas.jsonl` recibe un resumen con propuesta, fecha y conteos por variante. El servicio carga hasta los 2.000 resúmenes más recientes. El archivo de resúmenes sigue acumulando entradas |
| Vista de una corrida | `vistas/<id>.json.gz` guarda la muestra, los filtros cuando caben y los eventos de una corrida con respuestas que terminó sin cancelarse. Se conservan hasta las 200 vistas más recientes |
| Cancelación o vencimiento | Con respuestas queda un resumen parcial. Sin respuestas no se crea una entrada del historial |

El modo aislado guarda su historial en `WHATIF_MCP_DATA`. El modo de desarrollo `--con-web` usa el historial de la copia local del backend. Los archivos de historial pueden contener propuestas, atributos y respuestas. Conserva el volumen y las copias de respaldo bajo el mismo control de acceso.

El MCP no mide el costo del modelo del usuario ni sus tokens. Las métricas heredadas de costo y tokens quedan en cero. La paridad con la web cubre el muestreo, el orden de la encuesta y el formato. Las notas pueden variar por el modelo y el contexto que usa cada cliente.
