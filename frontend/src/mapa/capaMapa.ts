import type { Camara } from './camara';
import { OCEANO, ROTULOS, type Caminos, type Cumbre, type Ola } from './geografia';

/** Bajo esta escala (píxeles por grado) el nombre del océano estorba más de lo que orienta. */
const ESCALA_MINIMA_OCEANO = 12;
const ALTO_ROTULO = 17;
const PRIORIDAD = ['Santiago', 'Punta Arenas', 'Arica', 'Concepción', 'Antofagasta', 'Puerto Montt', 'La Serena', 'Coyhaique'];
const ROTULOS_POR_PRIORIDAD = [...ROTULOS].sort((a, b) => PRIORIDAD.indexOf(a.texto) - PRIORIDAD.indexOf(b.texto));

export interface Colores {
  mar: string;
  marTrazo: string;
  tierra: string;
  vecino: string;
  vecinoBorde: string;
  regionBorde: string;
  cordillera: string;
  costaClara: string;
  tinta: string;
  tintaSuave: string;
  papel: string;
  fuenteUi: string;
  fuenteMano: string;
}

interface Lienzo {
  ctx: CanvasRenderingContext2D;
  ancho: number;
  alto: number;
  dpr: number;
}

function cumbres(ctx: CanvasRenderingContext2D, lista: Cumbre[], colores: Colores, k: number): void {
  ctx.strokeStyle = colores.cordillera;
  ctx.lineWidth = 1.2 / k;
  ctx.lineJoin = 'round';
  ctx.lineCap = 'round';
  for (const lejana of [true, false]) {
    ctx.globalAlpha = lejana ? 0.4 : 0.9;
    ctx.beginPath();
    for (const c of lista) {
      if (c.lejana !== lejana) continue;
      ctx.moveTo(c.x - c.alto * 0.66, c.y);
      ctx.lineTo(c.x - c.alto * 0.08, c.y - c.alto);
      ctx.lineTo(c.x + c.alto * 0.6, c.y);
      ctx.moveTo(c.x - c.alto * 0.08, c.y - c.alto);
      ctx.lineTo(c.x + c.alto * 0.12, c.y - c.alto * 0.45);
    }
    ctx.stroke();
  }
  ctx.globalAlpha = 1;
}

/** Capa que solo cambia con la cámara: mar, países vecinos, regiones, cordillera y nombres de países. */
export function dibujarMapa(l: Lienzo, camara: Camara, caminos: Caminos, cordillera: Cumbre[], colores: Colores): void {
  const { ctx, ancho, alto, dpr } = l;
  const k = camara.escala;
  const [ox, oy] = camara.aPantalla(0, 0);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.fillStyle = colores.mar;
  ctx.fillRect(0, 0, ancho, alto);
  ctx.setTransform(dpr * k, 0, 0, dpr * k, dpr * ox, dpr * oy);
  ctx.fillStyle = colores.vecino;
  ctx.fill(caminos.vecinos);
  ctx.strokeStyle = colores.vecinoBorde;
  ctx.lineWidth = 1 / k;
  ctx.stroke(caminos.vecinos);
  // Franja clara de aguas bajas alrededor de la costa.
  ctx.lineJoin = 'round';
  ctx.strokeStyle = colores.costaClara;
  ctx.lineWidth = 9 / k;
  ctx.stroke(caminos.chile);
  ctx.fillStyle = colores.tierra;
  ctx.fill(caminos.chile);
  ctx.strokeStyle = colores.regionBorde;
  ctx.lineWidth = 0.9 / k;
  ctx.stroke(caminos.chile);
  cumbres(ctx, cordillera, colores, k);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  if (k < ESCALA_MINIMA_OCEANO) return;
  const [x, y] = camara.aPantalla(OCEANO.x, OCEANO.y);
  ctx.save();
  ctx.translate(x, y);
  ctx.rotate(-Math.PI / 2);
  ctx.font = `600 11px ${colores.fuenteUi}`;
  ctx.letterSpacing = '0.24em';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillStyle = colores.tintaSuave;
  ctx.globalAlpha = 0.75;
  ctx.fillText(OCEANO.texto, 0, 0);
  ctx.restore();
}

export function dibujarOlas(l: Lienzo, camara: Camara, olas: Ola[], colores: Colores, tiempo: number): void {
  const { ctx, ancho, alto } = l;
  ctx.strokeStyle = colores.marTrazo;
  ctx.lineWidth = 1.2;
  ctx.lineCap = 'round';
  ctx.globalAlpha = 0.6;
  ctx.beginPath();
  for (const ola of olas) {
    const [bx, y] = camara.aPantalla(ola.x, ola.y);
    const x = bx + Math.sin(tiempo * 0.7 + ola.fase) * 4;
    if (x < -12 || x > ancho + 12 || y < -6 || y > alto + 6) continue;
    ctx.moveTo(x - 6, y);
    ctx.quadraticCurveTo(x - 3, y - 3, x, y);
    ctx.quadraticCurveTo(x + 3, y + 3, x + 6, y);
  }
  ctx.stroke();
  ctx.globalAlpha = 1;
}

/** Ciudades de referencia, rotuladas a mano mar adentro o al otro lado de la cordillera. */
export function dibujarRotulos(l: Lienzo, camara: Camara, colores: Colores): void {
  const { ctx } = l;
  ctx.font = `500 13px ${colores.fuenteMano}`;
  ctx.textBaseline = 'middle';
  ctx.lineJoin = 'round';
  const ocupados: [number, boolean][] = [];
  for (const rotulo of ROTULOS_POR_PRIORIDAD) {
    const [x, y] = camara.aPantalla(rotulo.x, rotulo.y);
    // Si choca con uno que ya está, no se dibuja: de lejos quedan las ciudades principales.
    if (ocupados.some(([oy, mar]) => mar === rotulo.haciaElMar && Math.abs(oy - y) < ALTO_ROTULO)) continue;
    ocupados.push([y, rotulo.haciaElMar]);
    const [xTexto] = camara.aPantalla(rotulo.xTexto, rotulo.y);
    ctx.strokeStyle = colores.tinta;
    ctx.lineWidth = 1;
    ctx.globalAlpha = 0.55;
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.lineTo(xTexto, y);
    ctx.stroke();
    ctx.globalAlpha = 1;
    ctx.textAlign = rotulo.haciaElMar ? 'right' : 'left';
    // El texto nunca se sale por la izquierda aunque la costa quede cerca del borde.
    const ancho = ctx.measureText(rotulo.texto).width;
    const xLetra = rotulo.haciaElMar ? Math.max(ancho + 6, xTexto - 4) : xTexto + 4;
    ctx.strokeStyle = rotulo.haciaElMar ? colores.mar : colores.vecino;
    ctx.lineWidth = 4;
    ctx.strokeText(rotulo.texto, xLetra, y);
    ctx.fillStyle = colores.tinta;
    ctx.fillText(rotulo.texto, xLetra, y);
  }
}
