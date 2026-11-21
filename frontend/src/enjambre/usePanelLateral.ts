import { useCallback, useEffect, useState } from 'react';

const SALIDA_MS = 160; // Misma duración que el panel lateral en Popup.module.css.

/** Conserva el panel durante su salida y permite reabrirlo en mitad de la transición. */
export function usePanelLateral() {
  const [estado, setEstado] = useState<'cerrado' | 'abierto' | 'saliendo'>('cerrado');

  useEffect(() => {
    if (estado !== 'saliendo') return;
    const espera = window.setTimeout(() => setEstado((actual) => actual === 'saliendo' ? 'cerrado' : actual), SALIDA_MS);
    return () => window.clearTimeout(espera);
  }, [estado]);

  const abrir = useCallback(() => setEstado('abierto'), []);
  const cerrar = useCallback(() => {
    const reducir = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    setEstado((actual) => {
      if (actual !== 'abierto') return actual;
      return reducir ? 'cerrado' : 'saliendo';
    });
  }, []);

  return { abierto: estado === 'abierto', montado: estado !== 'cerrado', abrir, cerrar };
}
