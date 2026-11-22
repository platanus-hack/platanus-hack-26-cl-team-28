import type { Porcentajes } from '../../dominio/metricas';
import { personasAprox } from '../../dominio/textos';
import { useConteo } from '../useConteo';
import estilos from './ResumenPostura.module.css';

interface Props {
  porcentajes: Porcentajes;
  /** Agentes en cada postura. */
  conteo: { favor: number; contra: number; indecisa: number };
  /** A cuántas personas equivale cada agente; sin él no se dice cuántas personas son. */
  porAgente?: number | null;
}

/** El resultado en una línea, siempre a la vista en el asomo de la hoja: en contra a la izquierda, a favor a la derecha. */
export function ResumenPostura({ porcentajes, conteo, porAgente }: Props) {
  const contra = useConteo(porcentajes.contra);
  const favor = useConteo(porcentajes.favor);
  const personas = (agentes: number) => (porAgente ? `≈ ${personasAprox(agentes * porAgente)}` : null);
  return (
    <div
      className={estilos.resumen}
      role="group"
      aria-label={`${porcentajes.contra} % en contra, ${porcentajes.favor} % a favor, ${porcentajes.indecisa} % sin decidir`}
    >
      <div className={estilos.cifras} aria-hidden="true">
        <p data-postura="contra">
          <small>en contra</small>
          <b>
            {Math.round(contra)}
            <span>%</span>
          </b>
          {personas(conteo.contra) && <em>{personas(conteo.contra)}</em>}
        </p>
        <p data-postura="indecisa">
          <small>sin decidir</small>
          <b>
            {porcentajes.indecisa}
            <span>%</span>
          </b>
        </p>
        <p data-postura="favor">
          <small>a favor</small>
          <b>
            {Math.round(favor)}
            <span>%</span>
          </b>
          {personas(conteo.favor) && <em>{personas(conteo.favor)}</em>}
        </p>
      </div>
      <span className={estilos.barra} aria-hidden="true">
        {(['contra', 'indecisa', 'favor'] as const).map((postura) => (
          <i key={postura} data-postura={postura} style={{ flexGrow: porcentajes[postura] }} />
        ))}
      </span>
    </div>
  );
}
