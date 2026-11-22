import { useCallback, useEffect, useId, useLayoutEffect, useRef, useState, type CSSProperties, type FocusEvent, type KeyboardEvent, type PointerEvent, type ReactNode } from 'react';
import { acotar, alturas, elegirTope, vecino, type Alturas, type Tope } from './hoja';
import estilos from './HojaInferior.module.css';

interface Props {
  tope: Tope;
  alCambiar(tope: Tope): void;
  /** Lo que siempre queda a la vista, sobre el borde de abajo. */
  asomo: ReactNode;
  /** El resto, que aparece al subir la hoja. */
  children: ReactNode;
  /** Nombre de la región para lectores de pantalla. */
  etiqueta: string;
  /** Cuánto tapa la barra de arriba: la hoja completa llega hasta ahí. */
  arriba: number;
  /** Avisa cuánto asoma la hoja cuando queda quieta en un tope. */
  alAsentar?(visible: number, a: Alturas): void;
}

/** Lo que dura la transición entre topes (HojaInferior.module.css). */
const TRANSICION_MS = 280;
/** Cuánto hay que mover el dedo para que un toque pase a ser un arrastre. */
const UMBRAL_ARRASTRE = 6;

/** Cuánto ocupa el teclado del teléfono: con él abierto, la hoja sube sobre él (ver HojaInferior.module.css). */
function useTeclado(): number {
  const [teclado, setTeclado] = useState(0);
  useEffect(() => {
    const vista = window.visualViewport;
    if (!vista) return;
    const medir = () => {
      const alto = Math.max(0, Math.round(innerHeight - vista.height - vista.offsetTop));
      // Las barras del navegador que aparecen y desaparecen no son el teclado.
      setTeclado(alto > 80 ? alto : 0);
    };
    medir();
    vista.addEventListener('resize', medir);
    vista.addEventListener('scroll', medir);
    return () => {
      vista.removeEventListener('resize', medir);
      vista.removeEventListener('scroll', medir);
    };
  }, []);
  return teclado;
}

/**
 * La hoja de abajo en el teléfono. Se arrastra desde su asa o desde lo que asoma, y queda en uno de
 * tres topes. Sin arrastrar también se maneja: el asa es un botón (clic, flechas, Inicio y Fin).
 * No es modal: el mapa de arriba sigue a mano.
 */
export function HojaInferior({ tope, alCambiar, asomo, children, etiqueta, arriba, alAsentar }: Props) {
  const idCuerpo = useId();
  const hoja = useRef<HTMLElement>(null);
  const cabeza = useRef<HTMLDivElement>(null);
  const cuerpo = useRef<HTMLDivElement>(null);
  const asa = useRef<HTMLButtonElement>(null);
  const teclado = useTeclado();
  const [medidas, setMedidas] = useState({ asomo: 0, ventana: 0 });
  const a = alturas({ asomo: medidas.asomo, ventana: medidas.ventana, barra: arriba });
  const gesto = useRef<{ id: number; y0: number; v0: number; arrastra: boolean; muestras: { t: number; v: number }[] } | null>(null);
  const recienArrastrada = useRef(false);

  // Lo que asoma es la cabeza: el asa, el resumen y la franja de la barra de inicio del teléfono.
  useLayoutEffect(() => {
    const medir = () => {
      const alto = cabeza.current?.offsetHeight ?? 0;
      const ventana = Math.round(window.visualViewport?.height ?? innerHeight);
      setMedidas((antes) => (antes.asomo === alto && antes.ventana === ventana ? antes : { asomo: alto, ventana }));
    };
    medir();
    const observador = new ResizeObserver(medir);
    if (cabeza.current) observador.observe(cabeza.current);
    addEventListener('resize', medir);
    window.visualViewport?.addEventListener('resize', medir);
    return () => {
      observador.disconnect();
      removeEventListener('resize', medir);
      window.visualViewport?.removeEventListener('resize', medir);
    };
  }, []);

  const poner = useCallback((visible: number) => hoja.current?.style.setProperty('--visible', `${Math.round(visible)}px`), []);

  // El tope manda salvo mientras se arrastra: ahí la altura la lleva el dedo.
  useLayoutEffect(() => {
    if (!gesto.current?.arrastra) poner(a[tope]);
    // Lo que queda arriba de la hoja en reposo (la franja de voces se apoya ahí). No se toca al arrastrar.
    document.documentElement.style.setProperty('--alto-hoja', `${a[tope]}px`);
  }, [tope, a.asomo, a.mitad, a.completa, poner]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => () => void document.documentElement.style.removeProperty('--alto-hoja'), []);

  // Con la hoja quieta se avisa cuánto asoma, para que el mapa se acomode al espacio que queda. La
  // primera vez, de inmediato: el mapa todavía no se dibujó y no hay transición que esperar.
  const asentada = useRef(false);
  useEffect(() => {
    if (!medidas.asomo) return;
    const espera = window.setTimeout(() => {
      asentada.current = true;
      alAsentar?.(a[tope], a);
    }, asentada.current ? TRANSICION_MS + 20 : 0);
    return () => window.clearTimeout(espera);
  }, [tope, a.asomo, a.mitad, a.completa, alAsentar]); // eslint-disable-line react-hooks/exhaustive-deps

  // Lo que asoma también lo usan otros (el botón «Ver todo», la ficha de una persona) para quedar encima.
  useLayoutEffect(() => {
    const raiz = document.documentElement.style;
    raiz.setProperty('--alto-asomo', `${medidas.asomo}px`);
    return () => void raiz.removeProperty('--alto-asomo');
  }, [medidas.asomo]);

  /** Al plegarla, el foco no se queda en algo que ya no se ve: pasa al asa. */
  const cambiar = useCallback(
    (destino: Tope) => {
      if (destino === 'asomo' && cuerpo.current?.contains(document.activeElement)) asa.current?.focus({ preventScroll: true });
      alCambiar(destino);
    },
    [alCambiar],
  );

  const bajar = (e: PointerEvent<HTMLDivElement>) => {
    if (e.pointerType === 'mouse' && e.button !== 0) return;
    const visible = parseFloat(hoja.current?.style.getPropertyValue('--visible') ?? '') || a[tope];
    gesto.current = { id: e.pointerId, y0: e.clientY, v0: visible, arrastra: false, muestras: [{ t: e.timeStamp, v: visible }] };
  };

  const mover = (e: PointerEvent<HTMLDivElement>) => {
    const g = gesto.current;
    if (!g || g.id !== e.pointerId) return;
    const dy = e.clientY - g.y0;
    if (!g.arrastra) {
      if (Math.abs(dy) < UMBRAL_ARRASTRE) return;
      g.arrastra = true;
      cabeza.current?.setPointerCapture(e.pointerId);
      hoja.current?.setAttribute('data-arrastrando', '');
    }
    const visible = acotar(a, g.v0 - dy);
    poner(visible);
    g.muestras.push({ t: e.timeStamp, v: visible });
    if (g.muestras.length > 5) g.muestras.shift();
  };

  const soltar = (e: PointerEvent<HTMLDivElement>) => {
    const g = gesto.current;
    if (!g || g.id !== e.pointerId) return;
    gesto.current = null;
    if (!g.arrastra) return;
    hoja.current?.removeAttribute('data-arrastrando');
    recienArrastrada.current = true;
    window.setTimeout(() => (recienArrastrada.current = false), 0);
    const primera = g.muestras[0];
    const ultima = g.muestras[g.muestras.length - 1];
    const velocidad = ultima.t > primera.t ? (ultima.v - primera.v) / (ultima.t - primera.t) : 0;
    const destino = elegirTope(a, ultima.v, velocidad);
    // Si vuelve al mismo tope no hay cambio de estado que lo reubique: se reubica aquí.
    poner(a[destino]);
    cambiar(destino);
  };

  const teclas = (e: KeyboardEvent<HTMLButtonElement>) => {
    const destino = e.key === 'ArrowUp' ? vecino(tope, 1) : e.key === 'ArrowDown' ? vecino(tope, -1) : e.key === 'Home' ? 'asomo' : e.key === 'End' ? 'completa' : null;
    if (!destino) return;
    e.preventDefault();
    cambiar(destino);
  };

  // Al escribir, la hoja sube entera: el teclado tapa la mitad de abajo de la pantalla.
  const alEnfocar = (e: FocusEvent<HTMLDivElement>) => {
    if (e.target instanceof HTMLTextAreaElement || (e.target instanceof HTMLInputElement && !['checkbox', 'radio', 'range', 'button'].includes(e.target.type))) {
      if (tope !== 'completa') cambiar('completa');
    }
  };

  const abierta = tope !== 'asomo';
  return (
    <section
      ref={hoja}
      className={estilos.hoja}
      aria-label={etiqueta}
      data-tope={tope}
      style={{ '--alto-completa': `${a.completa}px`, '--teclado': `${teclado}px` } as CSSProperties}
    >
      <div
        ref={cabeza}
        className={estilos.cabeza}
        onPointerDown={bajar}
        onPointerMove={mover}
        onPointerUp={soltar}
        onPointerCancel={soltar}
        onClickCapture={(e) => {
          // El clic que sigue a un arrastre no aprieta lo que quedó bajo el dedo.
          if (!recienArrastrada.current) return;
          e.preventDefault();
          e.stopPropagation();
        }}
      >
        <button
          ref={asa}
          type="button"
          className={estilos.asa}
          aria-expanded={abierta}
          aria-controls={idCuerpo}
          aria-label={abierta ? 'Mostrar menos' : 'Mostrar más'}
          onClick={() => cambiar(abierta ? 'asomo' : 'mitad')}
          onKeyDown={teclas}
        >
          <span aria-hidden="true" />
        </button>
        <div className={estilos.asomo}>{asomo}</div>
      </div>
      <div id={idCuerpo} ref={cuerpo} className={estilos.cuerpo} inert={!abierta || undefined} onFocus={alEnfocar}>
        {children}
      </div>
    </section>
  );
}
