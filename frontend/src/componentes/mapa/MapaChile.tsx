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
  /** Posición horizontal en pantalla, en la vista inicial, de un punto del mundo. */
  xInicial(xMundo: number): number;
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
  alAcercarse(acercado: boolean): void;
  rotular(indice: number, reunidas: number): string;
  api: Ref<MapaApi>;
  children?: ReactNode;
}

/** Envoltorio de React para la escena: el lienzo ocupa toda la página y el país se encuadra en este hueco. */
export function MapaChile({ multitud, aspectos, orden, elegida, frase, region, alElegir, alMedir, alAcercarse, rotular, api, children }: Props) {
  const hueco = useRef<HTMLDivElement>(null);
  const lienzo = useRef<HTMLCanvasElement>(null);
  const escena = useRef<EscenaMapa | null>(null);
  const retornos = useRef({ alElegir, alMedir, alAcercarse });
  const [apuntada, setApuntada] = useState<{ indice: number; x: number; y: number; reunidas: number } | null>(null);
  retornos.current = { alElegir, alMedir, alAcercarse };

  useEffect(() => {
    const caja = hueco.current!;
    const tela = lienzo.current!;
    const nueva = new EscenaMapa({
      lienzo: tela,
      multitud,
      aspectos,
      obtenerMarco: () => {
        const h = caja.getBoundingClientRect();
        const l = tela.getBoundingClientRect();
        return { x: h.left - l.left, y: h.top - l.top, w: h.width, h: h.height };
      },
      alElegir: (indice) => retornos.current.alElegir(indice),
      alApuntar: (indice, x, y, reunidas) => setApuntada(indice < 0 ? null : { indice, x, y, reunidas }),
      alAcercarse: (acercado) => retornos.current.alAcercarse(acercado),
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

  useImperativeHandle(api, () => ({ xInicial: (x) => escena.current?.xInicial(x) ?? 0 }), []);
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
