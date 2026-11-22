import { useCallback, useEffect, useLayoutEffect, useRef, useState, type ReactNode } from 'react';
import type { CasoVivo, EnVivo } from '../../vivo/useEnVivo';
import type { Bordes } from '../EscenaEnjambre';
import { BarraSuperior } from './BarraSuperior';
import type { Alturas, Tope } from './hoja';
import { HojaInferior } from './HojaInferior';
import estilos from './DisposicionMovil.module.css';

interface Props {
  fase: EnVivo['fase'];
  caso?: CasoVivo;
  /** El botón de más opciones, a la derecha de la barra. */
  menu: ReactNode;
  /** Lo que asoma de la hoja: siempre a la vista. */
  asomo: ReactNode;
  /** El resto de la hoja. */
  children: ReactNode;
  /** Lo que se asoma por el borde de arriba de la hoja (el wati, al preparar). */
  encima?: ReactNode;
  etiqueta: string;
  /** Cuánto tapan la barra y la hoja, para que el mapa ubique sus burbujas en lo que queda libre. */
  alCambiarBordes(bordes: Bordes): void;
  alCambiarTope?(tope: Tope): void;
  /** El proceso o el análisis ocupan la pantalla, o la interfaz está oculta para presentar. */
  oculta?: boolean;
}

/** Al preparar, la hoja empieza a media altura: escribir la pregunta es lo primero. Con un resultado, asoma. */
const topeInicial = (fase: EnVivo['fase']): Tope => (fase === 'preparar' ? 'mitad' : 'asomo');

/** El teléfono: barra arriba, el país al medio y la hoja abajo. Ningún texto queda encima del mapa. */
export function DisposicionMovil({ fase, caso, menu, asomo, encima, children, etiqueta, alCambiarBordes, alCambiarTope, oculta = false }: Props) {
  const barra = useRef<HTMLElement>(null);
  const [tope, setTope] = useState<Tope>(() => topeInicial(fase));
  const [arriba, setArriba] = useState(0);
  const [abajo, setAbajo] = useState(0);

  // Solo al cambiar de fase: mientras llegan respuestas, la hoja queda donde la dejó la persona.
  useEffect(() => setTope(topeInicial(fase)), [fase]);
  useEffect(() => alCambiarTope?.(tope), [tope, alCambiarTope]);

  useLayoutEffect(() => {
    const medir = () => setArriba(Math.round(barra.current?.getBoundingClientRect().bottom ?? 0));
    medir();
    const observador = new ResizeObserver(medir);
    if (barra.current) observador.observe(barra.current);
    return () => observador.disconnect();
  }, []);

  // Con un resultado el mapa se arma sobre el asomo: al subir la hoja, lo tapa sin desarmarlo.
  // Al preparar no hay burbujas: el país se encoge sobre lo que queda libre, hasta la media altura.
  const preparando = fase === 'preparar';
  const alAsentar = useCallback(
    (visible: number, a: Alturas) => setAbajo(Math.round(preparando ? Math.min(visible, a.mitad) : a.asomo)),
    [preparando],
  );

  // La franja de frases se cuelga bajo la barra, lejos de la hoja y del wati que se asoma por su borde.
  useLayoutEffect(() => {
    if (!arriba) return;
    const raiz = document.documentElement.style;
    raiz.setProperty('--alto-barra', `${arriba}px`);
    return () => void raiz.removeProperty('--alto-barra');
  }, [arriba]);

  useLayoutEffect(() => {
    if (!arriba || !abajo) return;
    alCambiarBordes({ arriba, abajo, izquierda: 0, derecha: 0 });
  }, [arriba, abajo, alCambiarBordes]);

  return (
    <div className={estilos.movil} data-oculta={oculta || undefined} inert={oculta || undefined}>
      <BarraSuperior ref={barra} caso={caso} menu={menu} />
      <HojaInferior tope={tope} alCambiar={setTope} asomo={asomo} encima={encima} etiqueta={etiqueta} arriba={arriba} alAsentar={alAsentar}>
        {children}
      </HojaInferior>
    </div>
  );
}
