import { useEffect, useId, useRef, useState, type KeyboardEvent } from 'react';
import estilos from './Desplegable.module.css';

type Opcion = { valor: string; texto: string };
interface Props { valor: string; opciones: readonly Opcion[]; alCambiar(valor: string): void; etiqueta: string; compacto?: boolean }

export function Desplegable({ valor, opciones, alCambiar, etiqueta, compacto = false }: Props) {
  const [abierto, setAbierto] = useState(false);
  const [activo, setActivo] = useState(0);
  const [arriba, setArriba] = useState(false);
  const raiz = useRef<HTMLDivElement>(null);
  const lista = useRef<HTMLUListElement>(null);
  const busqueda = useRef('');
  const ultimo = useRef(0);
  const id = useId();
  const seleccionado = Math.max(0, opciones.findIndex((o) => o.valor === valor));
  useEffect(() => {
    if (!abierto) return;
    const cerrar = (e: PointerEvent) => { if (!raiz.current?.contains(e.target as Node)) setAbierto(false); };
    document.addEventListener('pointerdown', cerrar);
    return () => document.removeEventListener('pointerdown', cerrar);
  }, [abierto]);
  useEffect(() => { if (abierto) lista.current?.querySelector<HTMLElement>('[data-activa="true"]')?.scrollIntoView({ block: 'nearest' }); }, [activo, abierto]);
  const abrir = (indice = seleccionado) => {
    const rect = raiz.current?.getBoundingClientRect();
    if (rect) setArriba(window.innerHeight - rect.bottom < 240 && rect.top > window.innerHeight - rect.bottom);
    setActivo(indice); setAbierto(true);
  };
  const elegir = (indice: number) => { if (opciones[indice]) alCambiar(opciones[indice].valor); setAbierto(false); };
  const teclado = (e: KeyboardEvent<HTMLButtonElement>) => {
    if (e.key === 'Escape') { if (abierto) { e.preventDefault(); setAbierto(false); } return; }
    if (e.key === 'Tab') { setAbierto(false); return; }
    if (['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(e.key)) {
      e.preventDefault();
      if (!abierto) { abrir(); return; }
      setActivo((i) => e.key === 'Home' ? 0 : e.key === 'End' ? opciones.length - 1 : (i + (e.key === 'ArrowDown' ? 1 : -1) + opciones.length) % opciones.length);
    } else if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault(); if (abierto) elegir(activo); else abrir();
    } else if (e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey) {
      const ahora = Date.now(); busqueda.current = (ahora - ultimo.current > 700 ? '' : busqueda.current) + e.key.toLocaleLowerCase(); ultimo.current = ahora;
      const indice = opciones.findIndex((o) => o.texto.toLocaleLowerCase().startsWith(busqueda.current));
      if (indice >= 0) { e.preventDefault(); if (abierto) setActivo(indice); else abrir(indice); }
    }
  };
  return <div ref={raiz} className={estilos.raiz} data-compacto={compacto || undefined}>
    <button type="button" className={estilos.disparador} role="combobox" aria-label={etiqueta} aria-expanded={abierto} aria-controls={id} aria-haspopup="listbox" aria-activedescendant={abierto ? `${id}-${activo}` : undefined} onKeyDown={teclado} onClick={() => abierto ? setAbierto(false) : abrir()}>
      <span className={estilos.valor}>{opciones[seleccionado]?.texto}</span><svg aria-hidden="true" width="12" height="8" viewBox="0 0 12 8"><path d="M1 1.5l5 5 5-5" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" /></svg>
    </button>
    {abierto && <ul ref={lista} id={id} role="listbox" aria-label={etiqueta} className={estilos.lista} data-arriba={arriba || undefined}>
      {opciones.map((opcion, i) => <li key={opcion.valor} id={`${id}-${i}`} role="option" aria-selected={i === seleccionado} data-activa={i === activo || undefined} onPointerMove={() => setActivo(i)} onClick={() => elegir(i)}>{opcion.texto}{i === seleccionado && <span aria-hidden="true">✓</span>}</li>)}
    </ul>}
  </div>;
}
