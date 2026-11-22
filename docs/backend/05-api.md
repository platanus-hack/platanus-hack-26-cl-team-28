# 5. API

[Índice](README.md)

Todas las rutas cuelgan de `/api` y responden JSON en UTF-8, salvo el flujo de eventos. No hay
cuentas ni tokens: el acceso se controla en el servidor web (clave de acceso del sitio) y con los
cupos de la sección 5.4. El frontend y la API se sirven desde el mismo origen y la API no entrega
cabeceras de permiso entre orígenes.

Los valores de los ejemplos son ilustrativos; la forma es la real.

## 5.1 Resumen de rutas

| Método y ruta | Qué hace | Flujo |
|---|---|---|
| `GET /api/estado` | Motor, población, encuesta y topes | F1 |
| `POST /api/muestra` | Filtra la población y sortea una muestra | F2 |
| `GET /api/agentes` | La muestra sin filtros de 2.000 agentes, como lista (compatibilidad) | |
| `POST /api/documentos` | Lee un archivo y devuelve su texto o su resumen | F5 |
| `POST /api/corridas` | Lanza una simulación | F3 |
| `GET /api/corridas/{id}/eventos` | Flujo de eventos de una simulación | F3 |
| `POST /api/corridas/{id}/cancelar` | Detiene una simulación | F6 |
| `GET /api/historial` | Las últimas 100 simulaciones | F7 |
| `GET /api/historial/{id}` | Una simulación guardada, para volver a verla | F7 |

## 5.2 Rutas en detalle

### GET /api/estado

```json
{
  "motor": { "nombre": "Claude Code", "modelo": "claude-haiku", "perfil": "tematico" },
  "agentes": 1546322,
  "poblacion": {
    "fuente": "Tabla de agentes del Censo 2024",
    "agentes": 1546322,
    "personas": 15463163,
    "representa": 10,
    "niveles": [10, 100, 1000, 10000],
    "parametros": [{ "clave": "region", "opciones": ["Arica y Parinacota", "..."] }]
  },
  "lote": 10,
  "concurrencia": 150,
  "maximo_muestra": 10000,
  "preguntas": ["¿Estás de acuerdo o en desacuerdo con lo que plantea el tema de la encuesta?", "..."],
  "nombres": ["Apoyo", "Justicia", "Confianza", "Efectividad", "Influencia"],
  "escalas": [["totalmente en desacuerdo", "totalmente de acuerdo"], ["muy injusto", "muy justo"]]
}
```

`perfil` es el nivel del filtro de perfil (`tematico`, `nucleo` o `completo`). `maximo_muestra` es lo
más que el motor entrega en una muestra; la interfaz no ofrece tamaños mayores.

### POST /api/muestra

Pedido:

```json
{
  "tamano": 1000,
  "filtros": {
    "edadMin": 18,
    "edadMax": 85,
    "reduccion": 10,
    "region": [5, 6],
    "voto": [1]
  }
}
```

- `tamano` se ajusta al rango de 1 a `maximo_muestra`.
- `reduccion` es 10, 100, 1000 o 10000; cualquier otro valor se toma como 10.
- Cada parámetro es una lista de índices de opción. Las claves válidas y su orden están en
  `poblacion.parametros` de `/api/estado`: `region`, `genero`, `educacion`, `nacionalidad`,
  `trabajo`, `menores`, `vivienda`, `salud`, `quintil`, `politica`, `gobierno`, `voto` y `confianza`.
  Lo que no es un entero dentro del rango se ignora; una lista vacía o con todas las opciones no
  filtra.

Respuesta:

```json
{
  "id": "0c5efe32479d",
  "disponibles": 1546322,
  "representadas": 15463163,
  "dimensiones": ["region", "genero", "educacion", "..."],
  "retrato": { "region": [25180, 38000, "..."], "edad": [201000, "..."] },
  "agentes": [
    {
      "i": 0, "id": "p130000123", "region": 6, "comuna": "Maipú", "cod_comuna": 13119,
      "lon": -70.76, "lat": -33.51, "edad": 34, "genero": 0, "quintil": 2, "educacion": 2,
      "politica": 2, "representa": 10,
      "s": [6, 0, 2, 0, 0, 1, 1, 1, 2, 2, 1, 0, 1],
      "atributos": { "Edad": "34 años", "Género": "Mujer", "Comuna": "Maipú" }
    }
  ]
}
```

- `i` es el índice del agente dentro de esta muestra: es lo que se envía después en `agentes` y lo
  que traen los eventos.
- `s` es la opción del agente en cada parámetro, en el orden de `dimensiones`; menos uno si no tiene
  el dato (los menores de 18 no tienen opiniones).
- `retrato` trae, por parámetro, las personas de cada opción entre quienes cumplen los demás
  filtros, y en `edad`, las de cada edad desde los 14.
- El perfil que lee el modelo no viaja.

### POST /api/documentos

El cuerpo es el archivo. Cabeceras: `X-Nombre` con el nombre codificado para URL, y
`Content-Length`. Tipos: `.txt`, `.md`, `.html`, `.docx` y `.pdf`.

```json
{
  "nombre": "proyecto-de-ley.pdf",
  "titulo": "Rebaja de tarifas de autopistas",
  "texto": "El proyecto propone ...",
  "largo_original": 84211,
  "llamadas": 1,
  "costo_usd": 0.0312
}
```

`largo_original` aparece solo si el documento se resumió. El objeto con `nombre`, `titulo` y `texto`
es el que se envía como `documento` de una variante.

### POST /api/corridas

```json
{
  "casos": [
    { "id": "a", "texto": "Rebajar el TAG entre 10 % y 25 % a cambio de extender la concesión." },
    { "id": "b", "texto": "", "documento": { "nombre": "ley.pdf", "titulo": "...", "texto": "..." } }
  ],
  "muestra": "0c5efe32479d",
  "agentes": [0, 1, 2, 3],
  "iteraciones": 1,
  "filtros": { "tamano": 1000, "elegidos": {} }
}
```

- `casos`: hasta 8. Cada uno necesita `texto`, `documento` o ambos.
- `muestra`: el identificador que entregó `/api/muestra`. Sin él se usa la muestra sin filtros de
  2.000 agentes.
- `agentes`: índices dentro de la muestra. Sin él se pregunta a toda la muestra.
- `iteraciones`: de 0 a 3.
- `filtros`: los de la interfaz, tal como los tiene; se guardan con la simulación para volver a
  verla. No se interpretan.
- La letra de cada variante y el tamaño del lote los pone el servidor; si el pedido trae `letra`,
  `lote` o `preguntas`, no se usan.

Respuesta 201:

```json
{ "id": "e9b41c7204ff", "motor": { "nombre": "Claude Code", "modelo": "claude-haiku", "perfil": "tematico" }, "agentes": 4, "preguntas": ["..."] }
```

### POST /api/corridas/{id}/cancelar

Sin cuerpo. Responde `{"ok": true}` exista o no la simulación.

### GET /api/historial

```json
{
  "corridas": [
    {
      "id": "e9b41c7204ff", "hora": "2026-11-22T01:48:05+00:00", "agentes": 1000,
      "modelo": "claude-haiku", "segundos": 21.1, "costo_usd": 0.2866, "completa": true, "vista": true,
      "casos": [
        { "letra": "A", "texto": "...", "titulo": "", "documento": null, "iteracion": false,
          "respondidas": 1000, "favor": 954, "contra": 31, "indecisa": 15 }
      ]
    }
  ]
}
```

`vista` dice si la simulación se puede volver a ver. `costo_usd` es lo que informa el proveedor por
las llamadas; con suscripción no es un cobro.

### GET /api/historial/{id}

Devuelve `{ "muestra": {...}, "agentes": [0, 1, ...], "filtros": {...}, "eventos": [["inicio", {...}], ...] }`.
La muestra tiene la misma forma que la respuesta de `/api/muestra`. Va comprimida con gzip si el
cliente lo acepta.

## 5.3 Flujo de eventos

`GET /api/corridas/{id}/eventos` responde `text/event-stream`. Cada evento lleva un `id` numérico
consecutivo desde cero, un `event` con el tipo y un `data` con JSON. Si no hay novedades en 15
segundos se envía un comentario para mantener viva la conexión. Al reconectar, el navegador envía
`Last-Event-ID` y el servidor continúa desde el siguiente.

| Evento | Cuándo | Datos |
|---|---|---|
| `inicio` | Al empezar | `motor`, `agentes`, `casos` (cada uno con `id`, `letra`, `texto`, `titulo`, `documento`, `iteracion` y `temas`), `iteraciones`, `preguntas` |
| `respuestas` | Llega un lote, o una tanda de la caché | `caso` (índice), `cache` (si venía guardada), `r`: lista de `[agente, acuerdo, frase, notas]`, y `metricas` |
| `voces` | Llegan frases | `caso`, `r`: lista de `[agente, frase]`, `metricas` |
| `caso_listo` | Una variante terminó | `caso`, `apoyo` (de 0 a 1), `respondidas`, `ancla` (el % de acuerdo y en desacuerdo estimado para el país, o `null`), `metricas` |
| `redactando` | Empieza una iteración | `numero`, `metricas` |
| `caso` | El modelo redactó una variante nueva | `caso` y los mismos campos de un caso de `inicio`; `iteracion` trae `de`, `numero` y `cambio` |
| `aviso` | Un lote no pudo responder tras 3 intentos, o falló una vez con la simulación ya detenida | `mensaje` |
| `fin` | La simulación terminó o se detuvo | `metricas`, `apoyos` por variante |
| `falla` | Error no previsto | `mensaje` genérico |

`metricas` es `{ "llamadas", "costo_usd", "tokens", "segundos" }`, acumulado de la simulación.
`agente` es el índice `i` de la muestra. `acuerdo` es la primera de las cinco `notas`.

Ejemplo:

```text
id: 7
event: respuestas
data: {"caso": 0, "cache": false, "r": [[12, 6, "", [6, 5, 3, 5, 2]], [13, 2, "", [2, 2, 1, 3, 6]]], "metricas": {"llamadas": 4, "costo_usd": 0.0081, "tokens": 30122, "segundos": 6.2}}
```

## 5.4 Validación y cupos

Lo que se comprueba en `POST /api/corridas`, en este orden:

| Comprobación | Límite | Respuesta si falla |
|---|---|---|
| Pedidos por minuto desde la dirección | 3.000 en total, 60 simulaciones | 429 |
| Tamaño del pedido | 768 KB | 400 |
| Forma del pedido | Un objeto JSON | 400 |
| Variantes | `casos` debe ser una lista; los elementos que no son objetos y los que pasan de 8 se ignoran | Se filtran |
| Largo de cada propuesta | 8.000 caracteres | 400 |
| Documento de cada variante | Se usa solo `nombre` (limpio, 120 caracteres), `titulo` (200) y `texto` (10.500) | Se recorta |
| Al menos una variante con texto | | 400 |
| La muestra existe | | 400 |
| Agentes | Enteros dentro de la muestra, sin repetir | Se filtran; 400 si no queda ninguno |
| Respuestas pedidas | Agentes por (variantes más iteraciones), hasta 80.000 | 400 |
| Respuestas en cola | Pendientes de todas las simulaciones más las pedidas, hasta 200.000 | 429 |
| Simulaciones en curso | 40 en total, 12 desde la dirección | 429 |

Otros cupos:

| Ruta | Límite | Respuesta |
|---|---|---|
| `POST /api/muestra` | 600 por minuto por dirección; 12 muestras nuevas esperando la tabla | 429 |
| `POST /api/documentos` | 30 por minuto por dirección; 3 a la vez; 25 MB | 429, o rechazo por tamaño |
| `GET .../eventos` | 60 flujos abiertos por dirección; 30 por simulación | 429 |
| Cualquiera | 800 conexiones abiertas en total | La conexión se cierra |

Los cupos y las tasas se cambian con variables de entorno ([documento 8](08-operacion.md), sección
8.3). Los tamaños máximos (768 KB, 8.000 caracteres, 25 MB, 10.500 caracteres), las 3 iteraciones,
los 8 casos y los límites de lectura de documentos son constantes del código.

## 5.5 Errores

Toda respuesta de error es `{"error": "mensaje para la persona"}`. El frontend muestra ese mensaje
tal cual.

| Código | Significado | Ejemplo de mensaje |
|---|---|---|
| 400 | El pedido no es válido | "Falta al menos una propuesta con texto" |
| 404 | No existe la ruta, la simulación o la vista | "No existe esa corrida" |
| 422 | El documento no se pudo leer | "El documento no tiene texto legible" |
| 429 | No hay cupo; se puede reintentar. Trae `Retry-After: 10` | "Hay muchas simulaciones en curso. Intenta de nuevo en un minuto." |
| 500 | Error interno | "El servidor tuvo un problema. Intenta de nuevo." |

Hacia afuera nunca sale el detalle de un error interno ni de un error al leer el pedido: eso queda
en el registro del servidor. Después de una respuesta de error el servidor cierra esa conexión.

## 5.6 Compatibilidad

- Los campos se agregan, no se renombran. Un cliente debe ignorar los que no conoce.
- Si cambia una pregunta o una escala de la encuesta, hay que cambiarla en
  `backend/scripts/probar_modelo.py` y en `frontend/src/vivo/encuesta.ts`. La caché se invalida sola.
- Si se agrega o cambia un parámetro de filtro, va en `backend/servidor/sociedad.py` y en
  `frontend/src/vivo/sociedad.ts`, con las mismas claves y el mismo orden de opciones.
