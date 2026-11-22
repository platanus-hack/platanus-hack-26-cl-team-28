import { useEffect, useState } from 'react';

/** Si la pantalla cumple una consulta de medios; se actualiza al cambiar de tamaño u orientación. */
export function useConsulta(consulta: string): boolean {
  const [cumple, setCumple] = useState(() => matchMedia(consulta).matches);
  useEffect(() => {
    const medio = matchMedia(consulta);
    const cambio = () => setCumple(medio.matches);
    cambio();
    medio.addEventListener('change', cambio);
    return () => medio.removeEventListener('change', cambio);
  }, [consulta]);
  return cumple;
}

/** Verdadero en pantallas angostas o bajas: la criatura junto a la cifra no crece, no hay lugar. */
export function useAngosto(): boolean {
  return useConsulta('(max-width: 899px), (max-height: 800px)');
}

/** El ancho desde el que la interfaz deja las columnas a los costados del país y pasa a la hoja inferior. */
export const CONSULTA_MOVIL = '(max-width: 899px)';

/** Verdadero en teléfonos y ventanas angostas: barra arriba, mapa al medio y hoja abajo. */
export function useMovil(): boolean {
  return useConsulta(CONSULTA_MOVIL);
}
