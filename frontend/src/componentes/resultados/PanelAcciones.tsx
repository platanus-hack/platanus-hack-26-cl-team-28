import { POSTURA_TEXTO, RESULTADOS } from '../../contenido';
import { ACCIONES } from '../../dominio/catalogos';
import type { ResumenCaso } from '../../dominio/metricas';
import { POSTURAS } from '../../dominio/tipos';
import estilos from './PanelAcciones.module.css';

/** Qué haría la gente ante la variante activa, y de qué postura es quien lo haría. */
export function PanelAcciones({ resumen, letra }: { resumen: ResumenCaso; letra: string }) {
  const total = resumen.conteo.total || 1;
  const mayor = Math.max(1, ...resumen.acciones.map((accion) => accion.total));
  return (
    <section className={estilos.panel} aria-labelledby="titulo-acciones">
      <h2 id="titulo-acciones">
        {RESULTADOS.acciones} <span>ante la variante {letra}</span>
      </h2>
      <ul className={estilos.lista}>
        {ACCIONES.map((accion, i) => {
          const conteo = resumen.acciones[i];
          return (
            <li key={accion}>
              <span className={estilos.nombre}>{accion}</span>
              <b>{Math.round((conteo.total / total) * 100)} %</b>
              <span className={estilos.barra} style={{ width: `${(conteo.total / mayor) * 100}%` }} aria-hidden="true">
                {POSTURAS.map((postura) => (
                  <i key={postura} data-postura={postura} style={{ flexGrow: conteo[postura] }} />
                ))}
              </span>
            </li>
          );
        })}
      </ul>
      <p className={estilos.clave}>
        {POSTURAS.map((postura) => (
          <span key={postura}>
            <i data-postura={postura} aria-hidden="true" />
            {POSTURA_TEXTO[postura]}
          </span>
        ))}
      </p>
    </section>
  );
}
