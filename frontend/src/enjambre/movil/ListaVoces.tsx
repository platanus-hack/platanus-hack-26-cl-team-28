import { useMemo, useState } from 'react';
import { mezclar } from '../../dominio/azar';
import type { Postura } from '../../dominio/tipos';
import type { AgenteRemoto } from '../../vivo/api';
import { posturaDe, type CasoVivo } from '../../vivo/useEnVivo';
import { quienEs } from '../Voces';
import estilos from './ListaVoces.module.css';

interface Props {
  caso: CasoVivo;
  agentes: AgenteRemoto[];
  muestra: number[];
  /** Cambia con cada respuesta que llega. */
  version: number;
  /** Abre la ficha de quien dijo la frase. */
  alElegir(agente: number): void;
}

/** Cuántas frases se muestran de entrada y cuántas más con cada «Ver más». */
const TANDA = 6;
/** Para alternar: una a favor, una en contra, una sin decidir. */
const TURNO: readonly Postura[] = ['favor', 'contra', 'indecisa'];

/**
 * Lo que dijeron las personas, como lista: en el teléfono no hay lugar para los globos junto a cada
 * punto del mapa. Alterna posturas, y el orden es sorteado pero fijo para cada variante.
 */
export function ListaVoces({ caso, agentes, muestra, version, alElegir }: Props) {
  const [cuantas, setCuantas] = useState(TANDA);
  const voces = useMemo(() => {
    const semilla = [...caso.id].reduce((suma, letra) => suma * 31 + letra.charCodeAt(0), 7) >>> 0;
    const porPostura: Record<Postura, number[]> = { favor: [], contra: [], indecisa: [] };
    for (const i of muestra) {
      if (caso.acuerdo[i] && caso.frase[i]?.trim()) porPostura[posturaDe(caso.acuerdo[i])].push(i);
    }
    for (const lista of Object.values(porPostura)) lista.sort((a, b) => mezclar(semilla, a) - mezclar(semilla, b));
    const alternadas: number[] = [];
    for (let k = 0; alternadas.length < muestra.length; k++) {
      const quedan = TURNO.filter((postura) => k < porPostura[postura].length);
      if (!quedan.length) break;
      for (const postura of quedan) alternadas.push(porPostura[postura][k]);
    }
    return alternadas;
  }, [caso, muestra, version]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!voces.length) return <p className={estilos.vacio}>Todavía nadie respondió con palabras.</p>;
  return (
    <div className={estilos.voces}>
      <ul className={estilos.lista}>
        {voces.slice(0, cuantas).map((i) => (
          <li key={i}>
            <button type="button" className={estilos.voz} data-postura={posturaDe(caso.acuerdo[i])} onClick={() => alElegir(i)}>
              <q>{caso.frase[i]}</q>
              <span>{agentes[i] ? quienEs(agentes[i]) : ''}</span>
            </button>
          </li>
        ))}
      </ul>
      {cuantas < voces.length && (
        <button type="button" className={estilos.mas} onClick={() => setCuantas((antes) => antes + TANDA)}>
          Ver más voces
        </button>
      )}
    </div>
  );
}
