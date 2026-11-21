import type { CSSProperties } from 'react';
import { EDAD_MINIMA } from '../../dominio/catalogos';
import { EDAD_TOPE, type Parametro } from '../../vivo/sociedad';
import estilos from './Controles.module.css';

interface Props {
  parametro: Parametro;
  /** Personas en cada opción, entre quienes cumplen los demás filtros. */
  personas: number[];
  elegidas: number[];
  alTocar(opcion: number): void;
}

const suma = (valores: number[]) => valores.reduce((total, v) => total + v, 0);

/** La parte del total que es una opción, escrita: nunca "0 %" si hay alguien. */
function escrita(personas: number, total: number): string {
  if (!total) return '0 %';
  const parte = Math.round((personas / total) * 100);
  return personas > 0 && parte === 0 ? '<1 %' : `${parte} %`;
}

const variable = (nombre: string, valor: number) => ({ [nombre]: `${valor}%` }) as CSSProperties;

/**
 * Una fila por opción: su nombre, una barra con la parte de la población que es y la cifra.
 * `opciones` dibuja solo algunas (la que queda fuera de una escala); `doble` las reparte en dos columnas.
 */
export function Filas({ parametro, personas, elegidas, alTocar, opciones, doble }: Props & { opciones?: number[]; doble?: boolean }) {
  const total = suma(personas);
  const nombres = (doble && parametro.cortos) || parametro.opciones;
  const visibles = opciones ?? parametro.opciones.map((_, k) => k);
  const medidas = { '--filas': Math.ceil(visibles.length / 2), '--letras': Math.max(...nombres.map((n) => n.length)) } as CSSProperties;
  return (
    <div className={estilos.filas} data-eligiendo={elegidas.length > 0 || undefined} data-doble={doble || undefined} style={medidas}>
      {visibles.map((k) => (
        <button key={k} type="button" aria-pressed={elegidas.includes(k)} onClick={() => alTocar(k)}>
          <i aria-hidden="true" />
          <span className={estilos.nombre}>{nombres[k]}</span>
          <span className={estilos.barra} aria-hidden="true">
            <b style={variable('--parte', total ? (personas[k] / total) * 100 : 0)} />
          </span>
          <span className={estilos.parte}>{escrita(personas[k], total)}</span>
        </button>
      ))}
    </div>
  );
}

/** Dos opciones: una sola barra partida donde corresponde, con una opción a cada lado. */
export function BarraPartida({ parametro, personas, elegidas, alTocar }: Props) {
  const total = suma(personas);
  return (
    <div className={estilos.partida} data-eligiendo={elegidas.length > 0 || undefined}>
      {[0, 1].map((k) => (
        <button key={k} type="button" aria-pressed={elegidas.includes(k)} onClick={() => alTocar(k)}>
          <i aria-hidden="true" />
          <span className={estilos.nombre}>{parametro.opciones[k]}</span>
          <span className={estilos.parte}>{escrita(personas[k], total)}</span>
        </button>
      ))}
      <div className={estilos.reparto} aria-hidden="true" style={variable('--corte', total ? (personas[0] / total) * 100 : 50)}>
        {[0, 1].map((k) => (
          <b key={k} data-elegida={elegidas.includes(k) || undefined} onClick={() => alTocar(k)} />
        ))}
      </div>
    </div>
  );
}

/** Una escala ordenada (de menor a mayor ingreso, de izquierda a derecha): una columna por tramo. */
export function Columnas({ parametro, personas, elegidas, alTocar }: Props) {
  const total = suma(personas);
  const escala = parametro.opciones.map((_, k) => k).filter((k) => k !== parametro.aparte);
  const mayor = Math.max(1, ...escala.map((k) => personas[k]));
  const nombres = parametro.cortos ?? parametro.opciones;
  return (
    <>
      <div className={estilos.columnas} data-eligiendo={elegidas.length > 0 || undefined} style={{ gridTemplateColumns: `repeat(${escala.length}, 1fr)` }}>
        {escala.map((k) => (
          <button key={k} type="button" aria-pressed={elegidas.includes(k)} aria-label={`${parametro.opciones[k]}, ${escrita(personas[k], total)}`} onClick={() => alTocar(k)}>
            <span className={estilos.parte}>{escrita(personas[k], total)}</span>
            <span className={estilos.columna}>
              <b style={variable('--alto', (personas[k] / mayor) * 100)} />
            </span>
            <span className={estilos.nombre}>{nombres[k]}</span>
          </button>
        ))}
      </div>
      {parametro.aparte !== undefined && <Filas parametro={parametro} personas={personas} elegidas={elegidas} alTocar={alTocar} opciones={[parametro.aparte]} />}
    </>
  );
}

const MARCAS = [EDAD_MINIMA, 30, 50, 70, EDAD_TOPE];
const posicion = (edad: number) => ((edad - EDAD_MINIMA) / (EDAD_TOPE - EDAD_MINIMA)) * 100;

interface PropsEdad {
  /** Personas de cada edad, desde la mínima, entre quienes cumplen los demás filtros. */
  personas: number[];
  desde: number;
  hasta: number;
  alCambiar(desde: number, hasta: number): void;
}

/** La edad: cuánta gente hay de cada año y, debajo, una regla con dos topes. */
export function RangoEdad({ personas, desde, hasta, alCambiar }: PropsEdad) {
  const mayor = Math.max(1, ...personas);
  const recortando = desde > EDAD_MINIMA || hasta < EDAD_TOPE;
  const topes = { '--desde': posicion(desde) / 100, '--hasta': posicion(hasta) / 100 } as CSSProperties;
  return (
    <div className={estilos.edad} data-eligiendo={recortando || undefined} style={topes}>
      <div className={estilos.histograma} aria-hidden="true">
        {personas.map((p, k) => (
          <i key={k} data-fuera={EDAD_MINIMA + k < desde || EDAD_MINIMA + k > hasta || undefined} style={variable('--alto', (p / mayor) * 100)} />
        ))}
      </div>
      <div className={estilos.regla}>
        <input
          type="range"
          min={EDAD_MINIMA}
          max={EDAD_TOPE}
          value={desde}
          aria-label="Edad mínima"
          onChange={(e) => alCambiar(+e.target.value, Math.max(hasta, +e.target.value))}
        />
        <input
          type="range"
          min={EDAD_MINIMA}
          max={EDAD_TOPE}
          value={hasta}
          aria-label="Edad máxima"
          onChange={(e) => alCambiar(Math.min(desde, +e.target.value), +e.target.value)}
        />
      </div>
      <div className={estilos.marcas} aria-hidden="true">
        {MARCAS.map((edad) => (
          <span key={edad} style={variable('--en', posicion(edad))}>
            {edad >= EDAD_TOPE ? `${EDAD_TOPE}+` : edad}
          </span>
        ))}
      </div>
    </div>
  );
}
