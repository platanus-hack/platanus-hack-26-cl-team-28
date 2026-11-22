import { useEffect, useRef, useState, type ReactNode } from 'react';
import { Boton } from '../componentes/comunes/Boton';
import { PopupDialogo, type PopupHandle } from '../componentes/comunes/Popup';
import estilos from './ConexionMcp.module.css';
import { comandoMcp, EJEMPLO_MCP, leerUrlMcp } from './mcp';

/** Se define al compilar, cuando el servicio público ya está desplegado y su conexión comprobada. */
const URL_MCP = leerUrlMcp(import.meta.env.VITE_MCP_URL as string | undefined);

/** Cuánto dura a la vista el resultado de copiar. */
const AVISO_MS = 2400;

type Copia = { clave: string; hecho: boolean };

/** El botón MCP y su panel: cómo conectar un cliente a What If Chile. */
export function ConexionMcp() {
  const panel = useRef<PopupHandle>(null);
  const espera = useRef<number | undefined>(undefined);
  const [copia, setCopia] = useState<Copia | null>(null);

  useEffect(() => () => window.clearTimeout(espera.current), []);

  const copiar = async (clave: string, texto: string, bloque: HTMLElement) => {
    let hecho = true;
    try {
      await navigator.clipboard.writeText(texto);
    } catch {
      // Sin permiso o sin contexto seguro: el texto queda seleccionado para copiarlo a mano.
      hecho = false;
      getSelection()?.selectAllChildren(bloque);
    }
    setCopia({ clave, hecho });
    window.clearTimeout(espera.current);
    espera.current = window.setTimeout(() => setCopia(null), AVISO_MS);
  };

  const copiable = (clave: string, nombre: string, texto: string, contenido: ReactNode = texto) => {
    const hecho = copia?.clave === clave && copia.hecho;
    return (
      <>
        <div className={estilos.copiable}>
          <div className={estilos.texto}>{contenido}</div>
          <button
            type="button"
            className={estilos.copiar}
            aria-label={`Copiar ${nombre}`}
            data-hecho={hecho || undefined}
            onClick={(e) => void copiar(clave, texto, e.currentTarget.previousElementSibling as HTMLElement)}
          >
            {hecho ? (
              <svg viewBox="0 0 16 16" aria-hidden="true"><path d="m3.5 8.5 3 3 6-7" /></svg>
            ) : (
              <svg viewBox="0 0 16 16" aria-hidden="true"><rect x="5.5" y="5.5" width="8" height="8" rx="1.5" /><path d="M10.5 3.5v-.25a.75.75 0 0 0-.75-.75h-6.5a.75.75 0 0 0-.75.75v6.5c0 .41.34.75.75.75h.25" /></svg>
            )}
            {hecho ? 'Copiado' : 'Copiar'}
          </button>
        </div>
        {copia?.clave === clave && !copia.hecho && <p className={estilos.falla}>No se pudo copiar. El texto quedó seleccionado para copiarlo a mano.</p>}
      </>
    );
  };

  return (
    <>
      <Boton variante="secundario" aria-label="Conectar por MCP" aria-haspopup="dialog" onClick={() => panel.current?.showModal()}>
        MCP
      </Boton>
      <PopupDialogo ref={panel} className={estilos.panel} aria-labelledby="titulo-mcp" aria-describedby="descripcion-mcp">
        <div className={estilos.cabecera}>
          <h2 id="titulo-mcp">Conecta What If Chile a Claude Code</h2>
          <button type="button" className={estilos.cerrar} aria-label="Cerrar" onClick={() => panel.current?.close()}>
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m6 6 12 12M18 6 6 18" /></svg>
          </button>
        </div>
        <p id="descripcion-mcp" className={estilos.bajada}>
          Simula propuestas desde tu sesión de Claude Code. La inferencia corre con la cuenta o el proveedor que esa sesión ya usa: no compartes
          ninguna clave ni token.
        </p>

        {URL_MCP ? (
          <ol className={estilos.pasos} role="list">
            <li>
              <span aria-hidden="true">1</span>
              <p>Abre Claude Code con tu sesión habitual.</p>
            </li>
            <li>
              <span aria-hidden="true">2</span>
              <p>Copia y ejecuta el comando de conexión.</p>
              {copiable('comando', 'el comando', comandoMcp(URL_MCP), <code>{comandoMcp(URL_MCP)}</code>)}
            </li>
            <li>
              <span aria-hidden="true">3</span>
              <p>
                Escribe <code>/mcp</code> para comprobar que quedó conectado.
              </p>
            </li>
          </ol>
        ) : (
          <div className={estilos.pronto}>
            <strong>Conexión pública próximamente</strong>
            <p>El servicio público todavía no está desplegado. Cuando lo esté, aquí vas a encontrar el comando y la dirección para conectarte.</p>
          </div>
        )}

        <section className={estilos.seccion} aria-labelledby="titulo-mcp-prueba">
          <h3 id="titulo-mcp-prueba">Prueba una simulación</h3>
          <p>Con la conexión hecha, pide algo como esto:</p>
          {copiable('ejemplo', 'el ejemplo', EJEMPLO_MCP, `«${EJEMPLO_MCP}»`)}
          <p>El resultado se consulta desde tu cliente. Estas corridas se guardan en el historial del servicio MCP y no aparecen en el de esta web.</p>
        </section>

        <section className={estilos.seccion} aria-labelledby="titulo-mcp-otros">
          <h3 id="titulo-mcp-otros">Otros clientes MCP</h3>
          {URL_MCP && copiable('url', 'la dirección', URL_MCP, <code>{URL_MCP}</code>)}
          <p>
            El transporte es Streamable HTTP. Para completar una simulación, el cliente tiene que poder resolver los lotes con su modelo y devolver
            los resultados al servidor.
          </p>
        </section>

        <p className="solo-lectores" role="status">
          {copia && (copia.hecho ? 'Copiado al portapapeles.' : 'No se pudo copiar. El texto quedó seleccionado para copiarlo a mano.')}
        </p>
      </PopupDialogo>
    </>
  );
}
