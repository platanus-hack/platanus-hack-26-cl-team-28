import { MAPA, POSTURA_TITULO } from '../../contenido';
import { Figura } from '../comunes/Figura';
import estilos from './Leyenda.module.css';

/** Explica las posturas con el mismo dibujo del mapa: brazos en alto, encogida de hombros o cartel. */
export function Leyenda({ conPosturas }: { conPosturas: boolean }) {
  return (
    <div className={estilos.leyenda}>
      <p className={estilos.norte}>
        <span aria-hidden="true" className={estilos.flecha} />
        <b>N</b> {MAPA.orientacion}
        <span className={estilos.pista}>. {MAPA.arrastre}</span>
      </p>
      <ul>
        {!conPosturas && (
          <li>
            <Figura estado="neutra" aspecto={0} alto={36} />
            En la muestra
          </li>
        )}
        {conPosturas &&
          (['favor', 'indecisa', 'contra'] as const).map((postura, i) => (
            <li key={postura}>
              <Figura estado={postura} aspecto={i + 1} alto={36} />
              {POSTURA_TITULO[postura]}
            </li>
          ))}
        {!conPosturas && (
          <li>
            <Figura estado="fantasma" aspecto={3} alto={36} />
            Fuera de la muestra
          </li>
        )}
      </ul>
    </div>
  );
}
