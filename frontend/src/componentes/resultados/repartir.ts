/**
 * Separa etiquetas sobre un eje: cada una queda lo más cerca posible de su posición real,
 * sin acercarse a la vecina más que `separacion` ni salirse de [minimo, maximo].
 * Devuelve las posiciones en el mismo orden de entrada.
 */
export function repartir(reales: number[], separacion: number, minimo: number, maximo: number): number[] {
  const orden = reales.map((x, i) => ({ x, i })).sort((a, b) => a.x - b.x);
  const puestas = orden.map((o) => Math.max(minimo, o.x));
  for (let pasada = 0; pasada < 40; pasada++) {
    let movio = false;
    for (let k = 1; k < puestas.length; k++) {
      const falta = separacion - (puestas[k] - puestas[k - 1]);
      if (falta <= 0.01) continue;
      puestas[k - 1] -= falta / 2;
      puestas[k] += falta / 2;
      movio = true;
    }
    puestas[0] = Math.max(minimo, puestas[0]);
    const ultimo = puestas.length - 1;
    puestas[ultimo] = Math.min(maximo, puestas[ultimo]);
    for (let k = 1; k < puestas.length; k++) puestas[k] = Math.max(puestas[k], puestas[k - 1] + (pasada === 39 ? separacion : 0));
    if (!movio) break;
  }
  const salida = new Array<number>(reales.length);
  orden.forEach((o, k) => (salida[o.i] = puestas[k]));
  return salida;
}
