import { hashTexto, mezclar } from '../dominio/azar';

/**
 * El wati: el personaje de cada persona simulada. Un cuerpo redondo con contorno café, ojos
 * separados, sonrisa corta, bracitos, piecitos y un adorno en la cabeza que cambia de persona en
 * persona. Se dibuja en unidades de celda (CELDA_ANCHO × CELDA_ALTO) con los pies en (CX, PIES).
 */
export const CELDA_ANCHO = 40;
export const CELDA_ALTO = 46;
const CX = 20;
const PIES = 44.4;
/** Proporción de la celda donde quedan los pies, para apoyar el wati sobre su punto. */
export const PIES_RELATIVO = PIES / CELDA_ALTO;

/** Adornos distintos; la mitad de las personas lo lleva reflejado. */
export const CABEZAS = 12;
export const VARIANTES = CABEZAS * 2;
/** Cara de reposo y los tres cuadros del bostezo. */
export const CARAS = 4;
export const TONOS = 3;

const LW = 1.5;
const BORDE = '#3a1f1b';
const OJO = '#2b1511';
const BOCA = '#4a1c18';
const LENGUA = '#e0706a';

// ---------- Color ----------

const canal = (c: string, i: number) => parseInt(c.slice(1 + i * 2, 3 + i * 2), 16);

/** Mezcla dos colores `#rrggbb`: `peso` es cuánto pesa el segundo. */
export function mezclarColor(a: string, b: string, peso: number): string {
  return `#${[0, 1, 2].map((i) => Math.round(canal(a, i) * (1 - peso) + canal(b, i) * peso).toString(16).padStart(2, '0')).join('')}`;
}

function aHsl(c: string): [number, number, number] {
  const r = canal(c, 0) / 255;
  const g = canal(c, 1) / 255;
  const b = canal(c, 2) / 255;
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const l = (max + min) / 2;
  if (max === min) return [0, 0, l];
  const d = max - min;
  const s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
  const h = max === r ? (g - b) / d + (g < b ? 6 : 0) : max === g ? (b - r) / d + 2 : (r - g) / d + 4;
  return [h * 60, s, l];
}

function deHsl(h: number, s: number, l: number): string {
  const tono = ((h % 360) + 360) % 360;
  const sat = Math.max(0, Math.min(1, s));
  const luz = Math.max(0, Math.min(1, l));
  const a = sat * Math.min(luz, 1 - luz);
  const f = (n: number) => {
    const k = (n + tono / 30) % 12;
    return luz - a * Math.max(-1, Math.min(k - 3, 9 - k, 1));
  };
  return `#${[f(0), f(8), f(4)].map((v) => Math.round(v * 255).toString(16).padStart(2, '0')).join('')}`;
}

/**
 * Tres tonos de un color sin perder saturación: el claro se acerca al amarillo y el oscuro se
 * aleja de él (el amarillo oscuro queda mostaza, como en la referencia). El del medio es la base.
 * Con `suave` (quienes aún no responden) solo cambia un poco la luz: así no se confunden con una
 * postura.
 */
export function tonosDe(base: string, suave = false): string[] {
  if (!/^#[0-9a-f]{6}$/i.test(base)) return [base, base, base];
  const [h, s, l] = aHsl(base);
  if (suave) return [deHsl(h, s, l + 0.05), base, deHsl(h, s * 0.8, l - 0.07)];
  const hacia = Math.sign(50 - h) * Math.min(7, Math.abs(50 - h));
  return [deHsl(h + hacia, Math.min(0.95, s + 0.05), l + 0.09), base, deHsl(h - hacia * 0.8, Math.min(0.85, s + 0.04), l - 0.12)];
}

// ---------- Dibujo ----------

function muestrear(c: number[], n = 12): [number, number][] {
  const puntos: [number, number][] = [[c[0], c[1]]];
  for (let i = 2; i + 5 < c.length; i += 6) {
    const [x0, y0] = puntos[puntos.length - 1];
    for (let k = 1; k <= n; k++) {
      const t = k / n;
      const u = 1 - t;
      puntos.push([
        u * u * u * x0 + 3 * u * u * t * c[i] + 3 * u * t * t * c[i + 2] + t * t * t * c[i + 4],
        u * u * u * y0 + 3 * u * u * t * c[i + 1] + 3 * u * t * t * c[i + 3] + t * t * t * c[i + 5],
      ]);
    }
  }
  return puntos;
}

/** Tubo que se afina hacia la punta (curvas de Bézier encadenadas): primero el contorno y encima el relleno. */
function tubo(ctx: CanvasRenderingContext2D, curva: number[], grueso: number, punta: number, cuerpo: string): void {
  const puntos = muestrear(curva);
  ctx.lineCap = 'round';
  for (const pasada of [0, 1]) {
    ctx.strokeStyle = pasada ? cuerpo : BORDE;
    for (let i = 0; i < puntos.length - 1; i++) {
      ctx.lineWidth = grueso + (punta - grueso) * (i / (puntos.length - 2)) + (pasada ? 0 : LW * 2);
      ctx.beginPath();
      ctx.moveTo(puntos[i][0], puntos[i][1]);
      ctx.lineTo(puntos[i + 1][0], puntos[i + 1][1]);
      ctx.stroke();
    }
  }
}

function rellenar(ctx: CanvasRenderingContext2D, camino: Path2D, cuerpo: string): void {
  ctx.fillStyle = cuerpo;
  ctx.fill(camino);
  ctx.strokeStyle = BORDE;
  ctx.lineWidth = LW;
  ctx.stroke(camino);
}

/** Mechón de puntas alrededor de (cx, base), entre dos ángulos en grados. */
function penacho(cx: number, base: number, puntas: number, desde: number, hasta: number, largos: number[], adentro: number, inclina: number): Path2D {
  const p = new Path2D();
  const rad = (g: number) => (g * Math.PI) / 180;
  p.moveTo(cx + Math.cos(rad(desde - 12)) * 5, base + Math.sin(rad(desde - 12)) * 5 + 2);
  const paso = (hasta - desde) / (puntas - 1);
  for (let k = 0; k < puntas; k++) {
    const a = rad(desde + paso * k);
    const largo = largos[k % largos.length];
    p.lineTo(cx + Math.cos(a) * largo + inclina, base + Math.sin(a) * largo);
    if (k < puntas - 1) {
      const b = rad(desde + paso * (k + 0.5));
      p.lineTo(cx + Math.cos(b) * adentro + inclina * 0.3, base + Math.sin(b) * adentro);
    }
  }
  p.lineTo(cx + Math.cos(rad(hasta + 12)) * 5, base + Math.sin(rad(hasta + 12)) * 5 + 2);
  p.closePath();
  return p;
}

/** Los doce adornos: púa, llama, rulo, brote, hoja, ola, espiral, gancho, mechón, penacho, pasto y nube. */
function adorno(ctx: CanvasRenderingContext2D, k: number, T: number, cuerpo: string): void {
  const c = CX;
  ctx.lineJoin = 'round';
  if (k === 0) {
    const p = new Path2D();
    p.moveTo(c + 1, T + 3);
    p.quadraticCurveTo(c + 4, T - 3, c + 7.5, T - 10);
    p.quadraticCurveTo(c + 8.4, T - 3, c + 8.6, T + 3);
    p.closePath();
    rellenar(ctx, p, cuerpo);
  } else if (k === 1) {
    const p = new Path2D();
    p.moveTo(c - 2, T + 3);
    p.bezierCurveTo(c - 1, T - 3, c + 5, T - 3.5, c + 6, T - 7);
    p.bezierCurveTo(c + 6.6, T - 9, c + 5.8, T - 10.6, c + 4.6, T - 11.6);
    p.bezierCurveTo(c + 10, T - 10, c + 11.4, T - 3, c + 7.4, T + 3);
    p.closePath();
    rellenar(ctx, p, cuerpo);
  } else if (k === 2) {
    tubo(ctx, [c + 2, T + 3, c + 1, T - 4, c + 3, T - 9.5, c + 7.2, T - 10, c + 10.8, T - 10.4, c + 11.6, T - 6, c + 9, T - 4.4], 3.4, 1.3, cuerpo);
  } else if (k === 3) {
    tubo(ctx, [c, T + 3, c - 0.6, T - 5, c + 1, T - 9.5, c + 5.5, T - 12.4], 2.9, 0.9, cuerpo);
  } else if (k === 4) {
    tubo(ctx, [c + 2, T + 3, c + 3, T - 2, c + 4, T - 5.5, c + 5, T - 7.6], 2.6, 1.9, cuerpo);
    tubo(ctx, [c + 5, T - 7.6, c + 4.2, T - 10, c + 3.4, T - 12, c + 3.4, T - 14], 1.9, 0.6, cuerpo);
    tubo(ctx, [c + 5, T - 7.6, c + 8, T - 9, c + 11, T - 9, c + 13.4, T - 7.6], 1.9, 0.6, cuerpo);
  } else if (k === 5) {
    tubo(ctx, [c + 1, T + 3, c + 1, T - 5, c + 6, T - 7, c + 9, T - 6, c + 12, T - 5, c + 14.2, T - 7, c + 14.2, T - 11.4], 3.1, 0.9, cuerpo);
  } else if (k === 6) {
    tubo(
      ctx,
      [c, T + 3, c, T - 3, c - 1, T - 6, c - 3, T - 8, c - 6.2, T - 10.4, c - 4.2, T - 14.4, c - 1, T - 13.8, c + 1.6, T - 13.2, c + 1.4, T - 10, c - 0.8, T - 10.2],
      2.5,
      1.2,
      cuerpo,
    );
  } else if (k === 7) {
    tubo(ctx, [c + 1, T + 3, c + 1, T - 5, c + 2, T - 10, c + 5, T - 11, c + 8.2, T - 12, c + 9.2, T - 8.8, c + 7, T - 7.4], 2.5, 1, cuerpo);
  } else if (k === 8) {
    tubo(ctx, [c + 1, T + 3, c + 1, T - 6, c + 8, T - 9, c + 13, T - 8, c + 16, T - 7.4, c + 16.2, T - 11, c + 14, T - 12.2], 2.9, 0.8, cuerpo);
  } else if (k === 9) {
    rellenar(ctx, penacho(c + 0.5, T + 3, 7, -158, -22, [8.2, 9.6, 8.6, 10, 8.4], 4.6, 0), cuerpo);
  } else if (k === 10) {
    rellenar(ctx, penacho(c + 1, T + 3, 5, -134, -34, [11, 12.4, 11.6, 12.8, 10.6], 4, 3.2), cuerpo);
  } else {
    const bolas = [
      [c - 2.4, T + 1, 3.8],
      [c + 2.2, T - 1.8, 4],
      [c + 6.6, T + 0.2, 3.6],
      [c + 7.6, T + 3.6, 3],
    ];
    for (const pasada of [0, 1]) {
      ctx.fillStyle = pasada ? cuerpo : BORDE;
      for (const [x, y, r] of bolas) {
        ctx.beginPath();
        ctx.arc(x, y, r + (pasada ? 0 : LW), 0, Math.PI * 2);
        ctx.fill();
      }
    }
  }
}

function ojoAbierto(ctx: CanvasRenderingContext2D, x: number, y: number): void {
  ctx.fillStyle = OJO;
  ctx.beginPath();
  ctx.arc(x, y, 2.1, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = 'rgba(255,255,255,0.85)';
  ctx.beginPath();
  ctx.arc(x - 0.65, y - 0.75, 0.62, 0, Math.PI * 2);
  ctx.fill();
}

function boca(ctx: CanvasRenderingContext2D, y: number, rx: number, ry: number, lengua: boolean): void {
  ctx.fillStyle = BOCA;
  ctx.beginPath();
  ctx.ellipse(CX, y, rx, ry, 0, 0, Math.PI * 2);
  ctx.fill();
  if (!lengua) return;
  ctx.save();
  ctx.clip();
  ctx.fillStyle = LENGUA;
  ctx.beginPath();
  ctx.ellipse(CX, y + ry * 0.78, rx * 0.9, ry * 0.5, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();
}

/** 0: reposo. 1: entrecierra los ojos. 2: bosteza con la boca abierta. 3: va cerrando la boca. */
function cara(ctx: CanvasRenderingContext2D, medio: number, y: number, cuadro: number, animo: Animo): void {
  const dx = medio * 0.56;
  ctx.lineCap = 'round';
  if (cuadro === 0) {
    ojoAbierto(ctx, CX - dx, y);
    ojoAbierto(ctx, CX + dx, y);
    ctx.strokeStyle = OJO;
    ctx.lineWidth = 1.15;
    ctx.beginPath();
    if (animo === 'triste') {
      // Boca hacia abajo y cejas que suben hacia el centro.
      ctx.arc(CX, y + 2.6, 1.7, 1.18 * Math.PI, 1.82 * Math.PI);
      ctx.stroke();
      ctx.lineWidth = 1;
      for (const lado of [-1, 1]) {
        ctx.beginPath();
        ctx.moveTo(CX + lado * (dx - 1.5), y - 3.6);
        ctx.lineTo(CX + lado * (dx + 1.6), y - 2.7);
        ctx.stroke();
      }
    } else if (animo === 'seria') {
      // Boca recta, sin sonrisa.
      ctx.moveTo(CX - 1.6, y + 1.3);
      ctx.lineTo(CX + 1.6, y + 1.3);
      ctx.stroke();
    } else {
      ctx.arc(CX, y + 0.1, 1.7, 0.15 * Math.PI, 0.85 * Math.PI);
      ctx.stroke();
    }
    return;
  }
  if (cuadro === 1) {
    ctx.fillStyle = OJO;
    for (const lado of [-1, 1]) {
      ctx.beginPath();
      ctx.ellipse(CX + lado * dx, y + 0.5, 2.1, 0.95, 0, 0, Math.PI * 2);
      ctx.fill();
    }
    boca(ctx, y + 2.8, 1.3, 1.5, false);
    return;
  }
  ctx.strokeStyle = OJO;
  ctx.lineWidth = 1.35;
  for (const lado of [-1, 1]) {
    ctx.beginPath();
    ctx.arc(CX + lado * dx, y + 1.4, 1.9, 1.15 * Math.PI, 1.85 * Math.PI);
    ctx.stroke();
  }
  if (cuadro === 2) boca(ctx, y + 4, 2.5, 3.5, true);
  else boca(ctx, y + 3.3, 1.9, 2.4, true);
}

/** Gesto en reposo: sonríe, está triste (en contra) o serio (no se decide). */
export type Animo = 'alegre' | 'triste' | 'seria';

export interface OpcionesWati {
  cuerpo: string;
  /** 0 a VARIANTES - 1: desde CABEZAS el adorno va reflejado. */
  variante: number;
  /** 0 a CARAS - 1. */
  cuadro: number;
  animo?: Animo;
  /** Disfrazado de gato: orejas, cola, nariz y bigotes en vez del adorno. */
  gato?: boolean;
  /** Ángulo del brazo derecho, usado solo por el wati del mando. */
  saludo?: number;
}

/** Orejas y cola de gato; van detrás del cuerpo, que tapa donde se unen. */
function orejasYCola(ctx: CanvasRenderingContext2D, arriba: number, cuerpo: string): void {
  const interior = mezclarColor(cuerpo, LENGUA, 0.55);
  ctx.lineCap = 'round';
  // Cola: un trazo grueso café con el color del cuerpo encima, que sube en curva por el costado.
  const cola = new Path2D();
  cola.moveTo(CX + 11, 37.5);
  cola.bezierCurveTo(CX + 20.5, 38, CX + 21, 28, CX + 16.5, 24.5);
  ctx.strokeStyle = BORDE;
  ctx.lineWidth = 4.6;
  ctx.stroke(cola);
  ctx.strokeStyle = cuerpo;
  ctx.lineWidth = 2.5;
  ctx.stroke(cola);
  ctx.lineWidth = LW;
  ctx.strokeStyle = BORDE;
  for (const lado of [-1, 1]) {
    const oreja = new Path2D();
    oreja.moveTo(CX + lado * 3.6, arriba + 1.5);
    oreja.lineTo(CX + lado * 10.8, arriba - 8.2);
    oreja.lineTo(CX + lado * 13, arriba + 5.5);
    oreja.closePath();
    ctx.fillStyle = cuerpo;
    ctx.fill(oreja);
    ctx.stroke(oreja);
    const dentro = new Path2D();
    dentro.moveTo(CX + lado * 6.2, arriba + 1.6);
    dentro.lineTo(CX + lado * 10.4, arriba - 4.6);
    dentro.lineTo(CX + lado * 11.6, arriba + 3);
    dentro.closePath();
    ctx.fillStyle = interior;
    ctx.fill(dentro);
  }
}

/** Nariz y bigotes sobre la cara de reposo. */
function narizYBigotes(ctx: CanvasRenderingContext2D, y: number): void {
  ctx.fillStyle = LENGUA;
  ctx.beginPath();
  ctx.moveTo(CX - 1.1, y + 0.2);
  ctx.lineTo(CX + 1.1, y + 0.2);
  ctx.lineTo(CX, y + 1.2);
  ctx.closePath();
  ctx.fill();
  ctx.strokeStyle = OJO;
  ctx.lineWidth = 0.7;
  ctx.lineCap = 'round';
  for (const lado of [-1, 1]) {
    for (const dy of [-0.7, 1.1]) {
      ctx.beginPath();
      ctx.moveTo(CX + lado * 9.2, y + 1.9 + dy * 0.4);
      ctx.lineTo(CX + lado * 13.6, y + 1.2 + dy * 1.6);
      ctx.stroke();
    }
  }
}

/** Dibuja un wati en el origen del contexto, en unidades de celda. */
export function dibujarWati(ctx: CanvasRenderingContext2D, { cuerpo, variante, cuadro, animo = 'alegre', gato = false, saludo = 0 }: OpcionesWati): void {
  const medio = 14;
  const arriba = 15;
  const abajo = 40;
  const centro = 27.5;
  ctx.save();
  ctx.lineJoin = 'round';
  ctx.lineWidth = LW;
  ctx.strokeStyle = BORDE;
  const pie = mezclarColor(cuerpo, BORDE, 0.1);
  for (const lado of [-1, 1]) {
    ctx.beginPath();
    ctx.ellipse(CX + lado * 6, abajo + 1.3, 3.2, 2.7, 0, 0, Math.PI * 2);
    ctx.fillStyle = pie;
    ctx.fill();
    ctx.stroke();
  }
  for (const lado of [-1, 1]) {
    ctx.save();
    if (lado === 1 && saludo) {
      ctx.translate(CX + medio - 1, centro - 1);
      ctx.rotate(-saludo);
      ctx.translate(-(CX + medio - 1), -(centro - 1));
    }
    ctx.beginPath();
    ctx.ellipse(CX + lado * (medio + 0.4), centro + 1.6, 2.3, 4.7, -lado * 0.45, 0, Math.PI * 2);
    ctx.fillStyle = cuerpo;
    ctx.fill();
    ctx.stroke();
    ctx.restore();
  }
  ctx.save();
  if (gato) {
    orejasYCola(ctx, arriba, cuerpo);
  } else {
    if (variante >= CABEZAS) {
      ctx.translate(2 * CX, 0);
      ctx.scale(-1, 1);
    }
    adorno(ctx, variante % CABEZAS, arriba, cuerpo);
  }
  ctx.restore();
  const p = new Path2D();
  p.moveTo(CX, arriba);
  p.bezierCurveTo(CX + medio * 0.78, arriba, CX + medio, arriba + 6, CX + medio, centro - 1);
  p.bezierCurveTo(CX + medio, abajo - 4, CX + medio * 0.72, abajo, CX, abajo);
  p.bezierCurveTo(CX - medio * 0.72, abajo, CX - medio, abajo - 4, CX - medio, centro - 1);
  p.bezierCurveTo(CX - medio, arriba + 6, CX - medio * 0.78, arriba, CX, arriba);
  p.closePath();
  ctx.fillStyle = cuerpo;
  ctx.fill(p);
  // Sombra en la base: da volumen sin brillos.
  ctx.save();
  ctx.clip(p);
  ctx.fillStyle = mezclarColor(cuerpo, BORDE, 0.22);
  ctx.globalAlpha = 0.6;
  ctx.beginPath();
  ctx.ellipse(CX + 1.5, abajo + 1.5, medio * 1.15, 6.2, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();
  ctx.strokeStyle = BORDE;
  ctx.lineWidth = LW;
  ctx.stroke(p);
  cara(ctx, medio, arriba + 9, cuadro, animo);
  if (gato && cuadro === 0) narizYBigotes(ctx, arriba + 9);
  ctx.restore();
}

// ---------- Rasgos y animación ----------

/** Rasgos fijos de una persona: no cambian al volver a sortear la muestra. */
export function rasgosDe(clave: string): { semilla: number; variante: number; tono: number } {
  const semilla = hashTexto(clave);
  return {
    semilla,
    variante: Math.floor(mezclar(semilla, 1) * VARIANTES),
    tono: Math.floor(mezclar(semilla, 2) * TONOS),
  };
}

export interface Pose {
  /** Escala horizontal y vertical, con los pies fijos. */
  ancho: number;
  alto: number;
  cuadro: number;
  /** Giro en radianes alrededor de los pies (solo al bostezar). */
  giro: number;
}

export const QUIETO: Pose = { ancho: 1, alto: 1, cuadro: 0, giro: 0 };
const BOSTEZO = 1.9;

/**
 * Pose de un wati en el instante `t` (segundos). Respira siempre, con su propio ritmo de 3 a 4,5 s,
 * y bosteza una vez por ciclo de `cadaCuanto` segundos (el ciclo también varía por wati).
 */
export function poseDe(t: number, semilla: number, cadaCuanto: [number, number] = [40, 90]): Pose {
  const periodo = 3 + 1.5 * mezclar(semilla, 3);
  const respira = Math.sin((2 * Math.PI * t) / periodo + mezclar(semilla, 4) * 6.283);
  let alto = 1 + 0.03 * respira;
  let ancho = 1 - 0.015 * respira;
  let cuadro = 0;
  let giro = 0;
  const ciclo = cadaCuanto[0] + (cadaCuanto[1] - cadaCuanto[0]) * mezclar(semilla, 5);
  const q = (t + mezclar(semilla, 6) * ciclo) % ciclo;
  if (q < BOSTEZO) {
    const p = q / BOSTEZO;
    cuadro = p < 0.14 ? 1 : p < 0.7 ? 2 : p < 0.86 ? 3 : 1;
    const e = Math.sin(Math.PI * p);
    alto += 0.07 * e;
    ancho -= 0.035 * e;
    giro = 0.05 * e * (mezclar(semilla, 7) < 0.5 ? -1 : 1);
  }
  return { ancho, alto, cuadro, giro };
}

// ---------- Atlas ----------

export interface AtlasWati {
  lienzo: HTMLCanvasElement;
  celdaAncho: number;
  celdaAlto: number;
  /** Cuántas caras trae por wati: todas, o solo la de reposo. */
  caras: number;
}

/**
 * Hoja con todos los watis ya dibujados, para pintar cientos por cuadro con `drawImage`: una fila
 * por color y tono, una columna por adorno y cara. `alto` es el alto de cada celda en píxeles.
 * Los colores de `suaves` (por posición) llevan tonos apenas distintos: ver `tonosDe`. Con
 * `caras = 1` solo trae la cara de reposo (ocupa la cuarta parte).
 */
export function crearAtlasWati(colores: string[], alto: number, suaves: number[] = [], caras = CARAS, animos: Animo[] = []): AtlasWati {
  const escala = alto / CELDA_ALTO;
  const celdaAncho = Math.ceil(CELDA_ANCHO * escala);
  const celdaAlto = Math.ceil(alto);
  const lienzo = document.createElement('canvas');
  lienzo.width = celdaAncho * VARIANTES * caras;
  lienzo.height = celdaAlto * colores.length * TONOS;
  const ctx = lienzo.getContext('2d')!;
  colores.forEach((color, fila) => {
    tonosDe(color, suaves.includes(fila)).forEach((cuerpo, tono) => {
      for (let variante = 0; variante < VARIANTES; variante++) {
        for (let cuadro = 0; cuadro < caras; cuadro++) {
          ctx.setTransform(escala, 0, 0, escala, (variante * caras + cuadro) * celdaAncho, (fila * TONOS + tono) * celdaAlto);
          dibujarWati(ctx, { cuerpo, variante, cuadro, animo: animos[fila] });
        }
      }
    });
  });
  return { lienzo, celdaAncho, celdaAlto, caras };
}

/**
 * Un solo wati dibujado aparte, a `alto` píxeles: para los que se ven muy de cerca, donde el atlas
 * quedaría borroso. Se arma solo para los que aparecen en pantalla.
 */
export function crearSpriteWati(color: string, suave: boolean, tono: number, variante: number, cuadro: number, alto: number, animo: Animo = 'alegre'): HTMLCanvasElement {
  const escala = alto / CELDA_ALTO;
  const lienzo = document.createElement('canvas');
  lienzo.width = Math.ceil(CELDA_ANCHO * escala);
  lienzo.height = Math.ceil(alto);
  const ctx = lienzo.getContext('2d')!;
  ctx.setTransform(escala, 0, 0, escala, 0, 0);
  dibujarWati(ctx, { cuerpo: tonosDe(color, suave)[tono], variante, cuadro, animo });
  return lienzo;
}

/** Esquina de la celda de un wati en el atlas. */
export function celdaWati(atlas: AtlasWati, color: number, tono: number, variante: number, cuadro: number): [number, number] {
  return [(variante * atlas.caras + Math.min(cuadro, atlas.caras - 1)) * atlas.celdaAncho, (color * TONOS + tono) * atlas.celdaAlto];
}
