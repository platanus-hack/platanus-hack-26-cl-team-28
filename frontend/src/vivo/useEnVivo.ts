import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { mezclar } from '../dominio/azar';
import { REGIONES } from '../dominio/catalogos';
import { porcentajes, type Conteo, type Porcentajes } from '../dominio/metricas';
import { repartirPorRegion } from '../dominio/muestra';
import { letraDe } from '../dominio/textos';
import type { Persona, Postura } from '../dominio/tipos';
import { useBorradores } from '../estado/useBorradores';
import { cargarComunas, comunasCargadas } from '../mapa/geografia';
import {
  correrRemoto,
  pedirEstado,
  pedirMuestra,
  subirDocumento,
  type AgenteRemoto,
  type CasoPedido,
  type EstadoMotor,
  type Evento,
  type Metricas,
} from './api';
import { agentesDeDemostracion, correrDemostracion } from './demoLocal';
import { olvidarEncuestaGuardada, PREGUNTAS } from './encuesta';
import { poblacionDeAgentes } from './poblacion';
import { coincide, filtrosDePartida, retratoDelMotor, retratoLocal, type FiltrosVivo, type Retrato } from './sociedad';
import { CASOS_VALIDACION, type Referencia } from './validacion';

type Anillo = number[][];

export type FaseVivo = 'cargando' | 'preparar' | 'corriendo' | 'resultados';

/** Tamaños de muestra, en agentes. */
export const TAMANOS_AGENTES = [250, 500, 1000, 2000, 5000, 10000] as const;
const TAMANO_INICIAL = 1000;
const FILTROS_DE_PARTIDA: FiltrosVivo = filtrosDePartida(TAMANO_INICIAL);
/**
 * Milisegundos que se espera tras el último cambio de filtros antes de pedir la muestra al motor:
 * lo justo para que arrastrar el control de edad no dispare un pedido por cada paso.
 */
const PAUSA_MUESTRA = 40;
export const MAXIMO_VARIANTES = 6;
export const MAXIMO_ITERACIONES = 3;
/** Segundos que se queda en pantalla una variante ya respondida antes de pasar a la siguiente. */
const RETENCION = 5.5;
/** Las voces recientes que se guardan para mostrarlas sobre el mapa. */
const VOCES_GUARDADAS = 60;

export interface CasoVivo {
  id: string;
  letra: string;
  texto: string;
  titulo: string;
  iteracion: { de: string; numero: number; cambio: string } | null;
  referencia?: Referencia;
  /** Acuerdo de 1 a 7 de cada agente (índice global); cero mientras no responde. */
  acuerdo: Int8Array;
  frase: string[];
  /** Las notas de 1 a 7 de cada agente a todas las preguntas de la encuesta. */
  notas: (number[] | undefined)[];
  respondidas: number;
  /** En qué tanda de respuestas llegó cada agente (desde 1): cada tanda es un lote, una llamada al modelo. */
  lote: Int32Array;
  lotes: number;
  /** Cuántas respuestas vinieron de la caché del motor (ya se habían preguntado antes). */
  desdeCache: number;
  conteo: Conteo;
  listo: boolean;
}

export interface Voz {
  agente: number;
  caso: number;
  acuerdo: number;
  frase: string;
}

export interface Conexion {
  estado: EstadoMotor | null;
  /** Con el motor en vivo: la muestra que el motor sorteó para los filtros actuales. En demostración: todos. */
  agentes: AgenteRemoto[];
  puntos: Persona[];
  demo: boolean;
  /**
   * La muestra del motor: su identificador, cuántos agentes cumplen los filtros, a cuántas
   * personas representan y el retrato de la población con esos filtros.
   */
  muestra: { id: string; disponibles: number; representadas: number; retrato?: Retrato } | null;
}

export const posturaDe = (acuerdo: number): Postura => (acuerdo >= 5 ? 'favor' : acuerdo <= 3 ? 'contra' : 'indecisa');

/**
 * Mensaje para la persona: los errores que el motor redacta para humanos pasan tal cual;
 * los técnicos (códigos HTTP, excepciones) se cambian por uno claro.
 */
function humano(error: unknown, porDefecto: string): string {
  const texto = error instanceof Error ? error.message : '';
  return !texto || /\d{3}|Error|Errno|Exception|fetch/i.test(texto) ? porDefecto : texto;
}

const METRICAS_CERO: Metricas = { llamadas: 0, costo_usd: 0, tokens: 0, segundos: 0 };
const conteoVacio = (): Conteo => ({ favor: 0, contra: 0, indecisa: 0, total: 0 });

export interface MuestraVivo {
  /** Índices de los agentes elegidos. */
  agentes: number[];
  /** 1 si el agente está en la muestra. */
  elegido: Uint8Array;
  /** Cuántos agentes cumplen los filtros antes de recortar al tamaño pedido. */
  disponibles: number;
  total: number;
  /** Personas de la población a las que representan quienes cumplen los filtros, si el motor lo informa. */
  representadas?: number;
}

function elegir(agentes: AgenteRemoto[], filtros: FiltrosVivo): MuestraVivo {
  const posibles = agentes.filter((a) => coincide(a, filtros));
  // Orden sorteado pero fijo: al achicar la muestra no se pierde una región entera.
  posibles.sort((a, b) => mezclar(a.i, 31) - mezclar(b.i, 31));
  // Cada región aporta en proporción a las personas que representa. El motor reparte además por
  // comuna y zona; los agentes de la demo no traen esos datos.
  const porRegion: AgenteRemoto[][] = REGIONES.map(() => []);
  for (const a of posibles) porRegion[a.region]?.push(a);
  const cuotas = repartirPorRegion(
    filtros.tamano,
    porRegion.map((lista) => lista.reduce((suma, a) => suma + (a.representa ?? 1), 0)),
    porRegion.map((lista) => lista.length),
  );
  const entra = new Set(porRegion.flatMap((lista, region) => lista.slice(0, cuotas[region])));
  const tomados = posibles.filter((a) => entra.has(a)).map((a) => a.i);
  const elegido = new Uint8Array(agentes.length);
  for (const i of tomados) elegido[i] = 1;
  return { agentes: tomados, elegido, disponibles: posibles.length, total: tomados.length };
}

/** Con el motor en vivo, el motor ya filtró y sorteó: van todos los agentes que mandó. */
function todos(conexion: Conexion): MuestraVivo {
  const agentes = conexion.agentes.map((a) => a.i);
  return {
    agentes,
    elegido: new Uint8Array(agentes.length).fill(1),
    disponibles: conexion.muestra?.disponibles ?? agentes.length,
    total: agentes.length,
    representadas: conexion.muestra?.representadas,
  };
}

const INICIALES = [{ texto: CASOS_VALIDACION[0].texto, referencia: CASOS_VALIDACION[0].referencia }];

/** Estado de la herramienta conectada al motor: muestra, variantes y la corrida que llega en vivo. */
export function useEnVivo(regiones: Anillo[][], puntosDeseados: number) {
  const [conexion, setConexion] = useState<Conexion | null>(null);
  const edicion = useBorradores(INICIALES);
  const { borradores, fijar } = edicion;
  const [filtros, setFiltros] = useState<FiltrosVivo>(FILTROS_DE_PARTIDA);
  /** Los filtros de la muestra que está en pantalla, para no volver a pedirla. */
  const pedida = useRef(JSON.stringify(FILTROS_DE_PARTIDA));
  const [buscando, setBuscando] = useState(false);
  const [iteraciones, setIteraciones] = useState(0);
  /** La encuesta de la corrida en pantalla (vacía antes de la primera): siempre la misma, fija. */
  const [encuesta, setEncuesta] = useState<readonly string[]>([]);
  const [fase, setFase] = useState<FaseVivo>('cargando');
  const [viendo, setViendo] = useState(0);
  const [version, setVersion] = useState(0);
  const [metricas, setMetricas] = useState<Metricas>(METRICAS_CERO);
  const [redactando, setRedactando] = useState<number | null>(null);
  const [terminada, setTerminada] = useState(false);
  const [aviso, setAviso] = useState<string | null>(null);
  const casos = useRef<CasoVivo[]>([]);
  const voces = useRef<Voz[]>([]);
  const cancelar = useRef<(() => void) | null>(null);
  const pintar = useRef(0);

  // Conexión con el motor; sin motor queda la demostración en el navegador, rotulada como tal.
  useEffect(() => {
    let vigente = true;
    (async () => {
      let estado: EstadoMotor | null = null;
      let agentes: AgenteRemoto[];
      let muestra: Conexion['muestra'] = null;
      // Los polígonos de las comunas llegan antes que los puntos: cada persona se ubica una vez.
      const comunas = cargarComunas();
      try {
        estado = await pedirEstado();
        const remota = await pedirMuestra(FILTROS_DE_PARTIDA);
        agentes = remota.agentes;
        muestra = { id: remota.id, disponibles: remota.disponibles, representadas: remota.representadas, retrato: retratoDelMotor(remota.retrato) };
      } catch {
        estado = null;
        agentes = agentesDeDemostracion(regiones);
      }
      const geo = await comunas;
      if (!vigente) return;
      const porAgente = Math.max(1, Math.round(puntosDeseados / Math.max(1, agentes.length)));
      setConexion({ estado, agentes, puntos: poblacionDeAgentes(agentes, porAgente, regiones, geo), demo: estado === null, muestra });
      // La encuesta es fija: lo que haya quedado escrito de cuando se podía editar se borra.
      olvidarEncuestaGuardada();
      setFase('preparar');
    })();
    return () => {
      vigente = false;
      cancelar.current?.();
    };
  }, [regiones, puntosDeseados]);

  // Con el motor en vivo, cada cambio de filtros le pide una muestra nueva: él filtra la población
  // completa y sortea hasta el máximo pedido. Con una corrida en pantalla no se pide: ahí los
  // filtros solo eligen a quiénes se mira.
  const enVivo = !!conexion && !conexion.demo;
  useEffect(() => {
    if (!enVivo || fase !== 'preparar') return;
    const clave = JSON.stringify(filtros);
    if (clave === pedida.current) return;
    const control = new AbortController();
    setBuscando(true);
    const espera = window.setTimeout(async () => {
      try {
        const remota = await pedirMuestra(filtros, control.signal);
        pedida.current = clave;
        const porAgente = Math.max(1, Math.round(puntosDeseados / Math.max(1, remota.agentes.length)));
        setConexion(
          (previa) =>
            previa && {
              ...previa,
              agentes: remota.agentes,
              puntos: poblacionDeAgentes(remota.agentes, porAgente, regiones, comunasCargadas() ?? {}),
              muestra: { id: remota.id, disponibles: remota.disponibles, representadas: remota.representadas, retrato: retratoDelMotor(remota.retrato) },
            },
        );
        setBuscando(false);
      } catch (error) {
        if (control.signal.aborted) return;
        setBuscando(false);
        setAviso(humano(error, 'El motor no pudo armar la muestra. Intenta de nuevo en unos segundos.'));
      }
    }, PAUSA_MUESTRA);
    return () => {
      window.clearTimeout(espera);
      control.abort();
    };
  }, [enVivo, fase, filtros, regiones, puntosDeseados]);

  const muestra = useMemo<MuestraVivo>(() => {
    if (!conexion) return { agentes: [], elegido: new Uint8Array(0), disponibles: 0, total: 0 };
    return conexion.demo ? elegir(conexion.agentes, filtros) : todos(conexion);
  }, [conexion, filtros]);

  // Con una corrida en pantalla, la muestra queda fija y los filtros eligen a quiénes se mira dentro de ella.
  const [corrida, setCorrida] = useState<MuestraVivo | null>(null);
  const enCorrida = (fase === 'corriendo' || fase === 'resultados') && corrida !== null;
  const vista = useMemo<MuestraVivo>(() => {
    if (!enCorrida || !conexion || !corrida) return muestra;
    const agentes = corrida.agentes.filter((i) => coincide(conexion.agentes[i], filtros));
    const elegido = new Uint8Array(conexion.agentes.length);
    for (const i of agentes) elegido[i] = 1;
    return { agentes, elegido, disponibles: corrida.total, total: agentes.length };
  }, [enCorrida, conexion, corrida, muestra, filtros]);
  const filtrada = enCorrida && corrida !== null && vista.total < corrida.total;

  // El retrato que dibuja cada filtro. Al preparar lo calcula el motor sobre toda la población;
  // con una corrida en pantalla (o sin motor) se cuenta aquí, entre los agentes que hay.
  const retrato = useMemo<Retrato | null>(() => {
    if (!conexion) return null;
    if (enCorrida && corrida) return retratoLocal(corrida.agentes.map((i) => conexion.agentes[i]), filtros);
    return (!conexion.demo && conexion.muestra?.retrato) || retratoLocal(conexion.agentes, filtros);
  }, [conexion, enCorrida, corrida, filtros]);

  // Los conteos de cada variante se calculan sobre quienes se están mirando.
  useMemo(() => {
    for (const caso of casos.current) {
      const conteo = conteoVacio();
      for (const i of vista.agentes) {
        const acuerdo = caso.acuerdo[i];
        if (!acuerdo) continue;
        conteo[posturaDe(acuerdo)] += 1;
        conteo.total += 1;
      }
      caso.conteo = conteo;
    }
    // `version` cambia con cada respuesta que llega.
  }, [vista, version]);

  const refrescar = useCallback(() => {
    if (pintar.current) return;
    pintar.current = requestAnimationFrame(() => {
      pintar.current = 0;
      setVersion((v) => v + 1);
    });
  }, []);

  const nuevoCaso = useCallback(
    (base: { id: string; letra: string; texto: string; titulo?: string; iteracion?: CasoVivo['iteracion']; referencia?: Referencia }): CasoVivo => ({
      id: base.id,
      letra: base.letra,
      texto: base.texto,
      titulo: base.titulo || base.texto,
      iteracion: base.iteracion ?? null,
      referencia: base.referencia,
      acuerdo: new Int8Array(conexion?.agentes.length ?? 0),
      frase: [],
      notas: [],
      lote: new Int32Array(conexion?.agentes.length ?? 0),
      lotes: 0,
      respondidas: 0,
      desdeCache: 0,
      conteo: conteoVacio(),
      listo: false,
    }),
    [conexion],
  );

  // Cada evento del motor se aplica aquí. `loteFijo`: el número de lote, cuando el evento viene
  // de la cola que reparte las respuestas de un mismo lote en varios cuadros.
  const aplicar = useCallback(
    (evento: Evento, loteFijo?: number) => {
      const lista = casos.current;
      switch (evento.tipo) {
        case 'inicio':
          // El motor confirma con qué preguntas corre.
          if (evento.preguntas?.length) setEncuesta(evento.preguntas);
          break;
        case 'respuestas': {
          const caso = lista[evento.caso];
          if (!caso) return;
          const lote = loteFijo ?? caso.lotes + 1;
          caso.lotes = Math.max(caso.lotes, lote);
          for (const [agente, acuerdo, frase, notas] of evento.r) {
            if (caso.acuerdo[agente]) continue;
            caso.acuerdo[agente] = acuerdo;
            caso.lote[agente] = lote;
            caso.frase[agente] = frase;
            caso.notas[agente] = notas;
            caso.respondidas += 1;
            if (evento.cache) caso.desdeCache += 1;
            if (frase) voces.current.push({ agente, caso: evento.caso, acuerdo, frase });
          }
          if (voces.current.length > VOCES_GUARDADAS) voces.current.splice(0, voces.current.length - VOCES_GUARDADAS);
          setMetricas(evento.metricas);
          break;
        }
        case 'voces': {
          const caso = lista[evento.caso];
          if (!caso) return;
          for (const [agente, frase] of evento.r) {
            caso.frase[agente] = frase;
            voces.current.push({ agente, caso: evento.caso, acuerdo: caso.acuerdo[agente], frase });
          }
          setMetricas(evento.metricas);
          break;
        }
        case 'caso_listo':
          if (lista[evento.caso]) lista[evento.caso].listo = true;
          setMetricas(evento.metricas);
          break;
        case 'redactando':
          setRedactando(evento.numero);
          setMetricas(evento.metricas);
          break;
        case 'caso':
          lista[evento.caso] = nuevoCaso({ id: evento.id, letra: evento.letra, texto: evento.texto, titulo: evento.titulo, iteracion: evento.iteracion });
          setRedactando(null);
          setMetricas(evento.metricas);
          break;
        case 'aviso':
          setAviso(evento.mensaje);
          break;
        case 'fin':
          setMetricas(evento.metricas);
          setRedactando(null);
          setTerminada(true);
          break;
        case 'error':
          setAviso(humano(new Error(evento.mensaje), 'La simulación se interrumpió. Lo que alcanzó a responder queda en pantalla.'));
          setRedactando(null);
          setTerminada(true);
          // Lo que alcanzó a terminar se puede mirar; si no terminó nada, se vuelve a preparar.
          setFase(lista.some((c) => c.listo) ? 'resultados' : 'preparar');
          break;
        default:
          break;
      }
      refrescar();
    },
    [nuevoCaso, refrescar],
  );

  // Las respuestas llegan de a un lote entero (20 personas de golpe) y varios lotes terminan casi
  // juntos: aplicadas tal cual, el avance salta. Aquí se reparten en unos pocos cuadros, en orden,
  // para que el contador y el mapa avancen parejo. El resto de los eventos espera su turno en la
  // misma cola, así una variante no se da por terminada antes de mostrar sus últimas respuestas.
  const cola = useRef<{ evento: Evento; lote?: number }[]>([]);
  const filasEnCola = useRef(0);
  const lotesVistos = useRef<number[]>([]);
  const bomba = useRef(0);
  const vaciarCola = useCallback(() => {
    cancelAnimationFrame(bomba.current);
    bomba.current = 0;
    cola.current = [];
    filasEnCola.current = 0;
    lotesVistos.current = [];
  }, []);
  const bombear = useCallback(() => {
    bomba.current = 0;
    // Lo que haya en cola se termina de mostrar en menos de medio segundo; con la pestaña oculta, de una vez.
    let presupuesto = document.hidden ? Infinity : Math.max(3, Math.ceil(filasEnCola.current / 24));
    while (cola.current.length) {
      const { evento, lote } = cola.current[0];
      const esFila = evento.tipo === 'respuestas';
      if (esFila && presupuesto <= 0) break;
      cola.current.shift();
      if (esFila) {
        presupuesto -= 1;
        filasEnCola.current -= 1;
      }
      aplicar(evento, lote);
    }
    if (cola.current.length) bomba.current = requestAnimationFrame(bombear);
  }, [aplicar]);
  const alEvento = useCallback(
    (evento: Evento) => {
      if (evento.tipo === 'respuestas') {
        const lote = (lotesVistos.current[evento.caso] = (lotesVistos.current[evento.caso] ?? 0) + 1);
        for (const fila of evento.r) cola.current.push({ evento: { ...evento, r: [fila] }, lote });
        filasEnCola.current += evento.r.length;
      } else cola.current.push({ evento });
      if (document.hidden) bombear();
      else if (!bomba.current) bomba.current = requestAnimationFrame(bombear);
    },
    [bombear],
  );

  const listos = borradores.filter((b) => (b.texto.trim() || b.leido) && !b.leyendo);
  const leyendo = borradores.some((b) => b.leyendo);
  const puedePreguntar = !!conexion && fase === 'preparar' && listos.length > 0 && !leyendo && !buscando && muestra.total > 0;

  const preguntar = useCallback(async () => {
    if (!puedePreguntar || !conexion) return;
    const pedidos: CasoPedido[] = listos.slice(0, MAXIMO_VARIANTES).map((b, k) => ({
      id: String(b.id),
      letra: letraDe(k),
      texto: b.texto.trim(),
      documento: b.leido,
    }));
    casos.current = pedidos.map((p, k) =>
      nuevoCaso({ id: p.id, letra: p.letra, texto: p.texto, titulo: p.texto || p.documento?.titulo, referencia: listos[k].referencia }),
    );
    voces.current = [];
    vaciarCola();
    setMetricas(METRICAS_CERO);
    setTerminada(false);
    setAviso(null);
    setRedactando(null);
    setViendo(0);
    setCorrida(muestra);
    setEncuesta(PREGUNTAS);
    setFase('corriendo');
    const pedido = {
      casos: pedidos,
      muestra: conexion.muestra?.id,
      agentes: muestra.agentes,
      iteraciones: Math.min(iteraciones, MAXIMO_VARIANTES + 2 - pedidos.length),
    };
    try {
      cancelar.current = conexion.demo ? correrDemostracion(pedido, alEvento) : await correrRemoto(pedido, alEvento);
    } catch (error) {
      setAviso(humano(error, 'El motor de simulación no respondió. Intenta de nuevo en unos segundos.'));
      setFase('preparar');
    }
  }, [puedePreguntar, conexion, listos, nuevoCaso, muestra.agentes, iteraciones, alEvento]);

  // Recorrido automático: cada variante respondida queda unos segundos y se pasa a la siguiente.
  const casoActual = casos.current[viendo];
  const actualListo = casoActual?.listo ?? false;
  const cantidad = casos.current.length;
  useEffect(() => {
    if (fase !== 'corriendo' || !actualListo) return;
    const hayOtra = viendo + 1 < cantidad;
    if (!hayOtra && !terminada) return;
    // La primera variante con encuesta real se queda más: ahí se muestra la comparación con Cadem.
    const segundos = RETENCION + 1;
    const espera = window.setTimeout(() => (hayOtra ? setViendo(viendo + 1) : setFase('resultados')), segundos * 1000);
    return () => window.clearTimeout(espera);
  }, [fase, actualListo, viendo, cantidad, terminada]);

  const adjuntarArchivo = useCallback(
    async (id: number, archivo: File | undefined) => {
      if (!archivo) return edicion.adjuntar(id, undefined);
      edicion.adjuntar(id, { nombre: archivo.name, tamano: archivo.size, archivo });
      fijar(id, { leyendo: true });
      try {
        const leido = conexion?.demo
          ? { nombre: archivo.name, titulo: archivo.name, texto: (await archivo.text()).slice(0, 8000) }
          : await subirDocumento(archivo);
        fijar(id, { leido, leyendo: false });
      } catch (error) {
        fijar(id, { leyendo: false, errorDocumento: humano(error, 'No pudimos leer este documento. Prueba con un PDF con texto, un .docx o un .txt.') });
      }
    },
    [conexion, edicion, fijar],
  );

  const detener = useCallback(() => {
    cancelar.current?.();
    cancelar.current = null;
    vaciarCola();
    setFase('preparar');
  }, []);

  return {
    conexion,
    ...edicion,
    adjuntarArchivo,
    filtros,
    setFiltros,
    /** Cuánta gente hay en cada opción de cada filtro, entre quienes cumplen los demás. */
    retrato,
    iteraciones,
    setIteraciones,
    /** La encuesta, fija: la misma en cada corrida. */
    preguntas: PREGUNTAS,
    /** Las preguntas de la corrida en pantalla, en el orden de las notas de cada agente. */
    encuesta,
    fase,
    viendo,
    setViendo,
    version,
    casos: casos.current,
    voces,
    metricas,
    redactando,
    terminada,
    aviso,
    /** A quiénes se mira: la muestra que se va a consultar o, con una corrida en pantalla, los de esa corrida que pasan los filtros. */
    muestra: vista,
    /** Agentes de la corrida en pantalla (sin filtrar). */
    totalCorrida: corrida?.total ?? 0,
    filtrada,
    /** El motor está armando la muestra para los filtros nuevos. */
    buscando,
    puedePreguntar,
    preguntar,
    detener,
    volver: () => {
      cancelar.current?.();
      vaciarCola();
      setFase('preparar');
    },
  };
}

export type EnVivo = ReturnType<typeof useEnVivo>;

export function porcentajesDe(caso: CasoVivo): Porcentajes {
  return porcentajes(caso.conteo);
}
