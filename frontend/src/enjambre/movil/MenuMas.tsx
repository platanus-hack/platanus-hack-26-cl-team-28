import { useCallback, useEffect, useId, useRef, useState } from 'react';
import { PopupFlotante } from '../../componentes/comunes/Popup';
import type { EnVivo } from '../../vivo/useEnVivo';
import { useMenuHistorial } from '../MenuHistorial';
import { useMenuOpciones } from '../MenuOpciones';
import estilos from './MenuMas.module.css';

interface Props {
  sim: EnVivo;
  claro: boolean;
  alCambiarTema(): void;
  /** Sin motor no hay historial: en la demostración no se ofrece. */
  conHistorial: boolean;
  alUsarHistorial(textos: string[]): void;
  alVerHistorial(id: string): Promise<string | null>;
}

/**
 * En el teléfono, las utilidades de la esquina caben en un solo botón: tema, historial, opciones de
 * la muestra y, mientras corre, detener. Los cajones se montan fuera del menú, que se cierra al abrirlos.
 */
export function MenuMas({ sim, claro, alCambiarTema, conHistorial, alUsarHistorial, alVerHistorial }: Props) {
  const id = useId();
  const [abierto, setAbierto] = useState(false);
  const caja = useRef<HTMLDivElement>(null);
  const boton = useRef<HTMLButtonElement>(null);
  const devolverFoco = useCallback(() => boton.current?.focus(), []);
  const historial = useMenuHistorial({ alUsar: alUsarHistorial, alVer: alVerHistorial, devolverFoco });
  const opciones = useMenuOpciones(sim, devolverFoco);
  const corriendo = sim.fase === 'corriendo';

  useEffect(() => {
    if (!abierto) return;
    const fuera = (e: PointerEvent) => {
      if (!caja.current?.contains(e.target as Node)) setAbierto(false);
    };
    const escape = (e: KeyboardEvent) => {
      if (e.key !== 'Escape') return;
      setAbierto(false);
      boton.current?.focus();
    };
    window.addEventListener('pointerdown', fuera);
    window.addEventListener('keydown', escape);
    return () => {
      window.removeEventListener('pointerdown', fuera);
      window.removeEventListener('keydown', escape);
    };
  }, [abierto]);

  /** Cada opción cierra el menú antes de hacer lo suyo. */
  const elegir = (accion: () => void) => () => {
    setAbierto(false);
    accion();
  };

  return (
    <>
      <div ref={caja} className={estilos.menu}>
        <button
          ref={boton}
          type="button"
          className={estilos.boton}
          aria-label="Más opciones"
          aria-expanded={abierto}
          aria-controls={id}
          onClick={() => setAbierto((valor) => !valor)}
        >
          <svg viewBox="0 0 20 20" aria-hidden="true">
            <circle cx="4.5" cy="10" r="1.6" />
            <circle cx="10" cy="10" r="1.6" />
            <circle cx="15.5" cy="10" r="1.6" />
          </svg>
        </button>
        <PopupFlotante abierto={abierto} id={id} className={estilos.lista} role="group" aria-label="Más opciones">
          <button type="button" role="switch" aria-checked={claro} onClick={alCambiarTema}>
            <span>Tema claro</span>
            <span className={estilos.interruptor} aria-hidden="true" />
          </button>
          {corriendo && (
            <button type="button" onClick={elegir(sim.detener)}>
              Detener la simulación
            </button>
          )}
          {!corriendo && conHistorial && (
            <button type="button" aria-controls="cajon-historial" onClick={elegir(historial.abrir)}>
              Historial
            </button>
          )}
          {!corriendo && (
            <button type="button" disabled={opciones.bloqueado} aria-controls="cajon-muestra" onClick={elegir(opciones.abrir)}>
              Opciones de la muestra
            </button>
          )}
        </PopupFlotante>
      </div>
      {historial.cajon}
      {opciones.cajon}
    </>
  );
}
