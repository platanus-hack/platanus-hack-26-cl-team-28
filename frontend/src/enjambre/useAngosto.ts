import { useEffect, useState } from 'react';

const CONSULTA = '(max-width: 899px)';

/** Verdadero en pantallas angostas, donde las cifras van bajo el mapa y no a sus costados. */
export function useAngosto(): boolean {
  const [angosto, setAngosto] = useState(() => matchMedia(CONSULTA).matches);
  useEffect(() => {
    const consulta = matchMedia(CONSULTA);
    const cambio = () => setAngosto(consulta.matches);
    consulta.addEventListener('change', cambio);
    return () => consulta.removeEventListener('change', cambio);
  }, []);
  return angosto;
}
