import { describe, expect, it } from 'vitest';
import { separarPropuestas } from './orientacion';

describe('preparación de una comparación pública', () => {
  it('consulta cada alternativa sin mezclarla ni heredar una referencia de encuesta ajena', () => {
    const originales = [{ id: 8, texto: '¿Subir el IVA a 20% o bajarlo a 18%?' }, { id: 9, texto: 'Mantener el IVA en 19%' }];
    const resultado = separarPropuestas(originales, [
      { tipo: 'comparacion', motivo: '', propuestas: ['Subir el IVA a 20%', 'Bajar el IVA a 18%'] },
      { tipo: 'adecuada', motivo: '', propuestas: [] },
    ]);
    expect(resultado.map((b) => b.texto)).toEqual(['Subir el IVA a 20%', 'Bajar el IVA a 18%', 'Mantener el IVA en 19%']);
    expect(new Set(resultado.map((b) => b.id)).size).toBe(3);
    expect(resultado[2]).toBe(originales[1]);
    expect(originales[0].texto).toContain('¿Subir');
  });
  it('conserva íntegra una pregunta fuera de alcance cuando el usuario decide continuar', () => {
    const original = { id: 0, texto: '¿Colo Colo o la U?' };
    expect(separarPropuestas([original], [{ tipo: 'fuera', motivo: 'Preferencia deportiva', propuestas: [] }])).toEqual([original]);
  });
  it('conserva las políticas con varias medidas como un caso único', () => {
    const original = { id: 1, texto: 'Subsidiar buses eléctricos y ampliar recorridos rurales' };
    expect(separarPropuestas([original], [{ tipo: 'adecuada', motivo: '', propuestas: [] }])).toEqual([original]);
  });
});
