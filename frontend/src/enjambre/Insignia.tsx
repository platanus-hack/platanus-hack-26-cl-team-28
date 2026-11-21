import { formatear } from '../dominio/textos';
import type { Conexion } from '../vivo/useEnVivo';
import { nombreModelo } from './BloqueAvance';
import estilos from './Insignia.module.css';

/** Qué está respondiendo: el motor en vivo con su modelo, o la demostración sin motor. */
export function Insignia({ conexion, agentes }: { conexion: Conexion | null; agentes: number }) {
  if (!conexion) return null;
  const motor = conexion.estado?.motor;
  if (conexion.demo || !motor) {
    return (
      <p className={estilos.insignia} data-demo>
        <i aria-hidden="true" />
        Demostración sin motor
      </p>
    );
  }
  const modelo = nombreModelo(motor.modelo);
  return (
    <p className={estilos.insignia} data-grabado={motor.grabado || undefined}>
      <i aria-hidden="true" />
      <span>
        <b>{motor.grabado ? 'Corrida grabada' : 'En vivo'}</b> · {modelo}
      </span>
      <span className={estilos.detalle}>{formatear(agentes)} personas reales del Censo 2024, cada una con su agente</span>
    </p>
  );
}
