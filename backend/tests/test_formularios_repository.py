import json
import os
import threading
from datetime import datetime, timedelta, timezone

import psycopg
import pytest

from agent import sessions
from agent.admin import formularios_repository as formularios
from agent.admin.formularios_repository import (
    DatosInvalidos,
    FormularioNoDisponible,
    ReglaDeEdicion,
    RespuestaDuplicada,
    YaRespondio,
    calcular_estado_efectivo,
)
from tests.formularios_helpers import (
    CAMPOS_TRABAJO,
    crear_formulario,
    crear_organismo,
    crear_sesion,
    crear_tramite,
    datos_formulario,
    valores_validos,
)

AHORA = datetime(2026, 10, 23, 12, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    "estado, fecha_cierre, cupo, respuestas, esperado",
    [
        ("borrador", None, None, 0, "borrador"),
        ("cerrado", None, None, 0, "cerrado"),
        ("activo", None, None, 0, "abierto"),
        ("activo", AHORA + timedelta(minutes=1), None, 0, "abierto"),
        ("activo", AHORA, None, 0, "vencido"),
        ("activo", AHORA - timedelta(days=1), None, 0, "vencido"),
        ("activo", None, 5, 4, "abierto"),
        ("activo", None, 5, 5, "cupo_completo"),
        ("activo", AHORA - timedelta(days=1), 5, 5, "vencido"),
    ],
)
def test_calcular_estado_efectivo(estado, fecha_cierre, cupo, respuestas, esperado):
    assert calcular_estado_efectivo(estado, fecha_cierre, cupo, respuestas, ahora=AHORA) == esperado


def test_crear_y_obtener_formulario_con_campos_y_claves(db_conn, clean_db):
    organismo_id = crear_organismo(db_conn)

    formulario_id = crear_formulario(db_conn, organismo_id, cupo=40)
    formulario = formularios.obtener_formulario(db_conn, formulario_id)

    assert formulario["nombre"] == "Inscripción a la capacitación"
    assert formulario["organismo"] == "Subsecretaría de Trabajo"
    assert formulario["estado_efectivo"] == "abierto"
    assert formulario["cupo"] == 40 and formulario["respuestas"] == 0 and formulario["hay_respuestas"] is False
    assert [c["clave"] for c in formulario["campos"]] == [
        "nombre_y_apellido", "dni", "telefono", "participaria_de_la_capacitacion",
    ]
    assert [c["tipo"] for c in formulario["campos"]] == ["texto", "dni", "telefono", "si_no"]


def test_obtener_un_formulario_inexistente_devuelve_none(db_conn, clean_db):
    assert formularios.obtener_formulario(db_conn, "00000000-0000-0000-0000-000000000000") is None


def test_crear_rechaza_una_definicion_invalida(db_conn, clean_db):
    organismo_id = crear_organismo(db_conn)
    dos_dni = CAMPOS_TRABAJO + [{"etiqueta": "Otro DNI", "tipo": "dni", "obligatorio": False, "opciones": None}]

    with pytest.raises(ValueError):
        crear_formulario(db_conn, organismo_id, campos=dos_dni)


def test_un_campo_de_lista_guarda_sus_opciones(db_conn, clean_db):
    organismo_id = crear_organismo(db_conn)
    campos = [{"etiqueta": "Turno", "tipo": "opcion", "obligatorio": True, "opciones": [" Mañana ", "Tarde"]}]

    formulario_id = crear_formulario(db_conn, organismo_id, campos=campos)

    assert formularios.obtener_formulario(db_conn, formulario_id)["campos"][0]["opciones"] == ["Mañana", "Tarde"]


def test_listar_formularios_filtra_por_organismo_y_pagina(db_conn, clean_db):
    trabajo = crear_organismo(db_conn)
    registro = crear_organismo(db_conn, "Registro Civil")
    crear_formulario(db_conn, trabajo, nombre="A")
    crear_formulario(db_conn, trabajo, nombre="B")
    crear_formulario(db_conn, registro, nombre="C")

    de_trabajo, total_trabajo = formularios.listar_formularios(db_conn, trabajo, 1, 10)
    todos, total = formularios.listar_formularios(db_conn, None, 1, 10)
    primera, _ = formularios.listar_formularios(db_conn, None, 1, 2)
    segunda, _ = formularios.listar_formularios(db_conn, None, 2, 2)

    assert {f["nombre"] for f in de_trabajo} == {"A", "B"} and total_trabajo == 2
    assert total == 3 and len(todos) == 3
    assert len(primera) == 2 and len(segunda) == 1
    assert "campos" not in de_trabajo[0]


def test_guardar_una_respuesta_normaliza_los_valores(db_conn, clean_db):
    organismo_id = crear_organismo(db_conn)
    formulario_id = crear_formulario(db_conn, organismo_id)
    sesion = crear_sesion(db_conn)

    resultado = formularios.guardar_respuesta(
        db_conn, formulario_id, sesion, valores_validos(dni="30.123.456", participa="sí")
    )

    assert resultado["valores"] == {
        "nombre_y_apellido": "Ana Pérez",
        "dni": "30123456",
        "telefono": "3874567890",
        "participaria_de_la_capacitacion": True,
    }
    assert resultado["formulario"] == "Inscripción a la capacitación"
    respuestas, total = formularios.listar_respuestas(db_conn, formulario_id, 1, 10)
    assert total == 1 and respuestas[0]["valores"]["dni"] == "30123456"
    assert formularios.obtener_formulario(db_conn, formulario_id)["respuestas"] == 1


def test_guardar_con_datos_invalidos_no_guarda_nada(db_conn, clean_db):
    organismo_id = crear_organismo(db_conn)
    formulario_id = crear_formulario(db_conn, organismo_id)
    sesion = crear_sesion(db_conn)

    with pytest.raises(DatosInvalidos) as error:
        formularios.guardar_respuesta(db_conn, formulario_id, sesion, valores_validos(dni="123"))

    assert set(error.value.errores) == {"dni"}
    assert formularios.listar_respuestas(db_conn, formulario_id, 1, 10)[1] == 0


@pytest.mark.parametrize(
    "cambios",
    [
        {"estado": "borrador"},
        {"estado": "cerrado"},
        {"fecha_cierre": datetime.now(timezone.utc) - timedelta(hours=1)},
    ],
)
def test_un_formulario_no_abierto_no_recibe_respuestas(db_conn, clean_db, cambios):
    organismo_id = crear_organismo(db_conn)
    formulario_id = crear_formulario(db_conn, organismo_id, **cambios)
    sesion = crear_sesion(db_conn)

    with pytest.raises(FormularioNoDisponible) as error:
        formularios.guardar_respuesta(db_conn, formulario_id, sesion, valores_validos())

    assert error.value.motivo == "cerrado"


def test_con_el_cupo_completo_no_se_aceptan_mas_respuestas(db_conn, clean_db):
    organismo_id = crear_organismo(db_conn)
    formulario_id = crear_formulario(db_conn, organismo_id, cupo=1)
    formularios.guardar_respuesta(db_conn, formulario_id, crear_sesion(db_conn), valores_validos())

    with pytest.raises(FormularioNoDisponible) as error:
        formularios.guardar_respuesta(db_conn, formulario_id, crear_sesion(db_conn), valores_validos(dni="40123456"))

    assert error.value.motivo == "cupo"
    assert formularios.obtener_formulario(db_conn, formulario_id)["estado_efectivo"] == "cupo_completo"


@pytest.mark.parametrize("segundo_dni", ["30123456", "30.123.456", "30 123 456", " 30123456 "])
def test_el_mismo_dni_escrito_de_otra_forma_es_duplicado(db_conn, clean_db, segundo_dni):
    organismo_id = crear_organismo(db_conn)
    formulario_id = crear_formulario(db_conn, organismo_id)
    formularios.guardar_respuesta(db_conn, formulario_id, crear_sesion(db_conn), valores_validos(dni="30123456"))

    with pytest.raises(RespuestaDuplicada):
        formularios.guardar_respuesta(db_conn, formulario_id, crear_sesion(db_conn), valores_validos(dni=segundo_dni))

    assert formularios.listar_respuestas(db_conn, formulario_id, 1, 10)[1] == 1


def test_el_mismo_dni_se_puede_usar_en_otro_formulario(db_conn, clean_db):
    organismo_id = crear_organismo(db_conn)
    uno = crear_formulario(db_conn, organismo_id, nombre="Uno")
    otro = crear_formulario(db_conn, organismo_id, nombre="Otro")

    formularios.guardar_respuesta(db_conn, uno, crear_sesion(db_conn), valores_validos())
    formularios.guardar_respuesta(db_conn, otro, crear_sesion(db_conn), valores_validos())


def test_una_sesion_no_puede_enviar_dos_veces_el_mismo_formulario(db_conn, clean_db):
    organismo_id = crear_organismo(db_conn)
    formulario_id = crear_formulario(db_conn, organismo_id)
    sesion = crear_sesion(db_conn)
    formularios.guardar_respuesta(db_conn, formulario_id, sesion, valores_validos(dni="30123456"))

    with pytest.raises(YaRespondio):
        formularios.guardar_respuesta(db_conn, formulario_id, sesion, valores_validos(dni="40123456"))


def test_borrar_una_respuesta_libera_el_dni_y_el_lugar_del_cupo(db_conn, clean_db):
    organismo_id = crear_organismo(db_conn)
    formulario_id = crear_formulario(db_conn, organismo_id, cupo=1)
    resultado = formularios.guardar_respuesta(db_conn, formulario_id, crear_sesion(db_conn), valores_validos())

    assert formularios.borrar_respuesta(db_conn, formulario_id, resultado["id"], "admin@x.com") is True

    assert formularios.listar_respuestas(db_conn, formulario_id, 1, 10)[1] == 0
    assert formularios.obtener_respuesta(db_conn, formulario_id, resultado["id"]) is None
    assert formularios.obtener_formulario(db_conn, formulario_id)["hay_respuestas"] is True
    formularios.guardar_respuesta(db_conn, formulario_id, crear_sesion(db_conn), valores_validos())


def test_borrar_registra_quien_y_cuando(db_conn, clean_db):
    organismo_id = crear_organismo(db_conn)
    formulario_id = crear_formulario(db_conn, organismo_id)
    resultado = formularios.guardar_respuesta(db_conn, formulario_id, crear_sesion(db_conn), valores_validos())

    formularios.borrar_respuesta(db_conn, formulario_id, resultado["id"], "admin@x.com")

    with db_conn.cursor() as cur:
        cur.execute("SELECT eliminada_por_email, eliminada_en FROM formulario_respuestas WHERE id = %s", (resultado["id"],))
        quien, cuando = cur.fetchone()
    assert quien == "admin@x.com" and cuando is not None


def test_borrar_una_respuesta_de_otro_formulario_o_ya_borrada_devuelve_false(db_conn, clean_db):
    organismo_id = crear_organismo(db_conn)
    uno = crear_formulario(db_conn, organismo_id, nombre="Uno")
    otro = crear_formulario(db_conn, organismo_id, nombre="Otro")
    resultado = formularios.guardar_respuesta(db_conn, uno, crear_sesion(db_conn), valores_validos())

    assert formularios.borrar_respuesta(db_conn, otro, resultado["id"], "a@x.com") is False
    assert formularios.borrar_respuesta(db_conn, uno, resultado["id"], "a@x.com") is True
    assert formularios.borrar_respuesta(db_conn, uno, resultado["id"], "a@x.com") is False


def test_dos_envios_simultaneos_por_el_ultimo_lugar_guardan_solo_uno(db_conn, clean_db):
    organismo_id = crear_organismo(db_conn)
    formulario_id = crear_formulario(db_conn, organismo_id, cupo=1)
    sesiones_ids = [crear_sesion(db_conn), crear_sesion(db_conn)]
    db_conn.commit()
    url = os.environ.get("TEST_DATABASE_URL", "postgresql://macacha:macacha@localhost:5432/macacha_test")
    resultados: list[str] = []
    barrera = threading.Barrier(2)

    def enviar(indice: int):
        with psycopg.connect(url) as conn:
            barrera.wait()
            try:
                formularios.guardar_respuesta(
                    conn, formulario_id, sesiones_ids[indice], valores_validos(dni=f"3012345{indice}")
                )
                conn.commit()
                resultados.append("ok")
            except FormularioNoDisponible as error:
                conn.rollback()
                resultados.append(error.motivo)

    hilos = [threading.Thread(target=enviar, args=(i,)) for i in range(2)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join(timeout=30)

    assert sorted(resultados) == ["cupo", "ok"]


def test_actualizar_sin_respuestas_permite_reemplazar_los_campos(db_conn, clean_db):
    organismo_id = crear_organismo(db_conn)
    formulario_id = crear_formulario(db_conn, organismo_id)
    actuales = formularios.obtener_formulario(db_conn, formulario_id)["campos"]
    nuevos = [actuales[0], {"etiqueta": "Comentario", "tipo": "texto_largo", "obligatorio": False, "opciones": None}]

    formularios.actualizar_formulario(db_conn, formulario_id, datos_formulario(nombre="Nuevo nombre", cupo=10), nuevos)

    formulario = formularios.obtener_formulario(db_conn, formulario_id)
    assert formulario["nombre"] == "Nuevo nombre" and formulario["cupo"] == 10
    assert [c["clave"] for c in formulario["campos"]] == ["nombre_y_apellido", "comentario"]


def _formulario_con_una_respuesta(db_conn):
    organismo_id = crear_organismo(db_conn)
    campos = CAMPOS_TRABAJO + [{"etiqueta": "Turno", "tipo": "opcion", "obligatorio": False, "opciones": ["Mañana", "Tarde"]}]
    formulario_id = crear_formulario(db_conn, organismo_id, campos=campos)
    formularios.guardar_respuesta(db_conn, formulario_id, crear_sesion(db_conn), valores_validos())
    return formulario_id, formularios.obtener_formulario(db_conn, formulario_id)["campos"]


def test_con_respuestas_se_pueden_cambiar_textos_y_agregar_un_campo_opcional(db_conn, clean_db):
    formulario_id, campos = _formulario_con_una_respuesta(db_conn)
    campos[0] = {**campos[0], "etiqueta": "Nombre completo"}
    campos.append({"etiqueta": "Comentario", "tipo": "texto", "obligatorio": False, "opciones": None})

    formularios.actualizar_formulario(db_conn, formulario_id, datos_formulario(nombre="Otro nombre", cupo=99), campos)

    formulario = formularios.obtener_formulario(db_conn, formulario_id)
    assert formulario["nombre"] == "Otro nombre" and formulario["cupo"] == 99
    assert formulario["campos"][0]["etiqueta"] == "Nombre completo"
    assert formulario["campos"][0]["clave"] == "nombre_y_apellido"
    assert formulario["campos"][-1]["clave"] == "comentario"
    assert formularios.listar_respuestas(db_conn, formulario_id, 1, 10)[0][0]["valores"]["nombre_y_apellido"] == "Ana Pérez"


def test_con_respuestas_se_puede_agregar_una_opcion_a_una_lista(db_conn, clean_db):
    formulario_id, campos = _formulario_con_una_respuesta(db_conn)
    campos[-1] = {**campos[-1], "opciones": ["Mañana", "Tarde", "Noche"]}

    formularios.actualizar_formulario(db_conn, formulario_id, datos_formulario(), campos)

    assert formularios.obtener_formulario(db_conn, formulario_id)["campos"][-1]["opciones"] == ["Mañana", "Tarde", "Noche"]


def test_con_respuestas_no_se_puede_quitar_un_campo(db_conn, clean_db):
    formulario_id, campos = _formulario_con_una_respuesta(db_conn)

    with pytest.raises(ReglaDeEdicion):
        formularios.actualizar_formulario(db_conn, formulario_id, datos_formulario(), campos[1:])


def test_con_respuestas_no_se_puede_cambiar_el_tipo_de_un_campo(db_conn, clean_db):
    formulario_id, campos = _formulario_con_una_respuesta(db_conn)
    campos[0] = {**campos[0], "tipo": "texto_largo"}
    campos[3] = {**campos[3], "tipo": "texto"}

    with pytest.raises(ReglaDeEdicion):
        formularios.actualizar_formulario(db_conn, formulario_id, datos_formulario(), campos)


def test_con_respuestas_un_campo_nuevo_tiene_que_ser_opcional(db_conn, clean_db):
    formulario_id, campos = _formulario_con_una_respuesta(db_conn)
    campos.append({"etiqueta": "Obligatorio nuevo", "tipo": "texto", "obligatorio": True, "opciones": None})

    with pytest.raises(ReglaDeEdicion):
        formularios.actualizar_formulario(db_conn, formulario_id, datos_formulario(), campos)


def test_con_respuestas_no_se_puede_quitar_una_opcion(db_conn, clean_db):
    formulario_id, campos = _formulario_con_una_respuesta(db_conn)
    campos[-1] = {**campos[-1], "opciones": ["Mañana", "Noche"]}

    with pytest.raises(ReglaDeEdicion):
        formularios.actualizar_formulario(db_conn, formulario_id, datos_formulario(), campos)


def test_con_respuestas_una_clave_inexistente_se_rechaza(db_conn, clean_db):
    formulario_id, campos = _formulario_con_una_respuesta(db_conn)
    campos.append({"clave": "inventada", "etiqueta": "X", "tipo": "texto", "obligatorio": False, "opciones": None})

    with pytest.raises(ReglaDeEdicion):
        formularios.actualizar_formulario(db_conn, formulario_id, datos_formulario(), campos)


def _id_por_nombre(conn, nombre):
    return next(f["id"] for f in formularios.listar_formularios(conn, None, 1, 100)[0] if f["nombre"] == nombre)


def test_formularios_abiertos_solo_trae_los_activos_con_lugar_y_prioriza_el_vinculado(db_conn, clean_db):
    organismo_id = crear_organismo(db_conn)
    tramite_id = crear_tramite(db_conn, organismo_id)
    crear_formulario(db_conn, organismo_id, nombre="Borrador", estado="borrador")
    crear_formulario(db_conn, organismo_id, nombre="Cerrado", estado="cerrado")
    crear_formulario(db_conn, organismo_id, nombre="Vencido", fecha_cierre=datetime.now(timezone.utc) - timedelta(days=1))
    crear_formulario(db_conn, organismo_id, nombre="Sin cupo", cupo=1)
    formularios.guardar_respuesta(db_conn, _id_por_nombre(db_conn, "Sin cupo"), crear_sesion(db_conn), valores_validos())
    crear_formulario(db_conn, organismo_id, nombre="Aaa común")
    crear_formulario(db_conn, organismo_id, nombre="Zzz vinculado", tramite_id=tramite_id)

    resultado = formularios.formularios_abiertos(db_conn, tramite_id=tramite_id)

    assert [f["nombre"] for f in resultado] == ["Zzz vinculado", "Aaa común"]
    assert [c["clave"] for c in resultado[0]["campos"]] == ["nombre_y_apellido", "dni", "telefono", "participaria_de_la_capacitacion"]


def test_formularios_abiertos_prioriza_por_coincidencia_con_la_consulta_y_respeta_el_limite(db_conn, clean_db):
    organismo_id = crear_organismo(db_conn)
    for nombre in ["Alfa", "Beta", "Gamma", "Delta", "Epsilon", "Zeta"]:
        crear_formulario(db_conn, organismo_id, nombre=nombre, descripcion_uso="Otro tema")
    crear_formulario(
        db_conn, organismo_id, nombre="Zzz Capacitación", descripcion_uso="Inscripción a la capacitación laboral"
    )

    resultado = formularios.formularios_abiertos(db_conn, consulta="quiero anotarme a la capacitación", limite=5)

    assert len(resultado) == 5
    assert resultado[0]["nombre"] == "Zzz Capacitación"


def test_formularios_consultados_en_sesion_lee_las_herramientas_del_historial(db_conn, clean_db):
    organismo_id = crear_organismo(db_conn)
    formulario_id = crear_formulario(db_conn, organismo_id)
    sesion = crear_sesion(db_conn)
    assert formularios.formularios_consultados_en_sesion(db_conn, sesion) == set()

    llamada = [{"id": "call_1", "type": "function", "function": {"name": "buscar_formularios", "arguments": "{}"}}]
    sessions.guardar_mensaje(db_conn, sesion, "assistant", None, tool_calls=llamada)
    sessions.guardar_mensaje(db_conn, sesion, "tool", json.dumps([{"id": formulario_id, "nombre": "X"}]), tool_call_id="call_1")

    assert formularios.formularios_consultados_en_sesion(db_conn, sesion) == {formulario_id}


def test_otras_herramientas_no_cuentan_como_consulta_de_formularios(db_conn, clean_db):
    sesion = crear_sesion(db_conn)
    llamada = [{"id": "call_1", "type": "function", "function": {"name": "buscar_tramite", "arguments": "{}"}}]
    sessions.guardar_mensaje(db_conn, sesion, "assistant", None, tool_calls=llamada)
    sessions.guardar_mensaje(db_conn, sesion, "tool", json.dumps([{"id": "RC-0001"}]), tool_call_id="call_1")

    assert formularios.formularios_consultados_en_sesion(db_conn, sesion) == set()


def test_formularios_respondidos_en_sesion_cuenta_los_distintos_vigentes(db_conn, clean_db):
    organismo_id = crear_organismo(db_conn)
    uno = crear_formulario(db_conn, organismo_id, nombre="Uno")
    otro = crear_formulario(db_conn, organismo_id, nombre="Otro")
    sesion = crear_sesion(db_conn)
    assert formularios.formularios_respondidos_en_sesion(db_conn, sesion) == 0

    formularios.guardar_respuesta(db_conn, uno, sesion, valores_validos(dni="30123456"))
    formularios.guardar_respuesta(db_conn, otro, sesion, valores_validos(dni="30123456"))

    assert formularios.formularios_respondidos_en_sesion(db_conn, sesion) == 2
