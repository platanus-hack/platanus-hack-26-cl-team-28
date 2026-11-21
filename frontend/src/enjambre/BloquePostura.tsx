import { POSTURA_TEXTO } from '../contenido';
import { formatear } from '../dominio/textos';
import estilos from './BloquePostura.module.css';
import { FiguraWati } from './FiguraWati';
import { useConteo } from './useConteo';
import { rasgosDe } from './wati';

interface Props {
  postura: 'favor' | 'contra';
  porcentaje: number;
  personas: number;
  aspecto: number;
  /** Línea grande sobre la cifra, por ejemplo cuánto ganó una variante contra la A. */
  encabezado?: string;
  /** Una línea chica bajo el encabezado. */
  nota?: string;
  /** Qué se cuenta: personas simuladas o agentes. */
  unidad?: string;
  /** En pantallas angostas el wati no crece: no hay lugar. */
  compacto?: boolean;
}

/** La cifra de un lado del país: el wati de esa postura crece con su porcentaje. */
export function BloquePostura({ postura, porcentaje, personas, aspecto, unidad = 'personas', compacto = false, encabezado, nota }: Props) {
  const contado = useConteo(porcentaje);
  const alto = compacto ? 44 : Math.round(56 + contado * 0.75);
  return (
    <section className={estilos.bloque} data-postura={postura} data-compacto={compacto || undefined} aria-label={`${porcentaje} % ${POSTURA_TEXTO[postura]}`}>
      <FiguraWati estado={postura} rasgos={rasgosDe(`${postura}#${aspecto}`)} alto={alto} />
      <p className={estilos.cifra} aria-hidden="true">
        {Math.round(contado)}
        <span>%</span>
      </p>
      <p className={estilos.nombre}>{POSTURA_TEXTO[postura]}</p>
      <p className={estilos.personas}>{formatear(personas)} {unidad}</p>
      {encabezado && (
        <p className={estilos.encabezado} data-baja={encabezado.startsWith('-') || undefined}>
          {encabezado}
        </p>
      )}
      {nota && <p className={estilos.nota}>{nota}</p>}
    </section>
  );
}
