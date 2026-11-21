import { correlacion, type Notas } from '../../vivo/analisis';
import estilos from './PreguntasJuntas.module.css';

interface Props {
  /** El nombre corto de cada pregunta de la encuesta, en el orden de las notas. */
  nombres: readonly string[];
  /** La pregunta que se está analizando. */
  pregunta: number;
  notas: Notas;
  agentes: readonly number[];
  alElegir(pregunta: number): void;
}

const decimal = (valor: number) => valor.toFixed(2).replace('.', ',').replace('-', '−');

/** Cómo se lee una correlación, en palabras. */
function lectura(r: number): string {
  const fuerza = Math.abs(r);
  if (fuerza < 0.2) return 'casi no se relacionan';
  const cuanto = fuerza < 0.5 ? 'algo' : fuerza < 0.75 ? 'bastante' : 'casi siempre';
  return r > 0 ? `van juntas ${cuanto}` : `van al revés ${cuanto}`;
}

/**
 * Las demás preguntas de la encuesta frente a la que se mira: si quien puso nota alta en una
 * también la puso en la otra. La barra es la correlación entre las notas de las mismas personas.
 */
export function PreguntasJuntas({ nombres, pregunta, notas, agentes, alElegir }: Props) {
  const otras = nombres.map((nombre, k) => ({ nombre, k, r: k === pregunta ? null : correlacion(notas, agentes, pregunta, k) })).filter((otra) => otra.k !== pregunta && otra.r !== null);
  if (!otras.length) return null;
  otras.sort((a, b) => Math.abs(b.r!) - Math.abs(a.r!));
  return (
    <section className={estilos.juntas} aria-label={`Qué preguntas se mueven junto con ${nombres[pregunta]}`}>
      <header>
        <h2>Se mueve con {nombres[pregunta]}</h2>
        <span aria-hidden="true">correlación</span>
      </header>
      <ul>
        {otras.map(({ nombre, k, r }) => (
          <li key={k}>
            <button type="button" title={`Analizar ${nombre}`} aria-label={`${nombre}: correlación ${decimal(r!)}, ${lectura(r!)}. Analizar esta pregunta`} onClick={() => alElegir(k)}>
              <span>{nombre}</span>
              <span className={estilos.barra} aria-hidden="true" data-negativa={r! < 0 || undefined}>
                <i style={{ width: `${Math.abs(r!) * 100}%` }} />
              </span>
              <b>{decimal(r!)}</b>
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
