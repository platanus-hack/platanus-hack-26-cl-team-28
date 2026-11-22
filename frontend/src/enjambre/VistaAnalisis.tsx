import { useMemo, useState, type ReactNode } from 'react';
import { Desplegable } from '../componentes/comunes/Desplegable';
import { formatear } from '../dominio/textos';
import { alto, cruzar, mediaDe, MINIMO_GRUPO, ordenarDimensiones, resumirDimension, type ClaveDimension, type ResumenDimension } from '../vivo/analisis';
import { midePostura, preguntaDe, resumirEncuesta } from '../vivo/encuesta';
import type { Conexion, EnVivo } from '../vivo/useEnVivo';
import { Propuesta } from './Propuesta';
import { ListaSeparan } from './analisis/ListaSeparan';
import { PreguntasJuntas } from './analisis/PreguntasJuntas';
import { TablaGrupos, type Cruce } from './analisis/TablaGrupos';
import { VocesGrupos } from './analisis/VocesGrupos';
import { useConsulta } from './useAngosto';
import estilos from './VistaAnalisis.module.css';

interface Props {
  sim: EnVivo;
  conexion: Conexion;
}

/** Con más filas que estas la tabla ocupa todo el alto y las frases no se muestran. */
const FILAS_CON_VOCES = 8;
/** Un cruce con más columnas que estas no cabe junto a las barras. */
const MAXIMO_COLUMNAS = 6;

const decimal = (valor: number) => valor.toFixed(1).replace('.', ',');

/** Los dos lados de una escala en pocas palabras: «totalmente de acuerdo» es «de acuerdo», «nada influyente» es «poco influyente». */
const breve = (extremo: string) => extremo.replace(/^(totalmente|muy) /, '').replace(/^nada /, 'poco ');

const minuscula = (texto: string) => texto.charAt(0).toLowerCase() + texto.slice(1);
const mayuscula = (texto: string) => texto.charAt(0).toUpperCase() + texto.slice(1);

/** Lo que muestra la característica elegida, dicho en una frase. `lado` nombra el tramo de 5 a 7. */
function hallazgo(resumen: ResumenDimension, lado: string): ReactNode {
  const { extremos, grupos, dimension, clara } = resumen;
  if (!extremos) return `No hay dos grupos con al menos ${MINIMO_GRUPO} respuestas para comparar.`;
  const puntos = `${extremos.brecha} ${extremos.brecha === 1 ? 'punto' : 'puntos'}`;
  if (!clara) return `Esta característica casi no ordena las respuestas: entre el grupo más alto y el más bajo hay ${puntos}, lo esperable por azar con esta muestra.`;
  return (
    <>
      <b>{dimension.grupos[extremos.mayor]}</b> es el grupo que más respondió {lado} ({alto(grupos[extremos.mayor])}{'\u00a0'}%) y <b>{dimension.grupos[extremos.menor]}</b> el que menos ({alto(grupos[extremos.menor])}{'\u00a0'}%). Los separan {puntos}.
    </>
  );
}

/**
 * El análisis de la corrida en lugar del mapa: cómo respondió cada grupo de personas a cada
 * pregunta. A la izquierda, todas las características ordenadas por cuánto separan las respuestas;
 * al centro, la elegida, grupo por grupo, con la opción de cruzarla con otra.
 */
export function VistaAnalisis({ sim, conexion }: Props) {
  /** En pantallas táctiles no hay cursor que pase por encima: se toca. */
  const conDedo = useConsulta('(pointer: coarse)');
  const { casos, viendo, muestra, version, encuesta } = sim;
  const caso = casos[viendo];
  const base = viendo > 0 && casos[0].listo ? casos[0] : null;
  const [preguntaElegida, setPregunta] = useState(0);
  const [elegida, setElegida] = useState<ClaveDimension | null>(null);
  const [cruzada, setCruzada] = useState<ClaveDimension | null>(null);
  const [porResultado, setPorResultado] = useState(false);
  /** El grupo que se está leyendo, con la característica a la que pertenece: si cambia, deja de valer. */
  const [lectura, setLectura] = useState<{ clave: ClaveDimension; grupo: number } | null>(null);
  const pregunta = Math.min(preguntaElegida, Math.max(0, encuesta.length - 1));
  const personas = conexion.agentes;

  // `version` cambia con cada respuesta que llega: las notas se llenan en el mismo arreglo.
  /* eslint-disable react-hooks/exhaustive-deps */
  const totales = useMemo(() => resumirEncuesta(caso.notas, muestra.agentes, encuesta.length), [caso, muestra, encuesta.length, version]);
  const ranking = useMemo(() => ordenarDimensiones(personas, caso.notas, muestra.agentes, pregunta), [personas, caso, muestra, pregunta, version]);
  // Sin elegir, se mira la característica que más separa.
  const actual = ranking.find((r) => r.dimension.clave === elegida) ?? ranking[0];
  const deLaA = useMemo(() => (base && actual ? resumirDimension(actual.dimension, personas, base.notas, muestra.agentes, pregunta) : null), [base, actual?.dimension, personas, muestra, pregunta, version]);
  const cruzables = useMemo(() => ranking.filter((r) => r !== actual && r.grupos.filter((g) => g.total > 0).length <= MAXIMO_COLUMNAS).map((r) => r.dimension), [ranking, actual]);
  const segunda = cruzables.find((d) => d.clave === cruzada) ?? null;
  const cruce = useMemo<Cruce | null>(
    () => (actual && segunda ? { dimension: segunda, tabla: cruzar(actual.dimension, segunda, personas, caso.notas, muestra.agentes, pregunta) } : null),
    [actual?.dimension, segunda, personas, caso, muestra, pregunta, version],
  );
  /* eslint-enable react-hooks/exhaustive-deps */

  // La encuesta la define el motor: si trae preguntas que esta interfaz no conoce, sus nombres y escalas salen de él.
  const estado = conexion.estado;
  const delMotor = (texto: string) => estado?.preguntas?.indexOf(texto) ?? -1;
  const nombres = encuesta.map((texto, k) => preguntaDe(texto)?.nombre ?? estado?.nombres?.[delMotor(texto)] ?? `Pregunta ${k + 1}`);
  const conocida = preguntaDe(encuesta[pregunta] ?? '');
  const extremosEscala = estado?.escalas?.[delMotor(encuesta[pregunta] ?? '')];
  const escala = conocida ?? (extremosEscala ? { minimo: extremosEscala[0], maximo: extremosEscala[1] } : undefined);
  const neutra = !midePostura(encuesta[pregunta] ?? '');
  // Cómo se nombran los tres tramos de la escala de esta pregunta; sin escala conocida, por sus notas.
  const lados = escala ? { bajo: breve(escala.minimo), alto: breve(escala.maximo) } : { bajo: 'de 1 a 3', alto: 'de 5 a 7' };
  const activo = actual && lectura?.clave === actual.dimension.clave && actual.grupos[lectura.grupo]?.total ? lectura.grupo : null;
  const leido = actual && activo !== null ? actual.grupos[activo] : null;
  const respondieron = totales[pregunta]?.conteo.total ?? 0;
  // Elegir como principal la característica que estaba cruzada deshace el cruce.
  const elegir = (clave: ClaveDimension) => {
    if (clave === cruzada) setCruzada(null);
    setElegida(clave);
  };
  const filas = actual ? actual.grupos.filter((g) => g.total > 0).length : 0;

  return (
    <div className={estilos.vista} data-neutra={neutra || undefined}>
      <header className={estilos.cabeza}>
        <div className={estilos.variante}>
          {/* Con una sola propuesta no hay variantes que elegir: basta decir qué es el texto. */}
          <span className={estilos.rotulo}>{casos.length > 1 ? 'Variante' : 'Propuesta'}</span>
          {casos.length > 1 && (
            <div className={estilos.variantes} role="group" aria-label="Variante que se analiza">
              {casos.map((otro, k) => (
                <button key={otro.id} type="button" aria-pressed={k === viendo} disabled={!otro.respondidas} title={otro.titulo} onClick={() => sim.setViendo(k)}>
                  {otro.letra}
                </button>
              ))}
            </div>
          )}
          <h1 className={estilos.titulo}>
            <Propuesta letra={caso.letra} titulo={caso.titulo} texto={caso.texto} />
          </h1>
        </div>
        <div className={estilos.preguntas} role="group" aria-label="Pregunta de la encuesta que se analiza">
          {nombres.map((nombre, k) => (
            <button key={k} type="button" aria-pressed={k === pregunta} title={encuesta[k]} onClick={() => setPregunta(k)}>
              <span>{nombre}</span>
              <b>{totales[k].conteo.total ? `${alto(totales[k].conteo)} %` : ''}</b>
            </button>
          ))}
          <p>{encuesta[pregunta]}</p>
        </div>
      </header>
      {!actual ? (
        <p className={estilos.vacio}>{caso.respondidas ? 'Esta muestra no trae características para comparar.' : 'Esperando las primeras respuestas.'}</p>
      ) : (
        <div className={estilos.cuerpo}>
          <aside className={estilos.lado}>
            <ListaSeparan ranking={ranking} elegida={actual.dimension.clave} neutra={neutra} alElegir={elegir} />
            <PreguntasJuntas nombres={nombres} pregunta={pregunta} notas={caso.notas} agentes={muestra.agentes} alElegir={setPregunta} />
          </aside>
          <main className={estilos.centro}>
            <div className={estilos.encabezado}>
              <h2>
                {nombres[pregunta]} <span>según {minuscula(actual.dimension.breve)}</span>
              </h2>
              <p className={estilos.hallazgo}>{hallazgo(actual, escala ? `«${lados.alto}»` : lados.alto)}</p>
              <div className={estilos.controles}>
                <div className={estilos.cruce}>
                  <span>Cruzar con</span>
                  <Desplegable compacto etiqueta="Cruzar con" valor={segunda?.clave ?? ''} alCambiar={(v) => setCruzada((v || null) as ClaveDimension | null)} opciones={[{ valor: '', texto: 'Nada' }, ...cruzables.map((d) => ({ valor: d.clave, texto: d.breve }))]} />
                </div>
                <button type="button" aria-pressed={porResultado} onClick={() => setPorResultado(!porResultado)}>
                  Ordenar por resultado
                </button>
              </div>
            </div>
            <ul className={estilos.leyenda} aria-label="Cómo leer las barras">
              <li data-postura="contra">{mayuscula(lados.bajo)}{escala && ' (1 a 3)'}</li>
              <li data-postura="indecisa">{escala ? 'Al medio (4)' : 'El 4'}</li>
              <li data-postura="favor">{mayuscula(lados.alto)}{escala && ' (5 a 7)'}</li>
              <li data-marca="total">Total de la muestra</li>
              {deLaA && <li data-marca="antes">Dónde estaba en la variante A</li>}
              {cruce && <li data-marca="casilla">Casilla: % {lados.alto}, más intensa mientras más lejos del total</li>}
            </ul>
            <TablaGrupos alto={mayuscula(lados.alto)} resumen={actual} base={deLaA} cruce={cruce} neutra={neutra} porResultado={porResultado} activo={activo} alActivar={(grupo) => setLectura(grupo === null ? null : { clave: actual.dimension.clave, grupo })} />
            <footer className={estilos.pie} aria-live="polite">
              {leido && activo !== null ? (
                <p>
                  <b>{actual.dimension.grupos[activo]}</b> · {formatear(leido.total)} {leido.total === 1 ? 'agente' : 'agentes'} · {alto(leido)} % {lados.alto}, {100 - alto(leido) - Math.round((leido.contra / leido.total) * 100)} % al medio y{' '}
                  {Math.round((leido.contra / leido.total) * 100)} % {lados.bajo} · nota media {decimal(mediaDe(leido))} de 7
                </p>
              ) : (
                <p>
                  {actual.total.total < respondieron ? `${formatear(actual.total.total)} de ${formatear(respondieron)} agentes tienen este dato` : `${formatear(actual.total.total)} agentes`}
                  {sim.filtrada ? ', según los filtros' : ''}. {conDedo ? 'Toca' : 'Pasa el cursor por'} una fila para ver su detalle.
                </p>
              )}
            </footer>
            {filas <= FILAS_CON_VOCES && (
              <div className={estilos.hueco}>
                <VocesGrupos resumen={actual} pregunta={pregunta} agentes={personas} notas={caso.notas} frases={caso.frase} mirados={muestra.agentes} cuantas={filas <= 4 ? 2 : 1} neutra={neutra} nombres={lados} />
              </div>
            )}
          </main>
        </div>
      )}
    </div>
  );
}
