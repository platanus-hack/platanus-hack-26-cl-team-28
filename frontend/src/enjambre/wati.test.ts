import { describe, expect, it } from 'vitest';
import { rasgosDe, tonosDe, poseDe, TONOS, VARIANTES } from './wati';

describe('rasgosDe', () => {
  it('da siempre los mismos rasgos a la misma persona', () => {
    expect(rasgosDe('agente-17#2')).toEqual(rasgosDe('agente-17#2'));
  });
  it('reparte adornos y tonos entre todas las variantes', () => {
    const adornos = new Set<number>();
    const tonos = new Set<number>();
    for (let i = 0; i < 2000; i++) {
      const { variante, tono } = rasgosDe(`a${i}#0`);
      expect(variante).toBeGreaterThanOrEqual(0);
      expect(variante).toBeLessThan(VARIANTES);
      expect(tono).toBeLessThan(TONOS);
      adornos.add(variante);
      tonos.add(tono);
    }
    expect(adornos.size).toBe(VARIANTES);
    expect(tonos.size).toBe(TONOS);
  });
});

describe('tonosDe', () => {
  it('deja la base al medio, un tono más claro y otro más oscuro', () => {
    const luz = (c: string) => [1, 3, 5].reduce((s, k) => s + parseInt(c.slice(k, k + 2), 16), 0);
    const [claro, base, oscuro] = tonosDe('#24d07f');
    expect(base).toBe('#24d07f');
    expect(luz(claro)).toBeGreaterThan(luz(base));
    expect(luz(oscuro)).toBeLessThan(luz(base));
  });
  it('no rompe con un color que no es hexadecimal', () => {
    expect(tonosDe('red')).toEqual(['red', 'red', 'red']);
  });
});

describe('poseDe', () => {
  it('respira sin pasarse de un 3 % fuera del bostezo y bosteza alguna vez por ciclo', () => {
    let bostezos = 0;
    for (let t = 0; t < 90; t += 0.05) {
      const pose = poseDe(t, 12345);
      if (pose.cuadro) bostezos++;
      else expect(Math.abs(pose.alto - 1)).toBeLessThanOrEqual(0.03 + 1e-9);
    }
    expect(bostezos).toBeGreaterThan(0);
  });
});
