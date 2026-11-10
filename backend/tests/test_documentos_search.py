from agent.admin import documentos_repository as docs
from retrieval.documentos_search import UMBRAL_SIMILITUD, buscar_documentos_chunks
from tests.formularios_helpers import crear_organismo


def _vec(posicion: int) -> list[float]:
    v = [0.0] * 1536
    v[posicion] = 1.0
    return v


def _doc(conn, organismo_id, titulo, textos, posiciones):
    docs.crear_documento(conn, organismo_id, titulo, f"{titulo}.pdf", "a@b.c", textos, [_vec(p) for p in posiciones])
    conn.commit()


def _embed(posicion):
    return lambda textos: [_vec(posicion) for _ in textos]


def test_devuelve_fragmentos_de_documentos_de_todos_los_organismos(db_conn, clean_db):
    uno = crear_organismo(db_conn, "Organismo uno")
    otro = crear_organismo(db_conn, "Organismo otro")
    _doc(db_conn, uno, "Reglamento uno", ["horarios de atención en Orán"], [0])
    _doc(db_conn, otro, "Guía otro", ["horarios de atención en Tartagal"], [0])
    resultados = buscar_documentos_chunks(db_conn, _embed(0), "horarios")
    assert {r["organismo"] for r in resultados} == {"Organismo uno", "Organismo otro"}


def test_resultado_incluye_titulo_y_nombre_del_organismo(db_conn, clean_db):
    org = crear_organismo(db_conn, "Registro Civil")
    _doc(db_conn, org, "Reglamento interno", ["texto del reglamento"], [0])
    r = buscar_documentos_chunks(db_conn, _embed(0), "reglamento")[0]
    assert r["titulo"] == "Reglamento interno" and r["organismo"] == "Registro Civil"
    assert r["texto"] == "texto del reglamento" and r["documento_id"] and r["chunk_id"]


def test_descarta_fragmentos_bajo_el_umbral_de_similitud(db_conn, clean_db):
    org = crear_organismo(db_conn)
    _doc(db_conn, org, "Doc", ["algo sin relación"], [5])
    assert buscar_documentos_chunks(db_conn, _embed(0), "consulta distinta") == []
    assert 0 < UMBRAL_SIMILITUD < 1


def test_encuentra_por_texto_aunque_el_vector_no_alcance(db_conn, clean_db):
    org = crear_organismo(db_conn)
    _doc(db_conn, org, "Delegaciones", ["La delegación de Orán atiende en calle España"], [5])
    resultados = buscar_documentos_chunks(db_conn, _embed(0), "Orán")
    assert [r["titulo"] for r in resultados] == ["Delegaciones"]


def test_sin_coincidencias_devuelve_lista_vacia(db_conn, clean_db):
    assert buscar_documentos_chunks(db_conn, _embed(0), "nada") == []


def test_respeta_top_k(db_conn, clean_db):
    org = crear_organismo(db_conn)
    _doc(db_conn, org, "Doc", [f"fragmento {i}" for i in range(8)], [0] * 8)
    assert len(buscar_documentos_chunks(db_conn, _embed(0), "fragmento", top_k=3)) == 3
