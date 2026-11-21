import { porcentajesDe, type CasoVivo } from '../vivo/useEnVivo';
import estilos from './Validacion.module.css';

interface Props {
  casos: CasoVivo[];
  viendo: number;
  /** Al terminar la primera variante, la comparación ocupa el centro de la pantalla unos segundos. */
  grande?: boolean;
}

/** Lo que respondieron los agentes junto a lo que respondió la gente en una encuesta real. */
export function Validacion({ casos, viendo, grande = false }: Props) {
  const base = casos[0];
  const ref = base?.referencia;
  if (!ref || !base.listo) return null;
  const simulado = porcentajesDe(base).favor;
  const distancia = Math.abs(simulado - ref.favor);
  const otra = viendo > 0 && casos[viendo]?.listo ? casos[viendo] : null;
  const textoDistancia = distancia === 0 ? 'Mismo resultado que la encuesta real' : `${distancia} ${distancia === 1 ? 'punto' : 'puntos'} de diferencia con la encuesta real`;
  return (
    <section className={estilos.validacion} data-grande={grande || undefined} aria-label="Comparación con una encuesta real">
      <p className={estilos.titulo}>{grande ? '¿Le creemos? Lo comparamos con la gente real' : 'Contra la encuesta real'}</p>
      <div className={estilos.filas}>
        <p>
          <b>{ref.favor} %</b>
          <span>
            a favor en {ref.fuente}, {ref.fecha}
          </span>
        </p>
        <p data-agentes>
          <b>{simulado} %</b>
          <span>a favor entre los agentes{otra ? `, variante ${base.letra}` : ''}</span>
        </p>
        {otra && (
          <p data-otra>
            <b>{porcentajesDe(otra).favor} %</b>
            <span>con la variante {otra.letra}{otra.iteracion ? ', reescrita por el agente' : ''}</span>
          </p>
        )}
      </div>
      <p className={estilos.distancia}>
        {textoDistancia}
        {!grande && (
          <>
            {' · '}
            <a href={ref.url} target="_blank" rel="noreferrer">
              ver informe
            </a>
          </>
        )}
      </p>
    </section>
  );
}
