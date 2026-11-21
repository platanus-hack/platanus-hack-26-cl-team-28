export type Postura = 'favor' | 'contra' | 'indecisa';

export const POSTURAS: readonly Postura[] = ['favor', 'indecisa', 'contra'];

/** Perfil sintético que se dibuja en el mapa. Cada figura representa a varias personas de la muestra. */
export interface Persona {
  id: number;
  region: number;
  lon: number;
  lat: number;
  edad: number;
  genero: number;
  quintil: number;
  educacion: number;
  politica: number;
  /** Aspecto del dibujo (peinado y contextura), de 0 a 5. */
  aspecto: number;
}

export interface Caso {
  id: string;
  letra: string;
  texto: string;
}

export interface Filtros {
  tamano: number;
  region: number;
  edadMin: number;
  edadMax: number;
  genero: number;
  quintil: number;
  educacion: number;
  politica: number;
}

export interface Respuesta {
  postura: Postura;
  /** Qué tan firme es la postura, de 0 a 1. */
  firmeza: number;
  /** Índice en ACCIONES. */
  accion: number;
  /** Índice en RAZONES. */
  razon: number;
}

export interface ResultadoCaso {
  casoId: string;
  /** Una respuesta por persona, en el mismo orden que la lista de personas consultadas. */
  respuestas: Respuesta[];
}

export interface Muestra {
  /** Índices de las personas del mapa que entran en la muestra. */
  indices: number[];
  /** Personas simuladas que se consultan (lo pedido o lo disponible, lo que sea menor). */
  total: number;
  disponibles: number;
  pedidas: number;
}
