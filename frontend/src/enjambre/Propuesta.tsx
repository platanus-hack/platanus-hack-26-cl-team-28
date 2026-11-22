import { useId, useLayoutEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { PopupDialogo, type PopupHandle } from '../componentes/comunes/Popup';
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

/** El título abre la propuesta completa y la mantiene visible aunque avance la corrida. */
export function Propuesta({ letra, titulo, texto }: Props) {
  const id = useId();
  const dialogo = useRef<PopupHandle>(null);
  const [lectura, setLectura] = useState<{ letra: string; texto: string } | null>(null);
  const completo = texto || titulo;

  useLayoutEffect(() => {
    if (lectura) dialogo.current?.showModal();
  }, [lectura]);

  return (
    <>
      <button
        type="button"
        className={estilos.propuesta}
        aria-haspopup="dialog"
        aria-controls={lectura ? id : undefined}
        onClick={() => setLectura({ letra, texto: completo })}
      >
        <q className={estilos.titulo}>{sinCorte(titulo)}</q>
      </button>
      {lectura && createPortal(
        <PopupDialogo ref={dialogo} id={id} className={estilos.hoja} aria-labelledby={`${id}-titulo`} onClose={() => setLectura(null)}>
          <header className={estilos.cabecera}>
            <h2 id={`${id}-titulo`}>Propuesta completa · Variante {lectura.letra}</h2>
            <button type="button" className={estilos.cerrar} aria-label="Cerrar" onClick={() => dialogo.current?.close()}>
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m6 6 12 12M18 6 6 18" /></svg>
            </button>
          </header>
          <p className={estilos.texto} tabIndex={0}>{sinCorte(lectura.texto)}</p>
        </PopupDialogo>,
        document.body,
      )}
    </>
  );
}
