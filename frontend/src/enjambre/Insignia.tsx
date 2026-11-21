import { formatear } from '../dominio/textos';
import type { Conexion } from '../vivo/useEnVivo';
import estilos from './Insignia.module.css';

interface Props {
  conexion: Conexion | null;
  agentes: number;
  /** Porcentaje que no se decide, cuando hay un resultado en pantalla. */
  indecisas?: number;
}

/**
 * Ficha de la muestra: a quiénes se les pregunta y, con un resultado en pantalla, qué son los
 * puntos amarillos que se quedan en el mapa. Si no responde el motor en vivo, lo avisa.
 */
export function Insignia({ conexion, agentes, indecisas }: Props) {
  if (!conexion) return null;
  const motor = conexion.estado?.motor;
  const aviso = conexion.demo || !motor || motor.grabado ? 'Demostración sin motor' : null;
  return (
    <dl className={estilos.ficha}>
      <div>
        <dt>Muestra · Censo 2024</dt>
        <dd>
          <b>{formatear(agentes)}</b> <span className={estilos.unidad}>agentes</span>
        </dd>
      </div>
      {indecisas !== undefined && (
        <div data-indecisas>
          <dt>
            <i aria-hidden="true" />
            Sin decidir
          </dt>
          <dd>
            <b>{indecisas} %</b> se queda en el mapa
          </dd>
        </div>
      )}
      {aviso && <p className={estilos.aviso}>{aviso}</p>}
    </dl>
  );
}
