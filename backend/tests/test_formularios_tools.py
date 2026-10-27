import json
from datetime import datetime, timedelta, timezone

import pytest

from agent import formularios_tools, sessions, tools
from agent.admin import formularios_repository as formularios
from tests.formularios_helpers import (
    crear_formulario,
    crear_organismo,
    crear_sesion,
    crear_tramite,
    valores_validos,
)


@pytest.fixture
def mails(monkeypatch):
    enviados = []
    monkeypatch.setattr(
        formularios_tools.mail,
        "enviar_mail",
        lambda destinatarios, asunto, cuerpo_texto: enviados.append((destinatarios, asunto, cuerpo_texto)),
    )
    return enviados


def _consultar(conn, sesion, formulario_id, llamada="call_1"):
    """Reproduce en el historial lo que deja buscar_formularios: la llamada y su resultado."""
    sessions.guardar_mensaje(
        conn,
        sesion,
        "assistant",
        None,
        tool_calls=[{"id": llamada, "type": "function", "function": {"name": "buscar_formularios", "arguments": "{}"}}],
    )
    sessions.guardar_mensaje(conn, sesion, "tool", json.dumps([{"id": formulario_id}]), tool_call_id=llamada)


def _responder(conn, sesion, cantidad):
    """La persona escribe: primero los datos y después la confirmación del resumen."""
    for _ in range(cantidad):
        sessions.guardar_mensaje(conn, sesion, "user", "mensaje de la persona")


def _guardar(conn, sesion, formulario_id, mensajes_de_la_persona=2, **cambios):
    _responder(conn, sesion, mensajes_de_la_persona)
    argumentos = {"formulario_id": formulario_id, "valores": valores_validos(), "confirmado": True}
    argumentos.update(cambios)
    return formularios_tools.guardar_respuesta_formulario(conn, sesion, argumentos)


def _cantidad(conn, formulario_id):
    return formularios.listar_respuestas(conn, formulario_id, 1, 10)[1]


def test_buscar_formularios_devuelve_los_abiertos_con_campos_y_aviso(db_conn, clean_db):
    organismo_id = crear_organismo(db_conn)
    crear_formulario(db_conn, organismo_id, nombre="Abierto")
    crear_formulario(db_conn, organismo_id, nombre="Cerrado", estado="cerrado")

    resultado = formularios_tools.buscar_formularios(db_conn, {"consulta": "capacitación"})

    assert [f["nombre"] for f in resultado] == ["Abierto"]
    formulario = resultado[0]
    assert set(formulario) == {"id", "nombre", "organismo", "descripcion_uso", "aviso_finalidad", "campos"}
    assert formulario["organismo"] == "Subsecretaría de Trabajo"
    assert "inscribirte" in formulario["aviso_finalidad"]
    assert {c["tipo"] for c in formulario["campos"]} == {"texto", "dni", "telefono", "si_no"}
    json.dumps(resultado)  # tiene que ser serializable: el orquestador lo guarda como JSON


def test_buscar_formularios_prioriza_el_vinculado_al_tramite(db_conn, clean_db):
    organismo_id = crear_organismo(db_conn)
    tramite_id = crear_tramite(db_conn, organismo_id)
    crear_formulario(db_conn, organismo_id, nombre="Aaa común")
    crear_formulario(db_conn, organismo_id, nombre="Zzz vinculado", tramite_id=tramite_id)

    resultado = formularios_tools.buscar_formularios(db_conn, {"tramite_id": tramite_id})

    assert resultado[0]["nombre"] == "Zzz vinculado"


@pytest.mark.parametrize("confirmado", [False, None, "true", "sí", 1])
def test_no_guarda_si_la_persona_no_confirmo(db_conn, clean_db, mails, confirmado):
    organismo_id = crear_organismo(db_conn)
    formulario_id = crear_formulario(db_conn, organismo_id)
    sesion = crear_sesion(db_conn)
    _consultar(db_conn, sesion, formulario_id)

    resultado = _guardar(db_conn, sesion, formulario_id, confirmado=confirmado)

    assert resultado["ok"] is False and resultado["motivo"] == "no_confirmado"
    assert _cantidad(db_conn, formulario_id) == 0 and mails == []


def test_no_guarda_si_falta_el_campo_confirmado(db_conn, clean_db, mails):
    organismo_id = crear_organismo(db_conn)
    formulario_id = crear_formulario(db_conn, organismo_id)
    sesion = crear_sesion(db_conn)
    _consultar(db_conn, sesion, formulario_id)

    resultado = formularios_tools.guardar_respuesta_formulario(
        db_conn, sesion, {"formulario_id": formulario_id, "valores": valores_validos()}
    )

    assert resultado["motivo"] == "no_confirmado" and _cantidad(db_conn, formulario_id) == 0


@pytest.mark.parametrize("identificador", ["abc", "00000000-0000-0000-0000-000000000000", ""])
def test_no_guarda_un_formulario_que_no_se_consulto_en_la_sesion(db_conn, clean_db, mails, identificador):
    sesion = crear_sesion(db_conn)

    resultado = _guardar(db_conn, sesion, identificador)

    assert resultado["ok"] is False and resultado["motivo"] == "formulario_no_consultado"


def test_un_formulario_consultado_en_otra_sesion_no_sirve(db_conn, clean_db, mails):
    organismo_id = crear_organismo(db_conn)
    formulario_id = crear_formulario(db_conn, organismo_id)
    otra = crear_sesion(db_conn)
    _consultar(db_conn, otra, formulario_id)

    resultado = _guardar(db_conn, crear_sesion(db_conn), formulario_id)

    assert resultado["motivo"] == "formulario_no_consultado" and _cantidad(db_conn, formulario_id) == 0


def test_guardar_una_respuesta_confirmada_la_registra_y_avisa_al_organismo(db_conn, clean_db, mails):
    organismo_id = crear_organismo(db_conn)
    with db_conn.cursor() as cur:
        cur.execute("UPDATE organismos SET email_contacto = 'trabajo@gob.ar' WHERE id = %s", (organismo_id,))
    formulario_id = crear_formulario(db_conn, organismo_id)
    sesion = crear_sesion(db_conn)
    _consultar(db_conn, sesion, formulario_id)

    resultado = _guardar(db_conn, sesion, formulario_id)

    assert resultado == {"ok": True, "formulario": "Inscripción a la capacitación"}
    respuestas, total = formularios.listar_respuestas(db_conn, formulario_id, 1, 10)
    assert total == 1 and respuestas[0]["valores"]["dni"] == "30123456"
    destinatarios, asunto, cuerpo = mails[0]
    assert destinatarios == ["trabajo@gob.ar"]
    assert "Inscripción a la capacitación" in asunto
    assert "DNI: 30123456" in cuerpo
    assert "Nombre y apellido: Ana Pérez" in cuerpo
    assert "¿Participaría de la capacitación?: Sí" in cuerpo


def test_la_respuesta_queda_confirmada_en_la_base_sin_esperar_al_final_del_turno(db_conn, clean_db, mails):
    organismo_id = crear_organismo(db_conn)
    formulario_id = crear_formulario(db_conn, organismo_id)
    sesion = crear_sesion(db_conn)
    _consultar(db_conn, sesion, formulario_id)
    db_conn.commit()

    _guardar(db_conn, sesion, formulario_id)
    db_conn.rollback()  # si el turno falla después, lo guardado no se pierde

    assert _cantidad(db_conn, formulario_id) == 1


def test_datos_invalidos_devuelve_el_error_de_cada_campo_y_no_guarda(db_conn, clean_db, mails):
    organismo_id = crear_organismo(db_conn)
    formulario_id = crear_formulario(db_conn, organismo_id)
    sesion = crear_sesion(db_conn)
    _consultar(db_conn, sesion, formulario_id)

    resultado = _guardar(db_conn, sesion, formulario_id, valores=valores_validos(dni="123"))

    assert resultado["ok"] is False and resultado["motivo"] == "datos_invalidos"
    assert set(resultado["errores"]) == {"dni"} and "DNI" in resultado["errores"]["dni"]
    assert _cantidad(db_conn, formulario_id) == 0 and mails == []


@pytest.mark.parametrize("valores", [None, "texto", ["lista"], 5])
def test_valores_que_no_son_un_objeto_se_rechazan(db_conn, clean_db, mails, valores):
    organismo_id = crear_organismo(db_conn)
    formulario_id = crear_formulario(db_conn, organismo_id)
    sesion = crear_sesion(db_conn)
    _consultar(db_conn, sesion, formulario_id)

    resultado = _guardar(db_conn, sesion, formulario_id, valores=valores)

    assert resultado["ok"] is False and resultado["motivo"] == "datos_invalidos"


def test_un_dni_repetido_devuelve_duplicado(db_conn, clean_db, mails):
    organismo_id = crear_organismo(db_conn)
    formulario_id = crear_formulario(db_conn, organismo_id)
    primera, segunda = crear_sesion(db_conn), crear_sesion(db_conn)
    _consultar(db_conn, primera, formulario_id)
    _consultar(db_conn, segunda, formulario_id)
    _guardar(db_conn, primera, formulario_id)

    resultado = _guardar(db_conn, segunda, formulario_id, valores=valores_validos(dni="30.123.456"))

    assert resultado["ok"] is False and resultado["motivo"] == "duplicado"
    assert _cantidad(db_conn, formulario_id) == 1 and len(mails) == 1


def test_un_segundo_envio_de_la_misma_sesion_devuelve_ya_registrada(db_conn, clean_db, mails):
    organismo_id = crear_organismo(db_conn)
    formulario_id = crear_formulario(db_conn, organismo_id)
    sesion = crear_sesion(db_conn)
    _consultar(db_conn, sesion, formulario_id)
    _guardar(db_conn, sesion, formulario_id)

    resultado = _guardar(db_conn, sesion, formulario_id, valores=valores_validos(dni="40123456"))

    assert resultado["motivo"] == "ya_registrada" and _cantidad(db_conn, formulario_id) == 1


@pytest.mark.parametrize(
    "cambios, motivo",
    [
        ({"estado": "cerrado"}, "cerrado"),
        ({"fecha_cierre": datetime.now(timezone.utc) - timedelta(hours=1)}, "cerrado"),
    ],
)
def test_un_formulario_que_ya_no_esta_abierto_se_rechaza(db_conn, clean_db, mails, cambios, motivo):
    organismo_id = crear_organismo(db_conn)
    formulario_id = crear_formulario(db_conn, organismo_id, **cambios)
    sesion = crear_sesion(db_conn)
    _consultar(db_conn, sesion, formulario_id)

    resultado = _guardar(db_conn, sesion, formulario_id)

    assert resultado == {"ok": False, "motivo": motivo}


def test_el_cupo_completo_devuelve_cupo(db_conn, clean_db, mails):
    organismo_id = crear_organismo(db_conn)
    formulario_id = crear_formulario(db_conn, organismo_id, cupo=1)
    primera, segunda = crear_sesion(db_conn), crear_sesion(db_conn)
    _consultar(db_conn, primera, formulario_id)
    _consultar(db_conn, segunda, formulario_id)
    _guardar(db_conn, primera, formulario_id)

    resultado = _guardar(db_conn, segunda, formulario_id, valores=valores_validos(dni="40123456"))

    assert resultado == {"ok": False, "motivo": "cupo"}


def test_una_sesion_no_puede_completar_mas_de_tres_formularios(db_conn, clean_db, mails):
    organismo_id = crear_organismo(db_conn)
    sesion = crear_sesion(db_conn)
    ids = [crear_formulario(db_conn, organismo_id, nombre=f"Formulario {i}") for i in range(4)]
    for numero, formulario_id in enumerate(ids, start=1):
        _consultar(db_conn, sesion, formulario_id, llamada=f"call_{numero}")

    resultados = [_guardar(db_conn, sesion, formulario_id) for formulario_id in ids]

    assert [r["ok"] for r in resultados] == [True, True, True, False]
    assert resultados[3]["motivo"] == "limite_sesion"
    assert _cantidad(db_conn, ids[3]) == 0


def test_un_fallo_del_mail_no_deshace_la_respuesta(db_conn, clean_db, monkeypatch):
    def fallar(*args, **kwargs):
        raise RuntimeError("smtp caído")

    monkeypatch.setattr(formularios_tools.mail, "enviar_mail", fallar)
    organismo_id = crear_organismo(db_conn)
    formulario_id = crear_formulario(db_conn, organismo_id)
    sesion = crear_sesion(db_conn)
    _consultar(db_conn, sesion, formulario_id)

    resultado = _guardar(db_conn, sesion, formulario_id)

    assert resultado["ok"] is True and _cantidad(db_conn, formulario_id) == 1


def test_las_herramientas_estan_registradas_y_se_despachan(db_conn, clean_db, mails):
    nombres = [t["function"]["name"] for t in tools.TOOL_SCHEMAS]
    assert "buscar_formularios" in nombres and "guardar_respuesta_formulario" in nombres
    guardar = next(t for t in tools.TOOL_SCHEMAS if t["function"]["name"] == "guardar_respuesta_formulario")
    assert set(guardar["function"]["parameters"]["required"]) == {"formulario_id", "valores", "confirmado"}

    organismo_id = crear_organismo(db_conn)
    formulario_id = crear_formulario(db_conn, organismo_id)
    sesion = crear_sesion(db_conn)
    _consultar(db_conn, sesion, formulario_id)
    _responder(db_conn, sesion, 2)

    encontrados = tools.ejecutar_tool("buscar_formularios", {}, db_conn, None, None, session_id=sesion)
    guardado = tools.ejecutar_tool(
        "guardar_respuesta_formulario",
        {"formulario_id": formulario_id, "valores": valores_validos(), "confirmado": True},
        db_conn,
        None,
        None,
        session_id=sesion,
    )

    assert encontrados[0]["id"] == formulario_id and guardado["ok"] is True


@pytest.mark.parametrize("mensajes", [0, 1])
def test_no_guarda_si_la_persona_no_alcanzo_a_dar_los_datos_y_confirmar(db_conn, clean_db, mails, mensajes):
    # Con un solo mensaje de la persona después de la consulta, el asistente no pudo resumir y esperar la confirmación.
    organismo_id = crear_organismo(db_conn)
    formulario_id = crear_formulario(db_conn, organismo_id)
    sesion = crear_sesion(db_conn)
    _consultar(db_conn, sesion, formulario_id)

    resultado = _guardar(db_conn, sesion, formulario_id, mensajes_de_la_persona=mensajes)

    assert resultado["ok"] is False and resultado["motivo"] == "no_confirmado"
    assert "resum" in resultado["detalle"].lower()
    assert _cantidad(db_conn, formulario_id) == 0 and mails == []


def test_guarda_cuando_la_persona_dio_los_datos_y_despues_confirmo(db_conn, clean_db, mails):
    organismo_id = crear_organismo(db_conn)
    formulario_id = crear_formulario(db_conn, organismo_id)
    sesion = crear_sesion(db_conn)
    _consultar(db_conn, sesion, formulario_id)
    _responder(db_conn, sesion, 1)  # los datos; el asistente resume y pregunta

    assert _guardar(db_conn, sesion, formulario_id, mensajes_de_la_persona=1)["ok"] is True


def test_los_mensajes_anteriores_a_la_consulta_no_cuentan_como_confirmacion(db_conn, clean_db, mails):
    organismo_id = crear_organismo(db_conn)
    formulario_id = crear_formulario(db_conn, organismo_id)
    sesion = crear_sesion(db_conn)
    _responder(db_conn, sesion, 3)
    _consultar(db_conn, sesion, formulario_id)

    resultado = _guardar(db_conn, sesion, formulario_id, mensajes_de_la_persona=1)

    assert resultado["motivo"] == "no_confirmado" and _cantidad(db_conn, formulario_id) == 0
