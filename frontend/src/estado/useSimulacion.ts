import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { MAXIMO_CASOS, MINIMO_CASOS } from '../dominio/catalogos';
import { calcularMuestra, FILTROS_INICIALES } from '../dominio/muestra';
import { crearSimuladorDemostracion } from '../dominio/simulador';
import { letraDe } from '../dominio/textos';
import type { Caso, Filtros, Persona } from '../dominio/tipos';
import { ESTADO } from '../mapa/personajes';
import { correr, type Corrida } from './corrida';
import { useBorradores } from './useBorradores';

/**
 * `simulando`: los agentes corren y sus respuestas van llegando. `preguntando`: ya llegaron
 * todas y la interfaz recorre las variantes una a una. `resultados`: se exploran a mano.
 */
export type Fase = 'preparar' | 'simulando' | 'preguntando' | 'resultados';

/** Segundos que se muestra cada variante en el recorrido, y pausa antes de la siguiente. */
export const DURACION_BARRIDO = 2.6;
const PAUSA = 0.8;
const REFRESCO_LLEGADAS = 90;

interface Opciones {
  /** Con cuántas variantes escritas se puede preguntar. */
  minimoCasos?: number;
  /** Milisegundos que la demostración tarda en entregar las respuestas (cero: de inmediato). */
  duracionDemo?: number;
}

/** Estado de la herramienta: lo que se pregunta, a quiénes, y la corrida ya respondida. */
export function useSimulacion(personas: Persona[], { minimoCasos = MINIMO_CASOS, duracionDemo = 0 }: Opciones = {}) {
  const simulador = useMemo(() => crearSimuladorDemostracion(duracionDemo), [duracionDemo]);
  const edicion = useBorradores();
  const { borradores } = edicion;
  const [filtros, setFiltros] = useState<Filtros>(FILTROS_INICIALES);
  const [iteraciones, setIteraciones] = useState(0);
  const [fase, setFase] = useState<Fase>('preparar');
  const [corrida, setCorrida] = useState<Corrida | null>(null);
  const [activo, setActivo] = useState(0);
  const [anterior, setAnterior] = useState(0);
  const [enBarrido, setEnBarrido] = useState(0);
  /** Estado de dibujo de cada persona a medida que su agente termina (cero: aún no responde). */
  const llegadas = useRef(new Uint8Array(personas.length));
  const [respondidas, setRespondidas] = useState(0);

  const muestra = useMemo(() => calcularMuestra(personas, filtros), [personas, filtros]);
  const completos = borradores.filter((borrador) => borrador.texto.trim() || borrador.documento);
  const puedePreguntar = completos.length >= minimoCasos && muestra.total > 0 && fase !== 'simulando';

  const preguntar = useCallback(async () => {
    if (!puedePreguntar) return;
    const escritos: Caso[] = completos.map((b, i) => ({ id: String(b.id), letra: letraDe(i), texto: b.texto.trim(), documento: b.documento }));
    const cupo = Math.min(iteraciones, MAXIMO_CASOS - escritos.length);
    const propuestas = cupo > 0 ? await simulador.proponerIteraciones(escritos[0], cupo) : [];
    const casos = [...escritos, ...propuestas.map((p, k) => ({ ...p, id: `iteracion-${k}`, letra: letraDe(escritos.length + k) }))];

    llegadas.current = new Uint8Array(personas.length);
    let contadas = 0;
    setRespondidas(0);
    setCorrida(null);
    setFase('simulando');
    // Las respuestas llegan de a muchas: la pantalla se refresca a intervalos, no una vez por agente.
    const refresco = window.setInterval(() => setRespondidas(contadas), REFRESCO_LLEGADAS);
    try {
      const nueva = await correr(simulador, casos, personas, filtros, ({ caso, persona, respuesta }) => {
        if (caso !== 0) return;
        llegadas.current[muestra.indices[persona]] = ESTADO[respuesta.postura];
        contadas += 1;
      });
      setCorrida(nueva);
      setEnBarrido(0);
      setActivo(0);
      setAnterior(0);
      setFase('preguntando');
    } catch (error) {
      setFase('preparar');
      throw error;
    } finally {
      window.clearInterval(refresco);
    }
  }, [completos, filtros, iteraciones, muestra, personas, puedePreguntar, simulador]);

  // El recorrido muestra una variante a la vez y al terminar la última pasa a los resultados.
  useEffect(() => {
    if (fase !== 'preguntando' || !corrida) return;
    const espera = window.setTimeout(() => {
      if (enBarrido + 1 < corrida.casos.length) setEnBarrido(enBarrido + 1);
      else setFase('resultados');
    }, (DURACION_BARRIDO + PAUSA) * 1000);
    return () => window.clearTimeout(espera);
  }, [fase, corrida, enBarrido]);

  return {
    simulador,
    ...edicion,
    filtros,
    iteraciones,
    fase,
    corrida,
    activo,
    enBarrido,
    muestra,
    llegadas,
    respondidas,
    puedePreguntar,
    faltanCasos: completos.length < minimoCasos,
    setFiltros,
    setIteraciones,
    anterior,
    setActivo: (indice: number) => {
      setAnterior(activo);
      setActivo(indice);
    },
    preguntar,
    verResultados: () => setFase('resultados'),
    editar: () => setFase('preparar'),
  };
}

export type Simulacion = ReturnType<typeof useSimulacion>;
