import type { ButtonHTMLAttributes } from 'react';
import estilos from './Boton.module.css';

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  /** Una sola acción `primario` por pantalla; el resto, `secundario` o `texto`. */
  variante: 'primario' | 'secundario' | 'texto';
}

export function Boton({ variante, type = 'button', ...resto }: Props) {
  return <button type={type} className={estilos[variante]} {...resto} />;
}
