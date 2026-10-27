import pytest

from agent.formularios_validacion import (
    ErrorDeCampo,
    generar_clave,
    normalizar_valor,
    validar_definicion,
    validar_valores,
)


def _campo(tipo, obligatorio=True, opciones=None, clave="c"):
    return {"clave": clave, "etiqueta": "Campo", "tipo": tipo, "obligatorio": obligatorio, "opciones": opciones}


@pytest.mark.parametrize("entrada", ["30123456", "30.123.456", "30 123 456", " 30123456 ", 30123456])
def test_dni_acepta_puntos_y_espacios_y_queda_solo_con_numeros(entrada):
    assert normalizar_valor(_campo("dni"), entrada) == "30123456"


@pytest.mark.parametrize("entrada", ["123456", "123456789", "12a45678", "abc", ""])
def test_dni_rechaza_lo_que_no_tiene_7_u_8_numeros(entrada):
    with pytest.raises(ErrorDeCampo):
        normalizar_valor(_campo("dni"), entrada)


@pytest.mark.parametrize(
    "entrada, esperado",
    [("387 456-7890", "3874567890"), ("(387) 4567890", "3874567890"), ("+54 9 387 456 7890", "+5493874567890")],
)
def test_telefono_acepta_formatos_comunes(entrada, esperado):
    assert normalizar_valor(_campo("telefono"), entrada) == esperado


@pytest.mark.parametrize("entrada", ["1234567", "1" * 16, "387-abc-4567", "387#4567890"])
def test_telefono_rechaza_largos_y_caracteres_invalidos(entrada):
    with pytest.raises(ErrorDeCampo):
        normalizar_valor(_campo("telefono"), entrada)


def test_email_se_valida_y_se_recorta():
    assert normalizar_valor(_campo("email"), "  ana@correo.com ") == "ana@correo.com"
    with pytest.raises(ErrorDeCampo):
        normalizar_valor(_campo("email"), "no-es-un-mail")


@pytest.mark.parametrize("entrada, esperado", [("12", 12), ("12,5", 12.5), ("12.5", 12.5), (7, 7), (3.0, 3), ("-4", -4)])
def test_numero_acepta_coma_y_punto(entrada, esperado):
    assert normalizar_valor(_campo("numero"), entrada) == esperado


@pytest.mark.parametrize("entrada", ["abc", "", "nan", "inf", True])
def test_numero_rechaza_lo_que_no_es_numero(entrada):
    with pytest.raises(ErrorDeCampo):
        normalizar_valor(_campo("numero"), entrada)


@pytest.mark.parametrize("entrada, esperado", [("1990-12-25", "1990-12-25"), ("25/12/1990", "1990-12-25"), ("5/3/2001", "2001-03-05")])
def test_fecha_acepta_iso_y_dia_mes_anio(entrada, esperado):
    assert normalizar_valor(_campo("fecha"), entrada) == esperado


@pytest.mark.parametrize("entrada", ["31/02/2020", "2020-13-01", "mañana", "25-12-1990"])
def test_fecha_rechaza_fechas_que_no_existen_o_con_otro_formato(entrada):
    with pytest.raises(ErrorDeCampo):
        normalizar_valor(_campo("fecha"), entrada)


@pytest.mark.parametrize("entrada, esperado", [("sí", True), ("Si", True), (True, True), ("no", False), ("NO", False), (False, False)])
def test_si_no_acepta_variantes(entrada, esperado):
    assert normalizar_valor(_campo("si_no"), entrada) is esperado


def test_si_no_rechaza_otras_respuestas():
    with pytest.raises(ErrorDeCampo):
        normalizar_valor(_campo("si_no"), "quizás")


def test_opcion_acepta_sin_distinguir_mayusculas_y_devuelve_la_opcion_original():
    campo = _campo("opcion", opciones=["Mañana", "Tarde"])
    assert normalizar_valor(campo, "tarde") == "Tarde"
    with pytest.raises(ErrorDeCampo) as error:
        normalizar_valor(campo, "noche")
    assert "Mañana" in str(error.value) and "Tarde" in str(error.value)


def test_texto_y_texto_largo_respetan_su_largo_maximo():
    assert normalizar_valor(_campo("texto"), "  hola   mundo ") == "hola mundo"
    with pytest.raises(ErrorDeCampo):
        normalizar_valor(_campo("texto"), "x" * 201)
    assert normalizar_valor(_campo("texto_largo"), "x" * 1000) == "x" * 1000
    with pytest.raises(ErrorDeCampo):
        normalizar_valor(_campo("texto_largo"), "x" * 1001)


def test_validar_valores_junta_los_errores_por_clave_y_omite_los_opcionales_vacios():
    campos = [
        _campo("texto", clave="nombre"),
        _campo("dni", clave="dni"),
        _campo("telefono", obligatorio=False, clave="telefono"),
    ]

    normalizados, errores = validar_valores(campos, {"nombre": "Ana", "dni": "12", "telefono": "  "})

    assert normalizados == {"nombre": "Ana"}
    assert set(errores) == {"dni"}


def test_validar_valores_marca_los_obligatorios_faltantes_e_ignora_claves_desconocidas():
    campos = [_campo("texto", clave="nombre")]

    normalizados, errores = validar_valores(campos, {"otro": "x"})

    assert normalizados == {}
    assert errores == {"nombre": "Este dato es obligatorio."}


def test_validar_valores_acepta_el_valor_falso_de_un_si_no_obligatorio():
    campos = [_campo("si_no", clave="participa")]

    normalizados, errores = validar_valores(campos, {"participa": False})

    assert normalizados == {"participa": False} and errores == {}


def test_generar_clave_saca_acentos_y_evita_repetidas():
    assert generar_clave("¿Participaría de la capacitación?", set()) == "participaria_de_la_capacitacion"
    assert generar_clave("DNI", {"dni"}) == "dni_2"
    assert generar_clave("DNI", {"dni", "dni_2"}) == "dni_3"
    assert generar_clave("???", set()) == "campo"


def test_validar_definicion_acepta_el_ejemplo_de_trabajo():
    validar_definicion([_campo("texto"), _campo("dni"), _campo("telefono"), _campo("si_no")])


@pytest.mark.parametrize(
    "campos",
    [
        [],
        [_campo("dni"), _campo("dni")],
        [_campo("inventado")],
        [{**_campo("texto"), "etiqueta": "  "}],
        [{**_campo("texto"), "etiqueta": "x" * 121}],
        [_campo("opcion", opciones=["Una sola"])],
        [_campo("opcion", opciones=["A", "a"])],
        [_campo("opcion", opciones=[f"o{i}" for i in range(21)])],
        [_campo("texto") for _ in range(31)],
    ],
)
def test_validar_definicion_rechaza_definiciones_invalidas(campos):
    with pytest.raises(ValueError):
        validar_definicion(campos)
