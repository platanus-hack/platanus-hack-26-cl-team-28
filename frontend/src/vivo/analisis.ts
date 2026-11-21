/**
 * El análisis de una corrida por características de las personas: cómo respondió cada grupo
 * (región, género, edad, trabajo, posición política...) a una pregunta de la encuesta, qué
 * característica separa más las respuestas y cómo se cruzan dos de ellas.
 *
 * Todo se cuenta en agentes, sin ponderar, igual que las cifras del resto de la pantalla.
 */
import type { Conteo } from '../dominio/metricas';
import { PARAMETROS, type Clave } from './sociedad';

/** Lo que se necesita de una persona para ubicarla en cada característica. */
export interface PersonaAnalisis {
  edad: number;
  /** Su opción en cada parámetro, en el orden de `PARAMETROS` (-1 si no tiene el dato). */
  s?: number[];
}

export type ClaveDimension = Clave | 'edad';

export interface Dimension {
  clave: ClaveDimension;
  rotulo: string;
  /** El rótulo para donde hay poco lugar. */
  breve: string;
  grupos: readonly string[];
  /** Nombres de los grupos que caben en la cabeza de una columna. */
  cortos: readonly string[];
  /** Si los grupos tienen un orden propio (edad, ingreso, educación, izquierda a derecha). */
  ordenada: boolean;
  /** El grupo de una persona en esta característica, o -1 si no tiene el dato. */
  grupoDe(persona: PersonaAnalisis): number;
}

/** Con menos respuestas que estas, un grupo se muestra pero no entra en las comparaciones. */
export const MINIMO_GRUPO = 20;
/** En un cruce cada casilla tiene menos gente: se pide menos para mostrar su cifra. */
export const MINIMO_CASILLA = 12;
/**
 * Cuántas desviaciones sobre lo esperable por azar debe quedar una característica para decir que
 * ordena las respuestas. Se miran unas catorce a la vez, así que el corte es exigente.
 */
const DESVIACIONES = 2.5;

const TRAMOS: readonly { desde: number; rotulo: string; corto: string }[] = [
  { desde: 0, rotulo: '14 a 17 años', corto: '14 a 17' },
  { desde: 18, rotulo: '18 a 29 años', corto: '18 a 29' },
  { desde: 30, rotulo: '30 a 44 años', corto: '30 a 44' },
  { desde: 45, rotulo: '45 a 59 años', corto: '45 a 59' },
  { desde: 60, rotulo: '60 a 74 años', corto: '60 a 74' },
  { desde: 75, rotulo: '75 años o más', corto: '75 o más' },
];

export function tramoDe(edad: number): number {
  let tramo = 0;
  for (let k = 1; k < TRAMOS.length; k++) if (edad >= TRAMOS[k].desde) tramo = k;
  return tramo;
}

const ORDENADAS: readonly ClaveDimension[] = ['edad', 'educacion', 'quintil', 'politica'];

const BREVES: Partial<Record<Clave, string>> = { voto: 'Voto en 2025', quintil: 'Ingreso del hogar' };

/** Nombres de columna para los parámetros cuyos rótulos no caben. */
const COLUMNAS: Partial<Record<Clave, readonly string[]>> = {
  nacionalidad: ['Chilena', 'Extranjera'],
  trabajo: ['Trabaja', 'Busca', 'No busca'],
  menores: ['Con niños', 'Sin niños'],
  vivienda: ['Propia', 'Arrienda', 'Cedida'],
  salud: ['Fonasa A B', 'Fonasa C D', 'Isapre', 'Otra'],
  gobierno: ['Aprueba', 'Desaprueba', 'Ninguna'],
  voto: ['Jara', 'Kast', 'Blanco', 'No votó'],
  confianza: ['Mucha', 'Poca'],
};

const EDAD: Dimension = {
  clave: 'edad',
  rotulo: 'Edad',
  breve: 'Edad',
  grupos: TRAMOS.map((t) => t.rotulo),
  cortos: TRAMOS.map((t) => t.corto),
  ordenada: true,
  grupoDe: (persona) => tramoDe(persona.edad),
};

/** Todas las características, en el orden del cajón de la muestra: territorio, personas, hogar y opinión. */
export const DIMENSIONES: readonly Dimension[] = PARAMETROS.flatMap((parametro, k): Dimension[] => {
  const propia: Dimension = {
    clave: parametro.clave,
    rotulo: parametro.rotulo,
    breve: BREVES[parametro.clave] ?? parametro.rotulo,
    grupos: parametro.opciones,
    cortos: COLUMNAS[parametro.clave] ?? parametro.cortos ?? parametro.opciones,
    ordenada: ORDENADAS.includes(parametro.clave),
    grupoDe: (persona) => persona.s?.[k] ?? -1,
  };
  // La edad va donde está en el cajón: después del territorio.
  return parametro.clave === 'region' ? [propia, EDAD] : [propia];
});

export interface ResumenGrupo extends Conteo {
  /** Suma de las notas y de sus cuadrados: de ahí salen la media y cuánto separa la característica. */
  suma: number;
  cuadrados: number;
}

const grupoVacio = (): ResumenGrupo => ({ favor: 0, contra: 0, indecisa: 0, total: 0, suma: 0, cuadrados: 0 });

function anotar(grupo: ResumenGrupo, nota: number): void {
  grupo[nota >= 5 ? 'favor' : nota <= 3 ? 'contra' : 'indecisa'] += 1;
  grupo.total += 1;
  grupo.suma += nota;
  grupo.cuadrados += nota * nota;
}

export type Notas = readonly (readonly number[] | undefined)[];

/** La nota de un agente a la pregunta `k`, o cero si no la respondió. */
const notaDe = (notas: Notas, agente: number, k: number): number => notas[agente]?.[k] ?? 0;

/** Qué parte del grupo quedó en el lado alto de la escala (5 a 7), en porcentaje entero. */
export const alto = (grupo: Conteo): number => (grupo.total ? Math.round((grupo.favor / grupo.total) * 100) : 0);

export const mediaDe = (grupo: ResumenGrupo): number => (grupo.total ? grupo.suma / grupo.total : 0);

export interface ResumenDimension {
  dimension: Dimension;
  /** Un resumen por grupo, en el orden de `dimension.grupos`. */
  grupos: ResumenGrupo[];
  /** Todos los que respondieron y tienen el dato de esta característica. */
  total: ResumenGrupo;
  /**
   * Qué tan ligada está la característica a las notas, de 0 a 1: la razón de correlación (eta),
   * ajustada por la cantidad de grupos. Se lee como una correlación.
   */
  fuerza: number;
  /** Si la relación supera lo que daría el azar con esta cantidad de respuestas y de grupos. */
  clara: boolean;
  /** Los grupos con respuestas suficientes que quedaron más alto y más bajo, si hay al menos dos. */
  extremos: { mayor: number; menor: number; brecha: number } | null;
}

/**
 * Cómo respondió cada grupo de una característica a la pregunta `k`.
 *
 * La fuerza sale del eta cuadrado ajustado por la cantidad de grupos: una característica con muchos
 * grupos (las 16 regiones) muestra diferencias por puro azar, y el ajuste se las descuenta. Se
 * calcula solo con los grupos de `MINIMO_GRUPO` respuestas o más, los mismos que se comparan.
 *
 * Sin relación alguna, el eta cuadrado ajustado ronda el cero con una desviación cercana a
 * raíz de 2(k - 1) sobre N - k (k grupos, N respuestas): la relación es clara si queda varias
 * desviaciones por encima. Así el corte se adapta a muestras chicas y a características con muchos grupos.
 */
export function resumirDimension(dimension: Dimension, personas: readonly PersonaAnalisis[], notas: Notas, agentes: readonly number[], k: number): ResumenDimension {
  const grupos = dimension.grupos.map(grupoVacio);
  const total = grupoVacio();
  for (const i of agentes) {
    const nota = notaDe(notas, i, k);
    const grupo = personas[i] ? dimension.grupoDe(personas[i]) : -1;
    if (!nota || grupo < 0 || grupo >= grupos.length) continue;
    anotar(grupos[grupo], nota);
    anotar(total, nota);
  }
  const comparables = grupos.filter((g) => g.total >= MINIMO_GRUPO);
  let fuerza = 0;
  let clara = false;
  if (comparables.length > 1) {
    const n = comparables.reduce((suma, g) => suma + g.total, 0);
    const k = comparables.length;
    const media = comparables.reduce((suma, g) => suma + g.suma, 0) / n;
    const variacion = comparables.reduce((suma, g) => suma + g.cuadrados, 0) - n * media * media;
    const entre = comparables.reduce((suma, g) => suma + g.total * (g.suma / g.total - media) ** 2, 0);
    if (variacion > 0) {
      const ajustado = Math.max(0, 1 - ((1 - entre / variacion) * (n - 1)) / (n - k));
      fuerza = Math.sqrt(ajustado);
      clara = ajustado > (DESVIACIONES * Math.sqrt(2 * (k - 1))) / (n - k);
    }
  }
  let mayor = -1;
  let menor = -1;
  grupos.forEach((g, j) => {
    if (g.total < MINIMO_GRUPO) return;
    if (mayor < 0 || g.favor / g.total > grupos[mayor].favor / grupos[mayor].total) mayor = j;
    // Con empate el menor es el último: si todos los grupos coinciden, igual hay dos que comparar.
    if (menor < 0 || g.favor / g.total <= grupos[menor].favor / grupos[menor].total) menor = j;
  });
  const extremos = mayor >= 0 && mayor !== menor ? { mayor, menor, brecha: alto(grupos[mayor]) - alto(grupos[menor]) } : null;
  return { dimension, grupos, total, fuerza, clara, extremos };
}

/**
 * Las características que se pueden analizar en esta corrida: primero las que ordenan las
 * respuestas más allá del azar, de la más fuerte a la más débil, y después el resto. Solo entran las que tienen dato y al menos dos grupos con gente.
 */
export function ordenarDimensiones(personas: readonly PersonaAnalisis[], notas: Notas, agentes: readonly number[], k: number): ResumenDimension[] {
  return DIMENSIONES.map((dimension) => resumirDimension(dimension, personas, notas, agentes, k))
    .filter((resumen) => resumen.grupos.filter((g) => g.total > 0).length > 1)
    .sort((a, b) => Number(b.clara) - Number(a.clara) || b.fuerza - a.fuerza || (b.extremos?.brecha ?? 0) - (a.extremos?.brecha ?? 0));
}

/** Dos características a la vez: una casilla por cada par de grupos, filas de la primera y columnas de la segunda. */
export function cruzar(filas: Dimension, columnas: Dimension, personas: readonly PersonaAnalisis[], notas: Notas, agentes: readonly number[], k: number): ResumenGrupo[][] {
  const tabla = filas.grupos.map(() => columnas.grupos.map(grupoVacio));
  for (const i of agentes) {
    const nota = notaDe(notas, i, k);
    const persona = personas[i];
    if (!nota || !persona) continue;
    const fila = filas.grupoDe(persona);
    const columna = columnas.grupoDe(persona);
    if (fila < 0 || columna < 0 || fila >= filas.grupos.length || columna >= columnas.grupos.length) continue;
    anotar(tabla[fila][columna], nota);
  }
  return tabla;
}

/**
 * Qué tan juntas se mueven dos preguntas entre las mismas personas: la correlación de sus notas,
 * de -1 a 1. Nulo si no hay con qué calcularla (pocas respuestas o todas iguales).
 */
export function correlacion(notas: Notas, agentes: readonly number[], a: number, b: number): number | null {
  let n = 0;
  let sa = 0;
  let sb = 0;
  let saa = 0;
  let sbb = 0;
  let sab = 0;
  for (const i of agentes) {
    const x = notaDe(notas, i, a);
    const y = notaDe(notas, i, b);
    if (!x || !y) continue;
    n += 1;
    sa += x;
    sb += y;
    saa += x * x;
    sbb += y * y;
    sab += x * y;
  }
  if (n < MINIMO_GRUPO) return null;
  const varianzas = (saa - (sa * sa) / n) * (sbb - (sb * sb) / n);
  return varianzas > 0 ? (sab - (sa * sb) / n) / Math.sqrt(varianzas) : null;
}

/**
 * A quiénes citar de un grupo: personas con frase que respondieron del lado pedido de la escala
 * (5 a 7 o 1 a 3). Primero las de nota más marcada y, entre ellas, las frases de largo cómodo
 * para leer; el resultado es siempre el mismo para los mismos datos.
 */
export function vocesDe(
  dimension: Dimension,
  grupo: number,
  lado: 'alto' | 'bajo',
  personas: readonly PersonaAnalisis[],
  notas: Notas,
  frases: readonly (string | undefined)[],
  agentes: readonly number[],
  k: number,
  cuantas: number,
): number[] {
  const comodo = (frase: string) => Math.abs(frase.length - 110);
  return agentes
    .filter((i) => {
      const nota = notaDe(notas, i, k);
      return !!frases[i]?.trim() && !!personas[i] && dimension.grupoDe(personas[i]) === grupo && (lado === 'alto' ? nota >= 5 : nota >= 1 && nota <= 3);
    })
    .sort((a, b) => {
      const marcada = lado === 'alto' ? notaDe(notas, b, k) - notaDe(notas, a, k) : notaDe(notas, a, k) - notaDe(notas, b, k);
      return marcada || comodo(frases[a]!) - comodo(frases[b]!) || a - b;
    })
    .slice(0, cuantas);
}
