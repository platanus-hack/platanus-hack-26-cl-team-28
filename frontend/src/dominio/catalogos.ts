/** Catálogos del dominio. Los pesos regionales son ilustrativos (aproximan la distribución de población). */
export interface Region {
  nombre: string;
  corto: string;
  /** Para los rótulos del mapa en el teléfono, donde el nombre corto no cabe. */
  abreviado: string;
  capitalLon: number;
  capitalLat: number;
  peso: number;
}

export const REGIONES: readonly Region[] = [
  { nombre: 'Arica y Parinacota', corto: 'Arica', abreviado: 'Arica', capitalLon: -70.31, capitalLat: -18.48, peso: 2 },
  { nombre: 'Tarapacá', corto: 'Tarapacá', abreviado: 'Tarap.', capitalLon: -70.13, capitalLat: -20.22, peso: 3 },
  { nombre: 'Antofagasta', corto: 'Antofagasta', abreviado: 'Antof.', capitalLon: -70.39, capitalLat: -23.65, peso: 5 },
  { nombre: 'Atacama', corto: 'Atacama', abreviado: 'Atac.', capitalLon: -70.33, capitalLat: -27.37, peso: 3 },
  { nombre: 'Coquimbo', corto: 'Coquimbo', abreviado: 'Coq.', capitalLon: -71.25, capitalLat: -29.92, peso: 6 },
  { nombre: 'Valparaíso', corto: 'Valparaíso', abreviado: 'Valpo.', capitalLon: -71.61, capitalLat: -33.04, peso: 11 },
  { nombre: 'Metropolitana', corto: 'RM', abreviado: 'RM', capitalLon: -70.64, capitalLat: -33.45, peso: 30 },
  { nombre: 'O’Higgins', corto: 'O’Higgins', abreviado: 'O’Hig.', capitalLon: -70.74, capitalLat: -34.17, peso: 7 },
  { nombre: 'Maule', corto: 'Maule', abreviado: 'Maule', capitalLon: -71.66, capitalLat: -35.43, peso: 8 },
  { nombre: 'Ñuble', corto: 'Ñuble', abreviado: 'Ñuble', capitalLon: -72.1, capitalLat: -36.61, peso: 4 },
  { nombre: 'Biobío', corto: 'Biobío', abreviado: 'Biobío', capitalLon: -73.05, capitalLat: -36.83, peso: 9 },
  { nombre: 'La Araucanía', corto: 'Araucanía', abreviado: 'Arauc.', capitalLon: -72.59, capitalLat: -38.74, peso: 6 },
  { nombre: 'Los Ríos', corto: 'Los Ríos', abreviado: 'L. Ríos', capitalLon: -73.24, capitalLat: -39.81, peso: 3 },
  { nombre: 'Los Lagos', corto: 'Los Lagos', abreviado: 'L. Lagos', capitalLon: -72.94, capitalLat: -41.47, peso: 6 },
  { nombre: 'Aysén', corto: 'Aysén', abreviado: 'Aysén', capitalLon: -72.07, capitalLat: -45.57, peso: 2 },
  { nombre: 'Magallanes', corto: 'Magallanes', abreviado: 'Magall.', capitalLon: -70.91, capitalLat: -53.16, peso: 2 },
];

export const GENEROS = ['Mujer', 'Hombre', 'No binario', 'Otro'] as const;
export const QUINTILES = ['Quintil I', 'Quintil II', 'Quintil III', 'Quintil IV', 'Quintil V'] as const;
export const EDUCACION = ['Básica o inferior', 'Media', 'Técnica superior', 'Universitaria', 'Posgrado'] as const;
export const POLITICA = [
  'Izquierda',
  'Centroizquierda',
  'Centro',
  'Centroderecha',
  'Derecha',
  'Sin identificación',
] as const;

export const ACCIONES = [
  'No haría nada',
  'Lo conversaría con su entorno',
  'Firmaría una petición',
  'Cambiaría su voto',
  'Saldría a manifestarse',
] as const;

/** Desde este índice de ACCIONES se considera que la persona se moviliza. */
export const PRIMERA_ACCION_MOVILIZADA = 2;

export const RAZONES = [
  'el costo de vida',
  'el empleo y los ingresos',
  'el medio ambiente',
  'la confianza en el Estado',
  'la justicia entre regiones',
  'que le afecta poco',
] as const;

export const TAMANOS = [10_000, 50_000, 100_000, 200_000] as const;
/** Se simula desde los 14 años. */
export const EDAD_MINIMA = 14;
export const EDAD_MAXIMA = 90;
/** Perfiles sintéticos disponibles en el prototipo. */
export const UNIVERSO = 480_000;
export const MAXIMO_CASOS = 6;
export const MINIMO_CASOS = 2;
