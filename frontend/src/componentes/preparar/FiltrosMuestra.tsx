import { PREPARAR } from '../../contenido';
import { EDUCACION, GENEROS, POLITICA, QUINTILES, REGIONES, TAMANOS } from '../../dominio/catalogos';
import { FILTROS_INICIALES, SIN_FILTRO } from '../../dominio/muestra';
import { formatear } from '../../dominio/textos';
import type { Filtros } from '../../dominio/tipos';
import type { Simulacion } from '../../estado/useSimulacion';
import { Boton } from '../comunes/Boton';
import estilos from './FiltrosMuestra.module.css';
import { RangoEdad } from './RangoEdad';

type Lista = keyof Pick<Filtros, 'region' | 'genero' | 'quintil' | 'educacion' | 'politica'>;

const LISTAS: { clave: Lista; rotulo: string; todas: string; opciones: readonly string[] }[] = [
  { clave: 'region', rotulo: 'Región', todas: 'Todas las regiones', opciones: REGIONES.map((r) => r.nombre) },
  { clave: 'genero', rotulo: 'Género', todas: 'Todos', opciones: GENEROS },
  { clave: 'quintil', rotulo: 'Nivel socioeconómico', todas: 'Todos', opciones: QUINTILES },
  { clave: 'educacion', rotulo: 'Nivel educacional', todas: 'Todos', opciones: EDUCACION },
  { clave: 'politica', rotulo: 'Orientación política', todas: 'Todas', opciones: POLITICA },
];

export function FiltrosMuestra({ sim }: { sim: Simulacion }) {
  const { filtros, setFiltros } = sim;
  const cambiar = (parte: Partial<Filtros>) => setFiltros({ ...filtros, ...parte });
  return (
    <section className={estilos.filtros} aria-labelledby="titulo-muestra">
      <header>
        <div>
          <h2 id="titulo-muestra">{PREPARAR.muestra}</h2>
          <p>{PREPARAR.muestraAyuda}</p>
        </div>
        <Boton variante="texto" onClick={() => setFiltros({ ...FILTROS_INICIALES, tamano: filtros.tamano })}>
          {PREPARAR.limpiar}
        </Boton>
      </header>
      <div className={estilos.grilla}>
        <fieldset className={estilos.tamanos}>
        <legend>{PREPARAR.tamano}</legend>
        <div>
          {TAMANOS.map((tamano) => (
            <label key={tamano}>
              <input type="radio" name="tamano" checked={filtros.tamano === tamano} onChange={() => cambiar({ tamano })} />
              <span>{formatear(tamano)}</span>
            </label>
          ))}
        </div>
      </fieldset>
        {LISTAS.slice(0, 1).map((lista) => (
          <Selector key={lista.clave} lista={lista} valor={filtros[lista.clave]} alCambiar={(v) => cambiar({ [lista.clave]: v })} />
        ))}
        <RangoEdad minimo={filtros.edadMin} maximo={filtros.edadMax} alCambiar={(edadMin, edadMax) => cambiar({ edadMin, edadMax })} />
        {LISTAS.slice(1).map((lista) => (
          <Selector key={lista.clave} lista={lista} valor={filtros[lista.clave]} alCambiar={(v) => cambiar({ [lista.clave]: v })} />
        ))}
      </div>
    </section>
  );
}

function Selector({ lista, valor, alCambiar }: { lista: (typeof LISTAS)[number]; valor: number; alCambiar(valor: number): void }) {
  return (
    <label className={estilos.campo}>
      <span>{lista.rotulo}</span>
      <select value={valor} onChange={(e) => alCambiar(+e.target.value)}>
        <option value={SIN_FILTRO}>{lista.todas}</option>
        {lista.opciones.map((opcion, i) => (
          <option key={opcion} value={i}>
            {opcion}
          </option>
        ))}
      </select>
    </label>
  );
}
