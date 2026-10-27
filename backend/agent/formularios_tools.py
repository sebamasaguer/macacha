import logging

from agent import mail
from agent.admin import contacto_repository
from agent.admin import formularios_repository as formularios
from agent.formularios_csv import valor_legible

logger = logging.getLogger(__name__)

MAX_FORMULARIOS_POR_SESION = 3


def buscar_formularios(conn, argumentos: dict) -> list[dict]:
    abiertos = formularios.formularios_abiertos(
        conn, tramite_id=argumentos.get("tramite_id"), consulta=argumentos.get("consulta"), limite=5
    )
    return [
        {
            "id": f["id"],
            "nombre": f["nombre"],
            "organismo": f["organismo"],
            "descripcion_uso": f["descripcion_uso"],
            "aviso_finalidad": f["aviso_finalidad"],
            "campos": [
                {
                    "clave": c["clave"],
                    "etiqueta": c["etiqueta"],
                    "tipo": c["tipo"],
                    "obligatorio": c["obligatorio"],
                    "opciones": c["opciones"],
                }
                for c in f["campos"]
            ],
        }
        for f in abiertos
    ]


def guardar_respuesta_formulario(conn, session_id: str, argumentos: dict) -> dict:
    # El servidor no confía en el modelo: cada defensa se comprueba acá, antes de tocar los datos.
    if argumentos.get("confirmado") is not True:
        return {
            "ok": False,
            "motivo": "no_confirmado",
            "detalle": "Resumí los datos y pedile a la persona que confirme antes de guardar.",
        }
    formulario_id = str(argumentos.get("formulario_id", ""))
    if formulario_id not in formularios.formularios_consultados_en_sesion(conn, session_id):
        return {
            "ok": False,
            "motivo": "formulario_no_consultado",
            "detalle": "Primero consultá el formulario con buscar_formularios.",
        }
    valores = argumentos.get("valores")
    if not isinstance(valores, dict):
        return {"ok": False, "motivo": "datos_invalidos", "errores": {}, "detalle": "Faltan los valores del formulario."}
    if formularios.formularios_respondidos_en_sesion(conn, session_id) >= MAX_FORMULARIOS_POR_SESION:
        return {"ok": False, "motivo": "limite_sesion"}

    try:
        resultado = formularios.guardar_respuesta(conn, formulario_id, session_id, valores)
    except formularios.FormularioNoDisponible as error:
        return {"ok": False, "motivo": error.motivo}
    except formularios.DatosInvalidos as error:
        return {"ok": False, "motivo": "datos_invalidos", "errores": error.errores}
    except formularios.RespuestaDuplicada:
        return {"ok": False, "motivo": "duplicado"}
    except formularios.YaRespondio:
        return {"ok": False, "motivo": "ya_registrada"}

    # Se confirma ahora y no al final del turno: si algo falla después, la persona no pierde lo que ya se le confirmó.
    conn.commit()
    _avisar_por_mail(conn, resultado)
    return {"ok": True, "formulario": resultado["formulario"]}


def _avisar_por_mail(conn, resultado: dict) -> None:
    try:
        destinatarios = contacto_repository.resolver_destinatarios(conn, resultado["organismo_id"])
        lineas = [f"Nueva respuesta al formulario «{resultado['formulario']}»", ""]
        for campo in resultado["campos"]:
            lineas.append(f"{campo['etiqueta']}: {valor_legible(campo, resultado['valores'].get(campo['clave']))}")
        mail.enviar_mail(
            destinatarios,
            asunto=f"Nueva respuesta: {resultado['formulario']}",
            cuerpo_texto="\n".join(lineas),
        )
    except Exception:
        logger.exception("Falló el aviso por mail de la respuesta %s", resultado["id"])
