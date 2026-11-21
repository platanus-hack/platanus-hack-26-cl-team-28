import { useRef } from 'react';
import { Boton } from '../componentes/comunes/Boton';
import type { Documento } from '../dominio/tipos';
import estilos from './Adjunto.module.css';

interface Props {
  documento?: Documento;
  alCambiar(documento: Documento | undefined): void;
}

const TIPOS = '.pdf,.doc,.docx,.txt,.md,.rtf,.odt';

function tamanoLegible(bytes: number): string {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1).replace('.', ',')} MB`;
}

export function aDocumento(archivo: File): Documento {
  return { nombre: archivo.name, tamano: archivo.size, archivo };
}

/** Sube el texto completo de la propuesta (una ley, un proyecto) en vez de escribirlo. */
export function Adjunto({ documento, alCambiar }: Props) {
  const entrada = useRef<HTMLInputElement>(null);
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
          if (archivo) alCambiar(aDocumento(archivo));
          e.target.value = '';
        }}
      />
      {documento ? (
        <p className={estilos.archivo}>
          <span className={estilos.nombre}>{documento.nombre}</span>
          <span className={estilos.peso}>{tamanoLegible(documento.tamano)}</span>
          <Boton variante="texto" onClick={() => alCambiar(undefined)}>
            Quitar
          </Boton>
        </p>
      ) : (
        <Boton variante="texto" onClick={() => entrada.current?.click()}>
          Subir un documento
        </Boton>
      )}
    </div>
  );
}
