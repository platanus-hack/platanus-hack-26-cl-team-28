"""Texto de un documento subido (una ley completa, un proyecto, una minuta)."""

import html
import re
import shutil
import subprocess
import tempfile
import zipfile
from io import BytesIO
from pathlib import Path


class DocumentoIlegible(ValueError):
    pass


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
        salida = subprocess.run(["pdftotext", "-layout", "-enc", "UTF-8", str(origen), "-"],
                                capture_output=True, timeout=60, check=False)
    if salida.returncode != 0:
        raise DocumentoIlegible("No se pudo leer el PDF")
    return salida.stdout.decode("utf-8", errors="replace")


def _docx(datos: bytes) -> str:
    try:
        with zipfile.ZipFile(BytesIO(datos)) as archivo:
            xml = archivo.read("word/document.xml").decode("utf-8", errors="replace")
    except (zipfile.BadZipFile, KeyError) as error:
        raise DocumentoIlegible("No se pudo leer el .docx") from error
    xml = re.sub(r"</w:p>", "\n", xml)
    return html.unescape(re.sub(r"<[^>]+>", "", xml))


def extraer_texto(nombre: str, datos: bytes) -> str:
    extension = Path(nombre).suffix.lower()
    if extension == ".pdf" or datos[:4] == b"%PDF":
        texto = _pdf(datos)
    elif extension == ".docx":
        texto = _docx(datos)
    elif extension in (".html", ".htm"):
        texto = html.unescape(re.sub(r"<[^>]+>", " ", datos.decode("utf-8", errors="replace")))
    else:
        texto = datos.decode("utf-8", errors="replace")
    texto = _limpiar(texto)
    if len(texto) < 40:
        raise DocumentoIlegible("El documento no tiene texto legible")
    return texto
