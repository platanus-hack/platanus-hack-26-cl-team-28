# Front de Simulaciones

React, TypeScript y Vite. El mapa es un canvas 2D propio, sin librerías de mapas.

    npm install
    npm run dev       # http://127.0.0.1:5280 (diseño 2) y http://127.0.0.1:5280/?d=1 (diseño 1)
    npm test          # pruebas del dominio (métricas, muestra, simulador de demostración)
    npm run build     # compila a dist/

## Conectar el motor de simulación

Hoy las respuestas salen de `simuladorDemostracion` (`src/dominio/simulador.ts`), que las genera en el navegador
para probar la interfaz. Para conectar el backend basta implementar la misma interfaz y cambiar una línea en
`src/estado/useSimulacion.ts`:

    interface Simulador {
      nombre: string;
      esDemostracion: boolean;   // en falso desaparecen los avisos de demostración
      simular(casos: Caso[], personas: Persona[]): Promise<ResultadoCaso[]>;
    }

El backend recibe los casos (`id`, `letra`, `texto`) y las personas de la muestra (`region`, `edad`, `genero`,
`quintil`, `educacion`, `politica`) y devuelve, por cada caso, una respuesta por persona en el mismo orden:

    { postura: 'favor' | 'contra' | 'indecisa', firmeza: 0..1, accion: índice de ACCIONES, razon: índice de RAZONES }

Los catálogos están en `src/dominio/catalogos.ts`. Todo lo que se ve en resultados (porcentajes, apoyo neto, brecha
entre regiones, movilización, franja por región, voces) se calcula de esas respuestas en `src/dominio/metricas.ts`.

Pendiente de la integración: hoy el mapa dibuja unas 680 figuras y cada una representa a una parte igual de la
muestra. Si el motor entrega más respuestas que figuras, hay que agregarlas por figura antes de pintarlas.

## Estructura

- `src/dominio/`: tipos, catálogos, población sintética, muestra, simulador y métricas. Sin React.
- `src/mapa/`: la escena (proyección, cámara, geografía, multitud, personajes, capas de dibujo).
- `src/estado/`: el estado de la herramienta y la corrida.
- `src/componentes/`: un componente por archivo con su hoja de estilos.
- `DESIGN.md`: el contrato de diseño.
