import { agrupar, factorTamano, type Agrupacion } from './agrupar';
import type { Camara } from './camara';
import type { Multitud } from './multitud';
import { celdaAtlas, CELDA_ALTO, CELDA_ANCHO, CUADROS, ESTADO, PIES_RELATIVO, type Atlas } from './personajes';

export type ModoCambio = 'inmediato' | 'cambio' | 'barrido';

const ALTO_BASE = 25;
const SALTO = 0.45;
const AVISO = 0.12;
const SIN_CAMBIO = Infinity;
/** Rapidez con que una figura crece o se encoge al agruparse. */
const RAPIDEZ_ESCALA = 9;
/** El cuerpo ocupa esta fracción de la celda: de ahí sale cuánto lugar necesita cada figura. */
const CUERPO_ANCHO = 0.62;
const CUERPO_ALTO = 0.5;

export interface OpcionesDibujo {
  ctx: CanvasRenderingContext2D;
  camara: Camara;
  chico: Atlas;
  grande: Atlas;
  ahora: number;
  dt: number;
  reducido: boolean;
  ancho: number;
  alto: number;
  apuntada: number;
  elegida: number;
  tinta: string;
  papel: string;
}

/**
 * Estado y animación de cada figura. Lo que se dibuja depende de la distancia: de lejos las
 * figuras vecinas se funden en una más grande con la postura de la mayoría del grupo.
 */
export class CapaPersonas {
  readonly estados: Uint8Array;
  private readonly pendiente: Uint8Array;
  private readonly tCambio: Float32Array;
  private readonly tSalto: Float32Array;
  private readonly tNace: Float32Array;
  private readonly fase: Float32Array;
  private readonly escala: Float32Array;
  private readonly visto: Uint8Array;
  private readonly conteo: Uint16Array;
  private readonly prioridad: Uint16Array;
  private grupos: Agrupacion | null = null;
  private clave = '';
  private finAnimacion = 0;
  barrido: { inicio: number; duracion: number } | null = null;

  constructor(
    private readonly multitud: Multitud,
    private readonly aspectos: Uint8Array,
    ahora: number,
  ) {
    const n = multitud.x.length;
    this.estados = new Uint8Array(n).fill(ESTADO.neutra);
    this.visto = new Uint8Array(n).fill(ESTADO.neutra);
    this.pendiente = new Uint8Array(n);
    this.conteo = new Uint16Array(n * 5);
    this.escala = new Float32Array(n);
    this.tCambio = new Float32Array(n).fill(SIN_CAMBIO);
    this.tSalto = new Float32Array(n).fill(-10);
    this.fase = Float32Array.from({ length: n }, (_, i) => ((i * 0.618) % 1) * 6.283);
    // Orden fijo y repartido: así los representantes no cambian de un cuadro a otro.
    this.prioridad = Uint16Array.from(Array.from({ length: n }, (_, i) => i).sort((a, b) => ((a * 0.618) % 1) - ((b * 0.618) % 1)));
    // La gente aparece como una ola de norte a sur.
    this.tNace = Float32Array.from(multitud.avance, (avance, i) => ahora + 0.25 + avance * 1.1 + ((i * 0.37) % 1) * 0.25);
    this.finAnimacion = ahora + 2.4;
  }

  activa(ahora: number): boolean {
    return ahora < this.finAnimacion;
  }

  programar(estados: Uint8Array, modo: ModoCambio, ahora: number, duracion = 2.4): void {
    const { avance: avances } = this.multitud;
    this.barrido = modo === 'barrido' ? { inicio: ahora, duracion } : null;
    let fin = ahora;
    for (let i = 0; i < estados.length; i++) {
      if (estados[i] === this.estados[i] && this.tCambio[i] === SIN_CAMBIO) continue;
      const avance = avances[i];
      const espera = modo === 'barrido' ? avance * duracion : modo === 'cambio' ? avance * 0.5 + ((i * 0.37) % 1) * 0.18 : 0;
      this.pendiente[i] = estados[i];
      this.tCambio[i] = ahora + espera;
      fin = Math.max(fin, ahora + espera + SALTO);
    }
    this.finAnimacion = Math.max(this.finAnimacion, fin + 0.2);
  }

  private aplicarCambios(ahora: number, reducido: boolean): void {
    for (let i = 0; i < this.estados.length; i++) {
      if (this.tCambio[i] === SIN_CAMBIO || (!reducido && ahora < this.tCambio[i])) continue;
      this.estados[i] = this.pendiente[i];
      this.tCambio[i] = SIN_CAMBIO;
    }
    if (this.barrido && ahora > this.barrido.inicio + this.barrido.duracion) this.barrido = null;
  }

  /** Alto en pantalla de una figura que se representa solo a sí misma. */
  private altoUnidad(camara: Camara): number {
    // En pantallas angostas el país se ve entero y las figuras se achican con él.
    const base = Math.max(11, Math.min(ALTO_BASE, camara.u * 0.95));
    return Math.min(64, base * camara.zoom ** 0.4);
  }

  /** Recalcula los grupos cuando cambia la distancia, el tamaño de pantalla o la figura elegida. */
  private reagrupar(camara: Camara, elegida: number, ahora: number): void {
    const alto = this.altoUnidad(camara);
    const clave = `${Math.round(Math.log(camara.escala) * 14)}|${Math.round(alto)}|${elegida}`;
    if (clave === this.clave && this.grupos) return;
    this.clave = clave;
    const prioridad = elegida < 0 ? this.prioridad : [elegida, ...Array.from(this.prioridad).filter((i) => i !== elegida)];
    this.grupos = agrupar({
      x: this.multitud.x,
      y: this.multitud.y,
      prioridad,
      sx: (((alto * CELDA_ANCHO) / CELDA_ALTO) * CUERPO_ANCHO) / camara.escala,
      sy: (alto * CUERPO_ALTO) / camara.escala,
    });
    this.finAnimacion = Math.max(this.finAnimacion, ahora + 0.6);
  }

  /** Postura de cada grupo: la mayoría entre sus figuras que están en la muestra. */
  private posturas(ahora: number, reducido: boolean): void {
    const { grupo, cuenta } = this.grupos!;
    this.conteo.fill(0);
    for (let i = 0; i < grupo.length; i++) this.conteo[grupo[i] * 5 + this.estados[i]] += 1;
    for (let r = 0; r < grupo.length; r++) {
      if (!cuenta[r]) continue;
      const c = this.conteo.subarray(r * 5, r * 5 + 5);
      let estado: number = ESTADO.fantasma;
      let mayor = 0;
      for (const e of [ESTADO.favor, ESTADO.contra, ESTADO.indecisa, ESTADO.neutra]) {
        if (c[e] > mayor) {
          mayor = c[e];
          estado = e;
        }
      }
      if (c[ESTADO.favor] === c[ESTADO.contra] && estado === ESTADO.favor) estado = ESTADO.indecisa;
      if (estado !== this.visto[r] && estado !== ESTADO.fantasma && !reducido && this.escala[r] > 0.5) this.tSalto[r] = ahora;
      this.visto[r] = estado;
    }
  }

  /** Tamaño en pantalla del representante `r`. */
  private tamano(camara: Camara, r: number): [number, number] {
    const alto = this.altoUnidad(camara) * this.escala[r];
    return [(alto * CELDA_ANCHO) / CELDA_ALTO, alto];
  }

  /** Cuántas figuras reúne la figura dibujada `r` (cero si no se dibuja). */
  reunidas(r: number): number {
    return this.grupos?.cuenta[r] ?? 0;
  }

  altoDe(camara: Camara, r: number): number {
    return this.tamano(camara, r)[1];
  }

  dibujar(o: OpcionesDibujo): void {
    const { ctx, camara, ahora, reducido } = o;
    this.aplicarCambios(ahora, reducido);
    this.reagrupar(camara, o.elegida, ahora);
    this.posturas(ahora, reducido);
    const { cuenta } = this.grupos!;
    const { x, y, orden } = this.multitud;
    const k = reducido ? 1 : 1 - Math.exp(-RAPIDEZ_ESCALA * o.dt);
    const unidad = this.altoUnidad(camara);
    for (let n = 0; n < orden.length; n++) {
      const i = orden[n];
      const meta = cuenta[i] && (reducido || ahora >= this.tNace[i]) ? factorTamano(cuenta[i]) : 0;
      this.escala[i] += (meta - this.escala[i]) * k;
      if (this.escala[i] < 0.04) continue;
      const [w, h] = this.tamano(camara, i);
      const [px, py] = camara.aPantalla(x[i], y[i]);
      if (px < -w || px > o.ancho + w || py < -4 || py > o.alto + h) continue;
      const salto = reducido ? 1 : (ahora - this.tSalto[i]) / SALTO;
      const sube = salto < 1 ? Math.sin(Math.PI * salto) * unidad * 0.36 : 0;
      const viva = this.visto[i] > ESTADO.neutra;
      const respira = reducido ? 0 : Math.sin(ahora * (viva ? 3.4 : 1.6) + this.fase[i]) * (viva ? 0.9 : 0.4);
      const cuadro = reducido ? 0 : Math.floor(ahora * 6 + this.fase[i]) % CUADROS;
      const atlas = h > 40 ? o.grande : o.chico;
      const [sx, sy, sw, sh] = celdaAtlas(atlas, this.aspectos[i], this.visto[i], cuadro);
      if (i === o.elegida || i === o.apuntada) this.anillo(o, px, py, w, i === o.elegida);
      ctx.drawImage(atlas.lienzo, sx, sy, sw, sh, px - w / 2, py - h * PIES_RELATIVO - sube - respira - (i === o.apuntada ? 3 : 0), w, h);
      const falta = this.tCambio[i] - ahora;
      if (this.barrido && falta > 0 && falta < AVISO) this.globo(o, px + w * 0.3, py - h * 0.8);
    }
  }

  private anillo(o: OpcionesDibujo, px: number, py: number, ancho: number, elegida: boolean): void {
    const { ctx } = o;
    ctx.beginPath();
    ctx.ellipse(px, py, ancho * 0.48, ancho * 0.17, 0, 0, Math.PI * 2);
    ctx.fillStyle = o.papel;
    ctx.fill();
    ctx.strokeStyle = o.tinta;
    ctx.lineWidth = elegida ? 2.2 : 1.2;
    ctx.stroke();
  }

  /** Globo de "está respondiendo" que aparece un instante antes de que la figura tome postura. */
  private globo(o: OpcionesDibujo, x: number, y: number): void {
    const { ctx } = o;
    ctx.beginPath();
    ctx.ellipse(x, y, 7, 4.6, 0, 0, Math.PI * 2);
    ctx.fillStyle = o.papel;
    ctx.fill();
    ctx.strokeStyle = o.tinta;
    ctx.lineWidth = 1;
    ctx.stroke();
    ctx.fillStyle = o.tinta;
    for (const dx of [-3, 0, 3]) ctx.fillRect(x + dx - 0.6, y - 0.6, 1.3, 1.3);
  }

  /** Figura dibujada bajo el puntero; gana la que está más adelante. */
  buscar(px: number, py: number, camara: Camara): number {
    if (!this.grupos) return -1;
    const { x, y, orden } = this.multitud;
    for (let k = orden.length - 1; k >= 0; k--) {
      const i = orden[k];
      if (!this.grupos.cuenta[i] || this.visto[i] === ESTADO.fantasma) continue;
      const [ancho, alto] = this.tamano(camara, i);
      const [fx, fy] = camara.aPantalla(x[i], y[i]);
      if (Math.abs(px - fx) < ancho * 0.36 && py < fy + 2 && py > fy - alto * 0.7) return i;
    }
    return -1;
  }
}
