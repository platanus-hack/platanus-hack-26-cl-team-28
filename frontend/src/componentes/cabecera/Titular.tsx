import { POSTURA_TEXTO, PREPARAR } from '../../contenido';
import { formatear } from '../../dominio/textos';
import { cambianDePostura } from '../../estado/corrida';
import type { Simulacion } from '../../estado/useSimulacion';
import estilos from './Titular.module.css';

/** Voz de la página: la pregunta mientras se prepara y, después, el caso activo con su cifra principal. */
export function Titular({ sim }: { sim: Simulacion }) {
  const { fase, corrida, muestra } = sim;
  if (fase === 'preparar' || !corrida) {
    return (
      <section className={estilos.titular}>
        <div className={estilos.voz}>
          <h1>{PREPARAR.titular}</h1>
          <p>{PREPARAR.bajada}</p>
        </div>
        <p className={estilos.cifra}>
          <b>{formatear(muestra.total)}</b>
          <span>
            personas simuladas en la muestra
            <small>{muestra.total > 0 ? PREPARAR.figuras : PREPARAR.sinPersonas}</small>
          </span>
        </p>
      </section>
    );
  }
  const indice = fase === 'preguntando' ? sim.enBarrido : sim.activo;
  const caso = corrida.casos[indice];
  const pct = corrida.resumenes[indice].porcentajes;
  return (
    <section className={estilos.titular}>
      <div className={estilos.voz}>
        <p className={estilos.sobre}>
          {fase === 'preguntando' ? 'Preguntando la variante' : 'Variante'} {caso.letra} de {corrida.casos.length} · {formatear(corrida.muestra.total)} personas simuladas
          {fase === 'resultados' && sim.anterior !== sim.activo && (
            <span className={estilos.cambio} key={`${sim.anterior}-${sim.activo}`}>
              {formatear(cambianDePostura(corrida, sim.anterior, sim.activo))} cambian de postura respecto de la variante {corrida.casos[sim.anterior].letra}
            </span>
          )}
        </p>
        <h1 className={estilos.caso}>{caso.texto}</h1>
      </div>
      {fase === 'resultados' && (
        <p className={estilos.cifra} aria-live="polite">
          <b className={estilos.favor}>{pct.favor} %</b>
          <span>
            {POSTURA_TEXTO.favor}
            <small>
              {pct.indecisa} % {POSTURA_TEXTO.indecisa} · {pct.contra} % {POSTURA_TEXTO.contra}
            </small>
          </span>
        </p>
      )}
    </section>
  );
}
