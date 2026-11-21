import { useEffect, useRef } from 'react';
import { ENCUESTA } from '../vivo/encuesta';
import estilos from './CajonEncuesta.module.css';

interface Props {
  alCerrar(): void;
}

/**
 * La encuesta que responde cada agente, para leerla: qué se pregunta, en qué orden y qué
 * significan el 1 y el 7 en cada pregunta. Es fija: no se edita. Un cajón a todo el alto, como
 * el de la muestra.
 */
export function CajonEncuesta({ alCerrar }: Props) {
  const caja = useRef<HTMLElement>(null);

  useEffect(() => {
    caja.current?.focus();
    const tecla = (e: KeyboardEvent) => e.key === 'Escape' && alCerrar();
    const fuera = (e: PointerEvent) => !caja.current?.contains(e.target as Node) && alCerrar();
    window.addEventListener('keydown', tecla);
    // En el siguiente ciclo: el clic que abrió el cajón no debe cerrarlo.
    const escucha = window.setTimeout(() => window.addEventListener('pointerdown', fuera), 0);
    return () => {
      window.clearTimeout(escucha);
      window.removeEventListener('keydown', tecla);
      window.removeEventListener('pointerdown', fuera);
    };
  }, [alCerrar]);

  return (
    <aside ref={caja} tabIndex={-1} className={estilos.cajon} id="cajon-encuesta" aria-label="Encuesta">
      <header className={estilos.cabeza}>
        <div className={estilos.cuenta}>
          <span>ENCUESTA · {ENCUESTA.length} PREGUNTAS</span>
          <h2>Lo que preguntamos</h2>
          <p>Cada persona responde cada pregunta con un número del 1 al 7. Cada pregunta tiene su propia escala.</p>
        </div>
        <button type="button" className={estilos.cerrar} onClick={alCerrar} aria-label="Cerrar">
          <svg viewBox="0 0 12 12" aria-hidden="true">
            <path d="M2 2l8 8M10 2l-8 8" />
          </svg>
        </button>
      </header>

      <div className={estilos.cuerpo}>
        <ol className={estilos.preguntas}>
          {ENCUESTA.map((pregunta, k) => (
            <li key={pregunta.texto}>
              <span className={estilos.numero} aria-hidden="true">{k + 1}</span>
              <div className={estilos.pregunta}>
                <h3>{pregunta.nombre}</h3>
                <p>{pregunta.texto}</p>
                <dl className={estilos.escala} aria-label="Escala">
                  <div>
                    <dt>1</dt>
                    <dd>{pregunta.minimo}</dd>
                  </div>
                  <div>
                    <dt>7</dt>
                    <dd>{pregunta.maximo}</dd>
                  </div>
                </dl>
              </div>
            </li>
          ))}
        </ol>
        <p className={estilos.ayuda}>
          La encuesta es fija: todas las personas responden estas cinco preguntas en cada corrida. La primera es la que separa a quienes
          están a favor de quienes están en contra, y el índice de aceptación es la media de las cuatro primeras.
        </p>
      </div>
    </aside>
  );
}
