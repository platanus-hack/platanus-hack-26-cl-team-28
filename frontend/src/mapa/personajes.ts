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
  /** Un color suave por aspecto, para las criaturas que todavía no responden. */
  pasteles: string[];
  rubor: string;
  brote: string;
  ojo: string;
  sombra: string;
}

/**
 * Cada figura es una criatura blanda y redonda, no una persona: cuerpo de color, pies
 * chicos, ojos grandes con brillo y mejillas. La postura se lee en la silueta y en la cara,
 * no solo en el color: a favor levanta los brazos y cierra los ojos de gusto, en contra se
 * eriza y frunce el ceño, indecisa se ladea y mira hacia su signo de pregunta.
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

/** Medio ancho y alto del cuerpo según el aspecto. Más anchas que altas: así se ven más tiernas. */
const CUERPOS: [number, number][] = [
  [8.4, 14.2],
  [7.6, 16],
  [9.2, 13.2],
  [7.4, 12.6],
  [8.2, 14],
  [7.8, 15],
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

function disco(ctx: CanvasRenderingContext2D, x: number, y: number, rx: number, ry: number, color: string): void {
  ctx.beginPath();
  ctx.ellipse(x, y, rx, ry, 0, 0, Math.PI * 2);
  ctx.fillStyle = color;
  ctx.fill();
}

function pies(p: Pincel, w: number): void {
  const paso = (p.cuadro - 1) * 0.25;
  disco(p.ctx, CX - w * 0.42, PIES - 0.5 + paso, 2.5, 1.5, p.tintas.tinta);
  disco(p.ctx, CX + w * 0.42, PIES - 0.5 - paso, 2.5, 1.5, p.tintas.tinta);
}

function color(p: Pincel): string {
  const { estado, tintas, aspecto } = p;
  return estado === ESTADO.neutra ? tintas.pasteles[aspecto] : [tintas.favor, tintas.contra, tintas.indecisa][estado - 2];
}

/** Contorno del cuerpo, más ancho abajo como una gota blanda. En contra, la coronilla se eriza. */
function cuerpo(p: Pincel, w: number, arriba: number, base: number): void {
  const { ctx, t, estado, detalle } = p;
  const cintura = arriba + (base - arriba) * 0.6;
  ctx.beginPath();
  ctx.moveTo(CX - w + t(1), cintura + t(2));
  if (estado === ESTADO.contra) {
    const puas = 4;
    for (let k = 0; k < puas; k++) {
      const x0 = CX - w + ((k + 0.5) / puas) * 2 * w;
      const x1 = CX - w + ((k + 1) / puas) * 2 * w;
      const curva = Math.sin(((k + 0.5) / puas) * Math.PI);
      ctx.lineTo(x0 + t(10 + k), arriba - 1.6 - curva * 1.4 + t(20 + k));
      ctx.lineTo(x1, k === puas - 1 ? cintura : arriba + 2.6 - curva * 1.8);
    }
  } else {
    ctx.bezierCurveTo(CX - w * 0.96 + t(3), arriba - 1.6 + t(4), CX + w * 0.96 + t(5), arriba - 1.6 + t(6), CX + w + t(7), cintura + t(8));
  }
  ctx.bezierCurveTo(CX + w * 1.04, base + 1.8, CX - w * 1.04, base + 1.8, CX - w + t(1), cintura + t(2));
  ctx.closePath();
  if (estado !== ESTADO.fantasma) {
    ctx.fillStyle = color(p);
    ctx.fill();
  }
  ctx.stroke();
  if (estado === ESTADO.fantasma || !detalle) return;
  // Brillo de caramelo arriba a la izquierda.
  ctx.save();
  ctx.strokeStyle = p.tintas.ojo;
  ctx.globalAlpha = 0.55;
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  ctx.arc(CX, cintura - 1, w * 0.72, Math.PI * 1.12, Math.PI * 1.34);
  ctx.stroke();
  ctx.restore();
}

/** Lo que cada criatura lleva en la cabeza: un brote, un mechón, cuernitos, un rulo, orejas o una antena. */
function adornos(p: Pincel, w: number, arriba: number): void {
  const { ctx, aspecto, estado, tintas } = p;
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
    relleno(tintas.brote);
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
      relleno(color(p));
    }
  } else if (aspecto === 3) {
    ctx.beginPath();
    ctx.arc(CX + 1.4, arriba - 1.8, 1.6, Math.PI * 0.6, Math.PI * 2.3);
    ctx.stroke();
  } else if (aspecto === 4) {
    for (const lado of [-1, 1]) {
      ctx.beginPath();
      ctx.arc(CX + lado * w * 0.64, arriba + 0.4, 2.5, 0, Math.PI * 2);
      relleno(color(p));
    }
  } else {
    linea(p, [CX, arriba - 0.6, CX + 0.6, arriba - 3.6]);
    ctx.beginPath();
    ctx.arc(CX + 0.7, arriba - 4.4, 1.3, 0, Math.PI * 2);
    relleno(tintas.rubor);
  }
}

/** Bracitos cortos y gruesos: arriba de gusto, abiertos de duda, en jarra de enojo. */
function brazos(p: Pincel, w: number, medio: number): void {
  const { ctx, estado, cuadro } = p;
  const vaiven = (cuadro - 1) * 0.8;
  ctx.save();
  ctx.lineWidth *= 1.5;
  if (estado === ESTADO.favor) {
    linea(p, [CX - w + 0.8, medio, CX - w - 2.8 - vaiven, medio - 5.6 + vaiven]);
    linea(p, [CX + w - 0.8, medio, CX + w + 2.8 - vaiven, medio - 5.6 - vaiven]);
  } else if (estado === ESTADO.indecisa) {
    linea(p, [CX - w + 0.6, medio + 2, CX - w - 2.6, medio + 0.8 + vaiven * 0.5]);
    linea(p, [CX + w - 0.6, medio + 2, CX + w + 2.6, medio + 0.8 - vaiven * 0.5]);
  } else if (estado === ESTADO.contra) {
    linea(p, [CX - w + 0.4, medio + 2, CX - w - 1.6, medio + 4.2, CX - w + 1, medio + 5.6]);
    linea(p, [CX + w - 0.4, medio + 2, CX + w + 1.6, medio + 4.2, CX + w - 1, medio + 5.6]);
  } else {
    linea(p, [CX - w + 0.4, medio + 2.4, CX - w - 1.4, medio + 4.4 + vaiven * 0.4]);
    linea(p, [CX + w - 0.4, medio + 2.4, CX + w + 1.4, medio + 4.4 - vaiven * 0.4]);
  }
  ctx.restore();
}

/** Ojo grande y redondo: blanco, pupila y un brillo. `mx`, `my` mueven la mirada. */
function ojo(p: Pincel, x: number, y: number, r: number, mx: number, my: number): void {
  const { ctx, tintas, detalle } = p;
  disco(ctx, x, y, r, r * 1.08, tintas.ojo);
  disco(ctx, x + mx, y + my, r * 0.62, r * 0.7, tintas.tinta);
  if (detalle) disco(ctx, x + mx - r * 0.2, y + my - r * 0.28, r * 0.24, r * 0.24, tintas.ojo);
}

function mejillas(p: Pincel, dx: number, y: number): void {
  const { ctx, tintas } = p;
  ctx.save();
  ctx.globalAlpha = 0.6;
  disco(ctx, CX - dx - 1.9, y, 1.7, 1.05, tintas.rubor);
  disco(ctx, CX + dx + 1.9, y, 1.7, 1.05, tintas.rubor);
  ctx.restore();
}

function boca(p: Pincel, y: number): void {
  const { ctx, estado, tintas, cuadro } = p;
  ctx.save();
  ctx.lineWidth *= 0.85;
  ctx.beginPath();
  if (estado === ESTADO.favor) {
    // Boca abierta de alegría.
    ctx.arc(CX, y - 0.2, 2, 0, Math.PI);
    ctx.closePath();
    ctx.fillStyle = tintas.tinta;
    ctx.fill();
    disco(ctx, CX, y + 1.1, 1.1, 0.6, tintas.rubor);
  } else if (estado === ESTADO.contra) {
    ctx.strokeStyle = tintas.tinta;
    ctx.arc(CX, y + 1.9, 1.7, 1.15 * Math.PI, 1.85 * Math.PI);
    ctx.stroke();
  } else if (estado === ESTADO.indecisa) {
    disco(ctx, CX + 0.6, y + 0.3 + (cuadro - 1) * 0.1, 0.85, 1, tintas.tinta);
  } else {
    ctx.strokeStyle = tintas.tinta;
    ctx.arc(CX, y - 0.6, 1.5, 0.15 * Math.PI, 0.85 * Math.PI);
    ctx.stroke();
  }
  ctx.restore();
}

function cara(p: Pincel, w: number, medio: number): void {
  const { ctx, estado, detalle, tintas } = p;
  if (estado === ESTADO.fantasma) {
    disco(ctx, CX - 2.6, medio, 0.9, 0.9, tintas.tinta);
    disco(ctx, CX + 2.6, medio, 0.9, 0.9, tintas.tinta);
    return;
  }
  const y = medio - 0.4;
  const dx = Math.min(3.5, w * 0.42);
  const r = detalle ? 2.15 : 2.3;
  if (estado !== ESTADO.contra) mejillas(p, dx, y + 2.6);
  if (estado === ESTADO.favor) {
    // Ojos cerrados de gusto: dos arcos.
    ctx.save();
    ctx.strokeStyle = tintas.ojo;
    ctx.lineWidth *= detalle ? 1.35 : 1.6;
    for (const lado of [-1, 1]) {
      ctx.beginPath();
      ctx.arc(CX + lado * dx, y + 0.9, 1.7, Math.PI * 1.12, Math.PI * 1.88);
      ctx.stroke();
    }
    ctx.restore();
  } else {
    const [mx, my] = estado === ESTADO.indecisa ? [0.7, -0.6] : estado === ESTADO.contra ? [0, 0.3] : [0, 0.1];
    ojo(p, CX - dx, y, r, mx, my);
    ojo(p, CX + dx, y, estado === ESTADO.indecisa ? r * 1.15 : r, mx, my);
  }
  if (estado === ESTADO.contra) {
    // Cejas fruncidas, que tapan un poco los ojos.
    ctx.save();
    ctx.lineWidth *= 1.5;
    linea(p, [CX - dx - 2.4, y - 3, CX - dx + 1.8, y - 1.3]);
    linea(p, [CX + dx + 2.4, y - 3, CX + dx - 1.8, y - 1.3]);
    ctx.restore();
  }
  if (detalle) boca(p, y + 3.6);
}

function duda(p: Pincel, arriba: number): void {
  const { ctx, cuadro } = p;
  const x = CX + 8.6;
  const y = Math.max(3.4, arriba - 4.2) + (cuadro - 1) * 0.5;
  ctx.save();
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
  ctx.lineWidth = detalle ? 1.15 : 1.2;
  ctx.strokeStyle = tintas.tinta;
  ctx.globalAlpha = estado === ESTADO.fantasma ? 0.3 : 1;
  if (estado !== ESTADO.fantasma) {
    ctx.fillStyle = tintas.sombra;
    ctx.beginPath();
    ctx.ellipse(CX, PIES + 0.5, w * 0.85, 1.3, 0, 0, Math.PI * 2);
    ctx.fill();
  }
  pies(p, w);
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
