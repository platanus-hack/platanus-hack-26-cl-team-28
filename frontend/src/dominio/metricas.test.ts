import { describe, expect, it } from 'vitest';
import { calcularMuestra, FILTROS_INICIALES, personasPorFigura } from './muestra';
import { porcentajes, resumirCaso } from './metricas';
import { simuladorDemostracion } from './simulador';
import type { Persona, Respuesta } from './tipos';

const persona = (id: number, region: number, edad = 40): Persona => ({
  id, region, lon: -70, lat: -33, edad, genero: 0, quintil: 2, educacion: 1, politica: 2, aspecto: 0,
});
const respuesta = (postura: Respuesta['postura'], accion = 0): Respuesta => ({ postura, firmeza: 0.5, accion, razon: 0 });

describe('porcentajes', () => {
  it('suman 100 aunque los tercios no sean enteros', () => {
    const p = porcentajes({ favor: 1, contra: 1, indecisa: 1, total: 3 });
    expect(p.favor + p.contra + p.indecisa).toBe(100);
  });
  it('dan cero con total cero', () => {
    expect(porcentajes({ favor: 0, contra: 0, indecisa: 0, total: 0 })).toEqual({ favor: 0, contra: 0, indecisa: 0 });
  });
});

describe('resumirCaso', () => {
  const personas = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9].map((i) => persona(i, i < 5 ? 6 : 10));
  const respuestas = personas.map((_, i) => respuesta(i < 5 ? 'favor' : i < 8 ? 'contra' : 'indecisa', i < 2 ? 3 : 0));
  const r = resumirCaso(personas, respuestas);
  it('cuenta posturas y apoyo neto', () => {
    expect(r.porcentajes).toEqual({ favor: 50, contra: 30, indecisa: 20 });
    expect(r.apoyoNeto).toBe(20);
  });
  it('mide la brecha entre regiones con datos suficientes', () => {
    expect(r.brechaTerritorial).toBe(100);
  });
  it('cuenta la movilización', () => {
    expect(r.movilizacion).toBe(20);
  });
  it('rechaza listas de distinto largo', () => {
    expect(() => resumirCaso(personas, respuestas.slice(1))).toThrow();
  });
});

describe('muestra', () => {
  const personas = [persona(0, 6, 20), persona(1, 6, 70), persona(2, 10, 30), persona(3, 10, 90)];
  it('sin filtros entra todo y respeta el tamaño pedido', () => {
    const m = calcularMuestra(personas, FILTROS_INICIALES);
    expect(m.indices).toHaveLength(4);
    expect(m.total).toBe(10_000);
    expect(personasPorFigura(m)).toBe(2500);
  });
  it('el borde superior de edad incluye a los de 90 o más', () => {
    const m = calcularMuestra(personas, { ...FILTROS_INICIALES, edadMin: 70 });
    expect(m.indices).toEqual([1, 3]);
  });
  it('sin coincidencias la muestra queda vacía', () => {
    const m = calcularMuestra(personas, { ...FILTROS_INICIALES, region: 0 });
    expect(m.total).toBe(0);
    expect(personasPorFigura(m)).toBe(0);
  });
});

describe('simulador de demostración', () => {
  it('es determinista y entrega una respuesta por persona', async () => {
    const personas = [persona(0, 6), persona(1, 10)];
    const casos = [{ id: 'a', letra: 'A', texto: 'Caso de prueba' }];
    const [uno] = await simuladorDemostracion.simular(casos, personas);
    const [dos] = await simuladorDemostracion.simular(casos, personas);
    expect(uno.respuestas).toHaveLength(2);
    expect(uno).toEqual(dos);
  });
});
