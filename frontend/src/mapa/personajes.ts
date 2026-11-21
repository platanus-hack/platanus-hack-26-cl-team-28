import { mezclar } from '../dominio/azar';

/** Estado con que se dibuja cada figura. El orden es también el de las columnas del atlas. */
export const ESTADO = { fantasma: 0, neutra: 1, favor: 2, contra: 3, indecisa: 4 } as const;
export type EstadoFigura = (typeof ESTADO)[keyof typeof ESTADO];

export const ASPECTOS = 6;
export const CUADROS = 3;
const ESTADOS = 5;

/** Celda de dibujo en unidades propias: los pies quedan en (CX, PIES). */
export const CELDA_ANCHO = 28;
export const CELDA_ALTO = 36;
const CX = 14;
const PIES = 33;

export interface Tintas {
  tinta: string;
  papel: string;
  favor: string;
  contra: string;
  indecisa: string;
  neutra: string;
  sombra: string;
}

/**
 * Cada figura es una criatura redonda, no una persona: un cuerpo de color con patas cortas y
 * dos ojos. La postura se lee en la silueta y no solo en el color: a favor levanta los brazos,
 * en contra se eriza, indecisa se ladea bajo un signo de pregunta.
 */
interface Pincel {
  ctx: CanvasRenderingContext2D;
  /** Temblor del trazo: cambia en cada cuadro para que la línea "hierva" como dibujo a mano. */
  t: (n: number) => number;
  estado: EstadoFigura;
  cuadro: number;
  aspecto: number;
  tintas: Tintas;
  detalle: boolean;
}

/** Medio ancho y alto del cuerpo según el aspecto: redonda, alta, ancha, pequeña, con orejas, con antena. */
const CUERPOS: [number, number][] = [
  [7.6, 15],
  [6.6, 18],
  [8.8, 13.5],
  [6.4, 12.5],
  [7.4, 14.5],
  [7, 16],
];

function linea(p: Pincel, puntos: number[]): void {
  const { ctx, t } = p;
  ctx.beginPath();
  for (let i = 0; i < puntos.length; i += 2) {
    const x = puntos[i] + t(i);
    const y = puntos[i + 1] + t(i + 1);
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  }
  ctx.stroke();
}

function punto(ctx: CanvasRenderingContext2D, x: number, y: number, r: number): void {
  ctx.beginPath();
  ctx.arc(x, y, r, 0, Math.PI * 2);
  ctx.fillStyle = ctx.strokeStyle;
  ctx.fill();
}

function patas(p: Pincel, base: number): void {
  linea(p, [CX - 3, base - 1, CX - 3.2, PIES, CX - 5, PIES]);
  linea(p, [CX + 3, base - 1, CX + 3.2, PIES, CX + 5, PIES]);
}

function color(p: Pincel): string {
  const { estado, tintas } = p;
  return estado === ESTADO.neutra ? tintas.neutra : [tintas.favor, tintas.contra, tintas.indecisa][estado - 2];
}

/** Contorno del cuerpo. En contra, la parte de arriba se eriza en púas. */
function cuerpo(p: Pincel, w: number, arriba: number, base: number): void {
  const { ctx, t, estado } = p;
  const medio = (arriba + base) / 2;
  ctx.beginPath();
  ctx.moveTo(CX - w + t(1), medio + t(2));
  if (estado === ESTADO.contra) {
    const puas = 4;
    for (let k = 0; k < puas; k++) {
      const x0 = CX - w + ((k + 0.5) / puas) * 2 * w;
      const x1 = CX - w + ((k + 1) / puas) * 2 * w;
      const curva = Math.sin(((k + 0.5) / puas) * Math.PI);
      ctx.lineTo(x0 + t(10 + k), arriba - 2.4 - curva * 1.2 + t(20 + k));
      ctx.lineTo(x1, k === puas - 1 ? medio : arriba + 2.2 - curva * 1.6);
    }
  } else {
    ctx.bezierCurveTo(CX - w + t(3), arriba - 1 + t(4), CX + w + t(5), arriba - 1 + t(6), CX + w + t(7), medio + t(8));
  }
  ctx.bezierCurveTo(CX + w + t(9), base + 1.4, CX - w + t(11), base + 1.4, CX - w + t(1), medio + t(2));
  ctx.closePath();
  if (estado !== ESTADO.fantasma) {
    ctx.fillStyle = color(p);
    ctx.fill();
  }
  ctx.stroke();
}

function adornos(p: Pincel, w: number, arriba: number): void {
  const { ctx, aspecto, estado } = p;
  if (estado === ESTADO.contra) return;
  if (aspecto === 4) {
    for (const lado of [-1, 1]) {
      ctx.beginPath();
      ctx.arc(CX + lado * w * 0.62, arriba + 0.6, 2.3, 0, Math.PI * 2);
      if (estado !== ESTADO.fantasma) {
        ctx.fillStyle = color(p);
        ctx.fill();
      }
      ctx.stroke();
    }
  }
  if (aspecto === 5) {
    linea(p, [CX, arriba, CX + 0.6, arriba - 3.4]);
    punto(ctx, CX + 0.6, arriba - 3.8, 1);
  }
  if (aspecto === 1) linea(p, [CX - 1.4, arriba - 0.2, CX - 2, arriba - 2.4, CX, arriba - 0.6, CX + 1.6, arriba - 2.6, CX + 1.4, arriba - 0.2]);
}

function brazos(p: Pincel, w: number, medio: number): void {
  const { estado, cuadro } = p;
  const vaiven = (cuadro - 1) * 0.8;
  if (estado === ESTADO.favor) {
    linea(p, [CX - w + 0.6, medio - 1, CX - w - 3.2 - vaiven, medio - 7 + vaiven]);
    linea(p, [CX + w - 0.6, medio - 1, CX + w + 3.2 - vaiven, medio - 7 - vaiven]);
  } else if (estado === ESTADO.indecisa) {
    linea(p, [CX - w + 0.4, medio + 1, CX - w - 2.8, medio + 0.2 + vaiven * 0.5]);
    linea(p, [CX + w - 0.4, medio + 1, CX + w + 2.8, medio + 0.2 - vaiven * 0.5]);
  } else if (estado === ESTADO.contra) {
    linea(p, [CX - w + 0.4, medio + 2.4, CX - w + 3.4, medio + 4.6]);
    linea(p, [CX + w - 0.4, medio + 2.4, CX + w - 3.4, medio + 4.6]);
  }
}

function cara(p: Pincel, w: number, medio: number): void {
  const { ctx, estado, detalle, cuadro } = p;
  const y = medio - 1.6;
  const dx = Math.min(3, w * 0.42);
  ctx.save();
  ctx.strokeStyle = estado === ESTADO.favor || estado === ESTADO.contra ? p.tintas.papel : p.tintas.tinta;
  if (estado === ESTADO.fantasma) ctx.strokeStyle = p.tintas.tinta;
  const r = detalle ? 0.95 : 1.15;
  if (estado === ESTADO.favor && detalle) {
    ctx.lineWidth *= 0.95;
    for (const lado of [-1, 1]) {
      ctx.beginPath();
      ctx.arc(CX + lado * dx, y + 0.6, 1.3, Math.PI * 1.1, Math.PI * 1.9);
      ctx.stroke();
    }
  } else {
    const mira = estado === ESTADO.indecisa ? 0.7 : 0;
    punto(ctx, CX - dx + mira, y - mira * 0.6, r);
    punto(ctx, CX + dx + mira, y - mira * 0.6, estado === ESTADO.indecisa ? r * 1.35 : r);
  }
  if (detalle) {
    ctx.lineWidth *= 0.8;
    if (estado === ESTADO.contra) {
      linea(p, [CX - dx - 1.6, y - 2.8, CX - dx + 1.4, y - 1.7]);
      linea(p, [CX + dx + 1.6, y - 2.8, CX + dx - 1.4, y - 1.7]);
    }
    ctx.beginPath();
    if (estado === ESTADO.favor) ctx.arc(CX, y + 2.2, 1.7, 0.1 * Math.PI, 0.9 * Math.PI);
    else if (estado === ESTADO.contra) ctx.arc(CX, y + 5, 1.6, 1.15 * Math.PI, 1.85 * Math.PI);
    else {
      ctx.moveTo(CX - 1.2, y + 3.2);
      ctx.lineTo(CX + 1.2, y + 3.2 - (estado === ESTADO.indecisa ? 0.9 : 0) + (cuadro - 1) * 0.1);
    }
    ctx.stroke();
  }
  ctx.restore();
}

function duda(p: Pincel, arriba: number): void {
  const { ctx, cuadro } = p;
  const x = CX + 8.2;
  const y = Math.max(3.4, arriba - 4.6) + (cuadro - 1) * 0.5;
  ctx.save();
  ctx.lineWidth *= 1.1;
  ctx.beginPath();
  ctx.moveTo(x - 1.6, y);
  ctx.quadraticCurveTo(x - 1.4, y - 2.6, x + 0.4, y - 2.4);
  ctx.quadraticCurveTo(x + 2.4, y - 2, x + 1.2, y + 0.2);
  ctx.quadraticCurveTo(x + 0.2, y + 1.2, x + 0.2, y + 2.4);
  ctx.stroke();
  punto(ctx, x + 0.2, y + 4.4, 0.6);
  ctx.restore();
}

/** Dibuja una figura en el origen del contexto, en unidades de celda. */
export function dibujarFigura(
  ctx: CanvasRenderingContext2D,
  opciones: { estado: EstadoFigura; aspecto: number; cuadro: number; tintas: Tintas; detalle: boolean },
): void {
  const { estado, aspecto, cuadro, tintas, detalle } = opciones;
  const semilla = aspecto * 31 + cuadro * 7 + estado * 131;
  const p: Pincel = { ctx, estado, aspecto, cuadro, tintas, detalle, t: (n) => (mezclar(semilla, n) - 0.5) * 0.6 };
  const [w, alto] = CUERPOS[aspecto];
  const base = PIES - 2.6;
  const arriba = base - alto;
  const medio = (arriba + base) / 2;
  ctx.save();
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  ctx.lineWidth = detalle ? 1.1 : 1.15;
  ctx.strokeStyle = tintas.tinta;
  ctx.globalAlpha = estado === ESTADO.fantasma ? 0.3 : 1;
  if (estado !== ESTADO.fantasma) {
    ctx.fillStyle = tintas.sombra;
    ctx.beginPath();
    ctx.ellipse(CX, PIES + 0.5, w * 0.85, 1.3, 0, 0, Math.PI * 2);
    ctx.fill();
  }
  patas(p, base);
  if (estado === ESTADO.indecisa) {
    ctx.translate(CX, base);
    ctx.rotate(0.13);
    ctx.translate(-CX, -base);
  }
  brazos(p, w, medio);
  adornos(p, w, arriba);
  cuerpo(p, w, arriba, base);
  cara(p, w, medio);
  ctx.restore();
  if (estado === ESTADO.indecisa) {
    ctx.save();
    ctx.lineCap = 'round';
    ctx.lineWidth = 1.1;
    ctx.strokeStyle = tintas.tinta;
    duda(p, arriba);
    ctx.restore();
  }
}

export interface Atlas {
  lienzo: HTMLCanvasElement;
  /** Píxeles del atlas por unidad de celda. */
  escala: number;
}

/** Hoja con todas las combinaciones de aspecto, estado y cuadro, para dibujar cientos de figuras por cuadro. */
export function crearAtlas(tintas: Tintas, escala: number, detalle: boolean): Atlas {
  const lienzo = document.createElement('canvas');
  lienzo.width = Math.ceil(CELDA_ANCHO * escala) * ESTADOS * CUADROS;
  lienzo.height = Math.ceil(CELDA_ALTO * escala) * ASPECTOS;
  const ctx = lienzo.getContext('2d')!;
  for (let aspecto = 0; aspecto < ASPECTOS; aspecto++) {
    for (let estado = 0; estado < ESTADOS; estado++) {
      for (let cuadro = 0; cuadro < CUADROS; cuadro++) {
        ctx.setTransform(
          escala, 0, 0, escala,
          Math.ceil(CELDA_ANCHO * escala) * (estado * CUADROS + cuadro),
          Math.ceil(CELDA_ALTO * escala) * aspecto,
        );
        dibujarFigura(ctx, { estado: estado as EstadoFigura, aspecto, cuadro, tintas, detalle });
      }
    }
  }
  return { lienzo, escala };
}

export function celdaAtlas(atlas: Atlas, aspecto: number, estado: number, cuadro: number): [number, number, number, number] {
  const w = Math.ceil(CELDA_ANCHO * atlas.escala);
  const h = Math.ceil(CELDA_ALTO * atlas.escala);
  return [w * (estado * CUADROS + cuadro), h * aspecto, w, h];
}

/** Proporción de la celda donde quedan los pies, para apoyar la figura sobre su punto del mapa. */
export const PIES_RELATIVO = PIES / CELDA_ALTO;
