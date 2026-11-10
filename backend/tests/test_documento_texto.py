import io

import pytest
from docx import Document

from ingest.documento_texto import (
    MAX_FRAGMENTOS,
    MINIMO_CARACTERES,
    DocumentoInvalido,
    extraer_texto,
    fragmentar,
)

PARRAFO = "La delegación de Orán atiende de lunes a viernes de 8 a 14 horas en la calle España 123. "


def _docx(parrafos=(), tabla=None) -> bytes:
    doc = Document()
    for p in parrafos:
        doc.add_paragraph(p)
    if tabla:
        t = doc.add_table(rows=len(tabla), cols=len(tabla[0]))
        for i, fila in enumerate(tabla):
            for j, celda in enumerate(fila):
                t.cell(i, j).text = celda
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _pdf(lineas: list[str]) -> bytes:
    """PDF mínimo de una página con texto Helvetica, armado a mano."""
    contenido = "BT /F1 10 Tf 40 780 Td 12 TL " + " ".join(f"({l}) Tj T*" for l in lineas) + " ET"
    objetos = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] /Contents 4 0 R "
        "/Resources << /Font << /F1 5 0 R >> >> >>",
        f"<< /Length {len(contenido)} >>\nstream\n{contenido}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    salida = b"%PDF-1.4\n"
    offsets = []
    for i, obj in enumerate(objetos, start=1):
        offsets.append(len(salida))
        salida += f"{i} 0 obj\n{obj}\nendobj\n".encode("latin-1")
    xref = len(salida)
    salida += f"xref\n0 {len(objetos) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        salida += f"{off:010d} 00000 n \n".encode()
    salida += f"trailer\n<< /Size {len(objetos) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()
    return salida


def test_extrae_texto_de_docx():
    texto = extraer_texto("Reglamento.docx", _docx([PARRAFO * 3]))
    assert "delegación de Orán" in texto


def test_extrae_texto_de_celdas_de_tabla_en_docx():
    tabla = [["Delegación", "Dirección"], ["Tartagal", "Avenida San Martín 450 y Belgrano " * 6]]
    texto = extraer_texto("delegaciones.DOCX", _docx(tabla=tabla))
    assert "Tartagal" in texto and "San Martín 450" in texto


def test_extrae_texto_de_pdf_con_texto():
    linea = "La delegacion de Oran atiende de lunes a viernes de 8 a 14 horas en la calle Espana 123."
    texto = extraer_texto("guia.pdf", _pdf([linea] * 4))
    assert "delegacion de Oran" in texto


def test_rechaza_extension_no_admitida():
    for nombre in ("notas.txt", "viejo.doc", "sin_extension"):
        with pytest.raises(DocumentoInvalido, match="PDF o Word"):
            extraer_texto(nombre, b"hola")


def test_rechaza_pdf_con_contenido_invalido():
    with pytest.raises(DocumentoInvalido, match="No se pudo leer"):
        extraer_texto("roto.pdf", b"esto no es un pdf")


def test_rechaza_texto_menor_al_minimo():
    with pytest.raises(DocumentoInvalido, match="escaneo"):
        extraer_texto("corto.docx", _docx(["Muy poco texto."]))
    assert MINIMO_CARACTERES == 200


def test_fragmenta_en_trozos_cercanos_al_objetivo():
    texto = "\n\n".join(f"Párrafo {i}. " + PARRAFO * 3 for i in range(30))
    fragmentos = fragmentar(texto, objetivo=900, solapamiento=150)
    assert len(fragmentos) > 1
    assert all(len(f) <= 900 + 400 for f in fragmentos)


def test_fragmentos_consecutivos_comparten_solapamiento():
    texto = "\n\n".join(f"Sección {i}: " + PARRAFO * 2 for i in range(20))
    fragmentos = fragmentar(texto, objetivo=900, solapamiento=150)
    cola = fragmentos[0][-60:]
    assert cola in fragmentos[1]


def test_rechaza_documento_que_excede_el_maximo_de_fragmentos():
    texto = "\n\n".join(PARRAFO * 5 for _ in range(MAX_FRAGMENTOS * 3))
    with pytest.raises(DocumentoInvalido, match="demasiado extenso"):
        fragmentar(texto)


def test_rechaza_docx_que_expande_mas_de_lo_permitido():
    import zipfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("word/document.xml", b"0" * (60 * 1024 * 1024))
    assert len(buf.getvalue()) < 1024 * 1024
    with pytest.raises(DocumentoInvalido, match="demasiado extenso"):
        extraer_texto("bomba.docx", buf.getvalue())


def test_rechaza_pdf_con_demasiadas_paginas():
    from pypdf import PdfWriter

    from ingest.documento_texto import MAX_PAGINAS

    w = PdfWriter()
    for _ in range(MAX_PAGINAS + 1):
        w.add_blank_page(width=100, height=100)
    buf = io.BytesIO()
    w.write(buf)
    with pytest.raises(DocumentoInvalido, match="demasiado extenso"):
        extraer_texto("enorme.pdf", buf.getvalue())
