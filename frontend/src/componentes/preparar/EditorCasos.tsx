import { PREPARAR } from '../../contenido';
import { MAXIMO_CASOS, MINIMO_CASOS } from '../../dominio/catalogos';
import { letraDe } from '../../dominio/textos';
import type { Simulacion } from '../../estado/useSimulacion';
import { Boton } from '../comunes/Boton';
import estilos from './EditorCasos.module.css';

/** Lista de variantes de la política: una hoja con renglones, no tarjetas. */
export function EditorCasos({ sim }: { sim: Simulacion }) {
  const { borradores } = sim;
  return (
    <section className={estilos.editor} aria-labelledby="titulo-casos">
      <header>
        <h2 id="titulo-casos">{PREPARAR.casos}</h2>
        <p>{PREPARAR.casosAyuda}</p>
      </header>
      <ol className={estilos.lista}>
        {borradores.map((borrador, i) => (
          <li key={borrador.id}>
            <label htmlFor={`caso-${borrador.id}`}>
              <span className="solo-lectores">Variante </span>
              {letraDe(i)}
            </label>
            <textarea
              id={`caso-${borrador.id}`}
              rows={1}
              value={borrador.texto}
              placeholder={PREPARAR.marcador}
              onChange={(e) => sim.cambiarTexto(borrador.id, e.target.value)}
            />
            {borradores.length > MINIMO_CASOS && (
              <button type="button" className={estilos.quitar} onClick={() => sim.quitar(borrador.id)} aria-label={`Quitar la variante ${letraDe(i)}`}>
                <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M4 4l8 8M12 4l-8 8" /></svg>
              </button>
            )}
          </li>
        ))}
      </ol>
      {borradores.length < MAXIMO_CASOS && (
        <Boton variante="texto" onClick={sim.agregar}>
          {PREPARAR.agregar}
        </Boton>
      )}
    </section>
  );
}
