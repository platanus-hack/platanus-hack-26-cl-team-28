import { useEffect, useRef, useState } from 'react';
import { Boton } from '../componentes/comunes/Boton';
import { PopupDialogo, type PopupHandle } from '../componentes/comunes/Popup';
import { letraDe } from '../dominio/textos';
import type { Borrador } from '../estado/useBorradores';
import { orientarPreguntas } from '../vivo/api';
import { MAXIMO_VARIANTES, type EnVivo } from '../vivo/useEnVivo';
import { FiguraWati } from './FiguraWati';
import { separarPropuestas } from './orientacion';
import estilos from './GuiaPreguntas.module.css';

const EJEMPLO_PROPUESTA = 'Para terminar el paro de camioneros, el Gobierno se comprometió a rebajar el diésel en $142 por litro y congelar alzas de combustibles hasta marzo de 2027.';

export function Bienvenida() {
  const popup = useRef<PopupHandle>(null);
  useEffect(() => {
    const clave = 'whatif-chile:bienvenida-vista';
    try {
      if (localStorage.getItem(clave)) return;
    } catch { /* El navegador puede restringir el almacenamiento. */ }
    popup.current?.showModal();
    try {
      localStorage.setItem(clave, '1');
    } catch { /* La bienvenida también funciona sin persistencia. */ }
  }, []);
  return (
    <PopupDialogo ref={popup} className={estilos.panel} aria-labelledby="titulo-bienvenida" aria-describedby="descripcion-bienvenida">
      <div className={estilos.marca}>
        <span>Antes de preguntar · What If Chile</span>
        <button type="button" className={estilos.cerrar} aria-label="Cerrar bienvenida" onClick={() => popup.current?.close()}>×</button>
      </div>
      <div className={estilos.watis} aria-hidden="true">
        <FiguraWati estado="contra" rasgos={{ semilla: 3, variante: 2, tono: 0 }} alto={64} />
        <FiguraWati estado="indecisa" rasgos={{ semilla: 6, variante: 0, tono: 0 }} alto={64} />
        <FiguraWati estado="favor" rasgos={{ semilla: 9, variante: 1, tono: 0 }} alto={80} />
      </div>
      <h2 id="titulo-bienvenida">Una propuesta.<br />Muchas posturas.</h2>
      <p id="descripcion-bienvenida">What If Chile simula el apoyo y rechazo a una <strong>política pública</strong>: qué porcentaje de los agentes la apoya, la rechaza o queda indeciso.</p>
      <div className={estilos.ejemplo}>
        <span>Describe la medida y a quién afecta</span>
        <blockquote>{EJEMPLO_PROPUESTA}</blockquote>
      </div>
      <p>Para comparar dos políticas, medimos el apoyo a cada una por separado, con las mismas personas simuladas.</p>
      <p className={estilos.limite}>Los gustos y los “¿qué pasaría si…?” históricos se alejan de este uso. Puedes explorarlos, pero el sistema no está diseñado para predecir hechos ni elegir un ganador.</p>
      <footer className={estilos.pie}>
        <small>Personas simuladas con IA. Los resultados no son una encuesta real.</small>
        <Boton variante="primario" onClick={() => popup.current?.close()}>Entendido, quiero preguntar</Boton>
      </footer>
    </PopupDialogo>
  );
}

interface Revision {
  originales: Borrador[];
  separadas: Borrador[] | null;
  motivos: string[];
  fallo?: boolean;
  excedeLimite?: boolean;
}

export function useGuiaPreguntas(sim: EnVivo, alElegir: (indice: number) => void) {
  const [revisando, setRevisando] = useState(false);
  const [revision, setRevision] = useState<Revision | null>(null);
  const popup = useRef<PopupHandle>(null);
  const devolverFoco = useRef(false);
  const peticion = useRef<AbortController | null>(null);
  const firma = JSON.stringify([sim.borradores, sim.filtros, sim.fase]);
  const firmaActual = useRef(firma);
  firmaActual.current = firma;
  useEffect(() => {
    peticion.current?.abort();
    peticion.current = null;
    setRevisando(false);
    setRevision(null);
    popup.current?.close();
    return () => peticion.current?.abort();
  }, [firma]);
  useEffect(() => { if (revision) popup.current?.showModal(); }, [revision]);

  const reformular = () => {
    devolverFoco.current = true;
    popup.current?.close();
  };
  const revisar = async () => {
    if (!sim.puedePreguntar || peticion.current) return;
    const originales = sim.borradores.filter((b) => (b.texto.trim() || b.leido) && !b.leyendo);
    const controller = new AbortController();
    peticion.current = controller;
    setRevisando(true);
    const tiempo = window.setTimeout(() => controller.abort(), 35000);
    try {
      // Los documentos ya leídos son propuestas; esta orientación revisa lo escrito en el formulario público.
      if (originales.some((b) => b.leido)) throw new Error('Revisar el documento manualmente');
      const orientaciones = await orientarPreguntas(originales.map((b) => b.texto.trim()), controller.signal);
      if (firmaActual.current !== firma) return;
      const separadas = separarPropuestas(originales, orientaciones);
      const motivos = orientaciones.filter((o) => o.tipo === 'fuera').map((o) => o.motivo);
      const comparacion = orientaciones.some((o) => o.tipo === 'comparacion');
      if (comparacion && separadas.length > MAXIMO_VARIANTES) {
        motivos.push(`Separar esta consulta supera las ${MAXIMO_VARIANTES} variantes disponibles. Divide las comparaciones en consultas distintas o continúa con el texto original.`);
      }
      if (!motivos.length && !comparacion) { void sim.preguntar(originales); return; }
      setRevision({ originales, excedeLimite: separadas.length > MAXIMO_VARIANTES, separadas: comparacion && separadas.length <= MAXIMO_VARIANTES ? separadas : null, motivos });
    } catch {
      if (firmaActual.current === firma && peticion.current === controller) {
        setRevision({ originales, separadas: null, motivos: [], fallo: true });
      }
    } finally {
      window.clearTimeout(tiempo);
      if (peticion.current === controller) { peticion.current = null; setRevisando(false); }
    }
  };
  const continuar = () => {
    if (!revision || !sim.puedePreguntar) return;
    popup.current?.close();
    void sim.preguntar(revision.separadas ?? revision.originales, !!revision.separadas);
  };
  const avisoWhati = revision && !revision.fallo && !revision.separadas && !revision.excedeLimite;
  return {
    revisar, revisando,
    dialogo: (
      <PopupDialogo ref={popup} className={revision?.separadas ? estilos.comparacion : avisoWhati ? estilos.avisoWhati : estilos.panel} aria-labelledby="titulo-orientacion" aria-describedby="descripcion-orientacion" onClose={() => {
        if (devolverFoco.current) { devolverFoco.current = false; document.querySelector<HTMLTextAreaElement>('textarea')?.focus(); }
        setRevision(null);
      }}>
        {revision && <>
          {avisoWhati ? <div className={estilos.conversacion}>
            <FiguraWati estado="indecisa" animo="pensativa" rasgos={{ semilla: 6, variante: 0, tono: 0 }} alto={228} />
            <div className={estilos.globo}>
              <h2 id="titulo-orientacion" className="solo-lectores">Un consejo de Whati</h2>
              <p id="descripcion-orientacion">Respondo mejor cuando me propones una medida concreta. ¿Cuál te gustaría probar para ver cuánto apoyo tendría en Chile?</p>
            </div>
          </div> : revision.separadas ? <>
            <header className={estilos.encabezadoComparacion}>
              <h2 id="titulo-orientacion">Así lo preguntaremos en Chile</h2>
              <p id="descripcion-orientacion">La misma muestra evaluará cada propuesta por turno. Una persona puede apoyar más de una.</p>
            </header>
            <ol className={estilos.ronda} aria-label="Propuestas en orden de consulta">
              {revision.separadas.map((b, i) => <li key={b.id}>
                <div className={estilos.voz}>
                  <span>Propuesta {letraDe(i)}</span>
                  <p>{b.texto}</p>
                </div>
                <FiguraWati estado={i % 2 === 0 ? 'indecisa' : 'neutra'} animo="alegre" rasgos={{ semilla: i + 5, variante: i + 1, tono: 0 }} alto={96} />
              </li>)}
            </ol>
            {revision.motivos.map((motivo, i) => <p key={i} className={estilos.notaComparacion}>{motivo}</p>)}
          </> : <>
            <div className={estilos.marca}><span>Antes de consultar a los agentes</span></div>
            <h2 id="titulo-orientacion">{revision.fallo ? 'La revisión no está disponible.' : 'Esta pregunta necesita otro enfoque.'}</h2>
            <p id="descripcion-orientacion">{revision.fallo ? 'Puedes continuar con tu pregunta o reformularla como una propuesta de política pública.' : 'Divide la consulta en menos variantes o continúa con tu pregunta original.'}</p>
            {revision.motivos.map((motivo, i) => <p key={i} className={estilos.limite}>{motivo}</p>)}
            <div className={estilos.ejemplo}><span>Ejemplo de una medida concreta</span><blockquote>{EJEMPLO_PROPUESTA}</blockquote></div>
          </>}
          <footer className={avisoWhati || revision.separadas ? estilos.accionesWhati : estilos.acciones}>
            <Boton variante={avisoWhati ? "primario" : "secundario"} onClick={() => {
              if (revision.separadas) { sim.cargar(revision.separadas.map((b) => b.texto)); alElegir(0); }
              reformular();
            }}>{revision.separadas ? 'Editar propuestas' : 'Reformular'}</Boton>
            <Boton variante={avisoWhati ? "secundario" : "primario"} disabled={!sim.puedePreguntar} onClick={continuar}>{revision.separadas ? (revision.separadas.length === 2 ? 'Consultar A/B' : 'Consultar propuestas') : 'Continuar de todos modos'}</Boton>
          </footer>
        </>}
      </PopupDialogo>
    ),
  };
}
