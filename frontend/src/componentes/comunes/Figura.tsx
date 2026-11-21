import { useEffect, useRef } from 'react';
import { CELDA_ALTO, CELDA_ANCHO, dibujarFigura, ESTADO, type EstadoFigura } from '../../mapa/personajes';
import { leerTokens } from '../../mapa/tokens';
import { useCuadro } from './useCuadro';

interface Props {
  estado: keyof typeof ESTADO;
  aspecto: number;
  /** Alto en píxeles de pantalla. */
  alto?: number;
}

/** Un personaje del mapa dibujado fuera del mapa (leyenda, voces, ficha). Decorativo: el texto vecino dice lo mismo. */
export function Figura({ estado, aspecto, alto = 54 }: Props) {
  const ref = useRef<HTMLCanvasElement>(null);
  const cuadro = useCuadro();
  const ancho = (alto * CELDA_ANCHO) / CELDA_ALTO;

  useEffect(() => {
    const lienzo = ref.current;
    if (!lienzo) return;
    const dpr = Math.min(devicePixelRatio || 1, 2);
    lienzo.width = Math.round(ancho * dpr);
    lienzo.height = Math.round(alto * dpr);
    const ctx = lienzo.getContext('2d')!;
    const escala = (alto / CELDA_ALTO) * dpr;
    ctx.setTransform(escala, 0, 0, escala, 0, 0);
    dibujarFigura(ctx, { estado: ESTADO[estado] as EstadoFigura, aspecto, cuadro, tintas: leerTokens(), detalle: alto > 34 });
  }, [estado, aspecto, cuadro, alto, ancho]);

  return <canvas ref={ref} aria-hidden="true" style={{ width: ancho, height: alto, flex: 'none' }} />;
}
