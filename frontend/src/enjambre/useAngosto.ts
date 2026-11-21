import { useEffect, useState } from 'react';

const CONSULTA = '(max-width: 899px), (max-height: 800px)';

/** Verdadero en pantallas angostas o bajas: la criatura junto a la cifra no crece, no hay lugar. */
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
