import { useCallback, useRef, useState } from 'react';
import { Boton } from '../componentes/comunes/Boton';
import { CajonHistorial } from './CajonHistorial';

interface Props {
  /** Deja estos textos como las variantes por preguntar. */
  alUsar(textos: string[]): void;
}

/** El botón que abre el historial de simulaciones. Al cerrarlo, el foco vuelve al botón. */
export function MenuHistorial({ alUsar }: Props) {
  const [abierto, setAbierto] = useState(false);
  const boton = useRef<HTMLDivElement>(null);
  const cerrar = useCallback(() => {
    setAbierto(false);
    boton.current?.querySelector('button')?.focus();
  }, []);
  return (
    <div ref={boton}>
      <Boton variante="secundario" aria-expanded={abierto} aria-controls={abierto ? 'cajon-historial' : undefined} onClick={() => setAbierto(!abierto)}>
        Historial
      </Boton>
      {abierto && (
        <CajonHistorial
          alUsar={(textos) => {
            alUsar(textos);
            cerrar();
          }}
          alCerrar={cerrar}
        />
      )}
    </div>
  );
}
