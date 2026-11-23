import type { Borrador } from '../estado/useBorradores';
import type { Orientacion } from '../vivo/api';

/** Las propuestas conservadas mantienen su documento y referencia; las separadas nunca los heredan. */
export function separarPropuestas(borradores: Borrador[], orientaciones: Orientacion[]): Borrador[] {
  let id = Math.max(0, ...borradores.map((b) => b.id)) + 1;
  return borradores.flatMap((b, k) => orientaciones[k].tipo === 'comparacion' && !b.leido
    ? orientaciones[k].propuestas.map((texto) => ({ id: id++, texto }))
    : [b]);
}
