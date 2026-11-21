import { ACCIONES, EDUCACION, GENEROS, POLITICA, QUINTILES, RAZONES, REGIONES } from './catalogos';
import type { Persona, Respuesta } from './tipos';

const numero = new Intl.NumberFormat('es-CL', { maximumFractionDigits: 0 });

export const formatear = (valor: number): string => numero.format(valor);

export function letraDe(indice: number): string {
  return String.fromCharCode(65 + indice);
}

export function describirPersona(persona: Persona): string {
  const edad = persona.edad >= 90 ? '90 años o más' : `${persona.edad} años`;
  return `${GENEROS[persona.genero]}, ${edad}`;
}

export function detallarPersona(persona: Persona): string {
  return [REGIONES[persona.region].nombre, QUINTILES[persona.quintil], `Educación ${EDUCACION[persona.educacion].toLowerCase()}`, POLITICA[persona.politica]].join(' · ');
}

const AFECTA_POCO = RAZONES.length - 1;

/** Une una preposición con una frase que empieza con artículo: "de" + "el costo" da "del costo". */
function unir(preposicion: 'de', frase: string): string {
  return frase.startsWith('el ') ? `del ${frase.slice(3)}` : `${preposicion} ${frase}`;
}

/** Frase ilustrativa en primera persona a partir de la postura y el motivo. */
export function vozDe(respuesta: Respuesta): string {
  const razon = RAZONES[respuesta.razon];
  const poco = respuesta.razon === AFECTA_POCO;
  if (respuesta.postura === 'favor') return poco ? 'Estoy de acuerdo, aunque me afecta poco.' : `Estoy de acuerdo. Para mí pesa ${razon}.`;
  if (respuesta.postura === 'contra') return poco ? 'No me convence, aunque me afecta poco.' : `No me convence. Me preocupa ${razon}.`;
  return poco ? 'No lo tengo claro. Me afecta poco.' : `No lo tengo claro. Depende ${unir('de', razon)}.`;
}

export function accionDe(respuesta: Respuesta): string {
  return ACCIONES[respuesta.accion];
}
