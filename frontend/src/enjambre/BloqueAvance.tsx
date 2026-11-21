import { formatear } from '../dominio/textos';
import type { Metricas, MotorInfo } from '../vivo/api';
import type { CasoVivo } from '../vivo/useEnVivo';
import estilos from './BloqueAvance.module.css';
import { useConteo } from './useConteo';

interface Props {
  caso: CasoVivo;
  total: number;
  metricas: Metricas;
  motor: MotorInfo | null;
}

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
  return (
    <section className={estilos.bloque} aria-live="off">
      <p className={estilos.cifra}>{formatear(Math.round(contado))}</p>
      <p className={estilos.nombre}>
        de {formatear(total)} agentes {esperando ? 'leyendo la propuesta' : 'ya respondieron'}
      </p>
      {esperando ? (
        // Los primeros segundos no hay respuestas todavía: la barra se mueve para que se vea que está trabajando.
        <div className={estilos.barra} data-esperando role="progressbar" aria-label="La IA está leyendo los primeros perfiles" />
      ) : (
        <progress className={estilos.barra} max={total} value={contado} aria-label="Avance de la simulación" />
      )}
      {esperando && motor && !motor.grabado && <p className={estilos.detalle}>La IA está leyendo los primeros perfiles</p>}
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
