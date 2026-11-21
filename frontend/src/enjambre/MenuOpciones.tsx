import { useCallback, useRef, useState } from 'react';
import { Boton } from '../componentes/comunes/Boton';
import { activosEn, SECCIONES } from '../vivo/sociedad';
import type { EnVivo } from '../vivo/useEnVivo';
import { CajonMuestra, type Abiertas } from './CajonMuestra';

interface Props {
  sim: EnVivo;
  claro: boolean;
  alCambiarTema(): void;
  alOcultar(): void;
}

/** El botón que abre el cajón de la muestra. Al cerrarlo, el foco vuelve al botón. */
export function MenuOpciones({ sim, claro, alCambiarTema, alOcultar }: Props) {
  const [abierto, setAbierto] = useState(false);
  // Vive aquí y no en el cajón: al volver a abrirlo, las secciones quedan como se dejaron.
  const [abiertas, setAbiertas] = useState<Abiertas>({ muestra: true, territorio: true });
  const boton = useRef<HTMLDivElement>(null);
  const cerrar = useCallback(() => {
    setAbierto(false);
    boton.current?.querySelector('button')?.focus();
  }, []);
  const alternar = () => {
    // Al abrir, las secciones con algún filtro puesto se muestran abiertas.
    if (!abierto) setAbiertas((antes) => ({ ...antes, ...Object.fromEntries(SECCIONES.filter((s) => activosEn(sim.filtros, s.clave) > 0).map((s) => [s.clave, true])) }));
    setAbierto(!abierto);
  };
  return (
    <div ref={boton}>
      <Boton variante="secundario" aria-expanded={abierto} aria-controls={abierto ? 'cajon-muestra' : undefined} onClick={alternar}>
        Opciones
      </Boton>
      {abierto && (
        <CajonMuestra sim={sim} claro={claro} abiertas={abiertas} alAbrir={setAbiertas} alCambiarTema={alCambiarTema} alOcultar={alOcultar} alCerrar={cerrar} />
      )}
    </div>
  );
}
