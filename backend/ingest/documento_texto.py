import io
import re

MINIMO_CARACTERES = 200
MAX_FRAGMENTOS = 400
MAX_BYTES = 10 * 1024 * 1024
MAX_PAGINAS = 300
MAX_BYTES_DESCOMPRIMIDOS = 50 * 1024 * 1024
_MENSAJE_EXTENSO = "El documento es demasiado extenso. Dividilo en partes."


class DocumentoInvalido(ValueError):
    """El documento no se puede usar; el mensaje está pensado para mostrarse a la persona."""


def _texto_de_pdf(contenido: bytes) -> str:
    from pypdf import PdfReader

    lector = PdfReader(io.BytesIO(contenido))
    if len(lector.pages) > MAX_PAGINAS:
        raise DocumentoInvalido(_MENSAJE_EXTENSO)
    return "\n\n".join((pagina.extract_text() or "") for pagina in lector.pages)


def _texto_de_docx(contenido: bytes) -> str:
    import zipfile

    from docx import Document

    with zipfile.ZipFile(io.BytesIO(contenido)) as z:
        if sum(i.file_size for i in z.infolist()) > MAX_BYTES_DESCOMPRIMIDOS:
            raise DocumentoInvalido(_MENSAJE_EXTENSO)
    doc = Document(io.BytesIO(contenido))
    partes = [p.text for p in doc.paragraphs]
    for tabla in doc.tables:
        for fila in tabla.rows:
            celdas = [c.text.strip() for c in fila.cells if c.text.strip()]
            if celdas:
                partes.append(" | ".join(celdas))
    return "\n\n".join(partes)


def extraer_texto(nombre_archivo: str, contenido: bytes) -> str:
    nombre = nombre_archivo.lower()
    if nombre.endswith(".pdf"):
        lector = _texto_de_pdf
    elif nombre.endswith(".docx"):
        lector = _texto_de_docx
    else:
        raise DocumentoInvalido("Solo se admiten archivos PDF o Word (.docx).")
    try:
        texto = lector(contenido)
    except DocumentoInvalido:
        raise
    except Exception as error:
        raise DocumentoInvalido("No se pudo leer el archivo. Verificá que no esté dañado.") from error
    texto = re.sub(r"[ \t]+", " ", texto).strip()
    if len(texto) < MINIMO_CARACTERES:
        raise DocumentoInvalido(
            "El documento casi no tiene texto. Si es un escaneo (una imagen), no se puede leer."
        )
    return texto


def fragmentar(texto: str, objetivo: int = 900, solapamiento: int = 150) -> list[str]:
    parrafos = [p.strip() for p in re.split(r"\n\s*\n", texto) if p.strip()]
    # Un párrafo más largo que el objetivo se corta por oraciones o, en último caso, por tamaño.
    piezas: list[str] = []
    for parrafo in parrafos:
        if len(parrafo) <= objetivo:
            piezas.append(parrafo)
            continue
        actual = ""
        for oracion in re.split(r"(?<=[.!?])\s+", parrafo):
            while len(oracion) > objetivo:
                if actual:
                    piezas.append(actual)
                    actual = ""
                piezas.append(oracion[:objetivo])
                oracion = oracion[objetivo:]
            if actual and len(actual) + len(oracion) + 1 > objetivo:
                piezas.append(actual)
                actual = oracion
            else:
                actual = f"{actual} {oracion}".strip()
        if actual:
            piezas.append(actual)

    fragmentos: list[str] = []
    actual = ""
    for pieza in piezas:
        if actual and len(actual) + len(pieza) + 2 > objetivo:
            fragmentos.append(actual)
            cola = actual[-solapamiento:] if solapamiento else ""
            actual = f"{cola}\n\n{pieza}" if cola else pieza
        else:
            actual = f"{actual}\n\n{pieza}" if actual else pieza
    if actual:
        fragmentos.append(actual)

    if len(fragmentos) > MAX_FRAGMENTOS:
        raise DocumentoInvalido(
            f"El documento es demasiado extenso (más de {MAX_FRAGMENTOS} fragmentos). Dividilo en partes."
        )
    return fragmentos
