import { useMemo } from 'react';
import { REGIONES } from '../../dominio/catalogos';
import { POSTURAS, type Postura } from '../../dominio/tipos';
import type { AgenteRemoto } from '../../vivo/api';
import { posturaDe, type CasoVivo } from '../../vivo/useEnVivo';
import estilos from './PorRegion.module.css';

interface Props {
  caso: CasoVivo;
  agentes: AgenteRemoto[];
  /** Índices de los agentes de la muestra en pantalla. */
  muestra: number[];
  /** Cambia con cada respuesta que llega. */
  version: number;
}

/** Con menos agentes que esto en la región, el porcentaje engaña: se dice cuántos son (como en el mapa). */
const MINIMO_PARA_PORCENTAJE = 5;

/**
 * El resultado por región, de norte a sur, escrito. En el teléfono los rótulos del mapa van
 * abreviados o solo con la cifra: esta lista dice cuál es cuál con su nombre entero.
 */
export function PorRegion({ caso, agentes, muestra, version }: Props) {
  const filas = useMemo(() => {
    const cuentas = REGIONES.map(() => ({ favor: 0, contra: 0, indecisa: 0, total: 0 }));
    for (const i of muestra) {
      const acuerdo = caso.acuerdo[i];
      const region = agentes[i]?.region;
      if (!acuerdo || region === undefined || !cuentas[region]) continue;
      cuentas[region][posturaDe(acuerdo)] += 1;
      cuentas[region].total += 1;
    }
    return REGIONES.map((region, k) => ({ nombre: region.nombre, ...cuentas[k] })).filter((fila) => fila.total > 0);
    // `version` cambia cuando llegan respuestas nuevas: el arreglo de acuerdos es el mismo objeto.
  }, [caso, agentes, muestra, version]); // eslint-disable-line react-hooks/exhaustive-deps

  const parte = (fila: (typeof filas)[number], postura: Postura) => Math.round((fila[postura] / fila.total) * 100);
  return (
    <ol className={estilos.lista} aria-label="Resultado por región, de norte a sur">
      {filas.map((fila) => {
        const pocos = fila.total < MINIMO_PARA_PORCENTAJE;
        const contra = pocos ? `${fila.contra}` : `${parte(fila, 'contra')} %`;
        const favor = pocos ? `${fila.favor}` : `${parte(fila, 'favor')} %`;
        const detalle = pocos
          ? `${fila.contra} en contra y ${fila.favor} a favor, de ${fila.total} agentes`
          : `${parte(fila, 'contra')} % en contra, ${parte(fila, 'favor')} % a favor`;
        return (
          <li key={fila.nombre} className={estilos.fila} aria-label={`${fila.nombre}: ${detalle}`}>
            <span className={estilos.cifra} data-postura="contra" aria-hidden="true">{contra}</span>
            <span className={estilos.centro} aria-hidden="true">
              <span className={estilos.nombre}>{fila.nombre}</span>
              <span className={estilos.barra}>
                {POSTURAS.map((postura) => <i key={postura} data-postura={postura} style={{ flexGrow: fila[postura] }} />)}
              </span>
            </span>
            <span className={estilos.cifra} data-postura="favor" aria-hidden="true">{favor}</span>
          </li>
        );
      })}
    </ol>
  );
}
