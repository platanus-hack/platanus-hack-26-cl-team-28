import { formatear } from '../dominio/textos';
import estilos from './BloqueAvance.module.css';

interface Props {
  respondidas: number;
  total: number;
  /** Personas que representa cada punto. */
  porPunto: number;
}

/** Mientras los agentes corren: cuántas personas simuladas ya respondieron. */
export function BloqueAvance({ respondidas, total, porPunto }: Props) {
  const personas = Math.min(total, Math.round(respondidas * porPunto));
  return (
    <section className={estilos.bloque} aria-live="off">
      <p className={estilos.cifra}>{formatear(personas)}</p>
      <p className={estilos.nombre}>de {formatear(total)} personas simuladas ya respondieron</p>
      <p className={estilos.detalle}>Cada punto se enciende cuando su agente termina.</p>
      <progress className={estilos.barra} max={total} value={personas} aria-label="Avance de la simulación" />
    </section>
  );
}
