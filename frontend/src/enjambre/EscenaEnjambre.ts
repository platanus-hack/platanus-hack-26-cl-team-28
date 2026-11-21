import { mezclar } from '../dominio/azar';
import { REGIONES } from '../dominio/catalogos';
import type { Persona } from '../dominio/tipos';
import { cargarComunas, comunasCargadas, REGIONES_GEO } from '../mapa/geografia';
import { puntoEnBurbuja, radioDe, type Burbuja } from './disposicion';
import { CARAS, celdaWati, CELDA_ALTO, CELDA_ANCHO, crearAtlasWati, crearSpriteWati, PIES_RELATIVO, poseDe, QUIETO, rasgosDe, TONOS, VARIANTES, type Animo, type AtlasWati } from './wati';

/** Estado de cada punto. El número es también su color. */
export const PUNTO = { fuera: 0, neutra: 1, favor: 2, contra: 3, indecisa: 4, pendiente: 5 } as const;
/**
 * `ola`: el país responde de norte a sur. `cambio`: todos a la vez. `aparecer`: cada punto se
 * enciende en su lugar cuando su agente termina, sin volar todavía.
 */
export type ModoVuelo = 'ola' | 'cambio' | 'aparecer' | 'inmediato';

interface Etiqueta {
  /** Borde del texto más cercano a la burbuja. */
  x: number;
  y: number;
  lado: 1 | -1;
  region: number;
  texto: string;
}

/** Con menos personas que esto en la región, el porcentaje engaña: se muestra cuántas son. */
const MINIMO_PARA_PORCENTAJE = 5;

const LAT_NORTE = -17.2;
const GRADOS = 39.1;
/** Un grado de longitud mide cerca de 0,8 grados de latitud a la altura de Chile: el país va en su proporción real. */
const ESTRECHEZ = 0.8;
const LON_CENTRO = -71.4;
const LON_MINIMA = -76.5;
const DPR_MAXIMO = 2;
const VUELO = 1.15;
/** Al cambiar la muestra los puntos solo se reacomodan: un vuelo corto, sin la entrada completa. */
const VUELO_REACOMODO = 0.45;
/** Un punto nuevo sin ninguno cerca no viaja: crece en su lugar durante este tiempo. */
const APARECER = 0.3;
/** Y uno que sobra sin ningún lugar cerca se encoge donde está. */
const DESAPARECER = 0.25;
/** Lado de las celdas con que se busca el punto libre más cercano (píxeles). */
const CELDA = 26;
const DESTELLO = 0.45;
/** Desde este ancho las cifras gigantes van a los costados del lienzo. */
const ANCHO_CON_CIFRAS = 900;

/** Disposición del resultado por filas (píxeles). */
const MARGEN_FILAS = 18;
const ENTRE_FILAS = 4;
const ENTRE_FILAS_MAXIMO = 16;
const SEPARA_ROTULO = 9;

/** Cuánto se puede acercar el mapa: lo bastante para separar las comunas de Santiago y ver a cada wati. */
export const ZOOM_MAXIMO = 64;

/**
 * Al acercar, cada cuadrado se vuelve un wati. La mezcla depende del tamaño del cuadrado en
 * pantalla (píxeles): así en una pantalla chica la transformación llega más tarde.
 */
const WATI_DESDE = 10;
const WATI_HASTA = 12.5;
/** Alto de la celda del wati respecto del lado del cuadrado. */
const WATI_ALTO = 2.2;
/** Ancho de las zonas en que se ralea la multitud, en anchos de wati, y cuántos caben en una zona con una sola persona más. */
const ZONA_WATIS = 2.5;
/** Opacidad de los watis que no son de la persona elegida mientras hay una elegida. */
const ATENUADO = 0.45;
/**
 * Watis muy de cerca: alto máximo de su dibujo (píxeles). Los que están en reposo salen de un
 * atlas grande; los que bostezan, de una hoja que se va llenando con los que aparecen.
 */
const ALTO_GRANDE = 128;
const HOJA_GRANDE = 1536;
const POR_ZONA = 1.6;
/** Los watis respiran y bostezan solo desde este alto en pantalla (píxeles): de lejos quedan quietos. */
const WATI_ANIMA = 56;
/** Respirar no necesita 60 cuadros por segundo: con solo watis en movimiento se redibuja a unos 20. */
const RESPIRO = 1 / 21;

/** Estados sin postura: sus watis varían poco de tono para no parecer de un color de respuesta. */
const SIN_POSTURA: number[] = [PUNTO.fuera, PUNTO.neutra, PUNTO.pendiente];
/** Cara de cada estado (en el orden de `PUNTO`): triste en contra, seria si no se decide. */
const ANIMOS: Animo[] = ['alegre', 'alegre', 'alegre', 'triste', 'seria', 'alegre'];

/** Duración de los acercamientos de los botones, en segundos. */
const DURA_ZOOM = 0.4;
const salida = (p: number) => 1 - (1 - p) ** 3;
const suave = (p: number) => (p < 0.5 ? 4 * p * p * p : 1 - (-2 * p + 2) ** 3 / 2);
const azar = (i: number, sal: number) => (Math.sin(i * 12.9898 + sal * 78.233) * 43758.5453) % 1;

/**
 * Escena de puntos. Cada persona simulada es un punto: en reposo dibujan Chile, y al
 * responder vuelan a burbujas por región, a favor a un lado y en contra al otro.
 */
export class EscenaEnjambre {
  private readonly ctx: CanvasRenderingContext2D;
  private n = 0;
  private casaX!: Float32Array;
  private casaY!: Float32Array;
  private desdeX!: Float32Array;
  private desdeY!: Float32Array;
  private haciaX!: Float32Array;
  private haciaY!: Float32Array;
  private x!: Float32Array;
  private y!: Float32Array;
  private sale!: Float32Array;
  /** Cuánto dura el vuelo en curso de cada punto. */
  private dura!: Float32Array;
  /** Momento en que cada punto se encendió, para el destello de llegada. */
  private llega!: Float32Array;
  /** Momento en que cada punto apareció en su lugar sin venir de otro lado. */
  private nace!: Float32Array;
  /** Puntos que salieron de la muestra y se están encogiendo: x, y y color de cada uno. */
  private idos: number[] = [];
  private inicioIdos = 0;
  private color!: Uint8Array;
  private estados!: Uint8Array;
  /** Rasgos de cada wati, fijos por persona: semilla de su animación, adorno y tono. */
  private semilla!: Uint32Array;
  private variante!: Uint8Array;
  private tono!: Uint8Array;
  /** Orden fijo en que aparecen los watis al ralear una multitud (ver `ralear`): menor, antes. */
  private prioridad!: Float32Array;
  /** Watis que quedaron dibujados en el último cuadro: solo esos se pueden elegir con un clic. */
  private mostrado!: Uint8Array;
  /** Marca rápida de los puntos de `foco`, para no buscarlos en la lista por cada wati. */
  private enFoco!: Uint8Array;
  /** Hoja con los watis dibujados en los colores del tema; se arma la primera vez que hace falta. */
  private atlas: AtlasWati | null = null;
  /** Watis muy de cerca: cada combinación se dibuja aparte, a buena resolución, la primera vez que aparece. */
  private atlasGrande: AtlasWati | null = null;
  private hojaGrande: HTMLCanvasElement | null = null;
  private lugaresGrandes = new Map<number, number>();
  /** Capa con el mapa ya pintado y la vista con que se pintó (ver `pintarMapa`). */
  private readonly capaMapa = document.createElement('canvas');
  private claveMapa = '';
  private esperaAtlas = 0;
  /** Cuánto se ve el wati en vez del cuadrado (0 a 1) y su alto en unidades del mapa, del último cuadro. */
  private mezcla = 0;
  private altoWati = 0;
  private ultimoCuadro = 0;
  /** Índices de los watis visibles, ordenados de arriba abajo (los de abajo quedan delante). */
  private visibles = new Int32Array(0);
  /** Nivel (potencia de dos) de las zonas del raleo; ver `watis`. */
  private nivelZona = NaN;
  private burbujas: Burbuja[] = [];
  private etiquetas: Etiqueta[] = [];
  private colores: string[] = [];
  private tinta = '';
  private fondo = '';
  private chile = '';
  private chileBorde = '';
  private comunaBorde = '';
  private fuente = '';
  private silueta = new Path2D();
  /** Límites de las comunas, tenues bajo los de las regiones. Vacío hasta que cargan los polígonos. */
  private comunas = new Path2D();
  private ancho = 0;
  private alto = 0;
  private dpr = 1;
  private u = 1;
  private paso = 3;
  /** Tamaño de letra de los rótulos de región: crece con la pantalla para leerse en un proyector. */
  private letra = 12;
  /** Separación con que quedaron armadas las burbujas (puede ser menor que `paso` si no cabían). */
  private pasoActual = 3;
  private cuadro = 0;
  private finVuelo = 0;
  private inicioRotulos = 0;
  private sucio = true;
  private pausada = false;
  private zoom = 1;
  private ox = 0;
  private oy = 0;
  private agarre: [number, number] | null = null;
  private arrastro = false;
  private zoomAlPellizcar = 1;
  /** Acercamiento animado de los botones: de dónde viene la vista y adónde va. */
  private transicion: { inicio: number; z0: number; ox0: number; oy0: number; z1: number; ox1: number; oy1: number } | null = null;
  /** Aviso a la interfaz cuando cambia el acercamiento. */
  alCambiarVista?: (zoom: number) => void;
  /** Verdadero cuando los puntos ya volaron a sus burbujas con los estados actuales. */
  private abierta = false;
  /** Mientras hay agentes pensando, la escena se redibuja siempre para que latan. */
  private latiendo = false;
  /** Puntos resaltados con un anillo (la persona que habla o la que se eligió). */
  private foco: number[] = [];
  private readonly reducir = matchMedia('(prefers-reduced-motion: reduce)');
  private readonly observador: ResizeObserver;

  constructor(
    private readonly lienzo: HTMLCanvasElement,
    private personas: Persona[],
  ) {
    this.ctx = lienzo.getContext('2d')!;
    this.reservar(personas.length);
    this.observador = new ResizeObserver(() => this.medir());
  }

  private reservar(n: number): void {
    this.n = n;
    const crear = () => new Float32Array(n);
    [this.casaX, this.casaY, this.desdeX, this.desdeY, this.haciaX, this.haciaY, this.x, this.y, this.sale, this.llega] = [
      crear(), crear(), crear(), crear(), crear(), crear(), crear(), crear(), crear(), crear().fill(-10),
    ];
    this.dura = crear().fill(VUELO);
    this.nace = crear().fill(-10);
    this.color = new Uint8Array(n).fill(PUNTO.neutra);
    this.estados = new Uint8Array(n).fill(PUNTO.neutra);
    this.semilla = new Uint32Array(n);
    this.variante = new Uint8Array(n);
    this.tono = new Uint8Array(n);
    this.prioridad = new Float32Array(n);
    this.mostrado = new Uint8Array(n);
    this.enFoco = new Uint8Array(n);
    this.visibles = new Int32Array(n);
    this.personas.forEach((persona, i) => {
      const rasgos = rasgosDe(persona.clave ?? `#${persona.id}`);
      this.semilla[i] = rasgos.semilla;
      this.variante[i] = rasgos.variante;
      this.tono[i] = rasgos.tono;
      this.prioridad[i] = mezclar(rasgos.semilla, 9);
    });
  }

  /**
   * Cambia a quiénes se dibuja sin volver a armar la escena: quien sigue en la muestra se queda
   * donde está, y cada lugar nuevo lo ocupa el punto libre más cercano. Nadie cruza el mapa: si
   * no hay ninguno cerca, el punto nuevo crece en su lugar, y los que sobran lejos desaparecen.
   * No repite la entrada ni toca el acercamiento.
   */
  reemplazar(personas: Persona[]): void {
    const antes = { n: this.n, x: this.x, y: this.y, color: this.color, personas: this.personas };
    this.personas = personas;
    this.reservar(personas.length);
    this.burbujas = [];
    this.etiquetas = [];
    this.foco = [];
    this.inicioRotulos = 0;
    // Con todos en reposo, el próximo `fijar` con los mismos estados no relanza ningún vuelo.
    this.abierta = true;
    if (!this.ancho) return;
    personas.forEach((persona, i) => {
      [this.casaX[i], this.casaY[i]] = this.proyectar(Math.max(LON_MINIMA, persona.lon), persona.lat);
    });
    const clave = (lista: Persona[], i: number) => lista[i].clave ?? `#${i}`;
    const dondeEstaba = new Map<string, number>();
    for (let j = 0; j < antes.n; j++) dondeEstaba.set(clave(antes.personas, j), j);
    const origen = new Int32Array(this.n).fill(-1);
    const sigue = new Uint8Array(antes.n);
    for (let i = 0; i < this.n; i++) {
      const j = dondeEstaba.get(clave(personas, i));
      if (j === undefined) continue;
      origen[i] = j;
      sigue[j] = 1;
    }
    // Los puntos que ya no están quedan libres, repartidos en celdas para encontrarlos por cercanía.
    const columnas = Math.ceil(this.ancho / CELDA) + 1;
    const filas = Math.ceil(this.alto / CELDA) + 1;
    const celda = (x: number, y: number) =>
      Math.max(0, Math.min(filas - 1, Math.floor(y / CELDA))) * columnas + Math.max(0, Math.min(columnas - 1, Math.floor(x / CELDA)));
    const libres: number[][] = [];
    for (let j = 0; j < antes.n; j++) {
      if (sigue[j]) continue;
      (libres[celda(antes.x[j], antes.y[j])] ??= []).push(j);
    }
    // Hasta dónde puede viajar un punto: más o menos el alto de una región en pantalla.
    const alcance = Math.max(48, this.alto * 0.07);
    const anillos = Math.ceil(alcance / CELDA);
    const tomado = new Uint8Array(antes.n);
    const masCercano = (x: number, y: number): number => {
      const cx = Math.max(0, Math.min(columnas - 1, Math.floor(x / CELDA)));
      const cy = Math.max(0, Math.min(filas - 1, Math.floor(y / CELDA)));
      let mejor = -1;
      let distancia = alcance * alcance;
      for (let fy = Math.max(0, cy - anillos); fy <= Math.min(filas - 1, cy + anillos); fy++) {
        for (let fx = Math.max(0, cx - anillos); fx <= Math.min(columnas - 1, cx + anillos); fx++) {
          const lista = libres[fy * columnas + fx];
          if (!lista) continue;
          for (const j of lista) {
            if (tomado[j]) continue;
            const d = (antes.x[j] - x) ** 2 + (antes.y[j] - y) ** 2;
            if (d < distancia) {
              distancia = d;
              mejor = j;
            }
          }
        }
      }
      return mejor;
    };
    const ahora = performance.now() / 1000;
    const quieto = this.reducir.matches;
    for (let i = 0; i < this.n; i++) {
      let j = origen[i];
      if (j < 0 && !quieto) {
        j = masCercano(this.casaX[i], this.casaY[i]);
        if (j >= 0) tomado[j] = 1;
        // Sin nadie cerca, crece en su lugar en vez de llegar volando desde lejos.
        else this.nace[i] = ahora + Math.abs(azar(i, 6)) * 0.12;
      }
      const viene = j >= 0 && !quieto;
      this.x[i] = this.desdeX[i] = viene ? antes.x[j] : this.casaX[i];
      this.y[i] = this.desdeY[i] = viene ? antes.y[j] : this.casaY[i];
      this.haciaX[i] = this.casaX[i];
      this.haciaY[i] = this.casaY[i];
      this.sale[i] = ahora + Math.abs(azar(i, 4)) * 0.08;
      this.dura[i] = VUELO_REACOMODO;
    }
    // Los que sobran y nadie fue a buscar se encogen donde están.
    this.idos = [];
    this.inicioIdos = ahora;
    if (!quieto) {
      for (let j = 0; j < antes.n; j++) {
        if (!sigue[j] && !tomado[j]) this.idos.push(antes.x[j], antes.y[j], antes.color[j]);
      }
    }
    this.finVuelo = ahora + 0.08 + VUELO_REACOMODO;
    this.sucio = true;
  }

  montar(): void {
    this.actualizarTema();
    this.medir();
    // Entrada: los puntos llegan desde toda la pantalla y arman el país.
    const ahora = performance.now() / 1000;
    for (let i = 0; i < this.n; i++) {
      this.x[i] = this.desdeX[i] = this.reducir.matches ? this.casaX[i] : this.ancho * Math.abs(azar(i, 1));
      this.y[i] = this.desdeY[i] = this.reducir.matches ? this.casaY[i] : this.alto * Math.abs(azar(i, 2));
      this.sale[i] = ahora + Math.abs(azar(i, 3)) * 0.7;
    }
    this.finVuelo = ahora + 0.7 + VUELO;
    this.observador.observe(this.lienzo);
    document.addEventListener('wheel', this.rueda, { passive: false });
    document.addEventListener('gesturestart', this.gesto, { passive: false });
    document.addEventListener('gesturechange', this.gesto, { passive: false });
    this.lienzo.addEventListener('pointerdown', this.baja);
    this.lienzo.addEventListener('pointermove', this.mueve);
    this.lienzo.addEventListener('pointerup', this.sube);
    this.lienzo.addEventListener('pointercancel', this.sube);
    // Los rótulos se dibujan con la fuente de la página: se redibuja cuando termina de cargar.
    void document.fonts.ready.then(() => {
      this.sucio = true;
    });
    this.cuadro = requestAnimationFrame(this.ciclo);
  }

  destruir(): void {
    cancelAnimationFrame(this.cuadro);
    clearTimeout(this.esperaAtlas);
    this.observador.disconnect();
    document.removeEventListener('wheel', this.rueda);
    document.removeEventListener('gesturestart', this.gesto);
    document.removeEventListener('gesturechange', this.gesto);
    this.lienzo.removeEventListener('pointerdown', this.baja);
    this.lienzo.removeEventListener('pointermove', this.mueve);
    this.lienzo.removeEventListener('pointerup', this.sube);
    this.lienzo.removeEventListener('pointercancel', this.sube);
  }

  /** Vuelve a leer los colores de los tokens (al cambiar de tema). */
  actualizarTema(): void {
    const estilo = getComputedStyle(document.documentElement);
    const v = (nombre: string) => estilo.getPropertyValue(nombre).trim();
    this.colores = [v('--punto-fuera'), v('--punto-neutro'), v('--favor'), v('--contra'), v('--indecisa'), v('--punto-pendiente')];
    this.tinta = v('--tinta');
    this.fondo = v('--mar');
    this.chile = v('--chile');
    this.chileBorde = v('--chile-borde');
    this.comunaBorde = v('--comuna-borde');
    this.fuente = v('--fuente-ui');
    this.programarAtlas();
    this.claveMapa = '';
    this.sucio = true;
  }

  /** Dónde está dibujado ahora un punto, en píxeles del lienzo. */
  posicion(i: number): [number, number] {
    return [this.x[i] * this.zoom + this.ox, this.y[i] * this.zoom + this.oy];
  }

  /** Acerca o aleja la vista manteniendo fijo el punto (cx, cy) de la pantalla; sin punto, el centro. */
  acercar(factor: number, cx = this.ancho / 2, cy = this.alto / 2): void {
    this.transicion = null;
    const nuevo = Math.max(1, Math.min(ZOOM_MAXIMO, this.zoom * factor));
    const razon = nuevo / this.zoom;
    this.ox = cx - (cx - this.ox) * razon;
    this.oy = cy - (cy - this.oy) * razon;
    this.zoom = nuevo;
    this.acotar();
  }

  restablecer(): void {
    this.transicion = null;
    this.zoom = 1;
    this.acotar();
  }

  /** Como `acercar`, pero animado: la vista se desliza hasta el nuevo nivel. Varios toques seguidos se suman. */
  acercarSuave(factor: number): void {
    const base = this.transicion ?? { z1: this.zoom, ox1: this.ox, oy1: this.oy };
    const nuevo = Math.max(1, Math.min(ZOOM_MAXIMO, base.z1 * factor));
    const razon = nuevo / base.z1;
    const cx = this.ancho / 2;
    const cy = this.alto / 2;
    this.irA(nuevo, cx - (cx - base.ox1) * razon, cy - (cy - base.oy1) * razon);
  }

  /** Vuelve a la vista completa con la misma animación. */
  restablecerSuave(): void {
    this.irA(1, 0, 0);
  }

  private irA(z1: number, ox1: number, oy1: number): void {
    ox1 = Math.min(0, Math.max(this.ancho * (1 - z1), ox1));
    oy1 = Math.min(0, Math.max(this.alto * (1 - z1), oy1));
    if (this.reducir.matches) {
      this.transicion = null;
      this.zoom = z1;
      this.ox = ox1;
      this.oy = oy1;
      this.acotar();
      return;
    }
    this.transicion = { inicio: performance.now() / 1000, z0: this.zoom, ox0: this.ox, oy0: this.oy, z1, ox1, oy1 };
    this.sucio = true;
  }

  /** Un paso de la animación: el zoom crece de forma geométrica y el punto fijo de la vista se mantiene. */
  private avanzarZoom(ahora: number): void {
    const t = this.transicion;
    if (!t) return;
    const p = Math.min(1, (ahora - t.inicio) / DURA_ZOOM);
    const e = salida(p);
    if (p >= 1) {
      this.transicion = null;
      this.zoom = t.z1;
      this.ox = t.ox1;
      this.oy = t.oy1;
    } else {
      const z = t.z0 * (t.z1 / t.z0) ** e;
      const k = z / t.z0;
      const r = t.z1 / t.z0;
      if (r === 1) {
        this.ox = t.ox0 + (t.ox1 - t.ox0) * e;
        this.oy = t.oy0 + (t.oy1 - t.oy0) * e;
      } else {
        // El punto de la pantalla que no se mueve en todo el trayecto.
        const fx = (t.ox1 - t.ox0 * r) / (1 - r);
        const fy = (t.oy1 - t.oy0 * r) / (1 - r);
        this.ox = fx - (fx - t.ox0) * k;
        this.oy = fy - (fy - t.oy0) * k;
      }
      this.zoom = z;
    }
    this.acotar();
  }

  /** Cuánto está acercada la vista (1: completa). */
  nivel(): number {
    return this.zoom;
  }

  /** Verdadero una vez si el último gesto fue un arrastre: ese clic no debe abrir una ficha. */
  huboArrastre(): boolean {
    const valor = this.arrastro;
    this.arrastro = false;
    return valor;
  }

  /** La vista nunca deja ver más allá de los bordes del lienzo. */
  private acotar(): void {
    this.ox = Math.min(0, Math.max(this.ancho * (1 - this.zoom), this.ox));
    this.oy = Math.min(0, Math.max(this.alto * (1 - this.zoom), this.oy));
    this.sucio = true;
    this.alCambiarVista?.(this.zoom);
  }

  /**
   * Rueda sobre el mapa, o pellizco en el trackpad en cualquier parte (el navegador lo entrega como
   * rueda con Ctrl). Se acerca el mapa redibujándolo, nítido; si no se cancelara, el navegador
   * ampliaría la página entera como una imagen borrosa.
   */
  private readonly rueda = (e: WheelEvent): void => {
    const pellizco = e.ctrlKey || e.metaKey;
    if (!pellizco && e.target !== this.lienzo) return;
    e.preventDefault();
    const caja = this.lienzo.getBoundingClientRect();
    const paso = e.deltaMode === 1 ? e.deltaY * 16 : e.deltaY;
    this.acercar(Math.exp(-paso * (pellizco ? 0.012 : 0.0016)), e.clientX - caja.left, e.clientY - caja.top);
  };

  /** Safari entrega el pellizco como eventos de gesto propios. */
  private readonly gesto = (e: Event): void => {
    e.preventDefault();
    const { scale, clientX, clientY } = e as Event & { scale: number; clientX: number; clientY: number };
    if (e.type === 'gesturestart') this.zoomAlPellizcar = this.zoom;
    const caja = this.lienzo.getBoundingClientRect();
    this.acercar((this.zoomAlPellizcar * scale) / this.zoom, clientX - caja.left, clientY - caja.top);
  };

  private readonly baja = (e: PointerEvent): void => {
    this.arrastro = false;
    if (this.zoom === 1) return;
    this.agarre = [e.clientX, e.clientY];
    this.lienzo.setPointerCapture(e.pointerId);
  };

  private readonly mueve = (e: PointerEvent): void => {
    if (!this.agarre) return;
    const dx = e.clientX - this.agarre[0];
    const dy = e.clientY - this.agarre[1];
    if (!this.arrastro && Math.hypot(dx, dy) < 4) return;
    this.arrastro = true;
    this.agarre = [e.clientX, e.clientY];
    this.transicion = null;
    this.ox += dx;
    this.oy += dy;
    this.acotar();
  };

  private readonly sube = (): void => {
    this.agarre = null;
  };

  /** El punto visible más cercano a una posición, o -1 si no hay ninguno a menos de `radio` píxeles. */
  cercano(px: number, py: number, radio = 16): number {
    let mejor = -1;
    // Con watis se apunta al centro del cuerpo, y el radio alcanza a cubrirlo.
    const alcance = Math.max(radio, this.altoWati * this.zoom * 0.4 * this.mezcla);
    let distancia = alcance * alcance;
    for (let i = 0; i < this.n; i++) {
      if (this.color[i] === PUNTO.fuera) continue;
      if (this.mezcla > 0 && !this.mostrado[i]) continue;
      const dx = this.x[i] * this.zoom + this.ox - px;
      const dy = this.centroY(i) * this.zoom + this.oy - py;
      const d = dx * dx + dy * dy;
      if (d < distancia) {
        distancia = d;
        mejor = i;
      }
    }
    return mejor;
  }

  /**
   * Cuáles de estas cajas (en píxeles del lienzo) tienen debajo algún punto de la muestra o algún
   * rótulo de región, en el lugar donde quedan al terminar su vuelo. Los puntos fuera de la muestra
   * son fondo: no cuentan. Sirve para retirar un panel solo si tapa lo que se está mirando.
   */
  tapan(cajas: { x: number; y: number; ancho: number; alto: number }[], margen = 6): boolean[] {
    const tapa = cajas.map(() => false);
    const dentro = (k: number, x: number, y: number) => {
      const c = cajas[k];
      return x >= c.x - margen && x <= c.x + c.ancho + margen && y >= c.y - margen && y <= c.y + c.alto + margen;
    };
    for (let i = 0; i < this.n; i++) {
      if (this.estados[i] === PUNTO.fuera) continue;
      const x = this.haciaX[i] * this.zoom + this.ox;
      const y = this.haciaY[i] * this.zoom + this.oy;
      for (let k = 0; k < cajas.length; k++) if (!tapa[k] && dentro(k, x, y)) tapa[k] = true;
    }
    if (this.etiquetas.length) {
      const letra = this.letra / Math.sqrt(this.zoom);
      this.ctx.font = `650 ${letra}px ${this.fuente}`;
      for (const e of this.etiquetas) {
        const ancho = this.ctx.measureText(e.texto).width;
        const inicio = e.lado === 1 ? e.x : e.x - ancho;
        // El rótulo se revisa en sus dos extremos y al medio, a la altura de su línea.
        for (const wx of [inicio, inicio + ancho / 2, inicio + ancho]) {
          const x = wx * this.zoom + this.ox;
          const y = e.y * this.zoom + this.oy;
          for (let k = 0; k < cajas.length; k++) if (!tapa[k] && dentro(k, x, y)) tapa[k] = true;
        }
      }
    }
    return tapa;
  }

  resaltar(puntos: number[]): void {
    for (const i of this.foco) if (i < this.n) this.enFoco[i] = 0;
    this.foco = puntos;
    for (const i of puntos) if (i < this.n) this.enFoco[i] = 1;
    this.sucio = true;
  }

  latir(activo: boolean): void {
    this.latiendo = activo && !this.reducir.matches;
    this.sucio = true;
  }

  /** Cambia el estado de cada punto y lo manda a su nuevo lugar. */
  fijar(estados: Uint8Array, modo: ModoVuelo): void {
    if (modo === 'aparecer') {
      this.abierta = false;
      return this.encender(estados);
    }
    // Si nada cambió no se relanza el vuelo: los datos que siguen llegando no reinician la animación.
    if (this.abierta && estados.length === this.estados.length && estados.every((valor, i) => valor === this.estados[i])) return;
    this.abierta = true;
    this.estados = estados;
    this.destinos(this.reducir.matches ? 'inmediato' : modo);
  }

  /** Mientras la simulación corre: quien ya respondió se enciende con su color, en su lugar del mapa. */
  private encender(estados: Uint8Array): void {
    const ahora = performance.now() / 1000;
    for (let i = 0; i < this.n; i++) {
      if (estados[i] === this.color[i]) continue;
      this.color[i] = estados[i];
      if (estados[i] !== PUNTO.fuera && estados[i] !== PUNTO.pendiente) this.llega[i] = ahora;
      // Todos esperan en casa: las burbujas se arman recién cuando terminan todos.
      this.volar(i, this.casaX[i], this.casaY[i], this.reducir.matches ? 'inmediato' : 'cambio', ahora);
    }
    this.estados = estados.slice();
    this.burbujas = [];
    this.finVuelo = Math.max(this.finVuelo, ahora + 0.4 + VUELO);
    this.sucio = true;
  }

  private proyectar(lon: number, lat: number): [number, number] {
    return [this.ancho / 2 + (lon - LON_CENTRO) * ESTRECHEZ * this.u, this.margen() + (LAT_NORTE - lat) * this.u];
  }

  /**
   * Ancho que ocupan las columnas de la interfaz a cada lado (mismo cálculo que `.izquierda` en
   * AppEnjambre.module.css: margen más min(33vw, 27rem)). Ni burbujas ni rótulos entran ahí.
   */
  private lateral(): number {
    if (this.ancho < ANCHO_CON_CIFRAS) return 4;
    const margenLado = Math.max(16, Math.min(40, this.ancho * 0.026));
    return margenLado + Math.min(this.ancho * 0.33, 432) + 14;
  }

  private margen(): number {
    return Math.max(18, this.alto * 0.03);
  }

  private medir(): void {
    this.ancho = this.lienzo.clientWidth;
    this.alto = this.lienzo.clientHeight;
    if (!this.ancho || !this.alto) return;
    this.dpr = Math.min(devicePixelRatio || 1, DPR_MAXIMO);
    this.zoom = 1;
    this.ox = 0;
    this.oy = 0;
    // Al cambiar el tamaño la vista vuelve a completa: la interfaz se entera.
    this.alCambiarVista?.(1);
    this.lienzo.width = Math.round(this.ancho * this.dpr);
    this.lienzo.height = Math.round(this.alto * this.dpr);
    this.u = (this.alto - this.margen() * 2) / GRADOS;
    // El tamaño del punto crece con la pantalla: en un proyector se tiene que ver desde el fondo de la sala.
    this.paso = Math.max(2, Math.min(4.6, this.ancho / 450, this.alto / 250));
    this.letra = Math.round(Math.max(11, Math.min(15, this.alto / 70)));
    // El tamaño de los watis depende de la pantalla: su atlas se vuelve a armar.
    if (this.atlas && this.atlas.celdaAlto !== this.altoAtlas()) this.programarAtlas();
    if (this.atlasGrande && this.atlasGrande.celdaAlto !== this.altoGrande()) this.atlasGrande = null;
    this.hojaGrande = null;
    this.claveMapa = '';
    this.silueta = new Path2D();
    for (const region of REGIONES_GEO) {
      for (const anillo of region) {
        if (anillo[0][0] < LON_MINIMA) continue;
        anillo.forEach(([lon, lat], i) => {
          const [x, y] = this.proyectar(lon, lat);
          if (i === 0) this.silueta.moveTo(x, y);
          else this.silueta.lineTo(x, y);
        });
        this.silueta.closePath();
      }
    }
    this.trazarComunas();
    this.personas.forEach((persona, i) => {
      [this.casaX[i], this.casaY[i]] = this.proyectar(Math.max(LON_MINIMA, persona.lon), persona.lat);
    });
    this.destinos('inmediato');
  }

  /** Arma los límites comunales con la escala actual; si los polígonos no han llegado, los pide. */
  private trazarComunas(): void {
    const comunas = comunasCargadas();
    if (!comunas) {
      void cargarComunas().then(() => {
        if (this.ancho) this.trazarComunas();
        this.sucio = true;
      });
      return;
    }
    this.claveMapa = '';
    this.comunas = new Path2D();
    for (const comuna of Object.values(comunas)) {
      for (const anillo of comuna.anillos) {
        anillo.forEach(([lon, lat], i) => {
          const [x, y] = this.proyectar(lon, lat);
          if (i === 0) this.comunas.moveTo(x, y);
          else this.comunas.lineTo(x, y);
        });
        this.comunas.closePath();
      }
    }
  }

  /** Calcula a dónde va cada punto según su estado: a su burbuja o de vuelta a casa. */
  /**
   * Calcula a dónde va cada punto. Con respuestas, el resultado se arma como una fila por región,
   * de norte a sur: la burbuja en contra a la izquierda del país, la de a favor a la derecha y el
   * nombre de la región junto a cada una. Todas las regiones de la muestra aparecen siempre.
   */
  private destinos(modo: ModoVuelo): void {
    if (!this.ancho) return;
    const vacias = (): number[][] => REGIONES.map(() => []);
    const grupos = { [PUNTO.favor]: vacias(), [PUNTO.contra]: vacias() };
    const total = REGIONES.map(() => 0);
    for (let i = 0; i < this.n; i++) {
      const estado = this.estados[i];
      if (estado !== PUNTO.fuera) total[this.personas[i].region] += 1;
      if (estado === PUNTO.favor || estado === PUNTO.contra) grupos[estado][this.personas[i].region].push(i);
    }
    const ahora = performance.now() / 1000;
    const pendiente = new Uint8Array(this.n);
    const hayResultado = grupos[PUNTO.favor].some((g) => g.length) || grupos[PUNTO.contra].some((g) => g.length);
    this.burbujas = [];
    this.etiquetas = [];
    if (hayResultado) {
      const regiones = REGIONES.map((_, region) => region).filter((region) => total[region] > 0);
      const bordeDer = this.ancho / 2 + 3.4 * ESTRECHEZ * this.u + 10;
      const bordeIzq = this.ancho / 2 - 4.5 * ESTRECHEZ * this.u - 10;
      const lateral = this.lateral();
      const textos = regiones.map((region) => ({
        region,
        favor: this.textoDe(region, grupos[PUNTO.favor][region], total[region]),
        contra: this.textoDe(region, grupos[PUNTO.contra][region], total[region]),
      }));
      this.ctx.font = `650 ${this.letra}px ${this.fuente}`;
      const anchoTexto = (t: string) => this.ctx.measureText(t).width;
      const altoFila = this.letra * 1.55;
      const disponible = this.alto - 2 * MARGEN_FILAS;
      let paso = this.paso;
      let radios: { favor: number; contra: number }[] = [];
      for (let intento = 0; intento < 24; intento++) {
        radios = regiones.map((region) => ({
          favor: grupos[PUNTO.favor][region].length ? radioDe(grupos[PUNTO.favor][region].length, paso) : 0,
          contra: grupos[PUNTO.contra][region].length ? radioDe(grupos[PUNTO.contra][region].length, paso) : 0,
        }));
        const altura = radios.reduce((suma, r) => suma + Math.max(2 * r.favor, 2 * r.contra, altoFila) + ENTRE_FILAS, 0);
        const cabeAncho = radios.every(
          (r, k) =>
            bordeDer + 2 * r.favor + SEPARA_ROTULO + anchoTexto(textos[k].favor) <= this.ancho - lateral &&
            bordeIzq - 2 * r.contra - SEPARA_ROTULO - anchoTexto(textos[k].contra) >= lateral,
        );
        if (altura <= disponible && cabeAncho) break;
        paso *= 0.92;
      }
      this.pasoActual = paso;
      const altos = radios.map((r) => Math.max(2 * r.favor, 2 * r.contra, altoFila));
      const ocupado = altos.reduce((a, b) => a + b, 0);
      // El espacio que sobra se reparte entre las filas (hasta un tope) y el conjunto se centra.
      const entre = Math.max(ENTRE_FILAS, Math.min(ENTRE_FILAS_MAXIMO, (disponible - ocupado) / Math.max(1, regiones.length - 1)));
      let y = Math.max(MARGEN_FILAS, (this.alto - ocupado - entre * (regiones.length - 1)) / 2);
      regiones.forEach((region, k) => {
        const centro = y + altos[k] / 2;
        const lados = [
          [PUNTO.favor, 1, radios[k].favor, textos[k].favor],
          [PUNTO.contra, -1, radios[k].contra, textos[k].contra],
        ] as const;
        for (const [estado, lado, r, texto] of lados) {
          const borde = lado === 1 ? bordeDer : bordeIzq;
          const lista = grupos[estado][region];
          this.etiquetas.push({ x: borde + lado * (2 * r + SEPARA_ROTULO), y: centro, lado, region, texto });
          if (!lista.length) continue;
          const burbuja = { x: borde + lado * r, y: centro, r };
          this.burbujas.push(burbuja);
          lista.forEach((i, orden) => {
            const [dx, dy] = puntoEnBurbuja(orden, paso);
            this.volar(i, burbuja.x + dx, burbuja.y + dy, modo, ahora);
            pendiente[i] = 1;
          });
        }
        y += altos[k] + entre;
      });
    }
    // Para comprobar desde fuera que cada región quedó rotulada a ambos lados.
    this.lienzo.dataset.regiones = String(this.etiquetas.filter((e) => e.lado === 1).length);
    this.lienzo.dataset.rotulos = this.etiquetas.map((e) => `${e.lado === 1 ? 'F' : 'C'}:${e.texto}@${Math.round(e.x)},${Math.round(e.y)}`).join('|');
    for (let i = 0; i < this.n; i++) if (!pendiente[i]) this.volar(i, this.casaX[i], this.casaY[i], modo, ahora);
    if (modo === 'inmediato') this.color.set(this.estados);
    const espera = modo === 'ola' ? 1.7 : modo === 'cambio' ? 0.4 : 0;
    this.finVuelo = Math.max(this.finVuelo, ahora + espera + VUELO);
    this.inicioRotulos = modo === 'inmediato' ? 0 : ahora + espera + VUELO * 0.6;
    this.sucio = true;
  }

  /** "Maule 58 %": nombre de la región y qué parte de ella tomó esa postura. */
  private textoDe(region: number, lista: number[], total: number): string {
    const nombre = REGIONES[region].corto;
    const personas = new Set(lista.map((i) => this.personas[i].agente ?? i)).size;
    // Con muy poca gente en la región el porcentaje engaña: se dice cuántas personas son.
    const enRegion = lista.length ? Math.max(1, Math.round((total / lista.length) * personas)) : MINIMO_PARA_PORCENTAJE;
    if (lista.length && enRegion < MINIMO_PARA_PORCENTAJE) return `${nombre} ${personas} ${personas === 1 ? 'persona' : 'personas'}`;
    return `${nombre} ${Math.round((lista.length / total) * 100)} %`;
  }

  private volar(i: number, x: number, y: number, modo: ModoVuelo, ahora: number): void {
    if (modo === 'inmediato') {
      // Si el punto va en vuelo, solo se corrige su destino; si no, salta.
      if (ahora < this.sale[i] + this.dura[i]) {
        this.haciaX[i] = x;
        this.haciaY[i] = y;
        return;
      }
      this.x[i] = this.desdeX[i] = this.haciaX[i] = x;
      this.y[i] = this.desdeY[i] = this.haciaY[i] = y;
      return;
    }
    this.desdeX[i] = this.x[i];
    this.desdeY[i] = this.y[i];
    this.haciaX[i] = x;
    this.haciaY[i] = y;
    this.dura[i] = VUELO;
    // En la ola, el norte responde primero.
    const norteSur = (this.casaY[i] - this.margen()) / (this.alto - this.margen() * 2);
    this.sale[i] = ahora + (modo === 'ola' ? norteSur * 1.3 : 0) + Math.abs(azar(i, 4)) * 0.4;
  }

  /**
   * Deja de dibujar mientras otra vista tapa el mapa por completo (el proceso, el análisis): los
   * cambios se siguen anotando y al volver se pinta de inmediato con lo último.
   */
  pausar(pausada: boolean): void {
    if (this.pausada === pausada) return;
    this.pausada = pausada;
    if (!pausada) this.sucio = true;
  }

  private readonly ciclo = (marca: number): void => {
    this.cuadro = requestAnimationFrame(this.ciclo);
    if (document.hidden || !this.ancho || this.pausada) return;
    const ahora = marca / 1000;
    if (this.transicion) this.avanzarZoom(ahora);
    const volando = ahora < this.finVuelo + 0.6;
    const urgente = volando || this.sucio || this.latiendo || this.foco.length > 0;
    // Con watis cerca la escena nunca queda quieta: respiran.
    const respiran = this.animados();
    if (!urgente && (!respiran || ahora - this.ultimoCuadro < RESPIRO)) return;
    this.ultimoCuadro = ahora;
    this.sucio = false;
    if (volando) this.mover(ahora);
    this.dibujar(ahora);
  };

  private mover(ahora: number): void {
    for (let i = 0; i < this.n; i++) {
      const p = (ahora - this.sale[i]) / this.dura[i];
      if (p <= 0) continue;
      // El punto toma su color nuevo al despegar, no antes: así la ola se ve avanzar.
      this.color[i] = this.estados[i];
      if (p >= 1) {
        this.x[i] = this.haciaX[i];
        this.y[i] = this.haciaY[i];
        continue;
      }
      const e = suave(p);
      const dx = this.haciaX[i] - this.desdeX[i];
      const dy = this.haciaY[i] - this.desdeY[i];
      // Vuelo en arco: cada punto se curva un poco hacia un lado distinto.
      const arco = Math.sin(Math.PI * p) * azar(i, 5) * 0.16;
      this.x[i] = this.desdeX[i] + dx * e - dy * arco;
      this.y[i] = this.desdeY[i] + dy * e + dx * arco;
    }
  }

  /**
   * El país con sus límites, en una capa aparte que solo se vuelve a pintar cuando cambia la vista:
   * mientras los watis respiran, cada cuadro la copia en vez de trazar otra vez miles de comunas.
   */
  private pintarMapa(): void {
    const clave = `${this.zoom},${this.ox},${this.oy},${this.lienzo.width},${this.lienzo.height}`;
    if (clave === this.claveMapa) return;
    this.claveMapa = clave;
    const capa = this.capaMapa;
    if (capa.width !== this.lienzo.width || capa.height !== this.lienzo.height) {
      capa.width = this.lienzo.width;
      capa.height = this.lienzo.height;
    }
    const ctx = capa.getContext('2d')!;
    ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
    ctx.fillStyle = this.fondo;
    ctx.fillRect(0, 0, this.ancho, this.alto);
    ctx.translate(this.ox, this.oy);
    ctx.scale(this.zoom, this.zoom);
    ctx.fillStyle = this.chile;
    ctx.fill(this.silueta);
    ctx.strokeStyle = this.comunaBorde;
    ctx.lineWidth = 0.6 / this.zoom;
    ctx.stroke(this.comunas);
    ctx.strokeStyle = this.chileBorde;
    ctx.lineWidth = 1 / this.zoom;
    ctx.stroke(this.silueta);
  }

  private dibujar(ahora: number): void {
    const { ctx, dpr } = this;
    this.pintarMapa();
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.drawImage(this.capaMapa, 0, 0);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.translate(this.ox, this.oy);
    ctx.scale(this.zoom, this.zoom);
    // Al acercar, los puntos crecen menos que el mapa: así se separan y se ve a cada persona.
    const lado = Math.max(1.4, Math.min(this.paso, this.pasoActual * 1.12) * 0.66) / this.zoom ** 0.3;
    // De cerca el cuadrado se encoge y en su lugar aparece el wati.
    const mezcla = Math.max(0, Math.min(1, (lado * this.zoom - WATI_DESDE) / (WATI_HASTA - WATI_DESDE)));
    this.mezcla = mezcla;
    this.altoWati = lado * WATI_ALTO * (0.55 + 0.45 * mezcla);
    const ladoPunto = lado * (1 - mezcla);
    // Solo se dibuja lo que se ve: con el mapa acercado, la mayoría de los puntos queda fuera.
    const borde = lado * 4;
    const x0 = -this.ox / this.zoom - borde;
    const x1 = (this.ancho - this.ox) / this.zoom + borde;
    const y0 = -this.oy / this.zoom - borde;
    const y1 = (this.alto - this.oy) / this.zoom + borde;
    const ido = this.idos.length ? (ahora - this.inicioIdos) / DESAPARECER : 1;
    if (ido >= 1) this.idos = [];
    for (const estado of [PUNTO.fuera, PUNTO.pendiente, PUNTO.neutra, PUNTO.indecisa, PUNTO.contra, PUNTO.favor]) {
      ctx.fillStyle = this.colores[estado];
      if (ido < 1) {
        const tamano = lado * (1 - suave(Math.max(0, ido)));
        for (let k = 0; k < this.idos.length; k += 3) {
          if (this.idos[k + 2] === estado) ctx.fillRect(this.idos[k] - tamano / 2, this.idos[k + 1] - tamano / 2, tamano, tamano);
        }
      }
      for (let i = 0; i < this.n && mezcla < 1; i++) {
        if (this.color[i] !== estado) continue;
        if (this.x[i] < x0 || this.x[i] > x1 || this.y[i] < y0 || this.y[i] > y1) continue;
        // Los que siguen pensando laten en ondas que bajan por el país.
        if (estado === PUNTO.pendiente && this.latiendo) {
          ctx.globalAlpha = 0.35 + 0.65 * (0.5 + 0.5 * Math.sin(ahora * 3.2 - this.casaY[i] * 0.018 + (i % 7)));
        }
        // Destello de llegada: el punto nace grande y se asienta.
        const recien = (ahora - this.llega[i]) / DESTELLO;
        let tamano = recien < 1 ? ladoPunto * (1 + 2.2 * (1 - recien) ** 2) : ladoPunto;
        // Quien apareció en su lugar crece desde nada.
        const crecido = (ahora - this.nace[i]) / APARECER;
        if (crecido < 1) {
          if (crecido <= 0) continue;
          tamano *= suave(crecido);
        }
        ctx.fillRect(this.x[i] - tamano / 2, this.y[i] - tamano / 2, tamano, tamano);
      }
      ctx.globalAlpha = 1;
    }
    if (mezcla > 0) this.watis(ahora, mezcla);
    this.anillos(ahora);
    const visible = this.inicioRotulos === 0 ? 1 : Math.max(0, Math.min(1, (ahora - this.inicioRotulos) / 0.5));
    if (visible > 0) this.rotulos(visible);
  }

  /** Alto en píxeles del lienzo del wati más grande que se puede ver (a zoom máximo). */
  private altoMaximo(): number {
    const lado = Math.max(1.4, this.paso * 0.66) / ZOOM_MAXIMO ** 0.3;
    return Math.ceil(lado * WATI_ALTO * ZOOM_MAXIMO * this.dpr);
  }

  /** Alto de las celdas del atlas. Más grandes que esto, los watis salen de la hoja grande. */
  private altoAtlas(): number {
    return Math.min(48, this.altoMaximo());
  }

  private altoGrande(): number {
    return Math.min(ALTO_GRANDE, this.altoMaximo());
  }

  /** Cuántos watis caben en la hoja de los que bostezan. */
  private capacidadGrande(): number {
    const alto = this.altoGrande();
    return Math.floor(HOJA_GRANDE / Math.ceil((alto * CELDA_ANCHO) / CELDA_ALTO)) * Math.floor(HOJA_GRANDE / alto);
  }

  /**
   * Lugar en la hoja grande del wati con estos rasgos (una cara de bostezo): se dibuja ahí la
   * primera vez que aparece. Una sola hoja (y no un lienzo por wati) para que el navegador la tenga
   * en la GPU. Si está llena devuelve null: la hoja solo se vacía al empezar un cuadro.
   */
  private grande(estado: number, tono: number, variante: number, cuadro: number): [number, number, number, number] | null {
    const alto = this.altoGrande();
    const ancho = Math.ceil((alto * CELDA_ANCHO) / CELDA_ALTO);
    if (!this.hojaGrande) {
      this.hojaGrande = document.createElement('canvas');
      this.hojaGrande.width = this.hojaGrande.height = HOJA_GRANDE;
      this.lugaresGrandes.clear();
    }
    const columnas = Math.floor(HOJA_GRANDE / ancho);
    const clave = ((estado * TONOS + tono) * VARIANTES + variante) * CARAS + cuadro;
    let lugar = this.lugaresGrandes.get(clave);
    if (lugar === undefined) {
      if (this.lugaresGrandes.size >= this.capacidadGrande()) return null;
      const ctx = this.hojaGrande.getContext('2d')!;
      lugar = this.lugaresGrandes.size;
      this.lugaresGrandes.set(clave, lugar);
      const sprite = crearSpriteWati(this.colores[estado], SIN_POSTURA.includes(estado), tono, variante, cuadro, alto, ANIMOS[estado]);
      ctx.drawImage(sprite, (lugar % columnas) * ancho, Math.floor(lugar / columnas) * alto);
    }
    return [(lugar % columnas) * ancho, Math.floor(lugar / columnas) * alto, ancho, alto];
  }

  /** El atlas se arma apenas la página queda libre, para que el primer acercamiento no tironee. */
  private programarAtlas(): void {
    this.atlas = null;
    this.atlasGrande = null;
    this.hojaGrande = null;
    clearTimeout(this.esperaAtlas);
    this.esperaAtlas = window.setTimeout(() => {
      if (!this.atlas && this.colores.length) this.atlas = crearAtlasWati(this.colores, this.altoAtlas(), SIN_POSTURA, CARAS, ANIMOS);
      // El grande, después y aparte, para no trabar la página de una vez.
      this.esperaAtlas = window.setTimeout(() => {
        if (!this.atlasGrande && this.colores.length) this.atlasGrande = crearAtlasWati(this.colores, this.altoGrande(), SIN_POSTURA, 1, ANIMOS);
      }, 800);
    }, 500);
  }

  /**
   * Los watis a la vista, de arriba abajo para que los de abajo queden delante. Cada uno respira
   * a su ritmo y de vez en cuando bosteza; los que siguen pensando laten como los puntos.
   */
  private watis(ahora: number, mezcla: number): void {
    this.atlas ??= crearAtlasWati(this.colores, this.altoAtlas(), SIN_POSTURA, CARAS, ANIMOS);
    const { ctx, atlas } = this;
    const alto = this.altoWati;
    const ancho = (alto * CELDA_ANCHO) / CELDA_ALTO;
    // Vista en coordenadas del mapa. El wati crece hacia arriba desde sus pies: se incluye a los
    // que están un poco más abajo del borde inferior.
    const x0 = -this.ox / this.zoom - ancho;
    const x1 = (this.ancho - this.ox) / this.zoom + ancho;
    const y0 = -this.oy / this.zoom - alto * 0.2;
    const y1 = (this.alto - this.oy) / this.zoom + alto;
    // La zona del raleo es una potencia de dos y no cambia con cada paso de la rueda: solo cuando el
    // zoom se aleja bastante de ella (si no, un zoom que oscila la haría saltar de ida y vuelta).
    // Se cuenta a la gente de las zonas enteras, aunque el borde de la pantalla las corte: si no,
    // al mover la vista cambiaría la cuenta y los watis del borde parpadearían.
    const ideal = Math.log2(ancho * ZONA_WATIS);
    if (!(Math.abs(ideal - this.nivelZona) < 0.8)) this.nivelZona = Math.round(ideal);
    const zona = 2 ** this.nivelZona;
    const zx0 = Math.floor(x0 / zona) * zona;
    const zx1 = Math.ceil(x1 / zona) * zona;
    const zy0 = Math.floor(y0 / zona) * zona;
    const zy1 = Math.ceil(y1 / zona) * zona;
    let cuantos = 0;
    for (let i = 0; i < this.n; i++) {
      if (this.x[i] >= zx0 && this.x[i] < zx1 && this.y[i] >= zy0 && this.y[i] < zy1) this.visibles[cuantos++] = i;
    }
    const raleados = this.ralear(this.visibles.subarray(0, cuantos), zona);
    let enVista = 0;
    for (const i of raleados) {
      if (this.x[i] >= x0 && this.x[i] <= x1 && this.y[i] >= y0 && this.y[i] <= y1) raleados[enVista++] = i;
    }
    const lista = raleados.subarray(0, enVista).sort((a, b) => this.y[a] - this.y[b]);
    this.mostrado.fill(0);
    const quieto = !this.animados();
    // De muy cerca el atlas se vería borroso: salen del atlas grande (y los que bostezan, de la hoja).
    const enGrande = alto * this.zoom * this.dpr > atlas.celdaAlto * 1.15;
    if (enGrande) {
      this.atlasGrande ??= crearAtlasWati(this.colores, this.altoGrande(), SIN_POSTURA, 1, ANIMOS);
      // La hoja de los bostezos se vacía solo entre cuadros, nunca a mitad de uno.
      if (this.lugaresGrandes.size > this.capacidadGrande() * 0.75) this.hojaGrande = null;
    }
    for (const i of lista) {
      const estado = this.color[i];
      let escala = 1;
      const recien = (ahora - this.llega[i]) / DESTELLO;
      if (recien < 1) escala *= 1 + 0.6 * (1 - recien) ** 2;
      const crecido = (ahora - this.nace[i]) / APARECER;
      if (crecido < 1) {
        if (crecido <= 0) continue;
        escala *= suave(crecido);
      }
      this.mostrado[i] = 1;
      // Con alguien elegido, el resto da un paso atrás para que se distinga su grupo.
      const atenuado = this.foco.length && !this.enFoco[i] ? ATENUADO : 1;
      ctx.globalAlpha =
        atenuado *
        (estado === PUNTO.pendiente && this.latiendo ? mezcla * (0.45 + 0.55 * (0.5 + 0.5 * Math.sin(ahora * 3.2 - this.casaY[i] * 0.018 + (i % 7)))) : mezcla);
      const pose = quieto ? QUIETO : poseDe(ahora, this.semilla[i]);
      let fuente: CanvasImageSource = atlas.lienzo;
      let [sx, sy] = [0, 0];
      let [sw, sh] = [atlas.celdaAncho, atlas.celdaAlto];
      const bostezo = enGrande && pose.cuadro > 0 ? this.grande(estado, this.tono[i], this.variante[i], pose.cuadro) : null;
      if (bostezo) {
        [sx, sy, sw, sh] = bostezo;
        fuente = this.hojaGrande!;
      } else if (enGrande) {
        const grande = this.atlasGrande!;
        [sx, sy] = celdaWati(grande, estado, this.tono[i], this.variante[i], 0);
        [sw, sh] = [grande.celdaAncho, grande.celdaAlto];
        fuente = grande.lienzo;
      } else {
        [sx, sy] = celdaWati(atlas, estado, this.tono[i], this.variante[i], pose.cuadro);
      }
      const dw = ancho * escala * pose.ancho;
      const dh = alto * escala * pose.alto;
      const pies = this.y[i] + alto * 0.06;
      if (this.enFoco[i]) {
        this.marcaFoco(i, pies - alto * 0.03, ancho, mezcla, ahora);
        ctx.globalAlpha = mezcla;
      }
      if (pose.giro) {
        ctx.save();
        ctx.translate(this.x[i], pies);
        ctx.rotate(pose.giro);
        ctx.drawImage(fuente, sx, sy, sw, sh, -dw / 2, -dh * PIES_RELATIVO, dw, dh);
        ctx.restore();
      } else {
        ctx.drawImage(fuente, sx, sy, sw, sh, this.x[i] - dw / 2, pies - dh * PIES_RELATIVO, dw, dh);
      }
    }
    ctx.globalAlpha = 1;
  }

  /**
   * Ralea la multitud: el mapa se divide en zonas de unos pocos watis de ancho y en cada una se
   * muestra solo una parte, que crece menos que la cantidad de gente (≈ 1,6·n^⅓). Donde hay más
   * personas se siguen viendo más watis, pero sin amontonarse. Quién aparece lo decide su
   * prioridad fija: al acercar, las zonas se achican y van apareciendo más sin cambiar a los que ya
   * estaban. Deja la lista compactada al principio del mismo arreglo.
   */
  private ralear(lista: Int32Array, zona: number): Int32Array {
    const cuenta = new Map<number, number>();
    const clave = (i: number) => Math.floor(this.x[i] / zona) * 131071 + Math.floor(this.y[i] / zona);
    for (const i of lista) {
      const k = clave(i);
      cuenta.set(k, (cuenta.get(k) ?? 0) + 1);
    }
    let quedan = 0;
    for (const i of lista) {
      const n = cuenta.get(clave(i))!;
      const caben = Math.min(n, POR_ZONA * n ** (1 / 3));
      if (this.prioridad[i] * n < caben || this.enFoco[i]) lista[quedan++] = i;
    }
    return lista.subarray(0, quedan);
  }

  /** Si los watis a la vista se mueven: solo de cerca, y nunca con «reducir movimiento». */
  private animados(): boolean {
    return this.mezcla > 0 && this.altoWati * this.zoom >= WATI_ANIMA && !this.reducir.matches;
  }

  /** Dónde está el centro del cuerpo de un punto en el mapa: con watis, más arriba que sus pies. */
  private centroY(i: number): number {
    return this.y[i] - this.altoWati * 0.42 * this.mezcla;
  }

  /** Anillos alrededor de los puntos resaltados. Con watis se van: los marca `marcaFoco`. */
  private anillos(ahora: number): void {
    const queda = 1 - this.mezcla;
    if (!this.foco.length || queda <= 0) return;
    const { ctx } = this;
    const pulso = 0.5 + 0.5 * Math.sin(ahora * 4);
    ctx.lineWidth = 2 / this.zoom;
    for (const i of this.foco) {
      ctx.strokeStyle = this.colores[this.color[i]] || this.tinta;
      ctx.globalAlpha = 0.9 * queda;
      ctx.beginPath();
      ctx.arc(this.x[i], this.y[i], (7 + pulso * 3) / this.zoom, 0, Math.PI * 2);
      ctx.stroke();
      ctx.globalAlpha = 0.25 * (1 - pulso) * queda;
      ctx.beginPath();
      ctx.arc(this.x[i], this.y[i], (14 + pulso * 10) / this.zoom, 0, Math.PI * 2);
      ctx.stroke();
    }
    ctx.globalAlpha = 1;
  }

  /**
   * Marca de un wati resaltado: un óvalo en el suelo, bajo sus pies, que late suave. Se dibuja
   * justo antes del wati, así él queda parado encima y los de adelante lo pueden tapar.
   */
  private marcaFoco(i: number, pies: number, ancho: number, mezcla: number, ahora: number): void {
    const { ctx } = this;
    const pulso = 0.5 + 0.5 * Math.sin(ahora * 4);
    const rx = ancho * 0.5;
    const ry = ancho * 0.17;
    ctx.fillStyle = ctx.strokeStyle = this.colores[this.color[i]] || this.tinta;
    ctx.lineWidth = Math.max(1.5 / this.zoom, ancho * 0.045);
    ctx.globalAlpha = 0.22 * mezcla;
    ctx.beginPath();
    ctx.ellipse(this.x[i], pies, rx, ry, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.globalAlpha = 0.95 * mezcla;
    ctx.stroke();
    ctx.globalAlpha = 0.45 * (1 - pulso) * mezcla;
    ctx.beginPath();
    ctx.ellipse(this.x[i], pies, rx * (1.1 + 0.3 * pulso), ry * (1.1 + 0.3 * pulso), 0, 0, Math.PI * 2);
    ctx.stroke();
  }

  /** Los rótulos van siempre junto a su burbuja, del lado de afuera, en una sola línea. */
  private rotulos(visible: number): void {
    const { ctx } = this;
    // Al acercar, la letra crece menos que el mapa para no tapar las burbujas.
    const letra = this.letra / Math.sqrt(this.zoom);
    ctx.globalAlpha = visible;
    ctx.textBaseline = 'middle';
    for (const e of this.etiquetas) {
      const corte = e.texto.indexOf(' ', REGIONES[e.region].corto.length);
      const nombre = e.texto.slice(0, corte);
      const valor = e.texto.slice(corte);
      ctx.font = `650 ${letra}px ${this.fuente}`;
      const anchoNombre = ctx.measureText(nombre).width;
      const anchoTotal = ctx.measureText(e.texto).width;
      const inicio = e.lado === 1 ? e.x : e.x - anchoTotal;
      ctx.textAlign = 'left';
      ctx.fillStyle = this.tinta;
      ctx.fillText(nombre, inicio, e.y);
      ctx.font = `500 ${letra}px ${this.fuente}`;
      ctx.globalAlpha = visible * 0.72;
      ctx.fillText(valor, inicio + anchoNombre, e.y);
      ctx.globalAlpha = visible;
    }
    ctx.globalAlpha = 1;
  }
}
