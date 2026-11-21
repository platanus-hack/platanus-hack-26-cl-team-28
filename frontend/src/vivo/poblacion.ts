import { crearAzar, hashTexto } from '../dominio/azar';
import { REGIONES } from '../dominio/catalogos';
import { dentro } from '../dominio/poblacion';
import type { Persona } from '../dominio/tipos';
import { dentroDe, type ComunaGeo, type ComunasGeo, type ZonaUrbana } from '../mapa/geografia';
import type { AgenteRemoto } from './api';

type Anillo = number[][];

const INTENTOS = 24;
/** Intentos para caer dentro de la comuna: con fiordos e islas, muchos sorteos caen al mar. */
const INTENTOS_COMUNA = 64;
/** Sin comuna conocida: dispersión en grados alrededor de su centro; la ciudad se junta, el campo se abre. */
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

interface Caja {
  oeste: number;
  sur: number;
  ancho: number;
  alto: number;
}

/** De cada polígono, la caja de cada anillo y su área acumulada: para sortear un anillo según su tamaño. */
const CAJAS = new WeakMap<Anillo[], { cajas: Caja[]; acumulada: number[] }>();

function cajasDe(anillos: Anillo[]): { cajas: Caja[]; acumulada: number[] } {
  let hecho = CAJAS.get(anillos);
  if (!hecho) {
    const cajas = anillos.map((anillo) => {
      let [oeste, sur, este, norte] = [Infinity, Infinity, -Infinity, -Infinity];
      for (const [lon, lat] of anillo) {
        oeste = Math.min(oeste, lon);
        este = Math.max(este, lon);
        sur = Math.min(sur, lat);
        norte = Math.max(norte, lat);
      }
      return { oeste, sur, ancho: este - oeste, alto: norte - sur };
    });
    let suma = 0;
    const acumulada = cajas.map((c) => (suma += c.ancho * c.alto));
    hecho = { cajas, acumulada };
    CAJAS.set(anillos, hecho);
  }
  return hecho;
}

/**
 * Un lugar al azar, uniforme, dentro de un polígono de varios anillos. Se sortea un anillo según
 * el área de su caja, un punto en esa caja, y se acepta si cae dentro de ese anillo y del polígono
 * (no en un hueco) y si `vale` lo deja: así cada lugar tiene la misma probabilidad. Si no se
 * acierta en `intentos`, null.
 */
function lugarEn(anillos: Anillo[], azar: () => number, intentos: number, vale?: (lon: number, lat: number) => boolean): [number, number] | null {
  const { cajas, acumulada } = cajasDe(anillos);
  const total = acumulada[acumulada.length - 1] ?? 0;
  if (total <= 0) return null;
  for (let intento = 0; intento < intentos; intento++) {
    const elegido = azar() * total;
    let k = 0;
    while (k < acumulada.length - 1 && acumulada[k] < elegido) k++;
    const caja = cajas[k];
    const lon = caja.oeste + azar() * caja.ancho;
    const lat = caja.sur + azar() * caja.alto;
    if (dentro(lon, lat, anillos[k]) && dentroDe(lon, lat, anillos) && (!vale || vale(lon, lat))) return [lon, lat];
  }
  return null;
}

/** Una de las zonas urbanas, sorteada según cuántas personas viven en cada una. */
function zonaSegunPoblacion(zonas: ZonaUrbana[], azar: () => number): ZonaUrbana {
  const total = zonas.reduce((suma, z) => suma + z.personas, 0);
  let resto = azar() * total;
  for (const zona of zonas) {
    resto -= zona.personas;
    if (resto < 0) return zona;
  }
  return zonas[zonas.length - 1];
}

/**
 * Dónde vive alguien dentro de su comuna. Quien vive en zona urbana cae, uniforme, dentro de una
 * de sus ciudades o pueblos (límite urbano del INE), elegida según su población: así Lo Barnechea
 * se junta en su ciudad y no se reparte por la cordillera. Quien vive en zona rural cae en el
 * resto de la comuna. Sin zonas urbanas, o si el sorteo no acierta, en cualquier parte de la
 * comuna; y si tampoco, en su punto interior.
 */
export function lugarEnComuna(comuna: ComunaGeo, azar: () => number, zona: 'urbana' | 'rural' = 'urbana'): [number, number] {
  const urbanas = (comuna.urbano ?? []).filter((z) => z.personas > 0 && z.anillos.length);
  let lugar: [number, number] | null = null;
  if (zona === 'urbana' && urbanas.length) {
    // La ciudad se simplificó más fina que la comuna: su borde puede asomarse fuera del contorno dibujado.
    lugar = lugarEn(zonaSegunPoblacion(urbanas, azar).anillos, azar, INTENTOS_COMUNA, (lon, lat) => dentroDe(lon, lat, comuna.anillos));
  } else if (zona === 'rural' && urbanas.length) {
    lugar = lugarEn(comuna.anillos, azar, INTENTOS_COMUNA, (lon, lat) => !urbanas.some((z) => dentroDe(lon, lat, z.anillos)));
  }
  lugar ??= lugarEn(comuna.anillos, azar, INTENTOS_COMUNA);
  return lugar ?? [comuna.interior[0], comuna.interior[1]];
}

function ubicar(agente: AgenteRemoto, poligonos: Anillo[], comunas: ComunasGeo, azar: () => number): [number, number] {
  const comuna = agente.cod_comuna ? comunas[agente.cod_comuna] : undefined;
  if (comuna) return lugarEnComuna(comuna, azar, agente.atributos.Zona === 'Rural' ? 'rural' : 'urbana');
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
function lugaresDe(agente: AgenteRemoto, cuantos: number, poligonos: Anillo[], comunas: ComunasGeo): number[] {
  let lista = LUGARES.get(agente.id);
  if (!lista) {
    lista = [];
    LUGARES.set(agente.id, lista);
  }
  const semilla = hashTexto(agente.id);
  for (let k = lista.length / 3; k < cuantos; k++) {
    const azar = crearAzar(semilla + Math.imul(k + 1, 0x9e3779b1));
    const [lon, lat] = ubicar(agente, poligonos, comunas, azar);
    lista.push(lon, lat, Math.floor(azar() * 6));
  }
  return lista;
}

/**
 * Puntos del mapa a partir de los agentes reales: cada agente se dibuja con `porAgente` puntos
 * repartidos al azar dentro de su comuna, para que la densidad del país se lea. Sin la comuna
 * (la demostración, o si no cargaron los polígonos) van alrededor de su centro, dentro de su
 * región. Todos los puntos de un agente responden lo mismo, porque son la misma persona.
 *
 * Los lugares se guardan por agente la primera vez: las comunas tienen que estar cargadas antes
 * (`cargarComunas`), o esa persona queda ubicada por región.
 */
export function poblacionDeAgentes(agentes: AgenteRemoto[], porAgente: number, regiones: Anillo[][], comunas: ComunasGeo = {}): Persona[] {
  const personas: Persona[] = [];
  for (const agente of agentes) {
    const lugares = lugaresDe(agente, porAgente, regiones[agente.region], comunas);
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
