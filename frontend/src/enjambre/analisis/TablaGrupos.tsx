import type { CSSProperties } from 'react';
import { formatear } from '../../dominio/textos';
import { alto as parteAlta, MINIMO_CASILLA, MINIMO_GRUPO, type Dimension, type ResumenDimension, type ResumenGrupo } from '../../vivo/analisis';
import { FiguraWati } from '../FiguraWati';
import { rasgosDe } from '../wati';
import estilos from './TablaGrupos.module.css';

export interface Cruce {
  dimension: Dimension;
  /** Una fila por grupo de la característica principal y una columna por grupo de la segunda. */
  tabla: ResumenGrupo[][];
}

interface Props {
  resumen: ResumenDimension;
  /** Cómo se llama el tramo de 5 a 7 en esta pregunta («De acuerdo», «Justo»...): encabeza su cifra. */
  alto: string;
  /** La misma característica en la variante A, cuando se mira otra variante. */
  base: ResumenDimension | null;
  cruce: Cruce | null;
  /** La pregunta no mide postura: un solo tono en vez de los colores de a favor y en contra. */
  neutra: boolean;
  /** Los grupos del más alto al más bajo, en vez de en su orden propio. */
  porResultado: boolean;
  /** El grupo que se está leyendo (con el puntero o el teclado), para detallarlo al pie. */
  activo: number | null;
  alActivar(grupo: number | null): void;
}

/** Con esta distancia al total, en puntos, una casilla del cruce llega a su color más intenso. */
const TOPE_COLOR = 30;

/** Con más filas que estas los watis van chicos, y en ventanas bajas se retiran. */
const FILAS_HOLGADAS = 8;

/**
 * El ánimo del wati de un grupo: el de su mayoría. Sin mayoría queda indeciso; con pocas respuestas,
 * apagado; y en una pregunta que no mide postura, en el tono neutro del mapa.
 */
function animoDe(grupo: ResumenGrupo, pocos: boolean, neutra: boolean): 'favor' | 'contra' | 'indecisa' | 'neutra' | 'fantasma' {
  if (pocos) return 'fantasma';
  if (neutra) return 'neutra';
  if (grupo.favor * 2 >= grupo.total) return 'favor';
  return grupo.contra * 2 >= grupo.total ? 'contra' : 'indecisa';
}

const signo = (valor: number) => `${valor > 0 ? '+' : valor < 0 ? '−' : ''}${Math.abs(valor)}`;

/** El color de una casilla: hacia a favor si queda sobre el total, hacia en contra si queda bajo. */
function tinte(distancia: number): CSSProperties {
  const fuerza = Math.round(Math.min(Math.abs(distancia) / TOPE_COLOR, 1) * 46);
  return { '--fuerza': `${fuerza}%` } as CSSProperties;
}

/**
 * Una fila por grupo: cuántos respondieron, cómo se repartieron en la escala, cuántos quedaron de
 * 5 a 7 y a cuánto está eso del total. Una línea punteada baja por todas las barras marcando el
 * total, así se ve de un vistazo quién queda sobre él y quién bajo. Con un cruce, cada fila sigue
 * a la derecha con una casilla por grupo de la segunda característica.
 */
export function TablaGrupos({ resumen, alto: nombreAlto, base, cruce, neutra, porResultado, activo, alActivar }: Props) {
  const { dimension, grupos, total } = resumen;
  const delTotal = parteAlta(total);
  const filas = grupos.map((_, j) => j).filter((j) => grupos[j].total > 0);
  if (porResultado) {
    const valor = (j: number) => (grupos[j].total >= MINIMO_GRUPO ? grupos[j].favor / grupos[j].total : -1);
    filas.sort((a, b) => valor(b) - valor(a));
  }
  const columnas = cruce ? cruce.dimension.grupos.map((_, c) => c).filter((c) => cruce.tabla.some((fila) => fila[c].total > 0)) : [];
  const plantilla = ['minmax(8.5rem, 15rem) 3.6rem minmax(96px, 1fr) 3.4rem 5.4rem', base ? '5.4rem' : '', columnas.length ? `repeat(${columnas.length}, minmax(2.8rem, 4rem))` : ''].join(' ');
  const variables = { '--total': `${100 - delTotal}%`, '--plantilla': plantilla } as CSSProperties;
  return (
    <div className={estilos.tabla} role="table" aria-label={`${dimension.rotulo}: respuestas por grupo`} data-neutra={neutra || undefined} data-cruce={cruce ? true : undefined} data-base={base ? true : undefined} data-larga={filas.length > FILAS_HOLGADAS || undefined} style={variables}>
      <div className={estilos.cabeza} role="row">
        <span role="columnheader">Grupo de personas</span>
        <span role="columnheader" className={estilos.derecha}>
          Agentes
        </span>
        <span role="columnheader" className={estilos.marcaTotal}>
          <i>Total {delTotal} %</i>
        </span>
        <span role="columnheader" className={estilos.derecha}>
          {nombreAlto}
        </span>
        <span role="columnheader" className={estilos.derecha}>
          Contra el total
        </span>
        {base && (
          <span role="columnheader" className={estilos.derecha}>
            Contra la A
          </span>
        )}
        {cruce &&
          columnas.map((c) => (
            <span key={c} role="columnheader" className={estilos.columna} title={cruce.dimension.grupos[c]}>
              {cruce.dimension.cortos[c]}
            </span>
          ))}
      </div>
      {filas.map((j, lugar) => {
        const grupo = grupos[j];
        const pct = parteAlta(grupo);
        const pocos = grupo.total < MINIMO_GRUPO;
        const antes = base && base.grupos[j].total >= MINIMO_GRUPO ? parteAlta(base.grupos[j]) : null;
        return (
          <div
            key={`${dimension.clave}-${j}`}
            className={estilos.fila}
            role="row"
            tabIndex={0}
            data-pocos={pocos || undefined}
            data-activa={activo === j || undefined}
            style={{ '--lugar': lugar } as CSSProperties}
            onMouseEnter={() => alActivar(j)}
            onMouseLeave={() => alActivar(null)}
            onFocus={() => alActivar(j)}
            onBlur={() => alActivar(null)}
          >
            <span role="rowheader" className={estilos.nombre} title={dimension.grupos[j]}>
              <span className={estilos.figura}>
                <FiguraWati estado={animoDe(grupo, pocos, neutra)} rasgos={rasgosDe(`${dimension.clave}#${j}`)} alto={filas.length > FILAS_HOLGADAS ? 22 : 34} />
              </span>
              <span>{dimension.grupos[j]}</span>
            </span>
            <span role="cell" className={estilos.cuantos}>
              {formatear(grupo.total)}
            </span>
            <span role="cell" className={estilos.barra}>
              <span className={estilos.reparto}>
                <i data-postura="contra" style={{ flexGrow: grupo.contra }} />
                <i data-postura="indecisa" style={{ flexGrow: grupo.indecisa }} />
                <i data-postura="favor" style={{ flexGrow: grupo.favor }} />
                {antes !== null && <b className={estilos.antes} style={{ left: `${100 - antes}%` }} />}
              </span>
            </span>
            <b role="cell" className={estilos.cifra}>
              {pct} %
            </b>
            <span role="cell" className={estilos.diferencia} data-signo={pocos ? undefined : pct > delTotal ? 'mas' : pct < delTotal ? 'menos' : undefined}>
              {pocos ? 'pocos casos' : signo(pct - delTotal)}
            </span>
            {base && (
              <span role="cell" className={estilos.diferencia} data-signo={antes === null || pocos ? undefined : pct > antes ? 'mas' : pct < antes ? 'menos' : undefined}>
                {antes === null || pocos ? '' : signo(pct - antes)}
              </span>
            )}
            {cruce &&
              columnas.map((c) => {
                const casilla = cruce.tabla[j][c];
                if (casilla.total < MINIMO_CASILLA) {
                  return (
                    <span key={c} role="cell" className={estilos.casilla} data-vacia aria-label={`${cruce.dimension.grupos[c]}: ${casilla.total} agentes, muy pocos para mostrar`}>
                      ·
                    </span>
                  );
                }
                const suyo = parteAlta(casilla);
                return (
                  <span
                    key={c}
                    role="cell"
                    className={estilos.casilla}
                    data-lado={suyo > delTotal ? 'mas' : suyo < delTotal ? 'menos' : undefined}
                    style={tinte(suyo - delTotal)}
                    title={`${dimension.grupos[j]} y ${cruce.dimension.grupos[c]}: ${suyo} % entre ${formatear(casilla.total)} agentes`}
                  >
                    {suyo}
                  </span>
                );
              })}
          </div>
        );
      })}
    </div>
  );
}
