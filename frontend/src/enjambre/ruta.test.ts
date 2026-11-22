import { describe, expect, it } from 'vitest';
import { caminoDe, leerRuta } from './ruta';

describe('dirección de la página', () => {
  it('lee la simulación y la vista', () => {
    expect(leerRuta('/')).toEqual({ id: null, vista: 'mapa' });
    expect(leerRuta('/simulacion/3fa9c01b2e4d')).toEqual({ id: '3fa9c01b2e4d', vista: 'mapa' });
    expect(leerRuta('/simulacion/3fa9c01b2e4d/proceso')).toEqual({ id: '3fa9c01b2e4d', vista: 'proceso' });
    expect(leerRuta('/simulacion/3FA9C01B2E4D/analisis/')).toEqual({ id: '3fa9c01b2e4d', vista: 'analisis' });
  });

  it('cualquier otra dirección es la portada', () => {
    expect(leerRuta('/simulacion/')).toEqual({ id: null, vista: 'mapa' });
    expect(leerRuta('/simulacion/no-es-un-id')).toEqual({ id: null, vista: 'mapa' });
    expect(leerRuta('/simulacion/3fa9c01b2e4d/otra')).toEqual({ id: null, vista: 'mapa' });
    expect(leerRuta('/algo')).toEqual({ id: null, vista: 'mapa' });
  });

  it('arma la dirección de vuelta', () => {
    for (const camino of ['/', '/simulacion/3fa9c01b2e4d', '/simulacion/3fa9c01b2e4d/proceso', '/simulacion/3fa9c01b2e4d/analisis']) {
      expect(caminoDe(leerRuta(camino))).toBe(camino);
    }
    expect(caminoDe({ id: null, vista: 'proceso' })).toBe('/');
  });
});
