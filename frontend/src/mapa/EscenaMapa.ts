import type { Camara as TipoCamara, Marco } from './camara';
import { Camara } from './camara';
import { dibujarMapa, dibujarOlas, dibujarRotulos, type Colores } from './capaMapa';
import { CapaPersonas, type ModoCambio } from './capaPersonas';
import { dibujarGlobo } from './globo';
import { conectarEntrada } from './entrada';
import { CAJAS_REGION, crearCaminos, crearCordillera, crearOlas, type Caminos, type Cumbre, type Ola } from './geografia';
import type { Multitud } from './multitud';
import { crearAtlas, type Atlas, type Tintas } from './personajes';
import { ANCHO_UTIL, CENTRO_X } from './proyeccion';
import { leerTokens } from './tokens';

export interface OpcionesEscena {
  lienzo: HTMLCanvasElement;
  multitud: Multitud;
  aspectos: Uint8Array;
  /** Rectángulo del lienzo donde debe caber el país. */
  obtenerMarco(): Marco;
  alElegir(indice: number): void;
  /** `reunidas` dice cuántas figuras representa la apuntada (más de una si es un grupo). */
  alApuntar(indice: number, x: number, y: number, reunidas: number): void;
}

const DPR_MAXIMO = 2;
const CUADROS_EN_REPOSO = 12;

/** Escena del mapa: una clase con `montar` y `destruir` que React solo envuelve. */
export class EscenaMapa {
  private readonly camara: TipoCamara = new Camara();
  private readonly fondo = document.createElement('canvas');
  private readonly ctx: CanvasRenderingContext2D;
  private readonly caminos: Caminos = crearCaminos();
  private readonly cordillera: Cumbre[] = crearCordillera();
  private readonly olas: Ola[] = crearOlas();
  private readonly reducir = matchMedia('(prefers-reduced-motion: reduce)');
  private colores!: Colores & Tintas;
  private chico!: Atlas;
  private grande!: Atlas;
  private personas!: CapaPersonas;
  private ancho = 0;
  private alto = 0;
  private dpr = 1;
  private cuadro = 0;
  private anterior = 0;
  private ultimoDibujo = 0;
  private fondoSucio = true;
  private apuntada = -1;
  private elegida = -1;
  private frase = '';
  private region = -1;
  private etiqueta = '';
  private desconectar: (() => void) | null = null;
  private readonly observador: ResizeObserver;

  constructor(private readonly o: OpcionesEscena) {
    this.ctx = o.lienzo.getContext('2d')!;
    this.observador = new ResizeObserver(() => this.redimensionar());
  }

  montar(): void {
    this.colores = leerTokens();
    this.dpr = Math.min(devicePixelRatio || 1, DPR_MAXIMO);
    this.chico = crearAtlas(this.colores, 0.75 * this.dpr, false);
    this.grande = crearAtlas(this.colores, 2.5 * this.dpr, true);
    this.personas = new CapaPersonas(this.o.multitud, this.o.aspectos, performance.now() / 1000);
    this.redimensionar();
    this.observador.observe(this.o.lienzo);
    this.desconectar = conectarEntrada(this.o.lienzo, {
      arrastrar: (dx, dy) => this.mover(() => this.camara.desplazar(dx, dy)),
      acercar: (factor, x, y) => this.mover(() => this.camara.acercar(factor, x, y)),
      tocar: (x, y) => this.tocar(x, y),
      apuntar: (x, y) => this.apuntar(x, y),
      salir: () => this.apuntar(-1, -1),
      restablecer: () => this.restablecer(),
    });
    document.fonts.ready.then(() => (this.fondoSucio = true));
    this.cuadro = requestAnimationFrame(this.ciclo);
  }

  destruir(): void {
    cancelAnimationFrame(this.cuadro);
    this.observador.disconnect();
    this.desconectar?.();
  }

  /** Vuelve a medir el lienzo y el marco. Se llama también cuando cambia la disposición de la página. */
  redimensionar(): void {
    const { lienzo } = this.o;
    this.ancho = lienzo.clientWidth;
    this.alto = lienzo.clientHeight;
    if (!this.ancho || !this.alto) return;
    for (const c of [lienzo, this.fondo]) {
      c.width = Math.round(this.ancho * this.dpr);
      c.height = Math.round(this.alto * this.dpr);
    }
    this.camara.ajustar(this.o.obtenerMarco());
    this.fondoSucio = true;
  }

  fijarEstados(estados: Uint8Array, modo: ModoCambio, duracion?: number, etiqueta = ''): void {
    this.etiqueta = etiqueta;
    this.personas.programar(estados, this.reducir.matches ? 'inmediato' : modo, performance.now() / 1000, duracion);
  }

  enfocarRegion(indice: number): void {
    this.region = indice;
    if (indice < 0) return this.restablecer();
    const caja = CAJAS_REGION[indice];
    const marco = this.o.obtenerMarco();
    const zoom = Math.min(marco.w / (caja.w * this.camara.u * 1.5), marco.h / (caja.h * this.camara.u * 1.8));
    this.camara.irA(caja.x + caja.w / 2, caja.y + caja.h / 2, Math.max(1.6, Math.min(6, zoom)));
    if (this.reducir.matches) this.mover(() => this.camara.saltarAMeta());
  }

  /** Marca a una persona y, si hay frase, la muestra en un globo sobre su figura. */
  elegir(indice: number, frase = ''): void {
    this.elegida = indice;
    this.frase = frase;
  }

  acercar(factor: number): void {
    const marco = this.o.obtenerMarco();
    this.mover(() => this.camara.acercar(factor, marco.x + marco.w / 2, marco.y + marco.h / 2));
  }

  restablecer(): void {
    this.region = -1;
    this.camara.restablecer();
    if (this.reducir.matches) this.mover(() => this.camara.saltarAMeta());
  }

  /** Posición vertical de un punto del mundo en la vista inicial (para alinear la franja de regiones). */
  yInicial(yMundo: number): number {
    return this.camara.yInicial(yMundo);
  }

  /** Un clic en un grupo acerca el mapa hasta abrirlo; en una figura sola, la elige. */
  private tocar(x: number, y: number): void {
    const indice = this.personas.buscar(x, y, this.camara);
    if (indice >= 0 && this.personas.reunidas(indice) > 1) {
      const { multitud } = this.o;
      this.camara.irA(multitud.x[indice], multitud.y[indice], this.camara.zoom * 2.4);
      if (this.reducir.matches) this.mover(() => this.camara.saltarAMeta());
      return;
    }
    this.o.alElegir(indice);
  }

  private mover(accion: () => void): void {
    accion();
    this.fondoSucio = true;
  }

  private apuntar(x: number, y: number): void {
    const indice = x < 0 ? -1 : this.personas.buscar(x, y, this.camara);
    if (indice === this.apuntada && indice < 0) return;
    this.apuntada = indice;
    this.o.lienzo.style.cursor = indice >= 0 ? 'pointer' : '';
    this.o.alApuntar(indice, x, y, indice >= 0 ? this.personas.reunidas(indice) : 0);
  }

  private readonly ciclo = (marca: number): void => {
    this.cuadro = requestAnimationFrame(this.ciclo);
    if (document.hidden || !this.ancho) return;
    const ahora = marca / 1000;
    const dt = Math.min(0.05, ahora - this.anterior);
    this.anterior = ahora;
    if (this.camara.avanzar(dt)) this.fondoSucio = true;
    const enMovimiento = this.fondoSucio || this.personas.activa(ahora) || this.apuntada >= 0;
    if (!enMovimiento && ahora - this.ultimoDibujo < 1 / CUADROS_EN_REPOSO) return;
    this.ultimoDibujo = ahora;
    this.dibujar(ahora, dt);
  };

  private dibujar(ahora: number, dt: number): void {
    const { ctx, ancho, alto, dpr, camara, colores } = this;
    const lienzo = { ctx, ancho, alto, dpr };
    if (this.fondoSucio) {
      dibujarMapa({ ...lienzo, ctx: this.fondo.getContext('2d')! }, camara, this.caminos, this.cordillera, colores);
      this.fondoSucio = false;
    }
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.drawImage(this.fondo, 0, 0);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const reducido = this.reducir.matches;
    dibujarOlas(lienzo, camara, this.olas, colores, reducido ? 0 : ahora);
    if (this.region >= 0) this.contorno();
    this.personas.dibujar({
      ctx, camara, ahora, dt, reducido, ancho, alto,
      chico: this.chico, grande: this.grande,
      apuntada: this.apuntada, elegida: this.elegida,
      tinta: colores.tinta, papel: colores.papel,
    });
    dibujarRotulos(lienzo, camara, colores);
    if (this.elegida >= 0 && this.frase) this.globo();
    if (this.personas.barrido) this.barrido(ahora);
  }

  private globo(): void {
    const { multitud } = this.o;
    const [x, y] = this.camara.aPantalla(multitud.x[this.elegida], multitud.y[this.elegida]);
    const altoFigura = this.personas.altoDe(this.camara, this.elegida);
    dibujarGlobo(this.ctx, { texto: this.frase, x, y: y - altoFigura * 0.8, ancho: this.ancho, colores: this.colores });
  }

  private contorno(): void {
    const { ctx, dpr, camara } = this;
    const [ox, oy] = camara.aPantalla(0, 0);
    ctx.save();
    ctx.setTransform(dpr * camara.escala, 0, 0, dpr * camara.escala, dpr * ox, dpr * oy);
    ctx.strokeStyle = this.colores.tinta;
    ctx.lineWidth = 1.6 / camara.escala;
    ctx.lineJoin = 'round';
    ctx.stroke(this.caminos.regiones[this.region]);
    ctx.restore();
  }

  /** Línea que baja por el país de norte a sur mientras la población responde. */
  private barrido(ahora: number): void {
    const { ctx, camara, colores } = this;
    const { inicio, duracion } = this.personas.barrido!;
    const { norte, sur } = this.o.multitud;
    const avance = Math.min(1, (ahora - inicio) / duracion);
    const [izquierda, y] = camara.aPantalla(CENTRO_X - ANCHO_UTIL * 0.5, norte + (sur - norte) * avance);
    const [derecha] = camara.aPantalla(CENTRO_X + ANCHO_UTIL * 0.5, 0);
    ctx.save();
    ctx.strokeStyle = colores.tinta;
    ctx.lineWidth = 1.4;
    ctx.setLineDash([5, 5]);
    ctx.beginPath();
    ctx.moveTo(izquierda, y);
    ctx.lineTo(derecha, y);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.font = `600 14px ${colores.fuenteMano}`;
    const anchoTexto = ctx.measureText(this.etiqueta).width + 16;
    ctx.fillStyle = colores.tinta;
    ctx.fillRect(izquierda, y - 22, anchoTexto, 22);
    ctx.fillStyle = colores.papel;
    ctx.textAlign = 'left';
    ctx.textBaseline = 'middle';
    ctx.fillText(this.etiqueta, izquierda + 8, y - 10.5);
    ctx.restore();
  }
}
