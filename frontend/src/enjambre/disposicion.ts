/**
 * Geometría del diseño "Chile se abre": cada persona es un punto que vive dentro del país y,
 * al responder, vuela a una burbuja de su región: a la derecha si está a favor, a la
 * izquierda si está en contra. Quien está indecisa se queda en el mapa.
 */
export interface Burbuja {
  /** Centro, en píxeles. */
  x: number;
  y: number;
  r: number;
}

export interface Pedido {
  /** Altura deseada: la latitud de la región en pantalla. */
  y: number;
  r: number;
  /** Espacio horizontal de la etiqueta que sigue a la burbuja. */
  anchoTexto?: number;
  altoTexto?: number;
}

const HOLGURA = 7;
const PASO_X = 3;
const DESVIOS_Y = [0, -10, 10, -22, 22, -36, 36, -52, 52, -70, 70];

/**
 * Ubica las burbujas de un lado del país, lo más pegadas posible a él y a la altura de su
 * región, sin tocarse. `lado` es 1 (derecha) o -1 (izquierda); `borde` es la x desde donde
 * parten. Devuelve una burbuja por pedido, en el mismo orden.
 */
export function ubicarBurbujas(pedidos: Pedido[], lado: 1 | -1, borde: number, altoMinimo: number, altoMaximo: number): Burbuja[] {
  const puestas: (Burbuja & { anchoTexto: number; altoTexto: number })[] = [];
  const salida = new Array<Burbuja>(pedidos.length);
  const orden = pedidos.map((_, i) => i).sort((a, b) => pedidos[b].r - pedidos[a].r);
  for (const i of orden) {
    const { y, r, anchoTexto = 0, altoTexto = 0 } = pedidos[i];
    let mejor: Burbuja | null = null;
    for (const desvio of DESVIOS_Y) {
      const cy = Math.max(altoMinimo + r, Math.min(altoMaximo - r, y + desvio));
      let distancia = r;
      const choca = (d: number) => puestas.some((b) => {
        const cx = borde + lado * d;
        if (Math.hypot(cx - b.x, cy - b.y) < b.r + r + HOLGURA) return true;
        if (!anchoTexto && !b.anchoTexto) return false;
        const caja = (x: number, yy: number, radio: number, ancho: number, alto: number) => ({
          izq: lado === 1 ? x - radio : x - radio - ancho,
          der: lado === 1 ? x + radio + ancho : x + radio,
          sup: yy - Math.max(radio, alto / 2), inf: yy + Math.max(radio, alto / 2),
        });
        const a = caja(cx, cy, r, anchoTexto, altoTexto);
        const otra = caja(b.x, b.y, b.r, b.anchoTexto, b.altoTexto);
        return a.izq < otra.der + HOLGURA && a.der + HOLGURA > otra.izq && a.sup < otra.inf + HOLGURA && a.inf + HOLGURA > otra.sup;
      });
      while (choca(distancia)) distancia += PASO_X;
      // Se prefiere quedar cerca del país; alejarse de su latitud cuesta un poco.
      const costo = distancia + Math.abs(desvio) * 0.6;
      if (!mejor || costo < (mejor as Burbuja & { costo: number }).costo) mejor = Object.assign({ x: borde + lado * distancia, y: cy, r }, { costo });
    }
    puestas.push({ ...mejor!, anchoTexto, altoTexto });
    salida[i] = mejor!;
  }
  return salida;
}

/**
 * Apila tramos sobre un eje sin que se encimen y sin cambiar su orden: cada uno queda lo más
 * cerca posible de su centro deseado (en promedio de cuadrados) y todos dentro de [minimo, maximo].
 * `altos` es lo que ocupa cada tramo. Devuelve los centros, en el mismo orden de entrada, o null si
 * no caben ni pegados unos a otros.
 */
export function apilar(deseados: number[], altos: number[], minimo: number, maximo: number): number[] | null {
  const total = altos.reduce((suma, alto) => suma + alto, 0);
  if (total > maximo - minimo + 0.01) return null;
  const orden = deseados.map((_, i) => i).sort((a, b) => deseados[a] - deseados[b]);
  // Grupos de tramos pegados: dónde empieza cada uno, cuánto mide y la suma de los inicios que querría cada tramo.
  const grupos: { inicio: number; alto: number; suma: number; cuantos: number }[] = [];
  const ubicar = (g: (typeof grupos)[number]) => (g.inicio = Math.max(minimo, Math.min(maximo - g.alto, g.suma / g.cuantos)));
  for (const i of orden) {
    // Cada tramo querría empezar en su centro menos la mitad de su alto; dentro de un grupo, menos lo que tiene encima.
    const nuevo = { inicio: 0, alto: altos[i], suma: deseados[i] - altos[i] / 2, cuantos: 1 };
    ubicar(nuevo);
    grupos.push(nuevo);
    // Mientras se pise con el grupo de arriba, se funden y el grupo entero busca su mejor lugar.
    while (grupos.length > 1) {
      const abajo = grupos[grupos.length - 1];
      const arriba = grupos[grupos.length - 2];
      if (arriba.inicio + arriba.alto <= abajo.inicio + 0.01) break;
      grupos.pop();
      arriba.suma += abajo.suma - abajo.cuantos * arriba.alto;
      arriba.cuantos += abajo.cuantos;
      arriba.alto += abajo.alto;
      ubicar(arriba);
    }
  }
  const centros = new Array<number>(deseados.length);
  let k = 0;
  for (const g of grupos) {
    let y = g.inicio;
    for (let n = 0; n < g.cuantos; n++, k++) {
      const i = orden[k];
      centros[i] = y + altos[i] / 2;
      y += altos[i];
    }
  }
  return centros;
}

/**
 * Cuánto dice cada rótulo de región. En pantallas anchas va el nombre entero; si no caben, el nombre
 * abreviado y, como último recurso, solo la cifra (la lista por región de la hoja dice cuál es cuál).
 */
export type NivelRotulo = 'completo' | 'abreviado' | 'cifra';

export interface FilaResultado {
  /** Altura de la región en el lienzo. */
  y: number;
  /** Radio de cada burbuja con un paso dado. */
  radio(lado: 1 | -1, paso: number): number;
  /** El rótulo de cada lado en cada nivel. */
  texto(lado: 1 | -1, nivel: NivelRotulo): string;
}

export interface PedidoResultado {
  filas: FilaResultado[];
  ancho: number;
  /** Franja vertical donde pueden ir las burbujas. */
  arriba: number;
  abajo: number;
  /** Lo que la interfaz tapa a cada costado: ni burbujas ni rótulos entran ahí. */
  lateral: number;
  /** Desde dónde parten las burbujas de cada lado: el borde del país, con un poco de aire. */
  bordeIzq: number;
  bordeDer: number;
  paso: number;
  pisoPaso: number;
  altoTexto: number;
  separa: number;
  niveles: readonly NivelRotulo[];
  /** Ancho de un texto con la letra de los rótulos. */
  medir(texto: string): number;
  /** Las burbujas no pueden salir del lienzo: se apilan de norte a sur (ver `apilarLado`). */
  acotado: boolean;
  /**
   * Dónde termina el país, con su aire, entre dos alturas: en el teléfono cada fila parte de ahí y no
   * del punto más ancho del país, que está en el sur. Sin él, todas parten de `bordeIzq` y `bordeDer`.
   */
  bordeEntre?(lado: 1 | -1, desde: number, hasta: number): number;
}

export interface ResultadoDisposicion {
  nivel: NivelRotulo;
  paso: number;
  /** Burbujas de cada lado, una por fila y en el mismo orden. */
  favor: Burbuja[];
  contra: Burbuja[];
  /** Todo quedó a la vista sin encimarse. */
  cabe: boolean;
}

/**
 * Arma las dos columnas de burbujas del resultado. Por cada nivel de rótulo, del más largo al más
 * corto, achica los puntos hasta un piso; el primer nivel donde todo cabe gana. Ambos lados usan
 * el mismo nivel, para que se lean igual.
 */
export function disponerResultado(p: PedidoResultado): ResultadoDisposicion {
  const semiancho = p.ancho / 2;
  let ultimo: ResultadoDisposicion | null = null;
  for (const nivel of p.niveles) {
    const anchoDe = (lado: 1 | -1, k: number) => p.medir(p.filas[k].texto(lado, nivel));
    const anchoRotulo = Math.max(0, ...p.filas.flatMap((_, k) => [anchoDe(1, k), anchoDe(-1, k)]));
    // En espacios estrechos las columnas laterales pueden ocupar todo el ancho útil.
    // Reservar primero los nombres evita que una burbuja los empuje fuera del lienzo.
    const lateral = Math.min(p.lateral, Math.max(4, semiancho - anchoRotulo - p.separa - 8));
    const limiteBorde = Math.max(0, semiancho - lateral - anchoRotulo - p.separa - 8);
    const bordes = { 1: Math.min(p.bordeDer, semiancho + limiteBorde), [-1]: Math.max(p.bordeIzq, semiancho - limiteBorde) } as Record<1 | -1, number>;
    let paso = p.paso;
    // En el teléfono, por el nombre entero no se achican mucho los puntos: el abreviado se entiende
    // igual. Los demás niveles sí bajan hasta el piso, porque lo que suele faltar ahí es alto.
    const piso = p.acotado && nivel === 'completo' && p.niveles.length > 1 ? Math.max(p.pisoPaso, p.paso * 0.8) : p.pisoPaso;
    for (let intento = 0; intento < 60; intento++) {
      const armar = (lado: 1 | -1) => (p.acotado ? apilarLado(p, lado, bordes[lado], paso) : esparcirLado(p, lado, bordes[lado], paso, anchoDe));
      const favor = armar(1);
      const contra = armar(-1);
      const dentro = (lado: 1 | -1, puestas: Burbuja[] | null) =>
        !!puestas &&
        puestas.every((b, k) => (lado === 1 ? b.x + b.r + p.separa + anchoDe(1, k) <= p.ancho - lateral : b.x - b.r - p.separa - anchoDe(-1, k) >= lateral));
      const cabe = dentro(1, favor) && dentro(-1, contra);
      ultimo = { nivel, paso, favor: favor ?? apretarLado(p, 1, bordes[1], paso), contra: contra ?? apretarLado(p, -1, bordes[-1], paso), cabe };
      // Achicar ayuda solo hasta cierto punto: lo que choca en el centro del país son los nombres,
      // que no se achican. Más abajo de este piso los puntos dejan de verse y nada se gana.
      if (cabe || intento === 59 || paso * 0.92 < piso) break;
      paso *= 0.92;
    }
    if (ultimo!.cabe) return ultimo!;
  }
  return ultimo!;
}

/** Escritorio: cada burbuja a la altura de su región, y si choca, más lejos del país (ver `ubicarBurbujas`). */
function esparcirLado(p: PedidoResultado, lado: 1 | -1, borde: number, paso: number, anchoDe: (lado: 1 | -1, k: number) => number): Burbuja[] {
  const pedidos = p.filas.map((fila, k) => ({ y: fila.y, r: fila.radio(lado, paso), anchoTexto: p.separa + anchoDe(lado, k), altoTexto: p.altoTexto }));
  return ubicarBurbujas(pedidos, lado, borde, p.arriba, p.abajo);
}

/** Lo que ocupa en alto cada fila de un lado: su burbuja o su rótulo, y el aire hasta la siguiente. */
const altosDe = (p: PedidoResultado, lado: 1 | -1, paso: number) => p.filas.map((fila) => Math.max(2 * fila.radio(lado, paso), p.altoTexto) + HOLGURA);

/**
 * Teléfono: no hay ancho para una segunda columna, así que las filas se apilan de norte a sur, pegadas
 * al país y lo más cerca posible de su latitud. Null si no caben en el alto disponible.
 */
function apilarLado(p: PedidoResultado, lado: 1 | -1, borde: number, paso: number): Burbuja[] | null {
  const altos = altosDe(p, lado, paso);
  const centros = apilar(p.filas.map((fila) => fila.y), altos, p.arriba, p.abajo);
  if (!centros) return null;
  return p.filas.map((fila, k) => {
    const r = fila.radio(lado, paso);
    const y = centros[k];
    // Pegada al país a su altura, pero nunca más afuera que el borde que dejan libre los rótulos.
    const propio = p.bordeEntre ? p.bordeEntre(lado, y - altos[k] / 2, y + altos[k] / 2) : borde;
    const desde = lado === 1 ? Math.min(propio, borde) : Math.max(propio, borde);
    return { x: desde + lado * r, y, r };
  });
}

/** Último recurso cuando ni apiladas caben: se reparten parejas en el alto, aunque se rocen. */
function apretarLado(p: PedidoResultado, lado: 1 | -1, borde: number, paso: number): Burbuja[] {
  const orden = p.filas.map((_, k) => k).sort((a, b) => p.filas[a].y - p.filas[b].y);
  const salida = new Array<Burbuja>(p.filas.length);
  const tramo = (p.abajo - p.arriba) / Math.max(1, p.filas.length);
  orden.forEach((k, n) => {
    const r = Math.min(p.filas[k].radio(lado, paso), tramo / 2);
    salida[k] = { x: borde + lado * r, y: p.arriba + tramo * (n + 0.5), r };
  });
  return salida;
}

const ANGULO_AUREO = Math.PI * (3 - Math.sqrt(5));

/** Radio de una burbuja con `cantidad` puntos separados `paso` píxeles. */
export function radioDe(cantidad: number, paso: number): number {
  return cantidad > 0 ? paso * 0.56 * Math.sqrt(cantidad) + paso * 0.5 : 0;
}

/** Posición del punto número `k` dentro de una burbuja: espiral de girasol, pareja y sin huecos. */
export function puntoEnBurbuja(k: number, paso: number): [number, number] {
  const radio = paso * 0.56 * Math.sqrt(k + 0.5);
  const angulo = k * ANGULO_AUREO;
  return [Math.cos(angulo) * radio, Math.sin(angulo) * radio];
}
