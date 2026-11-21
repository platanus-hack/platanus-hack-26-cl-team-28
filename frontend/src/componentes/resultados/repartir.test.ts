import { describe, expect, it } from 'vitest';
import { repartir } from './repartir';

describe('repartir', () => {
  it('no mueve etiquetas que ya están separadas', () => {
    expect(repartir([100, 300, 500], 60, 0, 1000)).toEqual([100, 300, 500]);
  });
  it('separa las que chocan y conserva el orden', () => {
    const r = repartir([500, 510, 520, 900], 60, 0, 1000);
    expect(r[1] - r[0]).toBeGreaterThanOrEqual(59.9);
    expect(r[2] - r[1]).toBeGreaterThanOrEqual(59.9);
    expect(r[3]).toBe(900);
  });
  it('respeta los bordes', () => {
    const r = repartir([5, 10, 990, 995], 60, 30, 970);
    expect(Math.min(...r)).toBeGreaterThanOrEqual(30);
    expect(Math.max(...r)).toBeLessThanOrEqual(970.01);
  });
  it('devuelve en el orden de entrada', () => {
    const r = repartir([800, 100], 60, 0, 1000);
    expect(r).toEqual([800, 100]);
  });
});
