/**
 * Las cuentas de la hoja inferior, sin DOM: a qué altura queda cada tope y a cuál se va al soltarla.
 * La hoja se mide por lo que asoma desde el borde de abajo de la pantalla.
 */

export type Tope = 'asomo' | 'mitad' | 'completa';
export const TOPES: readonly Tope[] = ['asomo', 'mitad', 'completa'];

export interface Alturas {
  asomo: number;
  mitad: number;
  completa: number;
}

/** Lo que tiene que quedar a la vista del mapa con la hoja a media altura, además del asomo. */
const MINIMO_SOBRE_ASOMO = 120;
/** Aire entre la hoja completa y la barra de arriba. */
const AIRE_ARRIBA = 8;
/** Velocidad desde la que soltar la hoja es un golpe: avanza un tope en esa dirección, sin importar dónde quedó. */
export const VELOCIDAD_GOLPE = 0.5;
/** Cuánto se proyecta el movimiento al soltar, en milisegundos: un arrastre con impulso llega más lejos. */
const PROYECCION_MS = 180;

/** Las tres alturas, siempre en orden: asomo ≤ mitad ≤ completa. */
export function alturas({ asomo, ventana, barra }: { asomo: number; ventana: number; barra: number }): Alturas {
  const completa = Math.max(asomo, Math.round(ventana - barra - AIRE_ARRIBA));
  const mitad = Math.min(completa, Math.max(asomo + MINIMO_SOBRE_ASOMO, Math.round(ventana * 0.5)));
  return { asomo, mitad, completa };
}

/**
 * El tope donde queda la hoja al soltarla. `visible` es cuánto asoma en ese momento y `velocidad`
 * cuánto crecía, en píxeles por milisegundo (positiva hacia arriba).
 */
export function elegirTope(a: Alturas, visible: number, velocidad: number): Tope {
  if (velocidad >= VELOCIDAD_GOLPE) return TOPES.find((tope) => a[tope] > visible + 1) ?? 'completa';
  if (velocidad <= -VELOCIDAD_GOLPE) return [...TOPES].reverse().find((tope) => a[tope] < visible - 1) ?? 'asomo';
  const destino = visible + velocidad * PROYECCION_MS;
  let mejor: Tope = 'asomo';
  for (const tope of TOPES) if (Math.abs(a[tope] - destino) < Math.abs(a[mejor] - destino)) mejor = tope;
  return mejor;
}

/** El tope siguiente hacia arriba (+1) o hacia abajo (-1), sin pasarse de los extremos. */
export function vecino(tope: Tope, direccion: 1 | -1): Tope {
  const i = TOPES.indexOf(tope) + direccion;
  return TOPES[Math.max(0, Math.min(TOPES.length - 1, i))];
}

/** Lo que asoma mientras se arrastra: no baja del asomo ni sube más allá de la hoja completa. */
export function acotar(a: Alturas, visible: number): number {
  return Math.max(a.asomo, Math.min(a.completa, visible));
}
