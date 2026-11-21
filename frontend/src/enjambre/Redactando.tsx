import { formatear } from '../dominio/textos';
import type { CasoVivo } from '../vivo/useEnVivo';
import estilos from './Redactando.module.css';

interface Props {
  /** Variante con más apoyo hasta ahora: sobre ella reescribe el agente. */
  base: CasoVivo;
  numero: number;
}

/** Entre una variante y la siguiente: el agente lee las objeciones y reescribe la propuesta. */
export function Redactando({ base, numero }: Props) {
  const objeciones = base.conteo.contra + base.conteo.indecisa;
  return (
    <section className={estilos.redactando} aria-live="polite">
      <p className={estilos.etiqueta}>Iteración {numero}</p>
      <p className={estilos.texto}>
        Un agente lee las objeciones de {formatear(objeciones)} personas a la variante {base.letra} y reescribe la propuesta
      </p>
      <span className={estilos.cursor} aria-hidden="true" />
    </section>
  );
}
