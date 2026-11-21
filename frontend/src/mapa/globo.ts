import type { Colores } from './capaMapa';

interface Opciones {
  texto: string;
  /** Punto del que sale el globo (la cabeza de la figura). */
  x: number;
  y: number;
  /** Ancho del lienzo, para no salirse por los lados. */
  ancho: number;
  colores: Colores;
}

const ANCHO_MAXIMO = 210;
const RELLENO = 10;
const INTERLINEA = 18;
const COLA = 10;

function partir(ctx: CanvasRenderingContext2D, texto: string): string[] {
  const lineas: string[] = [];
  let actual = '';
  for (const palabra of texto.split(' ')) {
    const prueba = actual ? `${actual} ${palabra}` : palabra;
    if (actual && ctx.measureText(prueba).width > ANCHO_MAXIMO) {
      lineas.push(actual);
      actual = palabra;
    } else actual = prueba;
  }
  if (actual) lineas.push(actual);
  return lineas;
}

/** Globo de diálogo con la frase de una persona, escrito a mano como las demás voces. */
export function dibujarGlobo(ctx: CanvasRenderingContext2D, o: Opciones): void {
  ctx.save();
  ctx.font = `500 14px ${o.colores.fuenteMano}`;
  const lineas = partir(ctx, o.texto);
  const ancho = Math.max(...lineas.map((linea) => ctx.measureText(linea).width)) + RELLENO * 2;
  const alto = lineas.length * INTERLINEA + RELLENO * 1.4;
  const izquierda = Math.max(8, Math.min(o.ancho - ancho - 8, o.x - ancho * 0.3));
  const arriba = o.y - COLA - alto;
  ctx.beginPath();
  ctx.roundRect(izquierda, arriba, ancho, alto, 10);
  ctx.moveTo(o.x - 6, arriba + alto - 1);
  ctx.lineTo(o.x, o.y);
  ctx.lineTo(o.x + 8, arriba + alto - 1);
  ctx.fillStyle = o.colores.papel;
  ctx.strokeStyle = o.colores.tinta;
  ctx.lineWidth = 1.5;
  ctx.lineJoin = 'round';
  ctx.stroke();
  ctx.fill();
  ctx.fillStyle = o.colores.tinta;
  ctx.textBaseline = 'middle';
  ctx.textAlign = 'left';
  lineas.forEach((linea, i) => ctx.fillText(linea, izquierda + RELLENO, arriba + RELLENO * 0.7 + INTERLINEA * (i + 0.5)));
  ctx.restore();
}
