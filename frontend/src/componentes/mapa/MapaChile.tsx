import { useEffect, useImperativeHandle, useRef, useState, type ReactNode, type Ref } from 'react';
import { MAPA } from '../../contenido';
import type { ModoCambio } from '../../mapa/capaPersonas';
import { EscenaMapa } from '../../mapa/EscenaMapa';
import type { Multitud } from '../../mapa/multitud';
import { ControlesMapa } from './ControlesMapa';
import estilos from './MapaChile.module.css';

export interface OrdenMapa {
  estados: Uint8Array;
  modo: ModoCambio;
  duracion?: number;
  etiqueta?: string;
}

export interface MapaApi {
  /** Posición vertical dentro del mapa, en la vista inicial, de un punto del mundo. */
  yInicial(yMundo: number): number;
  /** Alto del mapa en pantalla. */
  alto(): number;
}

interface Props {
  multitud: Multitud;
  aspectos: Uint8Array;
  orden: OrdenMapa;
  elegida: number;
  /** Frase que la persona elegida dice en un globo sobre el mapa. */
  frase: string;
  region: number;
  alElegir(indice: number): void;
  alMedir(): void;
  rotular(indice: number, reunidas: number): string;
  api: Ref<MapaApi>;
  children?: ReactNode;
}

/** Envoltorio de React para la escena del mapa. */
export function MapaChile({ multitud, aspectos, orden, elegida, frase, region, alElegir, alMedir, rotular, api, children }: Props) {
  const hueco = useRef<HTMLDivElement>(null);
  const lienzo = useRef<HTMLCanvasElement>(null);
  const escena = useRef<EscenaMapa | null>(null);
  const retornos = useRef({ alElegir, alMedir });
  const [apuntada, setApuntada] = useState<{ indice: number; x: number; y: number; reunidas: number } | null>(null);
  retornos.current = { alElegir, alMedir };

  useEffect(() => {
    const caja = hueco.current!;
    const tela = lienzo.current!;
    const nueva = new EscenaMapa({
      lienzo: tela,
      multitud,
      aspectos,
      obtenerMarco: () => {
        // El país se encuadra en el mapa dejando libre la columna de la franja de regiones.
        const reserva = parseFloat(getComputedStyle(caja).getPropertyValue('--reserva-franja')) || 0;
        return { x: 0, y: 0, w: tela.clientWidth - reserva, h: tela.clientHeight };
      },
      alElegir: (indice) => retornos.current.alElegir(indice),
      alApuntar: (indice, x, y, reunidas) => setApuntada(indice < 0 ? null : { indice, x, y, reunidas }),
    });
    nueva.montar();
    escena.current = nueva;
    const observador = new ResizeObserver(() => {
      nueva.redimensionar();
      retornos.current.alMedir();
    });
    observador.observe(caja);
    return () => {
      observador.disconnect();
      nueva.destruir();
      escena.current = null;
    };
  }, [multitud, aspectos]);

  useImperativeHandle(api, () => ({ yInicial: (y) => escena.current?.yInicial(y) ?? 0, alto: () => hueco.current?.clientHeight ?? 0 }), []);
  useEffect(() => escena.current?.fijarEstados(orden.estados, orden.modo, orden.duracion, orden.etiqueta), [orden]);
  useEffect(() => escena.current?.elegir(elegida, frase), [elegida, frase]);
  useEffect(() => escena.current?.enfocarRegion(region), [region]);

  return (
    <div className={estilos.hueco} ref={hueco}>
      <div className={estilos.escena}>
        <canvas ref={lienzo} className={estilos.lienzo} tabIndex={0} role="img" aria-label={MAPA.descripcion} />
        {apuntada && (
          <p className={estilos.rotulo} style={{ translate: `${apuntada.x + 14}px ${apuntada.y - 34}px` }}>
            {rotular(apuntada.indice, apuntada.reunidas)}
          </p>
        )}
      </div>
      {children}
      <ControlesMapa
        alAcercar={() => escena.current?.acercar(1.5)}
        alAlejar={() => escena.current?.acercar(1 / 1.5)}
        alRestablecer={() => escena.current?.restablecer()}
      />
    </div>
  );
}
