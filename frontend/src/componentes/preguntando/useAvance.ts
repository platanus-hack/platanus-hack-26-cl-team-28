import { useEffect, useState } from 'react';

/** Avance de 0 a 1 de una animación de `duracion` segundos que parte cuando cambia `clave`. */
export function useAvance(clave: unknown, duracion: number): number {
  const [avance, setAvance] = useState(0);
  useEffect(() => {
    if (matchMedia('(prefers-reduced-motion: reduce)').matches) {
      setAvance(1);
      return;
    }
    const inicio = performance.now();
    setAvance(0);
    const reloj = window.setInterval(() => {
      const valor = Math.min(1, (performance.now() - inicio) / (duracion * 1000));
      setAvance(valor);
      if (valor >= 1) window.clearInterval(reloj);
    }, 90);
    return () => window.clearInterval(reloj);
  }, [clave, duracion]);
  return avance;
}
