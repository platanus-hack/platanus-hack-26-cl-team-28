import { describe, expect, it } from 'vitest';
import {
  activos,
  alternar,
  CLAVES,
  coincide,
  conDatos,
  EDAD_TOPE,
  filtrosDePartida,
  hayFiltros,
  PARAMETROS,
  paraElMotor,
  quitar,
  rasgosDe,
  retratoDelMotor,
  retratoLocal,
  sinFiltros,
  type Clave,
  type Rasgos,
} from './sociedad';

const parametro = (clave: Clave) => PARAMETROS.find((p) => p.clave === clave)!;
/** Una persona con las opciones dadas y sin dato en lo demás. */
const persona = (edad: number, representa: number, opciones: Partial<Record<Clave, number>>): Rasgos => ({
  edad,
  representa,
  s: CLAVES.map((clave) => opciones[clave] ?? -1),
});

const PERSONAS = [
  persona(30, 10, { genero: 0, trabajo: 0 }),
  persona(70, 20, { genero: 0, trabajo: 2 }),
  persona(40, 30, { genero: 1, trabajo: 0 }),
  persona(16, 40, { genero: 1, trabajo: 1 }),
  persona(92, 50, { genero: 1 }),
];

describe('elegir opciones', () => {
  const inicio = filtrosDePartida(1000);

  it('suma opciones y, con todas elegidas, deja de filtrar', () => {
    let f = alternar(inicio, parametro('educacion'), 2);
    f = alternar(f, parametro('educacion'), 0);
    expect(f.elegidos.educacion).toEqual([0, 2]);
    f = alternar(f, parametro('educacion'), 1);
    expect(f.elegidos.educacion).toBeUndefined();
    expect(hayFiltros(f)).toBe(false);
  });

  it('tocar de nuevo una opción la quita', () => {
    const f = alternar(alternar(inicio, parametro('region'), 6), parametro('region'), 6);
    expect(f.elegidos).toEqual({});
  });

  it('con dos opciones, la otra reemplaza a la elegida', () => {
    const f = alternar(alternar(inicio, parametro('genero'), 0), parametro('genero'), 1);
    expect(f.elegidos.genero).toEqual([1]);
  });

  it('los mismos filtros se escriben igual, se elijan en el orden que sea', () => {
    const a = alternar(alternar(inicio, parametro('region'), 6), parametro('region'), 2);
    const b = alternar(alternar(inicio, parametro('region'), 2), parametro('region'), 6);
    expect(JSON.stringify(a)).toBe(JSON.stringify(b));
  });

  it('resume lo puesto, con la edad después del territorio', () => {
    let f = alternar(alternar(inicio, parametro('region'), 6), parametro('politica'), 0);
    f = { ...alternar(f, parametro('politica'), 1), edadMin: 28, edadMax: 77 };
    expect(activos(f).map((a) => a.texto)).toEqual(['RM', '28 a 77 años', 'Izq., C. izq.']);
    expect(activos(quitar(f, 'edad')).map((a) => a.clave)).toEqual(['region', 'politica']);
    expect(activos(sinFiltros(f))).toEqual([]);
    expect(sinFiltros(f).tamano).toBe(1000);
  });

  it('manda al motor la edad, el nivel y las listas elegidas', () => {
    const f = alternar({ ...inicio, reduccion: 100 }, parametro('voto'), 1);
    expect(paraElMotor(f)).toEqual({ edadMin: 14, edadMax: EDAD_TOPE, reduccion: 100, voto: [1] });
  });
});

describe('retrato de una población', () => {
  const inicio = filtrosDePartida(1000);

  it('sin filtros cuenta a todos, y del tope de edad en adelante es un solo tramo', () => {
    const retrato = retratoLocal(PERSONAS, inicio);
    expect(retrato.genero).toEqual([30, 120]);
    expect(retrato.trabajo).toEqual([40, 40, 20]);
    expect(retrato.edad.reduce((s, p) => s + p, 0)).toBe(150);
    expect(retrato.edad.at(-1)).toBe(50);
  });

  it('cada parámetro ignora su propio filtro', () => {
    const f = alternar(alternar(inicio, parametro('genero'), 0), parametro('trabajo'), 0);
    const retrato = retratoLocal(PERSONAS, f);
    expect(retrato.genero).toEqual([10, 30]);
    expect(retrato.trabajo).toEqual([10, 0, 20]);
    expect(retrato.edad.reduce((s, p) => s + p, 0)).toBe(10);
  });

  it('la edad filtra a los demás, no a su propio histograma', () => {
    const retrato = retratoLocal(PERSONAS, { ...inicio, edadMin: 18, edadMax: 60 });
    expect(retrato.genero).toEqual([10, 30]);
    expect(retrato.edad.reduce((s, p) => s + p, 0)).toBe(150);
  });

  it('quien no tiene el dato queda fuera al filtrar por él', () => {
    const f = alternar(inicio, parametro('trabajo'), 0);
    expect(PERSONAS.filter((p) => coincide(p, f)).map((p) => p.representa)).toEqual([10, 30]);
    expect(coincide(PERSONAS[4], inicio)).toBe(true);
  });

  it('el tope de edad incluye a los mayores', () => {
    expect(coincide(PERSONAS[4], { ...inicio, edadMin: 80 })).toBe(true);
    expect(coincide(PERSONAS[4], { ...inicio, edadMax: 84 })).toBe(false);
  });

  it('un parámetro sin datos no se ofrece', () => {
    const retrato = retratoLocal(PERSONAS, inicio);
    expect(conDatos(retrato, 'trabajo')).toBe(true);
    expect(conDatos(retrato, 'voto')).toBe(false);
  });
});

describe('lo que llega del motor', () => {
  it('ordena los rasgos como la interfaz, venga como venga el orden del motor', () => {
    const agente = { region: 6, genero: 1, quintil: 4, educacion: 3, s: [1, 6, 2] };
    const s = rasgosDe(agente, ['genero', 'region', 'voto']);
    expect(s[CLAVES.indexOf('region')]).toBe(6);
    expect(s[CLAVES.indexOf('genero')]).toBe(1);
    expect(s[CLAVES.indexOf('voto')]).toBe(2);
    expect(s[CLAVES.indexOf('salud')]).toBe(-1);
  });

  it('sin rasgos del motor usa lo que el agente trae a la vista', () => {
    const s = rasgosDe({ region: 3, genero: 0, quintil: 2, educacion: 4, politica: 5 });
    expect(CLAVES.map((clave, k) => [clave, s[k]]).filter(([, v]) => v !== -1)).toEqual([
      ['region', 3],
      ['genero', 0],
      ['educacion', 2],
      ['quintil', 2],
      ['politica', 5],
    ]);
  });

  it('acepta el retrato del motor y completa lo que falte', () => {
    expect(retratoDelMotor(undefined)).toBeUndefined();
    const retrato = retratoDelMotor({ genero: [5, 7], voto: [1, 2] })!;
    expect(retrato.genero).toEqual([5, 7]);
    // Con otro número de opciones que el de la interfaz, no se usa.
    expect(retrato.voto).toEqual([0, 0, 0, 0]);
    expect(retrato.edad).toHaveLength(EDAD_TOPE - 14 + 1);
  });
});
