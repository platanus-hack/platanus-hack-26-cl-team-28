import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties, type MutableRefObject } from 'react';
import type { AgenteRemoto } from '../vivo/api';
import { posturaDe, type Voz } from '../vivo/useEnVivo';
import { bolsaDeDeseos, mismaComuna, type Deseo } from './deseos';
import estilos from './Voces.module.css';

interface Props {
  voces: MutableRefObject<Voz[]>;
  caso: number;
  agentes: AgenteRemoto[];
  /** Quiénes pueden decir un deseo: los agentes de la muestra, distinto de cero por índice. */
  elegibles?: ArrayLike<number>;
  /** Pantalla donde está dibujado el agente; null si no se puede ubicar. */
  ubicar(agente: number): [number, number] | null;
  alHablar(agentes: number[]): void;
  /** Avisa cada vez que el mapa se mueve o se acerca; devuelve cómo dejar de escuchar. */
  alMoverVista(oyente: () => void): () => void;
  /** Hay una encuesta en curso: aparecen las frases de quienes responden. */
  activo: boolean;
  /** Todavía no se pregunta nada: de vez en cuando alguien dice qué política le gustaría ver. */
  deseando: boolean;
  /**
   * En el teléfono no hay lugar para un globo junto a cada punto: una frase a la vez, a todo el
   * ancho y sobre la hoja de abajo. El punto de quien habla se sigue resaltando en el mapa.
   */
  franja?: boolean;
}

type Lado = 'izquierda' | 'derecha';
/** Los tres lugares donde puede haber un globo: una frase por lado y, de vez en cuando, un deseo. */
type Sitio = Lado | 'deseo';
const SITIOS: readonly Sitio[] = ['izquierda', 'derecha', 'deseo'];

interface Globo {
  clave: number;
  agente: number;
  lado: Lado;
  /** Lo que le da color: la postura de quien habla o, en las frases prehechas, `deseo`. */
  tono: string;
  frase: string;
  /** Lo que va bajo la frase en vez de la descripción de la persona: la firma de un deseo. */
  pie?: string;
  saliendo?: boolean;
}
type Globos = Partial<Record<Sitio, Globo>>;

/** Cada cuánto se busca una frase nueva, alternando lados. */
const CADA = 1400;
/** Lo que dura una frase si no llega otra a reemplazarla: sin esto, las últimas quedaban fijas. */
const DURA = 6000;
const DURA_DESEO = 8000;
/** Lo que se espera antes de sacar un globo que se va: la animación `salir` (600 ms) y un respiro. */
const SALIDA = 660;
/** Los deseos son esporádicos: el primero tarda un poco y los demás llegan cada tanto, al azar. */
const PRIMER_DESEO = 4000;
const ENTRE_DESEOS: readonly [number, number] = [12_000, 18_000];
/** Si un deseo no encontró lugar, se vuelve a intentar pronto en vez de esperar el turno entero. */
const REINTENTO = 3000;
const INTENTOS = 12;
const MARGEN = 16;
/** Distancia entre el punto de quien habla y su globo. */
const LEJOS = 30;
/** Alto con que se calcula si dos globos se tapan: el real depende del largo de la frase. */
const ALTO = 180;
const HOLGURA = 12;
/** A la derecha hablan quienes están a favor y a la izquierda quienes están en contra, como vuelan después. */
const PREFIERE: Record<Lado, string> = { derecha: 'favor', izquierda: 'contra' };
/** Dónde se prueba poner un deseo, en orden. */
const LADOS_DESEO: readonly Lado[] = ['derecha', 'izquierda'];
/** Con la pestaña oculta no se muestran frases que nadie va a leer. */
const enPausa = (): boolean => document.hidden;

/** En la franja basta con que quien habla se vea en el mapa: su frase no va junto a su punto. */
function seVe(lugar: [number, number] | null): boolean {
  return !!lugar && lugar[0] >= 0 && lugar[0] <= window.innerWidth && lugar[1] >= MARGEN && lugar[1] <= window.innerHeight - MARGEN;
}

const anchoGlobo = (): number => Math.round(Math.max(260, Math.min(380, window.innerWidth * 0.2)));

interface Caja {
  izq: number;
  /** En la mitad de abajo de la pantalla el globo se cuelga de su borde inferior y crece hacia arriba. */
  abajo: boolean;
  /** El borde del que cuelga: el de arriba o, si `abajo`, el de abajo. */
  borde: number;
}

/** Dónde va el globo de alguien dibujado en (x, y); null si esa persona no se ve o el globo no cabe a ese lado. */
function cajaDe(lado: Lado, [x, y]: [number, number], ancho: number): Caja | null {
  const { innerWidth, innerHeight } = window;
  if (!(x >= 0 && x <= innerWidth && y >= MARGEN && y <= innerHeight - MARGEN)) return null;
  const izq = lado === 'derecha' ? x + LEJOS : x - LEJOS - ancho;
  if (izq < MARGEN || izq + ancho > innerWidth - MARGEN) return null;
  const abajo = y > innerHeight / 2;
  return { izq, abajo, borde: abajo ? Math.min(innerHeight - MARGEN, y + 40) : Math.max(MARGEN, y - 40) };
}

function seTapan(a: Caja, b: Caja, ancho: number): boolean {
  const arriba = (c: Caja) => (c.abajo ? c.borde - ALTO : c.borde);
  return (
    a.izq < b.izq + ancho + HOLGURA &&
    b.izq < a.izq + ancho + HOLGURA &&
    arriba(a) < arriba(b) + ALTO + HOLGURA &&
    arriba(b) < arriba(a) + ALTO + HOLGURA
  );
}

/** Quién es, en pocas palabras: lo que diría un subtítulo. */
export function quienEs(agente: AgenteRemoto): string {
  const genero = agente.atributos['Género'] ?? agente.atributos.Sexo ?? '';
  const quien = genero.startsWith('F') || genero === 'Mujer' ? 'Mujer' : genero.startsWith('M') || genero === 'Hombre' ? 'Hombre' : 'Persona';
  return [`${quien}, ${agente.edad}`, agente.comuna].filter(Boolean).join(' · ');
}

/**
 * Mientras los agentes responden, frases reales aparecen junto al punto de quien las dijo: a la
 * derecha alguien a favor, a la izquierda alguien en contra. Así la escala se ve humana.
 *
 * Antes de preguntar, con el país a la espera, cada tanto aparece un deseo en otro color: una
 * política que a alguien de la muestra le gustaría ver. Esos no los dijo el modelo: salen de las
 * frases prehechas de `deseos.ts`.
 */
export function Voces({ voces, caso, agentes, elegibles, ubicar, alHablar, alMoverVista, activo, deseando, franja = false }: Props) {
  const [globos, setGlobos] = useState<Globos>({});
  const [, setVista] = useState(0);
  const vistas = useRef(new Set<number>());
  const clave = useRef(0);
  const turno = useRef<Lado>('derecha');
  /** Los globos que siguen hablando, sin los que ya se van: a quién resaltar y con quién no chocar. */
  const vivos = useRef<Globos>({});
  /** Por sitio, el reloj pendiente: el que vence al globo o el que termina de sacarlo. */
  const relojes = useRef<Partial<Record<Sitio, number>>>({});
  const siguienteDeseo = useMemo(() => bolsaDeDeseos(), []);
  /** El deseo que tocaba y aún no encontró lugar: se reintenta con ese en vez de saltárselo. */
  const pendiente = useRef<Deseo | null>(null);
  const alHablarActual = useRef(alHablar);
  useEffect(() => {
    alHablarActual.current = alHablar;
  }, [alHablar]);

  const anunciar = useCallback(() => {
    alHablarActual.current(SITIOS.flatMap((s) => (vivos.current[s] ? [vivos.current[s]!.agente] : [])));
  }, []);

  const callar = useCallback(() => {
    for (const sitio of SITIOS) window.clearTimeout(relojes.current[sitio]);
    relojes.current = {};
    vivos.current = {};
  }, []);

  const retirar = useCallback(
    (sitio: Sitio, cual: number) => {
      if (vivos.current[sitio]?.clave !== cual) return;
      delete vivos.current[sitio];
      anunciar();
      setGlobos((g) => (g[sitio]?.clave === cual ? { ...g, [sitio]: { ...g[sitio]!, saliendo: true } } : g));
      relojes.current[sitio] = window.setTimeout(
        () =>
          setGlobos((g) => {
            if (g[sitio]?.clave !== cual) return g;
            const resto = { ...g };
            delete resto[sitio];
            return resto;
          }),
        SALIDA,
      );
    },
    [anunciar],
  );

  const poner = useCallback(
    (sitio: Sitio, globo: Omit<Globo, 'clave'>, dura: number) => {
      const nuevo: Globo = { ...globo, clave: clave.current++ };
      window.clearTimeout(relojes.current[sitio]);
      relojes.current[sitio] = window.setTimeout(() => retirar(sitio, nuevo.clave), dura);
      vivos.current[sitio] = nuevo;
      setGlobos((g) => ({ ...g, [sitio]: nuevo }));
      anunciar();
    },
    [anunciar, retirar],
  );

  /** Si una caja no tapa a ninguno de los globos que están hablando; `salvo`, el sitio que va a ocupar. */
  const libre = useCallback(
    (caja: Caja, ancho: number, salvo: Sitio) =>
      SITIOS.every((sitio) => {
        const otro = sitio === salvo ? undefined : vivos.current[sitio];
        const lugar = otro && ubicar(otro.agente);
        const suya = otro && lugar && cajaDe(otro.lado, lugar, ancho);
        return !suya || !seTapan(caja, suya, ancho);
      }),
    [ubicar],
  );

  // La posición se calcula al dibujar: basta redibujar cuando el mapa se mueve o cambia la ventana.
  useEffect(() => {
    const redibujar = () => setVista((n) => n + 1);
    const soltar = alMoverVista(redibujar);
    window.addEventListener('resize', redibujar);
    return () => {
      soltar();
      window.removeEventListener('resize', redibujar);
    };
  }, [alMoverVista]);

  useEffect(() => {
    vistas.current = new Set();
    callar();
    anunciar();
    setGlobos((g) => (Object.keys(g).length ? {} : g));
  }, [caso, callar, anunciar]);

  /** Despide con un fundido al globo de un sitio, si hay alguno hablando. */
  const soltar = useCallback(
    (sitio: Sitio) => {
      const globo = vivos.current[sitio];
      if (globo) retirar(sitio, globo.clave);
    },
    [retirar],
  );

  // Las frases de la encuesta: una por lado, mientras llegan respuestas.
  useEffect(() => {
    if (!activo) return;
    const tic = window.setInterval(() => {
      if (enPausa()) return;
      const lado = turno.current;
      turno.current = lado === 'derecha' ? 'izquierda' : 'derecha';
      const ancho = anchoGlobo();
      const cabe = (voz: Voz) => {
        const lugar = ubicar(voz.agente);
        if (franja) return seVe(lugar);
        const caja = lugar && cajaDe(lado, lugar, ancho);
        return !!caja && libre(caja, ancho, lado);
      };
      // La más reciente primero, sea cual sea su postura.
      const candidatas = voces.current.filter((v) => v.caso === caso && !vistas.current.has(v.agente) && v.frase.length > 8).reverse();
      const voz =
        candidatas.find((v) => posturaDe(v.acuerdo) === PREFIERE[lado] && cabe(v)) ??
        candidatas.find((v) => posturaDe(v.acuerdo) === 'indecisa' && cabe(v));
      if (!voz) return;
      vistas.current.add(voz.agente);
      // En la franja cabe una sola: la nueva reemplaza a la anterior, alternando posturas.
      poner(franja ? 'derecha' : lado, { agente: voz.agente, lado, tono: posturaDe(voz.acuerdo), frase: voz.frase }, DURA);
    }, franja ? DURA * 0.75 : CADA);
    return () => {
      // Las frases se desvanecen antes de que el país se abra, en vez de cortarse de golpe.
      window.clearInterval(tic);
      soltar('izquierda');
      soltar('derecha');
    };
  }, [activo, caso, voces, ubicar, poner, libre, soltar, franja]);

  // Los deseos: uno cada tanto, mientras nadie ha preguntado nada todavía.
  useEffect(() => {
    if (!deseando || !elegibles) return;
    /** Pone un deseo junto a alguien de la muestra; false si esta vez no hubo dónde. */
    const desear = (): boolean => {
      if (enPausa()) return false;
      const deseo = (pendiente.current ??= siguienteDeseo());
      const { comuna } = deseo;
      const deAhi = (i: number) => !comuna || mismaComuna(agentes[i]?.comuna ?? '', comuna);
      const ancho = anchoGlobo();
      const posibles: number[] = [];
      for (let i = 0; i < elegibles.length; i++) if (elegibles[i] && deAhi(i)) posibles.push(i);
      // Si en la muestra no quedó nadie de esa comuna, sirve cualquiera que viva ahí.
      if (!posibles.length && comuna) for (let i = 0; i < agentes.length; i++) if (deAhi(i)) posibles.push(i);
      // Y si no hay nadie, ese deseo se deja pasar: el siguiente turno trae otro.
      if (!posibles.length) pendiente.current = null;
      for (let intento = 0; intento < INTENTOS && posibles.length; intento++) {
        const agente = posibles[Math.floor(Math.random() * posibles.length)];
        const lugar = ubicar(agente);
        if (!lugar) return false;
        // A la derecha el mapa está despejado; a la izquierda está la propuesta que se escribe.
        for (const lado of LADOS_DESEO) {
          const caja = franja ? null : cajaDe(lado, lugar, ancho);
          if (franja ? !seVe(lugar) : !caja || !libre(caja, ancho, 'deseo')) continue;
          const pie = deseo.firma ? [deseo.firma, comuna].filter(Boolean).join(' · ') : undefined;
          poner('deseo', { agente, lado, tono: 'deseo', frase: deseo.frase, pie }, DURA_DESEO);
          pendiente.current = null;
          return true;
        }
      }
      return false;
    };
    let espera = 0;
    const programar = (ms: number) => {
      espera = window.setTimeout(() => programar(desear() ? ENTRE_DESEOS[0] + Math.random() * (ENTRE_DESEOS[1] - ENTRE_DESEOS[0]) : REINTENTO), ms);
    };
    programar(PRIMER_DESEO);
    return () => {
      window.clearTimeout(espera);
      soltar('deseo');
    };
  }, [deseando, elegibles, agentes, ubicar, poner, libre, soltar, siguienteDeseo, franja]);

  // Al irse (se abre el proceso o el análisis) no quedan relojes ni nadie resaltado.
  useEffect(
    () => () => {
      callar();
      alHablarActual.current([]);
    },
    [callar],
  );

  if (franja) {
    // Con la hoja subida entera la franja quedaría sobre la barra de arriba: se va sin despedirse.
    if (!activo && !deseando) return null;
    return (
      <div className={estilos.franja} aria-hidden="true">
        {SITIOS.map((sitio) => {
          const g = globos[sitio];
          if (!g) return null;
          const agente = agentes[g.agente];
          return (
            <figure key={g.clave} className={estilos.globo} data-postura={g.tono} data-saliendo={g.saliendo || undefined}>
              <blockquote>{g.frase}</blockquote>
              <figcaption>{g.pie ?? (agente ? quienEs(agente) : '')}</figcaption>
            </figure>
          );
        })}
      </div>
    );
  }

  const ancho = anchoGlobo();
  return (
    <div className={estilos.capa} aria-hidden="true">
      {SITIOS.map((sitio) => {
        const g = globos[sitio];
        const lugar = g && ubicar(g.agente);
        const caja = g && lugar && cajaDe(g.lado, lugar, ancho);
        // Si quien habla salió de la pantalla al mover el mapa, su globo no se queda apuntando a nada.
        if (!g || !caja) return null;
        const agente = agentes[g.agente];
        const estilo: CSSProperties = caja.abajo
          ? { left: caja.izq, bottom: window.innerHeight - caja.borde, width: ancho }
          : { left: caja.izq, top: caja.borde, width: ancho };
        return (
          <figure key={g.clave} className={estilos.globo} data-postura={g.tono} data-lado={g.lado} data-ancla={caja.abajo ? 'abajo' : undefined} data-saliendo={g.saliendo || undefined} style={estilo}>
            <blockquote>{g.frase}</blockquote>
            <figcaption>{g.pie ?? (agente ? quienEs(agente) : '')}</figcaption>
          </figure>
        );
      })}
    </div>
  );
}
