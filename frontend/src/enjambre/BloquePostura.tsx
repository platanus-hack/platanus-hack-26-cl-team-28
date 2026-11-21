import { Figura } from '../componentes/comunes/Figura';
import { POSTURA_TEXTO } from '../contenido';
import { formatear } from '../dominio/textos';
import estilos from './BloquePostura.module.css';
import { useConteo } from './useConteo';

interface Props {
  postura: 'favor' | 'contra';
  porcentaje: number;
  personas: number;
  aspecto: number;
}

/** La cifra de un lado del país: la criatura de esa postura crece con su porcentaje. */
export function BloquePostura({ postura, porcentaje, personas, aspecto }: Props) {
  const contado = useConteo(porcentaje);
  const alto = Math.round(64 + contado * 1.5);
  return (
    <section className={estilos.bloque} data-postura={postura} aria-label={`${porcentaje} % ${POSTURA_TEXTO[postura]}`}>
      <Figura estado={postura} aspecto={aspecto} alto={alto} />
      <p className={estilos.cifra} aria-hidden="true">
        {Math.round(contado)}
        <span>%</span>
      </p>
      <p className={estilos.nombre}>{POSTURA_TEXTO[postura]}</p>
      <p className={estilos.personas}>{formatear(personas)} personas</p>
    </section>
  );
}
