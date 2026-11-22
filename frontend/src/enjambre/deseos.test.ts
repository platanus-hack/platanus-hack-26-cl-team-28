import { describe, expect, it } from 'vitest';
import { bolsaDeDeseos, DESEOS, mismaComuna } from './deseos';

/** Azar repetible, para que la prueba no dependa de la suerte. */
function azarFijo(semilla: number): () => number {
  let s = semilla;
  return () => {
    s = (s * 1664525 + 1013904223) % 4294967296;
    return s / 4294967296;
  };
}

describe('DESEOS', () => {
  it('son frases distintas y ninguna está vacía', () => {
    expect(DESEOS.length).toBeGreaterThan(1);
    expect(new Set(DESEOS.map((d) => d.frase)).size).toBe(DESEOS.length);
    for (const deseo of DESEOS) expect(deseo.frase.trim()).not.toBe('');
  });
  it('el de JAPS se dice desde Las Condes', () => {
    const japs = DESEOS.find((d) => d.firma === 'JAPS');
    expect(japs?.comuna).toBe('Las Condes');
  });
});

describe('mismaComuna', () => {
  it('no se fija en mayúsculas ni tildes', () => {
    expect(mismaComuna('Las Condes', 'las condes')).toBe(true);
    expect(mismaComuna('Ñuñoa', 'ÑUÑOA ')).toBe(true);
    expect(mismaComuna('Peñalolén', 'Penalolen')).toBe(true);
    expect(mismaComuna('Las Condes', 'Lo Barnechea')).toBe(false);
  });
});

describe('bolsaDeDeseos', () => {
  it('dice todos los deseos antes de repetir alguno', () => {
    for (let semilla = 1; semilla <= 50; semilla++) {
      const siguiente = bolsaDeDeseos(azarFijo(semilla));
      for (let vuelta = 0; vuelta < 4; vuelta++) {
        const dichos = Array.from({ length: DESEOS.length }, siguiente);
        expect(new Set(dichos).size).toBe(DESEOS.length);
      }
    }
  });
  it('no repite el mismo deseo dos veces seguidas al empezar otra vuelta', () => {
    for (let semilla = 1; semilla <= 200; semilla++) {
      const siguiente = bolsaDeDeseos(azarFijo(semilla));
      let anterior: unknown;
      for (let i = 0; i < DESEOS.length * 5; i++) {
        const deseo = siguiente();
        expect(deseo).not.toBe(anterior);
        anterior = deseo;
      }
    }
  });
  it('el de JAPS es siempre el segundo de cada vuelta', () => {
    for (let semilla = 1; semilla <= 50; semilla++) {
      const siguiente = bolsaDeDeseos(azarFijo(semilla));
      for (let vuelta = 0; vuelta < 3; vuelta++) {
        const dichos = Array.from({ length: DESEOS.length }, siguiente);
        expect(dichos.findIndex((d) => d.firma === 'JAPS')).toBe(1);
      }
    }
  });
  it('un puesto más allá del final deja ese deseo al último', () => {
    const [a, b, c] = [{ frase: 'a' }, { frase: 'b' }, { frase: 'c', puesto: 9 }];
    const siguiente = bolsaDeDeseos(azarFijo(7), [a, b, c]);
    expect(Array.from({ length: 3 }, siguiente)[2]).toBe(c);
  });
  it('con un solo deseo lo repite sin colgarse', () => {
    const uno = { frase: 'uno' };
    const siguiente = bolsaDeDeseos(azarFijo(3), [uno]);
    expect([siguiente(), siguiente()]).toEqual([uno, uno]);
  });
});
