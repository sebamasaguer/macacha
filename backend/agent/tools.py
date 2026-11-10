from agent import documentos_tools, formularios_tools
from ingest.repository import obtener_snapshot_vigente
from retrieval.hybrid_search import buscar_chunks

TOOL_SCHEMAS = [
    documentos_tools.SCHEMA_BUSCAR_DOCUMENTOS,
    {
        "type": "function",
        "function": {
            "name": "buscar_tramite",
            "description": (
                "Busca trámites relevantes a la pregunta del usuario. Usala "
                "siempre antes de nombrarle a la persona cuál es su trámite, "
                "incluso si te parece obvio cuál es — nunca asumas de "
                "memoria qué trámite corresponde sin confirmarlo primero con "
                "esta herramienta."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "La consulta o pregunta del usuario en lenguaje natural.",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "obtener_requisitos",
            "description": "Devuelve los requisitos de un trámite ya identificado por su tramite_id.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tramite_id": {"type": "string", "description": "El ID del trámite, ej. 'RC-0001'."}
                },
                "required": ["tramite_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "obtener_costos_modalidad",
            "description": "Devuelve el costo, la modalidad y la duración estimada de un trámite.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tramite_id": {"type": "string", "description": "El ID del trámite, ej. 'RC-0001'."}
                },
                "required": ["tramite_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "obtener_pasos",
            "description": "Devuelve la lista de pasos a seguir para completar un trámite.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tramite_id": {"type": "string", "description": "El ID del trámite, ej. 'RC-0001'."}
                },
                "required": ["tramite_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "obtener_normativa",
            "description": "Devuelve el objetivo y la descripción normativa de un trámite.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tramite_id": {"type": "string", "description": "El ID del trámite, ej. 'RC-0001'."}
                },
                "required": ["tramite_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "obtener_formularios_enlaces",
            "description": "Devuelve los enlaces oficiales (formularios, sitios de gestión) de un trámite.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tramite_id": {"type": "string", "description": "El ID del trámite, ej. 'RC-0001'."}
                },
                "required": ["tramite_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "obtener_problemas_frecuentes",
            "description": "Devuelve los problemas o advertencias frecuentes de un trámite.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tramite_id": {"type": "string", "description": "El ID del trámite, ej. 'RC-0001'."}
                },
                "required": ["tramite_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ofrecer_contacto_humano",
            "description": (
                "Usala cuando no puedas resolver la consulta de la persona — no "
                "encontrás el trámite, la información no alcanza, o la persona te "
                "dice explícitamente que la respuesta no le sirve o que necesita "
                "hablar con alguien. No la uses como primera opción: intentá "
                "resolver la consulta primero."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "buscar_formularios",
            "description": (
                "Busca los formularios de inscripción o registro que algún organismo tiene abiertos (por ejemplo, "
                "inscripción a una capacitación). Usala cuando la persona quiera anotarse, inscribirse o completar "
                "un formulario, o cuando lo que cuenta coincida con uno. Devuelve, por cada formulario, para qué se "
                "usan los datos (aviso_finalidad) y los campos que hay que pedir."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "consulta": {
                        "type": "string",
                        "description": "Lo que la persona quiere hacer, con sus palabras.",
                    },
                    "tramite_id": {
                        "type": "string",
                        "description": "El ID del trámite de la conversación, si ya está identificado (ej. 'TR-0001').",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "guardar_respuesta_formulario",
            "description": (
                "Guarda los datos que la persona dio para un formulario. Llamala solo después de haber consultado el "
                "formulario con buscar_formularios, de haber resumido los datos y de que la persona confirmó que son "
                "correctos. Si devuelve errores por campo, repreguntá solo esos datos."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "formulario_id": {"type": "string", "description": "El id del formulario devuelto por buscar_formularios."},
                    "valores": {
                        "type": "object",
                        "description": "Un valor por cada campo, usando la clave del campo (ej. {\"dni\": \"30123456\"}).",
                    },
                    "confirmado": {
                        "type": "boolean",
                        "description": "Verdadero solo si la persona confirmó explícitamente que los datos resumidos son correctos.",
                    },
                },
                "required": ["formulario_id", "valores", "confirmado"],
            },
        },
    },
]


def buscar_tramite(conn, embed_fn, rerank_fn, query: str) -> list[dict]:
    chunks = buscar_chunks(query, conn, embed_fn, rerank_fn, top_k=10)
    vistos: set[str] = set()
    resultados: list[dict] = []
    for chunk in chunks:
        if chunk["tramite_id"] not in vistos:
            vistos.add(chunk["tramite_id"])
            resultados.append(
                {
                    "tramite_id": chunk["tramite_id"],
                    "nombre_oficial": chunk["nombre_oficial"],
                    "categoria": chunk["categoria"],
                    "organismo": chunk["organismo"],
                }
            )
    return resultados


def obtener_requisitos(conn, tramite_id: str) -> list[str]:
    snapshot = obtener_snapshot_vigente(conn, tramite_id)
    return snapshot["requisitos"] if snapshot else []


def obtener_costos_modalidad(conn, tramite_id: str) -> dict:
    snapshot = obtener_snapshot_vigente(conn, tramite_id)
    if snapshot is None:
        return {}
    return {
        "costo": snapshot["costo"],
        "modalidad": snapshot["modalidad"],
        "duracion": snapshot["duracion"],
    }


def obtener_pasos(conn, tramite_id: str) -> list[str]:
    snapshot = obtener_snapshot_vigente(conn, tramite_id)
    return snapshot["pasos"] if snapshot else []


def obtener_normativa(conn, tramite_id: str) -> dict:
    snapshot = obtener_snapshot_vigente(conn, tramite_id)
    if snapshot is None:
        return {}
    return {"objetivo": snapshot["objetivo"], "descripcion": snapshot["descripcion"]}


def obtener_formularios_enlaces(conn, tramite_id: str) -> list[str]:
    snapshot = obtener_snapshot_vigente(conn, tramite_id)
    return snapshot["enlaces_oficiales"] if snapshot else []


def obtener_problemas_frecuentes(conn, tramite_id: str) -> list[str]:
    snapshot = obtener_snapshot_vigente(conn, tramite_id)
    return snapshot["problemas_frecuentes"] if snapshot else []


def ofrecer_contacto_humano() -> dict:
    return {"sugerido": True}


def ejecutar_tool(nombre: str, argumentos: dict, conn, embed_fn, rerank_fn, session_id: str | None = None):
    if nombre == "buscar_tramite":
        return buscar_tramite(conn, embed_fn, rerank_fn, argumentos["query"])
    if nombre == "obtener_requisitos":
        return obtener_requisitos(conn, argumentos["tramite_id"])
    if nombre == "obtener_costos_modalidad":
        return obtener_costos_modalidad(conn, argumentos["tramite_id"])
    if nombre == "obtener_pasos":
        return obtener_pasos(conn, argumentos["tramite_id"])
    if nombre == "obtener_normativa":
        return obtener_normativa(conn, argumentos["tramite_id"])
    if nombre == "obtener_formularios_enlaces":
        return obtener_formularios_enlaces(conn, argumentos["tramite_id"])
    if nombre == "obtener_problemas_frecuentes":
        return obtener_problemas_frecuentes(conn, argumentos["tramite_id"])
    if nombre == "ofrecer_contacto_humano":
        return ofrecer_contacto_humano()
    if nombre == "buscar_documentos":
        return documentos_tools.buscar_documentos(conn, embed_fn, argumentos)
    if nombre == "buscar_formularios":
        return formularios_tools.buscar_formularios(conn, argumentos)
    if nombre == "guardar_respuesta_formulario":
        return formularios_tools.guardar_respuesta_formulario(conn, session_id, argumentos)
    raise ValueError(f"Tool desconocida: {nombre}")
