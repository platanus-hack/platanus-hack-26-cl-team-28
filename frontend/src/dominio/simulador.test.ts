// @vitest-environment node
import { describe, expect, it, vi } from 'vitest';
import { resumirCaso } from './metricas';
import { crearSimuladorDemostracion } from './simulador';
import type { Avance, Caso, Persona } from './tipos';

const personas: Persona[] = Array.from({ length: 400 }, (_, id) => ({
  id, region: id % 16, lon: -70, lat: -20 - (id % 30), edad: 18 + (id % 70), genero: id % 2, quintil: id % 5, educacion: id % 5, politica: id % 6, aspecto: 0,
}));
const base: Caso = { id: 'a', letra: 'A', texto: 'Propuesta de prueba' };

describe('simulador de demostración', () => {
  it('avisa una vez por persona del primer caso, en desorden, antes de terminar', async () => {
    vi.stubGlobal('window', { setTimeout: (f: () => void) => setTimeout(f, 0) });
    const avances: Avance[] = [];
    const [resultado] = await crearSimuladorDemostracion(120).simular([base], personas, (a) => avances.push(a));
    expect(avances).toHaveLength(personas.length);
    expect(new Set(avances.map((a) => a.persona)).size).toBe(personas.length);
    expect(avances.map((a) => a.persona)).not.toEqual(personas.map((_, i) => i));
    expect(avances.every((a) => a.respuesta === resultado.respuestas[a.persona])).toBe(true);
    vi.unstubAllGlobals();
  });

  it('las iteraciones del agente parten de su variante y suman apoyo', async () => {
    const simulador = crearSimuladorDemostracion(0);
    const propuestas = await simulador.proponerIteraciones(base, 2);
    expect(propuestas.map((p) => p.iteracion)).toEqual([{ de: 'A', numero: 1 }, { de: 'A', numero: 2 }]);
    const casos = [base, ...propuestas.map((p, k) => ({ ...p, id: `i${k}`, letra: 'BC'[k] }))];
    const resultados = await simulador.simular(casos, personas);
    const favor = resultados.map((r) => resumirCaso(personas, r.respuestas).conteo.favor);
    expect(favor[1]).toBeGreaterThan(favor[0]);
    expect(favor[2]).toBeGreaterThan(favor[1]);
  });

  it('un documento sin texto también identifica la propuesta', async () => {
    const simulador = crearSimuladorDemostracion(0);
    const conDocumento = (nombre: string): Caso => ({ id: 'd', letra: 'A', texto: '', documento: { nombre, tamano: 1000, archivo: {} as File } });
    const [uno] = await simulador.simular([conDocumento('ley-a.pdf')], personas);
    const [otro] = await simulador.simular([conDocumento('ley-b.pdf')], personas);
    expect(uno.respuestas).not.toEqual(otro.respuestas);
  });
});
