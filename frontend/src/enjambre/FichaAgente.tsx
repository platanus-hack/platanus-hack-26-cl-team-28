import { useEffect, useRef } from 'react';
import { REGIONES } from '../dominio/catalogos';
import type { AgenteRemoto } from '../vivo/api';
import { corta } from '../vivo/encuesta';
import { posturaDe, type CasoVivo } from '../vivo/useEnVivo';
import { FiguraWati } from './FiguraWati';
import { rasgosDe } from './wati';
import estilos from './FichaAgente.module.css';
import { quienEs } from './Voces';

interface Props {
  agente: AgenteRemoto;
  casos: CasoVivo[];
  viendo: number;
  x: number;
  y: number;
  /** Las preguntas de la encuesta, en el orden de las notas. */
  preguntas?: string[];
  alCerrar(): void;
}

const ANCHO = 380;
const POSTURA = { favor: 'A favor', contra: 'En contra', indecisa: 'No se decide' } as const;
const ESCALA = [1, 2, 3, 4, 5, 6, 7];

/** Cómo se dice en la ficha cada dato que manda el motor (los grupos del perfil general). */
const DATOS: [string, (valor: string) => string][] = [
  ['Nivel educacional', (v) => `Educación ${v.toLowerCase()}`],
  ['Situación laboral', (v) => v],
  ['Tipo de colegio', (v) => `Va a un colegio ${v.toLowerCase()}`],
  ['Tramo socioeconómico', (v) => `${v} de ingreso`],
  ['Previsión de salud', (v) => v],
  ['Tipo de hogar', (v) => `Hogar ${v.toLowerCase()}`],
  ['Menores en el hogar', (v) => v],
  ['Tenencia de la vivienda', (v) => `Vivienda ${v.toLowerCase()}`],
  ['Religión', (v) => (v === 'Ninguna' ? 'Sin religión' : `Religión ${v.toLowerCase()}`)],
  ['Posición política', (v) => (v === 'No se ubica' ? 'No se ubica en izquierda ni derecha' : v.replace(/ \(.*\)$/, ''))],
  ['Evaluación del gobierno', (v) => (v === 'Sin respuesta' ? '' : `${v} al gobierno`)],
];

/** Lo que se sabe de la persona, dicho corto: sirve para leerlo de un vistazo. */
function datos(a: Record<string, string>): string[] {
  return DATOS.map(([clave, decir]) => (a[clave] ? decir(a[clave]) : '')).filter(Boolean);
}

/**
 * La persona detrás de un punto, como una credencial: su wati y su postura en la franja
 * de color, lo que dijo, cuánto apoyó cada variante en la misma escala de 1 a 7 que respondió,
 * y lo que el censo sabe de ella.
 */
export function FichaAgente({ agente, casos, viendo, x, y, preguntas, alCerrar }: Props) {
  const caja = useRef<HTMLElement>(null);
  useEffect(() => {
    caja.current?.focus({ preventScroll: true });
    const tecla = (e: KeyboardEvent) => e.key === 'Escape' && alCerrar();
    window.addEventListener('keydown', tecla);
    return () => window.removeEventListener('keydown', tecla);
  }, [alCerrar]);
  // Se abre hacia el centro de la pantalla, para no tapar las cifras de los costados.
  const haciaIzquierda = x > window.innerWidth / 2;
  // Se queda en la franja central, entre las dos columnas de texto, siempre que quepa ahí.
  const ancho = window.innerWidth;
  const columna = ancho >= 900 ? Math.max(16, Math.min(40, ancho * 0.026)) + Math.min(ancho * 0.28, 416) + 12 : 16;
  const borde = ancho - 2 * columna >= ANCHO ? columna : 16;
  const izquierda = Math.max(borde, Math.min(ancho - ANCHO - borde, haciaIzquierda ? x - ANCHO - 28 : x + 28));
  // Nunca se sale por abajo: sube lo necesario y, si aun así no cabe, se desplaza por dentro.
  const arriba = Math.max(16, Math.min(window.innerHeight - 500, y - 60));
  const caso = casos[viendo];
  const acuerdo = caso?.acuerdo[agente.i] ?? 0;
  const postura = acuerdo ? posturaDe(acuerdo) : 'indecisa';
  const frase = caso?.frase[agente.i];
  const notas = caso?.notas[agente.i];
  return (
    <aside
      ref={caja}
      tabIndex={-1}
      className={estilos.ficha}
      data-postura={postura}
      style={{ left: izquierda, top: arriba, width: ANCHO, maxHeight: window.innerHeight - arriba - 16 }}
      aria-label={`Agente: ${quienEs(agente)}`}
    >
      <header className={estilos.franja}>
        <FiguraWati estado={postura} rasgos={rasgosDe(`${agente.id}#0`)} alto={66} />
        <p className={estilos.postura}>
          {POSTURA[postura]}
          {acuerdo > 0 && (
            <span>
              {acuerdo} de 7{casos.length > 1 ? ` en la variante ${caso.letra}` : ''}
            </span>
          )}
        </p>
        <button type="button" className={estilos.cerrar} onClick={alCerrar} aria-label="Cerrar">
          <svg viewBox="0 0 12 12" aria-hidden="true">
            <path d="M2 2l8 8M10 2l-8 8" />
          </svg>
        </button>
      </header>
      <div className={estilos.cuerpo}>
        {frase && <blockquote className={estilos.frase}>{frase}</blockquote>}
        <p className={estilos.quien}>
          {quienEs(agente)}
          <span>{REGIONES[agente.region].nombre}</span>
        </p>
        {casos.length > 1 && (
          <ol className={estilos.variantes} aria-label="Lo que respondió en cada variante">
            {casos.map((c) => {
              const valor = c.acuerdo[agente.i];
              return (
                <li key={c.id} data-postura={valor ? posturaDe(valor) : undefined} aria-label={`Variante ${c.letra}: ${valor ? `${valor} de 7` : 'sin respuesta'}`}>
                  <b>{c.letra}</b>
                  <span aria-hidden="true">
                    {ESCALA.map((n) => (
                      <i key={n} data-lleno={n <= valor || undefined} />
                    ))}
                  </span>
                  <em>{valor || ''}</em>
                </li>
              );
            })}
          </ol>
        )}
        {notas && preguntas && preguntas.length > 0 && (
          <ol className={estilos.encuesta} aria-label={`Sus respuestas a la encuesta${casos.length > 1 ? `, variante ${caso.letra}` : ''}`}>
            {preguntas.map((pregunta, k) => (
              <li key={pregunta} data-postura={posturaDe(notas[k])} title={pregunta}>
                {/* Las preguntas de partida van dichas en corto; la completa aparece al pasar el cursor. */}
                <p>{corta(pregunta)}</p>
                <span aria-hidden="true">
                  {ESCALA.map((n) => (
                    <i key={n} data-lleno={n <= notas[k] || undefined} />
                  ))}
                </span>
                <em>{notas[k]}</em>
              </li>
            ))}
          </ol>
        )}
        <ul className={estilos.datos}>
          {datos(agente.atributos).map((dato) => (
            <li key={dato}>{dato}</li>
          ))}
        </ul>
        <p className={estilos.fuente}>Persona de la muestra del Censo 2024 · datos de Casen 2024 y opiniones de la CEP 96 imputados</p>
      </div>
    </aside>
  );
}
