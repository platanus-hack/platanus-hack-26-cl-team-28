import type { Postura } from '../../dominio/tipos';
import type { RasgoVoto } from '../../vivo/analisis';
import { TarjetaRasgos } from '../ConRasgos';
import { FiguraWati } from '../FiguraWati';
import { rasgosDe } from '../wati';
import estilos from './Quienes.module.css';

interface Props {
  rasgos: Record<Postura, RasgoVoto[]>;
  porAgente?: number | null;
}

const ORDEN: readonly Postura[] = ['favor', 'contra', 'indecisa'];
/** El mismo wati que representa a cada postura junto a su cifra en el escritorio. */
const WATI: Record<Postura, string> = { favor: 'favor#1', contra: 'contra#3', indecisa: 'indecisa#0' };
const TITULO: Record<Postura, string> = { favor: 'A favor', contra: 'En contra', indecisa: 'Sin decidir' };

/**
 * Qué distingue a cada lado del voto. En el escritorio se lee al tocar los watis junto a las cifras;
 * en el teléfono no hay lugar para tarjetas flotantes, así que van escritas, una postura debajo de otra.
 */
export function Quienes({ rasgos, porAgente }: Props) {
  return (
    <div className={estilos.quienes}>
      {ORDEN.map((postura) => (
        <section key={postura} className={estilos.postura} data-postura={postura} aria-label={`Quiénes: ${TITULO[postura].toLowerCase()}`}>
          <div className={estilos.cabeza}>
            <FiguraWati estado={postura} rasgos={rasgosDe(WATI[postura])} alto={44} />
            <h3>{TITULO[postura]}</h3>
          </div>
          {rasgos[postura].length ? (
            <TarjetaRasgos rasgos={rasgos[postura]} postura={postura} unidad="agentes" porAgente={porAgente} />
          ) : (
            <p className={estilos.vacio}>Ningún grupo se distingue del total.</p>
          )}
        </section>
      ))}
    </div>
  );
}
