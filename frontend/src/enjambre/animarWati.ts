/** Al interrumpir un gesto, el siguiente continúa desde la postura que se ve en ese instante. */
export function animarWati(figura: HTMLElement, transformaciones: Keyframe[], duracion: number) {
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  const transformacionActual = getComputedStyle(figura).transform;
  figura.getAnimations().forEach((animacion) => animacion.cancel());
  figura.animate([{ transform: transformacionActual }, ...transformaciones], { duration: duracion, easing: 'ease-in-out' });
}

export function rebotarWati(figura: HTMLElement) {
  animarWati(figura, [
    { transform: 'scale(1.24, 0.68)', offset: 0.28 },
    { transform: 'scale(0.9, 1.12)', offset: 0.65 },
    { transform: 'scale(1, 1)' },
  ], 500);
}
