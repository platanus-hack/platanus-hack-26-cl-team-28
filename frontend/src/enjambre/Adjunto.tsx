import { useRef, useState, type DragEvent } from 'react';
import { Boton } from '../componentes/comunes/Boton';
import { PopupDialogo, type PopupHandle } from '../componentes/comunes/Popup';
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

const TIPOS = ['.pdf', '.docx', '.txt', '.md', '.html', '.htm'];

function aislarArrastre(evento: DragEvent) {
  evento.preventDefault();
  evento.stopPropagation();
}

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
  const dialogo = useRef<PopupHandle>(null);
  const cancelar = useRef<HTMLButtonElement>(null);
  const [arrastrando, setArrastrando] = useState(false);
  const [errorArchivo, setErrorArchivo] = useState('');

  const abrir = () => {
    setArrastrando(false);
    setErrorArchivo('');
    dialogo.current?.showModal();
    cancelar.current?.focus({ preventScroll: true });
  };

  const recibir = (archivo: File) => {
    const extension = archivo.name.slice(archivo.name.lastIndexOf('.')).toLowerCase();
    if (!TIPOS.includes(extension)) {
      setErrorArchivo('Elige un archivo PDF, DOCX, TXT, Markdown o HTML.');
      return;
    }
    dialogo.current?.close();
    alElegir(archivo);
  };

  return (
    <div className={estilos.adjunto}>
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
          <button type="button" className={estilos.subir} aria-haspopup="dialog" aria-label="Subir documento" title="Subir documento" onClick={abrir}>
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 16V4m-4 4 4-4 4 4M4 16v4h16v-4" /></svg>
          </button>
          <PopupDialogo
            ref={dialogo}
            className={estilos.dialogo}
            aria-labelledby="titulo-adjunto"
            aria-describedby="formatos-adjunto"
            onDragOver={aislarArrastre}
            onDrop={aislarArrastre}
          >
            <input
              ref={entrada}
              type="file"
              accept={TIPOS.join(',')}
              className="solo-lectores"
              tabIndex={-1}
              aria-hidden="true"
              onChange={(e) => {
                const archivo = e.target.files?.[0];
                e.target.value = '';
                if (archivo) recibir(archivo);
              }}
            />
            <h2 id="titulo-adjunto">Subir un documento</h2>
            <div
              className={estilos.zona}
              data-arrastrando={arrastrando || undefined}
              onDragOver={(e) => {
                if (!e.dataTransfer.types.includes('Files')) return;
                e.dataTransfer.dropEffect = 'copy';
                setArrastrando(true);
              }}
              onDragLeave={(e) => {
                if (e.relatedTarget instanceof Node && e.currentTarget.contains(e.relatedTarget)) return;
                setArrastrando(false);
              }}
              onDrop={(e) => {
                setArrastrando(false);
                const { files } = e.dataTransfer;
                if (files.length > 1) setErrorArchivo('Adjunta un solo archivo por variante.');
                else if (files[0]) recibir(files[0]);
              }}
            >
              <span className={estilos.iconoZona} aria-hidden="true">
                <svg width="23" height="23" viewBox="0 0 24 24"><path d="M6 3h8l4 4v14H6zM14 3v5h4m-6 9v-6m-2.5 2.5L12 11l2.5 2.5" /></svg>
              </span>
              <p className={estilos.instruccion}>{arrastrando ? 'Suelta el documento aquí' : 'Arrastra tu documento aquí'}</p>
              <Boton variante="primario" onClick={() => entrada.current?.click()}>Elegir archivo</Boton>
              <p id="formatos-adjunto" className={estilos.formatos}>PDF, DOCX, TXT, Markdown o HTML</p>
            </div>
            {errorArchivo && <p className={estilos.errorArchivo} role="alert">{errorArchivo}</p>}
            <div className={estilos.acciones}>
              <button ref={cancelar} type="button" onClick={() => dialogo.current?.close()}>Cancelar</button>
            </div>
          </PopupDialogo>
        </>
      )}
    </div>
  );
}
