export interface Manejadores {
  arrastrar(dx: number, dy: number): void;
  acercar(factor: number, x: number, y: number): void;
  tocar(x: number, y: number): void;
  apuntar(x: number, y: number): void;
  salir(): void;
  restablecer(): void;
}

const UMBRAL_ARRASTRE = 5;
const PASO_TECLA = 48;
const PASO_ZOOM = 1.32;

function enLienzo(lienzo: HTMLCanvasElement, e: PointerEvent | WheelEvent): [number, number] {
  const caja = lienzo.getBoundingClientRect();
  return [e.clientX - caja.left, e.clientY - caja.top];
}

/** Conecta puntero, rueda y teclado del lienzo. Devuelve la función que lo desconecta. */
export function conectarEntrada(lienzo: HTMLCanvasElement, m: Manejadores): () => void {
  const fin = new AbortController();
  const opciones = { signal: fin.signal };
  let arrastre: { id: number; x: number; y: number; movio: boolean } | null = null;
  const local = (e: PointerEvent) => enLienzo(lienzo, e);

  lienzo.addEventListener('pointerdown', (e) => {
    if (arrastre || e.button !== 0) return;
    arrastre = { id: e.pointerId, x: e.clientX, y: e.clientY, movio: false };
    lienzo.setPointerCapture(e.pointerId);
  }, opciones);

  lienzo.addEventListener('pointermove', (e) => {
    if (arrastre?.id !== e.pointerId) {
      if (e.pointerType === 'mouse') m.apuntar(...local(e));
      return;
    }
    const dx = e.clientX - arrastre.x;
    const dy = e.clientY - arrastre.y;
    if (!arrastre.movio && Math.hypot(dx, dy) < UMBRAL_ARRASTRE) return;
    arrastre.movio = true;
    arrastre.x = e.clientX;
    arrastre.y = e.clientY;
    lienzo.dataset.arrastrando = '';
    m.arrastrar(dx, dy);
  }, opciones);

  const soltar = (e: PointerEvent) => {
    if (arrastre?.id !== e.pointerId) return;
    if (!arrastre.movio && e.type === 'pointerup') m.tocar(...local(e));
    arrastre = null;
    delete lienzo.dataset.arrastrando;
  };
  lienzo.addEventListener('pointerup', soltar, opciones);
  lienzo.addEventListener('pointercancel', soltar, opciones);
  lienzo.addEventListener('pointerleave', () => m.salir(), opciones);

  conectarRuedaYTeclado(lienzo, m, fin.signal);

  return () => fin.abort();
}

function conectarRuedaYTeclado(lienzo: HTMLCanvasElement, m: Manejadores, signal: AbortSignal): void {
  const opciones = { signal };
  lienzo.addEventListener('wheel', (e) => {
    e.preventDefault();
    m.acercar(e.deltaY < 0 ? 1.14 : 1 / 1.14, ...enLienzo(lienzo, e));
  }, { signal, passive: false });

  lienzo.addEventListener('keydown', (e) => {
    const pasos: Record<string, [number, number]> = {
      ArrowUp: [0, PASO_TECLA], ArrowDown: [0, -PASO_TECLA], ArrowLeft: [PASO_TECLA, 0], ArrowRight: [-PASO_TECLA, 0],
    };
    const centro: [number, number] = [lienzo.clientWidth / 2, lienzo.clientHeight / 2];
    if (e.key in pasos) m.arrastrar(...pasos[e.key]);
    else if (e.key === '+' || e.key === '=') m.acercar(PASO_ZOOM, ...centro);
    else if (e.key === '-') m.acercar(1 / PASO_ZOOM, ...centro);
    else if (e.key === 'Home') m.restablecer();
    else return;
    e.preventDefault();
  }, opciones);
}
