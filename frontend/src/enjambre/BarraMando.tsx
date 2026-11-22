import { useEffect, useRef, useState, type DragEvent } from 'react';
import { Boton } from '../componentes/comunes/Boton';
import { PopupDialogo, PopupFlotante, type PopupHandle } from '../componentes/comunes/Popup';
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
  /** Abre el cajón donde se lee la encuesta. */
  alAbrirEncuesta(boton: HTMLButtonElement): void;
}

/** Donde se arma la pregunta: la propuesta escrita o subida, sus variantes y si el agente itera. */
export function BarraMando({ sim, elegida, alElegir, alAbrirEncuesta }: Props) {
  const { borradores } = sim;
  const actual = borradores[Math.min(elegida, borradores.length - 1)];
  const [sobre, setSobre] = useState(false);
  const [menuIteraciones, setMenuIteraciones] = useState(false);
  const pestanas = useRef<HTMLDivElement>(null);
  const selectorIteraciones = useRef<HTMLDivElement>(null);
  const infoIteraciones = useRef<PopupHandle>(null);
  const infoProyecto = useRef<PopupHandle>(null);
  useEffect(() => {
    if (!menuIteraciones) return;
    const fuera = (e: PointerEvent) => { if (!selectorIteraciones.current?.contains(e.target as Node)) setMenuIteraciones(false); };
    const escape = (e: KeyboardEvent) => { if (e.key === 'Escape') { setMenuIteraciones(false); selectorIteraciones.current?.querySelector('button')?.focus(); } };
    window.addEventListener('pointerdown', fuera);
    window.addEventListener('keydown', escape);
    return () => { window.removeEventListener('pointerdown', fuera); window.removeEventListener('keydown', escape); };
  }, [menuIteraciones]);
  const enfocarVariante = () => requestAnimationFrame(() => pestanas.current?.querySelector<HTMLButtonElement>('[role="tab"][aria-selected="true"]')?.focus());
  const agregar = () => {
    sim.agregar();
    alElegir(borradores.length);
    enfocarVariante();
  };
  const quitar = () => {
    sim.quitar(actual.id);
    alElegir(Math.max(0, elegida - 1));
    enfocarVariante();
  };
  const soltar = (e: DragEvent) => {
    e.preventDefault();
    setSobre(false);
    const archivo = e.dataTransfer.files[0];
    if (archivo) void sim.adjuntarArchivo(actual.id, archivo);
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
      <div className={estilos.cabecera} data-con-documento={!!actual.documento || undefined}>
      <div ref={pestanas} className={estilos.pestanas} role="tablist" aria-label="Variantes de la propuesta">
        {borradores.map((borrador, i) => (
          <div key={borrador.id} className={estilos.variante} role="presentation">
            <button type="button" role="tab" aria-selected={i === elegida} aria-label={`Variante ${letraDe(i)}`} onClick={() => alElegir(i)}>
              {letraDe(i)}
            </button>
            <button
              type="button"
              className={estilos.quitarVariante}
              data-visible={i === elegida && borradores.length > 1 || undefined}
              disabled={i !== elegida || borradores.length <= 1}
              aria-hidden={i !== elegida || borradores.length <= 1}
              aria-label={`Quitar variante ${letraDe(i)}`}
              onClick={quitar}
            >
              <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M4 8h8" /></svg>
            </button>
          </div>
        ))}
        {borradores.length < MAXIMO_VARIANTES && (
          <button type="button" className={estilos.agregar} onClick={agregar} aria-label="Agregar otra variante" title="Agregar otra variante">
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5v14M5 12h14" /></svg>
          </button>
        )}
      </div>
      <button
        type="button"
        className={estilos.infoProyecto}
        aria-label="Sobre el proyecto y los ejemplos"
        title="Sobre el proyecto y los ejemplos"
        aria-haspopup="dialog"
        aria-controls="info-proyecto"
        onClick={() => infoProyecto.current?.showModal()}
      >
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="12" cy="12" r="9" />
          <path d="M12 11v5m0-8h.01" />
        </svg>
      </button>
      <Adjunto
        documento={actual.documento}
        leido={actual.leido}
        leyendo={actual.leyendo}
        error={actual.errorDocumento}
        alElegir={(archivo) => void sim.adjuntarArchivo(actual.id, archivo)}
      />
      </div>
      <label className={estilos.campo}>
        <span className="solo-lectores">Propuesta, variante {letraDe(elegida)}</span>
        <textarea
          key={actual.id}
          rows={2}
          value={actual.texto}
          placeholder={actual.documento ? 'Contexto o pregunta sobre el documento (opcional)' : 'Escribe la propuesta o suelta aquí un documento'}
          onChange={(e) => sim.cambiarTexto(actual.id, e.target.value)}
          onKeyDown={(e) => {
            if (e.key !== 'Enter' || !e.ctrlKey || e.nativeEvent.isComposing) return;
            e.preventDefault();
            if (!e.repeat && sim.puedePreguntar) e.currentTarget.form?.requestSubmit();
          }}
        />
      </label>
      <PopupDialogo
        ref={infoProyecto}
        id="info-proyecto"
        className={`${estilos.dialogoInfo} ${estilos.dialogoProyecto}`}
        aria-labelledby="titulo-info-proyecto"
        aria-describedby="descripcion-info-proyecto"
      >
        <div className={estilos.cabeceraProyecto}>
          <h2 id="titulo-info-proyecto">¿Cómo reaccionaría Chile?</h2>
          <button type="button" className={estilos.cerrarProyecto} aria-label="Cerrar" onClick={() => infoProyecto.current?.close()}>
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m6 6 12 12M18 6 6 18" /></svg>
          </button>
        </div>
        <p id="descripcion-info-proyecto" className={estilos.descripcionProyecto}>
          What If Chile simula cómo se recibiría una política pública usando agentes construidos a partir del Censo 2024.
        </p>
        <div className={estilos.contenidoProyecto}>
          <ul className={estilos.preguntasProyecto} role="list">
            <li>
              <strong>¿Cuánto apoyo tendría la propuesta?</strong>
              <p>Además del apoyo, la encuesta mide percepciones de justicia, efectividad, impacto personal y confianza en la implementación.</p>
            </li>
            <li>
              <strong>¿Cómo varía el apoyo entre grupos?</strong>
              <p>Compara regiones y perfiles, y lee por qué los agentes apoyan o rechazan la propuesta.</p>
            </li>
            <li>
              <strong>¿Qué cambios sumarían apoyo?</strong>
              <p>Consulta distintas versiones de una política a la misma muestra.</p>
            </li>
          </ul>
          {!sim.conexion?.demo && (
            <section className={estilos.ejemplosProyecto} aria-labelledby="titulo-ejemplos-propuesta">
              <h3 id="titulo-ejemplos-propuesta">Ejemplos con datos de Cadem</h3>
              <p>Carga un ejemplo y compara las respuestas simuladas con las de una encuesta real.</p>
              <div className={estilos.casos}>
                {CASOS_VALIDACION.map((caso) => (
                  <button
                    key={caso.corto}
                    type="button"
                    aria-pressed={actual.referencia === caso.referencia && !actual.documento}
                    disabled={actual.leyendo}
                    onClick={() => {
                      sim.fijar(actual.id, {
                        texto: caso.texto,
                        referencia: caso.referencia,
                        documento: undefined,
                        leido: undefined,
                        errorDocumento: undefined,
                      });
                      infoProyecto.current?.close();
                    }}
                  >
                    {caso.corto}
                    <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M3 8h9M8.5 4.5 12 8l-3.5 3.5" /></svg>
                  </button>
                ))}
              </div>
            </section>
          )}
        </div>
      </PopupDialogo>
      {sim.conexion?.demo && (
        <p className={estilos.aviso} role="status">
          Sin motor conectado: las respuestas se sortean en el navegador y no se comparan con encuestas.
        </p>
      )}
      <div className={estilos.iterar}>
        <div className={estilos.opcionAgente}>
          <label className={estilos.activarIterar}>
            <input type="checkbox" checked={sim.iteraciones > 0} onChange={(e) => { setMenuIteraciones(false); sim.setIteraciones(e.target.checked ? 2 : 0); }} />
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8L12 3zM19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8L19 15z" /></svg>
            <span>Mejorar con un agente</span>
          </label>
          <button
            type="button"
            className={estilos.infoIterar}
            aria-label="Cómo funciona la propuesta del agente"
            aria-haspopup="dialog"
            onClick={() => infoIteraciones.current?.showModal()}
          >
            <svg width="18" height="18" viewBox="0 0 20 20" aria-hidden="true">
              <circle cx="10" cy="10" r="7.5" />
              <path d="M10 9.25v4.5" />
              <circle cx="10" cy="6.5" r="0.85" fill="currentColor" stroke="none" />
            </svg>
          </button>
        </div>
        <PopupDialogo ref={infoIteraciones} className={estilos.dialogoInfo} aria-labelledby="titulo-info-iteraciones">
          <h2 id="titulo-info-iteraciones">Una versión con más apoyo</h2>
          <ol className={estilos.pasosIteraciones} role="list">
            <li>
              <span aria-hidden="true">1</span>
              <div>
                <strong>Revisar y reescribir</strong>
                <p>Una vez que termina la consulta inicial, el agente revisa las respuestas y redacta una versión que podría conseguir más apoyo.</p>
              </div>
            </li>
            <li>
              <span aria-hidden="true">2</span>
              <div>
                <strong>Volver a consultar</strong>
                <p>La simulación consulta de nuevo a los agentes y compara el apoyo entre las versiones.</p>
              </div>
            </li>
          </ol>
          <div className={estilos.pieIteraciones}>
            <p>Usa el selector para elegir cuántas versiones quieres que proponga el agente.</p>
            <Boton variante="primario" onClick={() => infoIteraciones.current?.close()}>Entendido</Boton>
          </div>
        </PopupDialogo>
          <div ref={selectorIteraciones} className={estilos.selectorIteraciones}>
            <button type="button" className={estilos.selectorBoton} disabled={sim.iteraciones === 0} aria-label={`Cantidad de versiones: ${sim.iteraciones || 2}`} aria-expanded={menuIteraciones} aria-controls="opciones-iteraciones" onClick={() => setMenuIteraciones((abierto) => !abierto)}>
              <span>{sim.iteraciones || 2}</span><svg viewBox="0 0 16 16" aria-hidden="true"><path d="m4 6 4 4 4-4" /></svg>
            </button>
            <PopupFlotante abierto={menuIteraciones} id="opciones-iteraciones" className={estilos.menuIteraciones} role="group" aria-label="Cantidad de versiones">
              {Array.from({ length: MAXIMO_ITERACIONES }, (_, k) => (
                <button key={k} type="button" aria-pressed={sim.iteraciones === k + 1} onClick={() => { sim.setIteraciones(k + 1); setMenuIteraciones(false); selectorIteraciones.current?.querySelector('button')?.focus(); }}>
                  {k + 1} {k === 0 ? 'versión' : 'versiones'}
                </button>
              ))}
            </PopupFlotante>
          </div>
      </div>
      {sim.aviso && <p className={estilos.aviso} role="alert">{sim.aviso}</p>}
      <div className={estilos.acciones}>
        <button type="button" className={estilos.encuesta} aria-haspopup="dialog" aria-label="Ver preguntas de la encuesta" title="Ver preguntas de la encuesta" onClick={(e) => alAbrirEncuesta(e.currentTarget)}>
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z" /><circle cx="12" cy="12" r="2.8" /></svg>
          Ver
        </button>
        <Boton type="submit" variante="primario" aria-keyshortcuts="Control+Enter" disabled={!sim.puedePreguntar}>
          {leyendo ? 'Leyendo el documento' : `Preguntar a ${formatear(sim.muestra.total)} agentes`}
        </Boton>
      </div>
    </form>
  );
}
