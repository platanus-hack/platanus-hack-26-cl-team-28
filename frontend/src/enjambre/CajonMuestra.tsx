import { useEffect, useRef, type CSSProperties } from 'react';
import { EDAD_MAXIMA, EDAD_MINIMA, REGIONES } from '../dominio/catalogos';
import { FILTROS_INICIALES, SIN_FILTRO } from '../dominio/muestra';
import { formatear } from '../dominio/textos';
import type { Filtros } from '../dominio/tipos';
import { TAMANOS_AGENTES, type EnVivo } from '../vivo/useEnVivo';
import { CASOS_VALIDACION } from '../vivo/validacion';
import estilos from './CajonMuestra.module.css';

interface Props {
  sim: EnVivo;
  claro: boolean;
  alCambiarTema(): void;
  alOcultar(): void;
  alCerrar(): void;
}

const GENEROS = [
  ['Mujeres', 0],
  ['Hombres', 1],
] as const;
/** Los agentes traen tres niveles; el número es su índice en el catálogo de educación. */
const EDUCACION = [
  ['Básica', 0],
  ['Media', 1],
  ['Superior', 3],
] as const;
const QUINTILES = ['I', 'II', 'III', 'IV', 'V'];
const CUADROS = 60;

const edad = (valor: number) => (valor >= EDAD_MAXIMA ? `${EDAD_MAXIMA}+` : String(valor));
const posicion = (valor: number) => `${((valor - EDAD_MINIMA) / (EDAD_MAXIMA - EDAD_MINIMA)) * 100}%`;

/**
 * A quiénes se les pregunta (o, con un resultado en pantalla, a quiénes se mira) y cómo se ve.
 * Un cajón a todo el alto: arriba cuánta gente queda, dibujada con los mismos cuadrados del
 * mapa; debajo, los filtros como fichas que se tocan.
 */
export function CajonMuestra({ sim, claro, alCambiarTema, alOcultar, alCerrar }: Props) {
  const { filtros, setFiltros, muestra } = sim;
  const caja = useRef<HTMLElement>(null);
  const enCorrida = sim.fase === 'resultados';
  // Sin corrida, los cuadros muestran cuánto de lo pedido se va a preguntar: con filtros muy finos no alcanza.
  const base = enCorrida ? sim.totalCorrida : sim.conexion?.demo ? (sim.conexion?.agentes.length ?? 0) : filtros.tamano;
  const representadas = !enCorrida && !sim.conexion?.demo ? muestra.representadas : undefined;
  const niveles = sim.conexion?.estado?.poblacion?.niveles ?? [];
  const llenos = base ? Math.max(muestra.total ? 1 : 0, Math.round((muestra.total / base) * CUADROS)) : 0;
  const cambiar = (parte: Partial<Filtros>) => setFiltros({ ...filtros, ...parte });
  const alternar = (clave: 'region' | 'genero' | 'quintil' | 'educacion', valor: number) =>
    cambiar({ [clave]: filtros[clave] === valor ? SIN_FILTRO : valor });
  const filtrando =
    filtros.region !== SIN_FILTRO ||
    filtros.genero !== SIN_FILTRO ||
    filtros.quintil !== SIN_FILTRO ||
    filtros.educacion !== SIN_FILTRO ||
    filtros.edadMin > EDAD_MINIMA ||
    filtros.edadMax < EDAD_MAXIMA;

  useEffect(() => {
    caja.current?.focus();
    const tecla = (e: KeyboardEvent) => e.key === 'Escape' && alCerrar();
    const fuera = (e: PointerEvent) => !caja.current?.contains(e.target as Node) && alCerrar();
    window.addEventListener('keydown', tecla);
    // En el siguiente ciclo: el clic que abrió el cajón no debe cerrarlo.
    const escucha = window.setTimeout(() => window.addEventListener('pointerdown', fuera), 0);
    return () => {
      window.clearTimeout(escucha);
      window.removeEventListener('keydown', tecla);
      window.removeEventListener('pointerdown', fuera);
    };
  }, [alCerrar]);

  return (
    <aside ref={caja} tabIndex={-1} className={estilos.cajon} id="cajon-muestra" aria-label="Muestra y vista">
      <header className={estilos.cabeza}>
        <p className={estilos.cuenta}>
          <b>{formatear(muestra.total)}</b>
          <span>
            {enCorrida
              ? `de ${formatear(base)} personas, las que estás mirando`
              : representadas
                ? `personas del Censo 2024 van a responder, sorteadas entre las ${formatear(representadas)} que cumplen los filtros`
                : `personas del Censo 2024 van a responder`}
          </span>
        </p>
        <button type="button" className={estilos.cerrar} onClick={alCerrar} aria-label="Cerrar">
          <svg viewBox="0 0 12 12" aria-hidden="true">
            <path d="M2 2l8 8M10 2l-8 8" />
          </svg>
        </button>
        <div className={estilos.cuadros} aria-hidden="true">
          {Array.from({ length: CUADROS }, (_, k) => (
            <i key={k} data-lleno={k < llenos || undefined} />
          ))}
        </div>
      </header>

      <div className={estilos.cuerpo}>
        <fieldset className={estilos.grupo}>
          <legend>{enCorrida ? 'Cuántas preguntar la próxima vez' : 'Cuántas preguntar'}</legend>
          <div className={estilos.tamanos}>
            {TAMANOS_AGENTES.map((tamano) => (
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
            <div className={estilos.tamanos} style={{ gridTemplateColumns: `repeat(${niveles.length}, 1fr)` }}>
              {niveles.map((nivel) => (
                <button key={nivel} type="button" aria-pressed={filtros.reduccion === nivel} onClick={() => cambiar({ reduccion: nivel })}>
                  {formatear(nivel)}
                </button>
              ))}
            </div>
          </fieldset>
        )}

        <fieldset className={estilos.grupo}>
          <legend>
            Región
            {filtros.region !== SIN_FILTRO && <output>{REGIONES[filtros.region].nombre}</output>}
          </legend>
          <div className={estilos.fichas} data-denso>
            {REGIONES.map((region, k) => (
              <button key={region.corto} type="button" aria-pressed={filtros.region === k} onClick={() => alternar('region', k)}>
                {region.corto}
              </button>
            ))}
          </div>
        </fieldset>

        <fieldset className={estilos.grupo}>
          <legend>
            Edad
            <output>
              {edad(filtros.edadMin)} a {edad(filtros.edadMax)} años
            </output>
          </legend>
          <div className={estilos.edad} style={{ '--desde': posicion(filtros.edadMin), '--hasta': posicion(filtros.edadMax) } as CSSProperties}>
            <input
              type="range"
              min={EDAD_MINIMA}
              max={EDAD_MAXIMA}
              value={filtros.edadMin}
              aria-label="Edad mínima"
              onChange={(e) => cambiar({ edadMin: +e.target.value, edadMax: Math.max(filtros.edadMax, +e.target.value) })}
            />
            <input
              type="range"
              min={EDAD_MINIMA}
              max={EDAD_MAXIMA}
              value={filtros.edadMax}
              aria-label="Edad máxima"
              onChange={(e) => cambiar({ edadMax: +e.target.value, edadMin: Math.min(filtros.edadMin, +e.target.value) })}
            />
          </div>
        </fieldset>

        <div className={estilos.par}>
          <fieldset className={estilos.grupo}>
            <legend>Género</legend>
            <div className={estilos.fichas}>
              {GENEROS.map(([nombre, valor]) => (
                <button key={nombre} type="button" aria-pressed={filtros.genero === valor} onClick={() => alternar('genero', valor)}>
                  {nombre}
                </button>
              ))}
            </div>
          </fieldset>
          <fieldset className={estilos.grupo}>
            <legend>Educación</legend>
            <div className={estilos.fichas}>
              {EDUCACION.map(([nombre, valor]) => (
                <button key={nombre} type="button" aria-pressed={filtros.educacion === valor} onClick={() => alternar('educacion', valor)}>
                  {nombre}
                </button>
              ))}
            </div>
          </fieldset>
        </div>

        <fieldset className={estilos.grupo}>
          <legend>
            Ingreso del hogar
            <output>{filtros.quintil === SIN_FILTRO ? 'de menor a mayor' : `quintil ${QUINTILES[filtros.quintil]}`}</output>
          </legend>
          <div className={estilos.escalera} data-eligiendo={filtros.quintil !== SIN_FILTRO || undefined}>
            {QUINTILES.map((nombre, k) => (
              <button
                key={nombre}
                type="button"
                aria-pressed={filtros.quintil === k}
                aria-label={`Quintil ${nombre}`}
                style={{ '--alto': `${44 + k * 14}%` } as CSSProperties}
                onClick={() => alternar('quintil', k)}
              >
                <span>{nombre}</span>
              </button>
            ))}
          </div>
        </fieldset>

        {filtrando && (
          <button type="button" className={estilos.limpiar} onClick={() => setFiltros({ ...FILTROS_INICIALES, tamano: filtros.tamano, reduccion: filtros.reduccion })}>
            Quitar los filtros
          </button>
        )}
      </div>

      <footer className={estilos.pie}>
        {!sim.conexion?.demo && sim.fase === 'preparar' && (
          <div className={estilos.ejemplos}>
            <p>Preguntas con encuesta real para comparar</p>
            {CASOS_VALIDACION.map((caso) => (
              <button
                key={caso.corto}
                type="button"
                onClick={() => {
                  sim.fijar(sim.borradores[0].id, { texto: caso.texto, referencia: caso.referencia, documento: undefined, leido: undefined });
                  alCerrar();
                }}
              >
                {caso.corto}
              </button>
            ))}
          </div>
        )}
        <div className={estilos.vista}>
          <div className={estilos.tema} role="group" aria-label="Fondo">
            <button type="button" aria-pressed={!claro} onClick={() => claro && alCambiarTema()}>
              Oscuro
            </button>
            <button type="button" aria-pressed={claro} onClick={() => !claro && alCambiarTema()}>
              Claro
            </button>
          </div>
          <button
            type="button"
            className={estilos.ocultar}
            onClick={() => {
              alCerrar();
              alOcultar();
            }}
          >
            Solo el mapa <kbd>H</kbd>
          </button>
        </div>
      </footer>
    </aside>
  );
}
