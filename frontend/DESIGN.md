# Diseño del front

Hay dos diseños sobre el mismo dominio y el mismo simulador:

- **Diseño 2, "Chile se abre"** (el que abre por defecto): pensado para impactar en la demo. Se describe aquí abajo.
- **Diseño 1, "mapa ilustrado"** (`?d=1` en la dirección, etiqueta de git `diseno-1-mapa-ilustrado`): el mapa con
  criaturas y la hoja de información a la derecha. Se describe desde "Diseño 1" en adelante.

## Diseño 2: Chile se abre

**Idea.** Chile va en su proporción real, de pie y a todo el alto de la pantalla. Es angosto, y eso se usa: el país
es el eje de un gráfico hecho con su propia gente. Cada persona simulada es un punto. En reposo los puntos dibujan
el país, densos donde vive más gente. Al preguntar, una ola baja de norte a sur y cada punto despega: quienes están
a favor vuelan a la derecha y quienes están en contra a la izquierda, y se juntan en una burbuja por región, a la
altura de su región. Quien está indecisa se queda en el mapa. El país se abre en dos.

**Por qué impacta.** Se entiende sin leer: el lado más cargado gana, las burbujas grandes son las regiones con más
gente, y al cambiar de variante se ve a la gente cruzar de un lado al otro.

**Lo que se lee.** Dos cifras gigantes, una por lado, cada una con su criatura, que crece con su porcentaje. Arriba,
la variante. Nada más compite con el mapa.

**Para quién se diseñó.** Una demo de 3 minutos en proyector ante un jurado. La investigación de demos anteriores de
Platanus mostró que un simulador de políticas con agentes (HIVE, Bogotá 2026) perdió porque el jurado no le creyó
a la simulación y su pantalla solo mostraba agregados en letra chica. Por eso cada momento contesta "¿es real?" con
algo que se ve: personas con nombre de comuna, frases propias, el costo medido y una encuesta real al lado.

**Momentos de la demo.**

1. *Entrada.* Titular "Sabe cómo reacciona Chile a una ley antes de aprobarla", bajada con el tamaño de la muestra y
   "Validado contra encuestas Cadem". El mapa ya muestra a los agentes reales en su comuna. Tres casos con encuesta
   real se cargan con un toque.
2. *Los agentes piensan.* Los puntos de la muestra se apagan y laten en ondas que bajan por el país. A la izquierda,
   el contador, la línea "Pensando ahora" con personas de la muestra pasando rápido y, al llegar respuestas, las
   llamadas, segundos y dólares que mide el motor.
3. *Responden.* Cada punto se enciende con su color cuando su agente termina. Frases reales aparecen junto al punto
   de quien las dijo: a la derecha alguien a favor, a la izquierda alguien en contra, como vuelan después.
4. *El país se abre.* La ola baja de norte a sur y los puntos vuelan a burbujas por región con su porcentaje; cifras
   gigantes a cada lado.
5. *¿Le creemos?* Si la variante tiene encuesta real, la comparación ocupa el centro unos segundos (Cadem contra
   agentes, en cifras de 8 rem) y luego queda en la esquina.
6. *El agente reescribe.* Con iteraciones, un agente lee las objeciones y lo que valoran quienes apoyan, y escribe una
   versión nueva con titular corto y qué cambió. Se vuelve a preguntar a las mismas personas; bajo la cifra a favor
   aparece "+N puntos con la versión del agente" y cuántas personas que no apoyaban la A ahora la apoyan.
7. *Conocer a alguien.* En resultados, tocar un punto abre la ficha de esa persona: quién es según el censo, su frase y
   cuánto apoyó cada variante.

**Honestidad en pantalla.** La esquina superior derecha dice siempre qué responde: "En vivo" con el modelo, "Corrida
grabada" o "Demostración sin motor". Lo que viene de caché se reproduce en seis segundos y lo dice. Sin motor no se
ofrece la comparación con Cadem.

**Interfaz mínima y ocultable.** Abajo a la izquierda, el mando: variantes, texto, casos con encuesta real, subir una
ley (o soltarla encima), iteraciones del agente y el botón de preguntar. Con resultados, pestañas por variante con su
porcentaje y la diferencia contra la A. Abajo a la derecha, Opciones (agentes a consultar y filtros, fondo claro u
oscuro, ocultar). La tecla H oculta todo; las flechas cambian de variante.

**Pantallas angostas y bajas.** En angostas todo va en una columna; en bajas (hasta 800 px de alto) las cifras bajan
para no chocar con la tarjeta de la encuesta.

**Sistema.** Fondo oscuro y plano, sin brillos ni degradados; tema claro para salas con mucha luz
(`src/enjambre/tema.css`). Rótulos de región que crecen con la pantalla (hasta 16 px) para leerse en un proyector.

**Código.** `src/enjambre/`: `EscenaEnjambre.ts` (canvas), `disposicion.ts` (burbujas, con prueba), `AppEnjambre.tsx`,
`BloqueAvance.tsx`, `Pensando.tsx`, `Voces.tsx`, `Validacion.tsx`, `Redactando.tsx`, `FichaAgente.tsx`,
`BarraResultado.tsx`, `BarraMando.tsx`, `Insignia.tsx`. La conexión con el motor está en `src/vivo/`.

**Medido.** 60 cuadros por segundo con 10.000 puntos durante toda una corrida en 1920 por 1080 (p99 de 17 ms).

**Pendiente.** En móvil el mapa queda chico y sin rótulos; la ficha solo se abre tocando un punto (no hay camino
por teclado).

# Diseño 1: Chile a pantalla completa

Contrato de diseño de la herramienta. Rediseño completo (tamaño L) del prototipo base de un solo `index.html`.

## Lo vigente y lo que se conserva

El prototipo base tenía un mapa de Chile vertical en una tarjeta a la izquierda, puntos negros y verdes para la
población, un formulario de casos y filtros a la derecha y una "previsualización" que solo repetía la configuración.

Se conserva: la geografía (geoBoundaries y Natural Earth, ahora en `src/datos/geografia.json`), el catálogo de
regiones con sus pesos, los filtros y sus opciones, los tamaños de muestra, los dos casos de ejemplo, el control del
mapa por teclado y la idea central: varios casos sobre la misma población.

Cambia: todo lo visual, la orientación del mapa, la representación de las personas y la etapa de resultados, que no
existía.

## Dirección

Default descartado: papel crema, verde tinta, serif con cursiva y tarjetas blancas redondeadas (era el aspecto del
prototipo y es el reflejo habitual de un modelo).

Direcciones consideradas:

1. **Chile de pie, a pantalla completa** (elegida). El mapa ocupa todo el lado izquierdo de la pantalla, con el norte
   arriba, y la información vive en una hoja a la derecha. Se probó primero con el país acostado (norte a la
   izquierda) para llenar el ancho; se descartó porque el mapa se leía raro y obligaba a apilar los paneles en
   poco alto, con scrolls internos.
2. Papeleta electoral: tipografía de voto impreso, timbres y casillas. Descartada: no deja lugar al mapa.
3. Cabildo en la plaza: la gente reunida sin geografía. Descartada: se pierde la lectura territorial.

Recurso propio: la franja de regiones corre de norte a sur pegada al mapa, unida a cada región con líneas guía, y la multitud cambia de postura con un salto
al cambiar de variante, de modo que se ve quién cambia de opinión.

Tres colores de postura sobre mar frío: verde azulado (a favor), ámbar (indecisa) y bermellón (en contra). El color
nunca va solo: a favor levanta los brazos y entrecierra los ojos, indecisa se ladea con una ceja levantada bajo un
signo de pregunta, en contra se eriza y baja los párpados. Toda barra lleva su porcentaje escrito.

Las figuras no son personas dibujadas: son criaturas de forma simple, con cuerpo de color plano, contorno del mismo
tono, pies cortos, dos ojos de tinta y algo en la cabeza (una hoja, un mechón, orejas, una antena). Antes de
responder cada una tiene un tono apagado propio; al responder toma el color de su postura y cambia de cara. Se
probaron ojos con brillo y mejillas y se descartaron por infantiles.

**Densidad según la distancia.** De lejos, las figuras que quedarían encimadas se funden en una sola más grande, con
la postura de la mayoría de su grupo: Santiago se ve como pocas figuras grandes y un pueblo como una chica, así la
diferencia de población se lee de un vistazo. Al acercarse, los grupos se abren hasta llegar a figuras sueltas. Un
clic en un grupo acerca el mapa; en una figura sola, la elige. El mapa exagera el ancho del país (no está a escala)
para darle lugar a la gente.

Tres voces tipográficas con función fija: Newsreader (serif) es la voz del análisis: titulares y cifras. Hanken
Grotesk es la de los controles. Shantell Sans, escrita a mano, es la voz de la gente y de las anotaciones del mapa.

## Sistema

Tokens en `src/estilos/tokens.css`; el lienzo los lee con `src/mapa/tokens.ts`, así el mapa y la interfaz comparten
valores. Sin sombras: las superficies se separan con un filete de tinta de 1,5 px. Radios de 6 y 2 px. Motion: 160 ms
en controles, 280 ms en barras, 450 ms el salto de una figura, 2,6 s el barrido de una variante.

## Composición

**1080 px o más.** Dos columnas a todo el alto. A la izquierda el mapa, que llena su columna: controles y leyenda
arriba a la izquierda, ciudades rotuladas mar adentro y, en resultados, la franja de regiones en el borde derecho
del mapa, alineada por latitud. A la derecha la hoja de información (entre 540 y 780 px), con un solo scroll y sin
alturas forzadas: cabecera, titular con la cifra principal y las secciones una debajo de otra, con aire.

**Bajo 1080 px.** El mapa arriba (72 % del alto) con el país entero y, debajo, la hoja en una columna. La franja de
regiones pasa a lista.

El mapa ensancha el país unas dos veces y media de este a oeste para que la gente quepa encima: es un mapa
ilustrado, no a escala.

## Escena

Canvas 2D. Clase `EscenaMapa` (`montar`, `destruir`) con una capa estática (mar, vecinos, regiones, cordillera) que
solo se redibuja cuando se mueve la cámara, y una capa viva (olas, personas, rótulos, globo). Las figuras salen de un
atlas de sprites pregenerado: 6 aspectos por 5 estados por 3 cuadros, en dos tamaños. El trazo "hierve" a seis
cuadros por segundo como dibujo a mano. El agrupamiento vive en `src/mapa/agrupar.ts` (función pura, con prueba).

## Coreografía

| Momento | Disparador | Qué pasa | Con movimiento reducido |
|---|---|---|---|
| Entrada | Carga | La gente aparece creciendo desde los pies, en ola de norte a sur (1,6 s) | Aparece completa |
| Reposo | Siempre | Respiración leve, trazo que hierve, olas que derivan | Todo quieto |
| Filtro | Cambio en la muestra | Quien sale queda en contorno tenue; quien entra salta | Cambio directo |
| Barrido | Preguntar | Una línea con la etiqueta de la variante baja por el país en 2,6 s; cada figura muestra un globo y toma postura con un salto; el conteo del tablero crece al mismo ritmo | Resultado directo |
| Cambio de variante | Elegir otra variante | Solo saltan quienes cambian de postura, en ola de 0,5 s; barras a 280 ms | Cambio directo |
| Región | Elegir en la franja | La cámara se acerca en 0,6 s y la región queda contorneada | Salto de cámara |
| Persona | Clic en figura o en una voz | Anillo bajo los pies, globo con su frase, ficha con su respuesta en cada variante | Igual, sin animación |

## Estados

Sin personas en la muestra (cifra en cero, botón deshabilitado y aviso), menos de dos variantes escritas, menos
perfiles disponibles que los pedidos, región con pocos datos (columna punteada y "pocos datos"), sin JavaScript
(aviso en `noscript`). El foco usa un anillo cobalto de 2 px; los tocables miden 44 px.

## Contenido

Las respuestas vienen de `simuladorDemostracion` y la interfaz lo dice en la cabecera y en el pie del tablero. La
población es sintética e ilustrativa. Las frases de las voces se arman con la postura y el motivo y se rotulan como
ilustrativas. No hay cifras escritas en textos: todas salen de `dominio/metricas.ts`.

## Evidencia

Capturas del flujo en 1440, 1920, 1366x768 y 390; detector de defectos del laboratorio; 60 cuadros por segundo
medidos en entrada, reposo, barrido, cambio de variante y zoom, en 1440 y 390, a doble densidad.
