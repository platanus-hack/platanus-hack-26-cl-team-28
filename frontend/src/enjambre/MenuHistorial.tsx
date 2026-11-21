import { useCallback, useRef } from 'react';
import { Boton } from '../componentes/comunes/Boton';
import { CajonHistorial } from './CajonHistorial';
import { usePanelLateral } from './usePanelLateral';

interface Props {
  /** Deja estos textos como las variantes por preguntar. */
  alUsar(textos: string[]): void;
  /** Vuelve a mostrar una simulación guardada. Devuelve el problema si no se pudo, o null. */
  alVer(id: string): Promise<string | null>;
}

/** El botón que abre el historial de simulaciones. Al cerrarlo, el foco vuelve al botón. */
export function MenuHistorial({ alUsar, alVer }: Props) {
  const { abierto, montado, abrir, cerrar: cerrarPanel } = usePanelLateral();
  const boton = useRef<HTMLDivElement>(null);
  const cerrar = useCallback(() => {
    cerrarPanel();
    boton.current?.querySelector('button')?.focus();
  }, [cerrarPanel]);
  return (
    <div ref={boton}>
      <Boton variante="secundario" aria-expanded={abierto} aria-controls={abierto ? 'cajon-historial' : undefined} onClick={abierto ? cerrar : abrir}>
        Historial
      </Boton>
      {montado && (
        <CajonHistorial
          abierto={abierto}
          alUsar={(textos) => {
            alUsar(textos);
            cerrar();
          }}
          alVer={async (id) => {
            const problema = await alVer(id);
            // Con la simulación ya en el mapa, el cajón deja de taparla.
            if (!problema) cerrar();
            return problema;
          }}
          alCerrar={cerrar}
        />
      )}
    </div>
  );
}
