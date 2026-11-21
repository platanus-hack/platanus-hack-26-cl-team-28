import { describe, expect, it } from 'vitest';
import { corta, limpiarPreguntas, PREGUNTAS_BASE, resumirEncuesta } from './encuesta';

describe('encuesta', () => {
  it('limpia espacios, vacías y repetidas', () => {
    expect(limpiarPreguntas(['  ¿Te   parece bien? ', '', '¿Te parece bien?', '¿Y justa?'])).toEqual(['¿Te parece bien?', '¿Y justa?']);
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

  it('acorta solo las preguntas de partida', () => {
    expect(corta(PREGUNTAS_BASE[3])).toBe('Confía en el Estado');
    expect(corta('¿Votarías por esto?')).toBe('¿Votarías por esto?');
  });
});
