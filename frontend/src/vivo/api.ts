/** Cliente del motor de simulación (backend/servidor). En desarrollo Vite lo atiende en /api. */
import { paraElMotor, rasgosDe, type FiltrosVivo } from './sociedad';
import type { EntradaHistorial } from './historial';

export interface MotorInfo {
  nombre: string;
  modelo: string;
  /** Solo en la demostración del navegador, que sortea las respuestas. */
  grabado?: boolean;
}

/** La población de la que el motor sortea a los agentes. */
export interface PoblacionInfo {
  fuente: string;
  /** Agentes disponibles en total, antes de filtrar. */
  agentes: number;
  /** Personas de 14 años o más que representan. */
  personas: number;
  /** A cuántas personas representa cada agente, en promedio. */
  representa: number;
  /** Niveles de clusterización que ofrece el motor: personas por agente (10, 100, 1.000 y 10.000). */
  niveles?: number[];
  /** Los parámetros por los que el motor deja filtrar, con sus opciones (ver vivo/sociedad.ts). */
  parametros?: { clave: string; opciones: string[] }[];
}

export interface EstadoMotor {
  motor: MotorInfo;
  agentes: number;
  poblacion?: PoblacionInfo;
  lote: number;
  concurrencia: number;
  /** La encuesta, fija, en el orden de las notas. */
  preguntas?: string[];
  /** El nombre corto de cada pregunta y lo que significan el 1 y el 7 en ella. */
  nombres?: string[];
  escalas?: [string, string][];
}

export interface AgenteRemoto {
  i: number;
  id: string;
  region: number;
  comuna: string;
  /** Código INE de la comuna (0 o ausente si no se reconoce): el punto se dibuja dentro de ella. */
  cod_comuna?: number;
  lon: number;
  lat: number;
  edad: number;
  genero: number;
  quintil: number;
  educacion: number;
  /** Índice en POLITICA: 0 izquierda … 4 derecha, 5 sin identificación. Imputado desde la CEP. */
  politica?: number;
  /** A cuántas personas representa en esta muestra. */
  representa?: number;
  /** Su opción en cada parámetro de vivo/sociedad.ts, en ese orden (-1 si no tiene el dato). */
  s?: number[];
  atributos: Record<string, string>;
}

/** Lo que devuelve el motor al filtrar la población y sortear una muestra. */
export interface MuestraRemota {
  id: string;
  /** Agentes que cumplen los filtros, antes de recortar al tamaño pedido. */
  disponibles: number;
  /** Personas a las que representan esos agentes. */
  representadas: number;
  /** El orden en que el motor manda los rasgos de cada agente. */
  dimensiones?: string[];
  /** Personas por opción de cada parámetro, entre quienes cumplen los demás filtros; y por edad. */
  retrato?: Record<string, number[]>;
  agentes: AgenteRemoto[];
}

export interface DocumentoLeido {
  nombre: string;
  titulo: string;
  texto: string;
  /** Caracteres del documento original, si se resumió. */
  largo_original?: number;
}

export interface Metricas {
  llamadas: number;
  costo_usd: number;
  tokens: number;
  segundos: number;
}

export interface CasoPedido {
  id: string;
  letra: string;
  texto: string;
  documento?: DocumentoLeido;
}

export interface CasoPublico {
  id: string;
  letra: string;
  texto: string;
  titulo: string;
  documento: { nombre: string; titulo: string } | null;
  iteracion: { de: string; numero: number; cambio: string } | null;
}

/** Eventos de una corrida, en el orden en que llegan. */
export type Evento =
  | { tipo: 'inicio'; motor: MotorInfo; agentes: number; casos: CasoPublico[]; preguntas?: string[] }
  // Cada fila: agente, acuerdo (la primera pregunta), frase si ya la tiene, y sus notas a todas las preguntas.
  | { tipo: 'respuestas'; caso: number; cache: boolean; r: [number, number, string, number[]?][]; metricas: Metricas }
  // Frases pedidas aparte, después de responder, a unas pocas personas: [agente, frase].
  | { tipo: 'voces'; caso: number; r: [number, string][]; metricas: Metricas }
  | { tipo: 'caso_listo'; caso: number; apoyo: number; metricas: Metricas }
  | { tipo: 'redactando'; numero: number; metricas: Metricas }
  | ({ tipo: 'caso'; caso: number; metricas: Metricas } & CasoPublico)
  | { tipo: 'aviso'; mensaje: string }
  | { tipo: 'fin'; metricas: Metricas }
  | { tipo: 'error'; mensaje: string };

const BASE = (import.meta.env.VITE_API as string | undefined) ?? '/api';
const ESPERA_ESTADO = 2500;

async function leer<T>(respuesta: Response): Promise<T> {
  const datos = await respuesta.json().catch(() => ({}));
  if (!respuesta.ok) throw new Error((datos as { error?: string }).error ?? `El motor respondió ${respuesta.status}`);
  return datos as T;
}

/** Las últimas simulaciones que guardó el motor, de la más nueva a la más antigua. */
export async function pedirHistorial(senal?: AbortSignal): Promise<EntradaHistorial[]> {
  const datos = await leer<{ corridas?: EntradaHistorial[] }>(await fetch(`${BASE}/historial`, { signal: senal }));
  return datos.corridas ?? [];
}

export async function pedirEstado(): Promise<EstadoMotor> {
  const control = new AbortController();
  const plazo = window.setTimeout(() => control.abort(), ESPERA_ESTADO);
  try {
    return await leer<EstadoMotor>(await fetch(`${BASE}/estado`, { signal: control.signal }));
  } finally {
    window.clearTimeout(plazo);
  }
}

/** Pide al motor que filtre la población y sortee hasta `filtros.tamano` agentes. */
export async function pedirMuestra(filtros: FiltrosVivo, senal?: AbortSignal): Promise<MuestraRemota> {
  const respuesta = await fetch(`${BASE}/muestra`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ filtros: paraElMotor(filtros), tamano: filtros.tamano }),
    signal: senal,
  });
  const remota = await leer<MuestraRemota>(respuesta);
  // Los rasgos quedan en el orden de la interfaz, venga como venga el del motor.
  for (const agente of remota.agentes) agente.s = rasgosDe(agente, remota.dimensiones);
  return remota;
}

export async function subirDocumento(archivo: File): Promise<DocumentoLeido> {
  const respuesta = await fetch(`${BASE}/documentos`, {
    method: 'POST',
    headers: { 'X-Nombre': encodeURIComponent(archivo.name), 'Content-Type': 'application/octet-stream' },
    body: archivo,
  });
  return leer<DocumentoLeido>(respuesta);
}

/** Lanza una corrida y entrega sus eventos. Devuelve una función que la cancela. */
export async function correrRemoto(
  pedido: { casos: CasoPedido[]; muestra?: string; agentes: number[]; iteraciones: number },
  alEvento: (evento: Evento) => void,
): Promise<() => void> {
  const { id } = await leer<{ id: string }>(
    await fetch(`${BASE}/corridas`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(pedido) }),
  );
  const fuente = new EventSource(`${BASE}/corridas/${id}/eventos`);
  // El servidor llama "falla" a su error: "error" es el evento propio de EventSource al perder la conexión.
  const tipos = ['inicio', 'respuestas', 'voces', 'caso_listo', 'redactando', 'caso', 'aviso', 'fin', 'falla'] as const;
  for (const tipo of tipos) {
    fuente.addEventListener(tipo, (e) => {
      const datos = JSON.parse((e as MessageEvent).data);
      alEvento({ ...datos, tipo: tipo === 'falla' ? 'error' : tipo } as Evento);
      if (tipo === 'fin' || tipo === 'falla') fuente.close();
    });
  }
  // Si el motor se cae o se reinicia, el navegador cierra el flujo: se avisa en vez de esperar para siempre.
  fuente.onerror = () => {
    if (fuente.readyState === EventSource.CLOSED) alEvento({ tipo: 'error', mensaje: 'Se perdió la conexión con el motor de simulación' });
  };
  return () => {
    fuente.onerror = null;
    fuente.close();
    void fetch(`${BASE}/corridas/${id}/cancelar`, { method: 'POST' });
  };
}
