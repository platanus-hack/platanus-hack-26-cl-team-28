import { REGIONES } from '../dominio/catalogos';
import type { Persona } from '../dominio/tipos';
import { REGIONES_GEO } from '../mapa/geografia';
import { puntoEnBurbuja, radioDe, type Burbuja } from './disposicion';

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
const DESTELLO = 0.45;
/** Desde este ancho las cifras gigantes van a los costados del lienzo. */
const ANCHO_CON_CIFRAS = 900;

/** Disposición del resultado por filas (píxeles). */
const MARGEN_FILAS = 18;
const ENTRE_FILAS = 4;
const ENTRE_FILAS_MAXIMO = 16;
const SEPARA_ROTULO = 9;

const ZOOM_MAXIMO = 8;

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
  private color!: Uint8Array;
  private estados!: Uint8Array;
  private burbujas: Burbuja[] = [];
  private etiquetas: Etiqueta[] = [];
  private colores: string[] = [];
  private tinta = '';
  private fondo = '';
  private chile = '';
  private chileBorde = '';
  private fuente = '';
  private silueta = new Path2D();
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
  private zoom = 1;
  private ox = 0;
  private oy = 0;
  private agarre: [number, number] | null = null;
  private arrastro = false;
  private zoomAlPellizcar = 1;
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
    this.color = new Uint8Array(n).fill(PUNTO.neutra);
    this.estados = new Uint8Array(n).fill(PUNTO.neutra);
  }

  /**
   * Cambia a quiénes se dibuja sin volver a armar la escena: quien sigue en la muestra se queda
   * donde está, y los puntos que sobran se van a ocupar el lugar de los que llegan. No repite la
   * entrada ni toca el acercamiento.
   */
  reemplazar(personas: Persona[]): void {
    const antes = { n: this.n, x: this.x, y: this.y, personas: this.personas };
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
    // Los puntos que ya no están se reparten entre los nuevos, para que el cambio se vea como un traslado.
    const libres: number[] = [];
    for (let j = 0; j < antes.n; j++) if (!sigue[j]) libres.push(j);
    let usados = 0;
    const ahora = performance.now() / 1000;
    const quieto = this.reducir.matches;
    for (let i = 0; i < this.n; i++) {
      const j = origen[i] >= 0 ? origen[i] : usados < libres.length ? libres[usados++] : -1;
      const parteX = j >= 0 && !quieto ? antes.x[j] : this.casaX[i];
      const parteY = j >= 0 && !quieto ? antes.y[j] : this.casaY[i];
      this.x[i] = this.desdeX[i] = parteX;
      this.y[i] = this.desdeY[i] = parteY;
      this.haciaX[i] = this.casaX[i];
      this.haciaY[i] = this.casaY[i];
      this.sale[i] = ahora + Math.abs(azar(i, 4)) * 0.08;
      this.dura[i] = VUELO_REACOMODO;
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
    this.fuente = v('--fuente-ui');
    this.sucio = true;
  }

  /** Dónde está dibujado ahora un punto, en píxeles del lienzo. */
  posicion(i: number): [number, number] {
    return [this.x[i] * this.zoom + this.ox, this.y[i] * this.zoom + this.oy];
  }

  /** Acerca o aleja la vista manteniendo fijo el punto (cx, cy) de la pantalla; sin punto, el centro. */
  acercar(factor: number, cx = this.ancho / 2, cy = this.alto / 2): void {
    const nuevo = Math.max(1, Math.min(ZOOM_MAXIMO, this.zoom * factor));
    const razon = nuevo / this.zoom;
    this.ox = cx - (cx - this.ox) * razon;
    this.oy = cy - (cy - this.oy) * razon;
    this.zoom = nuevo;
    this.acotar();
  }

  restablecer(): void {
    this.zoom = 1;
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
    let distancia = radio * radio;
    for (let i = 0; i < this.n; i++) {
      if (this.color[i] === PUNTO.fuera) continue;
      const dx = this.x[i] * this.zoom + this.ox - px;
      const dy = this.y[i] * this.zoom + this.oy - py;
      const d = dx * dx + dy * dy;
      if (d < distancia) {
        distancia = d;
        mejor = i;
      }
    }
    return mejor;
  }

  resaltar(puntos: number[]): void {
    this.foco = puntos;
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
   * AppEnjambre.module.css: margen más min(28vw, 26rem)). Ni burbujas ni rótulos entran ahí.
   */
  private lateral(): number {
    if (this.ancho < ANCHO_CON_CIFRAS) return 4;
    const margenLado = Math.max(16, Math.min(40, this.ancho * 0.026));
    return margenLado + Math.min(this.ancho * 0.28, 416) + 14;
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
    this.lienzo.width = Math.round(this.ancho * this.dpr);
    this.lienzo.height = Math.round(this.alto * this.dpr);
    this.u = (this.alto - this.margen() * 2) / GRADOS;
    // El tamaño del punto crece con la pantalla: en un proyector se tiene que ver desde el fondo de la sala.
    this.paso = Math.max(2, Math.min(4.6, this.ancho / 450, this.alto / 250));
    this.letra = Math.round(Math.max(11, Math.min(15, this.alto / 70)));
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
    this.personas.forEach((persona, i) => {
      [this.casaX[i], this.casaY[i]] = this.proyectar(Math.max(LON_MINIMA, persona.lon), persona.lat);
    });
    this.destinos('inmediato');
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

  private readonly ciclo = (marca: number): void => {
    this.cuadro = requestAnimationFrame(this.ciclo);
    if (document.hidden || !this.ancho) return;
    const ahora = marca / 1000;
    const volando = ahora < this.finVuelo + 0.6;
    if (!volando && !this.sucio && !this.latiendo && !this.foco.length) return;
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

  private dibujar(ahora: number): void {
    const { ctx, dpr } = this;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.fillStyle = this.fondo;
    ctx.fillRect(0, 0, this.ancho, this.alto);
    ctx.translate(this.ox, this.oy);
    ctx.scale(this.zoom, this.zoom);
    ctx.fillStyle = this.chile;
    ctx.fill(this.silueta);
    ctx.strokeStyle = this.chileBorde;
    ctx.lineWidth = 1 / this.zoom;
    ctx.stroke(this.silueta);
    // Al acercar, los puntos crecen menos que el mapa: así se separan y se ve a cada persona.
    const lado = Math.max(1.4, Math.min(this.paso, this.pasoActual * 1.12) * 0.66) / this.zoom ** 0.3;
    for (const estado of [PUNTO.fuera, PUNTO.pendiente, PUNTO.neutra, PUNTO.indecisa, PUNTO.contra, PUNTO.favor]) {
      ctx.fillStyle = this.colores[estado];
      for (let i = 0; i < this.n; i++) {
        if (this.color[i] !== estado) continue;
        // Los que siguen pensando laten en ondas que bajan por el país.
        if (estado === PUNTO.pendiente && this.latiendo) {
          ctx.globalAlpha = 0.35 + 0.65 * (0.5 + 0.5 * Math.sin(ahora * 3.2 - this.casaY[i] * 0.018 + (i % 7)));
        }
        // Destello de llegada: el punto nace grande y se asienta.
        const recien = (ahora - this.llega[i]) / DESTELLO;
        const tamano = recien < 1 ? lado * (1 + 2.2 * (1 - recien) ** 2) : lado;
        ctx.fillRect(this.x[i] - tamano / 2, this.y[i] - tamano / 2, tamano, tamano);
      }
      ctx.globalAlpha = 1;
    }
    this.anillos(ahora);
    const visible = this.inicioRotulos === 0 ? 1 : Math.max(0, Math.min(1, (ahora - this.inicioRotulos) / 0.5));
    if (visible > 0) this.rotulos(visible);
  }

  private anillos(ahora: number): void {
    if (!this.foco.length) return;
    const { ctx } = this;
    const pulso = 0.5 + 0.5 * Math.sin(ahora * 4);
    ctx.lineWidth = 2 / this.zoom;
    for (const i of this.foco) {
      ctx.strokeStyle = this.colores[this.color[i]] || this.tinta;
      ctx.globalAlpha = 0.9;
      ctx.beginPath();
      ctx.arc(this.x[i], this.y[i], (7 + pulso * 3) / this.zoom, 0, Math.PI * 2);
      ctx.stroke();
      ctx.globalAlpha = 0.25 * (1 - pulso);
      ctx.beginPath();
      ctx.arc(this.x[i], this.y[i], (14 + pulso * 10) / this.zoom, 0, Math.PI * 2);
      ctx.stroke();
    }
    ctx.globalAlpha = 1;
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
