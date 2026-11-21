import { RESULTADOS } from '../../contenido';
import { REGIONES } from '../../dominio/catalogos';
import type { Simulacion } from '../../estado/useSimulacion';
import { Boton } from '../comunes/Boton';
import { ComparacionCasos } from './ComparacionCasos';
import { FichaPersona } from './FichaPersona';
import { FranjaRegiones } from './FranjaRegiones';
import { PanelAcciones } from './PanelAcciones';
import { PanelVoces } from './PanelVoces';
import estilos from './TableroResultados.module.css';

interface Props {
  sim: Simulacion;
  xReales: number[];
  ancho: number;
  region: number;
  /** Posición en la muestra de la persona elegida, o -1. */
  posicionElegida: number;
  alElegirRegion(region: number): void;
  alElegirPersona(posicion: number): void;
}

export function TableroResultados({ sim, xReales, ancho, region, posicionElegida, alElegirRegion, alElegirPersona }: Props) {
  const corrida = sim.corrida!;
  const resumen = corrida.resumenes[sim.activo];
  return (
    <div className={estilos.tablero}>
      <FranjaRegiones resumen={resumen} xReales={xReales} ancho={ancho} region={region} alElegir={alElegirRegion} />
      <div className={estilos.rotulo}>
        <h2>
          {RESULTADOS.franja} <span>{region >= 0 ? `Viendo ${REGIONES[region].nombre}` : RESULTADOS.franjaAyuda}</span>
        </h2>
        <Boton variante="texto" onClick={sim.editar}>
          {RESULTADOS.editar}
        </Boton>
      </div>
      <div className={estilos.paneles}>
        <ComparacionCasos corrida={corrida} activo={sim.activo} alElegir={sim.setActivo} />
        <PanelAcciones resumen={resumen} letra={corrida.casos[sim.activo].letra} />
        {posicionElegida >= 0 ? (
          <FichaPersona corrida={corrida} posicion={posicionElegida} activo={sim.activo} alCerrar={() => alElegirPersona(-1)} />
        ) : (
          <PanelVoces corrida={corrida} activo={sim.activo} alElegir={alElegirPersona} />
        )}
      </div>
    </div>
  );
}
