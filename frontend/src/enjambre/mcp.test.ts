import { describe, expect, it } from 'vitest';
import { comandoMcp, leerUrlMcp } from './mcp';

describe('leerUrlMcp', () => {
  it('sin variable no hay conexión que ofrecer', () => {
    expect(leerUrlMcp(undefined)).toBeNull();
    expect(leerUrlMcp('')).toBeNull();
    expect(leerUrlMcp('   ')).toBeNull();
  });

  it('acepta la dirección pública completa, con su ruta', () => {
    expect(leerUrlMcp(' https://mcp.ejemplo.cl/mcp ')).toBe('https://mcp.ejemplo.cl/mcp');
  });

  it('acepta HTTP solo hacia la propia máquina', () => {
    expect(leerUrlMcp('http://127.0.0.1:8788/mcp')).toBe('http://127.0.0.1:8788/mcp');
    expect(leerUrlMcp('http://localhost:8788/mcp')).toBe('http://localhost:8788/mcp');
    expect(leerUrlMcp('http://mcp.ejemplo.cl/mcp')).toBeNull();
  });

  it('descarta lo que no es una dirección', () => {
    expect(leerUrlMcp('<URL_PUBLICA_DEL_MCP>')).toBeNull();
    expect(leerUrlMcp('mcp.ejemplo.cl/mcp')).toBeNull();
    expect(leerUrlMcp('javascript:alert(1)')).toBeNull();
  });
});

describe('comandoMcp', () => {
  it('arma el comando de Claude Code con la dirección', () => {
    expect(comandoMcp('https://mcp.ejemplo.cl/mcp')).toBe('claude mcp add --transport http whatif-chile https://mcp.ejemplo.cl/mcp');
  });
});
