import { RESULTADOS } from '../../contenido';
import type { Corrida } from '../../estado/corrida';
import { BarraPosturas } from '../comunes/BarraPosturas';
import estilos from './ComparacionCasos.module.css';

interface Props {
  corrida: Corrida;
  activo: number;
  alElegir(indice: number): void;
}

const conSigno = (valor: number) => (valor > 0 ? `+${valor}` : String(valor));

/** Las variantes lado a lado. Elegir una cambia la postura de la gente en el mapa. */
export function ComparacionCasos({ corrida, activo, alElegir }: Props) {
  return (
    <section className={estilos.panel} aria-labelledby="titulo-variantes">
      <h2 id="titulo-variantes">{RESULTADOS.casos}</h2>
      <div role="radiogroup" aria-labelledby="titulo-variantes" className={estilos.lista}>
        {corrida.casos.map((caso, i) => {
          const resumen = corrida.resumenes[i];
          return (
            <button key={caso.id} type="button" role="radio" aria-checked={i === activo} className={estilos.caso} onClick={() => alElegir(i)}>
              <b>{caso.letra}</b>
              <span className={estilos.cuerpo}>
                <span className={estilos.texto}>{caso.texto}</span>
                <BarraPosturas porcentajes={resumen.porcentajes} />
                <span className={estilos.metricas}>
                  <span>Apoyo neto <b>{conSigno(resumen.apoyoNeto)} pts</b></span>
                  {resumen.brechaTerritorial !== null && <span>Brecha entre regiones <b>{resumen.brechaTerritorial} pts</b></span>}
                  <span>Se movilizaría <b>{resumen.movilizacion} %</b></span>
                </span>
              </span>
            </button>
          );
        })}
      </div>
    </section>
  );
}
