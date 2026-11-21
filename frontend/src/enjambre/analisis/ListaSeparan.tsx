import { useState } from 'react';
import { alto, MINIMO_GRUPO, type ClaveDimension, type ResumenDimension } from '../../vivo/analisis';
import estilos from './ListaSeparan.module.css';

interface Props {
  /** Las características, de la que más separa las respuestas a la que menos. */
  ranking: ResumenDimension[];
  elegida: ClaveDimension;
  /** Si la pregunta no mide postura, los extremos no llevan los colores de a favor y en contra. */
  neutra: boolean;
  alElegir(clave: ClaveDimension): void;
}

const decimal = (valor: number) => valor.toFixed(2).replace('.', ',');

/**
 * El índice de la vista, que a la vez es un gráfico: una fila por característica con sus grupos
 * puestos de 0 a 100 según cuántos respondieron de 5 a 7. Mientras más separados los puntos, más
 * divide esa característica; todas las filas comparten la escala para compararlas de un vistazo.
 * La cifra es su correlación con las notas (eta), y por ella van ordenadas.
 */
export function ListaSeparan({ ranking, elegida, neutra, alElegir }: Props) {
  const corte = ranking.findIndex((r) => !r.clara);
  const [abiertas, setAbiertas] = useState(false);
  // Las que no ordenan las respuestas van plegadas, salvo la que se esté mirando.
  const plegadas = corte < 0 ? 0 : ranking.length - corte;
  const visible = (lugar: number) => corte < 0 || lugar < corte || abiertas || ranking[lugar].dimension.clave === elegida;
  return (
    <section className={estilos.lista} aria-label="Características, de la que más separa las respuestas a la que menos" data-neutra={neutra || undefined}>
      <header>
        <h2>Qué separa más</h2>
        <span aria-hidden="true">correlación</span>
      </header>
      <ol>
        {ranking.map((resumen, lugar) => {
          const { dimension, grupos, total, extremos, fuerza } = resumen;
          const lectura = extremos ? `${extremos.brecha} puntos entre ${dimension.grupos[extremos.menor]} y ${dimension.grupos[extremos.mayor]}` : 'grupos con pocas respuestas';
          const activa = dimension.clave === elegida;
          if (!visible(lugar)) return null;
          return (
            <li key={dimension.clave} data-tenue={(corte >= 0 && lugar >= corte) || undefined}>
              <button type="button" aria-pressed={activa} title={`${dimension.rotulo}: ${lectura}`} aria-label={`${dimension.rotulo}: correlación ${decimal(fuerza)}, ${lectura}`} onClick={() => alElegir(dimension.clave)}>
                <span>{dimension.breve}</span>
                <span className={estilos.franja} aria-hidden="true">
                  <i className={estilos.total} style={{ left: `${alto(total)}%` }} />
                  {grupos.map((grupo, j) =>
                    grupo.total >= MINIMO_GRUPO ? (
                      <i key={j} data-extremo={extremos && j === extremos.mayor ? 'mayor' : extremos && j === extremos.menor ? 'menor' : undefined} style={{ left: `${alto(grupo)}%` }} />
                    ) : null,
                  )}
                </span>
                <b>{decimal(fuerza)}</b>
              </button>
            </li>
          );
        })}
      </ol>
      {plegadas > 0 && (
        <button type="button" className={estilos.resto} aria-expanded={abiertas} onClick={() => setAbiertas(!abiertas)}>
          {abiertas ? 'Ocultar las que no separan' : `${plegadas === 1 ? 'Otra' : `Otras ${plegadas}`} sin relación clara`}
          <svg viewBox="0 0 12 8" aria-hidden="true">
            <path d="M1 1.5l5 5 5-5" />
          </svg>
        </button>
      )}
    </section>
  );
}
