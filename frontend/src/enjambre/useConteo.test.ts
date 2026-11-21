import { describe, expect, it } from 'vitest';
import { valorInterpolado } from './useConteo';

describe('valorInterpolado', () => {
  it('no retrocede cuando un fotograma tiene una marca anterior al inicio', () => {
    expect(valorInterpolado(0, 20, -16)).toBe(0);
    expect(valorInterpolado(10, 20, -16)).toBe(10);
  });

  it('avanza sin salirse de los extremos y termina en el destino', () => {
    const valores = [-10, 0, 100, 500, 1100, 2000].map((tiempo) => valorInterpolado(5, 20, tiempo));
    expect(valores).toEqual([...valores].sort((a, b) => a - b));
    expect(valores[0]).toBe(5);
    expect(valores.at(-1)).toBe(20);
  });

  it('también interpola correctamente al disminuir un porcentaje', () => {
    expect(valorInterpolado(80, 20, -1)).toBe(80);
    expect(valorInterpolado(80, 20, 2000)).toBe(20);
  });
});
