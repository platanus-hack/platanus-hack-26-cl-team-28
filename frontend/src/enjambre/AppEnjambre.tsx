import { useEffect, useMemo, useRef, useState } from 'react';
import { Boton } from '../componentes/comunes/Boton';
import { Figura } from '../componentes/comunes/Figura';
import { FiltrosMuestra } from '../componentes/preparar/FiltrosMuestra';
import { MARCA, PREPARAR } from '../contenido';
import { crearPoblacion } from '../dominio/poblacion';
import { personasPorFigura } from '../dominio/muestra';
import { formatear } from '../dominio/textos';
import { useSimulacion } from '../estado/useSimulacion';
import { REGIONES_GEO } from '../mapa/geografia';
import estilos from './AppEnjambre.module.css';
import { BarraMando } from './BarraMando';
import { BloquePostura } from './BloquePostura';
import { EscenaEnjambre, PUNTO, type ModoVuelo } from './EscenaEnjambre';

/** Puntos dibujados: cada uno representa a una parte igual de la muestra. */
const PUNTOS = matchMedia('(min-width: 1100px)').matches ? 10000 : 5000;
const PERSONAS = crearPoblacion(PUNTOS, REGIONES_GEO);

export function AppEnjambre() {
  const sim = useSimulacion(PERSONAS);
  const { fase, corrida, muestra, activo, enBarrido } = sim;
  const lienzo = useRef<HTMLCanvasElement>(null);
  const escena = useRef<EscenaEnjambre | null>(null);
  const [elegida, setElegida] = useState(0);
  const [oculta, setOculta] = useState(false);
  const [cajon, setCajon] = useState(false);
  const [claro, setClaro] = useState(false);

  const viendo = fase === 'preguntando' ? enBarrido : activo;
  const hayResultado = fase !== 'preparar' && corrida !== null;
  const resumen = hayResultado ? corrida.resumenes[viendo] : null;
  const porPunto = personasPorFigura(hayResultado ? corrida.muestra : muestra);

  const orden = useMemo<{ estados: Uint8Array; modo: ModoVuelo }>(() => {
    const estados = new Uint8Array(PUNTOS).fill(PUNTO.fuera);
    if (!hayResultado) {
      for (const indice of muestra.indices) estados[indice] = PUNTO.neutra;
      return { estados, modo: 'cambio' };
    }
    corrida.resultados[viendo].respuestas.forEach((respuesta, k) => {
      estados[corrida.muestra.indices[k]] = PUNTO[respuesta.postura];
    });
    return { estados, modo: fase === 'preguntando' && viendo === 0 ? 'ola' : 'cambio' };
  }, [hayResultado, corrida, muestra, viendo, fase]);

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
  // Mientras la pregunta recorre las variantes, la barra muestra la que se está viendo.
  useEffect(() => {
    if (fase === 'preguntando') setElegida(enBarrido);
  }, [fase, enBarrido]);

  const elegir = (indice: number) => {
    setElegida(indice);
    const enCorrida = corrida?.casos.findIndex((caso) => caso.id === String(sim.borradores[indice]?.id)) ?? -1;
    if (fase === 'resultados' && enCorrida >= 0) sim.setActivo(enCorrida);
  };

  // Teclas para presentar: H oculta la interfaz, las flechas cambian de variante.
  useEffect(() => {
    const tecla = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement).closest('textarea, input, select')) return;
      if (e.key === 'h' || e.key === 'H') setOculta((valor) => !valor);
      if (e.key === 'ArrowRight') elegir(Math.min(sim.borradores.length - 1, elegida + 1));
      if (e.key === 'ArrowLeft') elegir(Math.max(0, elegida - 1));
    };
    window.addEventListener('keydown', tecla);
    return () => window.removeEventListener('keydown', tecla);
  });

  return (
    <div className={estilos.app} data-oculta={oculta || undefined}>
      <canvas ref={lienzo} className={estilos.lienzo} role="img" aria-label="Chile dibujado con puntos: cada punto es un grupo de personas simuladas. Al responder, quienes están a favor vuelan a la derecha y quienes están en contra a la izquierda, agrupados por región." />
      <header className={estilos.arriba}>
        <p className={estilos.marca}>{MARCA}</p>
        {hayResultado ? (
          <h1 className={estilos.pregunta}>
            <span>Variante {corrida.casos[viendo].letra}</span>
            {corrida.casos[viendo].texto}
          </h1>
        ) : (
          <h1 className={estilos.titular}>{PREPARAR.titular}</h1>
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
      {resumen && (
        <>
          <div className={estilos.contra}>
            <BloquePostura postura="contra" porcentaje={resumen.porcentajes.contra} personas={Math.round(resumen.conteo.contra * porPunto)} aspecto={3} />
          </div>
          <div className={estilos.favor}>
            <BloquePostura postura="favor" porcentaje={resumen.porcentajes.favor} personas={Math.round(resumen.conteo.favor * porPunto)} aspecto={1} />
          </div>
        </>
      )}
      <div className={estilos.mando}>
        <BarraMando sim={sim} elegida={Math.min(elegida, sim.borradores.length - 1)} alElegir={elegir} />
      </div>
      <div className={estilos.utiles}>
        {sim.simulador.esDemostracion && <p>Datos de demostración</p>}
        <Boton variante="secundario" onClick={() => setCajon(true)}>
          Muestra
        </Boton>
        <Boton variante="secundario" onClick={() => setClaro(!claro)}>
          {claro ? 'Oscuro' : 'Claro'}
        </Boton>
        <Boton variante="secundario" onClick={() => setOculta(true)}>
          Ocultar (H)
        </Boton>
      </div>
      {cajon && (
        <aside className={estilos.cajon} aria-label="Muestra">
          <FiltrosMuestra sim={sim} />
          <Boton variante="primario" onClick={() => setCajon(false)}>
            Listo
          </Boton>
        </aside>
      )}
    </div>
  );
}
