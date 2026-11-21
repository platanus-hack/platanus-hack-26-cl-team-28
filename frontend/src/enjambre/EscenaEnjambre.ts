import { REGIONES } from '../dominio/catalogos';
import type { Persona } from '../dominio/tipos';
import { REGIONES_GEO } from '../mapa/geografia';
import { puntoEnBurbuja, radioDe, ubicarBurbujas, type Burbuja } from './disposicion';

/** Estado de cada punto. El número es también su color. */
export const PUNTO = { fuera: 0, neutra: 1, favor: 2, contra: 3, indecisa: 4, pendiente: 5 } as const;
/**
 * `ola`: el país responde de norte a sur. `cambio`: todos a la vez. `aparecer`: cada punto se
 * enciende en su lugar cuando su agente termina, sin volar todavía.
 */
export type ModoVuelo = 'ola' | 'cambio' | 'aparecer' | 'inmediato';

interface Rotulada extends Burbuja {
  region: number;
  lado: 1 | -1;
  /** Porcentaje de la región que tomó esta postura. */
  pct: number;
  /** Personas distintas en la burbuja (un agente puede dibujarse con varios puntos). */
  personas: number;
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
const DESTELLO = 0.45;
/** Desde este ancho las cifras gigantes van a los costados del lienzo. */
const ANCHO_CON_CIFRAS = 900;

const suave = (p: number) => (p < 0.5 ? 4 * p * p * p : 1 - (-2 * p + 2) ** 3 / 2);
const azar = (i: number, sal: number) => (Math.sin(i * 12.9898 + sal * 78.233) * 43758.5453) % 1;

/**
 * Escena de puntos. Cada persona simulada es un punto: en reposo dibujan Chile, y al
 * responder vuelan a burbujas por región, a favor a un lado y en contra al otro.
 */
export class EscenaEnjambre {
  private readonly ctx: CanvasRenderingContext2D;
  private readonly n: number;
  private readonly casaX: Float32Array;
  private readonly casaY: Float32Array;
  private readonly desdeX: Float32Array;
  private readonly desdeY: Float32Array;
  private readonly haciaX: Float32Array;
  private readonly haciaY: Float32Array;
  private readonly x: Float32Array;
  private readonly y: Float32Array;
  private readonly sale: Float32Array;
  /** Momento en que cada punto se encendió, para el destello de llegada. */
  private readonly llega: Float32Array;
  private readonly color: Uint8Array;
  private estados: Uint8Array;
  private burbujas: Rotulada[] = [];
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
    private readonly personas: Persona[],
  ) {
    this.ctx = lienzo.getContext('2d')!;
    this.n = personas.length;
    const crear = () => new Float32Array(this.n);
    [this.casaX, this.casaY, this.desdeX, this.desdeY, this.haciaX, this.haciaY, this.x, this.y, this.sale, this.llega] = [
      crear(), crear(), crear(), crear(), crear(), crear(), crear(), crear(), crear(), crear().fill(-10),
    ];
    this.color = new Uint8Array(this.n).fill(PUNTO.neutra);
    this.estados = new Uint8Array(this.n).fill(PUNTO.neutra);
    this.observador = new ResizeObserver(() => this.medir());
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
    this.cuadro = requestAnimationFrame(this.ciclo);
  }

  destruir(): void {
    cancelAnimationFrame(this.cuadro);
    this.observador.disconnect();
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
    return [this.x[i], this.y[i]];
  }

  /** El punto visible más cercano a una posición, o -1 si no hay ninguno a menos de `radio` píxeles. */
  cercano(px: number, py: number, radio = 16): number {
    let mejor = -1;
    let distancia = radio * radio;
    for (let i = 0; i < this.n; i++) {
      if (this.color[i] === PUNTO.fuera) continue;
      const dx = this.x[i] - px;
      const dy = this.y[i] - py;
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

  private margen(): number {
    return Math.max(18, this.alto * 0.03);
  }

  private medir(): void {
    this.ancho = this.lienzo.clientWidth;
    this.alto = this.lienzo.clientHeight;
    if (!this.ancho || !this.alto) return;
    this.dpr = Math.min(devicePixelRatio || 1, DPR_MAXIMO);
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
  private destinos(modo: ModoVuelo): void {
    if (!this.ancho) return;
    const filas = (): number[][] => REGIONES.map(() => []);
    const grupos = { [PUNTO.favor]: filas(), [PUNTO.contra]: filas() };
    const total = REGIONES.map(() => 0);
    for (let i = 0; i < this.n; i++) {
      const estado = this.estados[i];
      if (estado !== PUNTO.fuera) total[this.personas[i].region] += 1;
      if (estado === PUNTO.favor || estado === PUNTO.contra) grupos[estado][this.personas[i].region].push(i);
    }
    const ahora = performance.now() / 1000;
    const pendiente = new Uint8Array(this.n);
    const lados = [[PUNTO.favor, 1], [PUNTO.contra, -1]] as const;
    const bordes = { 1: this.ancho / 2 + 3.4 * ESTRECHEZ * this.u + 10, [-1]: this.ancho / 2 - 4.5 * ESTRECHEZ * this.u - 10 };
    // En pantallas anchas los costados son de las cifras: si las burbujas los invaden, los puntos se juntan más.
    const reserva = this.ancho >= ANCHO_CON_CIFRAS ? this.ancho * 0.25 : 4;
    let paso = this.paso;
    let armado: { lado: 1 | -1; regiones: { lista: number[]; region: number }[]; puestas: Burbuja[] }[] = [];
    for (let intento = 0; intento < 6; intento++) {
      armado = lados.map(([estado, lado]) => {
        const regiones = grupos[estado].map((lista, region) => ({ lista, region })).filter((g) => g.lista.length);
        const pedidos = regiones.map((g) => ({ y: this.proyectar(0, REGIONES[g.region].capitalLat)[1], r: radioDe(g.lista.length, paso) }));
        return { lado, regiones, puestas: ubicarBurbujas(pedidos, lado, bordes[lado], 8, this.alto - 8) };
      });
      const cabe = armado.every(({ puestas }) => puestas.every((b) => b.x - b.r >= reserva && b.x + b.r <= this.ancho - reserva));
      if (cabe) break;
      paso *= 0.88;
    }
    this.pasoActual = paso;
    this.burbujas = [];
    for (const { lado, regiones, puestas } of armado) {
      regiones.forEach((g, k) => {
        const burbuja = puestas[k];
        const personas = new Set(g.lista.map((i) => this.personas[i].agente ?? i)).size;
        const enRegion = Math.max(1, Math.round((total[g.region] / g.lista.length) * personas));
        this.burbujas.push({ ...burbuja, region: g.region, lado, personas, pct: enRegion < MINIMO_PARA_PORCENTAJE ? -1 : Math.round((g.lista.length / total[g.region]) * 100) });
        g.lista.forEach((i, orden) => {
          const [dx, dy] = puntoEnBurbuja(orden, paso);
          this.volar(i, burbuja.x + dx, burbuja.y + dy, modo, ahora);
          pendiente[i] = 1;
        });
      });
    }
    for (let i = 0; i < this.n; i++) if (!pendiente[i]) this.volar(i, this.casaX[i], this.casaY[i], modo, ahora);
    if (modo === 'inmediato') this.color.set(this.estados);
    const espera = modo === 'ola' ? 1.7 : modo === 'cambio' ? 0.4 : 0;
    this.finVuelo = Math.max(this.finVuelo, ahora + espera + VUELO);
    this.inicioRotulos = modo === 'inmediato' ? 0 : ahora + espera + VUELO * 0.6;
    this.sucio = true;
  }

  private volar(i: number, x: number, y: number, modo: ModoVuelo, ahora: number): void {
    if (modo === 'inmediato') {
      // Si el punto va en vuelo, solo se corrige su destino; si no, salta.
      if (ahora < this.sale[i] + VUELO) {
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
      const p = (ahora - this.sale[i]) / VUELO;
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
    ctx.fillStyle = this.chile;
    ctx.fill(this.silueta);
    ctx.strokeStyle = this.chileBorde;
    ctx.lineWidth = 1;
    ctx.stroke(this.silueta);
    const lado = Math.max(1.4, Math.min(this.paso, this.pasoActual * 1.12) * 0.66);
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
    ctx.lineWidth = 2;
    for (const i of this.foco) {
      ctx.strokeStyle = this.colores[this.color[i]] || this.tinta;
      ctx.globalAlpha = 0.9;
      ctx.beginPath();
      ctx.arc(this.x[i], this.y[i], 7 + pulso * 3, 0, Math.PI * 2);
      ctx.stroke();
      ctx.globalAlpha = 0.25 * (1 - pulso);
      ctx.beginPath();
      ctx.arc(this.x[i], this.y[i], 14 + pulso * 10, 0, Math.PI * 2);
      ctx.stroke();
    }
    ctx.globalAlpha = 1;
  }

  /**
   * Nombre de la región y qué parte de ella tomó esa postura. En las burbujas grandes va
   * adentro, sobre una placa; en las chicas, afuera, solo si no pisa a otra burbuja ni a otro rótulo.
   */
  private rotulos(visible: number): void {
    const { ctx } = this;
    const ocupados: [number, number, number, number][] = [];
    // Franja que ocupa el país: ningún rótulo va encima del mapa.
    const paisIzq = this.ancho / 2 - 4.5 * ESTRECHEZ * this.u;
    const paisDer = this.ancho / 2 + 3.4 * ESTRECHEZ * this.u;
    const libre = (x: number, y: number, w: number, h: number, propia: Rotulada) =>
      (x + w <= paisIzq || x >= paisDer) &&
      x >= 2 &&
      x + w <= this.ancho - 2 &&
      y >= 2 &&
      y + h <= this.alto - 2 &&
      !this.burbujas.some((b) => b !== propia && circuloTocaCaja(b, x, y, w, h)) &&
      !ocupados.some(([ox, oy, ow, oh]) => x < ox + ow && ox < x + w && y < oy + oh && oy < y + h);
    ctx.globalAlpha = visible;
    ctx.textBaseline = 'middle';
    ctx.textAlign = 'center';
    for (const b of [...this.burbujas].sort((p, q) => q.r - p.r)) {
      if (b.r < 7) continue;
      const nombre = REGIONES[b.region].corto;
      ctx.font = `650 ${this.letra}px ${this.fuente}`;
      const w = Math.max(ctx.measureText(nombre).width, 30) + 14;
      const h = this.letra * 2.7;
      const adentro = b.r >= 30;
      const candidatos: [number, number][] = adentro
        ? [[b.x, b.y]]
        : [
            [b.x + b.lado * (b.r + w / 2 + 3), b.y],
            [b.x, b.y - b.r - h / 2 - 2],
            [b.x, b.y + b.r + h / 2 + 2],
            [b.x + b.lado * (b.r * 0.7 + w / 2), b.y - b.r * 0.7 - h / 2],
            [b.x + b.lado * (b.r * 0.7 + w / 2), b.y + b.r * 0.7 + h / 2],
            [b.x + b.lado * (b.r + w / 2 + 3), b.y - h * 0.6],
            [b.x + b.lado * (b.r + w / 2 + 3), b.y + h * 0.6],
          ];
      const lugar = candidatos.find(([cx, cy]) => adentro || libre(cx - w / 2, cy - h / 2, w, h, b));
      if (!lugar) continue;
      const [cx, cy] = lugar;
      ocupados.push([cx - w / 2, cy - h / 2, w, h]);
      if (adentro) {
        ctx.fillStyle = this.fondo;
        ctx.globalAlpha = visible * 0.86;
        ctx.beginPath();
        ctx.roundRect(cx - w / 2, cy - h / 2, w, h, 4);
        ctx.fill();
        ctx.globalAlpha = visible;
      }
      ctx.font = `650 ${this.letra}px ${this.fuente}`;
      ctx.fillStyle = this.tinta;
      ctx.fillText(nombre, cx, cy - this.letra * 0.6);
      ctx.font = `600 ${this.letra - 1}px ${this.fuente}`;
      ctx.fillStyle = this.tinta;
      ctx.globalAlpha = visible * 0.8;
      ctx.fillText(b.pct < 0 ? `${b.personas} ${b.personas === 1 ? 'persona' : 'personas'}` : `${b.pct} %`, cx, cy + this.letra * 0.65);
      ctx.globalAlpha = visible;
    }
    ctx.globalAlpha = 1;
  }
}

function circuloTocaCaja(c: Burbuja, x: number, y: number, w: number, h: number): boolean {
  const dx = c.x - Math.max(x, Math.min(x + w, c.x));
  const dy = c.y - Math.max(y, Math.min(y + h, c.y));
  return dx * dx + dy * dy < c.r * c.r;
}
