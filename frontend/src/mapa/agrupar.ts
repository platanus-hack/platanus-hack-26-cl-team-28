/**
 * Agrupa figuras según la distancia a la que se mira el mapa. De lejos, quienes quedarían
 * encimados se funden en una sola figura más grande: una ciudad poblada se ve como pocas
 * figuras grandes y un pueblo como una chica. Al acercarse, los grupos se abren.
 */
export interface Agrupacion {
  /** Para cada figura, el índice de la figura que la representa (ella misma si se dibuja). */
  grupo: Int16Array;
  /** Para cada representante, cuántas figuras reúne; cero en las demás. */
  cuenta: Uint16Array;
}

const TOPE = 2.9;

/** Cuánto crece una figura que representa a `cuenta` figuras. */
export function factorTamano(cuenta: number): number {
  return Math.min(TOPE, cuenta ** 0.3);
}

interface Entrada {
  x: Float32Array;
  y: Float32Array;
  /** Orden en que las figuras reclaman lugar: las primeras quedan como representantes. */
  prioridad: ArrayLike<number>;
  /** Separación mínima entre dos figuras de tamaño uno, en unidades del mundo. */
  sx: number;
  sy: number;
}

export function agrupar({ x, y, prioridad, sx, sy }: Entrada): Agrupacion {
  const n = x.length;
  const grupo = new Int16Array(n).fill(-1);
  const cuenta = new Uint16Array(n);
  const distancia = (a: number, b: number) => Math.hypot((x[a] - x[b]) / sx, (y[a] - y[b]) / sy);
  const cercano = (i: number, lista: number[], alcance: (r: number) => number): number => {
    let mejor = -1;
    let menor = Infinity;
    for (const r of lista) {
      const d = distancia(i, r) / alcance(r);
      if (d < 1 && d < menor) {
        menor = d;
        mejor = r;
      }
    }
    return mejor;
  };

  // Primera pasada: cada figura se une a un representante que ya ocupa su lugar, o toma uno.
  const reps: number[] = [];
  for (let k = 0; k < n; k++) {
    const i = prioridad[k];
    const r = cercano(i, reps, () => 1);
    if (r < 0) reps.push(i);
    grupo[i] = r < 0 ? i : r;
    cuenta[grupo[i]] += 1;
  }

  // Segunda pasada: los grupos grandes ocupan más espacio y absorben a los que tapan.
  // El primero de la prioridad nunca se absorbe (es la figura elegida, si hay una).
  const fijo = prioridad[0];
  const orden = [...reps].sort((a, b) => (b === fijo ? 1 : 0) - (a === fijo ? 1 : 0) || cuenta[b] - cuenta[a]);
  const destino = new Int16Array(n).fill(-1);
  const aceptados: number[] = [];
  for (const r of orden) {
    const propio = factorTamano(cuenta[r]);
    const a = cercano(r, aceptados, (otro) => ((propio + factorTamano(cuenta[otro])) / 2) * 0.86);
    if (a < 0) {
      aceptados.push(r);
      continue;
    }
    destino[r] = a;
    cuenta[a] += cuenta[r];
    cuenta[r] = 0;
  }
  for (let i = 0; i < n; i++) if (destino[grupo[i]] >= 0) grupo[i] = destino[grupo[i]];
  return { grupo, cuenta };
}
