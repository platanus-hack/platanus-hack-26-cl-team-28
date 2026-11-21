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
  /** Agente real del motor que este punto dibuja (varios puntos pueden ser el mismo agente). */
  agente?: number;
  /** Identidad del punto entre una muestra y otra: si sigue en la muestra nueva, el mapa no lo mueve. */
  clave?: string;
}

export interface Documento {
  nombre: string;
  /** Tamaño en bytes. */
  tamano: number;
  /** El archivo tal como se subió, para enviarlo al motor (una ley completa, por ejemplo). */
  archivo: File;
}

export interface Caso {
  id: string;
  letra: string;
  /** Texto escrito de la propuesta; puede ir vacío si se subió un documento. */
  texto: string;
  documento?: Documento;
  /** Si la variante la propuso el agente: sobre qué variante iteró y qué número de iteración es. */
  iteracion?: { de: string; numero: number };
}

/** Una respuesta que llega mientras la simulación corre: los agentes terminan de a uno, en cualquier orden. */
export interface Avance {
  caso: number;
  persona: number;
  respuesta: Respuesta;
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
  /** Clusterización: a cuántas personas representa cada agente (10, 100, 1.000 o 10.000). */
  reduccion: number;
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
