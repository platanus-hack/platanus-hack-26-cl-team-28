/**
 * Los parámetros de la sociedad con que se elige a quiénes preguntar: región, género, trabajo,
 * posición política… Las claves, su orden y el de las opciones son los del motor
 * (backend/servidor/sociedad.py); aquí van los rótulos y cómo se dibuja cada uno.
 *
 * Un filtro es, por parámetro, la lista de opciones elegidas; sin lista no filtra. El retrato
 * de una población es, por parámetro, cuánta gente hay en cada opción entre quienes cumplen
 * los demás filtros: cada control muestra así cuánta gente suma o quita cada opción.
 */
import { EDAD_MINIMA, REGIONES } from '../dominio/catalogos';

export type Clave =
  | 'region'
  | 'genero'
  | 'educacion'
  | 'nacionalidad'
  | 'trabajo'
  | 'menores'
  | 'vivienda'
  | 'salud'
  | 'quintil'
  | 'politica'
  | 'gobierno'
  | 'voto'
  | 'confianza';

export type ClaveSeccion = 'territorio' | 'personas' | 'hogar' | 'opinion';

/** Filas con barra, una barra partida en dos, o columnas de una escala ordenada. */
export type Forma = 'filas' | 'partida' | 'columnas';

export interface Parametro {
  clave: Clave;
  rotulo: string;
  seccion: ClaveSeccion;
  forma: Forma;
  opciones: readonly string[];
  /** Rótulos más cortos, para las columnas y para las fichas de la cabeza. */
  cortos?: readonly string[];
  /** Con columnas: la opción que no es parte de la escala y va en una fila aparte. */
  aparte?: number;
}

export const SECCIONES: readonly { clave: ClaveSeccion; titulo: string; fuente: string }[] = [
  { clave: 'territorio', titulo: 'Territorio', fuente: 'Censo 2024' },
  { clave: 'personas', titulo: 'Personas', fuente: 'Censo 2024' },
  { clave: 'hogar', titulo: 'Hogar y trabajo', fuente: 'Censo 2024; previsión e ingreso imputados desde Casen' },
  { clave: 'opinion', titulo: 'Opinión', fuente: 'Imputada desde la encuesta CEP; solo mayores de 18 años' },
];

export const PARAMETROS: readonly Parametro[] = [
  { clave: 'region', rotulo: 'Región', seccion: 'territorio', forma: 'filas', opciones: REGIONES.map((r) => r.nombre), cortos: REGIONES.map((r) => r.corto) },
  { clave: 'genero', rotulo: 'Género', seccion: 'personas', forma: 'partida', opciones: ['Mujeres', 'Hombres'] },
  { clave: 'educacion', rotulo: 'Educación', seccion: 'personas', forma: 'filas', opciones: ['Básica o menos', 'Media', 'Superior'], cortos: ['Básica', 'Media', 'Superior'] },
  { clave: 'nacionalidad', rotulo: 'Nacionalidad', seccion: 'personas', forma: 'partida', opciones: ['Chilena', 'Extranjera'] },
  { clave: 'trabajo', rotulo: 'Situación laboral', seccion: 'hogar', forma: 'filas', opciones: ['Trabaja', 'Busca trabajo', 'No trabaja ni busca'] },
  { clave: 'menores', rotulo: 'Niños en el hogar', seccion: 'hogar', forma: 'partida', opciones: ['Con menores de 18', 'Sin menores'] },
  { clave: 'vivienda', rotulo: 'Vivienda', seccion: 'hogar', forma: 'filas', opciones: ['Propia', 'Arrendada', 'Cedida u otra'] },
  { clave: 'salud', rotulo: 'Previsión de salud', seccion: 'hogar', forma: 'filas', opciones: ['Fonasa A o B', 'Fonasa C o D', 'Isapre', 'Otra'] },
  {
    clave: 'quintil',
    rotulo: 'Ingreso del hogar',
    seccion: 'hogar',
    forma: 'columnas',
    opciones: ['Quintil I', 'Quintil II', 'Quintil III', 'Quintil IV', 'Quintil V'],
    cortos: ['I', 'II', 'III', 'IV', 'V'],
  },
  {
    clave: 'politica',
    rotulo: 'Posición política',
    seccion: 'opinion',
    forma: 'columnas',
    opciones: ['Izquierda', 'Centroizquierda', 'Centro', 'Centroderecha', 'Derecha', 'No se ubica'],
    cortos: ['Izq.', 'C. izq.', 'Centro', 'C. der.', 'Der.', 'No se ubica'],
    aparte: 5,
  },
  { clave: 'gobierno', rotulo: 'Aprobación del gobierno', seccion: 'opinion', forma: 'filas', opciones: ['Aprueba', 'Desaprueba', 'Ni aprueba ni desaprueba'] },
  { clave: 'voto', rotulo: 'Voto en la segunda vuelta de 2025', seccion: 'opinion', forma: 'filas', opciones: ['Jara', 'Kast', 'Blanco o nulo', 'No votó o no responde'] },
  { clave: 'confianza', rotulo: 'Confianza en el gobierno', seccion: 'opinion', forma: 'partida', opciones: ['Mucha o bastante', 'Poca o nada'] },
];

export const CLAVES: readonly Clave[] = PARAMETROS.map((p) => p.clave);
const POSICION = Object.fromEntries(CLAVES.map((clave, k) => [clave, k])) as Record<Clave, number>;
const SIN_DATO = -1;
/** El censo publica la edad con tope: 85 es «85 años o más», y ahí termina la escala. */
export const EDAD_TOPE = 85;
const EDADES = EDAD_TOPE - EDAD_MINIMA + 1;

export type Elegidos = Partial<Record<Clave, number[]>>;

export interface FiltrosVivo {
  /** Agentes que se van a consultar. */
  tamano: number;
  /** Clusterización: a cuántas personas representa cada agente. */
  reduccion: number;
  edadMin: number;
  edadMax: number;
  /** Las opciones elegidas en cada parámetro. Los que no filtran no aparecen. */
  elegidos: Elegidos;
}

/** Personas por opción de cada parámetro y, en `edad`, por cada edad desde la mínima. */
export type Retrato = Record<Clave | 'edad', number[]>;

/** Lo que se necesita de una persona para filtrarla y contarla. */
export interface Rasgos {
  /** Su opción en cada parámetro, en el orden de `CLAVES` (-1 si no tiene el dato). */
  s?: number[];
  edad: number;
  representa?: number;
}

export const filtrosDePartida = (tamano: number): FiltrosVivo => ({ tamano, reduccion: 10, edadMin: EDAD_MINIMA, edadMax: EDAD_TOPE, elegidos: {} });

/**
 * Toca una opción. En los parámetros de dos opciones la otra la reemplaza; en los demás se
 * suma a lo elegido. Tocarla de nuevo la quita, y con todas elegidas el parámetro deja de filtrar.
 */
export function alternar(filtros: FiltrosVivo, parametro: Parametro, opcion: number): FiltrosVivo {
  const antes = filtros.elegidos[parametro.clave] ?? [];
  let ahora: number[];
  if (antes.includes(opcion)) ahora = antes.filter((o) => o !== opcion);
  else if (parametro.opciones.length === 2) ahora = [opcion];
  else ahora = [...antes, opcion].sort((a, b) => a - b);
  const elegidos = { ...filtros.elegidos };
  if (ahora.length === 0 || ahora.length === parametro.opciones.length) delete elegidos[parametro.clave];
  else elegidos[parametro.clave] = ahora;
  return { ...filtros, elegidos };
}

export const filtraEdad = (filtros: FiltrosVivo): boolean => filtros.edadMin > EDAD_MINIMA || filtros.edadMax < EDAD_TOPE;

export const hayFiltros = (filtros: FiltrosVivo): boolean => filtraEdad(filtros) || Object.keys(filtros.elegidos).length > 0;

/** Deja de filtrar por un parámetro, o por la edad. */
export function quitar(filtros: FiltrosVivo, clave: Clave | 'edad'): FiltrosVivo {
  if (clave === 'edad') return { ...filtros, edadMin: EDAD_MINIMA, edadMax: EDAD_TOPE };
  const elegidos = { ...filtros.elegidos };
  delete elegidos[clave];
  return { ...filtros, elegidos };
}

export const sinFiltros = (filtros: FiltrosVivo): FiltrosVivo => ({ ...filtros, edadMin: EDAD_MINIMA, edadMax: EDAD_TOPE, elegidos: {} });

const anos = (valor: number) => (valor >= EDAD_TOPE ? `${EDAD_TOPE}+` : String(valor));

export const textoEdad = (filtros: FiltrosVivo): string => `${anos(filtros.edadMin)} a ${anos(filtros.edadMax)} años`;

/** Lo elegido en un parámetro, en pocas palabras: los nombres si son hasta `maximo`, o cuántas opciones. */
export function resumen(parametro: Parametro, elegidas: number[] | undefined, maximo = 2): string {
  if (!elegidas?.length) return '';
  const nombres = parametro.cortos ?? parametro.opciones;
  return elegidas.length <= maximo ? elegidas.map((o) => nombres[o]).join(', ') : `${elegidas.length} de ${parametro.opciones.length}`;
}

/** Los filtros puestos, en el orden del cajón: uno por parámetro y uno por la edad. */
export function activos(filtros: FiltrosVivo): { clave: Clave | 'edad'; rotulo: string; texto: string }[] {
  const lista: { clave: Clave | 'edad'; rotulo: string; texto: string }[] = [];
  for (const parametro of PARAMETROS) {
    const elegidas = filtros.elegidos[parametro.clave];
    if (!elegidas?.length) continue;
    const texto = parametro.clave === 'region' && elegidas.length > 2 ? `${elegidas.length} regiones` : resumen(parametro, elegidas);
    lista.push({ clave: parametro.clave, rotulo: parametro.rotulo, texto });
  }
  // La edad va donde está en el cajón: después del territorio.
  if (filtraEdad(filtros)) lista.splice(lista[0]?.clave === 'region' ? 1 : 0, 0, { clave: 'edad', rotulo: 'Edad', texto: textoEdad(filtros) });
  return lista;
}

/** Cuántos filtros hay puestos en una sección. */
export function activosEn(filtros: FiltrosVivo, seccion: ClaveSeccion): number {
  const propios = PARAMETROS.filter((p) => p.seccion === seccion && filtros.elegidos[p.clave]?.length).length;
  return propios + (seccion === 'personas' && filtraEdad(filtros) ? 1 : 0);
}

const enEdad = (edad: number, filtros: FiltrosVivo): boolean => edad >= filtros.edadMin && (edad <= filtros.edadMax || filtros.edadMax >= EDAD_TOPE);

/** ¿Cumple la persona todos los filtros? Sin sus rasgos solo se mira la edad. */
export function coincide(persona: Rasgos, filtros: FiltrosVivo): boolean {
  if (!enEdad(persona.edad, filtros)) return false;
  for (const clave of Object.keys(filtros.elegidos) as Clave[]) {
    if (!filtros.elegidos[clave]!.includes(persona.s?.[POSICION[clave]] ?? SIN_DATO)) return false;
  }
  return true;
}

export const retratoVacio = (): Retrato =>
  Object.fromEntries([...PARAMETROS.map((p) => [p.clave, p.opciones.map(() => 0)]), ['edad', new Array<number>(EDADES).fill(0)]]) as Retrato;

/**
 * El retrato de un grupo de personas, con la misma regla que el motor (`retrato_de` en
 * backend/servidor/sociedad.py): cada parámetro cuenta a quienes cumplen los demás filtros.
 */
export function retratoLocal(personas: Iterable<Rasgos>, filtros: FiltrosVivo): Retrato {
  const retrato = retratoVacio();
  const filtrados = Object.keys(filtros.elegidos) as Clave[];
  for (const persona of personas) {
    const fallas = filtrados.filter((clave) => !filtros.elegidos[clave]!.includes(persona.s?.[POSICION[clave]] ?? SIN_DATO));
    if (fallas.length > 1 || persona.edad < EDAD_MINIMA) continue;
    const peso = persona.representa ?? 1;
    if (!fallas.length) retrato.edad[Math.min(persona.edad, EDAD_TOPE) - EDAD_MINIMA] += peso;
    if (!enEdad(persona.edad, filtros)) continue;
    for (const clave of fallas.length ? fallas : CLAVES) {
      const opcion = persona.s?.[POSICION[clave]] ?? SIN_DATO;
      if (opcion >= 0) retrato[clave][opcion] += peso;
    }
  }
  return retrato;
}

/** El retrato que manda el motor, con la forma que espera la interfaz aunque falte algún parámetro. */
export function retratoDelMotor(remoto: Record<string, number[]> | undefined): Retrato | undefined {
  if (!remoto) return undefined;
  const retrato = retratoVacio();
  for (const clave of [...CLAVES, 'edad'] as (Clave | 'edad')[]) {
    if (remoto[clave]?.length === retrato[clave].length) retrato[clave] = remoto[clave];
  }
  return retrato;
}

/** ¿Hay datos de este parámetro en la población? Sin ellos no se ofrece. */
export const conDatos = (retrato: Retrato, clave: Clave): boolean => retrato[clave].some((personas) => personas > 0);

/**
 * Los rasgos de un agente en el orden de `CLAVES`. Del motor llegan en el orden que él declara
 * (`dimensiones`); sin eso (la demostración sin motor) se arman con lo que el agente trae a la vista.
 */
export function rasgosDe(
  agente: { region: number; genero: number; quintil: number; educacion: number; politica?: number; s?: number[] },
  dimensiones?: string[],
): number[] {
  if (dimensiones && agente.s) {
    const lugar = new Map(dimensiones.map((clave, k) => [clave, k]));
    return CLAVES.map((clave) => agente.s![lugar.get(clave) ?? -1] ?? SIN_DATO);
  }
  const propios: Partial<Record<Clave, number>> = {
    region: agente.region,
    genero: agente.genero <= 1 ? agente.genero : SIN_DATO,
    // El catálogo de la demostración tiene cinco niveles: de técnica superior en adelante es superior.
    educacion: Math.min(agente.educacion, 2),
    quintil: agente.quintil,
    politica: agente.politica ?? SIN_DATO,
  };
  return CLAVES.map((clave) => propios[clave] ?? SIN_DATO);
}

/** Los filtros como los pide el motor: la edad, el nivel y, por parámetro, las opciones elegidas. */
export function paraElMotor(filtros: FiltrosVivo): Record<string, number | number[]> {
  return { edadMin: filtros.edadMin, edadMax: filtros.edadMax, reduccion: filtros.reduccion, ...filtros.elegidos };
}

/** Qué parte del total es cada opción, en porcentaje entero. Sin nadie, todo en cero. */
export function partes(personas: number[]): number[] {
  const total = personas.reduce((suma, p) => suma + p, 0);
  return personas.map((p) => (total ? Math.round((p / total) * 100) : 0));
}
