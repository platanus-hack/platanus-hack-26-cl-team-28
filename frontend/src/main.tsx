import '@fontsource-variable/newsreader/opsz.css';
import '@fontsource-variable/newsreader/opsz-italic.css';
import '@fontsource-variable/hanken-grotesk/wght.css';
import '@fontsource-variable/shantell-sans/wght.css';
import '@fontsource-variable/bricolage-grotesque/standard.css';
import './estilos/tokens.css';
import './estilos/base.css';
import './enjambre/tema.css';
import { lazy, StrictMode, Suspense } from 'react';
import { createRoot } from 'react-dom/client';

// Hay dos diseños sobre el mismo dominio: `?d=1` abre el mapa ilustrado; sin parámetro, "Chile se abre".
const ilustrado = new URLSearchParams(location.search).get('d') === '1';
document.documentElement.dataset.diseno = ilustrado ? 'ilustrado' : 'enjambre';
// Cada diseño arma su propia población al cargarse: solo se carga el que se va a ver.
const Diseno = lazy(() =>
  ilustrado ? import('./App').then((m) => ({ default: m.App })) : import('./enjambre/AppEnjambre').then((m) => ({ default: m.AppEnjambre })),
);

createRoot(document.getElementById('raiz')!).render(
  <StrictMode>
    <Suspense fallback={null}>
      <Diseno />
    </Suspense>
  </StrictMode>,
);
