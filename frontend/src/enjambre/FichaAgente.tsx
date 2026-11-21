import { useEffect, useRef } from 'react';
import { REGIONES } from '../dominio/catalogos';
import type { AgenteRemoto } from '../vivo/api';
import { posturaDe, type CasoVivo } from '../vivo/useEnVivo';
import estilos from './FichaAgente.module.css';
import { quienEs } from './Voces';

interface Props {
  agente: AgenteRemoto;
  casos: CasoVivo[];
  viendo: number;
  x: number;
  y: number;
  alCerrar(): void;
}

const MOSTRAR = ['Nivel educacional', 'Tramo socioeconómico', 'Previsión de salud', 'Tipo de vivienda', 'Hijos', 'Transporte al trabajo', 'Estado civil'];
const ANCHO = 420;
const POSTURA = { favor: 'a favor', contra: 'en contra', indecisa: 'indecisa' } as const;

function corto(clave: string, valor: string): string {
  if (clave === 'Tramo socioeconómico') return valor.replace(/ de 5 según.*$/, '').replace('Quintil', 'Quintil de ingreso');
  return valor.replace(/\s*\(.*?\)\s*/g, ' ').trim();
}

/** La persona detrás de un punto: quién es según el censo, qué respondió y por qué, en cada variante. */
export function FichaAgente({ agente, casos, viendo, x, y, alCerrar }: Props) {
  const caja = useRef<HTMLElement>(null);
  useEffect(() => {
    caja.current?.focus();
    const tecla = (e: KeyboardEvent) => e.key === 'Escape' && alCerrar();
    window.addEventListener('keydown', tecla);
    return () => window.removeEventListener('keydown', tecla);
  }, [alCerrar]);
  const izquierda = Math.max(16, Math.min(window.innerWidth - ANCHO - 16, x + 24));
  const arriba = Math.max(16, Math.min(window.innerHeight - 460, y - 60));
  const caso = casos[viendo];
  const acuerdo = caso?.acuerdo[agente.i] ?? 0;
  const frase = caso?.frase[agente.i];
  return (
    <aside ref={caja} tabIndex={-1} className={estilos.ficha} style={{ left: izquierda, top: arriba, width: ANCHO }} aria-label={`Agente: ${quienEs(agente)}`}>
      <header>
        <p className={estilos.quien}>{quienEs(agente)}</p>
        <p className={estilos.donde}>{REGIONES[agente.region].nombre}</p>
        <button type="button" className={estilos.cerrar} onClick={alCerrar} aria-label="Cerrar">
          <svg viewBox="0 0 12 12" aria-hidden="true">
            <path d="M2 2l8 8M10 2l-8 8" />
          </svg>
        </button>
      </header>
      {acuerdo > 0 && (
        <div className={estilos.respuesta} data-postura={posturaDe(acuerdo)}>
          {frase && <blockquote>{frase}</blockquote>}
          <p>
            Variante {caso.letra}: {acuerdo} de 7, {POSTURA[posturaDe(acuerdo)]}
          </p>
        </div>
      )}
      {casos.length > 1 && (
        <ol className={estilos.variantes} aria-label="Lo que respondió en cada variante">
          {casos.map((c) => {
            const valor = c.acuerdo[agente.i];
            return (
              <li key={c.id} data-postura={valor ? posturaDe(valor) : undefined}>
                <b>{c.letra}</b>
                <span style={{ width: `${(valor / 7) * 100}%` }} />
                <i>{valor ? `${valor} de 7` : 'sin respuesta'}</i>
              </li>
            );
          })}
        </ol>
      )}
      <dl className={estilos.datos}>
        {MOSTRAR.filter((clave) => agente.atributos[clave]).map((clave) => (
          <div key={clave}>
            <dt>{clave}</dt>
            <dd>{corto(clave, agente.atributos[clave])}</dd>
          </div>
        ))}
      </dl>
      <p className={estilos.fuente}>Persona de la muestra del Censo 2024 (INE), con datos de Casen 2024 imputados.</p>
    </aside>
  );
}
