import pytest
from fastapi.testclient import TestClient

from agent import api
from agent.admin import documentos_repository as docs
from agent.api import obtener_openai_client, obtener_pool
from ingest.documento_texto import MAX_BYTES
from tests.formularios_helpers import FakePool, crear_organismo, loguear
from tests.test_documento_texto import PARRAFO, _docx, _pdf


class FakeOpenAI:
    def generate_embeddings(self, textos):
        return [[0.1] * 1536 for _ in textos]


@pytest.fixture
def cliente(db_conn, clean_db, monkeypatch):
    monkeypatch.setenv("ADMIN_JWT_SECRET", "secreto-de-test")
    api.app.dependency_overrides[obtener_pool] = lambda: FakePool(db_conn)
    api.app.dependency_overrides[obtener_openai_client] = lambda: FakeOpenAI()
    yield TestClient(api.app, base_url="https://testserver")
    api.app.dependency_overrides.clear()


def _archivo(nombre="Reglamento.docx", contenido=None):
    return {"archivo": (nombre, contenido if contenido is not None else _docx([PARRAFO * 3]), "application/octet-stream")}


def _subir(cliente, titulo=None, organismo_id=None, **archivo):
    datos = {}
    if titulo is not None:
        datos["titulo"] = titulo
    if organismo_id is not None:
        datos["organismo_id"] = str(organismo_id)
    return cliente.post("/admin/documentos", data=datos, files=_archivo(**archivo))


def test_sin_sesion_devuelve_401(cliente):
    assert cliente.get("/admin/documentos").status_code == 401
    assert _subir(cliente).status_code == 401
    assert cliente.delete("/admin/documentos/00000000-0000-0000-0000-000000000000").status_code == 401


def test_admin_organismo_sube_documento_a_su_organismo(cliente, db_conn):
    mio = crear_organismo(db_conn)
    otro = crear_organismo(db_conn, "Otro organismo")
    loguear(cliente, db_conn, organismo_id=mio, puede=False)
    r = _subir(cliente, titulo="Reglamento interno", organismo_id=otro)
    assert r.status_code == 201
    cuerpo = r.json()
    assert cuerpo["organismo_id"] == mio and cuerpo["titulo"] == "Reglamento interno"
    assert cuerpo["fragmentos"] >= 1 and cuerpo["subido_por_email"] == "admin@organismo.gob.ar"


def test_super_admin_debe_indicar_organismo(cliente, db_conn):
    org = crear_organismo(db_conn)
    loguear(cliente, db_conn, rol="super_admin", organismo_id=None)
    assert _subir(cliente).status_code == 400
    assert _subir(cliente, organismo_id=org).status_code == 201
    assert _subir(cliente, organismo_id=99999).status_code == 400


def test_titulo_por_defecto_es_el_nombre_del_archivo(cliente, db_conn):
    loguear(cliente, db_conn, organismo_id=crear_organismo(db_conn))
    assert _subir(cliente, nombre="Delegaciones del interior.docx").json()["titulo"] == "Delegaciones del interior"


def test_cuarto_documento_devuelve_409(cliente, db_conn):
    loguear(cliente, db_conn, organismo_id=crear_organismo(db_conn))
    for i in range(3):
        assert _subir(cliente, titulo=f"Doc {i}").status_code == 201
    r = _subir(cliente, titulo="Doc 4")
    assert r.status_code == 409 and "3 documentos" in r.json()["detail"]


def test_archivo_no_admitido_devuelve_400(cliente, db_conn):
    loguear(cliente, db_conn, organismo_id=crear_organismo(db_conn))
    r = _subir(cliente, nombre="notas.txt", contenido=b"hola")
    assert r.status_code == 400 and "PDF o Word" in r.json()["detail"]


def test_pdf_invalido_devuelve_400(cliente, db_conn):
    loguear(cliente, db_conn, organismo_id=crear_organismo(db_conn))
    assert _subir(cliente, nombre="roto.pdf", contenido=b"no es pdf").status_code == 400


def test_archivo_mayor_a_10mb_devuelve_413(cliente, db_conn):
    loguear(cliente, db_conn, organismo_id=crear_organismo(db_conn))
    assert _subir(cliente, nombre="grande.pdf", contenido=b"0" * (MAX_BYTES + 1)).status_code == 413


def test_reemplazar_cambia_los_fragmentos(cliente, db_conn):
    org = crear_organismo(db_conn)
    loguear(cliente, db_conn, organismo_id=org)
    doc = _subir(cliente, titulo="Mi doc").json()
    nuevo = "Texto totalmente nuevo sobre la delegación de Tartagal. " * 8
    r = cliente.put(f"/admin/documentos/{doc['id']}", files=_archivo("v2.docx", _docx([nuevo])))
    assert r.status_code == 200
    assert r.json()["titulo"] == "Mi doc" and r.json()["nombre_archivo"] == "v2.docx"
    with db_conn.cursor() as cur:
        cur.execute("SELECT texto FROM organismo_documento_chunks WHERE documento_id = %s", (doc["id"],))
        assert all("Tartagal" in fila[0] for fila in cur.fetchall())


def test_reemplazar_con_escaneo_devuelve_400_y_deja_el_original(cliente, db_conn):
    loguear(cliente, db_conn, organismo_id=crear_organismo(db_conn))
    doc = _subir(cliente, titulo="Original").json()
    r = cliente.put(f"/admin/documentos/{doc['id']}", files=_archivo("escaneo.pdf", _pdf(["x"])))
    assert r.status_code == 400
    despues = docs.obtener_documento(db_conn, doc["id"])
    assert despues["nombre_archivo"] == "Reglamento.docx" and despues["fragmentos"] == doc["fragmentos"]


def test_solo_cambiar_titulo(cliente, db_conn):
    loguear(cliente, db_conn, organismo_id=crear_organismo(db_conn))
    doc = _subir(cliente, titulo="Viejo").json()
    r = cliente.put(f"/admin/documentos/{doc['id']}", data={"titulo": "Nuevo"})
    assert r.status_code == 200 and r.json()["titulo"] == "Nuevo" and r.json()["fragmentos"] == doc["fragmentos"]


def test_put_sin_archivo_ni_titulo_devuelve_400(cliente, db_conn):
    loguear(cliente, db_conn, organismo_id=crear_organismo(db_conn))
    doc = _subir(cliente).json()
    assert cliente.put(f"/admin/documentos/{doc['id']}", data={}).status_code == 400


def test_admin_de_otro_organismo_recibe_404_al_reemplazar_y_borrar(cliente, db_conn):
    ajeno_org = crear_organismo(db_conn, "Ajeno")
    ajeno = docs.crear_documento(db_conn, ajeno_org, "Ajeno", "a.pdf", "x@y.z", ["t"], [[0.1] * 1536])
    db_conn.commit()
    loguear(cliente, db_conn, organismo_id=crear_organismo(db_conn))
    assert cliente.put(f"/admin/documentos/{ajeno['id']}", data={"titulo": "Mío"}).status_code == 404
    assert cliente.delete(f"/admin/documentos/{ajeno['id']}").status_code == 404
    assert docs.obtener_documento(db_conn, ajeno["id"])["titulo"] == "Ajeno"


def test_listar_solo_muestra_los_del_propio_organismo(cliente, db_conn):
    ajeno_org = crear_organismo(db_conn, "Ajeno")
    docs.crear_documento(db_conn, ajeno_org, "Ajeno", "a.pdf", "x@y.z", ["t"], [[0.1] * 1536])
    mio = crear_organismo(db_conn)
    db_conn.commit()
    loguear(cliente, db_conn, organismo_id=mio)
    _subir(cliente, titulo="Mío")
    assert [d["titulo"] for d in cliente.get("/admin/documentos").json()] == ["Mío"]


def test_super_admin_lista_todos_y_puede_filtrar(cliente, db_conn):
    uno = crear_organismo(db_conn, "Uno")
    otro = crear_organismo(db_conn, "Otro")
    docs.crear_documento(db_conn, uno, "De uno", "a.pdf", "x@y.z", ["t"], [[0.1] * 1536])
    docs.crear_documento(db_conn, otro, "De otro", "b.pdf", "x@y.z", ["t"], [[0.1] * 1536])
    db_conn.commit()
    loguear(cliente, db_conn, rol="super_admin", organismo_id=None)
    assert len(cliente.get("/admin/documentos").json()) == 2
    assert [d["titulo"] for d in cliente.get(f"/admin/documentos?organismo_id={uno}").json()] == ["De uno"]


def test_borrar_devuelve_204(cliente, db_conn):
    loguear(cliente, db_conn, organismo_id=crear_organismo(db_conn))
    doc = _subir(cliente).json()
    assert cliente.delete(f"/admin/documentos/{doc['id']}").status_code == 204
    assert cliente.get("/admin/documentos").json() == []
