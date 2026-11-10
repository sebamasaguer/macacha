import os
import threading

import psycopg
import pytest
from pgvector.psycopg import register_vector

from agent.admin import documentos_repository as docs
from agent.admin.documentos_repository import TopeDeDocumentos
from tests.formularios_helpers import crear_organismo


def _vec(valor: float = 0.1) -> list[float]:
    return [valor] * 1536


def _crear(conn, organismo_id, titulo="Reglamento", fragmentos=("uno", "dos")):
    return docs.crear_documento(
        conn, organismo_id, titulo, f"{titulo}.pdf", "admin@org.gob.ar",
        list(fragmentos), [_vec() for _ in fragmentos],
    )


def _textos(conn, documento_id):
    with conn.cursor() as cur:
        cur.execute("SELECT texto FROM organismo_documento_chunks WHERE documento_id = %s ORDER BY orden", (documento_id,))
        return [fila[0] for fila in cur.fetchall()]


def test_crea_documento_con_sus_fragmentos_en_orden(db_conn, clean_db):
    organismo_id = crear_organismo(db_conn)
    doc = _crear(db_conn, organismo_id, fragmentos=("a", "b", "c"))
    assert doc["titulo"] == "Reglamento" and doc["fragmentos"] == 3
    assert doc["organismo_id"] == organismo_id and doc["subido_por_email"] == "admin@org.gob.ar"
    assert _textos(db_conn, doc["id"]) == ["a", "b", "c"]


def test_rechaza_el_cuarto_documento_del_organismo(db_conn, clean_db):
    organismo_id = crear_organismo(db_conn)
    for i in range(3):
        _crear(db_conn, organismo_id, titulo=f"Doc {i}")
    with pytest.raises(TopeDeDocumentos):
        _crear(db_conn, organismo_id, titulo="Doc 4")
    assert docs.MAX_DOCUMENTOS_POR_ORGANISMO == 3


def test_el_tope_es_por_organismo(db_conn, clean_db):
    uno = crear_organismo(db_conn, "Organismo uno")
    otro = crear_organismo(db_conn, "Organismo otro")
    for i in range(3):
        _crear(db_conn, uno, titulo=f"Doc {i}")
    assert _crear(db_conn, otro, titulo="Propio")["organismo_id"] == otro


def test_dos_altas_simultaneas_con_dos_existentes_solo_una_pasa(db_conn, clean_db):
    organismo_id = crear_organismo(db_conn)
    for i in range(2):
        _crear(db_conn, organismo_id, titulo=f"Doc {i}")
    db_conn.commit()
    url = os.environ.get("TEST_DATABASE_URL", "postgresql://macacha:macacha@localhost:5432/macacha_test")
    resultados: list[str] = []
    barrera = threading.Barrier(2)

    def subir(indice: int):
        with psycopg.connect(url) as conn:
            register_vector(conn)
            barrera.wait()
            try:
                _crear(conn, organismo_id, titulo=f"Nuevo {indice}")
                conn.commit()
                resultados.append("ok")
            except TopeDeDocumentos:
                conn.rollback()
                resultados.append("tope")

    hilos = [threading.Thread(target=subir, args=(i,)) for i in range(2)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join(timeout=30)
    assert sorted(resultados) == ["ok", "tope"]


def test_reemplazar_deja_solo_los_fragmentos_nuevos(db_conn, clean_db):
    doc = _crear(db_conn, crear_organismo(db_conn), fragmentos=("viejo 1", "viejo 2"))
    nuevo = docs.reemplazar_contenido(db_conn, doc["id"], "v2.docx", "otro@org.gob.ar", ["nuevo"], [_vec(0.2)])
    assert _textos(db_conn, doc["id"]) == ["nuevo"]
    assert nuevo["nombre_archivo"] == "v2.docx" and nuevo["fragmentos"] == 1
    assert nuevo["actualizado_en"] >= doc["actualizado_en"]


def test_reemplazar_conserva_el_titulo_si_no_se_cambia(db_conn, clean_db):
    doc = _crear(db_conn, crear_organismo(db_conn), titulo="Mi título")
    sin_cambio = docs.reemplazar_contenido(db_conn, doc["id"], "v2.pdf", "a@b.c", ["x"], [_vec()])
    assert sin_cambio["titulo"] == "Mi título"
    con_cambio = docs.reemplazar_contenido(db_conn, doc["id"], "v3.pdf", "a@b.c", ["y"], [_vec()], titulo="Otro")
    assert con_cambio["titulo"] == "Otro"


def test_reemplazar_de_un_documento_inexistente_devuelve_none(db_conn, clean_db):
    assert docs.reemplazar_contenido(db_conn, "00000000-0000-0000-0000-000000000000", "a.pdf", "a@b.c", ["x"], [_vec()]) is None


def test_si_reemplazar_falla_a_mitad_el_documento_anterior_queda_intacto(db_conn, clean_db):
    doc = _crear(db_conn, crear_organismo(db_conn), fragmentos=("original",))
    db_conn.commit()
    with pytest.raises(Exception):
        docs.reemplazar_contenido(db_conn, doc["id"], "v2.pdf", "a@b.c", ["nuevo"], [[0.1, 0.2, 0.3]])
    db_conn.rollback()
    assert _textos(db_conn, doc["id"]) == ["original"]
    assert docs.obtener_documento(db_conn, doc["id"])["nombre_archivo"] == "Reglamento.pdf"


def test_renombrar_cambia_solo_el_titulo(db_conn, clean_db):
    doc = _crear(db_conn, crear_organismo(db_conn))
    nuevo = docs.renombrar_documento(db_conn, doc["id"], "Título nuevo")
    assert nuevo["titulo"] == "Título nuevo" and nuevo["fragmentos"] == 2


def test_listar_filtra_por_organismo(db_conn, clean_db):
    uno = crear_organismo(db_conn, "Organismo uno")
    otro = crear_organismo(db_conn, "Organismo otro")
    _crear(db_conn, uno, titulo="De uno")
    _crear(db_conn, otro, titulo="De otro")
    assert [d["titulo"] for d in docs.listar_documentos(db_conn, uno)] == ["De uno"]
    assert {d["titulo"] for d in docs.listar_documentos(db_conn, None)} == {"De uno", "De otro"}
    assert docs.listar_documentos(db_conn, uno)[0]["organismo"] == "Organismo uno"


def test_borrar_elimina_documento_y_fragmentos(db_conn, clean_db):
    doc = _crear(db_conn, crear_organismo(db_conn))
    assert docs.borrar_documento(db_conn, doc["id"]) is True
    assert docs.obtener_documento(db_conn, doc["id"]) is None
    assert _textos(db_conn, doc["id"]) == []
    assert docs.borrar_documento(db_conn, doc["id"]) is False
