import { crearAzar } from '../dominio/azar';
import { REGIONES } from '../dominio/catalogos';
import { dentro } from '../dominio/poblacion';
import type { Persona } from '../dominio/tipos';
import type { AgenteRemoto } from './api';

type Anillo = number[][];

const SEMILLA = 2024;
const INTENTOS = 24;
/** Dispersión en grados alrededor del centro de la comuna: la ciudad se junta, el campo se abre. */
const DISPERSION_URBANA = 0.045;
const DISPERSION_RURAL = 0.16;
/** Quien no se ubica en la escala, o es menor de 18, va como "Sin identificación" (índice en POLITICA). */
const SIN_POLITICA = 5;

function campana(azar: () => number): number {
  return Math.sqrt(-2 * Math.log(1 - azar())) * Math.cos(2 * Math.PI * azar());
}

function ubicar(agente: AgenteRemoto, poligonos: Anillo[], azar: () => number): [number, number] {
  const region = REGIONES[agente.region];
  const lon0 = agente.lon || region.capitalLon;
  const lat0 = agente.lat || region.capitalLat;
  const radio = agente.atributos.Zona === 'Rural' ? DISPERSION_RURAL : DISPERSION_URBANA;
  for (let intento = 0; intento < INTENTOS; intento++) {
    const lon = lon0 + campana(azar) * radio;
    const lat = lat0 + campana(azar) * radio;
    if (poligonos.some((anillo) => dentro(lon, lat, anillo))) return [lon, lat];
  }
  return [lon0, lat0];
}

/**
 * Puntos del mapa a partir de los agentes reales: cada agente se dibuja con `porAgente` puntos
 * alrededor de su comuna, para que la densidad del país se lea. Todos los puntos de un agente
 * responden lo mismo, porque son la misma persona.
 */
export function poblacionDeAgentes(agentes: AgenteRemoto[], porAgente: number, regiones: Anillo[][]): Persona[] {
  const azar = crearAzar(SEMILLA);
  const personas: Persona[] = [];
  for (const agente of agentes) {
    for (let k = 0; k < porAgente; k++) {
      const [lon, lat] = ubicar(agente, regiones[agente.region], azar);
      personas.push({
        id: personas.length,
        agente: agente.i,
        region: agente.region,
        lon,
        lat,
        edad: agente.edad,
        genero: agente.genero,
        quintil: agente.quintil,
        educacion: agente.educacion,
        politica: agente.politica ?? SIN_POLITICA,
        aspecto: Math.floor(azar() * 6),
      });
    }
  }
  return personas;
}
