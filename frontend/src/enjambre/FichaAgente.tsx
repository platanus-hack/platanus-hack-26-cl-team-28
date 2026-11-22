import { useEffect, useRef, useState } from 'react';
import { PopupFlotante } from '../componentes/comunes/Popup';
import { REGIONES } from '../dominio/catalogos';
import type { AgenteRemoto } from '../vivo/api';
import { corta, midePostura } from '../vivo/encuesta';
import { posturaDe, type CasoVivo } from '../vivo/useEnVivo';
import { FiguraWati } from './FiguraWati';
import { rasgosDe } from './wati';
import estilos from './FichaAgente.module.css';
import { useMovil } from './useAngosto';
import { quienEs } from './Voces';

interface Props {
  agente: AgenteRemoto;
  casos: CasoVivo[];
  viendo: number;
  x: number;
  y: number;
  /** Las preguntas de la encuesta, en el orden de las notas. */
  preguntas?: readonly string[];
  alCerrar(): void;
}

const ANCHO = 380;
const POSTURA = { favor: 'A favor', contra: 'En contra', indecisa: 'No se decide' } as const;
const ESCALA = [1, 2, 3, 4, 5, 6, 7];

/** Etiquetas e iconos para dar contexto a cada atributo del perfil. */
const DATOS: { clave: string; etiqueta: string; icono: string }[] = [
  { clave: 'Nivel educacional', etiqueta: 'Educación', icono: 'M2 8l10-5 10 5-10 5L2 8zm4 2.5V15c3 2 9 2 12 0v-4.5M22 8v6' },
  { clave: 'Situación laboral', etiqueta: 'Trabajo', icono: 'M3 8h18v12H3zM8 8V5h8v3M3 13h18' },
  { clave: 'Tipo de colegio', etiqueta: 'Colegio', icono: 'M3 21V8l9-5 9 5v13M2 21h20M9 21v-6h6v6M9 10h.01M15 10h.01' },
  { clave: 'Tramo socioeconómico', etiqueta: 'Ingresos', icono: 'M3 6h18v12H3zM3 10h18M7 15h4' },
  { clave: 'Previsión de salud', etiqueta: 'Salud', icono: 'M12 3v18M3 12h18' },
  { clave: 'Tipo de hogar', etiqueta: 'Hogar', icono: 'M3 11l9-8 9 8M5 10v11h14V10M9 21v-6h6v6' },
  { clave: 'Menores en el hogar', etiqueta: 'Menores en el hogar', icono: 'M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zm-7 10a7 7 0 0 1 14 0' },
  { clave: 'Tenencia de la vivienda', etiqueta: 'Vivienda', icono: 'M3 11l9-8 9 8M5 10v11h14V10M9 21v-6h6v6' },
  { clave: 'Religión', etiqueta: 'Religión', icono: 'M12 3v18M7 8h10M5 21h14' },
  { clave: 'Posición política', etiqueta: 'Posición política', icono: 'M4 12h16M8 8l-4 4 4 4M16 8l4 4-4 4' },
  { clave: 'Evaluación del gobierno', etiqueta: 'Gobierno', icono: 'M3 9l9-6 9 6H3zm2 2v7m5-7v7m4-7v7m5-7v7M3 21h18' },
];

/**
 * La persona detrás de un punto, como una credencial: su wati y su postura en la franja
 * de color, lo que dijo, cuánto apoyó cada variante en la misma escala de 1 a 7 que respondió,
 * y lo que el censo sabe de ella.
 */
export function FichaAgente({ agente, casos, viendo, x, y, preguntas, alCerrar }: Props) {
  const caja = useRef<HTMLElement>(null);
  const movil = useMovil();
  const cierre = useRef<number | undefined>(undefined);
  const [abierta, setAbierta] = useState(true);
  const cerrar = () => {
    window.clearTimeout(cierre.current);
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      alCerrar();
    } else {
      setAbierta(false);
      cierre.current = window.setTimeout(alCerrar, 220);
    }
  };
  useEffect(() => {
    window.clearTimeout(cierre.current);
    setAbierta(true);
  }, [agente.id]);
  useEffect(() => () => window.clearTimeout(cierre.current), []);
  useEffect(() => {
    caja.current?.focus({ preventScroll: true });
    const tecla = (e: KeyboardEvent) => e.key === 'Escape' && cerrar();
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
    <PopupFlotante
      as="aside"
      abierto={abierta}
      ref={caja}
      tabIndex={-1}
      className={estilos.ficha}
      data-postura={postura}
      // En el teléfono no va junto al punto: es una tarjeta abajo, a todo el ancho (ver la hoja de estilos).
      style={movil ? undefined : { left: izquierda, top: arriba, width: ANCHO, maxHeight: window.innerHeight - arriba - 16 }}
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
        <button type="button" className={estilos.cerrar} onClick={cerrar} aria-label="Cerrar">
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
              <li key={pregunta} data-postura={midePostura(pregunta) ? posturaDe(notas[k]) : undefined} title={pregunta}>
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
        <section aria-label="Perfil de la persona" className={estilos.perfil}>
          <h3>Perfil de la persona</h3>
          <ul className={estilos.datos}>
            {DATOS.filter(({ clave }) => agente.atributos[clave] && !(clave === 'Evaluación del gobierno' && agente.atributos[clave] === 'Sin respuesta')).map(({ clave, etiqueta, icono }) => (
              <li key={clave}>
                <svg viewBox="0 0 24 24" aria-hidden="true"><path d={icono} /></svg>
                <div><span>{etiqueta}</span><strong>{agente.atributos[clave]}</strong></div>
              </li>
            ))}
          </ul>
        </section>
        <p className={estilos.fuente}>Persona de la muestra del Censo 2024 · datos de Casen 2024 y opiniones de la CEP 96 imputados</p>
      </div>
    </PopupFlotante>
  );
}
