/** Cliente del motor de simulación (backend/servidor). En desarrollo Vite lo atiende en /api. */

export interface MotorInfo {
  nombre: string;
  modelo: string;
  grabado: boolean;
}

export interface EstadoMotor {
  motor: MotorInfo;
  agentes: number;
  lote: number;
  concurrencia: number;
  /** Las preguntas de la encuesta, en el orden de las notas. */
  preguntas?: string[];
}

export interface AgenteRemoto {
  i: number;
  id: string;
  region: number;
  comuna: string;
  lon: number;
  lat: number;
  edad: number;
  genero: number;
  quintil: number;
  educacion: number;
  /** Índice en POLITICA: 0 izquierda … 4 derecha, 5 sin identificación. Imputado desde la CEP. */
  politica?: number;
  atributos: Record<string, string>;
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
  | { tipo: 'inicio'; motor: MotorInfo; agentes: number; casos: CasoPublico[] }
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

export async function pedirEstado(): Promise<EstadoMotor> {
  const control = new AbortController();
  const plazo = window.setTimeout(() => control.abort(), ESPERA_ESTADO);
  try {
    return await leer<EstadoMotor>(await fetch(`${BASE}/estado`, { signal: control.signal }));
  } finally {
    window.clearTimeout(plazo);
  }
}

export async function pedirAgentes(): Promise<AgenteRemoto[]> {
  return leer<AgenteRemoto[]>(await fetch(`${BASE}/agentes`));
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
  pedido: { casos: CasoPedido[]; agentes: number[]; iteraciones: number },
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
