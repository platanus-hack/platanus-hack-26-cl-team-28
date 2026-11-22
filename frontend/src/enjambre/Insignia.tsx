import { formatear, personasAprox } from '../dominio/textos';
import type { Conexion } from '../vivo/useEnVivo';
import { useRef } from 'react';
import type { RasgoVoto } from '../vivo/analisis';
import { rebotarWati } from './animarWati';
import { ConRasgos } from './ConRasgos';
import estilos from './Insignia.module.css';
import { FiguraWati } from './FiguraWati';
import { rasgosDe } from './wati';

interface Props {
  conexion: Conexion | null;
  agentes: number;
  /** A cuántas personas equivale cada agente, si el motor lo informa. */
  porAgente?: number | null;
  /** Porcentaje que no se decide, cuando hay un resultado en pantalla. */
  indecisas?: number;
  agentesIndecisos?: number;
  /** Lo que distingue a quienes no se deciden: se lee al pasar el mouse o hacer click en su wati. */
  rasgosIndecisas?: RasgoVoto[];
}

/**
 * Ficha de la muestra: a quiénes se les pregunta y, con un resultado en pantalla, qué son los
 * puntos amarillos que se quedan en el mapa. Si no responde el motor en vivo, lo avisa.
 */
export function Insignia({ conexion, agentes, porAgente, indecisas, agentesIndecisos = 0, rasgosIndecisas = [] }: Props) {
  const figura = useRef<HTMLSpanElement>(null);
  if (!conexion) return null;
  const motor = conexion.estado?.motor;
  const aviso = conexion.demo || !motor || motor.grabado ? 'Demostración sin motor' : null;
  return (
    <dl className={estilos.ficha}>
      <div className={estilos.muestra}>
        <dt>Muestra · Censo 2024</dt>
        <dd>
          <b>{formatear(agentes)}</b> <span className={estilos.unidad}>agentes</span>
        </dd>
      </div>
      {indecisas !== undefined && (
        <div data-indecisas>
          <dt>sin decidir</dt>
          <dd className={estilos.cifraIndecisas}>
            <ConRasgos rasgos={rasgosIndecisas} postura="indecisa" unidad="agentes" porAgente={porAgente} hacia="izquierda" abajo>
              {(descrito) => (
                <button type="button" className={estilos.botonWati} aria-label={rasgosIndecisas.length ? 'Quiénes no se deciden' : 'Animar al wati sin decidir'} aria-describedby={descrito} onClick={() => figura.current && rebotarWati(figura.current)}>
                  <span ref={figura} className={estilos.figura}>
                    <FiguraWati estado="indecisa" rasgos={rasgosDe('indecisa#0')} alto={48} />
                  </span>
                </button>
              )}
            </ConRasgos>
            <b>{indecisas}<span className={estilos.signoPorcentaje}> %</span></b>
          </dd>
          {porAgente ? <dd className={estilos.cantidadIndecisas}>≈ {personasAprox(agentesIndecisos * porAgente)}</dd> : null}
        </div>
      )}
      {aviso && <p className={estilos.aviso}>{aviso}</p>}
    </dl>
  );
}
