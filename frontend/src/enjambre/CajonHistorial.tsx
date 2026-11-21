import { useEffect, useRef, useState } from 'react';
import { PopupFlotante } from '../componentes/comunes/Popup';
import { formatear } from '../dominio/textos';
import { pedirHistorial } from '../vivo/api';
import { cuando, preguntaDe, repartoDe, textosDe, type EntradaHistorial } from '../vivo/historial';
import estilos from './CajonHistorial.module.css';

interface Props {
  abierto: boolean;
  /** Deja estos textos como las variantes por preguntar. Sin esto, el historial solo se lee. */
  alUsar?(textos: string[]): void;
  /** Vuelve a mostrar esa simulación en el mapa. Devuelve el problema si no se pudo, o null. */
  alVer?(id: string): Promise<string | null>;
  alCerrar(): void;
}

/**
 * Las simulaciones que ya se hicieron, de la más nueva a la más antigua: cuándo, qué se preguntó
 * y cómo quedó cada variante en la primera pregunta. Las guarda el motor, así que son las de
 * todos los que usan este sitio.
 */
export function CajonHistorial({ abierto, alUsar, alVer, alCerrar }: Props) {
  const caja = useRef<HTMLElement>(null);
  const [entradas, setEntradas] = useState<EntradaHistorial[] | null>(null);
  const [error, setError] = useState('');
  /** La simulación que se está trayendo del motor para verla, y la que no se pudo abrir. */
  const [abriendo, setAbriendo] = useState<string | null>(null);
  const [fallida, setFallida] = useState<{ id: string; problema: string } | null>(null);
  const ver = async (id: string) => {
    if (!alVer || abriendo) return;
    setAbriendo(id);
    setFallida(null);
    const problema = await alVer(id);
    setAbriendo(null);
    if (problema) setFallida({ id, problema });
  };

  useEffect(() => {
    const control = new AbortController();
    pedirHistorial(control.signal)
      .then(setEntradas)
      .catch((problema: Error) => problema.name !== 'AbortError' && setError(problema.message));
    return () => control.abort();
  }, []);

  useEffect(() => {
    if (!abierto) return;
    caja.current?.focus({ preventScroll: true });
    const tecla = (e: KeyboardEvent) => e.key === 'Escape' && alCerrar();
    const fuera = (e: PointerEvent) => {
      const destino = e.target;
      if (destino instanceof Element && !caja.current?.contains(destino) && !destino.closest('[aria-controls="cajon-historial"]')) alCerrar();
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

  return (
    <PopupFlotante as="aside" abierto={abierto} lateral ref={caja} tabIndex={-1} className={estilos.cajon} id="cajon-historial" aria-label="Historial de simulaciones">
      <header className={estilos.cabeza}>
        <h2>Historial</h2>
        <p>{entradas ? (entradas.length === 1 ? '1 simulación' : `${formatear(entradas.length)} simulaciones`) : error ? '' : 'Cargando'}</p>
        <button type="button" className={estilos.cerrar} onClick={alCerrar} aria-label="Cerrar">
          <svg viewBox="0 0 12 12" aria-hidden="true">
            <path d="M1.5 1.5l9 9M10.5 1.5l-9 9" />
          </svg>
        </button>
      </header>
      <div className={estilos.cuerpo}>
        {error && <p className={estilos.aviso}>No se pudo leer el historial: {error}</p>}
        {entradas?.length === 0 && <p className={estilos.aviso}>Todavía no hay simulaciones. Cuando termine una, queda aquí con su resultado.</p>}
        {entradas && entradas.length > 0 && (
          <ol className={estilos.lista}>
            {entradas.map((entrada) => {
              const textos = textosDe(entrada);
              const hora = cuando(entrada.hora);
              return (
                <li key={entrada.id + entrada.hora}>
                  <div className={estilos.cuando}>
                    <div className={estilos.hora}>
                      {((alVer && entrada.vista) || (alUsar && textos.length > 0)) && (
                        <div className={estilos.acciones}>
                          {alVer && entrada.vista && (
                            <button
                              type="button"
                              className={estilos.usar}
                              aria-label={`Ver la simulación de ${hora}`}
                              title="Ver esta simulación"
                              aria-busy={abriendo === entrada.id || undefined}
                              disabled={abriendo !== null}
                              onClick={() => void ver(entrada.id)}
                            >
                              <svg viewBox="0 0 24 24" aria-hidden="true">
                                <path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12Z" />
                                <circle cx="12" cy="12" r="2.75" />
                              </svg>
                            </button>
                          )}
                          {alUsar && textos.length > 0 && (
                            <button type="button" className={estilos.usar} aria-label={`Volver a preguntar por la simulación de ${hora}`} title="Volver a preguntar" onClick={() => alUsar(textos)}>
                              <svg viewBox="0 0 24 24" aria-hidden="true">
                                <path d="M5 10a7 7 0 1 1 1.2 6.2M5 5.5V10h4.5" />
                              </svg>
                            </button>
                          )}
                        </div>
                      )}
                      <time dateTime={entrada.hora}>{hora}</time>
                    </div>
                    <span>
                      {formatear(entrada.agentes)} agentes{entrada.completa ? '' : ' · detenida antes de terminar'}
                    </span>
                  </div>
                  {fallida?.id === entrada.id && (
                    <p className={estilos.falla} role="alert">
                      {fallida.problema}
                    </p>
                  )}
                  {entrada.casos.map((caso) => {
                    const reparto = repartoDe(caso);
                    return (
                      <div key={caso.letra} className={estilos.caso}>
                        <p className={estilos.pregunta}>
                          {entrada.casos.length > 1 && <b>{caso.letra}</b>}
                          <span title={preguntaDe(caso)}>{preguntaDe(caso)}</span>
                        </p>
                        {(caso.iteracion || (caso.documento && caso.texto)) && (
                          <p className={estilos.origen}>{caso.iteracion ? 'Escrita por el agente' : `Con el documento ${caso.documento}`}</p>
                        )}
                        <div className={estilos.barra} role="img" aria-label={`${reparto.contra} % en contra, ${reparto.indecisa} % sin decidir, ${reparto.favor} % a favor`}>
                          <i data-postura="contra" style={{ flexGrow: caso.contra }} />
                          <i data-postura="indecisa" style={{ flexGrow: caso.indecisa }} />
                          <i data-postura="favor" style={{ flexGrow: caso.favor }} />
                        </div>
                        <p className={estilos.resultado}>
                          <span data-postura="contra">{reparto.contra} % en contra</span>
                          <span data-postura="indecisa">{reparto.indecisa} % sin decidir</span>
                          <span data-postura="favor">{reparto.favor} % a favor</span>
                        </p>
                      </div>
                    );
                  })}
                </li>
              );
            })}
          </ol>
        )}
      </div>
    </PopupFlotante>
  );
}
