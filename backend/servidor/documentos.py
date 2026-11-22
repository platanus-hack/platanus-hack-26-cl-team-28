"""Texto de un documento subido (una ley completa, un proyecto, una minuta)."""

import html
import re
import shutil
import subprocess
import tempfile
import threading
import zipfile
from io import BytesIO
from pathlib import Path


class DocumentoIlegible(ValueError):
    pass


#: Lo más que se lee de un documento ya convertido a texto. Un archivo armado para inflarse al
#: abrirlo (un zip de pocos KB que se expande a gigas) se corta aquí y no llena la memoria.
TEXTO_MAXIMO = 3_000_000
#: Páginas de un PDF que se convierten: lo que sigue no alcanza a entrar al resumen.
PAGINAS_MAXIMAS = 400
#: Documentos que se convierten a la vez: cada PDF es un proceso aparte.
CONVERSIONES = threading.BoundedSemaphore(4)


def _limpiar(texto: str) -> str:
    texto = texto.replace("\r", "")
    texto = re.sub(r"[ \t]+", " ", texto)
    return re.sub(r"\n{3,}", "\n\n", texto).strip()


def _pdf(datos: bytes) -> str:
    if not shutil.which("pdftotext"):
        raise DocumentoIlegible("Este servidor no tiene pdftotext para leer PDF; sube el texto en .txt o .md")
    with tempfile.TemporaryDirectory() as carpeta:
        origen = Path(carpeta) / "documento.pdf"
        origen.write_bytes(datos)
        destino = Path(carpeta) / "documento.txt"
        # El texto va a un archivo y se lee con tope: la salida de un PDF malicioso no se acumula en memoria.
        try:
            salida = subprocess.run(["pdftotext", "-layout", "-enc", "UTF-8", "-l", str(PAGINAS_MAXIMAS), str(origen), str(destino)],
                                    capture_output=True, timeout=45, check=False)
        except subprocess.TimeoutExpired as error:
            raise DocumentoIlegible("El PDF tardó demasiado en leerse; prueba con uno más corto o en .txt") from error
        if salida.returncode != 0 or not destino.exists():
            raise DocumentoIlegible("No se pudo leer el PDF")
        with open(destino, "rb") as f:
            return f.read(TEXTO_MAXIMO).decode("utf-8", errors="replace")


def _docx(datos: bytes) -> str:
    try:
        with zipfile.ZipFile(BytesIO(datos)) as archivo:
            # Se lee con tope, sin fiarse del tamaño que declara el archivo.
            with archivo.open("word/document.xml") as f:
                xml = f.read(TEXTO_MAXIMO * 4).decode("utf-8", errors="replace")
    except (zipfile.BadZipFile, KeyError, OSError, RuntimeError, NotImplementedError) as error:
        raise DocumentoIlegible("No se pudo leer el .docx") from error
    xml = re.sub(r"</w:p>", "\n", xml)
    return html.unescape(re.sub(r"<[^>]+>", "", xml))


def nombre_limpio(nombre: str) -> str:
    """El nombre del archivo como se muestra y se le dice al modelo: sin ruta, sin caracteres de control y corto."""
    nombre = re.sub(r"[\x00-\x1f\x7f]", " ", nombre.replace("\\", "/").rsplit("/", 1)[-1]).strip()
    return nombre[:120] or "documento.txt"


def extraer_texto(nombre: str, datos: bytes) -> str:
    extension = Path(nombre).suffix.lower()
    if not CONVERSIONES.acquire(timeout=20):
        raise DocumentoIlegible("Hay muchos documentos leyéndose a la vez; intenta de nuevo en un momento")
    try:
        if extension == ".pdf" or datos[:4] == b"%PDF":
            texto = _pdf(datos)
        elif extension == ".docx":
            texto = _docx(datos)
        elif extension in (".html", ".htm"):
            texto = html.unescape(re.sub(r"<[^>]+>", " ", datos[:TEXTO_MAXIMO * 2].decode("utf-8", errors="replace")))
        else:
            texto = datos[:TEXTO_MAXIMO * 2].decode("utf-8", errors="replace")
        texto = _limpiar(texto[:TEXTO_MAXIMO])
    finally:
        CONVERSIONES.release()
    if len(texto) < 40:
        raise DocumentoIlegible("El documento no tiene texto legible")
    return texto
