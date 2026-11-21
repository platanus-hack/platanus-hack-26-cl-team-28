/**
 * Políticas con encuesta real publicada, para comparar lo que responden los agentes con lo que
 * respondió la gente. Cifras tomadas de los informes de Cadem Plaza Pública citados en `url`.
 */
export interface Referencia {
  fuente: string;
  fecha: string;
  favor: number;
  contra: number;
  pregunta: string;
  url: string;
}

export interface CasoValidacion {
  corto: string;
  texto: string;
  referencia: Referencia;
}

export const CASOS_VALIDACION: CasoValidacion[] = [
  {
    corto: 'Rebaja del TAG',
    texto:
      'El Gobierno acordó rebajar entre 10 % y 25 % las tarifas del TAG de Autopista Central desde enero de 2027. A cambio, la concesión de la autopista se extiende 20 meses.',
    referencia: {
      fuente: 'Cadem Plaza Pública 698',
      fecha: 'octubre de 2026',
      favor: 55,
      contra: 40,
      pregunta: '¿Ud. está de acuerdo o en desacuerdo con esta decisión?',
      url: 'https://cadem.cl/wp-content/uploads/2026/10/Track-PP-698-Octubre-S3-M1-VF.pdf',
    },
  },
  {
    corto: 'Rebaja del diésel',
    texto:
      'Para terminar el paro de camioneros, el Gobierno se comprometió a rebajar el diésel en $142 por litro y congelar alzas de combustibles hasta marzo de 2027.',
    referencia: {
      fuente: 'Cadem Plaza Pública 704',
      fecha: 'noviembre de 2026',
      favor: 66,
      contra: 26,
      pregunta: '¿Usted está de acuerdo o en desacuerdo con las medidas que el Gobierno comprometió?',
      url: 'https://cadem.cl/wp-content/uploads/2026/11/Track-PP-704-Noviembre-S2-M1-VF.pdf',
    },
  },
  {
    corto: 'Condena en casa',
    texto: 'Se propone que las personas condenadas que tienen una enfermedad terminal puedan terminar de cumplir su condena en su hogar.',
    referencia: {
      fuente: 'Cadem Plaza Pública 698',
      fecha: 'octubre de 2026',
      favor: 33,
      contra: 59,
      pregunta: '¿Ud. está de acuerdo o en desacuerdo con que las personas condenadas que padecen una enfermedad terminal puedan terminar de cumplir su condena en su hogar?',
      url: 'https://cadem.cl/wp-content/uploads/2026/10/Track-PP-698-Octubre-S3-M1-VF.pdf',
    },
  },
];
