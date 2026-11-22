import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react';
import { Boton } from '../componentes/comunes/Boton';
import type { EnVivo } from '../vivo/useEnVivo';
import { CajonMuestra, type Abiertas } from './CajonMuestra';
import { usePanelLateral } from './usePanelLateral';

/**
 * El estado del cajón de la muestra, separado de su botón: en móvil el botón vive en un menú que se
 * cierra, y el cajón tiene que seguir abierto fuera de él.
 */
export function useMenuOpciones(sim: EnVivo, devolverFoco?: () => void): { abierto: boolean; bloqueado: boolean; abrir(): void; cerrar(): void; cajon: ReactNode } {
  const { abierto, montado, abrir, cerrar: cerrarPanel } = usePanelLateral();
  const bloqueado = sim.fase === 'resultados';
  const visible = abierto && !bloqueado;
  // Vive aquí y no en el cajón: al volver a abrirlo, las secciones quedan como se dejaron.
  const [abiertas, setAbiertas] = useState<Abiertas>({ muestra: true });
  const cerrar = useCallback(() => {
    cerrarPanel();
    devolverFoco?.();
  }, [cerrarPanel, devolverFoco]);
  useEffect(() => {
    if (bloqueado) cerrarPanel();
  }, [bloqueado, cerrarPanel]);
  const cajon = montado ? <CajonMuestra abierto={visible} sim={sim} abiertas={abiertas} alAbrir={setAbiertas} alCerrar={cerrar} /> : null;
  return { abierto: visible, bloqueado, abrir, cerrar, cajon };
}

interface Props {
  sim: EnVivo;
}

/** El botón que abre el cajón de la muestra. Al cerrarlo, el foco vuelve al botón. */
export function MenuOpciones({ sim }: Props) {
  const boton = useRef<HTMLDivElement>(null);
  const devolverFoco = useCallback(() => boton.current?.querySelector('button')?.focus(), []);
  const { abierto, bloqueado, abrir, cerrar, cajon } = useMenuOpciones(sim, devolverFoco);
  return (
    <div ref={boton}>
      <Boton variante="secundario" disabled={bloqueado} aria-expanded={abierto} aria-controls={abierto ? 'cajon-muestra' : undefined} onClick={abierto ? cerrar : abrir}>
        Opciones
      </Boton>
      {cajon}
    </div>
  );
}
