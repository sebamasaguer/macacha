import pytest
from fastapi.testclient import TestClient

from agent import api, sessions
from agent.admin import formularios_repository as formularios
from agent.api import obtener_pool
from tests.formularios_helpers import (
    FakePool,
    crear_formulario,
    crear_organismo,
    crear_sesion,
    crear_tramite,
    cuerpo_formulario,
    loguear,
    valores_validos,
)


@pytest.fixture
def cliente(db_conn, clean_db, monkeypatch):
    monkeypatch.setenv("ADMIN_JWT_SECRET", "secreto-de-test")
    api.app.dependency_overrides[obtener_pool] = lambda: FakePool(db_conn)
    yield TestClient(api.app, base_url="https://testserver")
    api.app.dependency_overrides.clear()


def _con_respuesta(db_conn, organismo_id, **valores):
    formulario_id = crear_formulario(db_conn, organismo_id)
    sesion = crear_sesion(db_conn)
    respuesta = formularios.guardar_respuesta(db_conn, formulario_id, sesion, valores_validos(**valores))
    db_conn.commit()
    return formulario_id, respuesta["id"], sesion


def test_sin_sesion_todo_devuelve_401(cliente):
    assert cliente.get("/admin/formularios").status_code == 401
    assert cliente.post("/admin/formularios", json=cuerpo_formulario()).status_code == 401
    assert cliente.get("/admin/formularios/00000000-0000-0000-0000-000000000000/respuestas.csv").status_code == 401


def test_un_usuario_no_habilitado_ve_pero_no_edita(cliente, db_conn):
    organismo_id = crear_organismo(db_conn)
    formulario_id, respuesta_id, _ = _con_respuesta(db_conn, organismo_id)
    loguear(cliente, db_conn, organismo_id=organismo_id, puede=False)

    assert cliente.get("/admin/formularios").status_code == 200
    assert cliente.get(f"/admin/formularios/{formulario_id}").status_code == 200
    assert cliente.get(f"/admin/formularios/{formulario_id}/respuestas").status_code == 200
    assert cliente.get(f"/admin/formularios/{formulario_id}/respuestas.csv").status_code == 200
    assert cliente.get(f"/admin/formularios/{formulario_id}/respuestas/{respuesta_id}").status_code == 200
    assert cliente.post("/admin/formularios", json=cuerpo_formulario()).status_code == 403
    assert cliente.put(f"/admin/formularios/{formulario_id}", json=cuerpo_formulario()).status_code == 403
    assert cliente.delete(f"/admin/formularios/{formulario_id}/respuestas/{respuesta_id}").status_code == 403
    assert formularios.listar_respuestas(db_conn, formulario_id, 1, 10)[1] == 1


def test_un_usuario_habilitado_crea_un_formulario_en_su_organismo(cliente, db_conn):
    organismo_id = crear_organismo(db_conn)
    otro = crear_organismo(db_conn, "Registro Civil")
    loguear(cliente, db_conn, organismo_id=organismo_id)

    respuesta = cliente.post("/admin/formularios", json=cuerpo_formulario(organismo_id=otro))

    assert respuesta.status_code == 200
    formulario = formularios.obtener_formulario(db_conn, respuesta.json()["id"])
    assert formulario["organismo_id"] == organismo_id
    assert formulario["creado_por_email"] == "admin@organismo.gob.ar"
    assert [c["clave"] for c in formulario["campos"]][:2] == ["nombre_y_apellido", "dni"]


def test_el_super_admin_elige_el_organismo(cliente, db_conn):
    organismo_id = crear_organismo(db_conn)
    loguear(cliente, db_conn, rol="super_admin", puede=False)

    sin_organismo = cliente.post("/admin/formularios", json=cuerpo_formulario())
    inexistente = cliente.post("/admin/formularios", json=cuerpo_formulario(organismo_id=99999))
    bien = cliente.post("/admin/formularios", json=cuerpo_formulario(organismo_id=organismo_id))

    assert sin_organismo.status_code == 400 and inexistente.status_code == 400
    assert bien.status_code == 200
    assert formularios.obtener_formulario(db_conn, bien.json()["id"])["organismo_id"] == organismo_id


def test_una_definicion_invalida_devuelve_400(cliente, db_conn):
    organismo_id = crear_organismo(db_conn)
    loguear(cliente, db_conn, organismo_id=organismo_id)
    dos_dni = cuerpo_formulario()
    dos_dni["campos"].append({"etiqueta": "Otro DNI", "tipo": "dni", "obligatorio": False})

    respuesta = cliente.post("/admin/formularios", json=dos_dni)

    assert respuesta.status_code == 400 and "DNI" in respuesta.json()["detail"]
    assert formularios.listar_formularios(db_conn, None, 1, 10)[1] == 0


@pytest.mark.parametrize("cambios", [{"nombre": ""}, {"cupo": 0}, {"campos": []}, {"estado": "inventado"}])
def test_el_cuerpo_invalido_devuelve_422(cliente, db_conn, cambios):
    organismo_id = crear_organismo(db_conn)
    loguear(cliente, db_conn, organismo_id=organismo_id)

    assert cliente.post("/admin/formularios", json=cuerpo_formulario(**cambios)).status_code == 422


def test_vincular_un_tramite_de_otro_organismo_se_rechaza(cliente, db_conn):
    trabajo = crear_organismo(db_conn)
    registro = crear_organismo(db_conn, "Registro Civil")
    ajeno = crear_tramite(db_conn, registro, "RC-0001", "Actas")
    propio = crear_tramite(db_conn, trabajo, "TR-0001", "Denuncia laboral")
    loguear(cliente, db_conn, organismo_id=trabajo)

    rechazado = cliente.post("/admin/formularios", json=cuerpo_formulario(tramite_id=ajeno))
    inexistente = cliente.post("/admin/formularios", json=cuerpo_formulario(tramite_id="NO-0000"))
    aceptado = cliente.post("/admin/formularios", json=cuerpo_formulario(tramite_id=propio))

    assert rechazado.status_code == 400 and inexistente.status_code == 400
    assert aceptado.status_code == 200
    assert formularios.obtener_formulario(db_conn, aceptado.json()["id"])["tramite_id"] == propio


def test_la_lista_se_limita_al_organismo_y_se_pagina(cliente, db_conn):
    trabajo = crear_organismo(db_conn)
    registro = crear_organismo(db_conn, "Registro Civil")
    for nombre in ("A", "B", "C"):
        crear_formulario(db_conn, trabajo, nombre=nombre)
    crear_formulario(db_conn, registro, nombre="Ajeno")
    db_conn.commit()
    loguear(cliente, db_conn, organismo_id=trabajo, puede=False)

    pagina = cliente.get("/admin/formularios", params={"page": 1, "page_size": 2}).json()

    assert pagina["total"] == 3 and len(pagina["formularios"]) == 2
    assert pagina["page"] == 1 and pagina["page_size"] == 2
    assert "Ajeno" not in {f["nombre"] for f in pagina["formularios"]}


def test_el_super_admin_ve_los_formularios_de_todos(cliente, db_conn):
    crear_formulario(db_conn, crear_organismo(db_conn), nombre="A")
    crear_formulario(db_conn, crear_organismo(db_conn, "Registro Civil"), nombre="B")
    db_conn.commit()
    loguear(cliente, db_conn, rol="super_admin", puede=False)

    assert cliente.get("/admin/formularios").json()["total"] == 2


@pytest.mark.parametrize("params", [{"page": 0}, {"page_size": 0}, {"page_size": 101}])
def test_la_lista_rechaza_paginacion_invalida(cliente, db_conn, params):
    loguear(cliente, db_conn, rol="super_admin", puede=False)

    assert cliente.get("/admin/formularios", params=params).status_code == 422


def test_lo_de_otro_organismo_devuelve_404_en_todos_los_endpoints(cliente, db_conn):
    trabajo = crear_organismo(db_conn)
    registro = crear_organismo(db_conn, "Registro Civil")
    formulario_id, respuesta_id, _ = _con_respuesta(db_conn, registro)
    loguear(cliente, db_conn, organismo_id=trabajo, puede=True)
    base = f"/admin/formularios/{formulario_id}"

    assert cliente.get(base).status_code == 404
    assert cliente.put(base, json=cuerpo_formulario()).status_code == 404
    assert cliente.get(f"{base}/respuestas").status_code == 404
    assert cliente.get(f"{base}/respuestas.csv").status_code == 404
    assert cliente.get(f"{base}/respuestas/{respuesta_id}").status_code == 404
    assert cliente.delete(f"{base}/respuestas/{respuesta_id}").status_code == 404
    assert formularios.listar_respuestas(db_conn, formulario_id, 1, 10)[1] == 1
    assert formularios.obtener_formulario(db_conn, formulario_id)["nombre"] == "Inscripción a la capacitación"


def test_formulario_inexistente_404_y_id_mal_formado_422(cliente, db_conn):
    loguear(cliente, db_conn, rol="super_admin", puede=False)

    assert cliente.get("/admin/formularios/00000000-0000-0000-0000-000000000000").status_code == 404
    assert cliente.get("/admin/formularios/no-es-uuid").status_code == 422


def test_editar_un_formulario_propio(cliente, db_conn):
    organismo_id = crear_organismo(db_conn)
    formulario_id = crear_formulario(db_conn, organismo_id)
    db_conn.commit()
    loguear(cliente, db_conn, organismo_id=organismo_id)
    cuerpo = cuerpo_formulario(nombre="Nuevo nombre", cupo=10)
    cuerpo["campos"] = formularios.obtener_formulario(db_conn, formulario_id)["campos"]

    respuesta = cliente.put(f"/admin/formularios/{formulario_id}", json=cuerpo)

    assert respuesta.status_code == 200
    formulario = formularios.obtener_formulario(db_conn, formulario_id)
    assert formulario["nombre"] == "Nuevo nombre" and formulario["cupo"] == 10


def test_una_regla_de_edicion_devuelve_409(cliente, db_conn):
    organismo_id = crear_organismo(db_conn)
    formulario_id, _, _ = _con_respuesta(db_conn, organismo_id)
    loguear(cliente, db_conn, organismo_id=organismo_id)
    cuerpo = cuerpo_formulario()
    cuerpo["campos"] = formularios.obtener_formulario(db_conn, formulario_id)["campos"][:2]

    respuesta = cliente.put(f"/admin/formularios/{formulario_id}", json=cuerpo)

    assert respuesta.status_code == 409 and "respuestas" in respuesta.json()["detail"]
    assert len(formularios.obtener_formulario(db_conn, formulario_id)["campos"]) == 4


def test_listar_respuestas_incluye_los_campos_para_armar_la_tabla(cliente, db_conn):
    organismo_id = crear_organismo(db_conn)
    formulario_id, respuesta_id, _ = _con_respuesta(db_conn, organismo_id)
    loguear(cliente, db_conn, organismo_id=organismo_id, puede=False)

    cuerpo = cliente.get(f"/admin/formularios/{formulario_id}/respuestas").json()

    assert cuerpo["total"] == 1
    assert cuerpo["respuestas"][0]["id"] == respuesta_id
    assert cuerpo["respuestas"][0]["valores"]["dni"] == "30123456"
    assert [c["clave"] for c in cuerpo["campos"]][1] == "dni"


def test_el_csv_se_descarga_con_bom_y_sin_formulas(cliente, db_conn):
    organismo_id = crear_organismo(db_conn)
    formulario_id, _, _ = _con_respuesta(db_conn, organismo_id, nombre="=1+1")
    loguear(cliente, db_conn, organismo_id=organismo_id, puede=False)

    respuesta = cliente.get(f"/admin/formularios/{formulario_id}/respuestas.csv")

    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"].startswith("text/csv")
    assert "attachment" in respuesta.headers["content-disposition"]
    assert respuesta.headers["content-disposition"].endswith('-respuestas.csv"')
    assert respuesta.content.startswith(b"\xef\xbb\xbf")
    texto = respuesta.content.decode("utf-8-sig")
    assert texto.splitlines()[0].startswith("Fecha,Nombre y apellido,DNI")
    assert "'=1+1" in texto


def test_el_detalle_de_una_respuesta_trae_la_conversacion_de_origen(cliente, db_conn):
    organismo_id = crear_organismo(db_conn)
    formulario_id, respuesta_id, sesion = _con_respuesta(db_conn, organismo_id)
    sessions.guardar_mensaje(db_conn, sesion, "user", "Quiero anotarme a la capacitación")
    db_conn.commit()
    loguear(cliente, db_conn, organismo_id=organismo_id, puede=False)

    cuerpo = cliente.get(f"/admin/formularios/{formulario_id}/respuestas/{respuesta_id}").json()

    assert cuerpo["session_id"] == sesion
    assert cuerpo["formulario"]["nombre"] == "Inscripción a la capacitación"
    assert any(m["contenido"] == "Quiero anotarme a la capacitación" for m in cuerpo["mensajes"])


def test_pedir_una_respuesta_con_el_id_de_otro_formulario_devuelve_404(cliente, db_conn):
    organismo_id = crear_organismo(db_conn)
    _, respuesta_id, _ = _con_respuesta(db_conn, organismo_id)
    otro = crear_formulario(db_conn, organismo_id, nombre="Otro")
    db_conn.commit()
    loguear(cliente, db_conn, organismo_id=organismo_id)

    assert cliente.get(f"/admin/formularios/{otro}/respuestas/{respuesta_id}").status_code == 404
    assert cliente.delete(f"/admin/formularios/{otro}/respuestas/{respuesta_id}").status_code == 404


def test_borrar_una_respuesta_la_saca_de_la_lista_y_registra_quien(cliente, db_conn):
    organismo_id = crear_organismo(db_conn)
    formulario_id, respuesta_id, _ = _con_respuesta(db_conn, organismo_id)
    loguear(cliente, db_conn, organismo_id=organismo_id)

    assert cliente.delete(f"/admin/formularios/{formulario_id}/respuestas/{respuesta_id}").status_code == 200

    assert cliente.get(f"/admin/formularios/{formulario_id}/respuestas").json()["total"] == 0
    assert cliente.delete(f"/admin/formularios/{formulario_id}/respuestas/{respuesta_id}").status_code == 404
    with db_conn.cursor() as cur:
        cur.execute("SELECT eliminada_por_email FROM formulario_respuestas WHERE id = %s", (respuesta_id,))
        assert cur.fetchone()[0] == "admin@organismo.gob.ar"


def test_retirar_el_permiso_a_un_usuario_con_sesion_iniciada_le_quita_la_edicion(cliente, db_conn):
    organismo_id = crear_organismo(db_conn)
    loguear(cliente, db_conn, organismo_id=organismo_id, puede=True)
    assert cliente.post("/admin/formularios", json=cuerpo_formulario()).status_code == 200

    with db_conn.cursor() as cur:
        cur.execute("UPDATE admins SET puede_crear_formularios = false WHERE email = 'admin@organismo.gob.ar'")
    db_conn.commit()

    assert cliente.post("/admin/formularios", json=cuerpo_formulario()).status_code == 403
    assert cliente.get("/admin/formularios").status_code == 200


def test_un_usuario_inactivo_no_gestiona_aunque_tenga_el_permiso(cliente, db_conn):
    organismo_id = crear_organismo(db_conn)
    loguear(cliente, db_conn, organismo_id=organismo_id, puede=True)
    with db_conn.cursor() as cur:
        cur.execute("UPDATE admins SET activo = false WHERE email = 'admin@organismo.gob.ar'")
    db_conn.commit()

    assert cliente.post("/admin/formularios", json=cuerpo_formulario()).status_code == 403


def test_el_super_admin_gestiona_formularios_de_cualquier_organismo(cliente, db_conn):
    organismo_id = crear_organismo(db_conn)
    formulario_id, respuesta_id, _ = _con_respuesta(db_conn, organismo_id)
    loguear(cliente, db_conn, rol="super_admin", puede=False)
    cuerpo = cuerpo_formulario(nombre="Editado por el super admin")
    cuerpo["campos"] = formularios.obtener_formulario(db_conn, formulario_id)["campos"]

    assert cliente.put(f"/admin/formularios/{formulario_id}", json=cuerpo).status_code == 200
    assert cliente.delete(f"/admin/formularios/{formulario_id}/respuestas/{respuesta_id}").status_code == 200
