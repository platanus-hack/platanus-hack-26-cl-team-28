import { useEffect, useRef, type ReactNode } from 'react';
import { PopupFlotante } from '../componentes/comunes/Popup';
import { formatear } from '../dominio/textos';
import {
  activos,
  activosEn,
  alternar,
  conDatos,
  PARAMETROS,
  quitar,
  SECCIONES,
  sinFiltros,
  textoEdad,
  type ClaveSeccion,
  type FiltrosVivo,
  type Parametro,
} from '../vivo/sociedad';
import { TAMANOS_AGENTES, type EnVivo } from '../vivo/useEnVivo';
import estilos from './CajonMuestra.module.css';
import { BarraPartida, Columnas, Filas, RangoEdad } from './muestra/Controles';
import { Seccion } from './muestra/Seccion';

/** Qué secciones del cajón están abiertas. */
export type Abiertas = Partial<Record<ClaveSeccion | 'muestra', boolean>>;

interface Props {
  abierto: boolean;
  sim: EnVivo;
  abiertas: Abiertas;
  alAbrir(abiertas: Abiertas): void;
  alCerrar(): void;
}

const CUADROS = 60;
const cuantos = (n: number) => (n === 1 ? '1 filtro' : `${n} filtros`);

/**
 * A quiénes se les pregunta (o, con un resultado en pantalla, a quiénes se mira) y cómo se ve.
 * Un cajón a todo el alto: arriba cuánta gente queda, dibujada con los mismos cuadrados del
 * mapa, y los filtros puestos; debajo, los parámetros de la sociedad por secciones. Cada filtro
 * es a la vez un gráfico de cuánta gente hay en cada opción.
 */
export function CajonMuestra({ abierto, sim, abiertas, alAbrir, alCerrar }: Props) {
  const { filtros, setFiltros, muestra, retrato } = sim;
  const caja = useRef<HTMLElement>(null);
  const enCorrida = sim.fase === 'resultados';
  // Sin corrida, los cuadros muestran cuánto de lo pedido se va a preguntar: con filtros muy finos no alcanza.
  const base = enCorrida ? sim.totalCorrida : sim.conexion?.demo ? (sim.conexion?.agentes.length ?? 0) : filtros.tamano;
  const representadas = sim.conexion?.demo ? undefined : muestra.representadas;
  const totalReferencia = enCorrida ? base : representadas;
  const niveles = sim.conexion?.estado?.poblacion?.niveles ?? [];
  // Con menos personas por agente hay más agentes entre los que sortear; con 10.000, un filtro deja muy pocos.
  const enNivel = !enCorrida && !sim.conexion?.demo && sim.conexion?.muestra ? muestra.disponibles : undefined;
  const llenos = base ? Math.max(muestra.total ? 1 : 0, Math.round((muestra.total / base) * CUADROS)) : 0;
  const cambiar = (parte: Partial<FiltrosVivo>) => setFiltros({ ...filtros, ...parte });
  const puestos = activos(filtros);
  const alternarSeccion = (clave: ClaveSeccion | 'muestra') => alAbrir({ ...abiertas, [clave]: !abiertas[clave] });

  useEffect(() => {
    if (!abierto) return;
    caja.current?.focus({ preventScroll: true });
    const tecla = (e: KeyboardEvent) => e.key === 'Escape' && alCerrar();
    const fuera = (e: PointerEvent) => {
      const destino = e.target;
      if (destino instanceof Element && !caja.current?.contains(destino) && !destino.closest('[aria-controls="cajon-muestra"]')) alCerrar();
    };
    window.addEventListener('keydown', tecla);
    // En el siguiente ciclo: el clic que abrió el cajón no debe cerrarlo.
    const escucha = window.setTimeout(() => window.addEventListener('pointerdown', fuera), 0);
    return () => {
      window.clearTimeout(escucha);
      window.removeEventListener('keydown', tecla);
      window.removeEventListener('pointerdown', fuera);
    };
  }, [abierto, alCerrar]);

  const control = (parametro: Parametro): ReactNode => {
    const elegidas = filtros.elegidos[parametro.clave] ?? [];
    // Un parámetro que la población no trae (el archivo de respaldo, la demostración) no se ofrece.
    if (!retrato || (!conDatos(retrato, parametro.clave) && !elegidas.length)) return null;
    const comun = { parametro, personas: retrato[parametro.clave], elegidas, alTocar: (opcion: number) => setFiltros(alternar(filtros, parametro, opcion)) };
    return (
      <fieldset key={parametro.clave} className={estilos.grupo}>
        <legend>{parametro.rotulo}</legend>
        {parametro.forma === 'partida' ? <BarraPartida {...comun} /> : parametro.forma === 'columnas' ? <Columnas {...comun} /> : <Filas {...comun} doble={parametro.clave === 'region'} />}
      </fieldset>
    );
  };

  return (
    <PopupFlotante as="aside" abierto={abierto} lateral ref={caja} tabIndex={-1} className={estilos.cajon} id="cajon-muestra" aria-label="Muestra y vista">
      <header className={estilos.cabeza}>
        <dl className={estilos.cuenta}>
          <div>
            <dt>{enCorrida ? 'Agentes visibles' : 'Agentes de la muestra'}</dt>
            <dd className={estilos.cifraPrincipal}>{formatear(muestra.total)}</dd>
          </div>
          {totalReferencia !== undefined && (
            <div>
              <dt>{enCorrida ? 'Total de agentes' : 'Personas según filtros'}</dt>
              <dd>{formatear(totalReferencia)}</dd>
            </div>
          )}
        </dl>
        <button type="button" className={estilos.cerrar} onClick={alCerrar} aria-label="Cerrar">
          <svg viewBox="0 0 12 12" aria-hidden="true">
            <path d="M2 2l8 8M10 2l-8 8" />
          </svg>
        </button>
        {niveles.length > 1 && enNivel !== undefined && (
          <p className={estilos.nivel}>
            {enNivel < filtros.tamano
              ? `Solo ${formatear(enNivel)} agentes cumplen los filtros en este nivel: responden todos.`
              : `${formatear(enNivel)} agentes cumplen los filtros en este nivel.`}
          </p>
        )}
        <div className={estilos.cuadros} aria-hidden="true">
          {Array.from({ length: CUADROS }, (_, k) => (
            <i key={k} data-lleno={k < llenos || undefined} />
          ))}
        </div>
        {puestos.length > 0 && (
          <div className={estilos.puestos}>
            {puestos.map((filtro) => (
              <button key={filtro.clave} type="button" aria-label={`Quitar el filtro de ${filtro.rotulo.toLowerCase()}: ${filtro.texto}`} onClick={() => setFiltros(quitar(filtros, filtro.clave))}>
                {filtro.texto}
                <svg viewBox="0 0 12 12" aria-hidden="true">
                  <path d="M3 3l6 6M9 3l-6 6" />
                </svg>
              </button>
            ))}
            <button type="button" className={estilos.limpiar} onClick={() => setFiltros(sinFiltros(filtros))}>
              Quitar todo
            </button>
          </div>
        )}
      </header>

      <div className={estilos.cuerpo}>
        <Seccion titulo="Muestra" resumen={abiertas.muestra ? undefined : `${formatear(filtros.tamano)} agentes`} abierta={!!abiertas.muestra} alAlternar={() => alternarSeccion('muestra')}>
          <div className={estilos.ajustesMuestra}>
            <fieldset className={estilos.grupo}>
              <legend>{enCorrida ? 'Cuántas preguntar la próxima vez' : 'Cuántas preguntar'}</legend>
              <div className={`${estilos.tamanos} ${estilos.tamanosMuestra}`}>
                {/* El motor puede tener un tope más bajo (con el sitio abierto al público): no se ofrece lo que no va a dar. */}
                {TAMANOS_AGENTES.filter((tamano) => tamano <= (sim.conexion?.estado?.maximo_muestra ?? Infinity)).map((tamano) => (
                  <button key={tamano} type="button" aria-pressed={filtros.tamano === tamano} onClick={() => cambiar({ tamano })}>
                    {formatear(tamano)}
                  </button>
                ))}
              </div>
            </fieldset>
            {niveles.length > 1 && (
              <fieldset className={estilos.grupo}>
                <legend>
                  Clusterización
                  <output>1 agente representa a {formatear(filtros.reduccion)} personas</output>
                </legend>
                <div className={estilos.tamanos}>
                  {niveles.map((nivel) => (
                    <button key={nivel} type="button" aria-pressed={filtros.reduccion === nivel} onClick={() => cambiar({ reduccion: nivel })}>
                      {formatear(nivel)}
                    </button>
                  ))}
                </div>
              </fieldset>
            )}
          </div>
        </Seccion>

        {SECCIONES.map((seccion) => {
          const controles = PARAMETROS.filter((p) => p.seccion === seccion.clave).map(control);
          const conEdad = seccion.clave === 'personas' && !!retrato;
          if (!conEdad && controles.every((c) => c === null)) return null;
          const filtrando = activosEn(filtros, seccion.clave);
          return (
            <Seccion
              key={seccion.clave}
              titulo={seccion.titulo}
              resumen={filtrando ? cuantos(filtrando) : undefined}
              fuente={sim.conexion?.demo ? undefined : seccion.fuente}
              abierta={!!abiertas[seccion.clave]}
              alAlternar={() => alternarSeccion(seccion.clave)}
            >
              {conEdad && retrato && (
                <fieldset className={estilos.grupo}>
                  <legend>
                    Edad
                    <output>{textoEdad(filtros)}</output>
                  </legend>
                  <RangoEdad personas={retrato.edad} desde={filtros.edadMin} hasta={filtros.edadMax} alCambiar={(edadMin, edadMax) => cambiar({ edadMin, edadMax })} />
                </fieldset>
              )}
              {controles}
            </Seccion>
          );
        })}
      </div>
    </PopupFlotante>
  );
}
