import { forwardRef, type ReactNode } from 'react';
import type { CasoVivo } from '../../vivo/useEnVivo';
import { Propuesta } from '../Propuesta';
import estilos from './BarraSuperior.module.css';

interface Props {
  caso?: CasoVivo;
  /** El botón de más opciones. */
  menu: ReactNode;
}

/**
 * Arriba en el teléfono: qué se preguntó, en dos líneas (al tocarlo se lee entero), y el menú.
 * Tiene fondo propio: el mapa empieza debajo de ella y no se pisan.
 */
export const BarraSuperior = forwardRef<HTMLElement, Props>(function BarraSuperior({ caso, menu }, ref) {
  return (
    <header ref={ref} className={estilos.barra}>
      {caso ? (
        <h1 className={estilos.pregunta}>
          <span>
            Variante {caso.letra}
            {caso.iteracion && ' · reescrita por el agente'}
          </span>
          <Propuesta letra={caso.letra} titulo={caso.titulo} texto={caso.texto} />
        </h1>
      ) : (
        <h1 className={estilos.titular}>What If Chile...</h1>
      )}
      {menu}
    </header>
  );
});
