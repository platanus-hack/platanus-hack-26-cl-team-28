import datos from '../datos/geografia.json';
import { crearAzar } from '../dominio/azar';
import { aGeografia, aMundo, ALTO_MUNDO, ANCHO_MUNDO, LAT_NORTE, LON_OESTE } from './proyeccion';

type Anillo = number[][];

interface Geografia {
  land: Anillo[][];
  regions: Anillo[][];
}

const geografia = datos as Geografia;

export const REGIONES_GEO: Anillo[][] = geografia.regions;

function trazar(anillos: Anillo[]): Path2D {
  const camino = new Path2D();
  for (const anillo of anillos) {
    anillo.forEach(([lon, lat], i) => {
      const [x, y] = aMundo(lon, lat);
      if (i === 0) camino.moveTo(x, y);
      else camino.lineTo(x, y);
    });
    camino.closePath();
  }
  return camino;
}

export interface Caminos {
  vecinos: Path2D;
  regiones: Path2D[];
  chile: Path2D;
}

export function crearCaminos(): Caminos {
  return {
    vecinos: trazar(geografia.land.flat()),
    regiones: geografia.regions.map(trazar),
    chile: trazar(geografia.regions.flat()),
  };
}

/** Longitudes donde los anillos de Chile cruzan una latitud dada. */
function cruces(lat: number): number[] {
  const lons: number[] = [];
  for (const region of geografia.regions) {
    for (const anillo of region) {
      for (let i = 0, j = anillo.length - 1; i < anillo.length; j = i++) {
        const [ax, ay] = anillo[i];
        const [bx, by] = anillo[j];
        if (ay > lat !== by > lat) lons.push(((bx - ax) * (lat - ay)) / (by - ay) + ax);
      }
    }
  }
  return lons;
}

/** Longitud de la costa del Pacífico a una latitud (sin contar islas oceánicas). */
export function costa(lat: number): number {
  const lons = cruces(lat).filter((lon) => lon > LON_OESTE);
  return lons.length ? Math.min(...lons) : -72;
}

export function limiteOriental(lat: number): number {
  const lons = cruces(lat);
  return lons.length ? Math.max(...lons) : -69;
}

export interface Cumbre {
  x: number;
  y: number;
  alto: number;
  lejana: boolean;
}

/** Cumbres dibujadas a lo largo del límite oriental: la cordillera como telón de fondo. */
export function crearCordillera(): Cumbre[] {
  const azar = crearAzar(1881);
  const cumbres: Cumbre[] = [];
  for (let lat = -17.8; lat > -52.5; lat -= 0.34) {
    const borde = limiteOriental(lat);
    const tamano = lat > -38 ? 0.62 : lat > -46 ? 0.46 : 0.34;
    for (const lejana of [true, false]) {
      const [x, y] = aMundo(borde + (lejana ? 0.42 : 0.08) + (azar() - 0.5) * 0.12, lat + (azar() - 0.5) * 0.2);
      cumbres.push({ x, y, alto: tamano * (0.7 + azar() * 0.6) * (lejana ? 0.72 : 1), lejana });
    }
  }
  return cumbres;
}

export interface Ola {
  x: number;
  y: number;
  fase: number;
}

function enTierra(lon: number, lat: number): boolean {
  const adentro = (anillo: Anillo) => {
    let hit = false;
    for (let i = 0, j = anillo.length - 1; i < anillo.length; j = i++) {
      const [ax, ay] = anillo[i];
      const [bx, by] = anillo[j];
      if (ay > lat !== by > lat && lon < ((bx - ax) * (lat - ay)) / (by - ay) + ax) hit = !hit;
    }
    return hit;
  };
  return geografia.land.flat().some(adentro);
}

/** Trazos de oleaje repartidos por el Pacífico, lejos de la costa. */
export function crearOlas(): Ola[] {
  const azar = crearAzar(1520);
  const olas: Ola[] = [];
  for (let x = 0.6; x < ANCHO_MUNDO; x += 1.25) {
    const lat = LAT_NORTE - x;
    const [, yCosta] = aMundo(costa(Math.max(-55.5, Math.min(-17.6, lat))), lat);
    for (let y = yCosta + 0.55; y < ALTO_MUNDO + 3; y += 0.85) {
      const ox = x + (azar() - 0.5) * 0.9;
      const oy = y + (azar() - 0.5) * 0.3;
      if (!enTierra(...aGeografia(ox, oy))) olas.push({ x: ox, y: oy, fase: azar() * 6.28 });
    }
  }
  return olas;
}

export interface Rotulo {
  texto: string;
  x: number;
  y: number;
  /** Altura del mundo donde va el texto: pasado la costa o pasado el límite oriental. */
  yTexto: number;
  haciaElMar: boolean;
}

const CIUDADES: [string, number, number, boolean][] = [
  ['Arica', -70.31, -18.48, true],
  ['Antofagasta', -70.39, -23.65, true],
  ['La Serena', -71.25, -29.92, true],
  ['Santiago', -70.64, -33.45, true],
  ['Concepción', -73.05, -36.83, true],
  ['Puerto Montt', -72.94, -41.47, true],
  ['Coyhaique', -72.07, -45.57, false],
  ['Punta Arenas', -70.91, -53.16, false],
];

export const ROTULOS: Rotulo[] = CIUDADES.map(([texto, lon, lat, haciaElMar]) => {
  const [x, y] = aMundo(lon, lat);
  const borde = haciaElMar ? costa(lat) - 0.5 : limiteOriental(lat) + 0.55;
  return { texto, x, y, yTexto: aMundo(borde, lat)[1], haciaElMar };
});

export const PAISES: { texto: string; x: number; y: number }[] = [
  { texto: 'ARGENTINA', ...punto(-66.9, -36) },
  { texto: 'BOLIVIA', ...punto(-66.9, -20.4) },
  { texto: 'OCÉANO PACÍFICO', ...punto(-75.5, -33.2) },
];

function punto(lon: number, lat: number): { x: number; y: number } {
  const [x, y] = aMundo(lon, lat);
  return { x, y };
}

export interface Caja {
  x: number;
  y: number;
  w: number;
  h: number;
}

/** Caja de cada región en el mundo, sin contar islas oceánicas. */
export const CAJAS_REGION: Caja[] = geografia.regions.map((region) => {
  const puntos = region.flat().filter(([lon]) => lon > LON_OESTE).map(([lon, lat]) => aMundo(lon, lat));
  const xs = puntos.map((p) => p[0]);
  const ys = puntos.map((p) => p[1]);
  const x = Math.min(...xs);
  const y = Math.min(...ys);
  return { x, y, w: Math.max(...xs) - x, h: Math.max(...ys) - y };
});
