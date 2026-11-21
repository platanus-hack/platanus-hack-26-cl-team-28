import { useCallback, useMemo, useRef, useState } from 'react';
import estilos from './App.module.css';
import { Cabecera } from './componentes/cabecera/Cabecera';
import { Titular } from './componentes/cabecera/Titular';
import { Leyenda } from './componentes/mapa/Leyenda';
import { MapaChile, type MapaApi, type OrdenMapa } from './componentes/mapa/MapaChile';
import { PanelPreguntando } from './componentes/preguntando/PanelPreguntando';
import { MesaPreparar } from './componentes/preparar/MesaPreparar';
import { TableroResultados } from './componentes/resultados/TableroResultados';
import { POSTURA_TITULO } from './contenido';
import { REGIONES } from './dominio/catalogos';
import { crearPoblacion } from './dominio/poblacion';
import { personasPorFigura } from './dominio/muestra';
import { describirPersona, formatear, vozDe } from './dominio/textos';
import { estadosDeCaso, estadosDeMuestra } from './estado/corrida';
import { DURACION_BARRIDO, useSimulacion } from './estado/useSimulacion';
import { REGIONES_GEO } from './mapa/geografia';
import { crearMultitud } from './mapa/multitud';
import { aMundo } from './mapa/proyeccion';

/** Figuras dibujadas en el mapa: menos en pantallas angostas, donde el país se recorre por tramos. */
const FIGURAS = matchMedia('(min-width: 1080px)').matches ? 680 : 420;
const PERSONAS = crearPoblacion(FIGURAS, REGIONES_GEO);
const MULTITUD = crearMultitud(PERSONAS);
const ASPECTOS = Uint8Array.from(PERSONAS, (persona) => persona.aspecto);
const X_REGIONES = REGIONES.map((region) => aMundo(region.capitalLon, region.capitalLat)[0]);

export function App() {
  const sim = useSimulacion(PERSONAS);
  const { fase, corrida, muestra, activo, enBarrido } = sim;
  const api = useRef<MapaApi>(null);
  const [medida, setMedida] = useState<{ xs: number[]; ancho: number }>({ xs: [], ancho: 0 });
  const [elegida, setElegida] = useState(-1);
  const [region, setRegion] = useState(-1);
  const [acercado, setAcercado] = useState(false);

  const orden = useMemo<OrdenMapa>(() => {
    if (fase === 'preparar' || !corrida) return { estados: estadosDeMuestra(muestra, FIGURAS), modo: 'cambio' };
    if (fase === 'resultados') return { estados: estadosDeCaso(corrida, activo, FIGURAS), modo: 'cambio' };
    const etiqueta = `Variante ${corrida.casos[enBarrido].letra}`;
    return { estados: estadosDeCaso(corrida, enBarrido, FIGURAS), modo: 'barrido', duracion: DURACION_BARRIDO, etiqueta };
  }, [fase, corrida, muestra, activo, enBarrido]);

  const medir = useCallback(() => {
    const mapa = api.current;
    if (!mapa) return;
    setMedida({ xs: X_REGIONES.map((x) => mapa.xInicial(x)), ancho: document.documentElement.clientWidth });
  }, []);

  const avances = useMemo(() => {
    const { x, minX, maxX } = MULTITUD;
    return corrida ? corrida.muestra.indices.map((indice) => (x[indice] - minX) / (maxX - minX)) : [];
  }, [corrida]);

  const enResultados = fase === 'resultados' && corrida !== null;
  const posicionElegida = enResultados ? corrida.muestra.indices.indexOf(elegida) : -1;

  const rotular = (indice: number, reunidas: number): string => {
    const persona = PERSONAS[indice];
    if (reunidas > 1) {
      const porFigura = personasPorFigura(enResultados ? corrida.muestra : muestra);
      const cerca = `Grupo cerca de ${REGIONES[persona.region].nombre}`;
      return porFigura > 0 ? `${cerca} · unas ${formatear(Math.round(reunidas * porFigura))} personas · clic para acercar` : `${cerca} · clic para acercar`;
    }
    const base = `${describirPersona(persona)} · ${REGIONES[persona.region].nombre}`;
    const posicion = enResultados ? corrida.muestra.indices.indexOf(indice) : -1;
    return posicion < 0 ? base : `${base} · ${POSTURA_TITULO[corrida!.resultados[activo].respuestas[posicion].postura]}`;
  };

  return (
    <div className={estilos.app} data-acercado={acercado || undefined}>
      <Cabecera fase={fase} esDemostracion={sim.simulador.esDemostracion} />
      <Titular sim={sim} />
      <MapaChile
        multitud={MULTITUD}
        aspectos={ASPECTOS}
        orden={orden}
        elegida={posicionElegida >= 0 ? elegida : -1}
        frase={posicionElegida >= 0 ? `“${vozDe(corrida!.resultados[activo].respuestas[posicionElegida])}”` : ''}
        region={enResultados ? region : -1}
        alElegir={(indice) => enResultados && setElegida(indice)}
        alMedir={medir}
        alAcercarse={setAcercado}
        rotular={rotular}
        api={api}
      >
        <Leyenda conPosturas={fase !== 'preparar'} />
      </MapaChile>
      <main className={estilos.tablero}>
        {fase === 'preparar' && <MesaPreparar sim={sim} />}
        {fase === 'preguntando' && corrida && <PanelPreguntando sim={sim} avances={avances} />}
        {enResultados && (
          <TableroResultados
            sim={sim}
            xReales={medida.xs}
            ancho={medida.ancho}
            region={region}
            posicionElegida={posicionElegida}
            alElegirRegion={setRegion}
            alElegirPersona={(posicion) => setElegida(posicion < 0 ? -1 : corrida.muestra.indices[posicion])}
          />
        )}
      </main>
    </div>
  );
}
