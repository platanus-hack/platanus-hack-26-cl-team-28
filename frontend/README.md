# Front de Simulaciones

React, TypeScript y Vite. El mapa es un canvas 2D propio, sin librerías de mapas.

    npm install
    npm run dev       # http://127.0.0.1:5280 (diseño 2, conectado al motor) y /?d=1 (diseño 1, demostración)
    npm test          # pruebas del dominio
    npm run build     # compila a dist/

En desarrollo, Vite reenvía `/api` al motor en `http://127.0.0.1:8787` (ver `backend/servidor/README.md`). Para
otro servidor, compila con `VITE_API=https://.../api`. Si el motor no responde, la interfaz entra en modo
demostración (acuerdos sorteados en el navegador, sin frases) y lo dice en la esquina superior derecha.

## Cómo se conecta

`src/vivo/` es todo lo que habla con el motor:

- `api.ts`: `GET /api/estado`, `GET /api/agentes`, `POST /api/documentos`, `POST /api/corridas` y los eventos de
  la corrida por `EventSource` (`inicio`, `respuestas`, `caso_listo`, `redactando`, `caso`, `aviso`, `fin`, `error`).
- `poblacion.ts`: dibuja a cada agente real con varios puntos alrededor del centro de su comuna, para que la
  densidad del país se lea. Todos los puntos de un agente responden lo mismo.
- `useEnVivo.ts`: el estado de la herramienta (variantes, muestra, corrida). Las respuestas llegan por lotes y se
  guardan por agente (acuerdo de 1 a 7 y su frase); 5 a 7 es a favor, 4 indecisa, 1 a 3 en contra. Las variantes
  que escribe el agente llegan durante la corrida como casos nuevos. Al terminar una variante, la interfaz la
  muestra unos segundos y pasa a la siguiente.
- `validacion.ts`: políticas con encuesta Cadem publicada, para comparar en pantalla lo que dijeron los agentes
  con lo que dijo la gente.

## Estructura

- `src/vivo/`: conexión con el motor y estado de la corrida en vivo.
- `src/enjambre/`: el diseño principal, "Chile se abre" (escena de puntos, burbujas, voces, ficha, validación).
- `src/dominio/`: tipos, catálogos, métricas y el simulador de demostración del diseño 1. Sin React.
- `src/mapa/`: la escena del diseño 1 (`?d=1`) y el dibujo de las criaturas, que usan ambos diseños.
- `src/estado/`: el estado del diseño 1 y los borradores de variantes, que comparten ambos.
- `src/componentes/`: un componente por archivo con su hoja de estilos.
- `DESIGN.md`: el contrato de diseño.
