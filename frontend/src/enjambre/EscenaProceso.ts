/**
 * El recorrido de una corrida, dibujado de izquierda a derecha con la misma gente del mapa:
 * de la población a la muestra, los lotes (cada uno es una llamada al modelo), las respuestas
 * de cada persona a todas las preguntas, su postura y, si hubo iteración, quién cambió.
 * Solo dibuja lo que de verdad ocurrió: los agentes no conversan entre sí, así que no hay
 * enlaces entre personas; lo único que comparten es el lote.
 */

export interface DatosProceso {
  /** Agentes que se miran (índices globales), en orden fijo. */
  agentes: number[];
  /** Acuerdo de 1 a 7 por agente; cero si todavía no responde. */
  acuerdo: Int8Array;
  notas: (number[] | undefined)[];
  /** Número del lote en que respondió cada agente (desde 1); cero si todavía no responde. */
  lote: Int32Array;
  frase: string[];
  /** La variante siguiente, para mostrar quién cambió de postura. */
  siguiente: { letra: string; acuerdo: Int8Array } | null;
  /** Un agente está redactando la variante siguiente. */
  redactando: boolean;
  embudo: { valor: number; rotulo: string }[];
  /** Nombre corto de cada pregunta, en el orden de las notas. */
  ejes: string[];
  /** Resumen de lo que costó la corrida: a la izquierda y a la derecha del botón central. */
  pie: [string, string];
  tamLote: number;
  /** Respuestas que no se preguntaron ahora: el motor las tenía guardadas de una corrida anterior. */
  deCache: number;
  describir(agente: number): string;
}

type Postura = 0 | 1 | 2; // favor, indecisa, contra
const posturaDe = (acuerdo: number): Postura => (acuerdo >= 5 ? 0 : acuerdo <= 3 ? 2 : 1);
const NOMBRES = ['A favor', 'Sin decidir', 'En contra'];

const ABRIR = 1.1;
const CERRAR = 0.55;
const DPR_MAXIMO = 2;
/**
 * Los caminos de todas las personas se pintan una vez en una capa aparte y cada cuadro la copia:
 * trazar miles de curvas translúcidas en cada cuadro es lo que trababa la vista.
 * Mientras llegan respuestas la capa se rehace a lo más cada tantos segundos.
 */
const PAUSA_CAPA = 0.5;
/** Con más caminos que estos se dibuja una parte, repartida pareja: a esa densidad se ven igual. */
const CAMINOS_MAXIMOS = 2500;
/** Mientras siguen llegando respuestas la capa va en borrador, con menos caminos; al terminar se pinta entera. */
const CAMINOS_BORRADOR = 450;
const suave = (p: number) => (p < 0.5 ? 4 * p * p * p : 1 - (-2 * p + 2) ** 3 / 2);
const azar = (i: number, sal: number) => {
  const v = Math.sin(i * 12.9898 + sal * 78.233) * 43758.5453;
  return v - Math.floor(v) - 0.5;
};
const miles = (n: number) => Math.round(n).toLocaleString('es-CL');

interface Lote {
  x: number;
  y: number;
  n: number;
  pendiente: boolean;
}

export class EscenaProceso {
  private readonly ctx: CanvasRenderingContext2D;
  private datos: DatosProceso | null = null;
  private ancho = 0;
  private alto = 0;
  private dpr = 1;
  private cuadro = 0;
  private sucio = true;
  /** Avance de la entrada: 0 en el mapa, 1 con el diagrama armado. */
  private t = 0;
  private sentido: 1 | -1 = 1;
  private marca = 0;
  private alCerrar: (() => void) | null = null;
  /** Posición actual y destino de cada agente (por su lugar en `datos.agentes`). */
  private px = new Float32Array(0);
  private py = new Float32Array(0);
  private tx = new Float32Array(0);
  private ty = new Float32Array(0);
  /** Desde dónde llega cada cuadrado al abrir: su lugar en el mapa. */
  private ox = new Float32Array(0);
  private oy = new Float32Array(0);
  private loteDe = new Int32Array(0);
  private lotes: Lote[] = [];
  private celda = 4;
  /** Alto de un lote en celdas y borde derecho del bloque de lotes: de ahí salen los caminos. */
  private filasLote = 4;
  private salida = 0;
  /** Altura donde termina cada persona en la pila de posturas. */
  private fin = new Float32Array(0);
  private orden: number[] = [0];
  private geo = { y0: 0, y1: 0, embudo: [0, 0], lotes: [0, 0], ejes: [0, 0], pila: [0, 0], otra: [0, 0], conOtra: false };
  private cuenta = [0, 0, 0];
  private sobre = -1;
  private colores = { favor: '', indecisa: '', contra: '', tinta: '', suave: '', fondo: '', linea: '', papel: '', pendiente: '', figura: '' };
  private fuente = 'sans-serif';
  /** Capa con los caminos de todos, y si quedó vieja (cambiaron los datos, el tamaño o el tema). */
  private capa: HTMLCanvasElement | null = null;
  private capaVieja = true;
  private capaPintada = -1;
  /** La capa se pintó en borrador (faltaban respuestas): hay que rehacerla entera cuando lleguen todas. */
  private capaBorrador = false;
  /** Donde se pinta la capa definitiva antes de mostrarla, y cuántas posturas lleva pintadas. */
  private capaAtras: HTMLCanvasElement | null = null;
  private pasoCapa = 0;
  private readonly reducir = matchMedia('(prefers-reduced-motion: reduce)');
  private readonly observador: ResizeObserver;
  /** Aviso al elegir a una persona: agente y dónde quedó en pantalla. */
  alElegir?: (agente: number, x: number, y: number) => void;

  constructor(
    private readonly lienzo: HTMLCanvasElement,
    private readonly origen: (agente: number) => [number, number] | null,
  ) {
    this.ctx = lienzo.getContext('2d')!;
    this.observador = new ResizeObserver(() => this.medir());
  }

  montar(): void {
    this.actualizarTema();
    this.observador.observe(this.lienzo);
    this.lienzo.addEventListener('pointermove', this.mueve);
    this.lienzo.addEventListener('pointerleave', this.sale);
    this.lienzo.addEventListener('click', this.toca);
    void document.fonts.ready.then(() => {
      this.sucio = true;
    });
    this.marca = performance.now() / 1000;
    if (this.reducir.matches) this.t = 1;
    this.cuadro = requestAnimationFrame(this.ciclo);
  }

  destruir(): void {
    cancelAnimationFrame(this.cuadro);
    this.observador.disconnect();
    this.lienzo.removeEventListener('pointermove', this.mueve);
    this.lienzo.removeEventListener('pointerleave', this.sale);
    this.lienzo.removeEventListener('click', this.toca);
  }

  /** Los cuadrados vuelven a su lugar del mapa y después se avisa para desmontar. */
  cerrar(alTerminar: () => void): void {
    this.alCerrar = alTerminar;
    this.sentido = -1;
    this.sobre = -1;
    if (this.reducir.matches) this.t = 0;
  }

  abrir(): void {
    this.alCerrar = null;
    this.sentido = 1;
  }

  actualizarTema(): void {
    const estilo = getComputedStyle(document.documentElement);
    const v = (nombre: string) => estilo.getPropertyValue(nombre).trim();
    this.colores = {
      favor: v('--favor'),
      indecisa: v('--indecisa'),
      contra: v('--contra'),
      tinta: v('--tinta'),
      suave: v('--tinta-suave'),
      fondo: v('--mar'),
      linea: v('--linea-suave'),
      papel: v('--papel'),
      pendiente: v('--punto-pendiente'),
      figura: v('--tinta-figura'),
    };
    this.fuente = v('--fuente-ui') || 'sans-serif';
    this.capaVieja = true;
    this.pasoCapa = 0;
    this.sucio = true;
  }

  fijar(datos: DatosProceso): void {
    const primera = !this.datos || this.datos.agentes !== datos.agentes;
    this.datos = datos;
    if (primera) {
      const n = datos.agentes.length;
      [this.px, this.py, this.tx, this.ty, this.ox, this.oy, this.fin] = [0, 0, 0, 0, 0, 0, 0].map(() => new Float32Array(n));
      this.loteDe = new Int32Array(n);
    }
    this.armar(primera);
  }

  private medir(): void {
    this.ancho = this.lienzo.clientWidth;
    this.alto = this.lienzo.clientHeight;
    if (!this.ancho || !this.alto) return;
    this.dpr = Math.min(devicePixelRatio || 1, DPR_MAXIMO);
    this.lienzo.width = Math.round(this.ancho * this.dpr);
    this.lienzo.height = Math.round(this.alto * this.dpr);
    this.armar(true);
  }

  /** Calcula dónde va cada cosa. `saltar`: los cuadrados quedan en su destino sin deslizarse. */
  private armar(saltar: boolean): void {
    const d = this.datos;
    if (!d || !this.ancho) return;
    const n = d.agentes.length;
    const margen = Math.max(28, this.ancho * 0.035);
    const util = this.ancho - margen * 2;
    const en = (a: number, b: number): [number, number] => [margen + util * a, margen + util * b];
    const conOtra = !!d.siguiente || d.redactando;
    this.geo = {
      y0: Math.max(150, this.alto * 0.2),
      y1: this.alto - Math.max(86, this.alto * 0.12),
      embudo: en(0, 0.115),
      lotes: en(0.16, 0.345),
      ejes: conOtra ? en(0.415, 0.72) : en(0.415, 0.83),
      pila: conOtra ? en(0.765, 0.8) : en(0.885, 0.925),
      otra: en(0.925, 0.96),
      conOtra,
    };
    const g = this.geo;

    // Preguntas: el acuerdo va al final, porque de esa respuesta sale la postura.
    const preguntas = d.agentes.reduce((maximo, a) => Math.max(maximo, d.notas[a]?.length ?? 0), 1);
    this.orden = [...Array.from({ length: preguntas - 1 }, (_, k) => k + 1), 0];

    // Lotes: los reales en el orden en que respondieron; quien falta espera en lotes provisorios.
    const porLote = new Map<number, number[]>();
    const esperando: number[] = [];
    for (let k = 0; k < n; k++) {
      const a = d.agentes[k];
      const lote = d.acuerdo[a] ? d.lote[a] : 0;
      if (!lote) esperando.push(k);
      else (porLote.get(lote) ?? porLote.set(lote, []).get(lote)!).push(k);
    }
    const tam = Math.max(4, Math.min(25, d.tamLote || 20));
    const grupos: { ks: number[]; pendiente: boolean }[] = [];
    for (const lote of [...porLote.keys()].sort((x, y) => x - y)) {
      const ks = porLote.get(lote)!;
      // Lo que llega de la caché viene en tandas grandes: se muestra en grupos del tamaño de un lote.
      for (let i = 0; i < ks.length; i += 25) grupos.push({ ks: ks.slice(i, i + (ks.length > 25 ? tam : 25)), pendiente: false });
    }
    for (let i = 0; i < esperando.length; i += tam) grupos.push({ ks: esperando.slice(i, i + tam), pendiente: true });

    const anchoLotes = g.lotes[1] - g.lotes[0];
    const altoLotes = g.y1 - g.y0;
    const COLS = 5;
    const filasLote = Math.ceil(Math.max(tam, ...grupos.map((gr) => gr.ks.length)) / COLS);
    let celda = 9;
    let columnas = 1;
    for (; celda > 1.2; celda -= 0.25) {
      columnas = Math.max(1, Math.floor((anchoLotes + celda * 1.6) / (celda * (COLS + 1.6))));
      const filas = Math.floor((altoLotes + celda * 1.6) / (celda * (filasLote + 1.6)));
      if (columnas * filas >= grupos.length) break;
    }
    this.celda = celda;
    this.filasLote = filasLote;
    const pasoX = celda * (COLS + 1.6);
    const pasoY = celda * (filasLote + 1.6);
    const filasUsadas = Math.ceil(grupos.length / columnas);
    const xLotes = g.lotes[0] + (anchoLotes - (Math.min(columnas, grupos.length) * pasoX - celda * 1.6)) / 2;
    const yLotes = g.y0 + (altoLotes - (filasUsadas * pasoY - celda * 1.6)) / 2;
    this.lotes = grupos.map((grupo, j) => {
      // Se llenan por columnas, de arriba abajo: así el orden de llegada se lee de izquierda a derecha.
      const col = Math.floor(j / Math.max(1, filasUsadas));
      const fila = j % Math.max(1, filasUsadas);
      const x = xLotes + col * pasoX;
      const y = yLotes + fila * pasoY;
      grupo.ks.forEach((k, m) => {
        this.tx[k] = x + (m % COLS) * celda + celda / 2;
        this.ty[k] = y + Math.floor(m / COLS) * celda + celda / 2;
        this.loteDe[k] = j;
      });
      return { x, y, n: grupo.ks.length, pendiente: grupo.pendiente };
    });

    this.salida = Math.max(...this.lotes.map((lote) => lote.x), g.lotes[0]) + celda * (COLS + 1.2);

    // Pila de posturas: cada persona tiene su altura dentro del tramo de su postura.
    const porPostura: number[][] = [[], [], []];
    for (let k = 0; k < n; k++) {
      const acuerdo = d.acuerdo[d.agentes[k]];
      if (acuerdo) porPostura[posturaDe(acuerdo)].push(k);
    }
    this.cuenta = porPostura.map((lista) => lista.length);
    const tramos = this.tramos(this.cuenta);
    porPostura.forEach((lista, p) => {
      lista.sort((a, b) => d.acuerdo[d.agentes[b]] - d.acuerdo[d.agentes[a]] || a - b);
      lista.forEach((k, m) => {
        this.fin[k] = tramos[p][0] + ((m + 0.5) / lista.length) * (tramos[p][1] - tramos[p][0]);
      });
    });

    for (let k = 0; k < n; k++) {
      const casa = this.origen(d.agentes[k]);
      this.ox[k] = casa ? casa[0] : this.tx[k];
      this.oy[k] = casa ? casa[1] : this.ty[k];
      if (saltar) {
        this.px[k] = this.tx[k];
        this.py[k] = this.ty[k];
      }
    }
    this.capaVieja = true;
    this.pasoCapa = 0;
    this.sucio = true;
  }

  /** Tramos verticales de la pila: a favor arriba, sin decidir al medio y en contra abajo. */
  private tramos(cuenta: number[]): [number, number][] {
    const { y0, y1 } = this.geo;
    const total = cuenta[0] + cuenta[1] + cuenta[2];
    const hueco = 5;
    const alto = y1 - y0 - hueco * 2;
    let y = y0;
    return cuenta.map((c) => {
      const h = total ? (c / total) * alto : alto / 3;
      const tramo: [number, number] = [y, y + h];
      y += h + hueco;
      return tramo;
    });
  }

  private yNota(nota: number, k: number, eje: number): number {
    const { y0, y1 } = this.geo;
    const unidad = (y1 - y0) / 6.9;
    return y0 + unidad * 0.45 + (7 - nota + azar(k, eje + 11) * 0.62) * unidad;
  }

  private xEje(e: number): number {
    const [a, b] = this.geo.ejes;
    return this.orden.length === 1 ? (a + b) / 2 : a + ((b - a) * e) / (this.orden.length - 1);
  }

  // Interacción ----------------------------------------------------------------------------

  private readonly mueve = (e: PointerEvent): void => {
    if (this.t < 1 || !this.datos) return;
    const caja = this.lienzo.getBoundingClientRect();
    const x = e.clientX - caja.left;
    const y = e.clientY - caja.top;
    let mejor = -1;
    let distancia = Math.max(9, this.celda * 1.5) ** 2;
    for (let k = 0; k < this.px.length; k++) {
      const dd = (this.px[k] - x) ** 2 + (this.py[k] - y) ** 2;
      if (dd < distancia) {
        distancia = dd;
        mejor = k;
      }
    }
    if (mejor !== this.sobre) {
      this.sobre = mejor;
      this.lienzo.style.cursor = mejor >= 0 ? 'pointer' : '';
      this.sucio = true;
    }
  };

  private readonly sale = (): void => {
    if (this.sobre < 0) return;
    this.sobre = -1;
    this.sucio = true;
  };

  private readonly toca = (): void => {
    const d = this.datos;
    if (!d || this.sobre < 0 || !d.acuerdo[d.agentes[this.sobre]]) return;
    this.alElegir?.(d.agentes[this.sobre], this.px[this.sobre], this.py[this.sobre]);
  };

  // Dibujo ---------------------------------------------------------------------------------

  private readonly ciclo = (marca: number): void => {
    this.cuadro = requestAnimationFrame(this.ciclo);
    const ahora = marca / 1000;
    const dt = Math.min(0.05, ahora - this.marca);
    this.marca = ahora;
    if (document.hidden || !this.ancho || !this.datos) return;
    const antes = this.t;
    this.t = Math.max(0, Math.min(1, this.t + (this.sentido * dt) / (this.sentido === 1 ? ABRIR : CERRAR)));
    if (this.sentido === -1 && this.t === 0 && this.alCerrar) {
      const avisar = this.alCerrar;
      this.alCerrar = null;
      avisar();
      return;
    }
    // Los cuadrados se deslizan a su lote cuando su respuesta llega.
    let moviendo = false;
    for (let k = 0; k < this.px.length; k++) {
      const dx = this.tx[k] - this.px[k];
      const dy = this.ty[k] - this.py[k];
      if (Math.abs(dx) + Math.abs(dy) < 0.3) {
        this.px[k] = this.tx[k];
        this.py[k] = this.ty[k];
        continue;
      }
      this.px[k] += dx * 0.16;
      this.py[k] += dy * 0.16;
      moviendo = true;
    }
    const esperando = this.lotes.some((lote) => lote.pendiente) || this.datos.redactando;
    if (this.capaBorrador && !this.lotes.some((lote) => lote.pendiente)) this.capaVieja = true;
    // Una capa vieja que todavía no toca rehacer mantiene el ciclo andando hasta que se rehace.
    if (!this.sucio && !moviendo && antes === this.t && !esperando && !this.capaVieja) return;
    this.sucio = false;
    this.dibujar(ahora);
  };

  private texto(texto: string, x: number, y: number, tamano: number, peso: number, color: string, alinear: CanvasTextAlign = 'left'): void {
    const { ctx } = this;
    ctx.font = `${peso} ${tamano}px ${this.fuente}`;
    ctx.fillStyle = color;
    ctx.textAlign = alinear;
    ctx.fillText(texto, x, y);
  }

  /** Parte un texto en líneas que caben en `ancho`. */
  private partir(texto: string, ancho: number, tamano: number, peso: number): string[] {
    const { ctx } = this;
    ctx.font = `${peso} ${tamano}px ${this.fuente}`;
    const lineas: string[] = [];
    let linea = '';
    for (const palabra of texto.split(' ')) {
      const prueba = linea ? `${linea} ${palabra}` : palabra;
      if (linea && ctx.measureText(prueba).width > ancho) {
        lineas.push(linea);
        linea = palabra;
      } else linea = prueba;
    }
    if (linea) lineas.push(linea);
    return lineas;
  }

  /** Texto en varias líneas dentro de un ancho. Devuelve cuántas líneas ocupó. */
  private parrafo(texto: string, x: number, y: number, ancho: number, tamano: number, peso: number, color: string): number {
    const lineas = this.partir(texto, ancho, tamano, peso);
    lineas.forEach((linea, m) => this.texto(linea, x, y + m * tamano * 1.25, tamano, peso, color));
    return lineas.length;
  }

  /** Título de una estación. Si no cabe en `ancho`, la letra se achica hasta que entre: nunca pisa al de al lado. */
  private titulo(texto: string, x: number, alinear: CanvasTextAlign = 'left', ancho = Infinity): void {
    const { ctx } = this;
    ctx.save();
    ctx.letterSpacing = '0.9px';
    let tamano = 11;
    ctx.font = `650 ${tamano}px ${this.fuente}`;
    const mide = ctx.measureText(texto.toUpperCase()).width;
    if (mide > ancho) {
      tamano = Math.max(8.5, (tamano * ancho) / mide);
      ctx.letterSpacing = '0.4px';
      ctx.font = `650 ${tamano}px ${this.fuente}`;
    }
    ctx.fillStyle = this.colores.suave;
    ctx.textAlign = alinear;
    ctx.fillText(texto.toUpperCase(), x, this.geo.y0 - 58);
    ctx.restore();
  }

  private dibujar(ahora: number): void {
    const d = this.datos!;
    const { ctx, dpr, colores, geo } = this;
    const e = suave(this.t);
    // Lo que no es gente aparece después de que los cuadrados despegan.
    // La capa de caminos se pinta antes de que haga falta: el costo cae al empezar a abrir, no a mitad del vuelo.
    if (this.capaVieja && (this.pasoCapa > 0 || this.capaPintada < 0 || ahora - this.capaPintada >= PAUSA_CAPA)) this.pintarCaminos(d, ahora);
    const visible = Math.max(0, Math.min(1, (this.t - 0.3) / 0.5));
    const trazo = Math.max(0, Math.min(1, (this.t - 0.42) / 0.58));
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, this.ancho, this.alto);
    ctx.globalAlpha = e;
    ctx.fillStyle = colores.fondo;
    ctx.fillRect(0, 0, this.ancho, this.alto);
    ctx.globalAlpha = 1;
    ctx.textBaseline = 'alphabetic';
    const n = d.agentes.length;
    const color = [colores.favor, colores.indecisa, colores.contra];
    const posX = (k: number) => this.ox[k] + (this.px[k] - this.ox[k]) * e;
    const posY = (k: number) => this.oy[k] + (this.py[k] - this.oy[k]) * e;

    if (visible > 0) {
      ctx.globalAlpha = visible;
      this.embudo(d);
      this.titulo('De Chile a la muestra', geo.embudo[0], 'left', geo.lotes[0] - geo.embudo[0] - 14);
      const grupos = this.lotes.length;
      const respondidas = this.cuenta[0] + this.cuenta[1] + this.cuenta[2];
      // Lo que el motor ya tenía de una consulta anterior no se volvió a preguntar: se dice así.
      const guardadas = !!d.deCache && d.deCache >= respondidas;
      this.titulo(guardadas ? 'Respuestas de una consulta anterior' : `La IA responde en grupos de ${d.tamLote}`, geo.lotes[0], 'left', geo.ejes[0] - geo.lotes[0] - 60);
      const explica = guardadas
        ? 'Esta pregunta ya se había hecho a estas mismas personas, así que no se volvió a consultar a la IA.'
        : `Cada cuadrado es una persona. Cada recuadro, un grupo que la IA respondió de una vez: ${miles(grupos)} ${grupos === 1 ? 'grupo' : 'grupos'} en total.`;
      this.parrafo(explica, geo.lotes[0], geo.y0 - 40, geo.lotes[1] - geo.lotes[0] + 30, 12, 500, colores.suave);
      this.titulo(this.orden.length > 1 ? `Cada línea es una persona y sus ${this.orden.length} respuestas` : 'Cada línea es una persona y su respuesta', geo.ejes[0] - 30, 'left', geo.pila[0] - geo.ejes[0] - 70);
      this.titulo('Resultado', geo.pila[1], 'right');
      // Del final del embudo a cada lote.
      ctx.strokeStyle = colores.suave;
      ctx.lineWidth = 1;
      ctx.globalAlpha = visible * 0.22;
      const salida = geo.embudo[1] + 6;
      const medio = (geo.y0 + geo.y1) / 2;
      const alturaLote = this.celda * Math.ceil(Math.max(d.tamLote, 1) / 5);
      ctx.beginPath();
      const primera = Math.min(...this.lotes.map((lote) => lote.x));
      for (const lote of this.lotes) {
        if (lote.x > primera + 1) continue; // solo la primera columna recibe la línea
        const y = lote.y + alturaLote / 2;
        ctx.moveTo(salida, medio);
        ctx.bezierCurveTo((salida + lote.x) / 2, medio, (salida + lote.x) / 2, y, lote.x - 4, y);
      }
      ctx.stroke();
      ctx.globalAlpha = 1;
    }

    // Caminos: del lote de cada persona, por sus respuestas, hasta su postura.
    if (trazo > 0) {
      ctx.save();
      ctx.beginPath();
      ctx.rect(0, 0, geo.lotes[1] + (this.ancho - geo.lotes[1]) * trazo, this.alto);
      ctx.clip();
      // Con una persona señalada los caminos de los demás se apagan.
      ctx.globalAlpha = this.sobre >= 0 ? 0.45 : 1;
      if (this.capa) ctx.drawImage(this.capa, 0, 0, this.ancho, this.alto);
      ctx.lineWidth = 1;
      const loteSobre = this.sobre >= 0 ? this.loteDe[this.sobre] : -1;
      // Con una persona señalada: su lote completo, y su camino encima.
      if (this.sobre >= 0 && d.acuerdo[d.agentes[this.sobre]]) {
        ctx.globalAlpha = 0.5;
        for (let p = 0; p < 3; p++) {
          ctx.strokeStyle = color[p];
          ctx.beginPath();
          for (let k = 0; k < n; k++) {
            const acuerdo = d.acuerdo[d.agentes[k]];
            if (k === this.sobre || this.loteDe[k] !== loteSobre || !acuerdo || posturaDe(acuerdo) !== p) continue;
            this.camino(ctx, d, k);
          }
          ctx.stroke();
        }
      }
      ctx.restore();
      ctx.globalAlpha = trazo;
      this.ejes(d);
      this.pila(d);
      if (geo.conOtra) this.iteracion(d, ahora);
      ctx.globalAlpha = 1;
    }

    // Cada lote va enmarcado: un marco es una llamada al modelo.
    if (visible > 0) {
      const borde = this.celda * 0.55;
      ctx.globalAlpha = visible;
      ctx.strokeStyle = colores.linea;
      ctx.fillStyle = colores.papel;
      ctx.lineWidth = 1;
      // Todos los marcos en un solo trazo: con miles de agentes son cientos de recuadros.
      ctx.beginPath();
      for (const lote of this.lotes) {
        ctx.roundRect(lote.x - borde, lote.y - borde, this.celda * 5 + borde * 2, this.celda * this.filasLote + borde * 2, Math.min(5, borde));
      }
      ctx.fill();
      ctx.stroke();
      ctx.globalAlpha = 1;
    }

    // La gente: un cuadrado por persona, con el color de su postura.
    const lado = Math.max(1.6, this.celda * 0.72);
    const pulso = 0.45 + 0.4 * Math.sin(ahora * 3.2);
    for (let p = -1; p < 3; p++) {
      ctx.fillStyle = p < 0 ? colores.pendiente : color[p];
      ctx.globalAlpha = p < 0 ? pulso : 1;
      for (let k = 0; k < n; k++) {
        const acuerdo = d.acuerdo[d.agentes[k]];
        if ((acuerdo ? posturaDe(acuerdo) : -1) !== p) continue;
        ctx.fillRect(posX(k) - lado / 2, posY(k) - lado / 2, lado, lado);
      }
    }
    ctx.globalAlpha = 1;

    if (this.sobre >= 0 && this.t === 1) this.senalar(d, this.sobre);
    if (visible > 0) {
      ctx.globalAlpha = visible;
      this.texto(d.pie[0], geo.embudo[0], this.alto - 30, 13, 500, colores.suave);
      this.texto(d.pie[1], this.ancho - geo.embudo[0], this.alto - 30, 13, 500, colores.suave, 'right');
      ctx.globalAlpha = 1;
    }
  }

  /**
   * Pinta en la capa los caminos de todas las personas que ya respondieron, un trazo por postura
   * (así los caminos del mismo color no se oscurecen entre sí al cruzarse).
   */
  private pintarCaminos(d: DatosProceso, ahora: number): void {
    const borrador = this.lotes.some((lote) => lote.pendiente);
    // El borrador va a un píxel por punto y de una vez: se rehace seguido y nadie lo mira de cerca
    // mientras cambia. La capa definitiva se pinta atrás, una postura por cuadro, y se muestra al
    // terminar: así ningún cuadro carga con todas las curvas.
    const escala = borrador ? 1 : this.dpr;
    const lienzo = borrador ? (this.capa ??= document.createElement('canvas')) : (this.capaAtras ??= document.createElement('canvas'));
    const primero = borrador || this.pasoCapa === 0;
    const ancho = Math.round(this.ancho * escala);
    const alto = Math.round(this.alto * escala);
    if (primero && (lienzo.width !== ancho || lienzo.height !== alto)) {
      lienzo.width = ancho;
      lienzo.height = alto;
    }
    const ctx = lienzo.getContext('2d')!;
    ctx.setTransform(escala, 0, 0, escala, 0, 0);
    if (primero) ctx.clearRect(0, 0, this.ancho, this.alto);
    const n = d.agentes.length;
    const respondidas = this.cuenta[0] + this.cuenta[1] + this.cuenta[2];
    const paso = Math.max(1, Math.ceil(respondidas / (borrador ? CAMINOS_BORRADOR : CAMINOS_MAXIMOS)));
    const dibujados = Math.max(1, respondidas / paso);
    const color = [this.colores.favor, this.colores.indecisa, this.colores.contra];
    ctx.lineWidth = 1;
    ctx.globalAlpha = Math.max(0.045, Math.min(0.4, 55 / dibujados));
    const desde = borrador ? 0 : this.pasoCapa;
    const hasta = borrador ? 3 : this.pasoCapa + 1;
    for (let p = desde; p < hasta; p++) {
      ctx.strokeStyle = color[p];
      ctx.beginPath();
      let visto = 0;
      for (let k = 0; k < n; k++) {
        const acuerdo = d.acuerdo[d.agentes[k]];
        if (!acuerdo || posturaDe(acuerdo) !== p) continue;
        if (visto++ % paso === 0) this.camino(ctx, d, k);
      }
      ctx.stroke();
    }
    if (!borrador) {
      this.pasoCapa += 1;
      // Faltan posturas: la capa sigue vieja y el próximo cuadro pinta la siguiente.
      if (this.pasoCapa < 3) return;
      [this.capa, this.capaAtras] = [this.capaAtras, this.capa];
    }
    this.pasoCapa = 0;
    this.capaVieja = false;
    this.capaBorrador = borrador;
    this.capaPintada = ahora;
  }

  /** Agrega al trazo en curso de `ctx` el camino de una persona. */
  private camino(ctx: CanvasRenderingContext2D, d: DatosProceso, k: number): void {
    const a = d.agentes[k];
    const notas = d.notas[a];
    // Los caminos salen del borde del bloque de lotes, a la altura de cada persona: así no cruzan
    // por encima de los otros lotes y cada grupo se lee limpio.
    let x = this.salida;
    // Parten de donde queda la persona en su lote (no de donde va mientras se desliza): la capa no depende del cuadro.
    let y = this.ty[k];
    ctx.moveTo(x, y);
    this.orden.forEach((pregunta, e) => {
      const nota = pregunta === 0 ? d.acuerdo[a] : (notas?.[pregunta] ?? d.acuerdo[a]);
      const nx = this.xEje(e);
      const ny = this.yNota(nota, k, e);
      const medio = (x + nx) / 2;
      ctx.bezierCurveTo(medio, y, medio, ny, nx, ny);
      x = nx;
      y = ny;
    });
    const fx = this.geo.pila[0];
    const medio = (x + fx) / 2;
    ctx.bezierCurveTo(medio, y, medio, this.fin[k], fx, this.fin[k]);
  }

  private embudo(d: DatosProceso): void {
    const { ctx, colores, geo } = this;
    const niveles = d.embudo.filter((nivel) => nivel.valor > 0);
    if (!niveles.length) return;
    const [x0, x1] = geo.embudo;
    const ancho = x1 - x0;
    const hueco = 10;
    const alto = (geo.y1 - geo.y0 - hueco * (niveles.length - 1)) / niveles.length;
    const mayor = Math.log10(niveles[0].valor + 1);
    // El ancho baja con el orden de magnitud, pero nunca tanto que el texto no quepa dentro.
    const anchoDe = (valor: number) => ancho * Math.max(0.72, Math.log10(valor + 1) / mayor);
    niveles.forEach((nivel, k) => {
      const y = geo.y0 + k * (alto + hueco);
      const arriba = anchoDe(nivel.valor);
      const abajo = k + 1 < niveles.length ? anchoDe(niveles[k + 1].valor) : arriba;
      ctx.beginPath();
      ctx.moveTo(x0, y);
      ctx.lineTo(x0 + arriba, y);
      ctx.lineTo(x0 + abajo, y + alto);
      ctx.lineTo(x0, y + alto);
      ctx.closePath();
      ctx.fillStyle = colores.papel;
      ctx.fill();
      ctx.strokeStyle = colores.linea;
      ctx.lineWidth = 1;
      ctx.stroke();
      const cifra = nivel.valor >= 1e6 ? `${(nivel.valor / 1e6).toLocaleString('es-CL', { maximumFractionDigits: 1 })} M` : miles(nivel.valor);
      const dentro = Math.min(arriba, abajo) - 22;
      const rotulo = this.partir(nivel.rotulo, dentro, 12, 500).slice(0, 3);
      const tamano = Math.max(15, Math.min(24, alto * 0.24));
      const bloque = tamano + rotulo.length * 15;
      const base = y + (alto - bloque) / 2 + tamano * 0.85;
      this.texto(cifra, x0 + 11, base, tamano, 650, colores.tinta);
      rotulo.forEach((linea, m) => this.texto(linea, x0 + 11, base + 17 + m * 15, 12, 500, colores.suave));
    });
  }

  private ejes(d: DatosProceso): void {
    const { ctx, colores, geo } = this;
    const n = d.agentes.length;
    const unidad = (geo.y1 - geo.y0) / 6.9;
    const yDe = (nota: number) => geo.y0 + unidad * 0.45 + (7 - nota) * unidad;
    this.orden.forEach((pregunta, e) => {
      const x = this.xEje(e);
      const final = pregunta === 0;
      if (final) {
        // En el acuerdo se ve el corte: 5 a 7 a favor, 4 sin decidir, 1 a 3 en contra.
        const cortes: [number, number, string][] = [[7.42, 4.5, colores.favor], [4.5, 3.5, colores.indecisa], [3.5, 0.58, colores.contra]];
        ctx.lineWidth = 3;
        for (const [desde, hasta, tono] of cortes) {
          ctx.strokeStyle = tono;
          ctx.beginPath();
          ctx.moveTo(x, yDe(desde) + 1.5);
          ctx.lineTo(x, yDe(hasta) - 1.5);
          ctx.stroke();
        }
      } else {
        ctx.strokeStyle = colores.suave;
        ctx.globalAlpha *= 0.55;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(x, yDe(7.42));
        ctx.lineTo(x, yDe(0.58));
        ctx.stroke();
        ctx.globalAlpha /= 0.55;
      }
      // Nombre de la pregunta, en dos líneas si hace falta.
      const nombre = d.ejes[pregunta] ?? `Pregunta ${pregunta + 1}`;
      const corte = nombre.indexOf(' ', Math.floor(nombre.length / 2) - 2);
      const lineas = nombre.length > 12 && corte > 0 ? [nombre.slice(0, corte), nombre.slice(corte + 1)] : [nombre];
      lineas.forEach((linea, m) => this.texto(linea, x, geo.y0 - 26 + (m - lineas.length + 1) * 14 + 8, 12, final ? 650 : 500, final ? colores.tinta : colores.suave, 'center'));
      // Promedio de la pregunta.
      let suma = 0;
      let cuantas = 0;
      for (let k = 0; k < n; k++) {
        const a = d.agentes[k];
        if (!d.acuerdo[a]) continue;
        suma += pregunta === 0 ? d.acuerdo[a] : (d.notas[a]?.[pregunta] ?? d.acuerdo[a]);
        cuantas += 1;
      }
      if (cuantas) {
        const media = suma / cuantas;
        const y = yDe(media);
        ctx.fillStyle = colores.tinta;
        ctx.beginPath();
        ctx.moveTo(x, y - 5);
        ctx.lineTo(x + 5, y);
        ctx.lineTo(x, y + 5);
        ctx.lineTo(x - 5, y);
        ctx.closePath();
        ctx.fill();
        // La cifra va junto a su marca, con un borde del color del fondo para leerse sobre los caminos.
        const cifra = media.toLocaleString('es-CL', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
        ctx.font = `650 13px ${this.fuente}`;
        ctx.textAlign = 'left';
        ctx.lineJoin = 'round';
        ctx.lineWidth = 4;
        ctx.strokeStyle = colores.fondo;
        ctx.strokeText(cifra, x + 10, y + 4.5);
        this.texto(cifra, x + 10, y + 4.5, 13, 650, colores.tinta);
      }
    });
    // Escala a la izquierda del primer eje.
    const x = this.xEje(0) - 12;
    // La escala, dicha en palabras: 7 es totalmente de acuerdo y 1 es nada. El rombo marca el promedio.
    const escala: [number, string][] = [[7, '7 · totalmente'], [4, '4'], [1, '1 · nada']];
    ctx.lineJoin = 'round';
    ctx.lineWidth = 4;
    ctx.strokeStyle = colores.fondo;
    ctx.font = `500 11px ${this.fuente}`;
    ctx.textAlign = 'right';
    for (const [nota, rotulo] of escala) {
      ctx.strokeText(rotulo, x, yDe(nota) + 4);
      this.texto(rotulo, x, yDe(nota) + 4, 11, 500, colores.tinta, 'right');
    }
    this.texto('◆ promedio', x, geo.y1 + 20, 11, 500, colores.suave, 'right');
  }

  private pila(d: DatosProceso, cuenta = this.cuenta, rango = this.geo.pila, etiquetas: 'dentro' | 'derecha' = this.geo.conOtra ? 'dentro' : 'derecha'): void {
    const { ctx, colores } = this;
    const color = [colores.favor, colores.indecisa, colores.contra];
    const total = cuenta[0] + cuenta[1] + cuenta[2];
    if (!total) return;
    const tramos = this.tramos(cuenta);
    tramos.forEach(([a, b], p) => {
      if (!cuenta[p]) return;
      ctx.fillStyle = color[p];
      ctx.fillRect(rango[0], a, rango[1] - rango[0], Math.max(1, b - a));
      const pct = `${Math.round((cuenta[p] / total) * 100)} %`;
      if (etiquetas === 'derecha') {
        const y = Math.max(a + 22, Math.min(b - 4, (a + b) / 2 + 2));
        this.texto(pct, rango[1] + 12, y, 22, 650, colores.tinta);
        this.texto(`${NOMBRES[p]} · ${miles(cuenta[p])}`, rango[1] + 12, y + 17, 12, 500, colores.suave);
      } else if (b - a > 20) {
        this.texto(pct, (rango[0] + rango[1]) / 2, (a + b) / 2 + 4, 12, 650, colores.figura, 'center');
      }
    });
    void d;
  }

  /** Quién cambió de postura entre esta variante y la siguiente: nueve cintas, de pila a pila. */
  private iteracion(d: DatosProceso, ahora: number): void {
    const { ctx, colores, geo } = this;
    const x0 = geo.pila[1];
    const x1 = geo.otra[0];
    if (!d.siguiente) {
      ctx.globalAlpha *= 0.55 + 0.45 * Math.sin(ahora * 3);
      this.texto('Un agente redacta', (x0 + this.ancho) / 2, (geo.y0 + geo.y1) / 2 - 6, 14, 600, colores.tinta, 'center');
      this.texto('una variante nueva', (x0 + this.ancho) / 2, (geo.y0 + geo.y1) / 2 + 12, 14, 600, colores.tinta, 'center');
      return;
    }
    const color = [colores.favor, colores.indecisa, colores.contra];
    const flujo = [0, 1, 2].map(() => [0, 0, 0]);
    const despues = [0, 0, 0];
    let cambiaron = 0;
    for (const a of d.agentes) {
      const antes = d.acuerdo[a];
      const luego = d.siguiente.acuerdo[a];
      if (!antes || !luego) continue;
      flujo[posturaDe(antes)][posturaDe(luego)] += 1;
      despues[posturaDe(luego)] += 1;
      if (posturaDe(antes) !== posturaDe(luego)) cambiaron += 1;
    }
    const antes = flujo.map((fila) => fila[0] + fila[1] + fila[2]);
    const tramosA = this.tramos(antes);
    const tramosB = this.tramos(despues);
    const usadoA = [0, 0, 0];
    const usadoB = [0, 0, 0];
    const base = ctx.globalAlpha;
    for (let i = 0; i < 3; i++) {
      for (let j = 0; j < 3; j++) {
        const c = flujo[i][j];
        if (!c) continue;
        const altoA = (c / antes[i]) * (tramosA[i][1] - tramosA[i][0]);
        const altoB = (c / despues[j]) * (tramosB[j][1] - tramosB[j][0]);
        const ya = tramosA[i][0] + usadoA[i];
        const yb = tramosB[j][0] + usadoB[j];
        usadoA[i] += altoA;
        usadoB[j] += altoB;
        const medio = (x0 + x1) / 2;
        const degradado = ctx.createLinearGradient(x0, 0, x1, 0);
        degradado.addColorStop(0, color[i]);
        degradado.addColorStop(1, color[j]);
        ctx.fillStyle = degradado;
        // Quien se queda donde estaba va tenue; quien cambia, marcado.
        ctx.globalAlpha = base * (i === j ? 0.2 : 0.62);
        ctx.beginPath();
        ctx.moveTo(x0, ya);
        ctx.bezierCurveTo(medio, ya, medio, yb, x1, yb);
        ctx.lineTo(x1, yb + altoB);
        ctx.bezierCurveTo(medio, yb + altoB, medio, ya + altoA, x0, ya + altoA);
        ctx.closePath();
        ctx.fill();
      }
    }
    ctx.globalAlpha = base;
    this.pila(d, despues, geo.otra, 'dentro');
    this.titulo(`Variante ${d.siguiente.letra}`, geo.otra[1], 'right');
    const total = despues[0] + despues[1] + despues[2];
    if (total) {
      this.texto(`${miles(cambiaron)} de ${miles(total)}`, (x0 + x1) / 2, geo.y1 + 20, 13, 650, colores.tinta, 'center');
      this.texto('cambiaron de postura', (x0 + x1) / 2, geo.y1 + 36, 11, 500, colores.suave, 'center');
    }
  }

  /** La persona bajo el cursor: su camino, sus notas y quién es. */
  private senalar(d: DatosProceso, k: number): void {
    const { ctx, colores } = this;
    const a = d.agentes[k];
    const acuerdo = d.acuerdo[a];
    const tono = acuerdo ? [colores.favor, colores.indecisa, colores.contra][posturaDe(acuerdo)] : colores.suave;
    const lado = Math.max(7, this.celda * 1.3);
    if (acuerdo) {
      ctx.strokeStyle = tono;
      ctx.lineWidth = 2.5;
      ctx.beginPath();
      ctx.moveTo(this.px[k], this.py[k]);
      ctx.lineTo(this.salida, this.py[k]);
      this.camino(ctx, d, k);
      ctx.stroke();
      this.orden.forEach((pregunta, e) => {
        const nota = pregunta === 0 ? acuerdo : (d.notas[a]?.[pregunta] ?? acuerdo);
        const x = this.xEje(e);
        const y = this.yNota(nota, k, e);
        ctx.fillStyle = tono;
        ctx.beginPath();
        ctx.arc(x, y, 10, 0, Math.PI * 2);
        ctx.fill();
        this.texto(String(nota), x, y + 4.5, 12, 700, colores.figura, 'center');
      });
    }
    ctx.strokeStyle = colores.tinta;
    ctx.lineWidth = 1.5;
    ctx.strokeRect(this.px[k] - lado / 2, this.py[k] - lado / 2, lado, lado);
    // Quién es, sobre su cuadrado.
    const lineas = [d.describir(a)];
    const frase = d.frase[a];
    if (frase) lineas.push(`“${frase.length > 70 ? `${frase.slice(0, 68)}…` : frase}”`);
    else if (!acuerdo) lineas.push('Todavía no responde');
    ctx.font = `600 13px ${this.fuente}`;
    const ancho = Math.max(...lineas.map((linea) => ctx.measureText(linea).width)) + 24;
    const alto = 14 + lineas.length * 18;
    const x = Math.max(8, Math.min(this.ancho - ancho - 8, this.px[k] - ancho / 2));
    const y = this.py[k] - lado - alto - 4 < 8 ? this.py[k] + lado + 6 : this.py[k] - lado - alto - 4;
    ctx.fillStyle = colores.papel;
    ctx.strokeStyle = colores.linea;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.roundRect(x, y, ancho, alto, 6);
    ctx.fill();
    ctx.stroke();
    lineas.forEach((linea, m) => this.texto(linea, x + 12, y + 21 + m * 18, 13, m ? 500 : 650, m ? colores.suave : colores.tinta));
  }
}
