import { describe, expect, it } from 'vitest';
import { agrupar } from './agrupar';

const entrada = (puntos: [number, number][], s: number) => ({
  x: Float32Array.from(puntos, (p) => p[0]),
  y: Float32Array.from(puntos, (p) => p[1]),
  prioridad: puntos.map((_, i) => i),
  sx: s,
  sy: s,
});

describe('agrupar', () => {
  const ciudad: [number, number][] = [[0, 0], [0.1, 0], [0, 0.1], [0.1, 0.1], [0.05, 0.05]];
  const pueblo: [number, number][] = [[10, 0]];
  it('de lejos funde la ciudad en una figura y deja al pueblo aparte', () => {
    const { grupo, cuenta } = agrupar(entrada([...ciudad, ...pueblo], 1));
    expect(cuenta[0]).toBe(5);
    expect(cuenta[5]).toBe(1);
    expect([...grupo.slice(0, 5)]).toEqual([0, 0, 0, 0, 0]);
  });
  it('de cerca cada figura se representa a sí misma', () => {
    const { cuenta } = agrupar(entrada([...ciudad, ...pueblo], 0.02));
    expect([...cuenta]).toEqual([1, 1, 1, 1, 1, 1]);
  });
  it('toda figura queda en un grupo y las cuentas suman el total', () => {
    const { grupo, cuenta } = agrupar(entrada([...ciudad, ...pueblo], 0.08));
    expect([...grupo].every((g) => g >= 0 && cuenta[g] > 0)).toBe(true);
    expect([...cuenta].reduce((a, b) => a + b, 0)).toBe(6);
  });
});
