import { ALTO_MUNDO, ANCHO_MUNDO, ANCHO_UTIL, CENTRO_X, CENTRO_Y } from './proyeccion';

export interface Marco {
  x: number;
  y: number;
  w: number;
  h: number;
}

const ZOOM_MAXIMO = 9;
const RAPIDEZ = 7;
/** Aire sobre Arica y bajo el Cabo de Hornos, en grados. */
const MARGEN_VERTICAL = 1;

export class Camara {
  u = 1;
  zoom = 1;
  cx = CENTRO_X;
  cy = CENTRO_Y;
  private sx = 0;
  private sy = 0;
  private meta: { cx: number; cy: number; zoom: number } | null = null;

  /** Encuadra el país entero dentro del marco. */
  ajustar(marco: Marco): void {
    this.u = Math.min(marco.w / ANCHO_UTIL, marco.h / (ALTO_MUNDO + MARGEN_VERTICAL));
    this.sx = marco.x + marco.w / 2;
    this.sy = marco.y + marco.h / 2;
    this.limitar();
  }

  get escala(): number {
    return this.u * this.zoom;
  }

  /** Posición vertical de un punto del mundo en la vista inicial, sin importar el zoom actual. */
  yInicial(y: number): number {
    return (y - CENTRO_Y) * this.u + this.sy;
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
    this.irA(CENTRO_X, CENTRO_Y, 1);
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
    const cerca = Math.abs(this.meta.zoom - this.zoom) < 0.004 && Math.abs(this.meta.cy - this.cy) < 0.004;
    if (cerca) this.saltarAMeta();
    return true;
  }

  /** Con la vista completa el país queda centrado; al acercar se puede recorrer hasta sus bordes. */
  private limitar(): void {
    const libre = 1 - 1 / this.zoom;
    const holguraX = (ANCHO_MUNDO / 2) * libre;
    const holguraY = (ALTO_MUNDO / 2) * libre;
    this.cx = Math.max(CENTRO_X - holguraX, Math.min(CENTRO_X + holguraX, this.cx));
    this.cy = Math.max(CENTRO_Y - holguraY, Math.min(CENTRO_Y + holguraY, this.cy));
  }
}
