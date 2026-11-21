import { useEffect, useRef, useState } from 'react';
import { Boton } from '../componentes/comunes/Boton';
import { FiltrosMuestra } from '../componentes/preparar/FiltrosMuestra';
import type { Simulacion } from '../estado/useSimulacion';
import estilos from './MenuOpciones.module.css';

interface Props {
  sim: Simulacion;
  claro: boolean;
  alCambiarTema(): void;
  alOcultar(): void;
}

/** Un solo botón que despliega todo lo que no es la pregunta: a quiénes se pregunta y cómo se ve. */
export function MenuOpciones({ sim, claro, alCambiarTema, alOcultar }: Props) {
  const [abierto, setAbierto] = useState(false);
  const caja = useRef<HTMLDivElement>(null);
  const boton = useRef<HTMLDivElement>(null);

  // Se cierra con Escape o al tocar fuera, y el foco vuelve al botón.
  useEffect(() => {
    if (!abierto) return;
    const cerrar = () => {
      setAbierto(false);
      boton.current?.querySelector('button')?.focus();
    };
    const tecla = (e: KeyboardEvent) => e.key === 'Escape' && cerrar();
    const fuera = (e: PointerEvent) => !caja.current?.contains(e.target as Node) && setAbierto(false);
    window.addEventListener('keydown', tecla);
    window.addEventListener('pointerdown', fuera);
    return () => {
      window.removeEventListener('keydown', tecla);
      window.removeEventListener('pointerdown', fuera);
    };
  }, [abierto]);

  return (
    <div className={estilos.menu} ref={caja}>
      {abierto && (
        <div className={estilos.panel} id="panel-opciones" role="region" aria-label="Opciones">
          <FiltrosMuestra sim={sim} />
          <div className={estilos.vista}>
            <Boton variante="secundario" onClick={alCambiarTema}>
              {claro ? 'Fondo oscuro' : 'Fondo claro'}
            </Boton>
            <Boton
              variante="secundario"
              onClick={() => {
                setAbierto(false);
                alOcultar();
              }}
            >
              Ocultar la interfaz (H)
            </Boton>
          </div>
          {sim.simulador.esDemostracion && (
            <p className={estilos.demo}>Datos de demostración: las respuestas se generan en el navegador hasta conectar el motor de simulación.</p>
          )}
        </div>
      )}
      <div ref={boton}>
        <Boton variante="secundario" aria-expanded={abierto} aria-controls="panel-opciones" onClick={() => setAbierto(!abierto)}>
          Opciones
          <svg viewBox="0 0 12 8" aria-hidden="true" data-abierto={abierto || undefined}>
            <path d="M1 6.5l5-5 5 5" />
          </svg>
        </Boton>
      </div>
    </div>
  );
}
