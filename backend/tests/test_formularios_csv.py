import csv
import io

from agent.formularios_csv import a_csv, valor_legible

CAMPOS = [
    {"clave": "nombre", "etiqueta": "Nombre", "tipo": "texto", "obligatorio": True, "opciones": None},
    {"clave": "edad", "etiqueta": "Edad", "tipo": "numero", "obligatorio": True, "opciones": None},
    {"clave": "participa", "etiqueta": "¿Participa?", "tipo": "si_no", "obligatorio": True, "opciones": None},
    {"clave": "nacimiento", "etiqueta": "Nacimiento", "tipo": "fecha", "obligatorio": False, "opciones": None},
]


def _leer(texto):
    return list(csv.reader(io.StringIO(texto)))


def test_valor_legible_por_tipo():
    assert valor_legible(CAMPOS[2], True) == "Sí"
    assert valor_legible(CAMPOS[2], False) == "No"
    assert valor_legible(CAMPOS[3], "1990-12-25") == "25/12/1990"
    assert valor_legible(CAMPOS[1], 12) == "12"
    assert valor_legible(CAMPOS[0], None) == ""


def test_el_csv_tiene_encabezado_y_una_fila_por_respuesta():
    respuestas = [
        {"creado_en": "2026-10-23T10:00:00", "valores": {"nombre": "Ana", "edad": 30, "participa": True, "nacimiento": "1990-12-25"}},
        {"creado_en": "2026-10-23T11:00:00", "valores": {"nombre": "Luis", "edad": 41, "participa": False}},
    ]

    filas = _leer(a_csv(CAMPOS, respuestas))

    assert filas[0] == ["Fecha", "Nombre", "Edad", "¿Participa?", "Nacimiento"]
    assert filas[1] == ["2026-10-23T10:00:00", "Ana", "30", "Sí", "25/12/1990"]
    assert filas[2] == ["2026-10-23T11:00:00", "Luis", "41", "No", ""]


def test_las_celdas_que_empiezan_como_formula_se_prefijan_con_comilla():
    respuestas = [{"creado_en": "x", "valores": {"nombre": "=HYPERLINK(\"http://malo\")", "edad": 1, "participa": True}}]

    celda = _leer(a_csv(CAMPOS, respuestas))[1][1]

    assert celda.startswith("'=")


def test_las_otras_marcas_de_formula_tambien_se_neutralizan():
    for texto in ("+54 9 387", "-cmd", "@usuario"):
        respuestas = [{"creado_en": "x", "valores": {"nombre": texto, "edad": 1, "participa": True}}]
        assert _leer(a_csv(CAMPOS, respuestas))[1][1] == "'" + texto


def test_los_numeros_negativos_no_se_prefijan():
    respuestas = [{"creado_en": "x", "valores": {"nombre": "Ana", "edad": -4, "participa": True}}]

    assert _leer(a_csv(CAMPOS, respuestas))[1][2] == "-4"


def test_el_encabezado_tambien_se_neutraliza():
    campos = [{"clave": "a", "etiqueta": "=1+1", "tipo": "texto", "obligatorio": True, "opciones": None}]

    assert _leer(a_csv(campos, []))[0][1] == "'=1+1"


def test_comas_comillas_y_saltos_de_linea_quedan_bien_formados():
    respuestas = [{"creado_en": "x", "valores": {"nombre": 'Ana, "la" mejor\nsegunda línea', "edad": 1, "participa": True}}]

    filas = _leer(a_csv(CAMPOS, respuestas))

    assert filas[1][1] == 'Ana, "la" mejor\nsegunda línea'
    assert len(filas[1]) == 5
