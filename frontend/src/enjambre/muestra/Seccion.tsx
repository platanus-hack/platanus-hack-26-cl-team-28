import { useId, type ReactNode } from 'react';
import estilos from './Seccion.module.css';

interface Props {
  titulo: string;
  /** Lo que se lee con la sección cerrada: qué hay elegido adentro. */
  resumen?: string;
  /** De dónde vienen los datos de la sección. */
  fuente?: string;
  abierta: boolean;
  alAlternar(): void;
  children: ReactNode;
}

/** Una sección del cajón que se pliega: el título es el botón. */
export function Seccion({ titulo, resumen, fuente, abierta, alAlternar, children }: Props) {
  const id = useId();
  return (
    <section className={estilos.seccion}>
      <h3>
        <button type="button" aria-expanded={abierta} aria-controls={id} onClick={alAlternar}>
          <span>{titulo}</span>
          {resumen && <small>{resumen}</small>}
          <svg viewBox="0 0 12 8" aria-hidden="true">
            <path d="M1 1.5l5 5 5-5" />
          </svg>
        </button>
      </h3>
      <div id={id} className={estilos.contenido} hidden={!abierta}>
        {children}
        {fuente && <p className={estilos.fuente}>{fuente}</p>}
      </div>
    </section>
  );
}
