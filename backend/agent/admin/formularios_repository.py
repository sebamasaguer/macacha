import json
import re
import unicodedata
from datetime import datetime, timezone

import psycopg

from agent.formularios_validacion import generar_clave, validar_definicion, validar_valores


class ReglaDeEdicion(ValueError):
    """Un cambio que no se permite en un formulario que ya tiene respuestas."""


class FormularioNoDisponible(Exception):
    def __init__(self, motivo: str):
        super().__init__(motivo)
        self.motivo = motivo


class DatosInvalidos(Exception):
    def __init__(self, errores: dict):
        super().__init__("datos inválidos")
        self.errores = errores


class RespuestaDuplicada(Exception):
    """Ya hay una respuesta vigente con ese DNI en el formulario."""


class YaRespondio(Exception):
    """Esta sesión ya envió una respuesta vigente a este formulario."""


def calcular_estado_efectivo(estado, fecha_cierre, cupo, respuestas, ahora=None) -> str:
    ahora = ahora or datetime.now(timezone.utc)
    if estado == "borrador":
        return "borrador"
    if estado == "cerrado":
        return "cerrado"
    if fecha_cierre is not None and ahora >= fecha_cierre:
        return "vencido"
    if cupo is not None and respuestas >= cupo:
        return "cupo_completo"
    return "abierto"


_SELECT = """
    SELECT f.id, f.organismo_id, o.nombre, f.nombre, f.descripcion_uso, f.aviso_finalidad, f.tramite_id,
           f.estado, f.fecha_cierre, f.cupo, f.creado_por_email, f.creado_en, f.actualizado_en,
           (SELECT COUNT(*) FROM formulario_respuestas r WHERE r.formulario_id = f.id AND r.eliminada_en IS NULL),
           EXISTS (SELECT 1 FROM formulario_respuestas r WHERE r.formulario_id = f.id)
    FROM formularios f
    JOIN organismos o ON o.id = f.organismo_id
"""


def _fila_a_formulario(fila) -> dict:
    (id_, organismo_id, organismo, nombre, descripcion_uso, aviso_finalidad, tramite_id, estado,
     fecha_cierre, cupo, creado_por_email, creado_en, actualizado_en, respuestas, hay_respuestas) = fila
    return {
        "id": str(id_),
        "organismo_id": organismo_id,
        "organismo": organismo,
        "nombre": nombre,
        "descripcion_uso": descripcion_uso,
        "aviso_finalidad": aviso_finalidad,
        "tramite_id": tramite_id,
        "estado": estado,
        "estado_efectivo": calcular_estado_efectivo(estado, fecha_cierre, cupo, respuestas),
        "fecha_cierre": fecha_cierre.isoformat() if fecha_cierre else None,
        "cupo": cupo,
        "respuestas": respuestas,
        "hay_respuestas": hay_respuestas,
        "creado_por_email": creado_por_email,
        "creado_en": creado_en.isoformat(),
        "actualizado_en": actualizado_en.isoformat(),
    }


def _campos(conn, formulario_id: str) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT clave, etiqueta, tipo, obligatorio, opciones
            FROM formulario_campos WHERE formulario_id = %s ORDER BY orden
            """,
            (formulario_id,),
        )
        return [
            {"clave": clave, "etiqueta": etiqueta, "tipo": tipo, "obligatorio": obligatorio, "opciones": opciones}
            for clave, etiqueta, tipo, obligatorio, opciones in cur.fetchall()
        ]


def _opciones_limpias(campo: dict):
    return [o.strip() for o in campo["opciones"]] if campo["tipo"] == "opcion" else None


def _insertar_campo(conn, formulario_id: str, campo: dict, clave: str, orden: int) -> None:
    opciones = _opciones_limpias(campo)
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO formulario_campos (formulario_id, clave, etiqueta, tipo, obligatorio, opciones, orden)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                formulario_id,
                clave,
                campo["etiqueta"].strip(),
                campo["tipo"],
                campo.get("obligatorio", True),
                json.dumps(opciones) if opciones is not None else None,
                orden,
            ),
        )


def crear_formulario(conn, organismo_id: int, datos: dict, campos: list[dict], creado_por_email: str) -> str:
    validar_definicion(campos)
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO formularios
                (organismo_id, nombre, descripcion_uso, aviso_finalidad, tramite_id, estado, fecha_cierre, cupo,
                 creado_por_email)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                organismo_id,
                datos["nombre"].strip(),
                datos.get("descripcion_uso", ""),
                datos.get("aviso_finalidad", ""),
                datos.get("tramite_id"),
                datos.get("estado", "borrador"),
                datos.get("fecha_cierre"),
                datos.get("cupo"),
                creado_por_email,
            ),
        )
        formulario_id = str(cur.fetchone()[0])
    usadas = {c["clave"] for c in campos if c.get("clave")}
    for orden, campo in enumerate(campos):
        clave = campo.get("clave")
        if not clave:
            clave = generar_clave(campo["etiqueta"], usadas)
            usadas.add(clave)
        _insertar_campo(conn, formulario_id, campo, clave, orden)
    return formulario_id


def obtener_formulario(conn, formulario_id: str) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(_SELECT + " WHERE f.id = %s", (formulario_id,))
        fila = cur.fetchone()
    if fila is None:
        return None
    formulario = _fila_a_formulario(fila)
    formulario["campos"] = _campos(conn, formulario_id)
    return formulario


def listar_formularios(conn, organismo_id: int | None, page: int, page_size: int) -> tuple[list[dict], int]:
    donde = ""
    parametros: tuple = ()
    if organismo_id is not None:
        donde = " WHERE f.organismo_id = %s"
        parametros = (organismo_id,)
    with conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM formularios f{donde}", parametros)
        total = cur.fetchone()[0]
        cur.execute(
            _SELECT + donde + " ORDER BY f.creado_en DESC, f.id LIMIT %s OFFSET %s",
            parametros + (page_size, (page - 1) * page_size),
        )
        return [_fila_a_formulario(f) for f in cur.fetchall()], total


def actualizar_formulario(conn, formulario_id: str, datos: dict, campos: list[dict]) -> None:
    validar_definicion(campos)
    actuales = {c["clave"]: c for c in _campos(conn, formulario_id)}
    with conn.cursor() as cur:
        cur.execute("SELECT EXISTS (SELECT 1 FROM formulario_respuestas WHERE formulario_id = %s)", (formulario_id,))
        con_respuestas = cur.fetchone()[0]

    if con_respuestas:
        enviadas = {c["clave"] for c in campos if c.get("clave")}
        for clave, actual in actuales.items():
            if clave not in enviadas:
                raise ReglaDeEdicion(f"No se puede quitar el campo «{actual['etiqueta']}» porque ya tiene respuestas.")
        for campo in campos:
            clave = campo.get("clave")
            if clave is None:
                if campo.get("obligatorio", True):
                    raise ReglaDeEdicion("Los campos nuevos tienen que ser opcionales porque el formulario ya tiene respuestas.")
                continue
            actual = actuales.get(clave)
            if actual is None:
                raise ReglaDeEdicion(f"El campo «{clave}» no existe en el formulario.")
            if campo["tipo"] != actual["tipo"]:
                raise ReglaDeEdicion(f"No se puede cambiar el tipo del campo «{actual['etiqueta']}» porque ya tiene respuestas.")
            if actual["tipo"] == "opcion":
                nuevas = {o.strip().lower() for o in campo["opciones"]}
                if not {o.strip().lower() for o in actual["opciones"]} <= nuevas:
                    raise ReglaDeEdicion(f"No se pueden quitar opciones de «{actual['etiqueta']}» porque ya tiene respuestas.")

    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE formularios
            SET nombre = %s, descripcion_uso = %s, aviso_finalidad = %s, tramite_id = %s, estado = %s,
                fecha_cierre = %s, cupo = %s, actualizado_en = now()
            WHERE id = %s
            """,
            (
                datos["nombre"].strip(),
                datos.get("descripcion_uso", ""),
                datos.get("aviso_finalidad", ""),
                datos.get("tramite_id"),
                datos.get("estado", "borrador"),
                datos.get("fecha_cierre"),
                datos.get("cupo"),
                formulario_id,
            ),
        )
        if not con_respuestas:
            conservadas = [c["clave"] for c in campos if c.get("clave") in actuales]
            cur.execute(
                "DELETE FROM formulario_campos WHERE formulario_id = %s AND clave <> ALL(%s)",
                (formulario_id, conservadas),
            )
    usadas = set(actuales) | {c["clave"] for c in campos if c.get("clave")}
    for orden, campo in enumerate(campos):
        clave = campo.get("clave")
        if clave in actuales:
            opciones = _opciones_limpias(campo)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE formulario_campos SET etiqueta = %s, obligatorio = %s, opciones = %s, orden = %s
                    WHERE formulario_id = %s AND clave = %s
                    """,
                    (
                        campo["etiqueta"].strip(),
                        campo.get("obligatorio", True),
                        json.dumps(opciones) if opciones is not None else None,
                        orden,
                        formulario_id,
                        clave,
                    ),
                )
        else:
            nueva = clave or generar_clave(campo["etiqueta"], usadas)
            usadas.add(nueva)
            _insertar_campo(conn, formulario_id, campo, nueva, orden)


def guardar_respuesta(conn, formulario_id: str, session_id: str, valores: dict) -> dict:
    with conn.cursor() as cur:
        # Se bloquea el formulario hasta el final de la transacción: dos envíos simultáneos no superan el cupo.
        cur.execute(
            "SELECT estado, fecha_cierre, cupo, organismo_id, nombre FROM formularios WHERE id = %s FOR UPDATE",
            (formulario_id,),
        )
        fila = cur.fetchone()
        if fila is None:
            raise FormularioNoDisponible("cerrado")
        estado, fecha_cierre, cupo, organismo_id, nombre = fila
        cur.execute(
            "SELECT COUNT(*) FROM formulario_respuestas WHERE formulario_id = %s AND eliminada_en IS NULL",
            (formulario_id,),
        )
        vigentes = cur.fetchone()[0]
        efectivo = calcular_estado_efectivo(estado, fecha_cierre, cupo, vigentes)
        if efectivo == "cupo_completo":
            raise FormularioNoDisponible("cupo")
        if efectivo != "abierto":
            raise FormularioNoDisponible("cerrado")
        cur.execute(
            """
            SELECT 1 FROM formulario_respuestas
            WHERE formulario_id = %s AND session_id = %s AND eliminada_en IS NULL
            """,
            (formulario_id, session_id),
        )
        if cur.fetchone() is not None:
            raise YaRespondio()

    campos = _campos(conn, formulario_id)
    normalizados, errores = validar_valores(campos, valores)
    if errores:
        raise DatosInvalidos(errores)
    dni = next((normalizados[c["clave"]] for c in campos if c["tipo"] == "dni" and c["clave"] in normalizados), None)
    try:
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO formulario_respuestas (formulario_id, session_id, valores, dni)
                    VALUES (%s, %s, %s, %s) RETURNING id
                    """,
                    (formulario_id, session_id, json.dumps(normalizados), dni),
                )
                respuesta_id = str(cur.fetchone()[0])
    except psycopg.errors.UniqueViolation:
        raise RespuestaDuplicada() from None
    return {
        "id": respuesta_id,
        "formulario": nombre,
        "organismo_id": organismo_id,
        "valores": normalizados,
        "campos": campos,
    }


def _fila_a_respuesta(fila) -> dict:
    id_, session_id, creado_en, valores = fila
    return {"id": str(id_), "session_id": str(session_id), "creado_en": creado_en.isoformat(), "valores": valores}


def listar_respuestas(conn, formulario_id: str, page: int, page_size: int) -> tuple[list[dict], int]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM formulario_respuestas WHERE formulario_id = %s AND eliminada_en IS NULL",
            (formulario_id,),
        )
        total = cur.fetchone()[0]
        cur.execute(
            """
            SELECT id, session_id, creado_en, valores FROM formulario_respuestas
            WHERE formulario_id = %s AND eliminada_en IS NULL
            ORDER BY creado_en DESC, id LIMIT %s OFFSET %s
            """,
            (formulario_id, page_size, (page - 1) * page_size),
        )
        return [_fila_a_respuesta(f) for f in cur.fetchall()], total


def todas_las_respuestas(conn, formulario_id: str) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, session_id, creado_en, valores FROM formulario_respuestas
            WHERE formulario_id = %s AND eliminada_en IS NULL ORDER BY creado_en, id
            """,
            (formulario_id,),
        )
        return [_fila_a_respuesta(f) for f in cur.fetchall()]


def obtener_respuesta(conn, formulario_id: str, respuesta_id: str) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, session_id, creado_en, valores FROM formulario_respuestas
            WHERE formulario_id = %s AND id = %s AND eliminada_en IS NULL
            """,
            (formulario_id, respuesta_id),
        )
        fila = cur.fetchone()
    return _fila_a_respuesta(fila) if fila else None


def borrar_respuesta(conn, formulario_id: str, respuesta_id: str, email: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE formulario_respuestas SET eliminada_en = now(), eliminada_por_email = %s
            WHERE formulario_id = %s AND id = %s AND eliminada_en IS NULL
            """,
            (email, formulario_id, respuesta_id),
        )
        return cur.rowcount == 1


def _sin_acentos(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


def _palabras(texto: str) -> set[str]:
    return {p for p in re.findall(r"[a-z0-9]+", _sin_acentos(texto.lower())) if len(p) >= 4}


def formularios_abiertos(conn, tramite_id: str | None = None, consulta: str | None = None, limite: int = 5) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(_SELECT + " WHERE f.estado = 'activo' ORDER BY f.nombre")
        todos = [_fila_a_formulario(f) for f in cur.fetchall()]
    abiertos = [f for f in todos if f["estado_efectivo"] == "abierto"]
    palabras_consulta = _palabras(consulta or "")

    def puntaje(formulario: dict) -> int:
        vinculado = 100 if tramite_id and formulario["tramite_id"] == tramite_id else 0
        coincidencias = len(palabras_consulta & _palabras(formulario["nombre"] + " " + formulario["descripcion_uso"]))
        return vinculado + coincidencias

    abiertos.sort(key=lambda f: (-puntaje(f), f["nombre"]))
    elegidos = abiertos[:limite]
    for formulario in elegidos:
        formulario["campos"] = _campos(conn, formulario["id"])
    return elegidos


def formularios_consultados_en_sesion(conn, session_id: str) -> set[str]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT DISTINCT t.contenido
            FROM mensajes t
            JOIN mensajes a ON a.session_id = t.session_id AND a.rol = 'assistant' AND a.tool_calls IS NOT NULL
            WHERE t.session_id = %s AND t.rol = 'tool'
              AND EXISTS (
                  SELECT 1 FROM jsonb_array_elements(a.tool_calls) llamada
                  WHERE llamada->>'id' = t.tool_call_id AND llamada->'function'->>'name' = 'buscar_formularios'
              )
            """,
            (session_id,),
        )
        contenidos = [fila[0] for fila in cur.fetchall()]
    ids: set[str] = set()
    for contenido in contenidos:
        try:
            lista = json.loads(contenido)
        except (TypeError, ValueError):
            continue
        if isinstance(lista, list):
            ids.update(str(item["id"]) for item in lista if isinstance(item, dict) and "id" in item)
    return ids


def formularios_respondidos_en_sesion(conn, session_id: str) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(DISTINCT formulario_id) FROM formulario_respuestas WHERE session_id = %s AND eliminada_en IS NULL",
            (session_id,),
        )
        return cur.fetchone()[0]
