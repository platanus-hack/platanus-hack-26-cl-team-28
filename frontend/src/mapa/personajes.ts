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
  /** Un color apagado por aspecto, para las criaturas que todavía no responden. */
  cuerpos: string[];
  sombra: string;
}

/**
 * Cada figura es una criatura de forma simple, no una persona: un cuerpo de color plano con
 * un contorno del mismo tono, pies cortos y dos ojos. Sin mejillas ni brillos: la gracia
 * está en la postura. A favor levanta los brazos y entrecierra los ojos de gusto; en contra
 * se eriza y baja los párpados; indecisa se ladea, levanta una ceja y mira su signo de pregunta.
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
  /** Color del cuerpo y su tono oscuro, que hace de contorno, pies y brazos. */
  cuerpo: string;
  borde: string;
}

/** Medio ancho y alto del cuerpo según el aspecto. */
const CUERPOS: [number, number][] = [
  [8.2, 14.4],
  [7.4, 16.4],
  [9, 13.4],
  [7.2, 12.8],
  [8, 14.2],
  [7.6, 15.2],
];

/** Mezcla dos colores `#rrggbb`: `peso` es cuánto pesa el segundo. */
export function mezclarColor(a: string, b: string, peso: number): string {
  const canal = (c: string, i: number) => parseInt(c.slice(1 + i * 2, 3 + i * 2), 16);
  const partes = [0, 1, 2].map((i) => Math.round(canal(a, i) * (1 - peso) + canal(b, i) * peso));
  return `#${partes.map((v) => v.toString(16).padStart(2, '0')).join('')}`;
}

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

function disco(ctx: CanvasRenderingContext2D, x: number, y: number, rx: number, ry: number, color: string): void {
  ctx.beginPath();
  ctx.ellipse(x, y, rx, ry, 0, 0, Math.PI * 2);
  ctx.fillStyle = color;
  ctx.fill();
}

function pies(p: Pincel, w: number): void {
  const paso = (p.cuadro - 1) * 0.25;
  disco(p.ctx, CX - w * 0.4, PIES - 0.6 + paso, 2.4, 1.5, p.borde);
  disco(p.ctx, CX + w * 0.4, PIES - 0.6 - paso, 2.4, 1.5, p.borde);
}

/** Contorno del cuerpo: una gota, más ancha abajo. En contra, la coronilla se eriza. */
function contorno(p: Pincel, w: number, arriba: number, base: number): Path2D {
  const { t, estado } = p;
  const cintura = arriba + (base - arriba) * 0.6;
  const camino = new Path2D();
  camino.moveTo(CX - w + t(1), cintura + t(2));
  if (estado === ESTADO.contra) {
    const puas = 3;
    for (let k = 0; k < puas; k++) {
      const x0 = CX - w + ((k + 0.5) / puas) * 2 * w;
      const x1 = CX - w + ((k + 1) / puas) * 2 * w;
      const curva = Math.sin(((k + 0.5) / puas) * Math.PI);
      camino.lineTo(x0 + t(10 + k), arriba - 1.4 - curva * 1.8 + t(20 + k));
      camino.lineTo(x1, k === puas - 1 ? cintura : arriba + 3 - curva * 1.6);
    }
  } else {
    camino.bezierCurveTo(CX - w * 0.96 + t(3), arriba - 1.6 + t(4), CX + w * 0.96 + t(5), arriba - 1.6 + t(6), CX + w + t(7), cintura + t(8));
  }
  camino.bezierCurveTo(CX + w * 1.04, base + 1.8, CX - w * 1.04, base + 1.8, CX - w + t(1), cintura + t(2));
  camino.closePath();
  return camino;
}

function cuerpo(p: Pincel, w: number, arriba: number, base: number): void {
  const { ctx, estado } = p;
  const camino = contorno(p, w, arriba, base);
  if (estado !== ESTADO.fantasma) {
    ctx.fillStyle = p.cuerpo;
    ctx.fill(camino);
    // Sombra plana abajo a la derecha: da volumen sin brillos.
    ctx.save();
    ctx.clip(camino);
    ctx.globalAlpha = 0.16;
    disco(ctx, CX + w * 0.55, base + 0.5, w * 1.25, (base - arriba) * 0.42, p.borde);
    ctx.restore();
  }
  ctx.stroke(camino);
}

/** Lo que cada criatura lleva en la cabeza, en su mismo tono: una hoja, un mechón, puntas, un rulo, orejas o una antena. */
function adornos(p: Pincel, w: number, arriba: number): void {
  const { ctx, aspecto, estado } = p;
  if (estado === ESTADO.contra) return;
  const relleno = (c: string) => {
    if (estado !== ESTADO.fantasma) {
      ctx.fillStyle = c;
      ctx.fill();
    }
    ctx.stroke();
  };
  if (aspecto === 0) {
    linea(p, [CX, arriba - 0.6, CX + 0.4, arriba - 3]);
    ctx.beginPath();
    ctx.ellipse(CX + 2.6, arriba - 3.6, 2.5, 1.4, -0.5, 0, Math.PI * 2);
    relleno(p.cuerpo);
  } else if (aspecto === 1) {
    linea(p, [CX - 1.6, arriba - 0.4, CX - 2.2, arriba - 2.8]);
    linea(p, [CX, arriba - 0.8, CX, arriba - 3.4]);
    linea(p, [CX + 1.6, arriba - 0.4, CX + 2.2, arriba - 2.8]);
  } else if (aspecto === 2) {
    for (const lado of [-1, 1]) {
      ctx.beginPath();
      ctx.moveTo(CX + lado * w * 0.62, arriba + 0.6);
      ctx.lineTo(CX + lado * w * 0.5, arriba - 2.6);
      ctx.lineTo(CX + lado * w * 0.28, arriba - 0.2);
      relleno(p.cuerpo);
    }
  } else if (aspecto === 3) {
    ctx.beginPath();
    ctx.arc(CX + 1.4, arriba - 1.8, 1.6, Math.PI * 0.6, Math.PI * 2.3);
    ctx.stroke();
  } else if (aspecto === 4) {
    for (const lado of [-1, 1]) {
      ctx.beginPath();
      ctx.arc(CX + lado * w * 0.64, arriba + 0.4, 2.4, 0, Math.PI * 2);
      relleno(p.cuerpo);
    }
  } else {
    linea(p, [CX, arriba - 0.6, CX + 0.6, arriba - 3.6]);
    disco(ctx, CX + 0.7, arriba - 4.3, 1.25, 1.25, p.borde);
  }
}

/** Brazos cortos: arriba de gusto, abiertos de duda, en jarra de enojo. */
function brazos(p: Pincel, w: number, medio: number): void {
  const { ctx, estado, cuadro } = p;
  const vaiven = (cuadro - 1) * 0.8;
  ctx.save();
  ctx.lineWidth *= 1.6;
  if (estado === ESTADO.favor) {
    linea(p, [CX - w + 0.8, medio, CX - w - 2.8 - vaiven, medio - 5.6 + vaiven]);
    linea(p, [CX + w - 0.8, medio, CX + w + 2.8 - vaiven, medio - 5.6 - vaiven]);
  } else if (estado === ESTADO.indecisa) {
    linea(p, [CX - w + 0.6, medio + 2, CX - w - 2.6, medio + 0.8 + vaiven * 0.5]);
    linea(p, [CX + w - 0.6, medio + 2, CX + w + 2.6, medio + 0.8 - vaiven * 0.5]);
  } else if (estado === ESTADO.contra) {
    linea(p, [CX - w + 0.4, medio + 2, CX - w - 1.6, medio + 4.2, CX - w + 1, medio + 5.6]);
    linea(p, [CX + w - 0.4, medio + 2, CX + w + 1.6, medio + 4.2, CX + w - 1, medio + 5.6]);
  }
  ctx.restore();
}

/** Ojo: un óvalo de tinta, sin blanco ni brillo. */
function ojo(p: Pincel, x: number, y: number, rx: number, ry: number): void {
  disco(p.ctx, x, y, rx, ry, p.tintas.tinta);
}

function cara(p: Pincel, w: number, medio: number): void {
  const { ctx, estado, detalle, tintas, cuadro } = p;
  const y = medio - 0.2;
  const dx = Math.min(3.1, w * 0.38);
  const rx = detalle ? 1.15 : 1.35;
  const ry = detalle ? 1.75 : 1.9;
  ctx.save();
  ctx.strokeStyle = tintas.tinta;
  if (estado === ESTADO.favor) {
    // Ojos entrecerrados de gusto y una sonrisa corta.
    ctx.lineWidth *= detalle ? 1.2 : 1.5;
    for (const lado of [-1, 1]) {
      ctx.beginPath();
      ctx.arc(CX + lado * dx, y + 0.8, 1.6, Math.PI * 1.1, Math.PI * 1.9);
      ctx.stroke();
    }
    if (detalle) {
      ctx.lineWidth *= 0.8;
      ctx.beginPath();
      ctx.arc(CX, y + 2.4, 1.7, 0.12 * Math.PI, 0.88 * Math.PI);
      ctx.stroke();
    }
  } else if (estado === ESTADO.contra) {
    // Párpados caídos: el ojo queda cortado por una ceja recta e inclinada.
    ojo(p, CX - dx, y + 0.3, rx, ry * 0.9);
    ojo(p, CX + dx, y + 0.3, rx, ry * 0.9);
    ctx.lineWidth *= 1.5;
    ctx.lineCap = 'butt';
    ctx.strokeStyle = p.cuerpo;
    linea(p, [CX - dx - 2.2, y - 1.9, CX - dx + 1.8, y - 0.5]);
    linea(p, [CX + dx + 2.2, y - 1.9, CX + dx - 1.8, y - 0.5]);
    ctx.strokeStyle = tintas.tinta;
    ctx.lineCap = 'round';
    ctx.lineWidth /= 1.5;
    linea(p, [CX - dx - 2.3, y - 2.7, CX - dx + 1.7, y - 1.2]);
    linea(p, [CX + dx + 2.3, y - 2.7, CX + dx - 1.7, y - 1.2]);
    if (detalle) {
      ctx.lineWidth *= 0.8;
      ctx.beginPath();
      ctx.arc(CX, y + 5, 1.5, 1.2 * Math.PI, 1.8 * Math.PI);
      ctx.stroke();
    }
  } else if (estado === ESTADO.indecisa) {
    // Un ojo más abierto que el otro y una ceja levantada.
    ojo(p, CX - dx + 0.5, y - 0.3, rx * 0.9, ry * 0.75);
    ojo(p, CX + dx + 0.5, y - 0.6, rx * 1.1, ry * 1.05);
    if (detalle) {
      ctx.lineWidth *= 0.8;
      linea(p, [CX + dx - 1.2, y - 3.9, CX + dx + 2.2, y - 4.4]);
      linea(p, [CX - 1, y + 3.4, CX + 1.4, y + 3 + (cuadro - 1) * 0.1]);
    }
  } else if (estado === ESTADO.fantasma) {
    ojo(p, CX - dx, y, rx * 0.8, rx * 0.8);
    ojo(p, CX + dx, y, rx * 0.8, rx * 0.8);
  } else {
    ojo(p, CX - dx, y, rx, ry);
    ojo(p, CX + dx, y, rx, ry);
  }
  ctx.restore();
}

function duda(p: Pincel, arriba: number): void {
  const { ctx, cuadro } = p;
  const x = CX + 8.6;
  const y = Math.max(3.4, arriba - 4.2) + (cuadro - 1) * 0.5;
  ctx.save();
  ctx.strokeStyle = p.tintas.tinta;
  ctx.lineWidth *= 1.2;
  ctx.beginPath();
  ctx.moveTo(x - 1.6, y);
  ctx.quadraticCurveTo(x - 1.4, y - 2.6, x + 0.4, y - 2.4);
  ctx.quadraticCurveTo(x + 2.4, y - 2, x + 1.2, y + 0.2);
  ctx.quadraticCurveTo(x + 0.2, y + 1.2, x + 0.2, y + 2.4);
  ctx.stroke();
  disco(ctx, x + 0.2, y + 4.4, 0.65, 0.65, p.tintas.tinta);
  ctx.restore();
}

function colorCuerpo(estado: EstadoFigura, aspecto: number, tintas: Tintas): string {
  if (estado === ESTADO.favor) return tintas.favor;
  if (estado === ESTADO.contra) return tintas.contra;
  if (estado === ESTADO.indecisa) return tintas.indecisa;
  return tintas.cuerpos[aspecto];
}

/** Dibuja una figura en el origen del contexto, en unidades de celda. */
export function dibujarFigura(
  ctx: CanvasRenderingContext2D,
  opciones: { estado: EstadoFigura; aspecto: number; cuadro: number; tintas: Tintas; detalle: boolean },
): void {
  const { estado, aspecto, cuadro, tintas, detalle } = opciones;
  const semilla = aspecto * 31 + cuadro * 7 + estado * 131;
  const base = colorCuerpo(estado, aspecto, tintas);
  const p: Pincel = {
    ctx, estado, aspecto, cuadro, tintas, detalle,
    t: (n) => (mezclar(semilla, n) - 0.5) * 0.5,
    cuerpo: base,
    borde: estado === ESTADO.fantasma ? tintas.tinta : mezclarColor(base, tintas.tinta, 0.58),
  };
  const [w, alto] = CUERPOS[aspecto];
  const abajo = PIES - 2.4;
  const arriba = abajo - alto;
  const medio = (arriba + abajo) / 2;
  ctx.save();
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  ctx.lineWidth = detalle ? 1.1 : 1.25;
  ctx.strokeStyle = p.borde;
  ctx.globalAlpha = estado === ESTADO.fantasma ? 0.3 : 1;
  if (estado !== ESTADO.fantasma) {
    disco(ctx, CX, PIES + 0.5, w * 0.85, 1.3, tintas.sombra);
    pies(p, w);
  }
  if (estado === ESTADO.indecisa) {
    ctx.translate(CX, abajo);
    ctx.rotate(0.13);
    ctx.translate(-CX, -abajo);
  }
  brazos(p, w, medio);
  adornos(p, w, arriba);
  cuerpo(p, w, arriba, abajo);
  cara(p, w, medio);
  ctx.restore();
  if (estado === ESTADO.indecisa) {
    ctx.save();
    ctx.lineCap = 'round';
    ctx.lineWidth = 1.1;
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
