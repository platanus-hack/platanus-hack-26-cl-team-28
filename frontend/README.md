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

- `api.ts`: `GET /api/estado`, `POST /api/muestra` (el motor filtra la población y sortea a quiénes preguntar; cada cambio de filtros o de
  nivel de clusterización pide una muestra nueva y el mapa solo reacomoda los puntos),
  `POST /api/documentos`, `POST /api/corridas` y los eventos de
  la corrida por `EventSource` (`inicio`, `respuestas`, `caso_listo`, `voces`, `redactando`, `caso`, `aviso`, `fin`, `falla`).
- `poblacion.ts`: dibuja a cada agente real con varios puntos dentro de su comuna (`datos/comunas.json`, de
  `backend/scripts/construir_comunas.py`): en una de sus ciudades o pueblos si vive en zona urbana, en el resto
  de la comuna si vive en zona rural. Todos los puntos de un agente responden lo mismo.
- `useEnVivo.ts`: el estado de la herramienta (variantes, muestra, corrida). Las respuestas llegan por lotes y se
  guardan por agente (sus notas de 1 a 7, una por pregunta); con la primera, 5 a 7 es a favor, 4 indecisa, 1 a 3 en contra. Las
  frases llegan aparte (`voces`), solo para algunas personas. Las variantes
  que escribe el agente llegan durante la corrida como casos nuevos. Al terminar una variante, la interfaz la
  muestra unos segundos y pasa a la siguiente.
- `encuesta.ts`: las preguntas de la encuesta. Se editan en el cajón «Encuesta» (`enjambre/CajonEncuesta.tsx`), quedan
  guardadas en el navegador y viajan en cada corrida. `resumirEncuesta` saca el resultado de cada pregunta, que
  se muestra junto a las cifras (`enjambre/ResultadoEncuesta.tsx`): reparto entre en desacuerdo, al medio y de
  acuerdo, y la diferencia con la variante A. La primera pregunta decide el color de cada punto.
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
