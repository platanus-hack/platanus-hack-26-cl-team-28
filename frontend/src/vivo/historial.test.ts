import { describe, expect, it } from 'vitest';
import { cuando, preguntaDe, repartoDe, textosDe, type CasoHistorial, type EntradaHistorial } from './historial';

const caso = (parte: Partial<CasoHistorial>): CasoHistorial => ({
  letra: 'A', texto: 'Rebajar el TAG', titulo: '', documento: null, iteracion: false, respondidas: 0, favor: 0, contra: 0, indecisa: 0, ...parte,
});

describe('repartoDe', () => {
  it('entrega porcentajes enteros que suman 100', () => {
    const reparto = repartoDe({ favor: 1, contra: 1, indecisa: 1 });
    expect(reparto.favor + reparto.contra + reparto.indecisa).toBe(100);
    expect(repartoDe({ favor: 142, contra: 52, indecisa: 6 })).toEqual({ favor: 71, contra: 26, indecisa: 3 });
    expect(repartoDe({ favor: 2, contra: 1, indecisa: 0 })).toEqual({ favor: 67, contra: 33, indecisa: 0 });
  });

  it('sin respuestas da ceros', () => {
    expect(repartoDe({ favor: 0, contra: 0, indecisa: 0 })).toEqual({ favor: 0, contra: 0, indecisa: 0 });
  });
});

describe('cuando', () => {
  const ahora = new Date(2026, 10, 21, 18, 0);
  it('nombra hoy y ayer, y después el día', () => {
    expect(cuando(new Date(2026, 10, 21, 17, 43).toISOString(), ahora)).toBe('Hoy, 17:43');
    expect(cuando(new Date(2026, 10, 20, 23, 59).toISOString(), ahora)).toBe('Ayer, 23:59');
    expect(cuando(new Date(2026, 10, 3, 9, 5).toISOString(), ahora)).toMatch(/^3 nov\.?, 09:05$/);
    expect(cuando(new Date(2025, 11, 30, 9, 5).toISOString(), ahora)).toMatch(/2025, 09:05$/);
  });

  it('una hora ilegible queda vacía', () => {
    expect(cuando('no es una fecha', ahora)).toBe('');
  });
});

describe('lo que se vuelve a preguntar', () => {
  const entrada: EntradaHistorial = {
    id: 'x', hora: '', agentes: 4, modelo: '', segundos: 1, costo_usd: 0, completa: true,
    casos: [caso({}), caso({ letra: 'B', texto: '', titulo: 'Ley corta', documento: 'ley.pdf' }), caso({ letra: 'C', texto: 'La del agente', iteracion: true })],
  };

  it('solo los textos que escribió la persona', () => {
    expect(textosDe(entrada)).toEqual(['Rebajar el TAG']);
  });

  it('un documento se muestra por su título', () => {
    expect(entrada.casos.map(preguntaDe)).toEqual(['Rebajar el TAG', 'Ley corta', 'La del agente']);
  });
});
