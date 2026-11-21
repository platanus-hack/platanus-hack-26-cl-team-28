import { Boton } from '../componentes/comunes/Boton';
import { porcentajesDe, type CasoVivo } from '../vivo/useEnVivo';
import estilos from './BarraResultado.module.css';

interface Props {
  casos: CasoVivo[];
  viendo: number;
  /** Mientras la corrida sigue, las variantes que aún no terminan no se pueden elegir. */
  corriendo: boolean;
  alElegir(indice: number): void;
  alVolver(): void;
}

export function diferencia(caso: CasoVivo, base: CasoVivo): number {
  return porcentajesDe(caso).favor - porcentajesDe(base).favor;
}

/** Las variantes una al lado de otra: cuánto apoyo tiene cada una y cuánto gana o pierde contra la A. */
export function BarraResultado({ casos, viendo, corriendo, alElegir, alVolver }: Props) {
  return (
    <nav className={estilos.barra} aria-label="Variantes">
      <div role="tablist" aria-label="Variante en pantalla" className={estilos.pestanas}>
        {casos.map((caso, i) => {
          const pct = porcentajesDe(caso).favor;
          const delta = i > 0 && caso.listo && casos[0].listo ? diferencia(caso, casos[0]) : null;
          return (
            <button
              key={caso.id}
              type="button"
              role="tab"
              aria-selected={i === viendo}
              disabled={corriendo || !caso.listo}
              data-iteracion={caso.iteracion ? true : undefined}
              onClick={() => alElegir(i)}
            >
              <b>{caso.letra}</b>
              <span>{caso.respondidas ? `${pct} % a favor` : 'esperando'}</span>
              {delta !== null && (
                <em data-signo={delta > 0 ? 'mas' : delta < 0 ? 'menos' : undefined}>
                  {delta > 0 ? '+' : ''}
                  {delta} pts
                </em>
              )}
              {caso.iteracion && <small>reescrita por el agente</small>}
            </button>
          );
        })}
      </div>
      {!corriendo && (
        <Boton variante="texto" onClick={alVolver}>
          Nueva pregunta
        </Boton>
      )}
    </nav>
  );
}
