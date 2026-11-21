import datos from '../datos/geografia.json';
import { crearAzar } from '../dominio/azar';
import { dentro } from '../dominio/poblacion';
import { aGeografia, aMundo, ALTO_MUNDO, ANCHO_MUNDO, LAT_NORTE, LON_OESTE } from './proyeccion';

type Anillo = number[][];

interface Geografia {
  land: Anillo[][];
  regions: Anillo[][];
}

const geografia = datos as Geografia;

export const REGIONES_GEO: Anillo[][] = geografia.regions;

/** Una zona urbana (ciudad o pueblo) de una comuna, con cuántas personas viven en ella. */
export interface ZonaUrbana {
  personas: number;
  anillos: Anillo[];
}

/**
 * Una comuna de la cartografía del Censo 2024 (`backend/scripts/construir_comunas.py`): sus
 * anillos en [lon, lat], sin las islas oceánicas que el mapa no dibuja, un punto que con
 * certeza cae dentro (para cuando no tiene anillos dibujables o el sorteo de un lugar falla) y
 * sus zonas urbanas, dentro del límite urbano del INE.
 */
export interface ComunaGeo {
  region: number;
  anillos: Anillo[];
  interior: number[];
  urbano?: ZonaUrbana[];
}

/** Comunas por código INE. */
export type ComunasGeo = Record<string, ComunaGeo>;

let comunas: ComunasGeo | null = null;
let cargando: Promise<ComunasGeo> | null = null;

/**
 * Los polígonos de las comunas. Pesan unos 375 KB, así que van en un archivo aparte que se pide
 * recién al conectarse; si no llega, queda vacío y cada punto se ubica como antes, por región.
 */
export function cargarComunas(): Promise<ComunasGeo> {
  cargando ??= import('../datos/comunas.json')
    .then((modulo) => (comunas = (modulo.default as { comunas: ComunasGeo }).comunas))
    .catch(() => (comunas = {}));
  return cargando;
}

/** Las comunas, si ya se cargaron. */
export function comunasCargadas(): ComunasGeo | null {
  return comunas;
}

/** Si un punto cae dentro de un polígono de varios anillos, por paridad: respeta los huecos. */
export function dentroDe(lon: number, lat: number, anillos: Anillo[]): boolean {
  let adentro = false;
  for (const anillo of anillos) if (dentro(lon, lat, anillo)) adentro = !adentro;
  return adentro;
}

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

/** Trazos de oleaje repartidos por el Pacífico, al oeste de la costa. */
export function crearOlas(): Ola[] {
  const azar = crearAzar(1520);
  const olas: Ola[] = [];
  for (let y = 0.5; y < ALTO_MUNDO; y += 1.05) {
    const lat = LAT_NORTE - y;
    const [xCosta] = aMundo(costa(Math.max(-55.5, Math.min(-17.6, lat))), lat);
    for (let x = xCosta - 0.7; x > -ANCHO_MUNDO; x -= 1.5) {
      const ox = x + (azar() - 0.5) * 0.7;
      const oy = y + (azar() - 0.5) * 0.7;
      if (!enTierra(...aGeografia(ox, oy))) olas.push({ x: ox, y: oy, fase: azar() * 6.28 });
    }
  }
  return olas;
}

export interface Rotulo {
  texto: string;
  x: number;
  y: number;
  /** Posición horizontal del texto en el mundo: mar adentro o al otro lado de la cordillera. */
  xTexto: number;
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
  ['Punta Arenas', -70.91, -53.16, true],
];

export const ROTULOS: Rotulo[] = CIUDADES.map(([texto, lon, lat, haciaElMar]) => {
  const [x, y] = aMundo(lon, lat);
  const borde = haciaElMar ? costa(lat) - 0.45 : limiteOriental(lat) + 0.5;
  return { texto, x, y, xTexto: aMundo(borde, lat)[0], haciaElMar };
});

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
