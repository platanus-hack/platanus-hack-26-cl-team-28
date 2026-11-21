import { useEffect, useRef, useState, type MutableRefObject } from 'react';
import type { AgenteRemoto } from '../vivo/api';
import { posturaDe, type Voz } from '../vivo/useEnVivo';
import estilos from './Voces.module.css';

interface Props {
  voces: MutableRefObject<Voz[]>;
  caso: number;
  agentes: AgenteRemoto[];
  /** Pantalla donde está dibujado el agente; null si no se puede ubicar. */
  ubicar(agente: number): [number, number] | null;
  alHablar(agentes: number[]): void;
  activo: boolean;
}

type Lado = 'izquierda' | 'derecha';

interface Globo {
  clave: number;
  voz: Voz;
  x: number;
  y: number;
}

const CADA = 1400;
const ANCHO = Math.round(Math.max(260, Math.min(380, window.innerWidth * 0.2)));
const MARGEN = 16;
/** A la derecha hablan quienes están a favor y a la izquierda quienes están en contra, como vuelan después. */
const PREFIERE: Record<Lado, string> = { derecha: 'favor', izquierda: 'contra' };

/** Quién es, en pocas palabras: lo que diría un subtítulo. */
export function quienEs(agente: AgenteRemoto): string {
  const genero = agente.atributos['Género'] ?? agente.atributos.Sexo ?? '';
  const quien = genero.startsWith('F') || genero === 'Mujer' ? 'Mujer' : genero.startsWith('M') || genero === 'Hombre' ? 'Hombre' : 'Persona';
  return [`${quien}, ${agente.edad}`, agente.comuna].filter(Boolean).join(' · ');
}

/**
 * Mientras los agentes responden, frases reales aparecen junto al punto de quien las dijo: a la
 * derecha alguien a favor, a la izquierda alguien en contra. Así la escala se ve humana.
 */
export function Voces({ voces, caso, agentes, ubicar, alHablar, activo }: Props) {
  const [globos, setGlobos] = useState<Partial<Record<Lado, Globo>>>({});
  const vistas = useRef(new Set<number>());
  const clave = useRef(0);
  const turno = useRef<Lado>('derecha');
  const hablando = useRef<Partial<Record<Lado, number>>>({});

  useEffect(() => {
    vistas.current = new Set();
    hablando.current = {};
    setGlobos((g) => (g.izquierda || g.derecha ? {} : g));
  }, [caso]);

  useEffect(() => {
    if (!activo) {
      setGlobos((g) => (g.izquierda || g.derecha ? {} : g));
      hablando.current = {};
      alHablar([]);
      return;
    }
    const tic = window.setInterval(() => {
      const lado = turno.current;
      turno.current = lado === 'derecha' ? 'izquierda' : 'derecha';
      const candidatas = voces.current.filter((v) => v.caso === caso && !vistas.current.has(v.agente) && v.frase.length > 8);
      const voz = [...candidatas].reverse().find((v) => posturaDe(v.acuerdo) === PREFIERE[lado]) ?? candidatas.find((v) => posturaDe(v.acuerdo) === 'indecisa');
      if (!voz) return;
      const lugar = ubicar(voz.agente);
      if (!lugar) return;
      vistas.current.add(voz.agente);
      hablando.current[lado] = voz.agente;
      setGlobos((g) => ({ ...g, [lado]: { clave: clave.current++, voz, x: lugar[0], y: lugar[1] } }));
      alHablar(Object.values(hablando.current) as number[]);
    }, CADA);
    return () => window.clearInterval(tic);
  }, [activo, caso, voces, ubicar, alHablar]);

  return (
    <div className={estilos.capa} aria-hidden="true">
      {(['izquierda', 'derecha'] as const).map((lado) => {
        const g = globos[lado];
        if (!g) return null;
        const agente = agentes[g.voz.agente];
        const izquierda = lado === 'derecha' ? g.x + 30 : g.x - 30 - ANCHO;
        const x = Math.max(MARGEN, Math.min(window.innerWidth - ANCHO - MARGEN, izquierda));
        const y = Math.max(MARGEN, Math.min(window.innerHeight - 170, g.y - 40));
        return (
          <figure key={g.clave} className={estilos.globo} data-postura={posturaDe(g.voz.acuerdo)} data-lado={lado} style={{ left: x, top: y, width: ANCHO }}>
            <blockquote>{g.voz.frase}</blockquote>
            <figcaption>{agente ? quienEs(agente) : ''}</figcaption>
          </figure>
        );
      })}
    </div>
  );
}
