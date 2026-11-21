# Diseño del front: Chile visto desde el Pacífico

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

1. **Chile visto desde el Pacífico** (elegida). El país se dibuja acostado: norte a la izquierda, cordillera arriba
   como telón de fondo, mar abajo. Así un país de 4.300 km de largo llena el ancho de la pantalla, y la gente queda
   de pie sobre él como una multitud. El gráfico por región comparte eje con el mapa.
2. Papeleta electoral: tipografía de voto impreso, timbres y casillas. Descartada: no deja lugar al mapa.
3. Cabildo en la plaza: la gente reunida sin geografía. Descartada: se pierde la lectura territorial.

Recurso propio: la franja de regiones cuelga del mapa con líneas guía, y la multitud cambia de postura con un salto
al cambiar de variante, de modo que se ve quién cambia de opinión.

Paleta de tres tintas de imprenta sobre mar frío: azul cobalto (a favor), mostaza (indecisa) y bermellón (en contra),
con tinta azul negra para el trazo. El color nunca va solo: a favor levanta los brazos y sonríe, indecisa se ladea
bajo un signo de pregunta, en contra se eriza en púas y frunce el ceño. Toda barra lleva su porcentaje escrito.

Las figuras no son personas dibujadas: son criaturas redondas con patas cortas y dos ojos. Una multitud de siluetas
humanas sobre un mapa resultaba inquietante; una mascota abstracta representa a un grupo sin retratar a nadie.

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

**1080 px o más (una sola pantalla, sin scroll).** El lienzo del mapa es el fondo de toda la página. Encima, de
arriba abajo: cabecera (marca, etapas, aviso de demostración), titular (izquierda) con la cifra principal (derecha),
el hueco donde se encuadra Chile y el tablero, que ocupa el 43 % inferior (entre 340 y 400 px) con fondo de papel. La cabecera y el
titular quedan sobre Argentina y Bolivia; el tablero, sobre el mar.

**Bajo 1080 px.** Cabecera, mapa fijo arriba (un tercio del alto) con el país entero, y debajo el contenido en una
columna con scroll. La franja de regiones pasa a lista de dos columnas.

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
| Barrido | Preguntar | Una línea con la etiqueta de la variante cruza el país en 2,6 s; cada figura muestra un globo y toma postura con un salto; el conteo del tablero crece al mismo ritmo | Resultado directo |
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
