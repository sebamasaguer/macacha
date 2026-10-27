import uuid

from agent import sessions
from agent.admin import formularios_repository as formularios
from ingest import repository as repo

CAMPOS_TRABAJO = [
    {"etiqueta": "Nombre y apellido", "tipo": "texto", "obligatorio": True, "opciones": None},
    {"etiqueta": "DNI", "tipo": "dni", "obligatorio": True, "opciones": None},
    {"etiqueta": "Teléfono", "tipo": "telefono", "obligatorio": True, "opciones": None},
    {"etiqueta": "¿Participaría de la capacitación?", "tipo": "si_no", "obligatorio": True, "opciones": None},
]


def crear_organismo(conn, nombre: str = "Subsecretaría de Trabajo") -> int:
    return repo.upsert_organismo(conn, nombre)


def crear_tramite(conn, organismo_id: int, tramite_id: str = "TR-0001", nombre: str = "Denuncia laboral") -> str:
    repo.upsert_tramite(conn, tramite_id, organismo_id, "Trabajo", nombre)
    return tramite_id


def datos_formulario(**cambios) -> dict:
    datos = {
        "nombre": "Inscripción a la capacitación",
        "descripcion_uso": "Inscripción a la capacitación de la Subsecretaría de Trabajo",
        "aviso_finalidad": "La Subsecretaría de Trabajo usa tus datos para inscribirte a la capacitación.",
        "tramite_id": None,
        "estado": "activo",
        "fecha_cierre": None,
        "cupo": None,
    }
    datos.update(cambios)
    return datos


def crear_formulario(conn, organismo_id: int, campos: list[dict] | None = None, **cambios) -> str:
    return formularios.crear_formulario(
        conn, organismo_id, datos_formulario(**cambios), campos or CAMPOS_TRABAJO, "creador@organismo.gob.ar"
    )


def crear_sesion(conn) -> str:
    session_id = str(uuid.uuid4())
    sessions.crear_sesion_si_no_existe(conn, session_id)
    return session_id


def valores_validos(dni: str = "30123456", nombre: str = "Ana Pérez", participa: bool = True) -> dict:
    return {
        "nombre_y_apellido": nombre,
        "dni": dni,
        "telefono": "387 456-7890",
        "participaria_de_la_capacitacion": participa,
    }
