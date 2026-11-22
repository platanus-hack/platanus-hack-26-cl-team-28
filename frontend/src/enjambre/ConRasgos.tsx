import { useEffect, useId, useRef, useState, type ReactNode } from 'react';
import { POSTURA_TEXTO } from '../contenido';
import { formatear, personasAprox } from '../dominio/textos';
import type { Postura } from '../dominio/tipos';
import type { RasgoVoto } from '../vivo/analisis';
import estilos from './ConRasgos.module.css';

interface Props {
  /** Lo que distingue a esta postura; sin rasgos no hay tarjeta y el wati queda como siempre. */
  rasgos: readonly RasgoVoto[];
  postura: Postura;
  /** Qué se cuenta: agentes o personas. */
  unidad: string;
  /** A cuántas personas equivale cada uno; sin él no se dice. */
  porAgente?: number | null;
  /** Hacia dónde se abre la tarjeta, para que no se salga de la pantalla. */
  hacia?: 'derecha' | 'izquierda';
  /** Si se abre debajo (para lo que está arriba en la pantalla) en vez de encima. */
  abajo?: boolean;
  /** El wati: recibe el id de la tarjeta para `aria-describedby`. */
  children(descrito: string | undefined): ReactNode;
}

function puntos(diferencia: number): string {
  return `${diferencia} ${diferencia === 1 ? 'punto' : 'puntos'}`;
}

/**
 * Un wati con la tarjeta de las características que más distinguen a su postura: se abre al pasar
 * el mouse, con el foco del teclado o con un click (o un toque), y el click la deja abierta hasta
 * otro click, uno afuera o Escape.
 */
export function ConRasgos({ rasgos, postura, unidad, porAgente, hacia = 'derecha', abajo = false, children }: Props) {
  const id = useId();
  const caja = useRef<HTMLSpanElement>(null);
  const [abierta, setAbierta] = useState(false);
  const hay = rasgos.length > 0;

  useEffect(() => {
    if (!abierta) return;
    const afuera = (evento: PointerEvent) => {
      if (!caja.current?.contains(evento.target as Node)) setAbierta(false);
    };
    const tecla = (evento: KeyboardEvent) => {
      if (evento.key !== 'Escape') return;
      setAbierta(false);
      // Con el foco puesto la tarjeta seguiría a la vista.
      if (document.activeElement instanceof HTMLElement && caja.current?.contains(document.activeElement)) document.activeElement.blur();
    };
    document.addEventListener('pointerdown', afuera);
    document.addEventListener('keydown', tecla);
    return () => {
      document.removeEventListener('pointerdown', afuera);
      document.removeEventListener('keydown', tecla);
    };
  }, [abierta]);

  return (
    <span
      ref={caja}
      className={estilos.anfitrion}
      data-hacia={hacia}
      data-abajo={abajo || undefined}
      data-abierta={(hay && abierta) || undefined}
      onClick={() => hay && setAbierta((antes) => !antes)}
    >
      {children(hay ? id : undefined)}
      {hay && (
        <span role="tooltip" id={id} className={estilos.tarjeta} data-postura={postura}>
          {rasgos.map((rasgo) => (
            <span key={rasgo.clave} className={estilos.rasgo}>
              <span className={estilos.dimension}>{rasgo.dimension}</span>
              <strong className={estilos.grupo}>{rasgo.grupo}</strong>
              <span className={estilos.cifra}>
                <b>{rasgo.parte} %</b> {POSTURA_TEXTO[postura]} · {puntos(rasgo.parte - rasgo.base)} sobre el total
              </span>
              <span className={estilos.agentes}>
                {formatear(rasgo.agentes)} {unidad}
                {porAgente ? ` ≈ ${personasAprox(rasgo.agentes * porAgente)}` : ''}
              </span>
            </span>
          ))}
        </span>
      )}
    </span>
  );
}
