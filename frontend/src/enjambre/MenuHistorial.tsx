import { useCallback, useRef, type ReactNode } from 'react';
import { Boton } from '../componentes/comunes/Boton';
import { CajonHistorial } from './CajonHistorial';
import { usePanelLateral } from './usePanelLateral';

interface Opciones {
  /** Deja estos textos como las variantes por preguntar. */
  alUsar(textos: string[]): void;
  /** Vuelve a mostrar una simulación guardada. Devuelve el problema si no se pudo, o null. */
  alVer(id: string): Promise<string | null>;
  /** A dónde vuelve el foco al cerrar el cajón. */
  devolverFoco?(): void;
}

/**
 * El estado del cajón del historial, separado de su botón: en móvil el botón vive en un menú que se
 * cierra, y el cajón tiene que seguir abierto fuera de él.
 */
export function useMenuHistorial({ alUsar, alVer, devolverFoco }: Opciones): { abierto: boolean; abrir(): void; cerrar(): void; cajon: ReactNode } {
  const { abierto, montado, abrir, cerrar: cerrarPanel } = usePanelLateral();
  const cerrar = useCallback(() => {
    cerrarPanel();
    devolverFoco?.();
  }, [cerrarPanel, devolverFoco]);
  const cajon = montado ? (
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
  ) : null;
  return { abierto, abrir, cerrar, cajon };
}

/** El botón que abre el historial de simulaciones. Al cerrarlo, el foco vuelve al botón. */
export function MenuHistorial({ alUsar, alVer }: Omit<Opciones, 'devolverFoco'>) {
  const boton = useRef<HTMLDivElement>(null);
  const devolverFoco = useCallback(() => boton.current?.querySelector('button')?.focus(), []);
  const { abierto, abrir, cerrar, cajon } = useMenuHistorial({ alUsar, alVer, devolverFoco });
  return (
    <div ref={boton}>
      <Boton variante="secundario" aria-expanded={abierto} aria-controls={abierto ? 'cajon-historial' : undefined} onClick={abierto ? cerrar : abrir}>
        Historial
      </Boton>
      {cajon}
    </div>
  );
}
