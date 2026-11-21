import { useCallback, useRef, useState } from 'react';
import { Boton } from '../componentes/comunes/Boton';
import type { EnVivo } from '../vivo/useEnVivo';
import { CajonMuestra, type Abiertas } from './CajonMuestra';
import { usePanelLateral } from './usePanelLateral';

interface Props {
  sim: EnVivo;
}

/** El botón que abre el cajón de la muestra. Al cerrarlo, el foco vuelve al botón. */
export function MenuOpciones({ sim }: Props) {
  const { abierto, montado, abrir, cerrar: cerrarPanel } = usePanelLateral();
  // Vive aquí y no en el cajón: al volver a abrirlo, las secciones quedan como se dejaron.
  const [abiertas, setAbiertas] = useState<Abiertas>({ muestra: true });
  const boton = useRef<HTMLDivElement>(null);
  const cerrar = useCallback(() => {
    cerrarPanel();
    boton.current?.querySelector('button')?.focus();
  }, [cerrarPanel]);
  return (
    <div ref={boton}>
      <Boton variante="secundario" aria-expanded={abierto} aria-controls={abierto ? 'cajon-muestra' : undefined} onClick={abierto ? cerrar : abrir}>
        Opciones
      </Boton>
      {montado && (
        <CajonMuestra abierto={abierto} sim={sim} abiertas={abiertas} alAbrir={setAbiertas} alCerrar={cerrar} />
      )}
    </div>
  );
}
