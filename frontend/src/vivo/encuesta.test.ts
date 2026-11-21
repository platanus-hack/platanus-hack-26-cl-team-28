import { describe, expect, it } from 'vitest';
import { corta, ENCUESTA, midePostura, PREGUNTAS, resumirEncuesta } from './encuesta';

describe('encuesta', () => {
  it('son cinco preguntas fijas, cada una con su escala', () => {
    expect(PREGUNTAS).toHaveLength(5);
    expect(ENCUESTA.map((p) => p.nombre)).toEqual(['Apoyo', 'Justicia', 'Confianza', 'Efectividad', 'Influencia']);
    expect(ENCUESTA[1]).toMatchObject({ minimo: 'muy injusto', maximo: 'muy justo' });
  });

  it('resume cada pregunta entre los agentes que se miran', () => {
    const notas = [[7, 1], [5, 4], undefined, [2, 6], [6, 6]];
    const [primera, segunda] = resumirEncuesta(notas, [0, 1, 2, 3], 2);
    expect(primera.conteo).toEqual({ favor: 2, contra: 1, indecisa: 0, total: 3 });
    expect(primera.media).toBeCloseTo(14 / 3);
    expect(segunda.conteo).toEqual({ favor: 1, contra: 1, indecisa: 1, total: 3 });
  });

  it('sin respuestas no divide por cero', () => {
    expect(resumirEncuesta([], [0, 1], 1)[0]).toEqual({ conteo: { favor: 0, contra: 0, indecisa: 0, total: 0 }, media: 0 });
  });

  it('nombra las preguntas en corto y separa la que no mide postura', () => {
    expect(corta(PREGUNTAS[2])).toBe('Confianza');
    expect(corta('¿Votarías por esto?')).toBe('¿Votarías por esto?');
    expect(midePostura(PREGUNTAS[0])).toBe(true);
    expect(midePostura(PREGUNTAS[4])).toBe(false);
  });
});
