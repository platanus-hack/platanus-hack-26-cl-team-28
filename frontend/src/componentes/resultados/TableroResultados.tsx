import { RESULTADOS } from '../../contenido';
import { REGIONES } from '../../dominio/catalogos';
import type { Simulacion } from '../../estado/useSimulacion';
import { Boton } from '../comunes/Boton';
import { ComparacionCasos } from './ComparacionCasos';
import { FichaPersona } from './FichaPersona';
import { PanelAcciones } from './PanelAcciones';
import { PanelVoces } from './PanelVoces';
import estilos from './TableroResultados.module.css';

interface Props {
  sim: Simulacion;
  region: number;
  /** Posición en la muestra de la persona elegida, o -1. */
  posicionElegida: number;
  alVerTodo(): void;
  alElegirPersona(posicion: number): void;
}

/** Los resultados, uno debajo de otro y sin alturas forzadas: la hoja completa se recorre con un solo scroll. */
export function TableroResultados({ sim, region, posicionElegida, alVerTodo, alElegirPersona }: Props) {
  const corrida = sim.corrida!;
  const resumen = corrida.resumenes[sim.activo];
  return (
    <div className={estilos.tablero}>
      <ComparacionCasos corrida={corrida} activo={sim.activo} alElegir={sim.setActivo} />
      {posicionElegida >= 0 && (
        <FichaPersona corrida={corrida} posicion={posicionElegida} activo={sim.activo} alCerrar={() => alElegirPersona(-1)} />
      )}
      <div className={estilos.par}>
        <PanelAcciones resumen={resumen} letra={corrida.casos[sim.activo].letra} />
        <PanelVoces corrida={corrida} activo={sim.activo} alElegir={alElegirPersona} />
      </div>
      <footer className={estilos.pie}>
        {region >= 0 && (
          <Boton variante="secundario" onClick={alVerTodo}>
            {RESULTADOS.verTodo} <span className="solo-lectores">(ahora {REGIONES[region].nombre})</span>
          </Boton>
        )}
        <Boton variante="secundario" onClick={sim.editar}>
          {RESULTADOS.editar}
        </Boton>
      </footer>
    </div>
  );
}
