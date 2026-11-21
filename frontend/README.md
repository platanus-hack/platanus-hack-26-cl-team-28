# Front de Simulaciones

React, TypeScript y Vite. El mapa es un canvas 2D propio, sin librerías de mapas.

    npm install
    npm run dev       # http://127.0.0.1:5280 (diseño 2) y http://127.0.0.1:5280/?d=1 (diseño 1)
    npm test          # pruebas del dominio (métricas, muestra, simulador de demostración)
    npm run build     # compila a dist/

## Conectar el motor de simulación

Hoy las respuestas salen de `crearSimuladorDemostracion` (`src/dominio/simulador.ts`), que las genera en el navegador
para probar la interfaz. Para conectar el backend basta implementar la misma interfaz y cambiar una línea en
`src/estado/useSimulacion.ts` (donde dice `crearSimuladorDemostracion`):

    interface Simulador {
      nombre: string;
      esDemostracion: boolean;   // en falso desaparecen los avisos de demostración
      simular(casos, personas, alAvanzar?): Promise<ResultadoCaso[]>;
      proponerIteraciones(base, cantidad): Promise<{ texto, iteracion }[]>;
    }

**Qué recibe `simular`.** Los casos y las personas de la muestra. Cada caso trae `id`, `letra`, `texto` y, si se
subió un archivo, `documento` (`nombre`, `tamano` y `archivo`, que es el `File` tal cual: una ley completa, por
ejemplo). Si el caso lo propuso el agente trae `iteracion` (`de`: letra de la variante de origen, `numero`). Cada
persona trae `region`, `edad`, `genero`, `quintil`, `educacion` y `politica` (catálogos en `src/dominio/catalogos.ts`).

**Qué devuelve.** Por cada caso, una respuesta por persona en el mismo orden:

    { postura: 'favor' | 'contra' | 'indecisa', firmeza: 0..1, accion: índice de ACCIONES, razon: índice de RAZONES }

**Respuestas en vivo.** Mientras los agentes corren en paralelo, llama a `alAvanzar({ caso, persona, respuesta })`
cada vez que uno termina, en cualquier orden (`persona` es su posición en la lista recibida). El mapa enciende ese
punto de inmediato. Hoy la interfaz muestra en vivo el caso 0; los demás se ven al terminar. Con un stream (SSE o
WebSocket) esto es llamar a `alAvanzar` por cada evento y resolver la promesa al final.

**Iteraciones.** Si la persona marca "que un agente proponga iteraciones", la interfaz llama antes a
`proponerIteraciones(base, cantidad)` con la primera variante y agrega lo que devuelva como variantes nuevas.

Todo lo que se ve en resultados (porcentajes, burbujas por región, cifras) se calcula de esas respuestas en
`src/dominio/metricas.ts`.

Pendiente de la integración: el mapa dibuja 10.000 puntos (5.000 en pantallas angostas) y cada uno representa a
una parte igual de la muestra. Si el motor entrega más o menos respuestas que puntos, hay que agregarlas o
repartirlas por punto antes de pintarlas.

## Estructura

- `src/dominio/`: tipos, catálogos, población sintética, muestra, simulador y métricas. Sin React.
- `src/enjambre/`: el diseño principal, "Chile se abre" (escena de puntos, burbujas, barra de mando, opciones).
- `src/mapa/`: la escena del diseño 1 (`?d=1`) y el dibujo de las criaturas, que usan ambos diseños.
- `src/estado/`: el estado de la herramienta y la corrida.
- `src/componentes/`: un componente por archivo con su hoja de estilos.
- `DESIGN.md`: el contrato de diseño.
