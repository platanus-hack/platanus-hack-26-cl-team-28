import { useEffect, useState } from 'react';
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
  /** En la versión del agente: frases reales de quienes no apoyaron la A, que rotan mientras se espera. */
  objeciones?: string[];
}

const ROTACION = 1800;

/** Una objeción real a la vez, para que la espera cuente qué leyó el agente. */
function useRotacion(frases: string[] | undefined): string | undefined {
  const [k, setK] = useState(0);
  useEffect(() => {
    if (!frases?.length) return;
    const tic = window.setInterval(() => setK((n) => n + 1), ROTACION);
    return () => window.clearInterval(tic);
  }, [frases]);
  return frases?.length ? frases[k % frases.length] : undefined;
}

export function nombreModelo(modelo: string): string {
  return modelo.replace(/^claude-/, 'Claude ').replace(/-/g, ' ').replace(/\b(haiku|sonnet|opus)\b/, (m) => m[0].toUpperCase() + m.slice(1));
}

export function dinero(usd: number): string {
  return `US$ ${usd < 0.01 && usd > 0 ? '0,01' : usd.toFixed(2).replace('.', ',')}`;
}

/** Mientras los agentes corren: cuántos ya respondieron y lo que costó, medido por el motor. */
export function BloqueAvance({ caso, total, metricas, motor, objeciones }: Props) {
  const objecion = useRotacion(caso.respondidas === 0 ? objeciones : undefined);
  const contado = useConteo(caso.respondidas);
  const esperando = caso.respondidas === 0;
  return (
    <section className={estilos.bloque} aria-live="off">
      <p className={estilos.etiqueta}>{caso.iteracion ? `Preguntando la versión del agente` : `Preguntando la variante ${caso.letra}`}</p>
      <p className={estilos.cifra}>{formatear(Math.round(contado))}</p>
      <p className={estilos.nombre}>
        de {formatear(total)} agentes {esperando ? 'leyendo la propuesta' : 'ya respondieron'}
      </p>
      <progress className={estilos.barra} max={total} value={caso.respondidas} aria-label="Avance de la simulación" />
      {motor && !motor.grabado && caso.respondidas === 0 && !caso.iteracion && (
        <p className={estilos.detalle}>Cada agente lee la propuesta y su perfil del censo antes de responder</p>
      )}
      {caso.iteracion && caso.respondidas === 0 && (
        <p className={estilos.cambio}>
          <span>Qué cambió el agente</span>
          {caso.iteracion.cambio}
        </p>
      )}
      {objecion && (
        <p className={estilos.objecion} key={objecion}>
          <span>Lo que leyó el agente</span>
          {objecion}
        </p>
      )}
      {motor && !motor.grabado && caso.desdeCache > 0 && caso.desdeCache === caso.respondidas && (
        <p className={estilos.detalle}>Esta pregunta ya se hizo hoy: se muestran las respuestas que dieron los agentes en esa corrida</p>
      )}
      {motor && !motor.grabado && caso.desdeCache < caso.respondidas && (
        <p className={estilos.detalle}>
          {formatear(metricas.llamadas)} {metricas.llamadas === 1 ? 'llamada' : 'llamadas'} a {nombreModelo(motor.modelo)} · {formatear(Math.round(metricas.segundos))} s ·{' '}
          {dinero(metricas.costo_usd)}
        </p>
      )}
      {(!motor || motor.grabado) && <p className={estilos.detalle}>Demostración: sin motor conectado</p>}
    </section>
  );
}
