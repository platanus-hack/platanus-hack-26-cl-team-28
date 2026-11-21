import { crearAzar } from './azar';
import { EDAD_MINIMA, REGIONES } from './catalogos';
import type { Persona } from './tipos';

type Anillo = number[][];

const SEMILLA = 281126;
const INTENTOS = 40;

function dentro(lon: number, lat: number, anillo: Anillo): boolean {
  let adentro = false;
  for (let i = 0, j = anillo.length - 1; i < anillo.length; j = i++) {
    const [ax, ay] = anillo[i];
    const [bx, by] = anillo[j];
    if (ay > lat !== by > lat && lon < ((bx - ax) * (lat - ay)) / (by - ay) + ax) adentro = !adentro;
  }
  return adentro;
}

function elegirRegion(azar: () => number): number {
  const total = REGIONES.reduce((suma, region) => suma + region.peso, 0);
  let resto = azar() * total;
  for (let i = 0; i < REGIONES.length; i++) {
    resto -= REGIONES[i].peso;
    if (resto < 0) return i;
  }
  return REGIONES.length - 1;
}

/** Sorteo con forma de campana (Box-Muller), para que la gente se junte en torno a la capital sin bordes rectos. */
function campana(azar: () => number): number {
  return Math.sqrt(-2 * Math.log(1 - azar())) * Math.cos(2 * Math.PI * azar());
}

function ubicar(region: number, poligonos: Anillo[], azar: () => number): [number, number] {
  const { capitalLon, capitalLat } = REGIONES[region];
  // La mayoría vive cerca de la capital regional; el resto se reparte más lejos.
  const radio = azar() < 0.3 ? 1.1 : 0.32;
  for (let intento = 0; intento < INTENTOS; intento++) {
    const lon = capitalLon + campana(azar) * radio;
    const lat = capitalLat + campana(azar) * radio;
    if (poligonos.some((anillo) => dentro(lon, lat, anillo))) return [lon, lat];
  }
  return [capitalLon, capitalLat];
}

/**
 * Población sintética ilustrativa: la ubicación sigue el peso de cada región y los
 * atributos son sorteos independientes. No representa datos censales.
 */
export function crearPoblacion(cantidad: number, regiones: Anillo[][]): Persona[] {
  const azar = crearAzar(SEMILLA);
  const personas: Persona[] = [];
  for (let id = 0; id < cantidad; id++) {
    const region = elegirRegion(azar);
    const [lon, lat] = ubicar(region, regiones[region], azar);
    const genero = azar();
    personas.push({
      id,
      region,
      lon,
      lat,
      edad: EDAD_MINIMA + Math.floor(azar() ** 1.55 * 73),
      genero: genero < 0.49 ? 0 : genero < 0.977 ? 1 : genero < 0.993 ? 2 : 3,
      quintil: Math.floor(azar() * 5),
      educacion: Math.min(4, Math.floor(azar() ** 1.45 * 5)),
      politica: Math.floor(azar() * 6),
      aspecto: Math.floor(azar() * 6),
    });
  }
  return personas;
}
