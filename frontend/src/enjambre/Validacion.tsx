import { useId, type CSSProperties } from 'react';
import { porcentajesDe, type CasoVivo } from '../vivo/useEnVivo';
import estilos from './Validacion.module.css';

interface Props {
  casos: CasoVivo[];
  /** Escrita en la página, sin botón ni tarjeta flotante (la hoja del teléfono, que pone su propio título). */
  enLinea?: boolean;
}

/**
 * La encuesta real y los agentes sobre una misma regla de 0 a 100: qué tan cerca quedaron se
 * ve por la distancia entre las dos marcas, antes de leer ningún número.
 */
export function Validacion({ casos, enLinea = false }: Props) {
  const tarjeta = useId();
  const titulo = `${tarjeta}-titulo`;
  const base = casos[0];
  const ref = base?.referencia;
  if (!ref || !base.listo) return null;
  const simulado = porcentajesDe(base).favor;
  const distancia = Math.abs(simulado - ref.favor);
  const marcas = { '--encuesta': `${ref.favor}%`, '--agentes': `${simulado}%` } as CSSProperties;
  const contenido = (
    <>
      <dl className={estilos.cifras}>
        <div>
          <dt>Cadem</dt>
          <dd>{ref.favor} %</dd>
        </div>
        <div data-agentes>
          <dt>Agentes</dt>
          <dd>{simulado} %</dd>
        </div>
      </dl>
      <span className={estilos.linea} aria-hidden="true" />
      <footer className={estilos.pie}>
        <p>{distancia === 0 ? 'Mismo resultado' : `${distancia} ${distancia === 1 ? 'punto' : 'puntos'} de diferencia`}</p>
        <a href={ref.url} target="_blank" rel="noreferrer">{ref.fuente}, {ref.fecha}</a>
      </footer>
    </>
  );
  if (enLinea) {
    return (
      <div className={estilos.enLinea} style={marcas}>
        {contenido}
      </div>
    );
  }
  return (
    <div className={estilos.contenedor} style={marcas}>
      <button type="button" className={estilos.boton} popoverTarget={tarjeta} aria-label="Comparar con la encuesta real">
        <span className={estilos.linea} aria-hidden="true" />
      </button>
      <section id={tarjeta} popover="auto" className={estilos.tarjeta} aria-labelledby={titulo}>
        <header className={estilos.cabeza}>
          <h2 id={titulo}>Encuesta real y agentes{casos.length > 1 ? `, variante ${base.letra}` : ''}</h2>
          <button type="button" className={estilos.cerrar} popoverTarget={tarjeta} popoverTargetAction="hide" aria-label="Cerrar comparación">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" aria-hidden="true">
              <path d="m4 4 8 8m0-8-8 8" />
            </svg>
          </button>
        </header>
        {contenido}
      </section>
    </div>
  );
}
