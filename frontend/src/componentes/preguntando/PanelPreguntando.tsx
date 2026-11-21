import { POSTURA_TEXTO } from '../../contenido';
import { personasPorFigura } from '../../dominio/muestra';
import { formatear } from '../../dominio/textos';
import { POSTURAS } from '../../dominio/tipos';
import { DURACION_BARRIDO, type Simulacion } from '../../estado/useSimulacion';
import { BarraPosturas } from '../comunes/BarraPosturas';
import { Boton } from '../comunes/Boton';
import { Figura } from '../comunes/Figura';
import estilos from './PanelPreguntando.module.css';
import { useAvance } from './useAvance';

interface Props {
  sim: Simulacion;
  /** Qué tan al sur está cada persona de la muestra, de 0 a 1: el orden en que la pregunta la alcanza. */
  avances: number[];
}

/** Mientras la pregunta recorre el país: el conteo de respuestas crece al ritmo del mapa. */
export function PanelPreguntando({ sim, avances }: Props) {
  const corrida = sim.corrida!;
  const avance = useAvance(sim.enBarrido, DURACION_BARRIDO);
  const respuestas = corrida.resultados[sim.enBarrido].respuestas;
  const porFigura = personasPorFigura(corrida.muestra);
  const conteo = { favor: 0, indecisa: 0, contra: 0 };
  respuestas.forEach((respuesta, k) => {
    if (avances[k] <= avance) conteo[respuesta.postura] += 1;
  });
  return (
    <section className={estilos.panel} aria-labelledby="titulo-preguntando">
      <div className={estilos.encabezado}>
        <h2 id="titulo-preguntando">La pregunta recorre Chile de norte a sur</h2>
        <Boton variante="secundario" onClick={sim.verResultados}>
          Ver resultados ahora
        </Boton>
      </div>
      <ul className={estilos.conteo} aria-hidden="true">
        {POSTURAS.map((postura, i) => (
          <li key={postura}>
            <Figura estado={postura} aspecto={i + 1} alto={72} />
            <p>
              <b>{formatear(Math.round(conteo[postura] * porFigura))}</b>
              {POSTURA_TEXTO[postura]}
            </p>
          </li>
        ))}
      </ul>
      <ol className={estilos.lista}>
        {corrida.casos.map((caso, i) => {
          const estado = i < sim.enBarrido ? 'lista' : i === sim.enBarrido ? 'actual' : 'espera';
          return (
            <li key={caso.id} data-estado={estado}>
              <b>{caso.letra}</b>
              <p>{caso.texto}</p>
              <span className={estilos.avance}>
                {estado === 'lista' && <BarraPosturas porcentajes={corrida.resumenes[i].porcentajes} conTexto={false} />}
                {estado === 'actual' && <progress max={1} value={avance} aria-label={`Avance de la variante ${caso.letra}`} />}
              </span>
              <em>{estado === 'lista' ? 'Respondida' : estado === 'actual' ? 'Preguntando' : 'En espera'}</em>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
