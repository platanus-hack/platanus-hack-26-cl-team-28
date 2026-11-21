import { resumirCaso, type ResumenCaso } from '../dominio/metricas';
import { calcularMuestra, personasPorFigura } from '../dominio/muestra';
import type { Simulador } from '../dominio/simulador';
import type { Caso, Filtros, Muestra, Persona, ResultadoCaso } from '../dominio/tipos';
import { ESTADO } from '../mapa/personajes';

/** Una simulación ya respondida: los casos, a quiénes se preguntó y qué dijeron. */
export interface Corrida {
  casos: Caso[];
  muestra: Muestra;
  personas: Persona[];
  resultados: ResultadoCaso[];
  resumenes: ResumenCaso[];
}

export async function correr(simulador: Simulador, casos: Caso[], todas: Persona[], filtros: Filtros): Promise<Corrida> {
  const muestra = calcularMuestra(todas, filtros);
  const personas = muestra.indices.map((indice) => todas[indice]);
  const resultados = await simulador.simular(casos, personas);
  if (resultados.length !== casos.length) throw new Error('El simulador debe responder todos los casos');
  const resumenes = resultados.map((resultado) => resumirCaso(personas, resultado.respuestas));
  return { casos, muestra, personas, resultados, resumenes };
}

/** Personas de la muestra cuya postura es distinta entre dos variantes. */
export function cambianDePostura(corrida: Corrida, desde: number, hasta: number): number {
  const a = corrida.resultados[desde].respuestas;
  const b = corrida.resultados[hasta].respuestas;
  const figuras = a.filter((respuesta, k) => respuesta.postura !== b[k].postura).length;
  return Math.round(figuras * personasPorFigura(corrida.muestra));
}

/** Estado de dibujo de cada figura del mapa mientras se prepara la muestra. */
export function estadosDeMuestra(muestra: Muestra, cantidad: number): Uint8Array {
  const estados = new Uint8Array(cantidad).fill(ESTADO.fantasma);
  for (const indice of muestra.indices) estados[indice] = ESTADO.neutra;
  return estados;
}

/** Estado de dibujo de cada figura según lo que respondió en un caso. */
export function estadosDeCaso(corrida: Corrida, caso: number, cantidad: number): Uint8Array {
  const estados = new Uint8Array(cantidad).fill(ESTADO.fantasma);
  corrida.resultados[caso].respuestas.forEach((respuesta, k) => {
    estados[corrida.muestra.indices[k]] = ESTADO[respuesta.postura];
  });
  return estados;
}
