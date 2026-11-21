import { useState } from 'react';
import { RESULTADOS } from '../../contenido';
import { describirPersona, vozDe } from '../../dominio/textos';
import { REGIONES } from '../../dominio/catalogos';
import type { Corrida } from '../../estado/corrida';
import { Boton } from '../comunes/Boton';
import { Figura } from '../comunes/Figura';
import estilos from './PanelVoces.module.css';
import { elegirVoces } from './voces';

interface Props {
  corrida: Corrida;
  activo: number;
  /** Recibe la posición de la persona dentro de la muestra. */
  alElegir(posicion: number): void;
}

/** Tres personas de la muestra, una por postura, dicen por qué. Al elegir una se marca en el mapa. */
export function PanelVoces({ corrida, activo, alElegir }: Props) {
  const [vuelta, setVuelta] = useState(0);
  const voces = elegirVoces(corrida, activo, vuelta);
  return (
    <section className={estilos.panel} aria-labelledby="titulo-voces">
      <header>
        <h2 id="titulo-voces">{RESULTADOS.voces}</h2>
        <Boton variante="texto" onClick={() => setVuelta(vuelta + 1)}>
          {RESULTADOS.otrasVoces}
        </Boton>
      </header>
      <ul className={estilos.lista}>
        {voces.map((k) => {
          const persona = corrida.personas[k];
          const respuesta = corrida.resultados[activo].respuestas[k];
          return (
            <li key={k}>
              <button type="button" onClick={() => alElegir(k)}>
                <Figura estado={respuesta.postura} aspecto={persona.aspecto} alto={50} />
                <span>
                  <q>{vozDe(respuesta)}</q>
                  <small>
                    {describirPersona(persona)} · {REGIONES[persona.region].nombre}
                  </small>
                </span>
              </button>
            </li>
          );
        })}
      </ul>
      <p className={estilos.nota}>{RESULTADOS.notaVoces}</p>
    </section>
  );
}
