/** Lo que el panel de conexión MCP ofrece para copiar. */

/** Petición de ejemplo para la sesión del cliente, sin las comillas con que se muestra. */
export const EJEMPLO_MCP = 'Usa What If Chile para simular con 10 agentes una propuesta para extender el subsidio al transporte público rural';

/**
 * La dirección pública del MCP tal como llega en `VITE_MCP_URL`: completa, con su ruta `/mcp`.
 * Solo vale una dirección que se pueda pegar en un cliente: HTTPS, o HTTP hacia la propia máquina
 * para probar. Sin ella el panel anuncia la conexión, pero no la ofrece.
 */
export function leerUrlMcp(valor: string | undefined): string | null {
  const texto = valor?.trim();
  if (!texto || !URL.canParse(texto)) return null;
  const url = new URL(texto);
  const local = url.hostname === 'localhost' || url.hostname === '127.0.0.1';
  return url.protocol === 'https:' || (url.protocol === 'http:' && local) ? url.href : null;
}

/** El comando que agrega el servidor a Claude Code. */
export function comandoMcp(url: string): string {
  return `claude mcp add --transport http whatif-chile ${url}`;
}
