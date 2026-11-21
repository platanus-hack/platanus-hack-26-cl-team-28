import { useEffect, useMemo, useRef } from 'react';
import { formatear } from '../dominio/textos';
import type { Conexion, EnVivo } from '../vivo/useEnVivo';
import { EscenaProceso, type DatosProceso } from './EscenaProceso';
import estilos from './VistaProceso.module.css';

interface Props {
  sim: EnVivo;
  conexion: Conexion;
  /** Falso mientras se cierra: los cuadrados vuelven al mapa y recién entonces se desmonta. */
  abierta: boolean;
  claro: boolean;
  /** Dónde está dibujado el agente en el mapa, para que su cuadrado salga de ahí. */
  origen(agente: number): [number, number] | null;
  alElegir(agente: number, x: number, y: number): void;
  alCerrado(): void;
}

/** Nombre corto de cada pregunta de la encuesta, en el orden de las notas. */
const CORTAS = ['Está de acuerdo', 'Quedaría satisfecha', 'Le parece justa', 'Confía en el Estado', 'La cumpliría', 'Cree que funcionará'];
const GENERO = ['Mujer', 'Hombre'];

/**
 * El proceso completo de la corrida en lugar del mapa: población, lotes, respuestas, postura e
 * iteración. La misma gente del mapa, ordenada por lo que le pasó.
 */
export function VistaProceso({ sim, conexion, abierta, claro, origen, alElegir, alCerrado }: Props) {
  const lienzo = useRef<HTMLCanvasElement>(null);
  const escena = useRef<EscenaProceso | null>(null);
  const { casos, viendo, muestra, version, metricas } = sim;
  const caso = casos[viendo];
  const siguiente = casos[viendo + 1];

  const acciones = useRef({ origen, alElegir, alCerrado });
  acciones.current = { origen, alElegir, alCerrado };

  useEffect(() => {
    const nueva = new EscenaProceso(lienzo.current!, (agente) => acciones.current.origen(agente));
    nueva.alElegir = (agente, x, y) => acciones.current.alElegir(agente, x, y);
    nueva.montar();
    escena.current = nueva;
    return () => {
      nueva.destruir();
      escena.current = null;
    };
  }, []);

  useEffect(() => {
    if (abierta) escena.current?.abrir();
    else escena.current?.cerrar(() => acciones.current.alCerrado());
  }, [abierta]);

  useEffect(() => escena.current?.actualizarTema(), [claro]);

  const embudo = useMemo(() => {
    const poblacion = conexion.estado?.poblacion;
    return [
      { valor: poblacion?.personas ?? 0, rotulo: 'personas de 14 años o más' },
      { valor: poblacion?.agentes ?? 0, rotulo: 'personas simuladas disponibles' },
      { valor: conexion.muestra?.disponibles ?? 0, rotulo: 'cumplen los filtros' },
      { valor: sim.totalCorrida, rotulo: sim.filtrada ? `sorteados, ${formatear(muestra.total)} a la vista` : 'sorteados' },
    ];
  }, [conexion, sim.totalCorrida, sim.filtrada, muestra.total]);

  useEffect(() => {
    if (!caso) return;
    const estado = conexion.estado;
    const izquierda = [
      estado ? `${estado.motor.nombre} · ${estado.motor.modelo}` : 'Demostración sin motor',
      metricas.llamadas ? `${formatear(metricas.llamadas)} llamadas` : '',
      metricas.tokens ? `${(metricas.tokens / 1e6).toLocaleString('es-CL', { maximumFractionDigits: 1 })} M de tokens` : '',
    ];
    const derecha = [metricas.segundos ? `${Math.round(metricas.segundos)} s` : '', estado ? `grupos de ${estado.lote} personas, hasta ${estado.concurrencia} grupos a la vez` : ''];
    const unir = (partes: string[]) => partes.filter(Boolean).join('  ·  ');
    const datos: DatosProceso = {
      agentes: muestra.agentes,
      acuerdo: caso.acuerdo,
      notas: caso.notas,
      lote: caso.lote,
      frase: caso.frase,
      siguiente: siguiente && siguiente.respondidas > 0 ? { letra: siguiente.letra, acuerdo: siguiente.acuerdo } : null,
      redactando: sim.redactando !== null && viendo === casos.length - 1,
      embudo,
      ejes: CORTAS,
      pie: [unir(izquierda), unir(derecha)],
      tamLote: estado?.lote ?? 20,
      deCache: caso.desdeCache,
      describir: (i) => {
        const agente = conexion.agentes[i];
        return agente ? `${GENERO[agente.genero] ?? 'Persona'}, ${agente.edad} años, ${agente.comuna}` : '';
      },
    };
    escena.current?.fijar(datos);
    // `version` cambia con cada respuesta que llega.
  }, [caso, siguiente, muestra, version, metricas, embudo, conexion, sim.redactando, viendo, casos.length]);

  return (
    <div className={estilos.vista} data-abierta={abierta || undefined}>
      <canvas
        ref={lienzo}
        className={estilos.lienzo}
        role="img"
        aria-label="El proceso de la simulación: de la población a la muestra, los lotes que respondió el modelo, las respuestas de cada persona y su postura."
      />
      {caso && (
        <header className={estilos.cabeza}>
          <div className={estilos.variantes} role="group" aria-label="Variante">
            {casos.map((otro, k) => (
              <button key={otro.id} type="button" aria-pressed={k === viendo} onClick={() => sim.setViendo(k)}>
                {otro.letra}
              </button>
            ))}
          </div>
          <p className={estilos.titulo}>{caso.titulo}</p>
        </header>
      )}
    </div>
  );
}
