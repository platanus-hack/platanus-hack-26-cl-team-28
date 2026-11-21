import { ACCIONES, PRIMERA_ACCION_MOVILIZADA, RAZONES, REGIONES } from './catalogos';
import type { Persona, Postura, Respuesta } from './tipos';

export interface Conteo {
  favor: number;
  contra: number;
  indecisa: number;
  total: number;
}

export interface Porcentajes {
  favor: number;
  contra: number;
  indecisa: number;
}

export interface ResumenCaso {
  conteo: Conteo;
  porcentajes: Porcentajes;
  /** Puntos porcentuales: a favor menos en contra. */
  apoyoNeto: number;
  /** Puntos porcentuales entre la región con más y con menos apoyo (con al menos MINIMO_REGION figuras). */
  brechaTerritorial: number | null;
  /** Porcentaje que firmaría, cambiaría su voto o se manifestaría. */
  movilizacion: number;
  porRegion: Conteo[];
  /** Por cada acción, cuántas personas de cada postura la elegirían. */
  acciones: Conteo[];
  razones: number[];
}

export const MINIMO_REGION = 5;

const conteoVacio = (): Conteo => ({ favor: 0, contra: 0, indecisa: 0, total: 0 });

function sumar(conteo: Conteo, postura: Postura): void {
  conteo[postura] += 1;
  conteo.total += 1;
}

/** Porcentajes enteros que suman exactamente 100 (método del resto mayor). */
export function porcentajes(conteo: Conteo): Porcentajes {
  if (conteo.total === 0) return { favor: 0, contra: 0, indecisa: 0 };
  const claves: Postura[] = ['favor', 'contra', 'indecisa'];
  const exactos = claves.map((clave) => (conteo[clave] / conteo.total) * 100);
  const enteros = exactos.map(Math.floor);
  let faltan = 100 - enteros.reduce((a, b) => a + b, 0);
  const orden = exactos.map((valor, i) => [valor - enteros[i], i]).sort((a, b) => b[0] - a[0]);
  for (let k = 0; faltan > 0; k++, faltan--) enteros[orden[k % 3][1]] += 1;
  return { favor: enteros[0], contra: enteros[1], indecisa: enteros[2] };
}

function brecha(porRegion: Conteo[]): number | null {
  const apoyos = porRegion.filter((c) => c.total >= MINIMO_REGION).map((c) => (c.favor / c.total) * 100);
  return apoyos.length >= 2 ? Math.round(Math.max(...apoyos) - Math.min(...apoyos)) : null;
}

export function resumirCaso(personas: Persona[], respuestas: Respuesta[]): ResumenCaso {
  if (personas.length !== respuestas.length) throw new Error('Cada persona debe tener exactamente una respuesta');
  const conteo = conteoVacio();
  const porRegion = REGIONES.map(conteoVacio);
  const acciones = ACCIONES.map(conteoVacio);
  const razones = RAZONES.map(() => 0);
  let movilizadas = 0;
  respuestas.forEach((respuesta, i) => {
    sumar(conteo, respuesta.postura);
    sumar(porRegion[personas[i].region], respuesta.postura);
    sumar(acciones[respuesta.accion], respuesta.postura);
    razones[respuesta.razon] += 1;
    if (respuesta.accion >= PRIMERA_ACCION_MOVILIZADA) movilizadas += 1;
  });
  verificar(conteo, porRegion, acciones);
  const pct = porcentajes(conteo);
  return {
    conteo,
    porcentajes: pct,
    apoyoNeto: pct.favor - pct.contra,
    brechaTerritorial: brecha(porRegion),
    movilizacion: conteo.total ? Math.round((movilizadas / conteo.total) * 100) : 0,
    porRegion,
    acciones,
    razones,
  };
}

function verificar(conteo: Conteo, porRegion: Conteo[], acciones: Conteo[]): void {
  const cierra = (c: Conteo) => c.favor + c.contra + c.indecisa === c.total;
  const totalDe = (lista: Conteo[]) => lista.reduce((suma, c) => suma + c.total, 0);
  if (!cierra(conteo) || !porRegion.every(cierra) || !acciones.every(cierra)) {
    throw new Error('Las posturas no suman el total');
  }
  if (totalDe(porRegion) !== conteo.total || totalDe(acciones) !== conteo.total) {
    throw new Error('Los desgloses no suman el total del caso');
  }
}
