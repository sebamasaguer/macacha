import pytest
from fastapi.testclient import TestClient

from agent import api
from agent.admin import repository as admin_repository
from agent.admin import security as admin_security
from agent.api import obtener_pool
from ingest import repository as repo


class _FakeConnCtx:
    def __init__(self, conn):
        self._conn = conn

    def __enter__(self):
        return self._conn

    def __exit__(self, *args):
        pass


class _FakePool:
    def __init__(self, conn):
        self._conn = conn

    def connection(self):
        return _FakeConnCtx(self._conn)


def _loguear(client, conn, rol="super_admin", organismo_id=None, email="admin@macacha.gob.ar", puede=False):
    password = "secreta123"
    admin_repository.crear_admin(
        conn, email, admin_security.hash_password(password), rol, organismo_id, puede_crear_formularios=puede
    )
    conn.commit()
    client.post("/admin/login", json={"email": email, "password": password})


@pytest.fixture
def cliente(db_conn, clean_db, monkeypatch):
    monkeypatch.setenv("ADMIN_JWT_SECRET", "secreto-de-test")
    api.app.dependency_overrides[obtener_pool] = lambda: _FakePool(db_conn)
    yield TestClient(api.app, base_url="https://testserver")
    api.app.dependency_overrides.clear()


def _admin(conn, email):
    return admin_repository.obtener_admin_por_email(conn, email)


def test_crear_admin_no_puede_crear_formularios_por_defecto(db_conn, clean_db):
    organismo_id = repo.upsert_organismo(db_conn, "Trabajo")
    admin_repository.crear_admin(db_conn, "a@x.com", "hash", "admin_organismo", organismo_id)

    assert admin_repository.obtener_admin_por_id(db_conn, _admin(db_conn, "a@x.com")["id"])["puede_crear_formularios"] is False


def test_crear_admin_con_permiso(db_conn, clean_db):
    organismo_id = repo.upsert_organismo(db_conn, "Trabajo")
    admin_repository.crear_admin(db_conn, "a@x.com", "hash", "admin_organismo", organismo_id, puede_crear_formularios=True)

    assert admin_repository.obtener_admin_por_id(db_conn, _admin(db_conn, "a@x.com")["id"])["puede_crear_formularios"] is True


def test_volver_a_crear_el_admin_no_pisa_el_permiso(db_conn, clean_db):
    # El comando create_admin se puede volver a correr para cambiar la contraseña.
    organismo_id = repo.upsert_organismo(db_conn, "Trabajo")
    admin_repository.crear_admin(db_conn, "a@x.com", "hash", "admin_organismo", organismo_id, puede_crear_formularios=True)
    admin_repository.crear_admin(db_conn, "a@x.com", "hash2", "admin_organismo", organismo_id)

    assert admin_repository.obtener_admin_por_id(db_conn, _admin(db_conn, "a@x.com")["id"])["puede_crear_formularios"] is True


def test_editar_admin_cambia_el_permiso_y_none_lo_deja_igual(db_conn, clean_db):
    organismo_id = repo.upsert_organismo(db_conn, "Trabajo")
    admin_repository.crear_admin(db_conn, "a@x.com", "hash", "admin_organismo", organismo_id)
    admin_id = _admin(db_conn, "a@x.com")["id"]

    admin_repository.editar_admin(db_conn, admin_id, "admin_organismo", organismo_id, True, puede_crear_formularios=True)
    assert admin_repository.obtener_admin_por_id(db_conn, admin_id)["puede_crear_formularios"] is True

    admin_repository.editar_admin(db_conn, admin_id, "admin_organismo", organismo_id, True)
    assert admin_repository.obtener_admin_por_id(db_conn, admin_id)["puede_crear_formularios"] is True


def test_listar_admins_incluye_el_permiso(db_conn, clean_db):
    organismo_id = repo.upsert_organismo(db_conn, "Trabajo")
    admin_repository.crear_admin(db_conn, "a@x.com", "hash", "admin_organismo", organismo_id, puede_crear_formularios=True)

    assert admin_repository.listar_admins(db_conn)[0]["puede_crear_formularios"] is True


def test_admin_me_super_admin_siempre_puede(cliente, db_conn):
    _loguear(cliente, db_conn)

    assert cliente.get("/admin/me").json()["puede_crear_formularios"] is True


@pytest.mark.parametrize("puede", [False, True])
def test_admin_me_organismo_refleja_el_permiso(cliente, db_conn, puede):
    organismo_id = repo.upsert_organismo(db_conn, "Trabajo")
    _loguear(cliente, db_conn, rol="admin_organismo", organismo_id=organismo_id, puede=puede)

    assert cliente.get("/admin/me").json()["puede_crear_formularios"] is puede


def test_super_admin_habilita_y_deshabilita_desde_usuarios(cliente, db_conn):
    organismo_id = repo.upsert_organismo(db_conn, "Trabajo")
    admin_repository.crear_admin(db_conn, "org@x.com", "hash", "admin_organismo", organismo_id)
    db_conn.commit()
    _loguear(cliente, db_conn)
    admin_id = _admin(db_conn, "org@x.com")["id"]
    cuerpo = {"rol": "admin_organismo", "organismo_id": organismo_id, "activo": True, "puede_crear_formularios": True}

    assert cliente.put(f"/admin/usuarios/{admin_id}", json=cuerpo).status_code == 200
    assert next(u for u in cliente.get("/admin/usuarios").json() if u["email"] == "org@x.com")["puede_crear_formularios"] is True

    cuerpo["puede_crear_formularios"] = False
    cliente.put(f"/admin/usuarios/{admin_id}", json=cuerpo)
    assert next(u for u in cliente.get("/admin/usuarios").json() if u["email"] == "org@x.com")["puede_crear_formularios"] is False


def test_el_permiso_no_se_guarda_en_un_super_admin(cliente, db_conn):
    admin_repository.crear_admin(db_conn, "otro@x.com", "hash", "super_admin", None)
    db_conn.commit()
    _loguear(cliente, db_conn)
    admin_id = _admin(db_conn, "otro@x.com")["id"]

    cliente.put(
        f"/admin/usuarios/{admin_id}",
        json={"rol": "super_admin", "organismo_id": None, "activo": True, "puede_crear_formularios": True},
    )

    assert admin_repository.obtener_admin_por_id(db_conn, admin_id)["puede_crear_formularios"] is False


def test_crear_usuario_de_organismo_con_permiso(cliente, db_conn):
    organismo_id = repo.upsert_organismo(db_conn, "Trabajo")
    _loguear(cliente, db_conn)

    respuesta = cliente.post(
        "/admin/usuarios",
        json={
            "email": "nuevo@x.com",
            "password": "secreta123",
            "rol": "admin_organismo",
            "organismo_id": organismo_id,
            "puede_crear_formularios": True,
        },
    )

    assert respuesta.status_code == 200
    assert admin_repository.obtener_admin_por_id(db_conn, _admin(db_conn, "nuevo@x.com")["id"])["puede_crear_formularios"] is True


def test_retirar_el_permiso_se_nota_sin_volver_a_iniciar_sesion(cliente, db_conn):
    organismo_id = repo.upsert_organismo(db_conn, "Trabajo")
    _loguear(cliente, db_conn, rol="admin_organismo", organismo_id=organismo_id, puede=True)
    assert cliente.get("/admin/me").json()["puede_crear_formularios"] is True

    admin_id = _admin(db_conn, "admin@macacha.gob.ar")["id"]
    admin_repository.editar_admin(db_conn, admin_id, "admin_organismo", organismo_id, True, puede_crear_formularios=False)
    db_conn.commit()

    assert cliente.get("/admin/me").json()["puede_crear_formularios"] is False
