import { AVISO_DEMO, MARCA, PASOS } from '../../contenido';
import type { Fase } from '../../estado/useSimulacion';
import estilos from './Cabecera.module.css';

const ORDEN: Fase[] = ['preparar', 'preguntando', 'resultados'];

export function Cabecera({ fase, esDemostracion }: { fase: Fase; esDemostracion: boolean }) {
  const actual = ORDEN.indexOf(fase);
  return (
    <header className={estilos.barra}>
      <p className={estilos.marca}>
        <span className={estilos.sello} aria-hidden="true">
          <i />
          <i />
          <i />
        </span>
        {MARCA}
      </p>
      <ol className={estilos.pasos} aria-label="Etapas">
        {PASOS.map((paso, i) => (
          <li key={paso} aria-current={i === actual ? 'step' : undefined} data-hecho={i < actual || undefined}>
            <span aria-hidden="true">{i + 1}</span>
            {paso}
          </li>
        ))}
      </ol>
      {esDemostracion && (
        <p className={estilos.aviso}>
          <span className={estilos.largo}>{AVISO_DEMO.largo}</span>
          <span className={estilos.corto}>{AVISO_DEMO.corto}</span>
        </p>
      )}
    </header>
  );
}
