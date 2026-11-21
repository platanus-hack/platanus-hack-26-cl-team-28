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
  alHablar(agente: number | null): void;
  activo: boolean;
}

interface Globo {
  clave: number;
  voz: Voz;
  x: number;
  y: number;
  lado: 1 | -1;
}

const CADA = 2100;
const ANCHO = 270;
const MARGEN = 16;

/** Quién es, en pocas palabras: lo que diría un subtítulo. */
export function quienEs(agente: AgenteRemoto): string {
  const genero = agente.atributos['Género'] ?? agente.atributos.Sexo ?? '';
  const quien = genero.startsWith('F') || genero === 'Mujer' ? 'Mujer' : genero.startsWith('M') || genero === 'Hombre' ? 'Hombre' : 'Persona';
  return [`${quien}, ${agente.edad}`, agente.comuna].filter(Boolean).join(' · ');
}

/**
 * Mientras los agentes responden, una frase real aparece junto al punto de quien la dijo.
 * Así la escala se ve humana: cada punto es alguien con nombre de comuna y motivo.
 */
export function Voces({ voces, caso, agentes, ubicar, alHablar, activo }: Props) {
  const [globos, setGlobos] = useState<Globo[]>([]);
  const vistas = useRef(new Set<number>());
  const clave = useRef(0);

  useEffect(() => {
    vistas.current = new Set();
    setGlobos([]);
  }, [caso]);

  useEffect(() => {
    if (!activo) {
      setGlobos([]);
      alHablar(null);
      return;
    }
    const tic = window.setInterval(() => {
      const candidatas = voces.current.filter((v) => v.caso === caso && !vistas.current.has(v.agente) && v.frase.length > 8);
      // Se alternan posturas para que no hablen solo los de un lado.
      const ultima = globos[globos.length - 1]?.voz;
      const voz = candidatas.reverse().find((v) => !ultima || posturaDe(v.acuerdo) !== posturaDe(ultima.acuerdo)) ?? candidatas[0];
      if (!voz) return;
      const lugar = ubicar(voz.agente);
      if (!lugar) return;
      vistas.current.add(voz.agente);
      const [x, y] = lugar;
      const lado: 1 | -1 = x < window.innerWidth / 2 ? -1 : 1;
      const nuevo = { clave: clave.current++, voz, x, y, lado };
      setGlobos((lista) => [...lista.slice(-1), nuevo]);
      alHablar(voz.agente);
    }, CADA);
    return () => window.clearInterval(tic);
  }, [activo, caso, voces, ubicar, alHablar, globos]);

  return (
    <div className={estilos.capa} aria-hidden="true">
      {globos.map((g, k) => {
        const agente = agentes[g.voz.agente];
        const izquierda = g.lado === 1 ? g.x + 22 : g.x - 22 - ANCHO;
        const x = Math.max(MARGEN, Math.min(window.innerWidth - ANCHO - MARGEN, izquierda));
        const y = Math.max(MARGEN, Math.min(window.innerHeight - 140, g.y - 34));
        return (
          <figure
            key={g.clave}
            className={estilos.globo}
            data-postura={posturaDe(g.voz.acuerdo)}
            data-viejo={k < globos.length - 1 || undefined}
            data-lado={g.lado}
            style={{ left: x, top: y, width: ANCHO }}
          >
            <blockquote>{g.voz.frase}</blockquote>
            <figcaption>{agente ? quienEs(agente) : ''}</figcaption>
          </figure>
        );
      })}
    </div>
  );
}
