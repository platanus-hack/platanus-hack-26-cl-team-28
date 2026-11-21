import { POSTURA_TEXTO } from '../../contenido';
import type { Porcentajes } from '../../dominio/metricas';
import { POSTURAS } from '../../dominio/tipos';
import estilos from './BarraPosturas.module.css';

interface Props {
  porcentajes: Porcentajes;
  /** Muestra bajo la barra el desglose escrito: el color nunca va solo. */
  conTexto?: boolean;
}

export function BarraPosturas({ porcentajes, conTexto = true }: Props) {
  return (
    <div className={estilos.caja}>
      <div className={estilos.barra} aria-hidden="true">
        {POSTURAS.map((postura) => (
          <span key={postura} className={estilos[postura]} style={{ flexGrow: porcentajes[postura] }} />
        ))}
      </div>
      {conTexto && (
        <p className={estilos.texto}>
          {POSTURAS.map((postura) => (
            <span key={postura} className={estilos[`texto_${postura}`]}>
              <b>{porcentajes[postura]} %</b> {POSTURA_TEXTO[postura]}
            </span>
          ))}
        </p>
      )}
    </div>
  );
}
