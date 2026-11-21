import { forwardRef, useEffect, useImperativeHandle, useRef, type ComponentPropsWithoutRef, type HTMLAttributes } from 'react';
import estilos from './Popup.module.css';

/** Conserva la API de dialog nativo y espera la salida antes de cerrar el top layer. */
export interface PopupHandle {
  readonly open: boolean;
  showModal(): void;
  close(): void;
}

const DURACION = 220;

export const PopupDialogo = forwardRef<PopupHandle, ComponentPropsWithoutRef<'dialog'>>(function PopupDialogo(
  { className, onCancel, children, ...props }, ref,
) {
  const dialogo = useRef<HTMLDialogElement>(null);
  const espera = useRef<number | undefined>(undefined);

  const cerrar = () => {
    const actual = dialogo.current;
    if (!actual?.open) return;
    window.clearTimeout(espera.current);
    delete actual.dataset.visible;
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      actual.close();
    } else {
      espera.current = window.setTimeout(() => actual.close(), DURACION);
    }
  };

  useImperativeHandle(ref, () => ({
    get open() { return dialogo.current?.open ?? false; },
    showModal() {
      const actual = dialogo.current;
      if (!actual) return;
      window.clearTimeout(espera.current);
      if (!actual.open) {
        actual.showModal();
        // Confirma el estado oculto antes de iniciar la transición de entrada.
        actual.getBoundingClientRect();
      }
      actual.dataset.visible = 'true';
    },
    close: cerrar,
  }));

  useEffect(() => () => window.clearTimeout(espera.current), []);

  return (
    <dialog
      {...props}
      ref={dialogo}
      className={`${estilos.popup} ${estilos.dialogo} ${className ?? ''}`}
      onCancel={(e) => {
        onCancel?.(e);
        if (!e.defaultPrevented) {
          e.preventDefault();
          cerrar();
        }
      }}
    >
      {children}
    </dialog>
  );
});

/** Superficie contextual no modal: permanece montada para poder invertir su transición. */
export const PopupFlotante = forwardRef<HTMLElement, HTMLAttributes<HTMLElement> & { abierto: boolean; lateral?: boolean; as?: 'aside' | 'div' }>(
  function PopupFlotante({ as: Tag = 'div', abierto, lateral, className, children, ...props }, ref) {
    const asignarRef = (elemento: HTMLElement | null) => {
      if (typeof ref === 'function') ref(elemento);
      else if (ref) ref.current = elemento;
    };
    return (
      <Tag
        {...props}
        ref={asignarRef}
        className={`${estilos.popup} ${estilos.flotante} ${lateral ? estilos.lateral : ''} ${className ?? ''}`}
        data-visible={abierto || undefined}
        aria-hidden={!abierto || undefined}
        inert={!abierto || undefined}
      >
        {children}
      </Tag>
    );
  },
);
