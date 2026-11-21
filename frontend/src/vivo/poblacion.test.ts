import { describe, expect, it } from 'vitest';
import { crearAzar } from '../dominio/azar';
import { dentro } from '../dominio/poblacion';
import { cargarComunas, dentroDe, REGIONES_GEO, type ComunaGeo } from '../mapa/geografia';
import type { AgenteRemoto } from './api';
import { lugarEnComuna, poblacionDeAgentes } from './poblacion';

const agente = (id: string, region: number, cod_comuna?: number): AgenteRemoto => ({
  i: 0,
  id,
  region,
  comuna: '',
  cod_comuna,
  lon: 0,
  lat: 0,
  edad: 40,
  genero: 0,
  quintil: 2,
  educacion: 1,
  atributos: { Zona: 'Urbana' },
});

describe('ubicación de los puntos', () => {
  it('cae uniforme dentro de la comuna y fuera de sus huecos', () => {
    // Un cuadrado de 2 × 2 con un hueco de 1 × 1 al centro.
    const comuna: ComunaGeo = {
      region: 0,
      anillos: [
        [[0, 0], [2, 0], [2, 2], [0, 2]],
        [[0.5, 0.5], [1.5, 0.5], [1.5, 1.5], [0.5, 1.5]],
      ],
      interior: [0.25, 0.25],
    };
    const azar = crearAzar(7);
    for (let k = 0; k < 500; k++) {
      const [lon, lat] = lugarEnComuna(comuna, azar);
      expect(dentroDe(lon, lat, comuna.anillos)).toBe(true);
    }
  });

  it('en zona urbana cae dentro de su ciudad; en zona rural, fuera de ella', async () => {
    const comunas = await cargarComunas();
    // Lo Barnechea: una ciudad chica en una comuna que llega hasta la cordillera.
    const barnechea = comunas[13115];
    const urbanas = barnechea.urbano!;
    expect(urbanas.length).toBeGreaterThan(0);
    const azar = crearAzar(3);
    for (let k = 0; k < 200; k++) {
      const [lon, lat] = lugarEnComuna(barnechea, azar, 'urbana');
      expect(urbanas.some((z) => dentroDe(lon, lat, z.anillos))).toBe(true);
      const [rlon, rlat] = lugarEnComuna(barnechea, azar, 'rural');
      expect(dentroDe(rlon, rlat, barnechea.anillos)).toBe(true);
      expect(urbanas.some((z) => dentroDe(rlon, rlat, z.anillos))).toBe(false);
    }
  });

  it('sin anillos usa el punto interior', () => {
    expect(lugarEnComuna({ region: 5, anillos: [], interior: [-78.8, -33.6] }, crearAzar(1))).toEqual([-78.8, -33.6]);
  });

  it('con la cartografía real, cada punto queda en su comuna; sin comuna, en su región', async () => {
    const comunas = await cargarComunas();
    expect(Object.keys(comunas).length).toBeGreaterThan(340);
    // Santiago, Puente Alto, Arica, Natales (fiordos) y Juan Fernández (sin anillos dibujables).
    const agentes = [13101, 13201, 15101, 12401, 5104].map((codigo) => agente(`a${codigo}`, comunas[codigo].region, codigo));
    const puntos = poblacionDeAgentes(agentes, 40, REGIONES_GEO, comunas);
    for (const punto of puntos) {
      const codigo = agentes.find((a) => a.region === punto.region && punto.clave?.startsWith(a.id + '#'))!.cod_comuna!;
      const comuna = comunas[codigo];
      if (comuna.anillos.length) expect(dentroDe(punto.lon, punto.lat, comuna.anillos)).toBe(true);
      else expect([punto.lon, punto.lat]).toEqual(comuna.interior);
    }
    const suelto = poblacionDeAgentes([agente('sin-comuna', 6)], 20, REGIONES_GEO, comunas);
    for (const punto of suelto) expect(REGIONES_GEO[6].some((anillo) => dentro(punto.lon, punto.lat, anillo))).toBe(true);
  });
});
