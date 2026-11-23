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

export const EJEMPLO_PROPUESTA = 'Implementar una ley que subsidie el transporte público para estudiantes de zonas rurales.';

export function Bienvenida() {
  const popup = useRef<PopupHandle>(null);
  useEffect(() => { popup.current?.showModal(); }, []);
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
        <span>Prueba con algo así</span>
        <blockquote>“¿Qué apoyo tendría una ley de transporte gratuito para estudiantes rurales?”</blockquote>
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
      setRevision({ originales, separadas: comparacion && separadas.length <= MAXIMO_VARIANTES ? separadas : null, motivos });
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
  return {
    revisar, revisando,
    dialogo: (
      <PopupDialogo ref={popup} className={estilos.panel} aria-labelledby="titulo-orientacion" aria-describedby="descripcion-orientacion" onClose={() => {
        if (devolverFoco.current) { devolverFoco.current = false; document.querySelector<HTMLTextAreaElement>('textarea')?.focus(); }
      }}>
        {revision && <>
          <div className={estilos.marca}><span>Antes de consultar a los agentes</span></div>
          <h2 id="titulo-orientacion">{revision.separadas ? 'Dos políticas, dos consultas.' : revision.fallo ? 'La revisión no está disponible.' : 'Esta pregunta necesita otro enfoque.'}</h2>
          <p id="descripcion-orientacion">{revision.separadas
            ? 'Primero consultaremos A y luego B, por separado y con la misma muestra. Revisa que las propuestas conserven lo que quieres preguntar.'
            : revision.fallo ? 'Puedes continuar con tu pregunta o reformularla como una propuesta de política pública.'
            : 'El sistema responde mejor al apoyo y rechazo a políticas públicas. Esta pregunta se aleja de ese uso; sus resultados pueden ser menos útiles.'}</p>
          {revision.motivos.map((motivo, i) => <p key={i} className={estilos.limite}>{motivo}</p>)}
          {revision.separadas ? <ol className={estilos.propuestas}>
            {revision.separadas.map((b, i) => <li key={b.id}><span>{letraDe(i)}</span><p>{b.texto}</p></li>)}
          </ol> : <div className={estilos.ejemplo}><span>Una forma de preguntar</span><blockquote>¿Qué apoyo tendría esta propuesta? {EJEMPLO_PROPUESTA}</blockquote></div>}
          {revision.separadas && <p className={estilos.limite}>Comparar apoyo no equivale a preguntar por una preferencia directa: una persona puede apoyar ambas propuestas.</p>}
          <footer className={estilos.acciones}>
            <Boton variante="secundario" onClick={() => {
              if (revision.separadas) { sim.cargar(revision.separadas.map((b) => b.texto)); alElegir(0); }
              reformular();
            }}>{revision.separadas ? 'Editar propuestas' : 'Reformular'}</Boton>
            <Boton variante="primario" disabled={!sim.puedePreguntar} onClick={continuar}>{revision.separadas ? 'Consultar A/B' : 'Continuar de todos modos'}</Boton>
          </footer>
        </>}
      </PopupDialogo>
    ),
  };
}
