import type { Persona } from '../dominio/tipos';
import { REGIONES_GEO } from './geografia';
import { aGeografia, aMundo } from './proyeccion';

/** Separación mínima entre figuras, en unidades del mundo. Más apretada en vertical: se leen como filas de gente. */
const DX = 0.1;
const DY = 0.11;
const PASADAS = 30;
const ATRACCION = 0.03;

type Caja = [number, number, number, number];

const cajas: Caja[][] = REGIONES_GEO.map((region) =>
  region.map((anillo) => {
    const lons = anillo.map((p) => p[0]);
    const lats = anillo.map((p) => p[1]);
    return [Math.min(...lons), Math.min(...lats), Math.max(...lons), Math.max(...lats)];
  }),
);

function enChile(lon: number, lat: number): boolean {
  for (let r = 0; r < REGIONES_GEO.length; r++) {
    for (let a = 0; a < REGIONES_GEO[r].length; a++) {
      const [x0, y0, x1, y1] = cajas[r][a];
      if (lon < x0 || lon > x1 || lat < y0 || lat > y1) continue;
      const anillo = REGIONES_GEO[r][a];
      let adentro = false;
      for (let i = 0, j = anillo.length - 1; i < anillo.length; j = i++) {
        const [ax, ay] = anillo[i];
        const [bx, by] = anillo[j];
        if (ay > lat !== by > lat && lon < ((bx - ax) * (lat - ay)) / (by - ay) + ax) adentro = !adentro;
      }
      if (adentro) return true;
    }
  }
  return false;
}

function separar(x: Float32Array, y: Float32Array): void {
  const n = x.length;
  for (let i = 0; i < n; i++) {
    for (let j = i + 1; j < n; j++) {
      const ex = (x[i] - x[j]) / DX;
      if (ex > 1 || ex < -1) continue;
      const ey = (y[i] - y[j]) / DY;
      const d2 = ex * ex + ey * ey;
      if (d2 >= 1) continue;
      const d = Math.sqrt(d2) || 0.01;
      const empuje = (1 - d) / 2 / d;
      const mx = (ex || 0.01) * empuje * DX;
      const my = (ey || 0.01) * empuje * DY;
      x[i] += mx;
      y[i] += my;
      x[j] -= mx;
      y[j] -= my;
    }
  }
}

export interface Multitud {
  x: Float32Array;
  y: Float32Array;
  /** Índices ordenados de atrás hacia adelante (cordillera primero, costa al final). */
  orden: Uint16Array;
  minX: number;
  maxX: number;
}

/**
 * Ubica a cada persona cerca de su punto de origen sin que las figuras se tapen por
 * completo: las capitales pobladas se vuelven una multitud que se abre alrededor.
 */
export function crearMultitud(personas: Persona[]): Multitud {
  const n = personas.length;
  const x = new Float32Array(n);
  const y = new Float32Array(n);
  const ax = new Float32Array(n);
  const ay = new Float32Array(n);
  personas.forEach((persona, i) => {
    [ax[i], ay[i]] = aMundo(persona.lon, persona.lat);
    x[i] = ax[i];
    y[i] = ay[i];
  });
  for (let pasada = 0; pasada < PASADAS; pasada++) {
    separar(x, y);
    for (let i = 0; i < n; i++) {
      x[i] += (ax[i] - x[i]) * ATRACCION * 0.3;
      y[i] += (ay[i] - y[i]) * ATRACCION;
      // Quien quedó en el mar o al otro lado de la frontera vuelve hacia tierra sin
      // devolverse a lo largo del país: la multitud se estira de norte a sur.
      if (pasada % 3 === 2 && !enChile(...aGeografia(x[i], y[i]))) y[i] += (ay[i] - y[i]) * 0.6;
    }
  }
  const orden = Uint16Array.from(Array.from({ length: n }, (_, i) => i).sort((a, b) => y[a] - y[b]));
  let minX = Infinity;
  let maxX = -Infinity;
  for (let i = 0; i < n; i++) {
    minX = Math.min(minX, x[i]);
    maxX = Math.max(maxX, x[i]);
  }
  return { x, y, orden, minX, maxX };
}
