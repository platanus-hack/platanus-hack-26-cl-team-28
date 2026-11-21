import type { Colores } from './capaMapa';
import type { Tintas } from './personajes';

/** Lee los tokens de `tokens.css`: el lienzo usa los mismos valores que el resto de la interfaz. */
export function leerTokens(): Colores & Tintas {
  const estilo = getComputedStyle(document.documentElement);
  const v = (nombre: string) => estilo.getPropertyValue(nombre).trim();
  return {
    mar: v('--mar'),
    marTrazo: v('--mar-trazo'),
    tierra: v('--tierra'),
    vecino: v('--vecino'),
    vecinoBorde: v('--vecino-borde'),
    regionBorde: v('--region-borde'),
    cordillera: v('--cordillera'),
    costaClara: v('--costa-clara'),
    sombra: v('--sombra-figura'),
    tinta: v('--tinta'),
    tintaSuave: v('--tinta-suave'),
    papel: v('--papel'),
    favor: v('--favor'),
    contra: v('--contra'),
    indecisa: v('--indecisa'),
    pasteles: [1, 2, 3, 4, 5, 6].map((n) => v(`--pastel-${n}`)),
    rubor: v('--rubor'),
    brote: v('--brote'),
    ojo: v('--ojo'),
    fuenteUi: v('--fuente-ui'),
    fuenteMano: v('--fuente-mano'),
  };
}
