import type { CSSProperties } from 'react';
import { REGIONES } from '../../dominio/catalogos';
import { MINIMO_REGION, type ResumenCaso } from '../../dominio/metricas';
import estilos from './FranjaRegiones.module.css';
import { repartir } from './repartir';

interface Props {
  resumen: ResumenCaso;
  /** Posición vertical de cada región en el mapa; vacío mientras no se mide. */
  yReales: number[];
  alto: number;
  region: number;
  alElegir(region: number): void;
}

const ALTO_FILA = 34;
const ANCHO_GUIA = 26;

/**
 * El apoyo por región, de norte a sur y alineado con el mapa: cada fila cuelga de su
 * región con una línea guía, así el gráfico comparte eje con el país.
 */
export function FranjaRegiones({ resumen, yReales, alto, region, alElegir }: Props) {
  const medido = yReales.length === REGIONES.length && alto > 0;
  const centros = medido ? repartir(yReales, ALTO_FILA, ALTO_FILA / 2 + 34, alto - ALTO_FILA / 2 - 8) : [];
  return (
    <section className={estilos.franja} aria-labelledby="titulo-franja">
      <h2 id="titulo-franja">A favor por región</h2>
      {medido && (
        <svg className={estilos.guias} width={ANCHO_GUIA} height={alto} aria-hidden="true">
          {centros.map((centro, i) => (
            <path key={i} d={`M0 ${yReales[i]} H4 L${ANCHO_GUIA - 6} ${centro} H${ANCHO_GUIA}`} />
          ))}
        </svg>
      )}
      <ol className={estilos.filas}>
        {REGIONES.map((r, i) => {
          const conteo = resumen.porRegion[i];
          const hay = conteo.total >= MINIMO_REGION;
          const pct = (parte: number) => `${(parte / (conteo.total || 1)) * 100}%`;
          const pila = { '--pct-favor': pct(conteo.favor), '--pct-indecisa': pct(conteo.indecisa) } as CSSProperties;
          return (
            <li key={r.nombre} style={medido ? ({ '--y': `${centros[i]}px` } as CSSProperties) : undefined}>
              <button type="button" aria-pressed={region === i} onClick={() => alElegir(region === i ? -1 : i)}>
                <span className={estilos.nombre}>{r.corto}</span>
                <span className={estilos.pila} style={pila} data-vacia={!hay || undefined} aria-hidden="true" />
                <span className={estilos.valor}>
                  {hay ? (
                    <>
                      <b>{Math.round((conteo.favor / conteo.total) * 100)}</b> %<span className="solo-lectores"> a favor</span>
                    </>
                  ) : (
                    <small>pocos datos</small>
                  )}
                </span>
              </button>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
