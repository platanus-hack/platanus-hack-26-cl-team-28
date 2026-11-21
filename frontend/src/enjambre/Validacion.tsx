import { porcentajesDe, type CasoVivo } from '../vivo/useEnVivo';
import estilos from './Validacion.module.css';

/** Lo que respondieron los agentes junto a lo que respondió la gente en una encuesta real. */
export function Validacion({ caso }: { caso: CasoVivo }) {
  const ref = caso.referencia;
  if (!ref || !caso.listo) return null;
  const simulado = porcentajesDe(caso).favor;
  const distancia = Math.abs(simulado - ref.favor);
  return (
    <section className={estilos.validacion} aria-label="Comparación con una encuesta real">
      <p className={estilos.titulo}>Contra la encuesta real</p>
      <div className={estilos.filas}>
        <p>
          <b>{ref.favor} %</b>
          <span>
            a favor en {ref.fuente}, {ref.fecha}
          </span>
        </p>
        <p>
          <b>{simulado} %</b>
          <span>a favor entre los agentes</span>
        </p>
      </div>
      <p className={estilos.distancia}>
        {distancia === 0 ? 'Mismo resultado' : `${distancia} ${distancia === 1 ? 'punto' : 'puntos'} de diferencia`}
        {' · '}
        <a href={ref.url} target="_blank" rel="noreferrer">
          ver informe
        </a>
      </p>
    </section>
  );
}
