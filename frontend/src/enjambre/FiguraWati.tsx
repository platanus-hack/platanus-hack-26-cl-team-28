import { useEffect, useRef } from 'react';
import { CELDA_ALTO, CELDA_ANCHO, dibujarWati, PIES_RELATIVO, poseDe, QUIETO, tonosDe, type Animo } from './wati';

/** Color de cuerpo de cada estado, el mismo token que usan los puntos del mapa. */
const TOKEN = {
  neutra: '--punto-neutro',
  favor: '--favor',
  contra: '--contra',
  indecisa: '--indecisa',
  fantasma: '--punto-pendiente',
} as const;

/** Lo que crece al respirar o bostezar: se deja ese aire arriba para que no se corte. */
const HOLGURA = 1.12;

interface Props {
  estado: keyof typeof TOKEN;
  rasgos: { semilla: number; variante: number; tono: number };
  /** Alto en píxeles de pantalla. */
  alto?: number;
  animada?: boolean;
  animo?: Animo;
  /** Disfraz de mono con una banana. */
  mono?: boolean;
  saludo?: number;
}

/** Un wati decorativo fuera del mapa. */
export function FiguraWati({ estado, animo, rasgos, alto = 54, animada = true, mono = false, saludo = 0 }: Props) {
  const ref = useRef<HTMLCanvasElement>(null);
  const ancho = Math.round((alto * CELDA_ANCHO) / CELDA_ALTO);
  const { semilla, variante, tono } = rasgos;

  useEffect(() => {
    const lienzo = ref.current;
    if (!lienzo) return;
    const dpr = Math.min(devicePixelRatio || 1, 2);
    lienzo.width = Math.round(ancho * dpr);
    lienzo.height = Math.round(alto * dpr);
    const ctx = lienzo.getContext('2d')!;
    const base = getComputedStyle(document.documentElement).getPropertyValue(TOKEN[estado]).trim();
    const cuerpo = tonosDe(base, estado === 'neutra' || estado === 'fantasma')[tono];
    const escala = (alto / HOLGURA / CELDA_ALTO) * dpr;
    const pintar = (t: number) => {
      const pose = t < 0 ? QUIETO : poseDe(t, semilla, [25, 50]);
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.clearRect(0, 0, lienzo.width, lienzo.height);
      // Pies abajo al centro; desde ahí respira y se ladea.
      ctx.translate(lienzo.width / 2, lienzo.height - 1);
      ctx.rotate(pose.giro);
      ctx.scale(escala * pose.ancho, escala * pose.alto);
      ctx.translate(-CELDA_ANCHO / 2, -CELDA_ALTO * PIES_RELATIVO);
      const transcurrido = t * 1000 - saludo;
      const gesto = saludo && transcurrido >= 0 && transcurrido < 1600
        ? Math.sin(Math.PI * transcurrido / 1600) * (1.5 + 0.35 * Math.sin(transcurrido / 100)) : 0;
      dibujarWati(ctx, { cuerpo, variante, cuadro: pose.cuadro, animo: animo ?? (estado === 'contra' ? 'triste' : estado === 'indecisa' ? 'seria' : 'alegre'), mono, saludo: gesto });
    };
    if (!animada || matchMedia('(prefers-reduced-motion: reduce)').matches) {
      pintar(-1);
      return;
    }
    let cuadro = 0;
    let ultimo = 0;
    const ciclo = (marca: number) => {
      cuadro = requestAnimationFrame(ciclo);
      // Respirar se ve igual a 30 cuadros por segundo.
      if (marca - ultimo < 30 || document.hidden) return;
      ultimo = marca;
      pintar(marca / 1000);
    };
    cuadro = requestAnimationFrame(ciclo);
    return () => cancelAnimationFrame(cuadro);
  }, [estado, animo, semilla, variante, tono, alto, ancho, animada, mono, saludo]);

  return <canvas ref={ref} aria-hidden="true" style={{ width: ancho, height: alto, flex: 'none' }} />;
}
