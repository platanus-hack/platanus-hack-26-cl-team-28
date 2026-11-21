import type { Colores } from './capaMapa';

interface Opciones {
  texto: string;
  /** Punto del que sale el globo (la cabeza de la figura). */
  x: number;
  y: number;
  /** Punto bajo los pies: si el globo no cabe arriba, sale desde aquí hacia abajo. */
  yPies: number;
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
  const cabe = o.y - COLA - alto > 6;
  const arriba = cabe ? o.y - COLA - alto : o.yPies + COLA;
  const borde = cabe ? arriba + alto - 1 : arriba + 1;
  ctx.beginPath();
  ctx.roundRect(izquierda, arriba, ancho, alto, 10);
  ctx.moveTo(o.x - 6, borde);
  ctx.lineTo(o.x, cabe ? o.y : o.yPies);
  ctx.lineTo(o.x + 8, borde);
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
