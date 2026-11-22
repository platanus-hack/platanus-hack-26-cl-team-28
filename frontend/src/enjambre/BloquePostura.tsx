import { useLayoutEffect, useRef, useState } from 'react';
import { POSTURA_TEXTO } from '../contenido';
import { personasAprox } from '../dominio/textos';
import type { RasgoVoto } from '../vivo/analisis';
import { rebotarWati } from './animarWati';
import estilos from './BloquePostura.module.css';
import { ConRasgos } from './ConRasgos';
import { FiguraWati } from './FiguraWati';
import { useConteo } from './useConteo';
import { CELDA_ALTO, CELDA_ANCHO, rasgosDe, TONOS, VARIANTES } from './wati';

interface Props {
  postura: 'favor' | 'contra';
  porcentaje: number;
  personas: number;
  aspecto: number;
  /** Las características que más distinguen a este lado: un wati por cada una. */
  rasgos?: RasgoVoto[];
  /** Línea grande sobre la cifra, por ejemplo cuánto ganó una variante contra la A. */
  encabezado?: string;
  /** Una línea chica bajo el encabezado. */
  nota?: string;
  /** Qué se cuenta: personas simuladas o agentes. */
  unidad?: string;
  /** A cuántas personas de la población equivale cada uno de lo que se cuenta; sin él no se dice. */
  porAgente?: number | null;
  /** En pantallas angostas el wati no crece: no hay lugar. */
  compacto?: boolean;
  /** Si un rectángulo de la pantalla tapa puntos o rótulos del mapa: al costado, los watis no deben. */
  tapaMapa?(rect: DOMRect): boolean;
  /** Cambian cuando el mapa reubica sus burbujas o se acerca: hay que volver a revisar. */
  revisionMapa?: unknown;
  zoomMapa?: number;
}

/** Alto de cada wati respecto del primero: el de la característica más marcada va adelante y más grande. */
const PROPORCION = [1, 0.8, 0.68];
/** Cuánto se corre el adorno de cada wati: con 7 y 14 sobre 24 ninguno repite cabeza. */
const SALTO_ADORNO = 7;
/** Separación entre la cifra y los watis, y entre un wati y otro (var(--e3) y var(--e1)). */
const ESPACIO_FILA = 12;
const ESPACIO_WATIS = 4;
/** Alto del wati principal respecto de la cifra: el wati deja aire arriba para respirar (ver FiguraWati). */
const RESPECTO_CIFRA = 1.12;
/** Parte del ancho de la ventana que puede ocupar el bloque, desde su borde: hasta ahí no llegan las regiones del mapa. */
const ALCANCE = 0.3;
/** Tope del tamaño de la cifra, en rem (el máximo del `clamp` de `.cifra` en BloquePostura.module.css). */
const CIFRA_MAXIMA_REM = 11;

/** La cifra de un lado del país y los watis que cuentan quiénes marcan esa postura. */
export function BloquePostura({ postura, porcentaje, personas, aspecto, rasgos = [], unidad = 'personas', porAgente, compacto = false, encabezado, nota, tapaMapa, revisionMapa, zoomMapa }: Props) {
  const bloque = useRef<HTMLElement>(null);
  const cifra = useRef<HTMLParagraphElement>(null);
  const conPersonas = useRef<HTMLDivElement>(null);
  const watis = useRef<HTMLDivElement>(null);
  const figuras = useRef<(HTMLSpanElement | null)[]>([]);
  const [medidas, setMedidas] = useState({ ancho: 0, columna: 0, altoCifra: 0, anchoCifra: 0, grande: false });
  const contado = useConteo(porcentaje);
  const base = rasgosDe(`${postura}#${aspecto}`);
  // Sin rasgos todavía (pocas respuestas o ninguna diferencia clara) queda el wati de siempre.
  const lista: (RasgoVoto | undefined)[] = rasgos.length ? rasgos.slice(0, PROPORCION.length) : [undefined];

  // Mientras la cifra está en su tamaño máximo hay alto de sobra y los watis van debajo de ella;
  // cuando la pantalla la achica, van a su lado, del alto de ella. Se mide cuánto mide y cuánto lugar queda.
  useLayoutEffect(() => {
    const caja = bloque.current;
    const numero = cifra.current;
    const junto = conPersonas.current;
    if (!caja || !numero || !junto) return;
    const medir = () =>
      setMedidas((antes) => {
        const rem = parseFloat(getComputedStyle(document.documentElement).fontSize) || 16;
        const ahora = {
          // En pantallas anchas la columna topa antes que el mapa: al lado, los watis pueden salirse de ella hasta ALCANCE.
          ancho: Math.max(caja.clientWidth, Math.round(innerWidth * ALCANCE)),
          // Debajo no: ahí el mapa puede llegar hasta el borde de la columna.
          columna: caja.clientWidth,
          altoCifra: numero.offsetHeight,
          // Los watis van al lado de la cifra con su línea de personas, que puede ser más ancha.
          anchoCifra: junto.offsetWidth,
          grande: !compacto && parseFloat(getComputedStyle(numero).fontSize) >= CIFRA_MAXIMA_REM * rem - 0.5,
        };
        return (Object.keys(ahora) as (keyof typeof ahora)[]).every((k) => ahora[k] === antes[k]) ? antes : ahora;
      });
    medir();
    const observador = new ResizeObserver(medir);
    observador.observe(caja);
    observador.observe(numero);
    observador.observe(junto);
    addEventListener('resize', medir);
    return () => {
      observador.disconnect();
      removeEventListener('resize', medir);
    };
  }, [compacto]);

  // Aun con la cifra achicada, al costado no pueden tapar el mapa: si lo tapan, también van debajo.
  const [tapan, setTapan] = useState(false);
  const apilado = medidas.grande || tapan;
  // Ambas posturas usan el mismo tamaño; si no caben, los watis se achican juntos.
  const escalaWati = compacto ? 1 : 0.85;
  const deseado = (medidas.altoCifra || 90) * RESPECTO_CIFRA * escalaWati;
  const proporciones = PROPORCION.slice(0, lista.length);
  const anchoWatis = (deseado * CELDA_ANCHO * proporciones.reduce((a, b) => a + b, 0)) / CELDA_ALTO + ESPACIO_WATIS * (lista.length - 1);
  const lugar = apilado ? medidas.columna : medidas.ancho - medidas.anchoCifra - ESPACIO_FILA;
  const alto = Math.max(32, Math.round(deseado * (medidas.ancho && lugar < anchoWatis ? Math.max(0, lugar) / anchoWatis : 1)));

  useLayoutEffect(() => {
    if (medidas.grande || compacto || !tapaMapa) {
      setTapan(false);
      return;
    }
    const comprobar = () => {
      const junto = conPersonas.current?.getBoundingClientRect();
      if (!junto) return;
      const disponible = Math.max(0, medidas.ancho - medidas.anchoCifra - ESPACIO_FILA);
      const escala = Math.min(1, disponible / Math.max(1, anchoWatis));
      const ancho = anchoWatis * escala;
      const altoLateral = Math.max(32, deseado * escala);
      // Los watis se paran en el pie de la cifra con su línea de personas. Si ahora están debajo, el
      // bloque (centrado en su columna) es más alto y la cifra subió la mitad de lo que ocupan.
      const subio = bloque.current?.dataset.apilado !== undefined ? ((watis.current?.offsetHeight ?? 0) + ESPACIO_FILA) / 2 : 0;
      const pie = junto.bottom + subio;
      const x = postura === 'favor' ? junto.left - ESPACIO_FILA - ancho : junto.right + ESPACIO_FILA;
      setTapan(x < 0 || x + ancho > innerWidth || tapaMapa(new DOMRect(x, pie - altoLateral, ancho, altoLateral)));
    };
    // Una vez ya puesto el diseño y de nuevo cuando las burbujas terminaron de acomodarse.
    const cuadro = requestAnimationFrame(comprobar);
    const espera = window.setTimeout(comprobar, 350);
    addEventListener('resize', comprobar);
    return () => {
      cancelAnimationFrame(cuadro);
      clearTimeout(espera);
      removeEventListener('resize', comprobar);
    };
  }, [tapaMapa, revisionMapa, zoomMapa, compacto, postura, medidas.grande, medidas.ancho, medidas.anchoCifra, anchoWatis, deseado]);

  return (
    <section ref={bloque} className={estilos.bloque} data-postura={postura} data-compacto={compacto || undefined} data-apilado={apilado || undefined} aria-label={`${porcentaje} % ${POSTURA_TEXTO[postura]}`}>
      <p className={estilos.nombre}>{POSTURA_TEXTO[postura]}</p>
      <div className={estilos.fila}>
      <div ref={conPersonas} className={estilos.cifraConPersonas}>
      <p ref={cifra} className={estilos.cifra} aria-hidden="true">
        {Math.round(contado)}
        <span>%</span>
      </p>
      {porAgente ? <p className={estilos.personas}>≈ {personasAprox(personas * porAgente)}</p> : null}
      </div>
      <div ref={watis} className={estilos.watis}>
        {lista.map((rasgo, k) => {
          // El primero es el wati de siempre; los otros cambian de cabeza, de tono y de ritmo.
          const propios = k ? { semilla: rasgosDe(`${postura}#${aspecto}#${k}`).semilla, variante: (base.variante + k * SALTO_ADORNO) % VARIANTES, tono: (base.tono + k) % TONOS } : base;
          return (
            <ConRasgos key={k} rasgos={rasgo ? [rasgo] : []} postura={postura} unidad={unidad} porAgente={porAgente} hacia={postura === 'favor' ? 'izquierda' : 'derecha'}>
              {(descrito) => (
                <button
                  type="button"
                  className={estilos.botonWati}
                  aria-label={rasgo ? `${rasgo.grupo}: ${rasgo.parte} % ${POSTURA_TEXTO[postura]}` : `Animar al wati ${POSTURA_TEXTO[postura]}`}
                  aria-describedby={descrito}
                  onClick={() => {
                    const figura = figuras.current[k];
                    if (figura) rebotarWati(figura);
                  }}
                >
                  <span ref={(nodo) => void (figuras.current[k] = nodo)} className={estilos.figura}>
                    <FiguraWati estado={postura} rasgos={propios} alto={Math.round(alto * PROPORCION[k])} />
                  </span>
                </button>
              )}
            </ConRasgos>
          );
        })}
      </div>
      </div>
      {encabezado && (
        <p className={estilos.encabezado} data-baja={encabezado.startsWith('-') || undefined}>
          {encabezado}
        </p>
      )}
      {nota && <p className={estilos.nota}>{nota}</p>}
    </section>
  );
}
