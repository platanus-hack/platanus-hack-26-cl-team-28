import type { CSSProperties } from 'react';
import { porcentajesDe, type CasoVivo } from '../vivo/useEnVivo';
import estilos from './Validacion.module.css';

interface Props {
  casos: CasoVivo[];
}

/**
 * La encuesta real y los agentes sobre una misma regla de 0 a 100: qué tan cerca quedaron se
 * ve por la distancia entre las dos marcas, antes de leer ningún número.
 */
export function Validacion({ casos }: Props) {
  const base = casos[0];
  const ref = base?.referencia;
  if (!ref || !base.listo) return null;
  const simulado = porcentajesDe(base).favor;
  const distancia = Math.abs(simulado - ref.favor);
  const marcas = { '--encuesta': `${ref.favor}%`, '--agentes': `${simulado}%` } as CSSProperties;
  return (
    <section className={estilos.regla} aria-label="Comparación con una encuesta real">
      <p className={estilos.titulo}>
        Encuesta real y agentes{casos.length > 1 ? `, variante ${base.letra}` : ''}
      </p>
      <div className={estilos.pista} style={marcas}>
        <p className={estilos.marca} data-encuesta>
          <b>{ref.favor} %</b> Cadem
        </p>
        <span className={estilos.linea} aria-hidden="true" />
        <p className={estilos.marca} data-agentes>
          <b>{simulado} %</b> agentes
        </p>
      </div>
      <p className={estilos.pie}>
        {distancia === 0 ? 'Mismo resultado' : `${distancia} ${distancia === 1 ? 'punto' : 'puntos'} de diferencia`}
        {' · '}
        <a href={ref.url} target="_blank" rel="noreferrer">
          {ref.fuente}, {ref.fecha}
        </a>
      </p>
    </section>
  );
}
