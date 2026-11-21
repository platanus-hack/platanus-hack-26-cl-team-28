import { useCallback, useEffect, useMemo, useState } from 'react';
import { MINIMO_CASOS } from '../dominio/catalogos';
import { calcularMuestra, FILTROS_INICIALES } from '../dominio/muestra';
import { simuladorDemostracion } from '../dominio/simulador';
import { letraDe } from '../dominio/textos';
import type { Caso, Filtros, Persona } from '../dominio/tipos';
import { correr, type Corrida } from './corrida';
import { useBorradores } from './useBorradores';

export type Fase = 'preparar' | 'preguntando' | 'resultados';

/** Segundos que tarda la pregunta en recorrer el país, y pausa antes del caso siguiente. */
export const DURACION_BARRIDO = 2.6;
const PAUSA = 0.8;

const simulador = simuladorDemostracion;

/** Estado de la herramienta: lo que se pregunta, a quiénes, y la corrida ya respondida. */
export function useSimulacion(personas: Persona[]) {
  const edicion = useBorradores();
  const { borradores } = edicion;
  const [filtros, setFiltros] = useState<Filtros>(FILTROS_INICIALES);
  const [fase, setFase] = useState<Fase>('preparar');
  const [corrida, setCorrida] = useState<Corrida | null>(null);
  const [activo, setActivo] = useState(0);
  const [anterior, setAnterior] = useState(0);
  const [enBarrido, setEnBarrido] = useState(0);

  const muestra = useMemo(() => calcularMuestra(personas, filtros), [personas, filtros]);
  const completos = borradores.filter((borrador) => borrador.texto.trim());
  const puedePreguntar = completos.length >= MINIMO_CASOS && muestra.total > 0;

  const preguntar = useCallback(async () => {
    if (!puedePreguntar) return;
    const casos: Caso[] = completos.map((b, i) => ({ id: String(b.id), letra: letraDe(i), texto: b.texto.trim() }));
    setCorrida(await correr(simulador, casos, personas, filtros));
    setEnBarrido(0);
    setActivo(0);
    setAnterior(0);
    setFase('preguntando');
  }, [completos, filtros, personas, puedePreguntar]);

  // El barrido recorre un caso a la vez y al terminar el último pasa a los resultados.
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
    fase,
    corrida,
    activo,
    enBarrido,
    muestra,
    puedePreguntar,
    faltanCasos: completos.length < MINIMO_CASOS,
    setFiltros,
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
