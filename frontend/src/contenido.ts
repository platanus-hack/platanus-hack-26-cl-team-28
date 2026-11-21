/** Textos de la interfaz. Los datos de dominio viven en `dominio/`. */
export const MARCA = 'Simulaciones';
export const PASOS = ['Preparar', 'Preguntar', 'Comparar'] as const;
export const AVISO_DEMO = { corto: 'Datos de demostración', largo: 'Prototipo con datos de demostración' };
export const NOTA_DEMO =
  'Las respuestas de esta versión se generan en el navegador para probar la interfaz. Se reemplazan al conectar el motor de simulación.';

export const CASOS_INICIALES = [
  'Mantener el impuesto específico a los combustibles',
  'Eliminar el impuesto específico a los combustibles',
];

export const PREPARAR = {
  titular: '¿Cómo respondería Chile?',
  bajada: 'Escribe una política pública y sus variantes. Una población simulada responde qué opina y qué haría.',
  casos: 'Qué se pregunta',
  casosAyuda: 'Cada variante se pregunta a las mismas personas.',
  agregar: 'Agregar otra variante',
  marcador: 'Describe una variante de la política',
  muestra: 'A quiénes',
  muestraAyuda: 'Los filtros dejan en el mapa solo a quienes entran en la muestra.',
  tamano: 'Tamaño de la muestra',
  limpiar: 'Limpiar filtros',
  faltanCasos: 'Escribe al menos dos variantes para comparar.',
  sinPersonas: 'Ningún perfil coincide con los filtros.',
  figuras: 'Las figuras grandes reúnen a más gente. Acércate para verlas una a una.',
};

export const POSTURA_TEXTO = { favor: 'a favor', indecisa: 'indecisas', contra: 'en contra' } as const;
export const POSTURA_TITULO = { favor: 'A favor', indecisa: 'Indecisa', contra: 'En contra' } as const;

export const RESULTADOS = {
  franja: 'A favor por región, de norte a sur',
  franjaAyuda: 'Elige una región para acercar el mapa',
  casos: 'Variantes comparadas',
  acciones: 'Qué haría la gente',
  voces: 'Voces de la muestra',
  otrasVoces: 'Otras voces',
  notaVoces: 'Frases ilustrativas, armadas con la postura y el motivo de cada perfil.',
  editar: 'Cambiar la pregunta',
  verTodo: 'Ver todo Chile',
};

export const MAPA = {
  descripcion:
    'Mapa de Chile dibujado con el norte a la izquierda. Cada figura es un grupo de personas simuladas; las más grandes reúnen a más gente. Usa las flechas para recorrerlo y las teclas más y menos para acercarte. Los mismos resultados están en las tablas de más abajo.',
  orientacion: 'Chile visto desde el Pacífico',
  arrastre: 'Acércate con el más',
  acercar: 'Acercar',
  alejar: 'Alejar',
  restablecer: 'Ver todo Chile',
};
