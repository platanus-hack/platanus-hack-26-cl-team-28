import { useCallback, useEffect, useMemo, useRef, useState, type MouseEvent } from 'react';
import { Boton } from '../componentes/comunes/Boton';
import { Figura } from '../componentes/comunes/Figura';
import { formatear } from '../dominio/textos';
import { REGIONES_GEO } from '../mapa/geografia';
import { porcentajesDe, posturaDe, useEnVivo, type CasoVivo } from '../vivo/useEnVivo';
import estilos from './AppEnjambre.module.css';
import { BarraMando } from './BarraMando';
import { BarraResultado } from './BarraResultado';
import { BloqueAvance } from './BloqueAvance';
import { BloquePostura } from './BloquePostura';
import { EscenaEnjambre, PUNTO, type ModoVuelo } from './EscenaEnjambre';
import { FichaAgente } from './FichaAgente';
import { Insignia } from './Insignia';
import { MenuOpciones } from './MenuOpciones';
import { Redactando } from './Redactando';
import { useAngosto } from './useAngosto';
import { Validacion } from './Validacion';
import { Voces } from './Voces';

/** Puntos que se quieren dibujar; cada agente real se dibuja con varios alrededor de su comuna. */
const PUNTOS = matchMedia('(min-width: 1100px)').matches ? 10000 : 5000;

const ESTADO_POSTURA = { favor: PUNTO.favor, contra: PUNTO.contra, indecisa: PUNTO.indecisa } as const;

function textoDelta(delta: number, caso: CasoVivo): string {
  const quien = caso.iteracion ? 'con la versión del agente' : `con la variante ${caso.letra}`;
  if (delta === 0) return `Igual que A ${quien}`;
  return `${delta > 0 ? '+' : ''}${delta} ${Math.abs(delta) === 1 ? 'punto' : 'puntos'} ${quien}`;
}

export function AppEnjambre() {
  const sim = useEnVivo(REGIONES_GEO, PUNTOS);
  const { conexion, fase, casos, viendo, muestra, version } = sim;
  const lienzo = useRef<HTMLCanvasElement>(null);
  const escena = useRef<EscenaEnjambre | null>(null);
  const [editando, setEditando] = useState(0);
  const [oculta, setOculta] = useState(false);
  const [claro, setClaro] = useState(false);
  const [ficha, setFicha] = useState<{ agente: number; x: number; y: number } | null>(null);
  const angosto = useAngosto();
  const [climax, setClimax] = useState(false);

  const puntos = conexion?.puntos;
  const porAgente = conexion && conexion.agentes.length ? conexion.puntos.length / conexion.agentes.length : 1;
  const caso = fase === 'corriendo' || fase === 'resultados' ? casos[viendo] : undefined;
  const listo = caso?.listo ?? false;

  // Estado de cada punto: fuera de la muestra, esperando a su agente o con su postura.
  const orden = useMemo<{ estados: Uint8Array; modo: ModoVuelo } | null>(() => {
    if (!puntos) return null;
    const estados = new Uint8Array(puntos.length);
    puntos.forEach((p, i) => {
      const agente = p.agente ?? 0;
      if (!muestra.elegido[agente]) estados[i] = PUNTO.fuera;
      else if (!caso) estados[i] = PUNTO.neutra;
      else estados[i] = caso.acuerdo[agente] ? ESTADO_POSTURA[posturaDe(caso.acuerdo[agente])] : PUNTO.pendiente;
    });
    if (!caso) return { estados, modo: 'cambio' };
    if (!listo) return { estados, modo: 'aparecer' };
    return { estados, modo: fase === 'corriendo' ? 'ola' : 'cambio' };
    // `version` cambia cada vez que llegan respuestas nuevas.
  }, [puntos, muestra, caso, listo, fase, version]);

  useEffect(() => {
    if (!puntos) return;
    const nueva = new EscenaEnjambre(lienzo.current!, puntos);
    nueva.montar();
    escena.current = nueva;
    return () => nueva.destruir();
  }, [puntos]);
  useEffect(() => {
    if (orden) escena.current?.fijar(orden.estados, orden.modo);
  }, [orden]);
  useEffect(() => escena.current?.latir(fase === 'corriendo' && !listo), [fase, listo, puntos]);
  useEffect(() => {
    document.documentElement.dataset.tema = claro ? 'claro' : 'oscuro';
    escena.current?.actualizarTema();
  }, [claro]);
  useEffect(() => setFicha(null), [fase, viendo]);

  // Cuando la primera variante termina y tiene encuesta real, la comparación ocupa el centro unos segundos.
  const primeraLista = casos[0]?.listo ?? false;
  const conReferencia = !!casos[0]?.referencia;
  useEffect(() => {
    if (fase !== 'corriendo' || !primeraLista || !conReferencia) return;
    const entra = window.setTimeout(() => setClimax(true), 1700);
    const sale = window.setTimeout(() => setClimax(false), 6200);
    return () => {
      window.clearTimeout(entra);
      window.clearTimeout(sale);
      setClimax(false);
    };
  }, [fase, primeraLista, conReferencia]);

  const puntosDe = useCallback((agente: number) => Array.from({ length: porAgente }, (_, k) => agente * porAgente + k), [porAgente]);
  const ubicar = useCallback((agente: number): [number, number] | null => (escena.current ? escena.current.posicion(agente * porAgente) : null), [porAgente]);
  const alHablar = useCallback((agentes: number[]) => escena.current?.resaltar(agentes.flatMap(puntosDe)), [puntosDe]);
  useEffect(() => {
    if (ficha) escena.current?.resaltar(puntosDe(ficha.agente));
    else if (fase !== 'corriendo') escena.current?.resaltar([]);
  }, [ficha, fase, puntosDe]);

  const tocar = (e: MouseEvent) => {
    if (!escena.current || !puntos || fase === 'preparar' || fase === 'cargando') return;
    const caja = lienzo.current!.getBoundingClientRect();
    const i = escena.current.cercano(e.clientX - caja.left, e.clientY - caja.top);
    const agente = i >= 0 ? puntos[i].agente : undefined;
    if (agente === undefined || !caso?.acuerdo[agente]) return setFicha(null);
    const [x, y] = escena.current.posicion(i);
    setFicha({ agente, x, y });
  };

  // Teclas para presentar: H oculta la interfaz, las flechas cambian de variante.
  useEffect(() => {
    const tecla = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement).closest('textarea, input, select')) return;
      if (e.key === 'h' || e.key === 'H') setOculta((valor) => !valor);
      if (fase !== 'resultados') return;
      if (e.key === 'ArrowRight') sim.setViendo(Math.min(casos.length - 1, viendo + 1));
      if (e.key === 'ArrowLeft') sim.setViendo(Math.max(0, viendo - 1));
    };
    window.addEventListener('keydown', tecla);
    return () => window.removeEventListener('keydown', tecla);
  });

  const pct = caso && listo ? porcentajesDe(caso) : null;
  const motor = conexion?.estado?.motor ?? null;
  const base = casos.length ? casos.reduce((mejor, c) => (c.listo && porcentajesDe(c).favor > porcentajesDe(mejor).favor ? c : mejor), casos[0]) : undefined;
  const mostrarRedactando = fase === 'corriendo' && sim.redactando !== null && listo && viendo === casos.length - 1;

  return (
    <div className={estilos.app} data-oculta={oculta || undefined}>
      <canvas
        ref={lienzo}
        className={estilos.lienzo}
        onClick={tocar}
        role="img"
        aria-label="Chile dibujado con puntos: cada agente es una persona de la muestra del Censo 2024. Al responder, quienes están a favor vuelan a la derecha y quienes están en contra a la izquierda, agrupados por región."
      />
      <header className={estilos.arriba}>
        {caso ? (
          <h1 className={estilos.pregunta}>
            <span>
              Variante {caso.letra}
              {caso.iteracion && ` · reescrita por el agente sobre ${caso.iteracion.de}`}
            </span>
            <q className={estilos.titulo}>{caso.titulo}</q>
            {caso.iteracion?.cambio && <small>{caso.iteracion.cambio}</small>}
          </h1>
        ) : (
          <>
            <h1 className={estilos.titular}>Sabe cómo reacciona Chile a una ley antes de aprobarla</h1>
            <p className={estilos.bajada}>
              {conexion?.demo
                ? 'Cada punto es una persona simulada.'
                : `${formatear(conexion?.agentes.length ?? 2000)} personas reales del Censo 2024, cada una con su agente de IA. Validado contra encuestas Cadem.`}
            </p>
          </>
        )}
        {caso && caso.texto !== caso.titulo && caso.texto && (
          <details className={estilos.completo}>
            <summary>Leer la propuesta completa</summary>
            <p>{caso.texto}</p>
          </details>
        )}
      </header>
      <div className={estilos.nota}>
        <Insignia conexion={conexion} agentes={muestra.total} />
        {pct && (
          <p className={estilos.indecisas}>
            <Figura estado="indecisa" aspecto={2} alto={30} />
            <span>
              <b>{pct.indecisa} %</b> no se decide y se queda en el mapa
            </span>
          </p>
        )}
        {caso && !climax && <Validacion casos={casos} viendo={viendo} />}
      </div>
      {fase === 'corriendo' && caso && !listo && (
        <div className={estilos.avance}>
          <BloqueAvance caso={caso} total={muestra.total} metricas={sim.metricas} motor={motor} />
        </div>
      )}
      {mostrarRedactando && base && (
        <div className={estilos.avance}>
          <Redactando base={base} numero={sim.redactando!} />
        </div>
      )}
      {pct && caso && (
        <>
          {!mostrarRedactando && (
            <div className={estilos.contra}>
              <BloquePostura postura="contra" porcentaje={pct.contra} personas={caso.conteo.contra} unidad="agentes" aspecto={3} compacto={angosto} />
            </div>
          )}
          <div className={estilos.favor}>
            <BloquePostura
              postura="favor"
              porcentaje={pct.favor}
              personas={caso.conteo.favor}
              unidad="agentes"
              aspecto={1}
              compacto={angosto}
              encabezado={viendo > 0 && casos[0].listo ? textoDelta(porcentajesDe(caso).favor - porcentajesDe(casos[0]).favor, caso) : undefined}
            />
          </div>
        </>
      )}
      {puntos && fase === 'corriendo' && conexion && (
        <Voces voces={sim.voces} caso={viendo} agentes={conexion.agentes} ubicar={ubicar} alHablar={alHablar} activo={!listo && !oculta} />
      )}
      <div className={estilos.mando}>
        {fase === 'preparar' && <BarraMando sim={sim} elegida={Math.min(editando, sim.borradores.length - 1)} alElegir={setEditando} />}
        {(fase === 'corriendo' || fase === 'resultados') && casos.length > 0 && (
          <BarraResultado casos={casos} viendo={viendo} corriendo={fase === 'corriendo'} alElegir={sim.setViendo} alVolver={sim.volver} />
        )}
        {fase === 'cargando' && <p className={estilos.cargando}>Conectando con el motor de simulación</p>}
      </div>
      <div className={estilos.utiles}>
        {fase === 'corriendo' ? (
          <Boton variante="secundario" onClick={sim.detener}>
            Detener
          </Boton>
        ) : (
          <MenuOpciones sim={sim} claro={claro} alCambiarTema={() => setClaro(!claro)} alOcultar={() => setOculta(true)} />
        )}
      </div>
      {climax && (
        <div className={estilos.climax}>
          <Validacion casos={casos} viendo={0} grande />
        </div>
      )}
      {ficha && conexion && (
        <FichaAgente agente={conexion.agentes[ficha.agente]} casos={casos} viendo={viendo} x={ficha.x} y={ficha.y} alCerrar={() => setFicha(null)} />
      )}
      {oculta && (
        <div className={estilos.mostrar}>
          <Boton variante="texto" onClick={() => setOculta(false)}>
            Mostrar la interfaz (H)
          </Boton>
        </div>
      )}
      {fase === 'resultados' && !ficha && <p className={estilos.pista}>Toca un punto para conocer a esa persona · {formatear(muestra.total)} agentes</p>}
    </div>
  );
}
