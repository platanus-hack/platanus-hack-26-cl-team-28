import { useCallback, useEffect, useMemo, useRef, useState, type MouseEvent } from 'react';
import { Boton } from '../componentes/comunes/Boton';
import { formatear } from '../dominio/textos';
import { REGIONES_GEO } from '../mapa/geografia';
import { porcentajesDe, posturaDe, useEnVivo, type CasoVivo } from '../vivo/useEnVivo';
import estilos from './AppEnjambre.module.css';
import { BarraMando } from './BarraMando';
import { BarraResultado } from './BarraResultado';
import { BloqueAvance } from './BloqueAvance';
import { BloquePostura } from './BloquePostura';
import { CajonEncuesta } from './CajonEncuesta';
import { EscenaEnjambre, PUNTO, ZOOM_MAXIMO, type ModoVuelo } from './EscenaEnjambre';
import { FichaAgente } from './FichaAgente';
import { FiguraWati } from './FiguraWati';
import { Insignia } from './Insignia';
import { MenuHistorial } from './MenuHistorial';
import { MenuOpciones } from './MenuOpciones';
import { Propuesta } from './Propuesta';
import { Redactando } from './Redactando';
import { ResultadoEncuesta } from './ResultadoEncuesta';
import { useAngosto } from './useAngosto';
import { Validacion } from './Validacion';
import { VistaAnalisis } from './VistaAnalisis';
import { VistaProceso } from './VistaProceso';
import { Voces } from './Voces';

/** Puntos que se quieren dibujar; cada agente real se dibuja con varios alrededor de su comuna. */
const PUNTOS = matchMedia('(min-width: 1100px)').matches ? 10000 : 5000;

const ESTADO_POSTURA = { favor: PUNTO.favor, contra: PUNTO.contra, indecisa: PUNTO.indecisa } as const;

/** El signo de porcentaje no se separa de su número al cortar la línea. */
const sinCorte = (texto: string) => texto.replace(/(\d) %/g, '$1\u00a0%');

function textoDelta(delta: number, caso: CasoVivo): string {
  const quien = caso.iteracion ? 'con la versión del agente' : `con la variante ${caso.letra}`;
  if (delta === 0) return `Igual que A ${quien}`;
  return `${delta > 0 ? '+' : ''}${delta} ${Math.abs(delta) === 1 ? 'punto' : 'puntos'} ${quien}`;
}

/** Cuántas personas que no apoyaban la A apoyan esta variante: el cambio dicho en gente, no en puntos. */
function textoConversos(a: CasoVivo, b: CasoVivo, agentes: number[]): string | undefined {
  let ganadas = 0;
  for (const i of agentes) if (a.acuerdo[i] && a.acuerdo[i] <= 4 && b.acuerdo[i] >= 5) ganadas += 1;
  if (!ganadas) return undefined;
  return `${formatear(ganadas)} ${ganadas === 1 ? 'persona que no apoyaba' : 'personas que no apoyaban'} la A ${ganadas === 1 ? 'ahora la apoya' : 'ahora la apoyan'}`;
}

export function AppEnjambre() {
  const sim = useEnVivo(REGIONES_GEO, PUNTOS);
  const { conexion, fase, casos, viendo, muestra, version } = sim;
  const lienzo = useRef<HTMLCanvasElement>(null);
  const escena = useRef<EscenaEnjambre | null>(null);
  const [editando, setEditando] = useState(0);
  const watiSaludo = useRef<HTMLSpanElement>(null);
  const [oculta, setOculta] = useState(false);
  const [claro, setClaro] = useState(false);
  const [ficha, setFicha] = useState<{ agente: number; x: number; y: number } | null>(null);
  const [encuestaAbierta, setEncuestaAbierta] = useState(false);
  const cerrarEncuesta = useCallback(() => setEncuestaAbierta(false), []);
  const angosto = useAngosto();
  const [zoom, setZoom] = useState(1);
  /** El proceso en lugar del mapa. `montado` sigue un momento más al cerrar, mientras los cuadrados vuelven. */
  const [proceso, setProceso] = useState(false);
  const [procesoMontado, setProcesoMontado] = useState(false);
  /** El análisis por características de las personas, también en lugar del mapa. */
  const [analisis, setAnalisis] = useState(false);
  const mostrar = useRef<HTMLDivElement>(null);
  const izquierda = useRef<HTMLDivElement>(null);
  const derecha = useRef<HTMLDivElement>(null);
  const revision = useRef(0);

  // Con el mapa acercado, cada bloque de los costados se retira solo si tiene puntos o rótulos
  // debajo; los demás siguen a la vista. Se marca en el DOM (`data-tapa`) y lo aplica el CSS.
  const revisarTapados = useCallback(() => {
    cancelAnimationFrame(revision.current);
    revision.current = requestAnimationFrame(() => {
      const actual = escena.current;
      const caja = lienzo.current?.getBoundingClientRect();
      const bloques = [izquierda.current, derecha.current].flatMap((columna) => (columna ? (Array.from(columna.children) as HTMLElement[]) : []));
      const acercado = !!actual && !!caja && actual.nivel() > 1;
      const tapan = acercado
        ? actual.tapan(
            bloques.map((bloque) => {
              const r = bloque.getBoundingClientRect();
              return { x: r.left - caja.left, y: r.top - caja.top, ancho: r.width, alto: r.height };
            }),
          )
        : [];
      bloques.forEach((bloque, k) => {
        if (tapan[k]) bloque.dataset.tapa = '';
        else delete bloque.dataset.tapa;
      });
    });
  }, []);

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

  // La escena se arma una sola vez. Cuando cambia la muestra (otro filtro, otro tamaño) solo se le
  // entregan los puntos nuevos: los mueve a su lugar sin repetir la entrada.
  useEffect(() => {
    if (!puntos) return;
    if (escena.current) return escena.current.reemplazar(puntos);
    const nueva = new EscenaEnjambre(lienzo.current!, puntos);
    nueva.alCambiarVista = (nivel) => {
      setZoom(nivel);
      setFicha(null);
      revisarTapados();
    };
    nueva.montar();
    escena.current = nueva;
  }, [puntos]);
  useEffect(
    () => () => {
      escena.current?.destruir();
      escena.current = null;
    },
    [],
  );
  useEffect(() => {
    if (orden) escena.current?.fijar(orden.estados, orden.modo);
  }, [orden]);
  useEffect(() => () => cancelAnimationFrame(revision.current), []);
  useEffect(() => escena.current?.latir(fase === 'corriendo' && !listo), [fase, listo, puntos]);
  useEffect(() => {
    document.documentElement.dataset.tema = claro ? 'claro' : 'oscuro';
    escena.current?.actualizarTema();
  }, [claro]);
  useEffect(() => setFicha(null), [fase, viendo]);

  const puntosDe = useCallback((agente: number) => Array.from({ length: porAgente }, (_, k) => agente * porAgente + k), [porAgente]);
  const ubicar = useCallback((agente: number): [number, number] | null => (escena.current ? escena.current.posicion(agente * porAgente) : null), [porAgente]);
  const alHablar = useCallback((agentes: number[]) => escena.current?.resaltar(agentes.flatMap(puntosDe)), [puntosDe]);
  useEffect(() => {
    if (ficha) escena.current?.resaltar(puntosDe(ficha.agente));
    else if (fase !== 'corriendo') escena.current?.resaltar([]);
  }, [ficha, fase, puntosDe]);

  const tocar = (e: MouseEvent) => {
    if (!escena.current || !puntos || escena.current.huboArrastre() || fase === 'preparar' || fase === 'cargando') return;
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
      if (e.key === 'h' || e.key === 'H') {
        setOculta((valor) => !valor);
        // El foco no se queda en algo invisible: pasa al botón que devuelve la interfaz.
        window.setTimeout(() => mostrar.current?.querySelector('button')?.focus(), 0);
      }
      if (e.key === 'Escape') setAnalisis(false);
      if (fase !== 'resultados') return;
      if (e.key === 'ArrowRight') sim.setViendo(Math.min(casos.length - 1, viendo + 1));
      if (e.key === 'ArrowLeft') sim.setViendo(Math.max(0, viendo - 1));
    };
    window.addEventListener('keydown', tecla);
    return () => window.removeEventListener('keydown', tecla);
  });

  // En pantallas angostas el grupo de botones no se muestra, así que el proceso tampoco se abre.
  const hayProceso = !!caso;
  const alternarProceso = () => {
    setFicha(null);
    setAnalisis(false);
    if (!proceso) setProcesoMontado(true);
    setProceso(!proceso);
  };
  // El análisis y el proceso ocupan el mismo lugar: al abrir uno, el otro se cierra.
  const alternarAnalisis = () => {
    setFicha(null);
    setProceso(false);
    setAnalisis(!analisis);
  };
  // Sin corrida en pantalla no hay proceso ni análisis que mostrar. En angosto no hay botón para volver del análisis.
  useEffect(() => {
    if (hayProceso) return;
    setProceso(false);
    setProcesoMontado(false);
    setAnalisis(false);
  }, [hayProceso]);
  // Con el mapa tapado por completo no se dibuja: el proceso lo cubre al terminar de abrirse (sus
  // cuadrados salen del mapa, que debe verse mientras vuelan) y el análisis, de inmediato.
  useEffect(() => {
    if (!proceso && !analisis) return escena.current?.pausar(false);
    const espera = window.setTimeout(() => escena.current?.pausar(true), analisis ? 400 : 1300);
    return () => window.clearTimeout(espera);
  }, [proceso, analisis, puntos]);
  useEffect(() => {
    const estrecha = matchMedia('(max-width: 899px)');
    const cerrar = () => estrecha.matches && setAnalisis(false);
    estrecha.addEventListener('change', cerrar);
    return () => estrecha.removeEventListener('change', cerrar);
  }, []);

  const pct = caso && listo ? porcentajesDe(caso) : null;
  const motor = conexion?.estado?.motor ?? null;
  const base = casos.length ? casos.reduce((mejor, c) => (c.listo && porcentajesDe(c).favor > porcentajesDe(mejor).favor ? c : mejor), casos[0]) : undefined;
  const mostrarRedactando = fase === 'corriendo' && sim.redactando !== null && listo && viendo === casos.length - 1;
  // El resultado de cada pregunta aparece junto con las cifras, cuando la variante ya terminó de responder.
  const conEncuesta = !!caso && listo && sim.encuesta.length > 0 && !mostrarRedactando;
  // Cuando los puntos cambian de lugar, o los bloques de tamaño, se vuelve a revisar al terminar el vuelo.
  useEffect(() => {
    revisarTapados();
    const espera = window.setTimeout(revisarTapados, 2000);
    return () => window.clearTimeout(espera);
  }, [orden, fase, viendo, conEncuesta, revisarTapados]);

  return (
    <div className={estilos.app} data-fase={fase} data-oculta={oculta || undefined} data-acercado={zoom > 1 || undefined} data-proceso={proceso || analisis || undefined} data-encuesta={conEncuesta || undefined}>
      <canvas
        ref={lienzo}
        className={estilos.lienzo}
        onClick={tocar}
        role="img"
        aria-label="Chile dibujado con puntos: cada agente es una persona de la muestra del Censo 2024. Al responder, quienes están a favor vuelan a la derecha y quienes están en contra a la izquierda, agrupados por región."
      />
      {(fase === 'preparar' || fase === 'resultados') && (
        <a className={estilos.irAlPanel} href={fase === 'resultados' && conEncuesta ? '#resultados-movil' : '#mando-movil'}>
          {fase === 'preparar' ? 'Preparar consulta' : 'Ver resultados'}
          <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M8 3v10m-4-4 4 4 4-4" /></svg>
        </a>
      )}
      {/* Dos columnas: en cada una, cada bloque va debajo del anterior y nada se pisa. */}
      <div ref={izquierda} className={estilos.izquierda}>
      <header className={estilos.arriba}>
        {caso ? (
          <h1 className={estilos.pregunta}>
            <span>
              Variante {caso.letra}
              {caso.iteracion && ` · reescrita por el agente sobre ${caso.iteracion.de}`}
            </span>
            <Propuesta letra={caso.letra} titulo={caso.titulo} texto={caso.texto} />
            {caso.iteracion?.cambio && <small>{sinCorte(caso.iteracion.cambio)}</small>}
          </h1>
        ) : (
          <h1 className={estilos.titular}>What If Chile...</h1>
        )}
        {fase === 'corriendo' && caso && !listo && (
          <div className={estilos.avance}>
            <BloqueAvance key={caso.id} caso={caso} total={sim.totalCorrida} metricas={sim.metricas} motor={motor} />
          </div>
        )}
      </header>
      {pct && caso && (
        <div className={estilos.contra}>
          <BloquePostura postura="contra" porcentaje={pct.contra} personas={caso.conteo.contra} unidad="agentes" aspecto={3} compacto={angosto} />
        </div>
      )}
      {conEncuesta && caso && (
        <div className={estilos.encuesta} id="resultados-movil">
          <ResultadoEncuesta casos={casos} viendo={viendo} preguntas={sim.encuesta} agentes={muestra.agentes} version={version} />
        </div>
      )}
      <div className={estilos.mando} id="mando-movil">
        {mostrarRedactando && base && <Redactando base={base} numero={sim.redactando!} />}
        {fase === 'preparar' && (
          <div className={estilos.panelMando}>
            <button type="button" className={estilos.asomo} aria-label="Saludar al wati" onClick={() => {
              const figura = watiSaludo.current;
              if (!figura || matchMedia('(prefers-reduced-motion: reduce)').matches || figura.getAnimations().some((animacion) => animacion.playState === 'running')) return;
              figura.animate([
                { transform: 'translateY(0) rotate(0)' },
                { transform: 'translateY(-7px) rotate(-10deg)', offset: 0.25 },
                { transform: 'translateY(-4px) rotate(10deg)', offset: 0.55 },
                { transform: 'rotate(-5deg)', offset: 0.8 },
                { transform: 'translateY(0) rotate(0)' },
              ], { duration: 500, easing: 'ease-in-out' });
            }}>
              <span><span ref={watiSaludo} className={estilos.figuraSaludo}><FiguraWati estado="neutra" rasgos={{ semilla: 7, variante: 2, tono: 1 }} alto={104} /></span></span>
            </button>
            <div className={estilos.contenidoMando}>
              <BarraMando sim={sim} elegida={Math.min(editando, sim.borradores.length - 1)} alElegir={setEditando} alAbrirEncuesta={() => setEncuestaAbierta(true)} />
            </div>
          </div>
        )}
        {(fase === 'corriendo' || fase === 'resultados') && casos.length > 0 && (
          <BarraResultado casos={casos} viendo={viendo} corriendo={fase === 'corriendo'} alElegir={sim.setViendo} alVolver={sim.volver} />
        )}
        {fase === 'cargando' && <p className={estilos.cargando}>Conectando con el motor de simulación</p>}
      </div>
      </div>
      <div ref={derecha} className={estilos.derecha}>
      <div className={estilos.nota}>
        <Insignia conexion={conexion} agentes={muestra.total} indecisas={pct?.indecisa} />
        {/* La encuesta real preguntó por el acuerdo, que es la primera pregunta (Apoyo). */}
        {caso && !conexion?.demo && !sim.filtrada && <Validacion casos={casos} />}
        {caso && sim.filtrada && (
          <p className={estilos.filtro}>
            Mirando a {formatear(muestra.total)} de {formatear(sim.totalCorrida)} agentes, según los filtros
          </p>
        )}
      </div>
      {pct && caso && (
        <div className={estilos.favor}>
          <BloquePostura
            postura="favor"
            porcentaje={pct.favor}
            personas={caso.conteo.favor}
            unidad="agentes"
            aspecto={1}
            compacto={angosto}
            encabezado={viendo > 0 && casos[0].listo ? textoDelta(porcentajesDe(caso).favor - porcentajesDe(casos[0]).favor, caso) : undefined}
            nota={viendo > 0 && casos[0].listo ? textoConversos(casos[0], caso, muestra.agentes) : undefined}
          />
        </div>
      )}
      <div className={estilos.utiles}>
        {fase === 'corriendo' ? (
          <Boton variante="secundario" onClick={sim.detener}>
            Detener
          </Boton>
        ) : (
          <>
            {/* El historial lo guarda el motor: en la demostración no hay. */}
            {conexion && !conexion.demo && (
              <MenuHistorial
                alUsar={(textos) => {
                  sim.cargar(textos);
                  sim.volver();
                }}
              />
            )}
            <MenuOpciones sim={sim} claro={claro} alCambiarTema={() => setClaro(!claro)} alOcultar={() => setOculta(true)} />
          </>
        )}
      </div>
      </div>
      {procesoMontado && conexion && caso && (
        <VistaProceso
          sim={sim}
          conexion={conexion}
          abierta={proceso}
          claro={claro}
          origen={ubicar}
          alElegir={(agente, x, y) => setFicha({ agente, x, y })}
          alCerrado={() => setProcesoMontado(false)}
        />
      )}
      {analisis && conexion && caso && <VistaAnalisis sim={sim} conexion={conexion} />}
      {puntos && !procesoMontado && !analisis && (fase === 'corriendo' || fase === 'resultados') && conexion && (
        <Voces voces={sim.voces} caso={viendo} agentes={conexion.agentes} ubicar={ubicar} alHablar={alHablar} activo={fase === 'corriendo' && !listo && !oculta} />
      )}
      <div className={estilos.zoom} role="group" aria-label="Acercamiento del mapa">
        {hayProceso && (
          <button type="button" className={estilos.verProceso} aria-pressed={proceso} title={proceso ? 'Volver al mapa' : 'Ver el proceso'} aria-label={proceso ? 'Volver al mapa' : 'Ver el proceso de la simulación'} onClick={alternarProceso}>
            <svg viewBox="0 0 16 16" aria-hidden="true">
              <path d="M4 4.2 11.6 8M4 11.8 11.6 8" />
              <circle cx="3" cy="3.6" r="1.9" />
              <circle cx="3" cy="12.4" r="1.9" />
              <circle cx="13" cy="8" r="1.9" />
            </svg>
          </button>
        )}
        {hayProceso && (
          <button type="button" className={estilos.verProceso} aria-pressed={analisis} title={analisis ? 'Volver al mapa' : 'Analizar por grupos'} aria-label={analisis ? 'Volver al mapa' : 'Analizar los resultados por características de las personas'} onClick={alternarAnalisis}>
            <svg viewBox="0 0 16 16" aria-hidden="true">
              <path d="M3 13.5V8.5M8 13.5V2.5M13 13.5V6" strokeWidth="2.6" />
            </svg>
          </button>
        )}
        <button type="button" data-mapa aria-label="Alejar" disabled={zoom <= 1} onClick={() => escena.current?.acercar(1 / 1.5)}>
          <svg viewBox="0 0 12 12" aria-hidden="true">
            <path d="M2 6h8" />
          </svg>
        </button>
        <button type="button" data-mapa aria-label="Acercar" disabled={zoom >= ZOOM_MAXIMO} onClick={() => escena.current?.acercar(1.5)}>
          <svg viewBox="0 0 12 12" aria-hidden="true">
            <path d="M2 6h8M6 2v8" />
          </svg>
        </button>
        {zoom > 1 && (
          <button type="button" data-mapa onClick={() => escena.current?.restablecer()}>
            Ver todo
          </button>
        )}
      </div>
      {ficha && conexion && (
        <FichaAgente agente={conexion.agentes[ficha.agente]} casos={casos} viendo={viendo} x={ficha.x} y={ficha.y} preguntas={sim.encuesta} alCerrar={() => setFicha(null)} />
      )}
      {encuestaAbierta && fase === 'preparar' && <CajonEncuesta alCerrar={cerrarEncuesta} />}
      {oculta && (
        <div className={estilos.mostrar} ref={mostrar}>
          <Boton variante="texto" onClick={() => setOculta(false)}>
            Mostrar la interfaz (H)
          </Boton>
        </div>
      )}
    </div>
  );
}
