import { useEffect, useMemo, useRef, useState } from 'react';
import { Boton } from '../componentes/comunes/Boton';
import { Figura } from '../componentes/comunes/Figura';
import { MARCA, PREPARAR } from '../contenido';
import { personasPorFigura } from '../dominio/muestra';
import { crearPoblacion } from '../dominio/poblacion';
import { formatear } from '../dominio/textos';
import type { Caso } from '../dominio/tipos';
import { useSimulacion } from '../estado/useSimulacion';
import { REGIONES_GEO } from '../mapa/geografia';
import estilos from './AppEnjambre.module.css';
import { BarraMando } from './BarraMando';
import { BarraResultado } from './BarraResultado';
import { BloqueAvance } from './BloqueAvance';
import { BloquePostura } from './BloquePostura';
import { EscenaEnjambre, PUNTO, type ModoVuelo } from './EscenaEnjambre';
import { useAngosto } from './useAngosto';
import { MenuOpciones } from './MenuOpciones';

/** Puntos dibujados: cada uno representa a una parte igual de la muestra. */
const PUNTOS = matchMedia('(min-width: 1100px)').matches ? 10000 : 5000;
const PERSONAS = crearPoblacion(PUNTOS, REGIONES_GEO);
/** Cuánto tarda la demostración en entregar las respuestas, para ver llegar a los agentes. */
const DURACION_DEMO = 5200;

const tituloDe = (caso: Caso) => caso.texto || caso.documento?.nombre || '';

export function AppEnjambre() {
  const sim = useSimulacion(PERSONAS, { minimoCasos: 1, duracionDemo: DURACION_DEMO });
  const { fase, corrida, muestra, activo, enBarrido, respondidas } = sim;
  const lienzo = useRef<HTMLCanvasElement>(null);
  const escena = useRef<EscenaEnjambre | null>(null);
  const [editando, setEditando] = useState(0);
  const [oculta, setOculta] = useState(false);
  const [claro, setClaro] = useState(false);
  const angosto = useAngosto();

  const viendo = fase === 'preguntando' ? enBarrido : activo;
  const hayResultado = (fase === 'preguntando' || fase === 'resultados') && corrida !== null;
  const resumen = hayResultado ? corrida.resumenes[viendo] : null;
  const porPunto = personasPorFigura(hayResultado ? corrida.muestra : muestra);

  const orden = useMemo<{ estados: Uint8Array; modo: ModoVuelo }>(() => {
    const estados = new Uint8Array(PUNTOS).fill(PUNTO.fuera);
    if (fase === 'simulando') {
      // Cada punto espera apagado hasta que su agente responde.
      for (const indice of muestra.indices) estados[indice] = sim.llegadas.current[indice] || PUNTO.pendiente;
      return { estados, modo: 'aparecer' };
    }
    if (!hayResultado) {
      for (const indice of muestra.indices) estados[indice] = PUNTO.neutra;
      return { estados, modo: 'cambio' };
    }
    corrida.resultados[viendo].respuestas.forEach((respuesta, k) => {
      estados[corrida.muestra.indices[k]] = PUNTO[respuesta.postura];
    });
    return { estados, modo: fase === 'preguntando' && viendo === 0 ? 'ola' : 'cambio' };
    // `respondidas` cambia cada vez que llegan respuestas nuevas.
  }, [hayResultado, corrida, muestra, viendo, fase, respondidas, sim.llegadas]);

  useEffect(() => {
    const nueva = new EscenaEnjambre(lienzo.current!, PERSONAS);
    nueva.montar();
    escena.current = nueva;
    return () => nueva.destruir();
  }, []);
  useEffect(() => escena.current?.fijar(orden.estados, orden.modo), [orden]);
  useEffect(() => {
    document.documentElement.dataset.tema = claro ? 'claro' : 'oscuro';
    escena.current?.actualizarTema();
  }, [claro]);

  // Teclas para presentar: H oculta la interfaz, las flechas cambian de variante.
  useEffect(() => {
    const tecla = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement).closest('textarea, input, select')) return;
      if (e.key === 'h' || e.key === 'H') setOculta((valor) => !valor);
      if (fase !== 'resultados' || !corrida) return;
      if (e.key === 'ArrowRight') sim.setActivo(Math.min(corrida.casos.length - 1, activo + 1));
      if (e.key === 'ArrowLeft') sim.setActivo(Math.max(0, activo - 1));
    };
    window.addEventListener('keydown', tecla);
    return () => window.removeEventListener('keydown', tecla);
  });

  const caso = hayResultado ? corrida.casos[viendo] : null;
  return (
    <div className={estilos.app} data-oculta={oculta || undefined}>
      <canvas ref={lienzo} className={estilos.lienzo} role="img" aria-label="Chile dibujado con puntos: cada punto es un grupo de personas simuladas. Al responder, quienes están a favor vuelan a la derecha y quienes están en contra a la izquierda, agrupados por región." />
      <header className={estilos.arriba}>
        <p className={estilos.marca}>{MARCA}</p>
        {caso ? (
          <h1 className={estilos.pregunta}>
            <span>
              Variante {caso.letra}
              {caso.iteracion && ` · iteración del agente sobre ${caso.iteracion.de}`}
            </span>
            {tituloDe(caso)}
          </h1>
        ) : (
          <h1 className={estilos.titular}>{fase === 'simulando' ? 'Chile está respondiendo' : PREPARAR.titular}</h1>
        )}
      </header>
      <p className={estilos.nota}>
        {resumen ? (
          <>
            <Figura estado="indecisa" aspecto={2} alto={34} />
            <span>
              <b>{resumen.porcentajes.indecisa} %</b> indecisas se quedan en el mapa
            </span>
          </>
        ) : (
          <span>{porPunto < 1.5 ? 'Cada punto es una persona simulada' : `Cada punto son ${formatear(Math.round(porPunto))} personas simuladas`}</span>
        )}
      </p>
      {fase === 'simulando' && (
        <div className={estilos.avance}>
          <BloqueAvance respondidas={respondidas} total={muestra.total} porPunto={porPunto} />
        </div>
      )}
      {resumen && (
        <>
          <div className={estilos.contra}>
            <BloquePostura postura="contra" porcentaje={resumen.porcentajes.contra} personas={Math.round(resumen.conteo.contra * porPunto)} aspecto={3} compacto={angosto} />
          </div>
          <div className={estilos.favor}>
            <BloquePostura postura="favor" porcentaje={resumen.porcentajes.favor} personas={Math.round(resumen.conteo.favor * porPunto)} aspecto={1} compacto={angosto} />
          </div>
        </>
      )}
      <div className={estilos.mando}>
        {fase === 'preparar' && <BarraMando sim={sim} elegida={Math.min(editando, sim.borradores.length - 1)} alElegir={setEditando} />}
        {hayResultado && (
          <BarraResultado corrida={corrida} viendo={viendo} recorriendo={fase === 'preguntando'} alElegir={sim.setActivo} alVolver={sim.editar} />
        )}
      </div>
      <div className={estilos.utiles}>
        <MenuOpciones sim={sim} claro={claro} alCambiarTema={() => setClaro(!claro)} alOcultar={() => setOculta(true)} />
      </div>
      {oculta && (
        <div className={estilos.mostrar}>
          <Boton variante="texto" onClick={() => setOculta(false)}>
            Mostrar la interfaz (H)
          </Boton>
        </div>
      )}
    </div>
  );
}
