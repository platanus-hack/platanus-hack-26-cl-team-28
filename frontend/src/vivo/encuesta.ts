import type { Conteo } from '../dominio/metricas';

/**
 * La encuesta que responde cada agente: una nota de 1 a 7 por pregunta (1 es totalmente en
 * desacuerdo y 7 totalmente de acuerdo). La primera pregunta decide la postura de la persona,
 * y con ella el color de su punto en el mapa.
 *
 * Estas son las preguntas de partida del motor (backend/scripts/probar_modelo.py). Se usan sin
 * motor conectado; con motor, las de partida llegan en `/api/estado`.
 */
export const PREGUNTAS_BASE = [
  '¿Estarías de acuerdo con que se implemente esta política en tu región?',
  'Si esta política se implementara tal como está descrita, ¿estarías satisfecho con ella?',
  '¿Te parece justa la forma en que esta política reparte costos y beneficios?',
  '¿Confías en que el Estado chileno sea capaz de implementar bien esta política?',
  'Si esta política fuera obligatoria, ¿la cumplirías?',
  '¿Crees que esta política va a lograr lo que se propone?',
];

export const MAXIMO_PREGUNTAS = 10;
export const LARGO_PREGUNTA = 300;

/** Las preguntas de partida dichas en corto, para la ficha de una persona. */
const CORTAS = ['Está de acuerdo', 'Quedaría satisfecha', 'Le parece justa', 'Confía en el Estado', 'La cumpliría', 'Cree que funcionará'];

/** Cómo se nombra una pregunta donde hay poco lugar: su forma corta si es de las de partida. */
export function corta(pregunta: string): string {
  const k = PREGUNTAS_BASE.indexOf(pregunta);
  return k >= 0 ? CORTAS[k] : pregunta;
}

/** Las preguntas tal como se le mandan al motor: sin espacios de más, sin vacías ni repetidas. */
export function limpiarPreguntas(lista: readonly string[]): string[] {
  const limpias = lista.map((p) => p.replace(/\s+/g, ' ').trim()).filter(Boolean);
  return [...new Set(limpias)];
}

export const mismasPreguntas = (a: readonly string[], b: readonly string[]) => a.length === b.length && a.every((p, k) => p === b[k]);

export interface ResultadoPregunta {
  /** De acuerdo (5 a 7), en desacuerdo (1 a 3) y al medio (4). */
  conteo: Conteo;
  /** Promedio de las notas, de 1 a 7; cero si nadie respondió. */
  media: number;
}

/** El resultado de cada pregunta entre los agentes dados (los que se están mirando). */
export function resumirEncuesta(notas: readonly (readonly number[] | undefined)[], agentes: readonly number[], cuantas: number): ResultadoPregunta[] {
  const filas = Array.from({ length: cuantas }, () => ({ conteo: { favor: 0, contra: 0, indecisa: 0, total: 0 }, suma: 0 }));
  for (const i of agentes) {
    const suyas = notas[i];
    if (!suyas) continue;
    for (let k = 0; k < cuantas; k++) {
      const nota = suyas[k];
      if (!nota) continue;
      const fila = filas[k];
      fila.conteo[nota >= 5 ? 'favor' : nota <= 3 ? 'contra' : 'indecisa'] += 1;
      fila.conteo.total += 1;
      fila.suma += nota;
    }
  }
  return filas.map(({ conteo, suma }) => ({ conteo, media: conteo.total ? suma / conteo.total : 0 }));
}

const CLAVE = 'delphos.encuesta';

/** La encuesta que la persona dejó escrita en este navegador, si la cambió. */
export function leerEncuestaGuardada(): string[] | null {
  try {
    const lista: unknown = JSON.parse(localStorage.getItem(CLAVE) ?? 'null');
    if (!Array.isArray(lista) || !lista.every((p) => typeof p === 'string')) return null;
    const limpias = limpiarPreguntas(lista).slice(0, MAXIMO_PREGUNTAS);
    return limpias.length ? limpias : null;
  } catch {
    return null;
  }
}

/** Guarda la encuesta escrita; con `null` (volvió a la de partida) la olvida. */
export function guardarEncuesta(preguntas: readonly string[] | null): void {
  try {
    if (preguntas) localStorage.setItem(CLAVE, JSON.stringify(preguntas));
    else localStorage.removeItem(CLAVE);
  } catch {
    // Sin almacenamiento (ventana privada): la encuesta vive solo mientras la página esté abierta.
  }
}
