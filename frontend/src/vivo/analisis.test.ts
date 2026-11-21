import { describe, expect, it } from 'vitest';
import { alto, correlacion, cruzar, DIMENSIONES, MINIMO_GRUPO, ordenarDimensiones, resumirDimension, tramoDe, type PersonaAnalisis } from './analisis';
import { CLAVES } from './sociedad';

const dimension = (clave: string) => DIMENSIONES.find((d) => d.clave === clave)!;
const lugar = (clave: string) => CLAVES.indexOf(clave as (typeof CLAVES)[number]);

/** Una persona con los rasgos dados y el resto sin dato. */
function persona(edad: number, rasgos: Record<string, number> = {}): PersonaAnalisis {
  const s = CLAVES.map(() => -1);
  for (const [clave, opcion] of Object.entries(rasgos)) s[lugar(clave)] = opcion;
  return { edad, s };
}

describe('análisis por características', () => {
  it('pone cada edad en su tramo, con los bordes del lado que corresponde', () => {
    expect([14, 17, 18, 29, 30, 44, 45, 59, 60, 74, 75, 85].map(tramoDe)).toEqual([0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5]);
  });

  it('ofrece la edad después de la región y lee cada rasgo en su lugar', () => {
    expect(DIMENSIONES.slice(0, 3).map((d) => d.clave)).toEqual(['region', 'edad', 'genero']);
    expect(dimension('politica').grupoDe(persona(40, { politica: 4 }))).toBe(4);
    expect(dimension('politica').grupoDe({ edad: 40 })).toBe(-1);
  });

  it('resume cada grupo y deja fuera a quien no respondió o no tiene el dato', () => {
    const personas = [persona(30, { genero: 0 }), persona(30, { genero: 0 }), persona(30, { genero: 1 }), persona(30), persona(30, { genero: 1 })];
    const notas = [[7], [4], [2], [6], undefined];
    const r = resumirDimension(dimension('genero'), personas, notas, [0, 1, 2, 3, 4], 0);
    expect(r.grupos[0]).toMatchObject({ favor: 1, indecisa: 1, contra: 0, total: 2, suma: 11 });
    expect(r.grupos[1]).toMatchObject({ favor: 0, contra: 1, total: 1 });
    expect(r.total.total).toBe(3);
    expect(alto(r.grupos[0])).toBe(50);
    // Con menos de MINIMO_GRUPO respuestas por grupo no hay extremos que comparar.
    expect(r.extremos).toBeNull();
  });

  it('solo cuenta a los agentes que se están mirando', () => {
    const personas = [persona(30, { genero: 0 }), persona(30, { genero: 0 })];
    expect(resumirDimension(dimension('genero'), personas, [[7], [1]], [1], 0).grupos[0]).toMatchObject({ contra: 1, total: 1 });
  });

  it('ordena primero la característica que de verdad separa las respuestas', () => {
    // 60 personas: la posición política decide la nota; la región se reparte sin relación con ella.
    const personas = Array.from({ length: 60 }, (_, i) => persona(30, { politica: i % 2 ? 4 : 0, region: Math.floor(i / 2) % 3 }));
    const notas = personas.map((_, i) => [i % 2 ? 6 : 2]);
    const agentes = personas.map((_, i) => i);
    const ranking = ordenarDimensiones(personas, notas, agentes, 0);
    expect(ranking[0].dimension.clave).toBe('politica');
    expect(ranking[0].fuerza).toBeCloseTo(1);
    expect(ranking[0].clara).toBe(true);
    expect(ranking[0].extremos).toEqual({ mayor: 4, menor: 0, brecha: 100 });
    const region = ranking.find((r) => r.dimension.clave === 'region')!;
    expect(region.fuerza).toBe(0);
    expect(region.clara).toBe(false);
    expect(region.extremos!.brecha).toBe(0);
    // La edad es la misma en todos: un solo grupo, no hay nada que comparar.
    expect(ranking.some((r) => r.dimension.clave === 'edad')).toBe(false);
  });

  it('no da por clara una diferencia que es puro azar, aunque haya muchos grupos y poca gente', () => {
    // 250 personas en 6 grupos, con notas que no dependen del grupo: un generador fijo, sin relación alguna.
    let semilla = 12345;
    const azar = () => (semilla = (semilla * 1103515245 + 12345) % 2147483648) / 2147483648;
    let claras = 0;
    for (let vuelta = 0; vuelta < 200; vuelta++) {
      const personas = Array.from({ length: 250 }, () => persona(30, { politica: Math.floor(azar() * 6) }));
      const notas = personas.map(() => [1 + Math.floor(azar() * 7)]);
      if (resumirDimension(dimension('politica'), personas, notas, personas.map((_, i) => i), 0).clara) claras += 1;
    }
    // Con el corte fijo anterior pasaba casi una de cada tres; ahora, a lo más unas pocas de 200.
    expect(claras).toBeLessThanOrEqual(6);
  });

  it('con un solo grupo comparable no hay fuerza ni extremos, y va al final', () => {
    const personas = [...Array.from({ length: 30 }, () => persona(30, { region: 6, genero: 0 })), ...Array.from({ length: 5 }, () => persona(30, { region: 1, genero: 1 }))];
    const notas = personas.map((_, i) => [i < 30 ? 2 : 7]);
    const r = resumirDimension(dimension('region'), personas, notas, personas.map((_, i) => i), 0);
    expect(r).toMatchObject({ fuerza: 0, clara: false, extremos: null });
  });

  it('un grupo chico no entra en los extremos aunque sea el más alto', () => {
    const personas = [...Array.from({ length: 2 * MINIMO_GRUPO }, (_, i) => persona(30, { genero: i % 2 })), persona(30, { genero: 2 })];
    const notas = personas.map((_, i) => [i === personas.length - 1 ? 7 : i % 2 ? 5 : 3]);
    const r = resumirDimension({ ...dimension('genero'), grupos: ['a', 'b', 'c'] }, personas, notas, personas.map((_, i) => i), 0);
    expect(r.grupos[2].total).toBe(1);
    expect(r.extremos).toEqual({ mayor: 1, menor: 0, brecha: 100 });
  });

  it('cruza dos características en una tabla de filas por columnas', () => {
    const personas = [persona(20, { genero: 0 }), persona(20, { genero: 1 }), persona(70, { genero: 1 }), persona(70)];
    const tabla = cruzar(dimension('edad'), dimension('genero'), personas, [[7], [1], [5], [5]], [0, 1, 2, 3], 0);
    expect(tabla).toHaveLength(6);
    expect(tabla[1][0]).toMatchObject({ favor: 1, total: 1 });
    expect(tabla[1][1]).toMatchObject({ contra: 1, total: 1 });
    expect(tabla[4][1]).toMatchObject({ favor: 1, total: 1 });
    expect(tabla.flat().reduce((suma, c) => suma + c.total, 0)).toBe(3);
  });

  it('mide si dos preguntas se mueven juntas', () => {
    const agentes = Array.from({ length: 40 }, (_, i) => i);
    const juntas = agentes.map((i) => [1 + (i % 7), 1 + (i % 7), 7 - (i % 7), 4]);
    expect(correlacion(juntas, agentes, 0, 1)).toBeCloseTo(1);
    expect(correlacion(juntas, agentes, 0, 2)).toBeCloseTo(-1);
    // Una pregunta que todos responden igual no tiene con qué correlacionar.
    expect(correlacion(juntas, agentes, 0, 3)).toBeNull();
    expect(correlacion(juntas, agentes.slice(0, 5), 0, 1)).toBeNull();
  });
});
