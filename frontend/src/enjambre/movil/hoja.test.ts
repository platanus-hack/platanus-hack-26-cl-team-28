import { describe, expect, it } from 'vitest';
import { acotar, alturas, elegirTope, vecino } from './hoja';

const telefono = alturas({ asomo: 150, ventana: 740, barra: 64 });

describe('alturas', () => {
  it('quedan en orden en un teléfono', () => {
    expect(telefono.asomo).toBeLessThan(telefono.mitad);
    expect(telefono.mitad).toBeLessThan(telefono.completa);
    expect(telefono.completa).toBe(740 - 64 - 8);
  });

  it('nunca se cruzan, aunque la ventana sea muy baja o el asomo muy alto', () => {
    for (const [asomo, ventana] of [[150, 200], [400, 500], [0, 300], [300, 300]]) {
      const a = alturas({ asomo, ventana, barra: 64 });
      expect(a.asomo).toBeLessThanOrEqual(a.mitad);
      expect(a.mitad).toBeLessThanOrEqual(a.completa);
    }
  });
});

describe('elegirTope', () => {
  it('un arrastre corto y lento vuelve a su tope', () => {
    expect(elegirTope(telefono, telefono.asomo + 30, 0.05)).toBe('asomo');
    expect(elegirTope(telefono, telefono.mitad - 30, -0.05)).toBe('mitad');
  });

  it('un golpe rápido avanza un solo tope en su dirección', () => {
    expect(elegirTope(telefono, telefono.asomo + 10, 1.2)).toBe('mitad');
    expect(elegirTope(telefono, telefono.mitad + 10, 1.2)).toBe('completa');
    expect(elegirTope(telefono, telefono.completa - 10, -1.2)).toBe('mitad');
    expect(elegirTope(telefono, telefono.mitad - 10, -1.2)).toBe('asomo');
  });

  it('en los extremos el golpe no se sale', () => {
    expect(elegirTope(telefono, telefono.completa, 2)).toBe('completa');
    expect(elegirTope(telefono, telefono.asomo, -2)).toBe('asomo');
  });

  it('soltada a medio camino, gana el tope más cercano', () => {
    expect(elegirTope(telefono, telefono.mitad + 20, 0)).toBe('mitad');
    expect(elegirTope(telefono, telefono.completa - 20, 0)).toBe('completa');
  });
});

describe('vecino y acotar', () => {
  it('no se pasan de los extremos', () => {
    expect(vecino('asomo', -1)).toBe('asomo');
    expect(vecino('asomo', 1)).toBe('mitad');
    expect(vecino('completa', 1)).toBe('completa');
    expect(acotar(telefono, 0)).toBe(telefono.asomo);
    expect(acotar(telefono, 5000)).toBe(telefono.completa);
  });
});
