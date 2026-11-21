import { useState, type DragEvent } from 'react';
import { Boton } from '../componentes/comunes/Boton';
import { MAXIMO_CASOS } from '../dominio/catalogos';
import { formatear, letraDe } from '../dominio/textos';
import type { Simulacion } from '../estado/useSimulacion';
import { aDocumento, Adjunto } from './Adjunto';
import estilos from './BarraMando.module.css';

interface Props {
  sim: Simulacion;
  /** Variante que se está editando. */
  elegida: number;
  alElegir(indice: number): void;
}

const MAXIMO_ITERACIONES = 4;

/** Donde se arma la pregunta: la propuesta escrita o subida, sus variantes y si el agente itera. */
export function BarraMando({ sim, elegida, alElegir }: Props) {
  const { borradores } = sim;
  const actual = borradores[Math.min(elegida, borradores.length - 1)];
  const [sobre, setSobre] = useState(false);
  const cupo = Math.min(MAXIMO_ITERACIONES, MAXIMO_CASOS - borradores.length);
  const agregar = () => {
    sim.agregar();
    alElegir(borradores.length);
  };
  const quitar = () => {
    sim.quitar(actual.id);
    alElegir(Math.max(0, elegida - 1));
  };
  const soltar = (e: DragEvent) => {
    e.preventDefault();
    setSobre(false);
    const archivo = e.dataTransfer.files[0];
    if (archivo) sim.adjuntar(actual.id, aDocumento(archivo));
  };
  return (
    <form
      className={estilos.barra}
      data-sobre={sobre || undefined}
      onDragOver={(e) => {
        e.preventDefault();
        setSobre(true);
      }}
      onDragLeave={() => setSobre(false)}
      onDrop={soltar}
      onSubmit={(e) => {
        e.preventDefault();
        void sim.preguntar();
      }}
    >
      <div className={estilos.pestanas} role="tablist" aria-label="Variantes de la propuesta">
        {borradores.map((borrador, i) => (
          <button key={borrador.id} type="button" role="tab" aria-selected={i === elegida} aria-label={`Variante ${letraDe(i)}`} onClick={() => alElegir(i)}>
            {letraDe(i)}
          </button>
        ))}
        {borradores.length < MAXIMO_CASOS && (
          <button type="button" className={estilos.mas} onClick={agregar}>
            Otra variante
          </button>
        )}
        {borradores.length > 1 && (
          <button type="button" className={estilos.mas} onClick={quitar}>
            Quitar {letraDe(elegida)}
          </button>
        )}
      </div>
      <label className={estilos.campo}>
        <span className="solo-lectores">Propuesta, variante {letraDe(elegida)}</span>
        <textarea
          key={actual.id}
          rows={2}
          value={actual.texto}
          placeholder={actual.documento ? 'Nombre o resumen de la propuesta (opcional)' : 'Escribe la propuesta o suelta aquí un documento'}
          onChange={(e) => sim.cambiarTexto(actual.id, e.target.value)}
        />
      </label>
      <Adjunto documento={actual.documento} alCambiar={(documento) => sim.adjuntar(actual.id, documento)} />
      {cupo > 0 && (
        <label className={estilos.iterar}>
          <input type="checkbox" checked={sim.iteraciones > 0} onChange={(e) => sim.setIteraciones(e.target.checked ? Math.min(2, cupo) : 0)} />
          <span>Que un agente proponga iteraciones con más apoyo</span>
          {sim.iteraciones > 0 && (
            <select aria-label="Cantidad de iteraciones" value={Math.min(sim.iteraciones, cupo)} onChange={(e) => sim.setIteraciones(+e.target.value)}>
              {Array.from({ length: cupo }, (_, k) => (
                <option key={k} value={k + 1}>
                  {k + 1}
                </option>
              ))}
            </select>
          )}
        </label>
      )}
      <Boton type="submit" variante="primario" disabled={!sim.puedePreguntar}>
        Preguntar a {formatear(sim.muestra.total)} personas
      </Boton>
    </form>
  );
}
