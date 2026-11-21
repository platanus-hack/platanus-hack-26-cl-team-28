import { EDAD_MAXIMA, EDAD_MINIMA, TAMANOS, UNIVERSO } from './catalogos';
import type { Filtros, Muestra, Persona } from './tipos';

export const SIN_FILTRO = -1;

export const FILTROS_INICIALES: Filtros = {
  tamano: TAMANOS[0],
  region: SIN_FILTRO,
  edadMin: EDAD_MINIMA,
  edadMax: EDAD_MAXIMA,
  genero: SIN_FILTRO,
  quintil: SIN_FILTRO,
  educacion: SIN_FILTRO,
  politica: SIN_FILTRO,
  reduccion: 10,
};

function coincide(persona: Persona, filtros: Filtros): boolean {
  const pasa = (valor: number, filtro: number) => filtro === SIN_FILTRO || valor === filtro;
  return (
    pasa(persona.region, filtros.region) &&
    persona.edad >= filtros.edadMin &&
    (persona.edad <= filtros.edadMax || filtros.edadMax >= EDAD_MAXIMA) &&
    pasa(persona.genero, filtros.genero) &&
    pasa(persona.quintil, filtros.quintil) &&
    pasa(persona.educacion, filtros.educacion) &&
    pasa(persona.politica, filtros.politica)
  );
}

/**
 * Las figuras del mapa representan en partes iguales al universo de perfiles. La muestra
 * toma a quienes cumplen los filtros, hasta el tamaño pedido.
 */
export function calcularMuestra(personas: Persona[], filtros: Filtros): Muestra {
  const indices: number[] = [];
  personas.forEach((persona, indice) => {
    if (coincide(persona, filtros)) indices.push(indice);
  });
  const disponibles = personas.length ? Math.round((indices.length / personas.length) * UNIVERSO) : 0;
  return { indices, disponibles, pedidas: filtros.tamano, total: Math.min(filtros.tamano, disponibles) };
}

export function personasPorFigura(muestra: Muestra): number {
  return muestra.indices.length ? muestra.total / muestra.indices.length : 0;
}
