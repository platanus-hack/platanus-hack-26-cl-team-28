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

/**
 * Cuántos van de cada región: `tamano` repartido en proporción a `pesos` (las personas que
 * representa cada región) por el método del resto mayor. Ninguna región recibe más de sus
 * `disponibles`; lo que no cabe en una se reparte entre las demás. Sin mínimo por región: la que
 * pesa menos de media persona de la muestra puede quedar en 0, que es lo proporcional. Lo usa la
 * demo, cuyos agentes no traen comuna ni zona; el motor reparte además por comuna y zona
 * (`repartir` en backend/servidor/poblacion.py).
 */
export function repartirPorRegion(tamano: number, pesos: number[], disponibles: number[]): number[] {
  const cuotas = pesos.map(() => 0);
  const meta = Math.min(Math.max(0, Math.floor(tamano)), disponibles.reduce((s, d) => s + d, 0));
  let abiertas = disponibles.map((_, r) => r).filter((r) => disponibles[r] > 0);
  let falta = meta;
  while (falta > 0 && abiertas.length) {
    const peso = abiertas.reduce((s, r) => s + Math.max(0, pesos[r]), 0);
    const medida = (r: number) => (peso > 0 ? Math.max(0, pesos[r]) : disponibles[r]);
    const total = peso > 0 ? peso : abiertas.reduce((s, r) => s + disponibles[r], 0);
    const ideal = new Map(abiertas.map((r) => [r, (falta * medida(r)) / total]));
    const extra = new Map(abiertas.map((r) => [r, Math.floor(ideal.get(r)!)]));
    const sobran = falta - [...extra.values()].reduce((s, e) => s + e, 0);
    [...abiertas]
      .sort((a, b) => ideal.get(b)! - extra.get(b)! - (ideal.get(a)! - extra.get(a)!) || a - b)
      .slice(0, sobran)
      .forEach((r) => extra.set(r, extra.get(r)! + 1));
    const topadas = new Set<number>();
    for (const r of abiertas) {
      const cabe = disponibles[r] - cuotas[r];
      cuotas[r] += Math.min(extra.get(r)!, cabe);
      if (extra.get(r)! >= cabe) topadas.add(r);
    }
    falta = meta - cuotas.reduce((s, c) => s + c, 0);
    abiertas = abiertas.filter((r) => !topadas.has(r));
  }
  return cuotas;
}

export function personasPorFigura(muestra: Muestra): number {
  return muestra.indices.length ? muestra.total / muestra.indices.length : 0;
}
