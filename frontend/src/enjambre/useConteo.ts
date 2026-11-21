import { useEffect, useRef, useState } from 'react';

const DURACION = 1100;

/** Interpola sin salirse de los valores de partida y llegada, incluso si el reloj del cuadro se adelanta. */
export function valorInterpolado(origen: number, destino: number, transcurrido: number): number {
  const p = Math.max(0, Math.min(1, transcurrido / DURACION));
  return origen + (destino - origen) * (1 - (1 - p) ** 3);
}

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
      const transcurrido = ahora - inicio;
      const actual = valorInterpolado(origen, valor, transcurrido);
      desde.current = actual;
      setMostrado(actual);
      if (transcurrido < DURACION) cuadro = requestAnimationFrame(paso);
    };
    cuadro = requestAnimationFrame(paso);
    return () => cancelAnimationFrame(cuadro);
  }, [valor]);
  return mostrado;
}
