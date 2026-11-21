import { useEffect, useRef } from 'react';
import { POSTURA_TITULO } from '../../contenido';
import { accionDe, describirPersona, detallarPersona, vozDe } from '../../dominio/textos';
import type { Corrida } from '../../estado/corrida';
import { Boton } from '../comunes/Boton';
import { Figura } from '../comunes/Figura';
import estilos from './FichaPersona.module.css';

interface Props {
  corrida: Corrida;
  /** Posición de la persona dentro de la muestra. */
  posicion: number;
  activo: number;
  alCerrar(): void;
}

/** Una persona de la muestra y lo que respondió en cada variante. */
export function FichaPersona({ corrida, posicion, activo, alCerrar }: Props) {
  const persona = corrida.personas[posicion];
  const actual = corrida.resultados[activo].respuestas[posicion];
  const ficha = useRef<HTMLElement>(null);
  // Al elegir a alguien, la ficha se trae a la vista: puede haber quedado fuera del scroll de la hoja.
  useEffect(() => {
    const suave = !matchMedia('(prefers-reduced-motion: reduce)').matches;
    ficha.current?.scrollIntoView({ block: 'nearest', behavior: suave ? 'smooth' : 'auto' });
  }, [posicion]);
  return (
    <section className={estilos.ficha} aria-labelledby="titulo-ficha" ref={ficha}>
      <header>
        <Figura estado={actual.postura} aspecto={persona.aspecto} alto={64} />
        <div>
          <h2 id="titulo-ficha">{describirPersona(persona)}</h2>
          <p>{detallarPersona(persona)}</p>
        </div>
        <Boton variante="texto" onClick={alCerrar}>
          Cerrar
        </Boton>
      </header>
      <ol className={estilos.respuestas}>
        {corrida.casos.map((caso, i) => {
          const respuesta = corrida.resultados[i].respuestas[posicion];
          return (
            <li key={caso.id} aria-current={i === activo || undefined}>
              <b>{caso.letra}</b>
              <p>
                <strong data-postura={respuesta.postura}>{POSTURA_TITULO[respuesta.postura]}.</strong> <q>{vozDe(respuesta)}</q>
                <small>{accionDe(respuesta)}</small>
              </p>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
