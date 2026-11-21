/**
 * Chile de pie, con el norte arriba. El país real es diez veces más largo que ancho, así que
 * el mapa lo ensancha de este a oeste para que la gente quepa encima: es un mapa ilustrado,
 * no a escala.
 */
export const LAT_NORTE = -17.0;
export const LAT_SUR = -56.4;
export const LON_ESTE = -66.0;
export const LON_OESTE = -76.2;
const ENSANCHE = 2.4;

export const ANCHO_MUNDO = (LON_ESTE - LON_OESTE) * ENSANCHE;
export const ALTO_MUNDO = LAT_NORTE - LAT_SUR;
/** Franja horizontal que debe caber siempre en pantalla: de las islas del sur al límite oriental. */
export const ANCHO_UTIL = 9.4 * ENSANCHE;
export const CENTRO_X = (-71.2 - LON_OESTE) * ENSANCHE;
export const CENTRO_Y = ALTO_MUNDO / 2;

export function aMundo(lon: number, lat: number): [number, number] {
  return [(lon - LON_OESTE) * ENSANCHE, LAT_NORTE - lat];
}

export function aGeografia(x: number, y: number): [number, number] {
  return [x / ENSANCHE + LON_OESTE, LAT_NORTE - y];
}
