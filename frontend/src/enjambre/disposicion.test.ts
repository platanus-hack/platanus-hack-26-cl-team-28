import { describe, expect, it } from 'vitest';
import { puntoEnBurbuja, radioDe, ubicarBurbujas } from './disposicion';

describe('ubicarBurbujas', () => {
  const pedidos = [
    { y: 100, r: 40 },
    { y: 110, r: 30 },
    { y: 115, r: 12 },
    { y: 400, r: 20 },
  ];
  const puestas = ubicarBurbujas(pedidos, 1, 500, 0, 800);
  it('ninguna se toca con otra', () => {
    for (let i = 0; i < puestas.length; i++) {
      for (let j = i + 1; j < puestas.length; j++) {
        const d = Math.hypot(puestas[i].x - puestas[j].x, puestas[i].y - puestas[j].y);
        expect(d).toBeGreaterThanOrEqual(puestas[i].r + puestas[j].r);
      }
    }
  });
  it('quedan del lado pedido y sin invadir el país', () => {
    for (const b of puestas) expect(b.x - b.r).toBeGreaterThanOrEqual(500 - 0.01);
    const izquierda = ubicarBurbujas(pedidos, -1, 500, 0, 800);
    for (const b of izquierda) expect(b.x + b.r).toBeLessThanOrEqual(500.01);
  });
  it('reserva espacio para que etiquetas y grupos no se superpongan', () => {
    const ubicadas = ubicarBurbujas([{ y: 100, r: 20, anchoTexto: 100, altoTexto: 16 }, { y: 100, r: 15, anchoTexto: 90, altoTexto: 16 }], 1, 100, 0, 400);
    const [a, b] = ubicadas;
    const separadas = a.x + a.r + 100 <= b.x - b.r || b.x + b.r + 90 <= a.x - a.r || Math.abs(a.y - b.y) >= a.r + b.r;
    expect(separadas).toBe(true);
  });
  it('una burbuja sola queda pegada al borde y a su altura', () => {
    expect(puestas[3]).toMatchObject({ x: 520, y: 400 });
  });
});

describe('burbuja', () => {
  it('todos sus puntos caben dentro de su radio', () => {
    const r = radioDe(500, 3);
    for (let k = 0; k < 500; k++) {
      const [x, y] = puntoEnBurbuja(k, 3);
      expect(Math.hypot(x, y)).toBeLessThanOrEqual(r);
    }
  });
  it('sin puntos no tiene radio', () => {
    expect(radioDe(0, 3)).toBe(0);
  });
});
