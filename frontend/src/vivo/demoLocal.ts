import { hashTexto, mezclar } from '../dominio/azar';
import { crearPoblacion } from '../dominio/poblacion';
import type { AgenteRemoto, CasoPedido, Evento, Metricas } from './api';
import { PREGUNTAS } from './encuesta';
import { rasgosDe } from './sociedad';

type Anillo = number[][];

const AGENTES = 2000;
const LOTE = 40;
const PAUSA = 70;

/** Agentes inventados para cuando no hay motor: misma forma que los reales, sin perfil detrás. */
export function agentesDeDemostracion(regiones: Anillo[][]): AgenteRemoto[] {
  return crearPoblacion(AGENTES, regiones).map((p) => ({
    i: p.id,
    id: `demo-${p.id}`,
    region: p.region,
    comuna: '',
    lon: p.lon,
    lat: p.lat,
    edad: p.edad,
    genero: p.genero,
    quintil: p.quintil,
    educacion: p.educacion,
    politica: p.politica,
    s: rasgosDe(p),
    atributos: { Edad: `${p.edad} años`, Zona: 'Urbana' },
  }));
}

/**
 * Motor de demostración en el navegador: mismos eventos que el real, con acuerdos sorteados
 * según el texto y sin frases. La interfaz lo rotula como demostración.
 */
export function correrDemostracion(
  pedido: { casos: CasoPedido[]; agentes: number[]; iteraciones: number },
  alEvento: (evento: Evento) => void,
): () => void {
  let cancelado = false;
  const inicio = performance.now();
  const metricas = (): Metricas => ({ llamadas: 0, costo_usd: 0, tokens: 0, segundos: Math.round((performance.now() - inicio) / 100) / 10 });
  const casos = pedido.casos.map((c) => ({ id: c.id, letra: c.letra, texto: c.texto, titulo: c.texto, documento: null, iteracion: null }));
  const preguntas = [...PREGUNTAS];
  alEvento({ tipo: 'inicio', motor: { nombre: 'Demostración', modelo: 'sin motor', grabado: true }, agentes: pedido.agentes.length, casos, preguntas });
  const tareas: { caso: number; agentes: number[] }[] = [];
  casos.forEach((_, k) => {
    for (let i = 0; i < pedido.agentes.length; i += LOTE) tareas.push({ caso: k, agentes: pedido.agentes.slice(i, i + LOTE) });
  });
  const restantes = casos.map((_, k) => tareas.filter((t) => t.caso === k).length);
  const paso = () => {
    if (cancelado) return;
    const tarea = tareas.shift();
    if (!tarea) {
      alEvento({ tipo: 'fin', metricas: metricas() });
      return;
    }
    const semilla = hashTexto(casos[tarea.caso].texto);
    const nota = (valor: number) => Math.max(1, Math.min(7, Math.round(valor)));
    const r = tarea.agentes.map((a): [number, number, string, number[]] => {
      const base = 4 + (mezclar(semilla, a) - 0.5) * 5 + (mezclar(semilla, 7) - 0.5) * 2;
      // Las demás preguntas se sortean alrededor de la primera, cada una con su propio sesgo.
      const notas = preguntas.map((pregunta, k) => {
        if (k === 0) return nota(base);
        const propia = hashTexto(pregunta);
        return nota(base + (mezclar(propia, 3) - 0.5) * 2.4 + (mezclar(propia, a) - 0.5) * 3);
      });
      return [a, nota(base), '', notas];
    });
    alEvento({ tipo: 'respuestas', caso: tarea.caso, cache: false, r, metricas: metricas() });
    restantes[tarea.caso] -= 1;
    if (restantes[tarea.caso] === 0) alEvento({ tipo: 'caso_listo', caso: tarea.caso, apoyo: 0, metricas: metricas() });
    window.setTimeout(paso, PAUSA);
  };
  window.setTimeout(paso, 600);
  return () => {
    cancelado = true;
  };
}
