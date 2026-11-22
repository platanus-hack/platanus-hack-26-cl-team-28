/**
 * La dirección de la página dice qué se está mirando, para que atrás y adelante del navegador
 * funcionen y un enlace (o recargar) vuelva al mismo lugar:
 *
 *   /                               preparar una consulta
 *   /simulacion/<id>                el mapa con el resultado de esa simulación
 *   /simulacion/<id>/proceso        su proceso
 *   /simulacion/<id>/analisis       su análisis por grupos
 *
 * El id es el de la corrida en el motor, el mismo con que queda en el historial.
 */
export type Vista = 'mapa' | 'proceso' | 'analisis';

export interface Ruta {
  id: string | null;
  vista: Vista;
}

const FORMA = /^\/simulacion\/([0-9a-f]{6,32})(?:\/(proceso|analisis))?\/?$/i;

/** Lo que pide una dirección; cualquier otra cosa es la portada. */
export function leerRuta(camino: string): Ruta {
  const partes = FORMA.exec(camino);
  if (!partes) return { id: null, vista: 'mapa' };
  return { id: partes[1].toLowerCase(), vista: (partes[2]?.toLowerCase() as Vista | undefined) ?? 'mapa' };
}

export function caminoDe({ id, vista }: Ruta): string {
  if (!id) return '/';
  return `/simulacion/${id}${vista === 'mapa' ? '' : `/${vista}`}`;
}
