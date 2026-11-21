import { describe, expect, it } from 'vitest';
import { repartirPorRegion } from './muestra';

describe('repartirPorRegion', () => {
  it('reparte en proporción a las personas que representa cada región', () => {
    expect(repartirPorRegion(10, [50, 50], [100, 100])).toEqual([5, 5]);
    expect(repartirPorRegion(10, [70, 20, 10], [100, 100, 100])).toEqual([7, 2, 1]);
  });

  it('da lo que sobra a los restos mayores y suma exacto', () => {
    const cuotas = repartirPorRegion(7, [1, 1, 1], [9, 9, 9]);
    expect(cuotas.reduce((s, c) => s + c, 0)).toBe(7);
    expect(Math.max(...cuotas) - Math.min(...cuotas)).toBeLessThanOrEqual(1);
  });

  it('no pasa de los disponibles y reparte lo que no cabe entre las demás', () => {
    expect(repartirPorRegion(10, [90, 10], [2, 100])).toEqual([2, 8]);
    expect(repartirPorRegion(10, [1, 1], [3, 4])).toEqual([3, 4]);
  });

  it('una región que pesa muy poco puede quedar sin nadie', () => {
    expect(repartirPorRegion(10, [995, 5], [1000, 1000])).toEqual([10, 0]);
  });

  it('sin disponibles no reparte', () => {
    expect(repartirPorRegion(5, [1, 1], [0, 0])).toEqual([0, 0]);
  });
});
