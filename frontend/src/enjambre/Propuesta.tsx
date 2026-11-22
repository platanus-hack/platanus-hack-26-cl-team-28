import { useCallback, useEffect, useId, useLayoutEffect, useRef, useState, type PointerEvent } from 'react';
import { createPortal } from 'react-dom';
import estilos from './Propuesta.module.css';

interface Props {
  letra: string;
  /** Lo que se muestra en grande y se corta a unas pocas líneas. */
  titulo: string;
  /** El texto completo que leyeron los agentes. */
  texto: string;
}

/** El signo de porcentaje no se separa de su número al cortar la línea. */
const sinCorte = (texto: string) => texto.replace(/(\d) %/g, '$1 %');

/** La lectura se superpone al título y conserva la variante que estaba visible al abrirla. */
export function Propuesta({ letra, titulo, texto }: Props) {
  const id = useId();
  const boton = useRef<HTMLButtonElement>(null);
  const panel = useRef<HTMLElement>(null);
  const contenido = useRef<HTMLParagraphElement>(null);
  const enfocar = useRef(false);
  const puntero = useRef<{ x: number; y: number } | null>(null);
  const hoverSuspendido = useRef(false);
  const [lectura, setLectura] = useState<{ letra: string; texto: string; fija: boolean } | null>(null);
  const completo = texto || titulo;
  const visible = lectura !== null;

  const abrir = (fija: boolean) => {
    setLectura((actual) => actual ? (fija && !actual.fija ? { ...actual, fija } : actual) : { letra, texto: completo, fija });
  };

  const contiene = useCallback((destino: EventTarget | null) =>
    destino instanceof Node && (boton.current?.contains(destino) || panel.current?.contains(destino)), []);

  const cerrar = useCallback(() => {
    const origen = boton.current;
    const punto = puntero.current;
    if (origen && punto && (panel.current?.matches(':hover') || origen.matches(':hover'))) {
      const rect = origen.getBoundingClientRect();
      // Al retirar la hoja, el navegador puede volver a detectar el botón bajo el mismo cursor.
      hoverSuspendido.current = punto.x >= rect.left && punto.x <= rect.right && punto.y >= rect.top && punto.y <= rect.bottom;
    }
    if (panel.current?.contains(document.activeElement)) origen?.focus({ preventScroll: true });
    setLectura(null);
  }, []);

  const registrarPuntero = (e: PointerEvent) => {
    if (e.pointerType === 'mouse') puntero.current = { x: e.clientX, y: e.clientY };
  };

  const alSalir = (e: PointerEvent) => {
    if (e.pointerType !== 'mouse' || contiene(e.relatedTarget)) return;
    hoverSuspendido.current = false;
    setLectura((actual) => actual?.fija ? actual : null);
  };

  useLayoutEffect(() => {
    const origen = boton.current;
    const hoja = panel.current;
    if (!visible || !origen || !hoja) return;

    const ubicar = () => {
      const rect = origen.getBoundingClientRect();
      const margen = 12;
      const relleno = 13;
      const ancho = Math.min(rect.width + relleno * 2, window.innerWidth - margen * 2);
      const izquierda = Math.min(Math.max(margen, rect.left - relleno), window.innerWidth - ancho - margen);
      const arriba = Math.min(Math.max(margen, rect.top - relleno), Math.max(margen, window.innerHeight - 160));
      const estilo = getComputedStyle(origen);
      if (contenido.current) {
        contenido.current.style.font = estilo.font;
        contenido.current.style.letterSpacing = estilo.letterSpacing;
      }
      hoja.style.width = `${ancho}px`;
      hoja.style.left = `${izquierda}px`;
      hoja.style.top = `${arriba}px`;
      hoja.style.setProperty('--alto-lectura', `min(26rem, ${window.innerHeight - arriba - margen}px)`);
    };
    ubicar();
    const cambios = new ResizeObserver(ubicar);
    cambios.observe(origen);
    window.addEventListener('resize', ubicar);
    window.addEventListener('scroll', ubicar, true);
    return () => {
      cambios.disconnect();
      window.removeEventListener('resize', ubicar);
      window.removeEventListener('scroll', ubicar, true);
    };
  }, [visible]);

  useLayoutEffect(() => {
    if (!lectura?.fija || !enfocar.current) return;
    contenido.current?.focus({ preventScroll: true });
    enfocar.current = false;
  }, [lectura?.fija]);

  useEffect(() => {
    if (!visible) return;
    const fuera = (e: globalThis.PointerEvent) => { if (!contiene(e.target)) cerrar(); };
    const escape = (e: KeyboardEvent) => {
      if (e.key !== 'Escape') return;
      e.preventDefault();
      cerrar();
    };
    window.addEventListener('pointerdown', fuera);
    window.addEventListener('keydown', escape, true);
    return () => {
      window.removeEventListener('pointerdown', fuera);
      window.removeEventListener('keydown', escape, true);
    };
  }, [visible, cerrar, contiene]);

  return (
    <>
      <button
        ref={boton}
        type="button"
        className={estilos.propuesta}
        aria-expanded={visible}
        aria-controls={visible ? id : undefined}
        onPointerEnter={(e) => {
          registrarPuntero(e);
          if (e.pointerType === 'mouse' && !hoverSuspendido.current) abrir(false);
        }}
        onPointerMove={registrarPuntero}
        onPointerLeave={alSalir}
        onClick={(e) => {
          if (lectura?.fija) cerrar();
          else {
            enfocar.current = e.detail === 0;
            abrir(true);
          }
        }}
      >
        <q className={estilos.titulo}>{sinCorte(titulo)}</q>
      </button>
      {lectura && createPortal(
        <aside
          ref={panel}
          id={id}
          className={estilos.hoja}
          aria-label={`Propuesta completa, variante ${lectura.letra}`}
          onPointerLeave={alSalir}
          onPointerMove={registrarPuntero}
          onPointerDown={() => abrir(true)}
          onKeyDown={(e) => e.stopPropagation()}
        >
          <p ref={contenido} className={estilos.texto} tabIndex={0}>{sinCorte(lectura.texto)}</p>
          <button type="button" className={estilos.cerrar} aria-label="Cerrar propuesta" onClick={cerrar}>
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m6 6 12 12M18 6 6 18" /></svg>
          </button>
        </aside>,
        document.body,
      )}
    </>
  );
}
