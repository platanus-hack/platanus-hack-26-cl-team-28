import type { CSSProperties } from 'react';
import { REGIONES } from '../../dominio/catalogos';
import { MINIMO_REGION, type ResumenCaso } from '../../dominio/metricas';
import estilos from './FranjaRegiones.module.css';
import { repartir } from './repartir';

interface Props {
  resumen: ResumenCaso;
  /** Posición horizontal de cada región en el mapa; vacío mientras no se mide. */
  xReales: number[];
  ancho: number;
  region: number;
  alElegir(region: number): void;
}

const ANCHO_COLUMNA = 66;
const ALTO_GUIA = 16;

/**
 * El apoyo por región, alineado con el mapa de arriba: cada columna cuelga de su región
 * con una línea guía, así el gráfico comparte eje con el país.
 */
export function FranjaRegiones({ resumen, xReales, ancho, region, alElegir }: Props) {
  const medido = xReales.length === REGIONES.length && ancho > 0;
  const centros = medido ? repartir(xReales, ANCHO_COLUMNA, ANCHO_COLUMNA / 2 + 4, ancho - ANCHO_COLUMNA / 2 - 4) : [];
  return (
    <div className={estilos.franja}>
      {medido && (
        <svg className={estilos.guias} width={ancho} height={ALTO_GUIA} aria-hidden="true">
          {centros.map((centro, i) => (
            <path key={i} d={`M${xReales[i]} 0 V3 L${centro} ${ALTO_GUIA - 4} V${ALTO_GUIA}`} />
          ))}
        </svg>
      )}
      <ol className={estilos.columnas}>
        {REGIONES.map((r, i) => {
          const conteo = resumen.porRegion[i];
          const hay = conteo.total >= MINIMO_REGION;
          const pct = (parte: number) => `${(parte / (conteo.total || 1)) * 100}%`;
          const pila = { '--pct-favor': pct(conteo.favor), '--pct-indecisa': pct(conteo.indecisa) } as CSSProperties;
          return (
            <li key={r.nombre} style={medido ? ({ '--x': `${centros[i]}px` } as CSSProperties) : undefined}>
              <button type="button" aria-pressed={region === i} onClick={() => alElegir(region === i ? -1 : i)} title={r.nombre}>
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
    </div>
  );
}
