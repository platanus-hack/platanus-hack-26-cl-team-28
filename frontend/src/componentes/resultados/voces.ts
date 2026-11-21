import type { Corrida } from '../../estado/corrida';
import { POSTURAS } from '../../dominio/tipos';

/**
 * Elige una voz por postura para la variante activa. `vuelta` rota entre las personas
 * más firmes de cada postura, así "Otras voces" trae gente distinta.
 */
export function elegirVoces(corrida: Corrida, caso: number, vuelta: number): number[] {
  const respuestas = corrida.resultados[caso].respuestas;
  const voces: number[] = [];
  for (const postura of POSTURAS) {
    const candidatas = respuestas
      .map((respuesta, k) => ({ k, respuesta }))
      .filter(({ respuesta }) => respuesta.postura === postura)
      .sort((a, b) => b.respuesta.firmeza - a.respuesta.firmeza)
      .slice(0, 12);
    if (candidatas.length) voces.push(candidatas[vuelta % candidatas.length].k);
  }
  return voces;
}
