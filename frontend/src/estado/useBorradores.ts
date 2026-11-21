import { useRef, useState } from 'react';
import { CASOS_INICIALES } from '../contenido';
import type { Documento } from '../dominio/tipos';
import type { DocumentoLeido } from '../vivo/api';
import type { Referencia } from '../vivo/validacion';

export interface Borrador {
  id: number;
  texto: string;
  documento?: Documento;
  /** Texto del documento ya leído (o resumido) por el motor, listo para dárselo a los agentes. */
  leido?: DocumentoLeido;
  /** Mientras el motor lee el documento. */
  leyendo?: boolean;
  /** Error al leer el documento. */
  errorDocumento?: string;
  /** Encuesta real con la que se compara esta variante, si viene de un caso de validación. */
  referencia?: Referencia;
}

/** Las variantes mientras se escriben. El id es estable para que React no pierda el foco al quitar una. */
export function useBorradores(iniciales: readonly Omit<Borrador, 'id'>[] = CASOS_INICIALES.map((texto) => ({ texto })), maximo = Infinity) {
  const siguienteId = useRef(Math.min(iniciales.length, maximo));
  const [borradores, setBorradores] = useState<Borrador[]>(() => iniciales.slice(0, maximo).map((b, id) => ({ ...b, id })));
  const fijar = (id: number, parte: Partial<Borrador>) => setBorradores((lista) => lista.map((b) => (b.id === id ? { ...b, ...parte } : b)));
  return {
    borradores,
    fijar,
    // Escribir a mano deja de ser el caso de validación: la encuesta ya no corresponde.
    cambiarTexto: (id: number, texto: string) => fijar(id, { texto, referencia: undefined }),
    adjuntar: (id: number, documento: Documento | undefined) => fijar(id, { documento, leido: undefined, errorDocumento: undefined }),
    /** Reemplaza todas las variantes por estos textos (al volver a una pregunta del historial). */
    cargar: (textos: string[]) => setBorradores(textos.slice(0, maximo).map((texto) => ({ id: siguienteId.current++, texto }))),
    agregar: () => setBorradores((lista) => lista.length < maximo ? [...lista, { id: siguienteId.current++, texto: '' }] : lista),
    quitar: (id: number) => setBorradores((lista) => lista.filter((b) => b.id !== id)),
  };
}
