import { Boton } from '../componentes/comunes/Boton';
import { MAXIMO_CASOS, MINIMO_CASOS } from '../dominio/catalogos';
import { formatear, letraDe } from '../dominio/textos';
import type { Simulacion } from '../estado/useSimulacion';
import estilos from './BarraMando.module.css';

interface Props {
  sim: Simulacion;
  /** Variante que se está viendo y editando. */
  elegida: number;
  alElegir(indice: number): void;
}

/** Lo único que hay que tocar: elegir una variante, escribirla y preguntar. */
export function BarraMando({ sim, elegida, alElegir }: Props) {
  const { borradores } = sim;
  const actual = borradores[Math.min(elegida, borradores.length - 1)];
  const agregar = () => {
    sim.agregar();
    alElegir(borradores.length);
  };
  const quitar = () => {
    sim.quitar(actual.id);
    alElegir(Math.max(0, elegida - 1));
  };
  return (
    <form
      className={estilos.barra}
      onSubmit={(e) => {
        e.preventDefault();
        void sim.preguntar();
      }}
    >
      <div className={estilos.pestanas} role="tablist" aria-label="Variantes de la política">
        {borradores.map((borrador, i) => (
          <button key={borrador.id} type="button" role="tab" aria-selected={i === elegida} onClick={() => alElegir(i)}>
            {letraDe(i)}
          </button>
        ))}
        {borradores.length < MAXIMO_CASOS && (
          <button type="button" className={estilos.mas} onClick={agregar} aria-label="Agregar otra variante">
            +
          </button>
        )}
      </div>
      <label className={estilos.campo}>
        <span className="solo-lectores">Variante {letraDe(elegida)}</span>
        <textarea
          key={actual.id}
          rows={2}
          value={actual.texto}
          placeholder="Escribe una variante de la política"
          onChange={(e) => sim.cambiarTexto(actual.id, e.target.value)}
        />
      </label>
      <div className={estilos.acciones}>
        {borradores.length > MINIMO_CASOS && (
          <Boton variante="texto" onClick={quitar}>
            Quitar variante
          </Boton>
        )}
        <Boton type="submit" variante="primario" disabled={!sim.puedePreguntar}>
          Preguntar a {formatear(sim.muestra.total)}
        </Boton>
      </div>
    </form>
  );
}
