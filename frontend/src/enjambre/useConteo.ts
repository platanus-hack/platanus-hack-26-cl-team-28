import { useEffect, useRef, useState } from 'react';

const DURACION = 1100;

/** Lleva un número de su valor anterior al nuevo, contando: así se ve el cambio y no solo el resultado. */
export function useConteo(valor: number): number {
  const [mostrado, setMostrado] = useState(valor);
  const desde = useRef(valor);
  useEffect(() => {
    if (matchMedia('(prefers-reduced-motion: reduce)').matches) {
      setMostrado(valor);
      desde.current = valor;
      return;
    }
    const origen = desde.current;
    const inicio = performance.now();
    let cuadro = 0;
    const paso = (ahora: number) => {
      const p = Math.min(1, (ahora - inicio) / DURACION);
      const actual = origen + (valor - origen) * (1 - (1 - p) ** 3);
      desde.current = actual;
      setMostrado(actual);
      if (p < 1) cuadro = requestAnimationFrame(paso);
    };
    cuadro = requestAnimationFrame(paso);
    return () => cancelAnimationFrame(cuadro);
  }, [valor]);
  return mostrado;
}
