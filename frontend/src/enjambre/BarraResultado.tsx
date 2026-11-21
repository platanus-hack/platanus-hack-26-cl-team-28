import { Boton } from '../componentes/comunes/Boton';
import type { Corrida } from '../estado/corrida';
import estilos from './BarraResultado.module.css';

interface Props {
  corrida: Corrida;
  viendo: number;
  /** Mientras la interfaz recorre sola las variantes no se puede elegir. */
  recorriendo: boolean;
  alElegir(indice: number): void;
  alVolver(): void;
}

/** Con resultados en pantalla solo queda elegir qué variante mirar, o volver a preguntar. */
export function BarraResultado({ corrida, viendo, recorriendo, alElegir, alVolver }: Props) {
  return (
    <nav className={estilos.barra} aria-label="Variantes">
      <div role="tablist" aria-label="Variante en pantalla" className={estilos.pestanas}>
        {corrida.casos.map((caso, i) => {
          const pct = corrida.resumenes[i].porcentajes.favor;
          return (
            <button key={caso.id} type="button" role="tab" aria-selected={i === viendo} disabled={recorriendo} onClick={() => alElegir(i)}>
              <b>{caso.letra}</b>
              <span>{pct} % a favor</span>
              {caso.iteracion && <small>iteración del agente</small>}
            </button>
          );
        })}
      </div>
      <Boton variante="texto" onClick={alVolver}>
        Nueva pregunta
      </Boton>
    </nav>
  );
}
