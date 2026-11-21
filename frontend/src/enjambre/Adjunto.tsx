import { useRef } from 'react';
import { Boton } from '../componentes/comunes/Boton';
import { formatear } from '../dominio/textos';
import type { Documento } from '../dominio/tipos';
import type { DocumentoLeido } from '../vivo/api';
import estilos from './Adjunto.module.css';

interface Props {
  documento?: Documento;
  leido?: DocumentoLeido;
  leyendo?: boolean;
  error?: string;
  alElegir(archivo: File | undefined): void;
}

const TIPOS = '.pdf,.docx,.txt,.md,.html';

function tamanoLegible(bytes: number): string {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1).replace('.', ',')} MB`;
}

function estado({ leido, leyendo, error }: Props): string {
  if (error) return error;
  if (leyendo) return 'El agente lo está leyendo';
  if (!leido) return '';
  if (leido.largo_original) return `Resumido de ${formatear(leido.largo_original)} caracteres: ${leido.titulo}`;
  return 'Leído completo';
}

/** Sube el texto completo de la propuesta (una ley, un proyecto); el motor lo lee y, si es largo, lo resume. */
export function Adjunto(props: Props) {
  const { documento, leyendo, error, alElegir } = props;
  const entrada = useRef<HTMLInputElement>(null);
  const dialogo = useRef<HTMLDialogElement>(null);
  return (
    <div className={estilos.adjunto}>
      <input
        ref={entrada}
        type="file"
        accept={TIPOS}
        className="solo-lectores"
        tabIndex={-1}
        aria-hidden="true"
        onChange={(e) => {
          const archivo = e.target.files?.[0];
          if (archivo) alElegir(archivo);
          e.target.value = '';
        }}
      />
      {documento ? (
        <div className={estilos.archivo} data-leyendo={leyendo || undefined} data-error={error ? true : undefined}>
          <span className={estilos.nombre}>{documento.nombre}</span>
          <span className={estilos.peso}>{tamanoLegible(documento.tamano)}</span>
          <Boton variante="texto" onClick={() => alElegir(undefined)}>
            Quitar
          </Boton>
          <p className={estilos.estado} aria-live="polite">
            {estado(props)}
          </p>
        </div>
      ) : (
        <>
          <button type="button" className={estilos.subir} aria-haspopup="dialog" onClick={() => dialogo.current?.showModal()}>
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 16V4m-4 4 4-4 4 4M4 16v4h16v-4" /></svg>
            Subir documento
          </button>
          <dialog ref={dialogo} className={estilos.dialogo} aria-labelledby="titulo-adjunto">
            <h2 id="titulo-adjunto">Subir un documento</h2>
            <p>Selecciona una ley o documento para usarlo en tu propuesta.</p>
            <p className={estilos.formatos}>Formatos admitidos: PDF, DOCX, TXT, Markdown y HTML.</p>
            <div className={estilos.acciones}>
              <button type="button" onClick={() => dialogo.current?.close()}>Cancelar</button>
              <button type="button" onClick={() => { dialogo.current?.close(); entrada.current?.click(); }}>Elegir archivo</button>
            </div>
          </dialog>
        </>
      )}
    </div>
  );
}
