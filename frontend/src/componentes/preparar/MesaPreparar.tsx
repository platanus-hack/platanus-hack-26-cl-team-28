import { NOTA_DEMO, PREPARAR } from '../../contenido';
import { formatear } from '../../dominio/textos';
import type { Simulacion } from '../../estado/useSimulacion';
import { Boton } from '../comunes/Boton';
import { EditorCasos } from './EditorCasos';
import { FiltrosMuestra } from './FiltrosMuestra';
import estilos from './MesaPreparar.module.css';

function aviso(sim: Simulacion): string {
  if (sim.muestra.total === 0) return PREPARAR.sinPersonas;
  if (sim.faltanCasos) return PREPARAR.faltanCasos;
  if (sim.muestra.total < sim.muestra.pedidas) {
    return `Hay ${formatear(sim.muestra.disponibles)} perfiles disponibles de los ${formatear(sim.muestra.pedidas)} pedidos.`;
  }
  return sim.simulador.esDemostracion ? NOTA_DEMO : '';
}

export function MesaPreparar({ sim }: { sim: Simulacion }) {
  return (
    <form
      className={estilos.mesa}
      onSubmit={(e) => {
        e.preventDefault();
        void sim.preguntar();
      }}
    >
      <EditorCasos sim={sim} />
      <FiltrosMuestra sim={sim} />
      <footer className={estilos.pie}>
        <p role="status">{aviso(sim)}</p>
        <Boton type="submit" variante="primario" disabled={!sim.puedePreguntar}>
          Preguntar a {formatear(sim.muestra.total)} personas
        </Boton>
      </footer>
    </form>
  );
}
