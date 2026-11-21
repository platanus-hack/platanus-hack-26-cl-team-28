import { useState, type DragEvent } from 'react';
import { Boton } from '../componentes/comunes/Boton';
import { formatear, letraDe } from '../dominio/textos';
import { MAXIMO_ITERACIONES, MAXIMO_VARIANTES, type EnVivo } from '../vivo/useEnVivo';
import { CASOS_VALIDACION } from '../vivo/validacion';
import { Adjunto } from './Adjunto';
import estilos from './BarraMando.module.css';

interface Props {
  sim: EnVivo;
  /** Variante que se está editando. */
  elegida: number;
  alElegir(indice: number): void;
}

/** Donde se arma la pregunta: la propuesta escrita o subida, sus variantes y si el agente itera. */
export function BarraMando({ sim, elegida, alElegir }: Props) {
  const { borradores } = sim;
  const actual = borradores[Math.min(elegida, borradores.length - 1)];
  const [sobre, setSobre] = useState(false);
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
    if (archivo) void sim.adjuntarArchivo(actual.id, archivo);
  };
  const usarCaso = (k: number) => {
    const caso = CASOS_VALIDACION[k];
    sim.fijar(actual.id, { texto: caso.texto, referencia: caso.referencia, documento: undefined, leido: undefined });
  };
  const leyendo = borradores.some((b) => b.leyendo);
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
        {borradores.length < MAXIMO_VARIANTES && (
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
          rows={3}
          value={actual.texto}
          placeholder={actual.documento ? 'Contexto o pregunta sobre el documento (opcional)' : 'Escribe la propuesta o suelta aquí un documento'}
          onChange={(e) => sim.cambiarTexto(actual.id, e.target.value)}
        />
      </label>
      {sim.conexion?.demo && (
        <p className={estilos.aviso} role="status">
          Sin motor conectado: las respuestas se sortean en el navegador y no se comparan con encuestas.
        </p>
      )}
      {actual.referencia && !sim.conexion?.demo && (
        <p className={estilos.referencia}>
          Se comparará con <b>{actual.referencia.fuente}</b>, {actual.referencia.fecha}: {actual.referencia.favor} % a favor.
        </p>
      )}
      <div className={estilos.casos} aria-label="Casos con encuesta real">
        <span>Probar con una encuesta real</span>
        {CASOS_VALIDACION.map((caso, k) => (
          <button key={caso.corto} type="button" aria-pressed={actual.referencia?.url === caso.referencia.url && actual.texto === caso.texto} onClick={() => usarCaso(k)}>
            {caso.corto}
          </button>
        ))}
      </div>
      <Adjunto
        documento={actual.documento}
        leido={actual.leido}
        leyendo={actual.leyendo}
        error={actual.errorDocumento}
        alElegir={(archivo) => void sim.adjuntarArchivo(actual.id, archivo)}
      />
      <label className={estilos.iterar}>
        <input type="checkbox" checked={sim.iteraciones > 0} onChange={(e) => sim.setIteraciones(e.target.checked ? 2 : 0)} />
        <span>Que un agente reescriba la propuesta con las objeciones y vuelva a preguntar</span>
        {sim.iteraciones > 0 && (
          <select aria-label="Cantidad de iteraciones" value={sim.iteraciones} onChange={(e) => sim.setIteraciones(+e.target.value)}>
            {Array.from({ length: MAXIMO_ITERACIONES }, (_, k) => (
              <option key={k} value={k + 1}>
                {k + 1}
              </option>
            ))}
          </select>
        )}
      </label>
      {sim.aviso && <p className={estilos.aviso} role="alert">{sim.aviso}</p>}
      <Boton type="submit" variante="primario" disabled={!sim.puedePreguntar}>
        {leyendo ? 'Leyendo el documento' : `Preguntar a ${formatear(sim.muestra.total)} agentes`}
      </Boton>
    </form>
  );
}
