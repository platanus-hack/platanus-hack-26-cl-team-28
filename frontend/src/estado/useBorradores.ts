import { useRef, useState } from 'react';
import { CASOS_INICIALES } from '../contenido';
import type { Documento } from '../dominio/tipos';

export interface Borrador {
  id: number;
  texto: string;
  documento?: Documento;
}

/** Las variantes mientras se escriben. El id es estable para que React no pierda el foco al quitar una. */
export function useBorradores() {
  const siguienteId = useRef(CASOS_INICIALES.length);
  const [borradores, setBorradores] = useState<Borrador[]>(() => CASOS_INICIALES.map((texto, id) => ({ id, texto })));
  return {
    borradores,
    cambiarTexto: (id: number, texto: string) => setBorradores((lista) => lista.map((b) => (b.id === id ? { ...b, texto } : b))),
    adjuntar: (id: number, documento: Documento | undefined) =>
      setBorradores((lista) => lista.map((b) => (b.id === id ? { ...b, documento } : b))),
    agregar: () => setBorradores((lista) => [...lista, { id: siguienteId.current++, texto: '' }]),
    quitar: (id: number) => setBorradores((lista) => lista.filter((b) => b.id !== id)),
  };
}
