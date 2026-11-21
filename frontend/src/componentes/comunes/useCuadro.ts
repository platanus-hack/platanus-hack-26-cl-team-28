import { useEffect, useState } from 'react';

const INTERVALO = 170;

/** Cuadro de la animación de los dibujos (el trazo "hierve" a unos seis cuadros por segundo). */
export function useCuadro(): number {
  const [cuadro, setCuadro] = useState(0);
  useEffect(() => {
    if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const reloj = window.setInterval(() => {
      if (!document.hidden) setCuadro((c) => (c + 1) % 3);
    }, INTERVALO);
    return () => window.clearInterval(reloj);
  }, []);
  return cuadro;
}
