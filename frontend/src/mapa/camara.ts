import { ALTO_MUNDO, ALTO_UTIL, ANCHO_MUNDO, CENTRO_Y } from './proyeccion';

export interface Marco {
  x: number;
  y: number;
  w: number;
  h: number;
}

const ZOOM_MAXIMO = 9;
const X_SANTIAGO = 16.45;
/** Bajo esta proporción el país no cabe a lo ancho: se ajusta al alto y se recorre arrastrando. */
const PROPORCION_MINIMA = 0;
const RAPIDEZ = 7;

export class Camara {
  u = 1;
  zoom = 1;
  cx = ANCHO_MUNDO / 2;
  cy = CENTRO_Y;
  private sx = 0;
  private sy = 0;
  private ancho = 1;
  private meta: { cx: number; cy: number; zoom: number } | null = null;
  private recorre = false;
  private iniciada = false;

  ajustar(marco: Marco): void {
    this.recorre = marco.w / marco.h < PROPORCION_MINIMA;
    this.u = this.recorre ? marco.h / (ALTO_UTIL + 0.3) : Math.min(marco.w / ANCHO_MUNDO, marco.h / ALTO_UTIL);
    this.sx = marco.x + marco.w / 2;
    this.sy = marco.y + marco.h / 2;
    this.ancho = marco.w;
    if (!this.iniciada) {
      this.iniciada = true;
      this.cx = this.inicioX();
    }
    this.limitar();
  }

  get escala(): number {
    return this.u * this.zoom;
  }

  private inicioX(): number {
    return this.recorre ? X_SANTIAGO : ANCHO_MUNDO / 2;
  }

  /** Posición horizontal de un punto del mundo en la vista inicial, sin importar el zoom actual. */
  xInicial(x: number): number {
    return (x - this.inicioX()) * this.u + this.sx;
  }

  aPantalla(x: number, y: number): [number, number] {
    return [(x - this.cx) * this.escala + this.sx, (y - this.cy) * this.escala + this.sy];
  }

  desdePantalla(px: number, py: number): [number, number] {
    return [(px - this.sx) / this.escala + this.cx, (py - this.sy) / this.escala + this.cy];
  }

  acercar(factor: number, px = this.sx, py = this.sy): void {
    const [mx, my] = this.desdePantalla(px, py);
    this.meta = null;
    this.zoom = Math.max(1, Math.min(ZOOM_MAXIMO, this.zoom * factor));
    this.cx = mx - (px - this.sx) / this.escala;
    this.cy = my - (py - this.sy) / this.escala;
    this.limitar();
  }

  desplazar(dx: number, dy: number): void {
    this.meta = null;
    this.cx -= dx / this.escala;
    this.cy -= dy / this.escala;
    this.limitar();
  }

  irA(cx: number, cy: number, zoom: number): void {
    this.meta = { cx, cy, zoom: Math.max(1, Math.min(ZOOM_MAXIMO, zoom)) };
  }

  restablecer(): void {
    this.irA(this.inicioX(), CENTRO_Y, 1);
  }

  saltarAMeta(): void {
    if (!this.meta) return;
    Object.assign(this, this.meta);
    this.meta = null;
    this.limitar();
  }

  /** Avanza la animación de cámara. Devuelve verdadero si la vista cambió. */
  avanzar(dt: number): boolean {
    if (!this.meta) return false;
    const k = 1 - Math.exp(-RAPIDEZ * dt);
    this.cx += (this.meta.cx - this.cx) * k;
    this.cy += (this.meta.cy - this.cy) * k;
    this.zoom += (this.meta.zoom - this.zoom) * k;
    const cerca = Math.abs(this.meta.zoom - this.zoom) < 0.004 && Math.abs(this.meta.cx - this.cx) < 0.004;
    if (cerca) this.saltarAMeta();
    return true;
  }

  private limitar(): void {
    const medio = this.ancho / 2 / this.escala;
    const [minimo, maximo] = medio * 2 >= ANCHO_MUNDO ? [ANCHO_MUNDO / 2, ANCHO_MUNDO / 2] : [medio - 0.6, ANCHO_MUNDO - medio + 0.6];
    this.cx = Math.max(minimo, Math.min(maximo, this.cx));
    const holgura = this.zoom > 1 ? (ALTO_MUNDO / 2) * (1 - 1 / this.zoom) + 0.4 : 0;
    this.cy = Math.max(CENTRO_Y - holgura, Math.min(CENTRO_Y + holgura, this.cy));
  }
}
