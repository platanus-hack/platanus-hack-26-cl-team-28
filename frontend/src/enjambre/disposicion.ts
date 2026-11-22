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
