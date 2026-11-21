import type { CSSProperties } from 'react';
import { EDAD_MAXIMA, EDAD_MINIMA } from '../../dominio/catalogos';
import estilos from './RangoEdad.module.css';

interface Props {
  minimo: number;
  maximo: number;
  alCambiar(minimo: number, maximo: number): void;
}

const rotulo = (edad: number) => (edad >= EDAD_MAXIMA ? `${EDAD_MAXIMA}+` : String(edad));
const porcentaje = (edad: number) => `${((edad - EDAD_MINIMA) / (EDAD_MAXIMA - EDAD_MINIMA)) * 100}%`;

/** Dos deslizadores sobre una misma pista. Si se cruzan, el que se mueve empuja al otro. */
export function RangoEdad({ minimo, maximo, alCambiar }: Props) {
  const pista = { '--desde': porcentaje(minimo), '--hasta': porcentaje(maximo) } as CSSProperties;
  return (
    <fieldset className={estilos.rango}>
      <legend>
        Edad <output>{rotulo(minimo)} a {rotulo(maximo)} años</output>
      </legend>
      <div className={estilos.pista} style={pista}>
        <input
          type="range"
          min={EDAD_MINIMA}
          max={EDAD_MAXIMA}
          value={minimo}
          aria-label="Edad mínima"
          aria-valuetext={rotulo(minimo)}
          onChange={(e) => alCambiar(+e.target.value, Math.max(maximo, +e.target.value))}
        />
        <input
          type="range"
          min={EDAD_MINIMA}
          max={EDAD_MAXIMA}
          value={maximo}
          aria-label="Edad máxima"
          aria-valuetext={rotulo(maximo)}
          onChange={(e) => alCambiar(Math.min(minimo, +e.target.value), +e.target.value)}
        />
      </div>
    </fieldset>
  );
}
