import { crearAzar, hashTexto } from '../dominio/azar';
import { REGIONES } from '../dominio/catalogos';
import { dentro } from '../dominio/poblacion';
import type { Persona } from '../dominio/tipos';
import type { AgenteRemoto } from './api';

type Anillo = number[][];

const INTENTOS = 24;
/** Dispersión en grados alrededor del centro de la comuna: la ciudad se junta, el campo se abre. */
const DISPERSION_URBANA = 0.045;
const DISPERSION_RURAL = 0.16;
/** Quien no se ubica en la escala, o es menor de 18, va como "Sin identificación" (índice en POLITICA). */
const SIN_POLITICA = 5;

/**
 * Dónde se dibuja cada punto de cada agente: lon, lat y aspecto, uno tras otro. Se guarda por
 * identificador para que la misma persona quede siempre en el mismo lugar, aunque cambie la
 * muestra: al cambiar un filtro, quienes siguen no se mueven y no hay que recalcularlos.
 */
const LUGARES = new Map<string, number[]>();

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

/** Los primeros `cuantos` puntos de un agente; cada uno sale de su propio sorteo, fijo. */
function lugaresDe(agente: AgenteRemoto, cuantos: number, poligonos: Anillo[]): number[] {
  let lista = LUGARES.get(agente.id);
  if (!lista) {
    lista = [];
    LUGARES.set(agente.id, lista);
  }
  const semilla = hashTexto(agente.id);
  for (let k = lista.length / 3; k < cuantos; k++) {
    const azar = crearAzar(semilla + Math.imul(k + 1, 0x9e3779b1));
    const [lon, lat] = ubicar(agente, poligonos, azar);
    lista.push(lon, lat, Math.floor(azar() * 6));
  }
  return lista;
}

/**
 * Puntos del mapa a partir de los agentes reales: cada agente se dibuja con `porAgente` puntos
 * alrededor de su comuna, para que la densidad del país se lea. Todos los puntos de un agente
 * responden lo mismo, porque son la misma persona.
 */
export function poblacionDeAgentes(agentes: AgenteRemoto[], porAgente: number, regiones: Anillo[][]): Persona[] {
  const personas: Persona[] = [];
  for (const agente of agentes) {
    const lugares = lugaresDe(agente, porAgente, regiones[agente.region]);
    for (let k = 0; k < porAgente; k++) {
      personas.push({
        id: personas.length,
        agente: agente.i,
        clave: `${agente.id}#${k}`,
        region: agente.region,
        lon: lugares[k * 3],
        lat: lugares[k * 3 + 1],
        edad: agente.edad,
        genero: agente.genero,
        quintil: agente.quintil,
        educacion: agente.educacion,
        politica: agente.politica ?? SIN_POLITICA,
        aspecto: lugares[k * 3 + 2],
      });
    }
  }
  return personas;
}
