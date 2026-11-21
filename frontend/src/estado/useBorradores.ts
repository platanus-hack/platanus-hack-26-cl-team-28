import { useRef, useState } from 'react';
import { CASOS_INICIALES } from '../contenido';

export interface Borrador {
  id: number;
  texto: string;
}

/** Las variantes mientras se escriben. El id es estable para que React no pierda el foco al quitar una. */
export function useBorradores() {
  const siguienteId = useRef(CASOS_INICIALES.length);
  const [borradores, setBorradores] = useState<Borrador[]>(() => CASOS_INICIALES.map((texto, id) => ({ id, texto })));
  return {
    borradores,
    cambiarTexto: (id: number, texto: string) => setBorradores((lista) => lista.map((b) => (b.id === id ? { ...b, texto } : b))),
    agregar: () => setBorradores((lista) => [...lista, { id: siguienteId.current++, texto: '' }]),
    quitar: (id: number) => setBorradores((lista) => lista.filter((b) => b.id !== id)),
  };
}
