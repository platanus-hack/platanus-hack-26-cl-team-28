import { useMemo, useState } from 'react';
import { porcentajes } from '../dominio/metricas';
import { resumirEncuesta } from '../vivo/encuesta';
import type { CasoVivo } from '../vivo/useEnVivo';
import estilos from './ResultadoEncuesta.module.css';

interface Props {
  casos: CasoVivo[];
  viendo: number;
  /** Las preguntas de la corrida, en el orden de las notas de cada agente. */
  preguntas: string[];
  /** Los agentes que se están mirando (la muestra, o quienes pasan los filtros). */
  agentes: number[];
  /** Cambia cada vez que llegan respuestas. */
  version: number;
}

const decimal = (valor: number) => valor.toFixed(1).replace('.', ',');

/**
 * Cómo respondieron cada pregunta de la encuesta en la variante que se mira: la pregunta, el
 * reparto entre en desacuerdo, al medio y de acuerdo, y cuántos están de acuerdo. Con más de
 * una variante, también cuánto cambia cada pregunta contra la A. Al tocar una pregunta se lee
 * completa, con su desglose y su nota media.
 */
export function ResultadoEncuesta({ casos, viendo, preguntas, agentes, version }: Props) {
  const caso = casos[viendo];
  const base = viendo > 0 && casos[0].listo ? casos[0] : null;
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
        <span>De acuerdo</span>
      </header>
      <ol>
        {preguntas.map((pregunta, k) => {
          const { conteo, media } = filas[k];
          const pct = porcentajes(conteo);
          const delta = deLaA && deLaA[k].conteo.total ? pct.favor - porcentajes(deLaA[k].conteo).favor : null;
          const detalle = `${pct.favor} % de acuerdo, ${pct.indecisa} % al medio y ${pct.contra} % en desacuerdo. Nota media ${decimal(media)} de 7`;
          return (
            <li key={pregunta} data-abierta={abierta === k || undefined}>
              <button type="button" aria-expanded={abierta === k} title={abierta === k ? undefined : pregunta} onClick={() => setAbierta(abierta === k ? null : k)}>
                <span>
                  <i aria-hidden="true">{k + 1}</i>
                  {pregunta}
                </span>
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
              {abierta === k && (
                <p className={estilos.detalle}>
                  {detalle}, entre {conteo.total} {conteo.total === 1 ? 'respuesta' : 'respuestas'}
                </p>
              )}
            </li>
          );
        })}
      </ol>
      <footer>
        <span data-postura="contra">En desacuerdo 1 a 3</span>
        <span data-postura="indecisa">Al medio 4</span>
        <span data-postura="favor">De acuerdo 5 a 7</span>
      </footer>
    </section>
  );
}
