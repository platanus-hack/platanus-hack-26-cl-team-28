import { useEffect, useRef } from 'react';
import { limpiarPreguntas, mismasPreguntas } from '../vivo/encuesta';
import type { EnVivo } from '../vivo/useEnVivo';
import estilos from './CajonEncuesta.module.css';

interface Props {
  sim: EnVivo;
  alCerrar(): void;
}

/**
 * La encuesta que responde cada agente, para leerla y cambiarla: qué se pregunta y en qué orden.
 * Un cajón a todo el alto, como el de la muestra. Lo escrito queda guardado en este navegador.
 */
export function CajonEncuesta({ sim, alCerrar }: Props) {
  const { preguntas, setPreguntas, preguntasBase, maximoPreguntas, largoPregunta } = sim;
  const editable = sim.encuestaEditable;
  const caja = useRef<HTMLElement>(null);
  const lista = useRef<HTMLOListElement>(null);
  /** Tras agregar una pregunta, el cursor queda en ella. */
  const enfocarUltima = useRef(false);

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

  useEffect(() => {
    if (!enfocarUltima.current) return;
    enfocarUltima.current = false;
    lista.current?.querySelector<HTMLTextAreaElement>('li:last-child textarea')?.focus();
  }, [preguntas.length]);

  const cambiar = (k: number, texto: string) => setPreguntas(preguntas.map((p, i) => (i === k ? texto : p)));
  const quitar = (k: number) => setPreguntas(preguntas.filter((_, i) => i !== k));
  const subir = (k: number) => {
    const nuevas = [...preguntas];
    [nuevas[k - 1], nuevas[k]] = [nuevas[k], nuevas[k - 1]];
    setPreguntas(nuevas);
  };
  const agregar = () => {
    enfocarUltima.current = true;
    setPreguntas([...preguntas, '']);
  };
  const cambiada = !mismasPreguntas(limpiarPreguntas(preguntas), preguntasBase);
  const repetida = (k: number) => {
    const texto = preguntas[k].replace(/\s+/g, ' ').trim();
    return texto !== '' && preguntas.some((p, i) => i < k && p.replace(/\s+/g, ' ').trim() === texto);
  };

  return (
    <aside ref={caja} tabIndex={-1} className={estilos.cajon} id="cajon-encuesta" aria-label="Encuesta">
      <header className={estilos.cabeza}>
        <p className={estilos.cuenta}>
          <b>{sim.porPreguntar}</b>
          <span>
            {sim.porPreguntar === 1 ? 'pregunta responde' : 'preguntas responde'} cada persona, con una nota de 1 (totalmente en desacuerdo) a 7
            (totalmente de acuerdo)
          </span>
        </p>
        <button type="button" className={estilos.cerrar} onClick={alCerrar} aria-label="Cerrar">
          <svg viewBox="0 0 12 12" aria-hidden="true">
            <path d="M2 2l8 8M10 2l-8 8" />
          </svg>
        </button>
      </header>

      <div className={estilos.cuerpo}>
        <ol ref={lista} className={estilos.preguntas}>
          {preguntas.map((pregunta, k) => (
            // El lugar es la identidad de cada fila: al subir una pregunta, cambian los textos y no las filas.
            <li key={k}>
              <span className={estilos.numero} aria-hidden="true">
                {k + 1}
              </span>
              <textarea
                rows={2}
                value={pregunta}
                maxLength={largoPregunta}
                readOnly={!editable}
                aria-label={`Pregunta ${k + 1}`}
                aria-invalid={repetida(k) || undefined}
                placeholder="Escribe la pregunta"
                onChange={(e) => cambiar(k, e.target.value)}
                // Una pregunta es una sola línea: Enter no agrega saltos.
                onKeyDown={(e) => e.key === 'Enter' && e.preventDefault()}
              />
              <div className={estilos.pie}>
                <p>{repetida(k) ? 'Está repetida: se pregunta una sola vez' : k === 0 ? 'Decide el color de cada punto en el mapa' : ''}</p>
                {editable && k > 0 && (
                  <button type="button" onClick={() => subir(k)} aria-label={`Subir la pregunta ${k + 1}`}>
                    Subir
                  </button>
                )}
                {editable && preguntas.length > 1 && (
                  <button type="button" onClick={() => quitar(k)} aria-label={`Quitar la pregunta ${k + 1}`}>
                    Quitar
                  </button>
                )}
              </div>
            </li>
          ))}
        </ol>
        {editable ? (
          <>
            <button type="button" className={estilos.agregar} disabled={preguntas.length >= maximoPreguntas} onClick={agregar}>
              {preguntas.length >= maximoPreguntas ? `Máximo ${maximoPreguntas} preguntas` : 'Agregar una pregunta'}
            </button>
            <p className={estilos.ayuda}>
              Escribe cada pregunta de modo que se conteste con qué tan de acuerdo está la persona. La primera es la que separa a quienes
              están a favor de quienes están en contra.
            </p>
          </>
        ) : (
          <p className={estilos.ayuda}>La corrida grabada solo tiene respuestas para estas preguntas: no se pueden cambiar.</p>
        )}
      </div>

      {editable && cambiada && (
        <footer className={estilos.final}>
          <button type="button" className={estilos.restablecer} onClick={() => setPreguntas(preguntasBase)}>
            Volver a las preguntas originales
          </button>
        </footer>
      )}
    </aside>
  );
}
