import type { Conteo } from '../dominio/metricas';

/** Una pregunta de la encuesta: se responde con un entero de 1 a 7, con su propia escala. */
export interface PreguntaEncuesta {
  /** Cómo se nombra donde hay poco lugar. */
  nombre: string;
  texto: string;
  /** Lo que significan el 1 y el 7 en esta pregunta. */
  minimo: string;
  maximo: string;
  /** Si mide postura frente a la política (a favor o en contra) y se pinta con sus colores. */
  postura: boolean;
}

/**
 * La encuesta que responde cada agente. Es fija: las mismas cinco preguntas en cada corrida, cada
 * una con su escala. La primera decide la postura de la persona, y con ella el color de su punto
 * en el mapa. Influencia no mide apoyo: dice cuánto le toca la política, y va en tono neutro.
 *
 * Son las del motor (backend/scripts/probar_modelo.py, `ENCUESTA`); si cambian allá, cambian aquí.
 */
export const ENCUESTA: readonly PreguntaEncuesta[] = [
  { nombre: 'Apoyo', texto: '¿Estarías de acuerdo con que se implemente esta política en tu región?', minimo: 'totalmente en desacuerdo', maximo: 'totalmente de acuerdo', postura: true },
  { nombre: 'Justicia', texto: '¿Te parece justa la forma en que esta política reparte costos y beneficios?', minimo: 'muy injusto', maximo: 'muy justo', postura: true },
  { nombre: 'Confianza', texto: '¿Confías en que el Estado chileno sea capaz de implementar bien esta política?', minimo: 'muy desconfiado', maximo: 'muy confiado', postura: true },
  { nombre: 'Efectividad', texto: '¿Qué tan efectiva crees que es esta política en lograr lo que propone?', minimo: 'muy inefectivo', maximo: 'muy efectivo', postura: true },
  { nombre: 'Influencia', texto: '¿Qué tan influyente es esta política en tu situación personal o la de tu hogar?', minimo: 'nada influyente', maximo: 'muy influyente', postura: false },
];

/** Los textos de la encuesta, en el orden de las notas. */
export const PREGUNTAS: readonly string[] = ENCUESTA.map((p) => p.texto);

/** La pregunta de la encuesta con este texto, si es una de ellas. */
export const preguntaDe = (texto: string): PreguntaEncuesta | undefined => ENCUESTA.find((p) => p.texto === texto);

/** Cómo se nombra una pregunta donde hay poco lugar: su nombre (Apoyo, Justicia...). */
export function corta(pregunta: string): string {
  return preguntaDe(pregunta)?.nombre ?? pregunta;
}

/** Si la nota de esta pregunta se lee como postura (a favor o en contra). */
export const midePostura = (pregunta: string) => preguntaDe(pregunta)?.postura ?? true;

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

/** Antes la encuesta se podía escribir y quedaba guardada en el navegador: ya no se usa. */
export function olvidarEncuestaGuardada(): void {
  try {
    localStorage.removeItem('delphos.encuesta');
  } catch {
    // Sin almacenamiento (ventana privada): no hay nada que borrar.
  }
}
