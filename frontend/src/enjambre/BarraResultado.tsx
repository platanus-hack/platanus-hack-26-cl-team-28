import { Boton } from '../componentes/comunes/Boton';
import { POSTURAS } from '../dominio/tipos';
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

/** La postura más frecuente de cada variante y su diferencia de apoyo respecto de la A. */
export function BarraResultado({ casos, viendo, corriendo, alElegir, alVolver }: Props) {
  return (
    <nav className={estilos.barra} aria-label="Variantes">
      <div role="tablist" aria-label="Variante en pantalla" className={estilos.pestanas}>
        {casos.map((caso, i) => {
          const pct = porcentajesDe(caso);
          const mayor = Math.max(caso.conteo.favor, caso.conteo.indecisa, caso.conteo.contra);
          const lideres = POSTURAS.filter((postura) => caso.conteo[postura] === mayor);
          const lider = lideres.length === 1 ? lideres[0] : undefined;
          const cuota = lider ? pct[lider] : Math.max(pct.favor, pct.indecisa, pct.contra);
          const detalle = caso.respondidas ? `${pct.favor} % a favor, ${pct.indecisa} % sin decidir, ${pct.contra} % en contra` : undefined;
          const delta = i > 0 && caso.listo && casos[0].listo ? diferencia(caso, casos[0]) : null;
          return (
            <button
              key={caso.id}
              type="button"
              role="tab"
              aria-selected={i === viendo}
              aria-description={detalle}
              title={detalle}
              disabled={corriendo || !caso.listo}
              data-iteracion={caso.iteracion ? true : undefined}
              onClick={() => alElegir(i)}
            >
              <b className={estilos.letra}>{caso.letra}</b>
              <span className={estilos.dato}>
                {caso.respondidas ? <strong data-postura={lider}>{cuota} %</strong> : 'esperando'}
              </span>
              {delta !== null && (
                <em data-signo={delta > 0 ? 'mas' : delta < 0 ? 'menos' : undefined}>
                  {delta > 0 ? '+' : ''}
                  {delta} pts
                </em>
              )}
              {caso.iteracion && <small>versión del agente</small>}
              <span className={estilos.reparto} aria-hidden="true">
                {POSTURAS.map((postura) => <i key={postura} data-postura={postura} style={{ width: `${pct[postura]}%` }} />)}
              </span>
            </button>
          );
        })}
      </div>
      {!corriendo && (
        <Boton variante="secundario" onClick={alVolver}>
          Nueva pregunta
        </Boton>
      )}
    </nav>
  );
}
