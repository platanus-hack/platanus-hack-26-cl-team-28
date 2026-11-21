import { MAPA } from '../../contenido';
import estilos from './ControlesMapa.module.css';

interface Props {
  alAcercar(): void;
  alAlejar(): void;
  alRestablecer(): void;
}

export function ControlesMapa({ alAcercar, alAlejar, alRestablecer }: Props) {
  return (
    <div className={estilos.controles} role="group" aria-label="Controles del mapa">
      <button type="button" onClick={alAcercar} aria-label={MAPA.acercar}>
        <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M8 3v10M3 8h10" /></svg>
      </button>
      <button type="button" onClick={alAlejar} aria-label={MAPA.alejar}>
        <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M3 8h10" /></svg>
      </button>
      <button type="button" onClick={alRestablecer} aria-label={MAPA.restablecer}>
        <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M2.5 6V2.5H6M13.5 10v3.5H10M2.5 2.5l4 4M13.5 13.5l-4-4" /></svg>
      </button>
    </div>
  );
}
