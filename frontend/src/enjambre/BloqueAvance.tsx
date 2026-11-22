import { formatear } from '../dominio/textos';
import type { Metricas, MotorInfo } from '../vivo/api';
import type { CasoVivo } from '../vivo/useEnVivo';
import estilos from './BloqueAvance.module.css';
import { FiguraWati } from './FiguraWati';
import { useConteo } from './useConteo';
import { rasgosDe } from './wati';

interface Props {
  caso: CasoVivo;
  total: number;
  metricas: Metricas;
  motor: MotorInfo | null;
}

const RASGOS_ESPERA = rasgosDe('contactando-entrevistados');

export function nombreModelo(modelo: string): string {
  return modelo.replace(/^claude-/, 'Claude ').replace(/-/g, ' ').replace(/\b(haiku|sonnet|opus)\b/, (m) => m[0].toUpperCase() + m.slice(1));
}

export function dinero(usd: number): string {
  return `US$ ${usd < 0.01 && usd > 0 ? '0,01' : usd.toFixed(2).replace('.', ',')}`;
}

/** Mientras los agentes corren: cuántos ya respondieron y lo que costó, medido por el motor. */
export function BloqueAvance({ caso, total, metricas, motor }: Props) {
  const contado = useConteo(caso.respondidas);
  const esperando = caso.respondidas === 0;
  const mostrado = Math.max(1, Math.round(contado));
  return (
    <section className={estilos.bloque} aria-live="off">
      {esperando ? (
        <div className={estilos.espera} role="status">
          <FiguraWati estado="neutra" rasgos={RASGOS_ESPERA} alto={48} />
          <div>
            <p>Contactando a los entrevistados…</p>
            <p>Preparando la consulta para {formatear(total)} agentes.</p>
          </div>
          <div className={estilos.barra} data-esperando aria-hidden="true" />
        </div>
      ) : (
        <>
          <p className={estilos.cifra}>{formatear(mostrado)}</p>
          <p className={estilos.nombre}>de {formatear(total)} agentes ya respondieron</p>
          <progress className={estilos.barra} max={total} value={mostrado} aria-label="Avance de la simulación" />
        </>
      )}
      {motor && !motor.grabado && caso.desdeCache > 0 && caso.desdeCache === caso.respondidas && (
        <p className={estilos.detalle}>Esta pregunta ya se hizo hoy: se muestran las respuestas que dieron los agentes en esa corrida</p>
      )}
      {motor && !motor.grabado && caso.desdeCache < caso.respondidas && (
        <p className={estilos.detalle}>
          {formatear(metricas.llamadas)} {metricas.llamadas === 1 ? 'llamada' : 'llamadas'} al modelo · {formatear(Math.round(metricas.segundos))} s ·{' '}
          {dinero(metricas.costo_usd)}
        </p>
      )}
      {(!motor || motor.grabado) && <p className={estilos.detalle}>Demostración: sin motor conectado</p>}
    </section>
  );
}
