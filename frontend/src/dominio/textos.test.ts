import { describe, expect, it } from 'vitest';
import { personasAprox } from './textos';

describe('personas aproximadas', () => {
  it('redondea a dos cifras y nombra los millones', () => {
    expect(personasAprox(6_348_000)).toBe('6,3 millones de personas');
    expect(personasAprox(1_020_000)).toBe('1 millón de personas');
    expect(personasAprox(12_400_000)).toBe('12 millones de personas');
    expect(personasAprox(23_870)).toBe('24.000 personas');
    expect(personasAprox(987_000)).toBe('990.000 personas');
    expect(personasAprox(996_000)).toBe('1 millón de personas');
    expect(personasAprox(42.4)).toBe('42 personas');
    expect(personasAprox(1)).toBe('1 persona');
  });
});
