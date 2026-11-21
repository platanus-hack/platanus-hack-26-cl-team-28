/** El historial de simulaciones que guarda el motor: qué se preguntó, cuándo y qué resultó. */

export interface CasoHistorial {
  letra: string;
  /** Lo que la persona escribió; vacío si la variante era solo un documento. */
  texto: string;
  titulo: string;
  /** Nombre del documento adjunto, si lo hubo. */
  documento: string | null;
  /** La escribió el agente a partir de otra variante. */
  iteracion: boolean;
  respondidas: number;
  favor: number;
  contra: number;
  indecisa: number;
}

export interface EntradaHistorial {
  id: string;
  /** Cuándo partió, en ISO 8601 con zona. */
  hora: string;
  agentes: number;
  modelo: string;
  segundos: number;
  costo_usd: number;
  /** Falso si se detuvo antes de que respondieran todos. */
  completa: boolean;
  casos: CasoHistorial[];
}

export interface Reparto {
  favor: number;
  contra: number;
  indecisa: number;
}

/** Porcentajes enteros que suman 100: lo que sobra al redondear va a los que más se acercaban al siguiente. */
export function repartoDe(caso: Pick<CasoHistorial, 'favor' | 'contra' | 'indecisa'>): Reparto {
  const claves = ['favor', 'contra', 'indecisa'] as const;
  const total = claves.reduce((suma, clave) => suma + caso[clave], 0);
  if (!total) return { favor: 0, contra: 0, indecisa: 0 };
  const exactos = claves.map((clave) => (caso[clave] / total) * 100);
  const enteros = exactos.map(Math.floor);
  const orden = claves.map((_, k) => k).sort((a, b) => exactos[b] - enteros[b] - (exactos[a] - enteros[a]));
  for (let k = 0, faltan = 100 - enteros.reduce((s, v) => s + v, 0); k < faltan; k++) enteros[orden[k]] += 1;
  return { favor: enteros[0], contra: enteros[1], indecisa: enteros[2] };
}

const HORA = new Intl.DateTimeFormat('es-CL', { hour: '2-digit', minute: '2-digit', hour12: false });
const DIA = new Intl.DateTimeFormat('es-CL', { day: 'numeric', month: 'short' });
const DIA_Y_ANO = new Intl.DateTimeFormat('es-CL', { day: 'numeric', month: 'short', year: 'numeric' });
const medianoche = (fecha: Date) => new Date(fecha.getFullYear(), fecha.getMonth(), fecha.getDate()).getTime();

/** «Hoy, 17:43», «Ayer, 09:12» o «19 nov, 14:03», en la hora de quien mira. */
export function cuando(hora: string, ahora: Date = new Date()): string {
  const fecha = new Date(hora);
  if (Number.isNaN(fecha.getTime())) return '';
  const dias = Math.round((medianoche(ahora) - medianoche(fecha)) / 86_400_000);
  const dia = dias === 0 ? 'Hoy' : dias === 1 ? 'Ayer' : (fecha.getFullYear() === ahora.getFullYear() ? DIA : DIA_Y_ANO).format(fecha);
  return `${dia}, ${HORA.format(fecha)}`;
}

/** Lo que se muestra como la pregunta de una variante. */
export const preguntaDe = (caso: CasoHistorial): string => caso.texto || caso.titulo || caso.documento || '';

/** Los textos con que se puede volver a preguntar: los que escribió la persona, no los del agente ni los documentos. */
export const textosDe = (entrada: EntradaHistorial): string[] => entrada.casos.filter((caso) => !caso.iteracion && caso.texto).map((caso) => caso.texto);
