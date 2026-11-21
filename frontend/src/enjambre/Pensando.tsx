import { useEffect, useState } from 'react';
import type { AgenteRemoto } from '../vivo/api';
import type { CasoVivo } from '../vivo/useEnVivo';
import estilos from './Pensando.module.css';
import { quienEs } from './Voces';

interface Props {
  caso: CasoVivo;
  agentes: AgenteRemoto[];
  muestra: number[];
}

const CADA = 140;
const FILAS = 4;

/** Mientras esperan, pasan rápido las personas a las que se les está preguntando: se ve la escala. */
export function Pensando({ caso, agentes, muestra }: Props) {
  const [filas, setFilas] = useState<string[]>([]);
  useEffect(() => {
    if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const tic = window.setInterval(() => {
      for (let intento = 0; intento < 12; intento++) {
        const i = muestra[Math.floor(Math.random() * muestra.length)];
        if (i === undefined || caso.acuerdo[i]) continue;
        const agente = agentes[i];
        setFilas((lista) => [quienEs(agente), ...lista].slice(0, FILAS));
        return;
      }
    }, CADA);
    return () => window.clearInterval(tic);
  }, [caso, agentes, muestra]);
  if (!filas.length) return null;
  return (
    <div className={estilos.pensando} aria-hidden="true">
      <p className={estilos.titulo}>Pensando ahora</p>
      <ol>
        {filas.map((fila, k) => (
          <li key={`${fila}-${k}`} style={{ opacity: 1 - k * 0.24 }}>
            {fila}
          </li>
        ))}
      </ol>
    </div>
  );
}
