import { useEffect, useRef } from 'react';
import { Boton } from '../componentes/comunes/Boton';
import { PopupDialogo, PopupFlotante, type PopupHandle } from '../componentes/comunes/Popup';
import { ENCUESTA } from '../vivo/encuesta';
import estilos from './CajonEncuesta.module.css';

interface Props {
  abierto: boolean;
  alCerrar(): void;
}

const mayusculaInicial = (texto: string) => texto.charAt(0).toLocaleUpperCase('es-CL') + texto.slice(1);

/**
 * La encuesta que responde cada agente, para leerla: qué se pregunta, en qué orden y qué
 * significan el 1 y el 7 en cada pregunta. Es fija: no se edita. Un cajón a todo el alto, como
 * el de la muestra.
 */
export function CajonEncuesta({ abierto, alCerrar }: Props) {
  const caja = useRef<HTMLElement>(null);
  const porQue = useRef<PopupHandle>(null);
  const tituloPorQue = useRef<HTMLHeadingElement>(null);

  const abrirPorQue = () => {
    porQue.current?.showModal();
    tituloPorQue.current?.focus();
  };

  useEffect(() => {
    if (!abierto) return;
    caja.current?.focus({ preventScroll: true });
    // Con el diálogo abierto, Escape cierra solo el diálogo; el cajón sigue.
    const tecla = (e: KeyboardEvent) => e.key === 'Escape' && !porQue.current?.open && alCerrar();
    const fuera = (e: PointerEvent) => !caja.current?.contains(e.target as Node) && alCerrar();
    window.addEventListener('keydown', tecla);
    // En el siguiente ciclo: el clic que abrió el cajón no debe cerrarlo.
    const escucha = window.setTimeout(() => window.addEventListener('pointerdown', fuera), 0);
    return () => {
      window.clearTimeout(escucha);
      window.removeEventListener('keydown', tecla);
      window.removeEventListener('pointerdown', fuera);
    };
  }, [abierto, alCerrar]);

  return (
    <PopupFlotante as="aside" abierto={abierto} lateral ref={caja} tabIndex={-1} className={estilos.cajon} id="cajon-encuesta" aria-label="Encuesta">
      <header className={estilos.cabeza}>
        <div className={estilos.cuenta}>
          <span>ENCUESTA · {ENCUESTA.length} PREGUNTAS</span>
          <h2>Lo que preguntamos</h2>
        </div>
        <button type="button" className={estilos.cerrar} onClick={alCerrar} aria-label="Cerrar">
          <svg viewBox="0 0 12 12" aria-hidden="true">
            <path d="M2 2l8 8M10 2l-8 8" />
          </svg>
        </button>
        <button type="button" className={estilos.porQue} aria-haspopup="dialog" onClick={abrirPorQue}>
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <circle cx="12" cy="12" r="9" />
            <path d="M9.6 9.4a2.5 2.5 0 1 1 3.6 2.2c-.8.4-1.2.9-1.2 1.7M12 16.6v.1" />
          </svg>
          ¿Por qué preguntamos esto?
        </button>
      </header>

      <div className={estilos.cuerpo}>
        <ol className={estilos.preguntas}>
          {ENCUESTA.map((pregunta, k) => (
            <li key={pregunta.texto}>
              <span className={estilos.numero} aria-hidden="true">{k + 1}</span>
              <div className={estilos.pregunta}>
                <h3>{pregunta.nombre}</h3>
                <p>{pregunta.texto}</p>
                <div className={estilos.escala} aria-label="Escala de respuesta">
                  <div className={estilos.linea} aria-hidden="true"><span>1</span><i /><span>7</span></div>
                  <div className={estilos.extremos}>
                    <span><span className="solo-lectores">1: </span>{mayusculaInicial(pregunta.minimo)}</span>
                    <span><span className="solo-lectores">7: </span>{mayusculaInicial(pregunta.maximo)}</span>
                  </div>
                </div>
              </div>
            </li>
          ))}
        </ol>
      </div>

      <PopupDialogo ref={porQue} className={estilos.dialogo} aria-labelledby="titulo-por-que" aria-describedby="resumen-por-que">
        <div className={estilos.metodo}>
          <header>
            <h2 id="titulo-por-que" ref={tituloPorQue} tabIndex={-1}>¿Por qué preguntamos esto?</h2>
            <p id="resumen-por-que">Medimos la <strong>aceptabilidad</strong> de una propuesta, es decir, cómo la recibiría la gente antes de implementarla.</p>
          </header>

          <section>
            <h3>Qué cubren las cinco preguntas</h3>
            <p>El apoyo, la justicia, la confianza en la implementación, la efectividad esperada y cuánto afectaría la propuesta a cada persona. La encuesta sirve para evaluar leyes en trámite y ordenanzas en diseño.</p>
          </section>

          <section>
            <h3>Por qué usamos una escala de 1 a 7</h3>
            <p>Tomamos la escala de la Encuesta de Medición de Satisfacción Usuaria (MESU). Desde 2015, esta encuesta mide la satisfacción con los trámites del Estado como parte de un programa del BID y el Ministerio de Hacienda.</p>
            <div className={estilos.datoMesu}>
              <strong>65&nbsp;%</strong>
              <p>de los usuarios de las 78 instituciones participantes en la MESU 2024 evaluó su último trámite con nota 6 o 7.</p>
            </div>
          </section>
        </div>

        <div className={estilos.acciones}>
          <Boton variante="primario" onClick={() => porQue.current?.close()}>Entendido</Boton>
        </div>
      </PopupDialogo>
    </PopupFlotante>
  );
}
