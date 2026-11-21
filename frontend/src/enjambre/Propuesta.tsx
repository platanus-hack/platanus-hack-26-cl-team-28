import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { PopupFlotante } from '../componentes/comunes/Popup';
import estilos from './Propuesta.module.css';

interface Props {
  letra: string;
  /** Lo que se muestra en grande; se corta a unas pocas líneas. */
  titulo: string;
  /** El texto completo que leyeron los agentes. */
  texto: string;
}

/** El signo de porcentaje no se separa de su número al cortar la línea. */
const sinCorte = (texto: string) => texto.replace(/(\d) %/g, '$1 %');

/**
 * El título de la variante. Cuando no cabe entero (o los agentes leyeron un texto más largo que
 * el título), se puede leer completo: al pasar el cursor, con el teclado o con un toque se abre
 * una hoja con la propuesta tal como se preguntó.
 */
export function Propuesta({ letra, titulo, texto }: Props) {
  const caja = useRef<HTMLDivElement>(null);
  const linea = useRef<HTMLQuoteElement>(null);
  const [cortado, setCortado] = useState(false);
  const [abierta, setAbierta] = useState(false);
  const [fija, setFija] = useState(false);
  const [lugar, setLugar] = useState({ x: 0, y: 0, ancho: 0 });
  const espera = useRef(0);
  const completo = texto && texto !== titulo ? texto : titulo;
  const hayMas = cortado || completo !== titulo;

  // ¿El título quedó cortado? Se vuelve a medir si cambia el texto o el tamaño de la ventana.
  useLayoutEffect(() => {
    const medir = () => linea.current && setCortado(linea.current.scrollHeight > linea.current.clientHeight + 1);
    medir();
    const observador = new ResizeObserver(medir);
    if (linea.current) observador.observe(linea.current);
    return () => observador.disconnect();
  }, [titulo]);

  useEffect(() => {
    setAbierta(false);
    setFija(false);
  }, [titulo, texto]);

  const abrir = () => {
    window.clearTimeout(espera.current);
    const r = caja.current?.getBoundingClientRect();
    if (r) setLugar({ x: r.left, y: r.top, ancho: r.width });
    setAbierta(true);
  };
  const cerrarLuego = () => {
    window.clearTimeout(espera.current);
    if (!fija) espera.current = window.setTimeout(() => setAbierta(false), 160);
  };

  useEffect(() => {
    if (!abierta) return;
    const tecla = (e: KeyboardEvent) => {
      if (e.key !== 'Escape') return;
      setAbierta(false);
      setFija(false);
    };
    const fuera = (e: PointerEvent) => {
      if (caja.current?.contains(e.target as Node)) return;
      setAbierta(false);
      setFija(false);
    };
    window.addEventListener('keydown', tecla);
    window.addEventListener('pointerdown', fuera);
    return () => {
      window.removeEventListener('keydown', tecla);
      window.removeEventListener('pointerdown', fuera);
    };
  }, [abierta]);
  useEffect(() => () => window.clearTimeout(espera.current), []);

  return (
    <div ref={caja} className={estilos.propuesta} onPointerEnter={(e) => hayMas && e.pointerType === 'mouse' && abrir()} onPointerLeave={cerrarLuego}>
      <q ref={linea} className={estilos.titulo}>
        {sinCorte(titulo)}
      </q>
      {hayMas && (
        <button
          type="button"
          className={estilos.ver}
          aria-expanded={abierta}
          onClick={() => {
            if (abierta && fija) {
              setAbierta(false);
              setFija(false);
            } else {
              abrir();
              setFija(true);
            }
          }}
        >
          Leer completa
        </button>
      )}
      {hayMas && (
        <PopupFlotante abierto={abierta} className={estilos.hoja} role="dialog" aria-label={`Variante ${letra}, propuesta completa`} style={{ left: lugar.x, top: lugar.y, minWidth: lugar.ancho }}>
          <p className={estilos.rotulo}>Variante {letra} · lo que leyeron los agentes</p>
          <p className={estilos.texto}>{sinCorte(completo)}</p>
        </PopupFlotante>
      )}
    </div>
  );
}
