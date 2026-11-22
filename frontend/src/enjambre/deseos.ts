export interface Deseo {
  frase: string;
  /** Quién lo firma, en vez de la descripción de la persona («Mujer, 34»). */
  firma?: string;
  /** Comuna desde donde se dice: el globo sale junto a alguien de ahí. Sin ella, de cualquier parte. */
  comuna?: string;
  /** En qué lugar de cada vuelta se dice, contando desde 1. Sin él, donde caiga al barajar. */
  puesto?: number;
}

/**
 * Políticas que a la gente le gustaría ver. Son frases prehechas, de ambiente: no las responde el
 * modelo ni dependen de la propuesta que se está encuestando.
 */
export const DESEOS: readonly Deseo[] = [
  { frase: 'Ojalá hubiera más especialistas en los consultorios, sin esperar meses.' },
  { frase: 'Me gustaría ver pensiones que alcancen para llegar a fin de mes.' },
  { frase: 'Quiero más seguridad en mi barrio, poder caminar sin miedo de noche.' },
  { frase: 'Que arrendar o comprar una casa no se lleve medio sueldo.' },
  { frase: 'Me gustaría que el transporte en regiones funcionara tan bien como en Santiago.' },
  { frase: 'Ojalá apoyaran más a las pymes, que son las que dan pega.' },
  { frase: 'Ojalá hubieran hackatones todas las semanas 🍌', firma: 'JAPS', comuna: 'Las Condes', puesto: 2 },
];

/** Si un nombre de comuna es el mismo que otro, sin fijarse en mayúsculas ni tildes. */
export function mismaComuna(a: string, b: string): boolean {
  const llano = (texto: string) => texto.normalize('NFD').replace(/\p{Diacritic}/gu, '').trim().toLowerCase();
  return llano(a) === llano(b);
}

/**
 * Reparte los deseos barajados: no repite ninguno hasta haberlos dicho todos, ni empieza una
 * vuelta con el que cerró la anterior. Los que tienen `puesto` salen siempre en ese lugar de la vuelta.
 */
export function bolsaDeDeseos(azar: () => number = Math.random, deseos: readonly Deseo[] = DESEOS): () => Deseo {
  let quedan: Deseo[] = [];
  let ultimo: Deseo | undefined;
  return () => {
    if (!quedan.length) {
      const orden = deseos.filter((d) => !d.puesto);
      for (let i = orden.length - 1; i > 0; i--) {
        const j = Math.floor(azar() * (i + 1));
        [orden[i], orden[j]] = [orden[j], orden[i]];
      }
      // Si la vuelta iba a empezar con el último que se dijo, ese se va al final.
      if (orden.length > 1 && orden[0] === ultimo) orden.push(orden.shift()!);
      const fijos = deseos.filter((d) => d.puesto).sort((a, b) => a.puesto! - b.puesto!);
      for (const fijo of fijos) orden.splice(Math.min(orden.length, fijo.puesto! - 1), 0, fijo);
      quedan = orden.reverse();
    }
    ultimo = quedan.pop()!;
    return ultimo;
  };
}
