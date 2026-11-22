import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState, type MouseEvent } from 'react';
import { Boton } from '../componentes/comunes/Boton';
import { formatear, personasAprox } from '../dominio/textos';
import { REGIONES_GEO } from '../mapa/geografia';
import { rasgosDelVoto } from '../vivo/analisis';
import { porcentajesDe, posturaDe, useEnVivo, type CasoVivo } from '../vivo/useEnVivo';
import estilos from './AppEnjambre.module.css';
import { animarWati, rebotarWati } from './animarWati';
import { BarraMando } from './BarraMando';
import { BarraResultado } from './BarraResultado';
import { BloqueAvance } from './BloqueAvance';
import { BloquePostura } from './BloquePostura';
import { CajonEncuesta } from './CajonEncuesta';
import { ConexionMcp } from './ConexionMcp';
import { EscenaEnjambre, PUNTO, ZOOM_MAXIMO, type Bordes, type ModoVuelo } from './EscenaEnjambre';
import { FichaAgente } from './FichaAgente';
import { FiguraWati } from './FiguraWati';
import { Insignia } from './Insignia';
import { MenuHistorial } from './MenuHistorial';
import { MenuOpciones } from './MenuOpciones';
import { Propuesta } from './Propuesta';
import { Redactando } from './Redactando';
import { ResultadoEncuesta } from './ResultadoEncuesta';
import { DisposicionMovil } from './movil/DisposicionMovil';
import movilEstilos from './movil/DisposicionMovil.module.css';
import type { Tope } from './movil/hoja';
import { ListaVoces } from './movil/ListaVoces';
import { MenuMas } from './movil/MenuMas';
import { useMenuOpciones } from './MenuOpciones';
import { PorRegion } from './movil/PorRegion';
import { Quienes } from './movil/Quienes';
import { ResumenPostura } from './movil/ResumenPostura';
import { useAngosto, useMovil } from './useAngosto';
import { usePanelLateral } from './usePanelLateral';
import { Validacion } from './Validacion';
import { VistaAnalisis } from './VistaAnalisis';
import { caminoDe, leerRuta, type Ruta, type Vista } from './ruta';
import { VistaProceso } from './VistaProceso';
import { Voces } from './Voces';

/** Cuántos toques seguidos al wati del mando lo vuelven mono, y cuánto puede pasar entre uno y otro. */
const TOQUES_PARA_MONO = 7;
const TOQUES_SEGUIDOS_MS = 700;
const ESPERA_WATI_MS = 3000;

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
  /** Quienes necesitan enterarse de que el mapa se movió o se acercó (los globos, para seguir a su punto). */
  const oyentesVista = useRef(new Set<() => void>());
  const [editando, setEditando] = useState(0);
  const watiSaludo = useRef<HTMLSpanElement>(null);
  const [mono, setMono] = useState(false);
  const [watiVisible, setWatiVisible] = useState(false);
  const [saludo, setSaludo] = useState(0);
  const botonWati = useRef<HTMLButtonElement>(null);
  const toques = useRef({ cuantos: 0, ultimo: 0 });
  const [oculta, setOculta] = useState(false);
  const [claro, setClaro] = useState(false);
  const [ficha, setFicha] = useState<{ agente: number; x: number; y: number } | null>(null);
  const { abierto: encuestaAbierta, montado: encuestaMontada, abrir: abrirEncuesta, cerrar: cerrarPanelEncuesta } = usePanelLateral();
  const botonEncuesta = useRef<HTMLButtonElement>(null);
  const cerrarEncuesta = useCallback(() => {
    cerrarPanelEncuesta();
    botonEncuesta.current?.focus();
  }, [cerrarPanelEncuesta]);
  const angosto = useAngosto();
  /** En el teléfono la interfaz no va a los costados del país: barra arriba y hoja abajo (ver movil/). */
  const movil = useMovil();
  /** Lo que tapan la barra y la hoja en el teléfono; se guarda por si la escena se arma después. */
  const ultimosBordes = useRef<Bordes | null>(null);
  const [hojaCompleta, setHojaCompleta] = useState(false);
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
    nueva.fijarBordes(ultimosBordes.current);
    nueva.alCambiarVista = (nivel) => {
      setZoom(nivel);
      setFicha(null);
      revisarTapados();
      oyentesVista.current.forEach((oyente) => oyente());
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
  // En el teléfono el mapa se acomoda en lo que dejan libre la barra y la hoja; en escritorio, a los costados.
  const alCambiarBordes = useCallback((bordes: Bordes) => {
    ultimosBordes.current = bordes;
    escena.current?.fijarBordes(bordes);
  }, []);
  useLayoutEffect(() => {
    if (movil) return;
    ultimosBordes.current = null;
    escena.current?.fijarBordes(null);
    setHojaCompleta(false);
  }, [movil]);
  const alCambiarTope = useCallback((tope: Tope) => setHojaCompleta(tope === 'completa'), []);
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
  useEffect(() => {
    if (fase !== 'preparar') {
      setWatiVisible(false);
      return;
    }
    const reducir = matchMedia('(prefers-reduced-motion: reduce)');
    let ciclo = 0;
    let saludoPendiente = 0;
    const limpiar = () => {
      window.clearTimeout(ciclo);
      window.clearTimeout(saludoPendiente);
    };
    const programarSaludo = () => {
      saludoPendiente = window.setTimeout(() => {
        if (!document.hidden && !botonWati.current?.matches(':hover, :focus-within')) setSaludo(performance.now());
        programarSaludo();
      }, 5000 + Math.random() * 4000);
    };
    const mostrarWati = () => {
      setWatiVisible(true);
      if (reducir.matches) return;
      setSaludo(performance.now());
      programarSaludo();
      ciclo = window.setTimeout(ocultarWati, 12000 + Math.random() * 8000);
    };
    const ocultarWati = () => {
      if (document.hidden || botonWati.current?.matches(':hover, :focus-within')) {
        ciclo = window.setTimeout(ocultarWati, 2000);
        return;
      }
      window.clearTimeout(saludoPendiente);
      setWatiVisible(false);
      ciclo = window.setTimeout(mostrarWati, 3000 + Math.random() * 2000);
    };
    const iniciar = () => {
      limpiar();
      if (reducir.matches) setWatiVisible(true);
      else {
        setWatiVisible(false);
        ciclo = window.setTimeout(mostrarWati, ESPERA_WATI_MS);
      }
    };
    iniciar();
    reducir.addEventListener('change', iniciar);
    return () => { limpiar(); reducir.removeEventListener('change', iniciar); };
  }, [fase]);

  const puntosDe = useCallback((agente: number) => Array.from({ length: porAgente }, (_, k) => agente * porAgente + k), [porAgente]);
  const tapaMapa = useCallback((rect: DOMRect) => {
    const caja = lienzo.current?.getBoundingClientRect();
    if (!caja || !escena.current) return false;
    return escena.current.tapan([{ x: rect.left - caja.left, y: rect.top - caja.top, ancho: rect.width, alto: rect.height }], 12)[0];
  }, []);
  const ubicar = useCallback((agente: number): [number, number] | null => (escena.current ? escena.current.posicion(agente * porAgente) : null), [porAgente]);

  /** Quiénes hablan en los globos. Se resaltan mientras no haya una ficha abierta: esa manda. */
  const hablan = useRef<number[]>([]);
  const conFicha = useRef(false);
  const alHablar = useCallback(
    (agentes: number[]) => {
      hablan.current = agentes;
      if (!conFicha.current) escena.current?.resaltar(agentes.flatMap(puntosDe));
    },
    [puntosDe],
  );
  const alMoverVista = useCallback((oyente: () => void) => {
    oyentesVista.current.add(oyente);
    return () => {
      oyentesVista.current.delete(oyente);
    };
  }, []);
  useEffect(() => {
    conFicha.current = !!ficha;
    if (ficha) escena.current?.resaltar(puntosDe(ficha.agente));
    else escena.current?.resaltar(hablan.current.flatMap(puntosDe));
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
      if (e.defaultPrevented || (e.target as HTMLElement).closest('dialog[open], textarea, input, select')) return;
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
  // Sin corrida en pantalla no hay proceso ni análisis que mostrar.
  useEffect(() => {
    if (hayProceso) return;
    setProceso(false);
    setProcesoMontado(false);
    setAnalisis(false);
  }, [hayProceso]);

  // La dirección de la página sigue a lo que se mira (ver ruta.ts): así funcionan atrás y adelante
  // del navegador, y recargar o abrir un enlace vuelve a la misma simulación y vista.
  const vista: Vista = proceso ? 'proceso' : analisis ? 'analisis' : 'mapa';
  const deseado = caminoDe({ id: fase === 'preparar' || fase === 'cargando' ? null : sim.corridaId, vista });
  const ponerVista = (destino: Vista) => {
    setFicha(null);
    if (destino === 'proceso') setProcesoMontado(true);
    setProceso(destino === 'proceso');
    setAnalisis(destino === 'analisis');
  };
  /** La dirección a la que se está llegando por el navegador: mientras la pantalla no llegue, no se escribe otra encima. */
  const yendoA = useRef<string | null>(leerRuta(location.pathname).id ? location.pathname : null);
  const alCargar = useRef(yendoA.current !== null);
  const ultimo = useRef({ fase, corridaId: sim.corridaId, deseado });
  ultimo.current = { fase, corridaId: sim.corridaId, deseado };
  const llegar = async (ruta: Ruta) => {
    const camino = caminoDe(ruta);
    const ahora = ultimo.current;
    if (camino === ahora.deseado) {
      yendoA.current = null;
      return;
    }
    yendoA.current = camino;
    if (!ruta.id) {
      if (ahora.fase !== 'preparar') sim.volver();
      ponerVista('mapa');
      return;
    }
    if (ruta.id !== ahora.corridaId || ahora.fase === 'preparar') {
      const problema = await sim.reabrir(ruta.id);
      if (problema) {
        // Ya no está guardada (o el motor no responde): la dirección vuelve a lo que hay en pantalla.
        yendoA.current = null;
        history.replaceState(null, '', ultimo.current.deseado);
        return;
      }
    }
    ponerVista(ruta.vista);
  };
  useEffect(() => {
    if (fase === 'cargando') return;
    if (yendoA.current !== null) {
      if (deseado === yendoA.current) yendoA.current = null;
      return;
    }
    if (deseado !== location.pathname) history.pushState(null, '', deseado);
  }, [fase, deseado]);
  useEffect(() => {
    const alNavegar = () => void llegar(leerRuta(location.pathname));
    addEventListener('popstate', alNavegar);
    return () => removeEventListener('popstate', alNavegar);
  });
  // Al entrar por una dirección con simulación, se abre apenas el motor responde; sin motor no hay historial.
  useEffect(() => {
    if (!alCargar.current || fase !== 'preparar' || !conexion) return;
    alCargar.current = false;
    if (conexion.demo) {
      yendoA.current = null;
      history.replaceState(null, '', '/');
      return;
    }
    void llegar(leerRuta(location.pathname));
  });
  // Con el mapa tapado por completo no se dibuja: el proceso lo cubre al terminar de abrirse (sus
  // cuadrados salen del mapa, que debe verse mientras vuelan) y el análisis, de inmediato.
  // En el teléfono, con la hoja subida entera, el mapa tampoco se ve.
  useEffect(() => {
    if (!proceso && !analisis && !hojaCompleta) return escena.current?.pausar(false);
    const espera = window.setTimeout(() => escena.current?.pausar(true), analisis ? 400 : hojaCompleta && !proceso ? 320 : 1300);
    return () => window.clearTimeout(espera);
  }, [proceso, analisis, hojaCompleta, puntos]);

  const pct = caso && listo ? porcentajesDe(caso) : null;
  const agentesAnalisis = conexion?.agentes;
  // Qué distingue a cada lado del voto: un wati por característica en cada bloque.
  /* eslint-disable react-hooks/exhaustive-deps -- `version` cambia con cada respuesta que llega. */
  const rasgos = useMemo(
    () =>
      caso && listo && agentesAnalisis
        ? {
            favor: rasgosDelVoto(agentesAnalisis, caso.acuerdo, muestra.agentes, 'favor'),
            contra: rasgosDelVoto(agentesAnalisis, caso.acuerdo, muestra.agentes, 'contra'),
            indecisa: rasgosDelVoto(agentesAnalisis, caso.acuerdo, muestra.agentes, 'indecisa'),
          }
        : null,
    [caso, listo, agentesAnalisis, muestra, version],
  );
  /* eslint-enable react-hooks/exhaustive-deps */
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

  const barraMando = (
    <BarraMando sim={sim} elegida={Math.min(editando, sim.borradores.length - 1)} alElegir={setEditando} alAbrirEncuesta={(boton) => {
      botonEncuesta.current = boton;
      abrirEncuesta();
    }} />
  );

  /** El wati que se asoma sobre el panel para preparar la consulta (sobre la hoja, en el teléfono). */
  const watiSaludando = (
    <button ref={botonWati} type="button" className={estilos.asomo} data-visible={watiVisible || undefined} disabled={!watiVisible} aria-hidden={!watiVisible} aria-label={mono ? 'Saludar al mono con banana' : 'Saludar al wati'} onClick={() => {
      const figura = watiSaludo.current;
      // Muchos toques seguidos lo disfrazan de mono; otros tantos lo devuelven a wati.
      const ahora = performance.now();
      const racha = toques.current;
      racha.cuantos = ahora - racha.ultimo < TOQUES_SEGUIDOS_MS ? racha.cuantos + 1 : 1;
      racha.ultimo = ahora;
      if (racha.cuantos >= TOQUES_PARA_MONO) {
        racha.cuantos = 0;
        setMono((es) => !es);
        if (figura) {
          animarWati(figura, [
            { transform: 'scale(1.25, 0.8)', offset: 0.2 },
            { transform: 'scale(0.85, 1.2) translateY(-8px)', offset: 0.5 },
            { transform: 'scale(1, 1)' },
          ], 450);
        }
        return;
      }
      if (figura) rebotarWati(figura);
    }}>
      <span><span ref={watiSaludo} className={estilos.figuraSaludo}><FiguraWati estado="neutra" rasgos={{ semilla: 7, variante: 2, tono: 1 }} alto={104} mono={mono} saludo={saludo} /></span></span>
    </button>
  );

  // El cajón de la muestra en el teléfono: se abre desde el menú de la barra o junto a «Muestra» en la
  // hoja, y al cerrarse el foco vuelve a quien lo abrió.
  const origenOpciones = useRef<HTMLElement | null>(null);
  const opcionesMovil = useMenuOpciones(sim, useCallback(() => origenOpciones.current?.focus(), []));
  const abrirOpcionesMovil = (origen: HTMLElement | null) => {
    origenOpciones.current = origen;
    opcionesMovil.abrir();
  };

  // ─── Teléfono: el menú de la barra, lo que asoma de la hoja y lo que hay debajo, según la fase ───
  const menuMovil = (
    <MenuMas
      sim={sim}
      claro={claro}
      alCambiarTema={() => setClaro((valor) => !valor)}
      conHistorial={!!conexion && !conexion.demo}
      alUsarHistorial={(textos) => {
        sim.cargar(textos);
        sim.volver();
      }}
      alVerHistorial={(id) => {
        setFicha(null);
        return sim.reabrir(id);
      }}
      opciones={{ bloqueado: opcionesMovil.bloqueado, abrir: abrirOpcionesMovil }}
    />
  );
  const borrador = sim.borradores[Math.min(editando, sim.borradores.length - 1)];
  const asomoMovil =
    !conexion || fase === 'cargando' ? (
      <p className={movilEstilos.cargando}>Conectando con el motor de simulación</p>
    ) : fase === 'preparar' ? (
      <div className={movilEstilos.preparar}>
        <h2>Preparar consulta</h2>
        <p>
          {borrador?.texto.trim() ? <q>{borrador.texto.trim()}</q> : `Para ${formatear(muestra.total)} agentes del Censo 2024`}
        </p>
      </div>
    ) : pct && caso ? (
      <div className={movilEstilos.resumen}>
        <ResumenPostura porcentajes={pct} conteo={caso.conteo} porAgente={sim.personasPorAgente} />
        {casos.length > 1 && <BarraResultado compacta casos={casos} viendo={viendo} corriendo={fase === 'corriendo'} alElegir={sim.setViendo} alVolver={sim.volver} />}
        {mostrarRedactando && base && <Redactando base={base} numero={sim.redactando!} />}
      </div>
    ) : caso ? (
      <BloqueAvance key={caso.id} caso={caso} total={sim.totalCorrida} metricas={sim.metricas} motor={motor} />
    ) : null;
  const seccionMuestra = (
    <section className={movilEstilos.seccion}>
      <div className={movilEstilos.cabeceraSeccion}>
        <h2>Muestra</h2>
        {!opcionesMovil.bloqueado && (
          <button type="button" className={movilEstilos.opcionesSeccion} aria-expanded={opcionesMovil.abierto} aria-controls={opcionesMovil.abierto ? 'cajon-muestra' : undefined} onClick={(e) => abrirOpcionesMovil(e.currentTarget)}>
            <svg viewBox="0 0 16 16" aria-hidden="true">
              <path d="M2 4.5h7m4 0h1M2 11.5h2m4 0h6" />
              <circle cx="11" cy="4.5" r="1.8" />
              <circle cx="6" cy="11.5" r="1.8" />
            </svg>
            Opciones
          </button>
        )}
      </div>
      <Insignia conexion={conexion} agentes={muestra.total} porAgente={sim.personasPorAgente} />
      {caso && sim.filtrada && (
        <p className={estilos.filtro}>
          Mirando a {formatear(muestra.total)} de {formatear(sim.totalCorrida)} agentes{sim.personasPorAgente ? ` (≈ ${personasAprox(muestra.total * sim.personasPorAgente)})` : ''}, según los filtros
        </p>
      )}
    </section>
  );
  const deltaMovil = pct && caso && viendo > 0 && casos[0].listo ? textoDelta(porcentajesDe(caso).favor - porcentajesDe(casos[0]).favor, caso) : null;
  const conversosMovil = deltaMovil && caso ? textoConversos(casos[0], caso, muestra.agentes) : undefined;
  const cuerpoMovil =
    fase === 'preparar' ? (
      <div className={movilEstilos.secciones}>
        <div className={movilEstilos.mando}>{barraMando}</div>
        {seccionMuestra}
      </div>
    ) : (
      <div className={movilEstilos.secciones}>
        {deltaMovil && (
          <section className={movilEstilos.seccion}>
            <h2>Contra la variante A</h2>
            <p className={movilEstilos.cambio} data-baja={deltaMovil.startsWith('-') || undefined}>{deltaMovil}</p>
            {conversosMovil && <p className={movilEstilos.nota}>{conversosMovil}</p>}
          </section>
        )}
        {caso?.iteracion?.cambio && (
          <section className={movilEstilos.seccion}>
            <h2>Qué cambió el agente</h2>
            <p className={movilEstilos.nota}>{sinCorte(caso.iteracion.cambio)}</p>
          </section>
        )}
        {conEncuesta && caso && (
          <section className={movilEstilos.seccion}>
            <ResultadoEncuesta casos={casos} viendo={viendo} preguntas={sim.encuesta} agentes={muestra.agentes} version={version} />
          </section>
        )}
        {caso && listo && !conexion?.demo && !sim.filtrada && casos[0]?.referencia && (
          <section className={movilEstilos.seccion}>
            <h2>Encuesta real y agentes{casos.length > 1 ? `, variante ${casos[0].letra}` : ''}</h2>
            <Validacion casos={casos} enLinea />
          </section>
        )}
        {rasgos && (
          <section className={movilEstilos.seccion}>
            <h2>Quiénes</h2>
            <Quienes rasgos={rasgos} porAgente={sim.personasPorAgente} />
          </section>
        )}
        {caso && listo && conexion && (
          <section className={movilEstilos.seccion}>
            <h2>Por región</h2>
            <PorRegion caso={caso} agentes={conexion.agentes} muestra={muestra.agentes} version={version} />
          </section>
        )}
        {caso && conexion && (
          <section className={movilEstilos.seccion}>
            <h2>Voces</h2>
            <ListaVoces caso={caso} agentes={conexion.agentes} muestra={muestra.agentes} version={version} alElegir={(agente) => {
              const lugar = ubicar(agente);
              setFicha({ agente, x: lugar?.[0] ?? 0, y: lugar?.[1] ?? 0 });
            }} />
          </section>
        )}
        {seccionMuestra}
        {caso && (
          <section className={movilEstilos.seccion} aria-label="Otras vistas">
            <div className={movilEstilos.acciones}>
              <button type="button" className={movilEstilos.accion} onClick={alternarProceso}>
                <svg viewBox="0 0 16 16" aria-hidden="true">
                  <path d="M4 4.2 11.6 8M4 11.8 11.6 8" />
                  <circle cx="3" cy="3.6" r="1.9" fill="currentColor" stroke="none" />
                  <circle cx="3" cy="12.4" r="1.9" fill="currentColor" stroke="none" />
                  <circle cx="13" cy="8" r="1.9" fill="currentColor" stroke="none" />
                </svg>
                Ver el proceso
              </button>
              <button type="button" className={movilEstilos.accion} onClick={alternarAnalisis}>
                <svg viewBox="0 0 16 16" aria-hidden="true">
                  <path d="M3 13.5V8.5M8 13.5V2.5M13 13.5V6" strokeWidth="2.6" />
                </svg>
                Analizar por grupos
              </button>
              {fase === 'resultados' && (
                <button type="button" className={movilEstilos.accion} onClick={sim.volver}>
                  Nueva pregunta
                </button>
              )}
            </div>
          </section>
        )}
      </div>
    );

  return (
    <div className={estilos.app} data-movil={movil || undefined} data-fase={fase} data-oculta={oculta || undefined} data-acercado={zoom > 1 || undefined} data-proceso={proceso || analisis || undefined} data-encuesta={conEncuesta || undefined}>
      <canvas
        ref={lienzo}
        className={estilos.lienzo}
        onClick={tocar}
        role="img"
        aria-label="Chile dibujado con puntos: cada agente es una persona de la muestra del Censo 2024. Al responder, quienes están a favor vuelan a la derecha y quienes están en contra a la izquierda, agrupados por región."
      />
      {movil ? (
        <>
        <DisposicionMovil fase={fase} caso={caso} menu={menuMovil} asomo={asomoMovil} encima={fase === 'preparar' ? watiSaludando : undefined} etiqueta={fase === 'preparar' ? 'Preparar consulta' : 'Resultados'} alCambiarBordes={alCambiarBordes} alCambiarTope={alCambiarTope} oculta={oculta || proceso || analisis}>
          {cuerpoMovil}
        </DisposicionMovil>
        {/* Fuera de la barra y de la hoja: así queda sobre las dos (z-index 6 en CajonMuestra). */}
        {opcionesMovil.cajon}
        </>
      ) : (
      <>
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
          <BloquePostura tapaMapa={tapaMapa} revisionMapa={orden} zoomMapa={zoom} postura="contra" porcentaje={pct.contra} personas={caso.conteo.contra} unidad="agentes" porAgente={sim.personasPorAgente} aspecto={3} rasgos={rasgos?.contra} compacto={angosto} />
        </div>
      )}
      {conEncuesta && caso && (
        <div className={estilos.encuesta}>
          <ResultadoEncuesta casos={casos} viendo={viendo} preguntas={sim.encuesta} agentes={muestra.agentes} version={version} />
        </div>
      )}
      <div className={estilos.mando}>
        {mostrarRedactando && base && <Redactando base={base} numero={sim.redactando!} />}
        {fase === 'preparar' && (
          <div className={estilos.panelMando}>
            {watiSaludando}
            <div className={estilos.contenidoMando}>
              {barraMando}
            </div>
          </div>
        )}
        {(fase === 'corriendo' || fase === 'resultados') && casos.length > 0 && (
          <BarraResultado casos={casos} viendo={viendo} corriendo={fase === 'corriendo'} alElegir={sim.setViendo} alVolver={sim.volver} acciones={<div className={estilos.accionesMapa} role="group" aria-label="Vistas de la simulación">
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
      </div>} />
        )}
        {fase === 'cargando' && <p className={estilos.cargando}>Conectando con el motor de simulación</p>}
      </div>
      </div>
      <div ref={derecha} className={estilos.derecha}>
      <div className={estilos.nota}>
        <Insignia conexion={conexion} agentes={muestra.total} porAgente={sim.personasPorAgente} indecisas={pct?.indecisa} agentesIndecisos={caso?.conteo.indecisa} rasgosIndecisas={rasgos?.indecisa} />
        {/* La encuesta real preguntó por el acuerdo, que es la primera pregunta (Apoyo). */}
        {caso && !conexion?.demo && !sim.filtrada && <Validacion casos={casos} />}
        {caso && sim.filtrada && (
          <p className={estilos.filtro}>
            Mirando a {formatear(muestra.total)} de {formatear(sim.totalCorrida)} agentes{sim.personasPorAgente ? ` (≈ ${personasAprox(muestra.total * sim.personasPorAgente)})` : ''}, según los filtros
          </p>
        )}
      </div>
      {pct && caso && (
        <div className={estilos.favor}>
          <BloquePostura
            tapaMapa={tapaMapa}
            revisionMapa={orden}
            zoomMapa={zoom}
            postura="favor"
            porcentaje={pct.favor}
            personas={caso.conteo.favor}
            unidad="agentes"
            porAgente={sim.personasPorAgente}
            aspecto={1}
            rasgos={rasgos?.favor}
            compacto={angosto}
            encabezado={viendo > 0 && casos[0].listo ? textoDelta(porcentajesDe(caso).favor - porcentajesDe(casos[0]).favor, caso) : undefined}
            nota={viendo > 0 && casos[0].listo ? textoConversos(casos[0], caso, muestra.agentes) : undefined}
          />
        </div>
      )}
      <div className={estilos.utiles}>
        <button type="button" role="switch" aria-label="Tema claro" aria-checked={claro} className={estilos.cambiarTema} onClick={() => setClaro((valor) => !valor)}>
          <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M16.6 12.5A7 7 0 0 1 7.5 3.4a7 7 0 1 0 9.1 9.1Z" /></svg>
          <svg viewBox="0 0 20 20" aria-hidden="true">
            <circle cx="10" cy="10" r="3.2" />
            <path d="M10 2v2m0 12v2M2 10h2m12 0h2M4.3 4.3l1.4 1.4m8.6 8.6 1.4 1.4m0-11.4-1.4 1.4m-8.6 8.6-1.4 1.4" />
          </svg>
        </button>
        <div className={estilos.accionesVista}>
          <ConexionMcp />
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
                  alVer={(id) => {
                    // La ficha abierta era de una persona de la muestra anterior.
                    setFicha(null);
                    return sim.reabrir(id);
                  }}
                />
              )}
              <MenuOpciones sim={sim} />
            </>
          )}
        </div>
      </div>
      </div>
      </>
      )}
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
      {(proceso || analisis) && (
        <button type="button" className={estilos.volverMapa} onClick={() => { setProceso(false); setAnalisis(false); }}>
          <span aria-hidden="true">←</span> Volver al mapa
        </button>
      )}
      {puntos && !procesoMontado && !analisis && fase !== 'cargando' && conexion && (
        <Voces voces={sim.voces} caso={viendo} agentes={conexion.agentes} elegibles={muestra.elegido} ubicar={ubicar} alHablar={alHablar} alMoverVista={alMoverVista} activo={fase === 'corriendo' && !listo && !oculta && !hojaCompleta} deseando={fase === 'preparar' && !oculta && !hojaCompleta} franja={movil} />
      )}
      <div className={estilos.zoom} role="group" aria-label="Acercamiento del mapa">
        <div className={estilos.parZoom}>
          {/* Siempre montado, sobre − y +: sube y se retira con una animación en vez de saltar. */}
          <div className={estilos.verTodo} data-visible={zoom > 1 || undefined} data-mapa inert={zoom <= 1}>
            <button type="button" onClick={() => escena.current?.restablecerSuave()}>
              Ver todo
            </button>
          </div>
          <button type="button" data-mapa aria-label="Alejar" disabled={zoom <= 1} onClick={() => escena.current?.acercarSuave(1 / 1.5)}>
            <svg viewBox="0 0 12 12" aria-hidden="true">
              <path d="M2 6h8" />
            </svg>
          </button>
          <button type="button" data-mapa aria-label="Acercar" disabled={zoom >= ZOOM_MAXIMO} onClick={() => escena.current?.acercarSuave(1.5)}>
            <svg viewBox="0 0 12 12" aria-hidden="true">
              <path d="M2 6h8M6 2v8" />
            </svg>
          </button>
        </div>
      </div>
      {ficha && conexion && (
        <FichaAgente agente={conexion.agentes[ficha.agente]} casos={casos} viendo={viendo} x={ficha.x} y={ficha.y} preguntas={sim.encuesta} alCerrar={() => setFicha(null)} />
      )}
      {encuestaMontada && fase === 'preparar' && <CajonEncuesta abierto={encuestaAbierta} alCerrar={cerrarEncuesta} />}
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
