import { vocesDe, type Notas, type ResumenDimension } from '../../vivo/analisis';
import type { AgenteRemoto } from '../../vivo/api';
import { FiguraWati } from '../FiguraWati';
import { rasgosDe } from '../wati';
import estilos from './VocesGrupos.module.css';

interface Props {
  resumen: ResumenDimension;
  pregunta: number;
  agentes: readonly AgenteRemoto[];
  notas: Notas;
  frases: readonly (string | undefined)[];
  /** Los agentes que se están mirando. */
  mirados: readonly number[];
  /** Frases por grupo: dos si hay lugar, una si la tabla es larga. */
  cuantas: number;
  neutra: boolean;
  /** Cómo se llaman los dos lados de la escala en esta pregunta. */
  nombres: { bajo: string; alto: string };
}

const GENERO = ['Mujer', 'Hombre'];

/**
 * El porqué detrás de las cifras: frases de personas del grupo que quedó más alto y del que quedó
 * más bajo. En el más alto hablan quienes respondieron de 5 a 7 y en el más bajo quienes
 * respondieron de 1 a 3: el rótulo dice qué parte del grupo son.
 */
export function VocesGrupos({ resumen, pregunta, agentes, notas, frases, mirados, cuantas, neutra, nombres }: Props) {
  const { extremos, dimension } = resumen;
  if (!extremos || extremos.brecha === 0) return null;
  const lados = [
    { grupo: extremos.mayor, lado: 'alto' as const },
    { grupo: extremos.menor, lado: 'bajo' as const },
  ].map((item) => ({ ...item, voces: vocesDe(dimension, item.grupo, item.lado, agentes, notas, frases, mirados, pregunta, cuantas) }));
  if (lados.some((item) => !item.voces.length)) return null;
  return (
    <section className={estilos.voces} aria-label="Frases de personas de los grupos más alto y más bajo" data-neutra={neutra || undefined}>
      {lados.map(({ grupo, lado, voces }) => (
        <div key={lado} data-lado={lado}>
          <span className={estilos.figura}>
            <FiguraWati estado={neutra ? 'neutra' : lado === 'alto' ? 'favor' : 'contra'} rasgos={rasgosDe(`${dimension.clave}#${grupo}`)} alto={68} />
          </span>
          <h3>
            {dimension.grupos[grupo]}
            <span>en palabras de quien respondió {nombres[lado]}</span>
          </h3>
          {voces.map((i) => (
            <figure key={i}>
              <blockquote>{frases[i]}</blockquote>
              <figcaption>
                {[GENERO[agentes[i].genero] ?? 'Persona', `${agentes[i].edad} años`, agentes[i].comuna].filter(Boolean).join(', ')}
              </figcaption>
            </figure>
          ))}
        </div>
      ))}
    </section>
  );
}
