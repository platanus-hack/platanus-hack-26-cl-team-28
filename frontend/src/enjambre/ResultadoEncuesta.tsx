import { useId, useMemo, useState } from 'react';
import { porcentajes } from '../dominio/metricas';
import { midePostura, preguntaDe, resumirEncuesta } from '../vivo/encuesta';
import type { CasoVivo } from '../vivo/useEnVivo';
import estilos from './ResultadoEncuesta.module.css';

interface Props {
  casos: CasoVivo[];
  viendo: number;
  /** Las preguntas de la corrida, en el orden de las notas de cada agente. */
  preguntas: readonly string[];
  /** Los agentes que se están mirando (la muestra, o quienes pasan los filtros). */
  agentes: number[];
  /** Cambia cada vez que llegan respuestas. */
  version: number;
}

const decimal = (valor: number) => valor.toFixed(1).replace('.', ',');

/**
 * Cómo respondieron cada pregunta de la encuesta en la variante que se mira: el criterio, el
 * reparto entre el lado bajo (1 a 3), el medio (4) y el lado alto (5 a 7) de su escala, y cuántos
 * quedan en el lado alto. Cada pregunta tiene su escala: en Justicia el 7 es «muy justo», en
 * Influencia «muy influyente». Con más de una variante, también cuánto cambia cada pregunta
 * contra la A. Al tocar un criterio se lee la pregunta completa, con su desglose y su nota media.
 */
export function ResultadoEncuesta({ casos, viendo, preguntas, agentes, version }: Props) {
  const caso = casos[viendo];
  const base = viendo > 0 && casos[0].listo ? casos[0] : null;
  const id = useId();
  const [abierta, setAbierta] = useState<number | null>(null);
  const filas = useMemo(
    () => resumirEncuesta(caso.notas, agentes, preguntas.length),
    // `version` cambia con cada respuesta que llega: las notas se llenan en el mismo arreglo.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [caso, agentes, preguntas.length, version],
  );
  const deLaA = useMemo(
    () => (base ? resumirEncuesta(base.notas, agentes, preguntas.length) : null),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [base, agentes, preguntas.length, version],
  );
  if (!filas.some((fila) => fila.conteo.total > 0)) return null;
  return (
    <section className={estilos.encuesta} aria-label={`Resultado de cada pregunta${casos.length > 1 ? `, variante ${caso.letra}` : ''}`}>
      <header>
        <h2>
          Encuesta · {preguntas.length} {preguntas.length === 1 ? 'pregunta' : 'preguntas'}
        </h2>
      </header>
      <ol>
        {preguntas.map((pregunta, k) => {
          const { conteo, media } = filas[k];
          const pct = porcentajes(conteo);
          const delta = deLaA && deLaA[k].conteo.total ? pct.favor - porcentajes(deLaA[k].conteo).favor : null;
          const escala = preguntaDe(pregunta);
          const expandida = abierta === k;
          const idDetalle = `${id}-${k}`;
          const alto = escala ? `hacia «${escala.maximo}» (5 a 7)` : 'entre 5 y 7';
          const bajo = escala ? `hacia «${escala.minimo}» (1 a 3)` : 'entre 1 y 3';
          const detalle = `${pct.favor} % ${alto}, ${pct.indecisa} % al medio y ${pct.contra} % ${bajo}. Nota media ${decimal(media)} de 7`;
          return (
            <li key={pregunta} data-neutra={!midePostura(pregunta) || undefined}>
              <button type="button" aria-expanded={expandida} aria-controls={idDetalle} onClick={() => setAbierta(expandida ? null : k)}>
                <span>{escala?.nombre ?? `Pregunta ${k + 1}`}</span>
                <svg width="10" height="7" viewBox="0 0 10 7" aria-hidden="true">
                  <path d="m1 1.5 4 4 4-4" />
                </svg>
              </button>
              <div className={estilos.reparto} role="img" aria-label={detalle}>
                <i data-postura="contra" style={{ flexGrow: conteo.contra }} />
                <i data-postura="indecisa" style={{ flexGrow: conteo.indecisa }} />
                <i data-postura="favor" style={{ flexGrow: conteo.favor }} />
              </div>
              <b>
                {pct.favor} %
                {delta !== null && (
                  <em data-signo={delta > 0 ? 'mas' : delta < 0 ? 'menos' : undefined}>
                    {delta > 0 ? '+' : ''}
                    {delta}
                  </em>
                )}
              </b>
              <div className={estilos.despliegue} id={idDetalle} data-abierta={expandida || undefined} aria-hidden={!expandida} inert={!expandida}>
                <div className={estilos.contenidoDetalle}>
                  <div className={estilos.detalle}>
                    <p className={estilos.pregunta}>{pregunta}</p>
                    <p>{detalle}, entre {conteo.total} {conteo.total === 1 ? 'respuesta' : 'respuestas'}</p>
                  </div>
                </div>
              </div>
            </li>
          );
        })}
      </ol>
      <footer>
        <span data-postura="contra">1 a 3</span>
        <span data-postura="indecisa">Al medio (4)</span>
        <span data-postura="favor">5 a 7</span>
      </footer>
    </section>
  );
}
