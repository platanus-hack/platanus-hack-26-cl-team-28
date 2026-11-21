/**
 * Chile se dibuja acostado: el norte queda a la izquierda, la cordillera arriba y el
 * Pacífico abajo, como se ve el país desde el mar. Así el país ocupa todo el ancho.
 */
export const LAT_NORTE = -17.0;
export const LAT_SUR = -56.4;
export const LON_ESTE = -66.0;
export const LON_OESTE = -76.2;
/** Exageración este-oeste: Chile real es demasiado angosto para pararse encima. Es un mapa ilustrado, no a escala. */
const ACHATADO = 1.15;

export const ANCHO_MUNDO = LAT_NORTE - LAT_SUR;
export const ALTO_MUNDO = (LON_ESTE - LON_OESTE) * ACHATADO;
/** Franja vertical que debe caber siempre en pantalla (del límite oriental a las islas del sur). */
export const ALTO_UTIL = 7.3 * (ACHATADO / 0.83);
export const CENTRO_Y = 4.65 * (ACHATADO / 0.83);

export function aMundo(lon: number, lat: number): [number, number] {
  return [LAT_NORTE - lat, (LON_ESTE - lon) * ACHATADO];
}

export function aGeografia(x: number, y: number): [number, number] {
  return [LON_ESTE - y / ACHATADO, LAT_NORTE - x];
}
