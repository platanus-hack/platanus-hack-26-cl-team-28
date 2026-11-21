import { useCallback, useRef, useState } from 'react';
import { Boton } from '../componentes/comunes/Boton';
import type { EnVivo } from '../vivo/useEnVivo';
import { CajonMuestra } from './CajonMuestra';

interface Props {
  sim: EnVivo;
  claro: boolean;
  alCambiarTema(): void;
  alOcultar(): void;
}

/** El botón que abre el cajón de la muestra. Al cerrarlo, el foco vuelve al botón. */
export function MenuOpciones({ sim, claro, alCambiarTema, alOcultar }: Props) {
  const [abierto, setAbierto] = useState(false);
  const boton = useRef<HTMLDivElement>(null);
  const cerrar = useCallback(() => {
    setAbierto(false);
    boton.current?.querySelector('button')?.focus();
  }, []);
  return (
    <div ref={boton}>
      <Boton variante="secundario" aria-expanded={abierto} aria-controls={abierto ? 'cajon-muestra' : undefined} onClick={() => setAbierto(!abierto)}>
        Opciones
      </Boton>
      {abierto && <CajonMuestra sim={sim} claro={claro} alCambiarTema={alCambiarTema} alOcultar={alOcultar} alCerrar={cerrar} />}
    </div>
  );
}
