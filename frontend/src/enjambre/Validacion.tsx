import { porcentajesDe, type CasoVivo } from '../vivo/useEnVivo';
import estilos from './Validacion.module.css';

interface Props {
  casos: CasoVivo[];
  viendo: number;
  /** Al terminar la primera variante, la comparación ocupa el centro de la pantalla unos segundos. */
  grande?: boolean;
}

/** Medido con 334 agentes en las tres encuestas de `validacion.ts` (diferencias de 1, 8 y 6 puntos). */
const HISTORIAL = 'En las 3 encuestas Cadem que probamos, la diferencia promedio fue de 5 puntos.';

/** Lo que respondieron los agentes junto a lo que respondió la gente en una encuesta real. */
export function Validacion({ casos, viendo, grande = false }: Props) {
  const base = casos[0];
  const ref = base?.referencia;
  if (!ref || !base.listo) return null;
  const simulado = porcentajesDe(base).favor;
  const distancia = Math.abs(simulado - ref.favor);
  // La variante que se mira ya tiene su cifra gigante al lado: aquí solo va la comparación con la encuesta.
  const otra = viendo > 0;
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
      </div>
      <p className={estilos.distancia}>
        {textoDistancia}
        {grande && <span className={estilos.historial}>{HISTORIAL}</span>}
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
