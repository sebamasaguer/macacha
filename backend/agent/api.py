import json
import logging
import os
import uuid
from datetime import datetime, timezone
from functools import lru_cache, partial
from typing import Iterator, Literal

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Request, Response, UploadFile
import anyio
from anyio import to_thread
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from agent import audio_transcription, feedback, formularios_csv, mail, rate_limit, sessions
from agent.admin import chats_repository as admin_chats_repository
from agent.admin import contacto_repository
from agent.admin import documentos_repository
from agent.admin.email_contacto import normalizar_email_contacto
from agent.admin import feedback_repository as admin_feedback_repository
from agent.admin import formularios_repository
from agent.admin import repository as admin_repository
from agent.admin import security as admin_security
from agent.admin import tramite_editor as admin_tramite_editor
from agent.admin import tramites_repository as admin_tramites_repository
from agent.admin.dependencies import AdminActual, requiere_admin, requiere_super_admin
from agent.chat_client import build_real_chat_client
from agent.formularios_validacion import generar_clave
from agent.orchestrator import procesar_turno
from db.pool import crear_pool
from ingest.documento_texto import MAX_BYTES as DOCUMENTO_MAX_BYTES
from ingest.documento_texto import DocumentoInvalido, extraer_texto, fragmentar
from ingest.openai_client import build_real_client
from ingest.repository import (
    incrementar_veces_consultado,
    obtener_snapshot_vigente,
    obtener_top_tramites,
    obtener_tramites_frecuentes,
)

load_dotenv()

logger = logging.getLogger(__name__)

if not os.environ.get("ADMIN_JWT_SECRET"):
    raise RuntimeError(
        "Falta la variable de entorno ADMIN_JWT_SECRET. Ver .env.example."
    )

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.environ.get("FRONTEND_ORIGIN", "http://localhost:3000")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@lru_cache
def obtener_pool():
    return crear_pool(os.environ["DATABASE_URL"])


@lru_cache
def obtener_chat_client():
    return build_real_chat_client()


@lru_cache
def obtener_openai_client():
    return build_real_client()


class ChatRequest(BaseModel):
    session_id: uuid.UUID
    mensaje: str


@app.post("/chat")
def chat(
    request: ChatRequest,
    pool=Depends(obtener_pool),
    chat_client=Depends(obtener_chat_client),
    openai_client=Depends(obtener_openai_client),
):
    def generar() -> Iterator[str]:
        with pool.connection() as conn:
            try:
                fuentes_del_turno: list[dict] = []
                for evento in procesar_turno(
                    conn,
                    chat_client,
                    openai_client.generate_embeddings,
                    openai_client.rerank,
                    str(request.session_id),
                    request.mensaje,
                ):
                    if evento["tipo"] == "fin":
                        fuentes_del_turno = evento["fuentes"]
                    yield f"data: {json.dumps(evento, ensure_ascii=False)}\n\n"
                for fuente in fuentes_del_turno:
                    incrementar_veces_consultado(conn, fuente["tramite_id"])
                conn.commit()
            except Exception:
                conn.rollback()
                evento_error = {"tipo": "error", "mensaje": "Ocurrió un error al procesar tu mensaje."}
                yield f"data: {json.dumps(evento_error, ensure_ascii=False)}\n\n"

    return StreamingResponse(generar(), media_type="text/event-stream")


@app.get("/sesiones/{session_id}/mensajes")
def obtener_mensajes(session_id: uuid.UUID, pool=Depends(obtener_pool)):
    with pool.connection() as conn:
        return sessions.obtener_mensajes_visibles(conn, str(session_id))


@app.get("/tramites/{tramite_id}")
def obtener_tramite(tramite_id: str, pool=Depends(obtener_pool)):
    with pool.connection() as conn:
        snapshot = obtener_snapshot_vigente(conn, tramite_id)
        if snapshot is None:
            raise HTTPException(status_code=404, detail="Trámite no encontrado")
        return {
            "tramite_id": tramite_id,
            "nombre_oficial": snapshot["nombre_oficial"],
            "organismo": snapshot["organismo"],
            "categoria": snapshot["categoria"],
            "requisitos": snapshot.get("requisitos", []),
            "costo": snapshot.get("costo", ""),
            "modalidad": snapshot.get("modalidad", ""),
            "duracion": snapshot.get("duracion", ""),
            "pasos": snapshot.get("pasos", []),
            "enlaces_oficiales": snapshot.get("enlaces_oficiales", []),
            "telefono_contacto": snapshot.get("telefono_contacto", ""),
            "email_contacto": snapshot.get("email_contacto", ""),
        }


@app.get("/organismos/{organismo}/tramites-frecuentes")
def tramites_frecuentes(organismo: str, pool=Depends(obtener_pool)):
    with pool.connection() as conn:
        return obtener_tramites_frecuentes(conn, organismo)


@app.get("/tramites-frecuentes")
def top_tramites(pool=Depends(obtener_pool)):
    with pool.connection() as conn:
        return obtener_top_tramites(conn)


class ContactoPayload(BaseModel):
    session_id: uuid.UUID
    tramite_id: str | None = None
    nombre: str = Field(min_length=1)
    email: str = Field(min_length=1)
    telefono: str = Field(min_length=1)
    consulta: str = Field(min_length=1)


def _armar_cuerpo_mail(request: ContactoPayload, mensajes: list[dict]) -> str:
    lineas = [
        f"Nombre: {request.nombre}",
        f"Email: {request.email}",
        f"Teléfono: {request.telefono}",
        "",
        "Consulta:",
        request.consulta,
        "",
        "--- Conversación completa ---",
    ]
    for mensaje in mensajes:
        etiqueta = "Persona" if mensaje["rol"] == "user" else "Macacha"
        lineas.append(f"{etiqueta}: {mensaje['contenido']}")
    return "\n".join(lineas)


@app.post("/contacto")
def crear_solicitud_contacto(request: ContactoPayload, pool=Depends(obtener_pool)):
    with pool.connection() as conn:
        sessions.crear_sesion_si_no_existe(conn, str(request.session_id))

        tramite_id = request.tramite_id
        organismo_id = None
        if tramite_id:
            organismo_id = admin_tramites_repository.obtener_organismo_id_de_tramite(conn, tramite_id)
            if organismo_id is None:
                tramite_id = None  # trámite desconocido -> tratamos como "sin trámite"

        solicitud_id = contacto_repository.crear_solicitud(
            conn,
            str(request.session_id),
            tramite_id,
            organismo_id,
            request.nombre,
            request.email,
            request.telefono,
            request.consulta,
        )
        conn.commit()

        destinatarios = contacto_repository.resolver_destinatarios(conn, organismo_id)
        mensajes = sessions.obtener_mensajes_visibles(conn, str(request.session_id))

    try:
        mail.enviar_mail(
            destinatarios,
            asunto=f"Nueva consulta de {request.nombre}",
            cuerpo_texto=_armar_cuerpo_mail(request, mensajes),
        )
    except Exception:
        logger.exception("Falló el envío de mail de contacto para la solicitud %s", solicitud_id)

    return {"ok": True}


class FeedbackRequest(BaseModel):
    session_id: uuid.UUID
    mensaje_id: uuid.UUID
    util: bool
    motivo: feedback.MotivoFeedback | None = None
    comentario: str | None = Field(default=None, max_length=500)


@app.post("/feedback")
def registrar_feedback(request: FeedbackRequest, pool=Depends(obtener_pool)):
    comentario = (request.comentario or "").strip() or None
    if request.util and (request.motivo is not None or comentario is not None):
        raise HTTPException(
            status_code=422, detail="El motivo y el comentario solo aplican a un voto negativo"
        )

    with pool.connection() as conn:
        if not feedback.mensaje_votable(conn, str(request.session_id), str(request.mensaje_id)):
            raise HTTPException(status_code=404, detail="Respuesta no encontrada")
        feedback.guardar_voto(
            conn,
            str(request.session_id),
            str(request.mensaje_id),
            request.util,
            request.motivo,
            comentario,
        )
        conn.commit()
    return {"ok": True}


_FORMATOS_DE_AUDIO = {
    "audio/flac",
    "audio/mpeg",
    "audio/mp3",
    "audio/mp4",
    "video/mp4",
    "audio/x-m4a",
    "audio/m4a",
    "audio/ogg",
    "application/ogg",
    "audio/wav",
    "audio/x-wav",
    "audio/webm",
    "video/webm",
}

_AUDIO_MAX_BYTES_POR_DEFECTO = 4 * 1024 * 1024
# Hilos propios: un OpenAI lento no debe dejar sin hilos al chat, que comparte el pool por defecto.
_hilos_audio = anyio.CapacityLimiter(4)
_limitador_audio = rate_limit.LimitadorPorIP()


def _entero_de_entorno(nombre: str, defecto: int) -> int:
    try:
        return int(os.environ.get(nombre, defecto))
    except (TypeError, ValueError):
        return defecto


@app.post("/audio/transcribe")
async def transcribir_audio(request: Request):
    ip = rate_limit.ip_cliente(
        request.headers.get("x-forwarded-for"),
        request.client.host if request.client else None,
        _entero_de_entorno("AUDIO_PROXY_HOPS", 1),
    )
    limite = _entero_de_entorno("AUDIO_RATE_LIMIT_PER_MINUTE", 6)
    if limite > 0:
        espera = _limitador_audio.verificar(ip, limite)
        if espera is not None:
            logger.warning("Límite de audio superado para la IP %s", ip)
            raise HTTPException(
                status_code=429,
                detail="Hiciste muchas consultas por voz seguidas. Probá de nuevo en un minuto.",
                headers={"Retry-After": str(espera)},
            )

    content_type = (request.headers.get("content-type", "").split(";", 1)[0].strip().lower()) or "audio/webm"
    if content_type not in _FORMATOS_DE_AUDIO:
        raise HTTPException(status_code=415, detail="El formato de audio no está permitido.")

    maximo = _entero_de_entorno("AUDIO_MAX_BYTES", _AUDIO_MAX_BYTES_POR_DEFECTO)
    demasiado_grande = HTTPException(status_code=413, detail="El audio supera el tamaño máximo permitido.")
    declarado = request.headers.get("content-length")
    if declarado and declarado.isdigit() and int(declarado) > maximo:
        raise demasiado_grande

    datos = bytearray()
    async for parte in request.stream():
        datos.extend(parte)
        if len(datos) > maximo:
            raise demasiado_grande
    if not datos:
        raise HTTPException(status_code=400, detail="El audio está vacío.")

    try:
        resultado = await to_thread.run_sync(
            partial(
                audio_transcription.transcribe_audio_bytes_detailed,
                bytes(datos),
                filename=request.query_params.get("filename") or "consulta-audio",
                content_type=content_type,
            ),
            limiter=_hilos_audio,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=422, detail="No pude obtener una transcripción confiable de ese audio."
        ) from error
    except RuntimeError as error:
        if "not_configured" in str(error):
            raise HTTPException(status_code=503, detail="La transcripción de audio no está configurada.") from error
        logger.error("Falló la transcripción de audio: %s", error, exc_info=error.__cause__)
        raise HTTPException(status_code=502, detail="No se pudo transcribir el audio en este momento.") from error
    except Exception as error:
        logger.exception("Error inesperado al transcribir audio")
        raise HTTPException(status_code=502, detail="No se pudo transcribir el audio en este momento.") from error

    return resultado.to_dict()


class LoginRequest(BaseModel):
    email: str
    password: str


@app.post("/admin/login")
def admin_login(request: LoginRequest, response: Response, pool=Depends(obtener_pool)):
    with pool.connection() as conn:
        admin = admin_repository.obtener_admin_por_email(conn, request.email)

        if (
            admin is None
            or not admin["activo"]
            or not admin_security.verify_password(request.password, admin["password_hash"])
        ):
            raise HTTPException(status_code=401, detail="Credenciales inválidas")

        organismo = (
            admin_tramites_repository.obtener_nombre_organismo(conn, admin["organismo_id"])
            if admin["organismo_id"] is not None
            else None
        )

        token = admin_security.crear_token(admin)

    response.set_cookie(
        "admin_session",
        token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=86400,
        domain=os.environ.get("COOKIE_DOMAIN") or None,
    )
    return {"email": admin["email"], "rol": admin["rol"], "organismo": organismo}


@app.post("/admin/logout")
def admin_logout(response: Response):
    response.delete_cookie("admin_session", domain=os.environ.get("COOKIE_DOMAIN") or None)
    return {"ok": True}


@app.get("/admin/me")
def admin_me(admin: AdminActual = Depends(requiere_admin), pool=Depends(obtener_pool)):
    with pool.connection() as conn:
        admin_db = admin_repository.obtener_admin_por_id(conn, admin.id)
        if admin_db is None or not admin_db["activo"]:
            raise HTTPException(status_code=401, detail="No autenticado")
        organismo = (
            admin_tramites_repository.obtener_nombre_organismo(conn, admin_db["organismo_id"])
            if admin_db["organismo_id"] is not None
            else None
        )
    puede = admin_db["rol"] == "super_admin" or admin_db["puede_crear_formularios"]
    return {
        "email": admin_db["email"],
        "rol": admin_db["rol"],
        "organismo": organismo,
        "puede_crear_formularios": puede,
    }


def requiere_gestor_de_formularios(
    admin: AdminActual = Depends(requiere_admin), pool=Depends(obtener_pool)
) -> AdminActual:
    """El permiso se lee de la base en cada pedido: activarlo o retirarlo tiene efecto inmediato."""
    if admin.rol == "super_admin":
        return admin
    with pool.connection() as conn:
        admin_db = admin_repository.obtener_admin_por_id(conn, admin.id)
    if admin_db is None or not admin_db["activo"] or not admin_db["puede_crear_formularios"]:
        raise HTTPException(status_code=403, detail="No tenés permiso para gestionar formularios")
    return admin


@app.get("/admin/sesiones")
def admin_listar_sesiones(
    page: int = 1,
    page_size: int = 20,
    admin: AdminActual = Depends(requiere_admin),
    pool=Depends(obtener_pool),
):
    with pool.connection() as conn:
        if admin.rol == "admin_organismo":
            sesiones, total = admin_chats_repository.listar_sesiones_de_organismo(
                conn, admin.organismo_id, page, page_size
            )
        else:
            sesiones = admin_chats_repository.listar_sesiones(conn, page, page_size)
            total = admin_chats_repository.contar_sesiones(conn)
    return {"sesiones": sesiones, "total": total, "page": page, "page_size": page_size}


@app.get("/admin/sesiones/{session_id}")
def admin_obtener_sesion(
    session_id: uuid.UUID,
    admin: AdminActual = Depends(requiere_admin),
    pool=Depends(obtener_pool),
):
    with pool.connection() as conn:
        if admin.rol == "admin_organismo":
            permitido = admin_chats_repository.sesion_pertenece_a_organismo(
                conn, str(session_id), admin.organismo_id
            )
        else:
            permitido = admin_chats_repository.sesion_existe(conn, str(session_id))

        if not permitido:
            raise HTTPException(status_code=404, detail="Sesión no encontrada")
        return admin_chats_repository.obtener_mensajes_completos(conn, str(session_id))


@app.get("/admin/feedback/metricas")
def admin_metricas_feedback(admin: AdminActual = Depends(requiere_admin), pool=Depends(obtener_pool)):
    with pool.connection() as conn:
        organismo_id = admin.organismo_id if admin.rol == "admin_organismo" else None
        return admin_feedback_repository.calcular_metricas(conn, organismo_id)


@app.get("/admin/tramites")
def admin_listar_tramites(admin: AdminActual = Depends(requiere_admin), pool=Depends(obtener_pool)):
    with pool.connection() as conn:
        organismo_id = admin.organismo_id if admin.rol == "admin_organismo" else None
        return admin_tramites_repository.listar_tramites(conn, organismo_id)


@app.get("/admin/organismos")
def admin_listar_organismos(admin: AdminActual = Depends(requiere_admin), pool=Depends(obtener_pool)):
    with pool.connection() as conn:
        return admin_tramites_repository.listar_organismos(conn)


def _verificar_tramite_de_mi_organismo(conn, admin: AdminActual, tramite_id: str) -> None:
    if admin.rol != "admin_organismo":
        return
    organismo_del_tramite = admin_tramites_repository.obtener_organismo_id_de_tramite(conn, tramite_id)
    if organismo_del_tramite != admin.organismo_id:
        raise HTTPException(status_code=404, detail="Trámite no encontrado")


def _verificar_payload_de_mi_organismo(conn, admin: AdminActual, organismo_payload: str) -> None:
    if admin.rol != "admin_organismo":
        return
    nombre_organismo_admin = admin_tramites_repository.obtener_nombre_organismo(conn, admin.organismo_id)
    if organismo_payload != nombre_organismo_admin:
        raise HTTPException(
            status_code=400, detail="No podés asignar un trámite a otro organismo"
        )


def _verificar_organismo_existente(conn, nombre: str) -> None:
    if admin_tramites_repository.obtener_organismo_id_por_nombre(conn, nombre) is None:
        raise HTTPException(
            status_code=422, detail=f"El organismo '{nombre}' no existe. Elegí uno de la lista."
        )


@app.get("/admin/tramites/{tramite_id}")
def admin_obtener_tramite(
    tramite_id: str, admin: AdminActual = Depends(requiere_admin), pool=Depends(obtener_pool)
):
    with pool.connection() as conn:
        _verificar_tramite_de_mi_organismo(conn, admin, tramite_id)
        snapshot = obtener_snapshot_vigente(conn, tramite_id)
        if snapshot is None:
            raise HTTPException(status_code=404, detail="Trámite no encontrado")
        return {
            "organismo": snapshot["organismo"],
            "categoria": snapshot["categoria"],
            "nombre_oficial": snapshot["nombre_oficial"],
            "descripcion": snapshot.get("descripcion", ""),
            "objetivo": snapshot.get("objetivo", ""),
            "requisitos": snapshot.get("requisitos", []),
            "pasos": snapshot.get("pasos", []),
            "costo": snapshot.get("costo", ""),
            "modalidad": snapshot.get("modalidad", ""),
            "duracion": snapshot.get("duracion", ""),
            "telefono_contacto": snapshot.get("telefono_contacto", ""),
            "email_contacto": snapshot.get("email_contacto", ""),
            "problemas_frecuentes": snapshot.get("problemas_frecuentes", []),
            "sinonimos": snapshot.get("sinonimos", []),
            "keywords": snapshot.get("keywords", []),
            "enlaces_oficiales": snapshot.get("enlaces_oficiales", []),
            "preguntas_frecuentes": snapshot.get("preguntas_frecuentes", []),
        }


class FaqPayload(BaseModel):
    pregunta: str
    respuesta: str


class TramitePayload(BaseModel):
    organismo: str = Field(min_length=1)
    categoria: str = ""
    nombre_oficial: str = Field(min_length=1)
    descripcion: str = ""
    objetivo: str = ""
    requisitos: list[str] = []
    pasos: list[str] = []
    costo: str = ""
    modalidad: str = ""
    duracion: str = ""
    telefono_contacto: str = ""
    email_contacto: str = ""
    problemas_frecuentes: list[str] = []
    sinonimos: list[str] = []
    keywords: list[str] = []
    enlaces_oficiales: list[str] = []
    preguntas_frecuentes: list[FaqPayload] = []


@app.put("/admin/tramites/{tramite_id}")
def admin_editar_tramite(
    tramite_id: str,
    request: TramitePayload,
    admin: AdminActual = Depends(requiere_admin),
    pool=Depends(obtener_pool),
    openai_client=Depends(obtener_openai_client),
):
    with pool.connection() as conn:
        _verificar_tramite_de_mi_organismo(conn, admin, tramite_id)
        _verificar_payload_de_mi_organismo(conn, admin, request.organismo)

        if obtener_snapshot_vigente(conn, tramite_id) is None:
            raise HTTPException(status_code=404, detail="Trámite no encontrado")

        _verificar_organismo_existente(conn, request.organismo)

        try:
            resultado = admin_tramite_editor.editar_tramite(
                conn, tramite_id, request.model_dump(), openai_client.generate_embeddings
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise HTTPException(
                status_code=502,
                detail="No se pudieron generar los embeddings. Verificá la configuración de OpenAI.",
            )
    return resultado


@app.post("/admin/tramites")
def admin_crear_tramite(
    request: TramitePayload,
    admin: AdminActual = Depends(requiere_admin),
    pool=Depends(obtener_pool),
    openai_client=Depends(obtener_openai_client),
):
    with pool.connection() as conn:
        _verificar_payload_de_mi_organismo(conn, admin, request.organismo)
        _verificar_organismo_existente(conn, request.organismo)
        try:
            resultado = admin_tramite_editor.crear_tramite(
                conn, request.model_dump(), openai_client.generate_embeddings
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise HTTPException(
                status_code=502,
                detail="No se pudieron generar los embeddings. Verificá la configuración de OpenAI.",
            )
    return resultado


class UsuarioPayload(BaseModel):
    email: str = Field(min_length=1)
    password: str = Field(min_length=8)
    rol: Literal["super_admin", "admin_organismo"]
    organismo_id: int | None = None
    puede_crear_formularios: bool = False


class UsuarioEdicionPayload(BaseModel):
    rol: Literal["super_admin", "admin_organismo"]
    organismo_id: int | None = None
    activo: bool
    password: str | None = Field(default=None, min_length=8)
    puede_crear_formularios: bool | None = None


def _validar_consistencia_rol_organismo(rol: str, organismo_id: int | None) -> None:
    if rol == "admin_organismo" and organismo_id is None:
        raise HTTPException(
            status_code=400, detail="Un admin de organismo necesita un organismo asignado"
        )
    if rol == "super_admin" and organismo_id is not None:
        raise HTTPException(
            status_code=400, detail="Un super admin no puede tener un organismo asignado"
        )


@app.get("/admin/usuarios")
def admin_listar_usuarios(
    admin: AdminActual = Depends(requiere_super_admin), pool=Depends(obtener_pool)
):
    with pool.connection() as conn:
        return admin_repository.listar_admins(conn)


@app.post("/admin/usuarios")
def admin_crear_usuario(
    request: UsuarioPayload,
    admin: AdminActual = Depends(requiere_super_admin),
    pool=Depends(obtener_pool),
):
    _validar_consistencia_rol_organismo(request.rol, request.organismo_id)
    password_hash = admin_security.hash_password(request.password)
    with pool.connection() as conn:
        if admin_repository.obtener_admin_por_email(conn, request.email) is not None:
            raise HTTPException(status_code=409, detail="Ya existe un admin con ese email")
        admin_repository.crear_admin(
            conn,
            request.email,
            password_hash,
            request.rol,
            request.organismo_id,
            puede_crear_formularios=request.puede_crear_formularios and request.rol == "admin_organismo",
        )
        conn.commit()
    return {"ok": True}


@app.put("/admin/usuarios/{admin_id}")
def admin_editar_usuario(
    admin_id: uuid.UUID,
    request: UsuarioEdicionPayload,
    admin: AdminActual = Depends(requiere_super_admin),
    pool=Depends(obtener_pool),
):
    _validar_consistencia_rol_organismo(request.rol, request.organismo_id)
    password_hash = admin_security.hash_password(request.password) if request.password else None
    with pool.connection() as conn:
        if admin_repository.obtener_admin_por_id(conn, str(admin_id)) is None:
            raise HTTPException(status_code=404, detail="Admin no encontrado")
        puede = (
            None
            if request.puede_crear_formularios is None
            else request.puede_crear_formularios and request.rol == "admin_organismo"
        )
        admin_repository.editar_admin(
            conn,
            str(admin_id),
            request.rol,
            request.organismo_id,
            request.activo,
            password_hash,
            puede_crear_formularios=puede,
        )
        conn.commit()
    return {"ok": True}


class ContactoEstadoPayload(BaseModel):
    estado: Literal["pendiente", "resuelto"]


@app.get("/admin/contacto")
def admin_listar_contacto(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin: AdminActual = Depends(requiere_admin),
    pool=Depends(obtener_pool),
):
    with pool.connection() as conn:
        organismo_id = admin.organismo_id if admin.rol == "admin_organismo" else None
        solicitudes, total = contacto_repository.listar_solicitudes(conn, organismo_id, page, page_size)
    return {"solicitudes": solicitudes, "total": total, "page": page, "page_size": page_size}


def _verificar_solicitud_de_mi_organismo(conn, admin: AdminActual, solicitud: dict | None) -> None:
    if solicitud is None:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    if admin.rol == "admin_organismo" and solicitud["organismo_id"] != admin.organismo_id:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")


class CasillaPayload(BaseModel):
    email_contacto: str | None = None


@app.get("/admin/contacto/casillas")
def admin_listar_casillas(admin: AdminActual = Depends(requiere_admin), pool=Depends(obtener_pool)):
    with pool.connection() as conn:
        organismo_id = admin.organismo_id if admin.rol == "admin_organismo" else None
        return contacto_repository.listar_casillas(conn, organismo_id)


@app.put("/admin/contacto/casillas/{organismo_id}")
def admin_guardar_casilla(
    organismo_id: int,
    request: CasillaPayload,
    admin: AdminActual = Depends(requiere_admin),
    pool=Depends(obtener_pool),
):
    if admin.rol == "admin_organismo" and organismo_id != admin.organismo_id:
        raise HTTPException(status_code=404, detail="Organismo no encontrado")
    try:
        email = normalizar_email_contacto(request.email_contacto)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))

    with pool.connection() as conn:
        casilla = contacto_repository.guardar_casilla(conn, organismo_id, email)
        if casilla is None:
            raise HTTPException(status_code=404, detail="Organismo no encontrado")
        conn.commit()
    return casilla


@app.get("/admin/contacto/{solicitud_id}")
def admin_obtener_contacto(
    solicitud_id: uuid.UUID, admin: AdminActual = Depends(requiere_admin), pool=Depends(obtener_pool)
):
    with pool.connection() as conn:
        solicitud = contacto_repository.obtener_solicitud(conn, str(solicitud_id))
        _verificar_solicitud_de_mi_organismo(conn, admin, solicitud)
        mensajes = admin_chats_repository.obtener_mensajes_completos(conn, solicitud["session_id"])
    return {**solicitud, "mensajes": mensajes}


@app.put("/admin/contacto/{solicitud_id}")
def admin_editar_estado_contacto(
    solicitud_id: uuid.UUID,
    request: ContactoEstadoPayload,
    admin: AdminActual = Depends(requiere_admin),
    pool=Depends(obtener_pool),
):
    with pool.connection() as conn:
        solicitud = contacto_repository.obtener_solicitud(conn, str(solicitud_id))
        _verificar_solicitud_de_mi_organismo(conn, admin, solicitud)
        quien = admin_repository.obtener_admin_por_id(conn, admin.id)
        contacto_repository.actualizar_estado(
            conn, str(solicitud_id), request.estado, quien["email"] if quien else None
        )
        conn.commit()
    return {"ok": True}


# ---------- Formularios por organismo ----------


class CampoFormularioPayload(BaseModel):
    clave: str | None = None
    etiqueta: str = Field(min_length=1, max_length=120)
    tipo: Literal["texto", "texto_largo", "dni", "telefono", "email", "numero", "fecha", "si_no", "opcion"]
    obligatorio: bool = True
    opciones: list[str] | None = None


class FormularioPayload(BaseModel):
    organismo_id: int | None = None
    nombre: str = Field(min_length=1, max_length=150)
    descripcion_uso: str = Field(default="", max_length=500)
    aviso_finalidad: str = Field(default="", max_length=500)
    tramite_id: str | None = None
    estado: Literal["borrador", "activo", "cerrado"] = "borrador"
    fecha_cierre: datetime | None = None
    cupo: int | None = Field(default=None, gt=0)
    campos: list[CampoFormularioPayload] = Field(min_length=1, max_length=30)


def _cargar_formulario_de_mi_organismo(conn, admin: AdminActual, formulario_id: uuid.UUID) -> dict:
    formulario = formularios_repository.obtener_formulario(conn, str(formulario_id))
    if formulario is None or (admin.rol == "admin_organismo" and formulario["organismo_id"] != admin.organismo_id):
        raise HTTPException(status_code=404, detail="Formulario no encontrado")
    return formulario


def _datos_de_formulario(conn, request: FormularioPayload, organismo_id: int) -> dict:
    if request.tramite_id is not None:
        if admin_tramites_repository.obtener_organismo_id_de_tramite(conn, request.tramite_id) != organismo_id:
            raise HTTPException(status_code=400, detail="El trámite no pertenece al organismo del formulario")
    fecha_cierre = request.fecha_cierre
    if fecha_cierre is not None and fecha_cierre.tzinfo is None:
        fecha_cierre = fecha_cierre.replace(tzinfo=timezone.utc)
    return {
        "nombre": request.nombre,
        "descripcion_uso": request.descripcion_uso,
        "aviso_finalidad": request.aviso_finalidad,
        "tramite_id": request.tramite_id,
        "estado": request.estado,
        "fecha_cierre": fecha_cierre,
        "cupo": request.cupo,
    }


@app.get("/admin/formularios")
def admin_listar_formularios(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin: AdminActual = Depends(requiere_admin),
    pool=Depends(obtener_pool),
):
    with pool.connection() as conn:
        organismo_id = admin.organismo_id if admin.rol == "admin_organismo" else None
        lista, total = formularios_repository.listar_formularios(conn, organismo_id, page, page_size)
    return {"formularios": lista, "total": total, "page": page, "page_size": page_size}


@app.post("/admin/formularios")
def admin_crear_formulario(
    request: FormularioPayload,
    admin: AdminActual = Depends(requiere_gestor_de_formularios),
    pool=Depends(obtener_pool),
):
    if admin.rol == "admin_organismo":
        organismo_id = admin.organismo_id
    elif request.organismo_id is None:
        raise HTTPException(status_code=400, detail="Elegí el organismo del formulario")
    else:
        organismo_id = request.organismo_id
    with pool.connection() as conn:
        if admin_tramites_repository.obtener_nombre_organismo(conn, organismo_id) is None:
            raise HTTPException(status_code=400, detail="El organismo no existe")
        datos = _datos_de_formulario(conn, request, organismo_id)
        creador = admin_repository.obtener_admin_por_id(conn, admin.id)
        try:
            formulario_id = formularios_repository.crear_formulario(
                conn, organismo_id, datos, [c.model_dump() for c in request.campos], creador["email"]
            )
        except ValueError as error:
            conn.rollback()
            raise HTTPException(status_code=400, detail=str(error)) from error
        conn.commit()
    return {"id": formulario_id}


@app.get("/admin/formularios/{formulario_id}")
def admin_obtener_formulario(
    formulario_id: uuid.UUID, admin: AdminActual = Depends(requiere_admin), pool=Depends(obtener_pool)
):
    with pool.connection() as conn:
        return _cargar_formulario_de_mi_organismo(conn, admin, formulario_id)


@app.put("/admin/formularios/{formulario_id}")
def admin_editar_formulario(
    formulario_id: uuid.UUID,
    request: FormularioPayload,
    admin: AdminActual = Depends(requiere_gestor_de_formularios),
    pool=Depends(obtener_pool),
):
    with pool.connection() as conn:
        formulario = _cargar_formulario_de_mi_organismo(conn, admin, formulario_id)
        datos = _datos_de_formulario(conn, request, formulario["organismo_id"])
        try:
            formularios_repository.actualizar_formulario(
                conn, str(formulario_id), datos, [c.model_dump() for c in request.campos]
            )
        except formularios_repository.ReglaDeEdicion as error:
            conn.rollback()
            raise HTTPException(status_code=409, detail=str(error)) from error
        except ValueError as error:
            conn.rollback()
            raise HTTPException(status_code=400, detail=str(error)) from error
        conn.commit()
    return {"ok": True}


@app.get("/admin/formularios/{formulario_id}/respuestas")
def admin_listar_respuestas_formulario(
    formulario_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin: AdminActual = Depends(requiere_admin),
    pool=Depends(obtener_pool),
):
    with pool.connection() as conn:
        formulario = _cargar_formulario_de_mi_organismo(conn, admin, formulario_id)
        respuestas, total = formularios_repository.listar_respuestas(conn, str(formulario_id), page, page_size)
    return {
        "respuestas": [{"id": r["id"], "creado_en": r["creado_en"], "valores": r["valores"]} for r in respuestas],
        "campos": formulario["campos"],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@app.get("/admin/formularios/{formulario_id}/respuestas.csv")
def admin_exportar_respuestas_formulario(
    formulario_id: uuid.UUID, admin: AdminActual = Depends(requiere_admin), pool=Depends(obtener_pool)
):
    with pool.connection() as conn:
        formulario = _cargar_formulario_de_mi_organismo(conn, admin, formulario_id)
        respuestas = formularios_repository.todas_las_respuestas(conn, str(formulario_id))
    contenido = "﻿" + formularios_csv.a_csv(formulario["campos"], respuestas)
    archivo = generar_clave(formulario["nombre"], set())
    return Response(
        content=contenido.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{archivo}-respuestas.csv"'},
    )


@app.get("/admin/formularios/{formulario_id}/respuestas/{respuesta_id}")
def admin_obtener_respuesta_formulario(
    formulario_id: uuid.UUID,
    respuesta_id: uuid.UUID,
    admin: AdminActual = Depends(requiere_admin),
    pool=Depends(obtener_pool),
):
    with pool.connection() as conn:
        formulario = _cargar_formulario_de_mi_organismo(conn, admin, formulario_id)
        respuesta = formularios_repository.obtener_respuesta(conn, str(formulario_id), str(respuesta_id))
        if respuesta is None:
            raise HTTPException(status_code=404, detail="Respuesta no encontrada")
        mensajes = admin_chats_repository.obtener_mensajes_completos(conn, respuesta["session_id"])
    return {
        **respuesta,
        "formulario": {"id": formulario["id"], "nombre": formulario["nombre"]},
        "campos": formulario["campos"],
        "mensajes": mensajes,
    }


@app.delete("/admin/formularios/{formulario_id}/respuestas/{respuesta_id}")
def admin_borrar_respuesta_formulario(
    formulario_id: uuid.UUID,
    respuesta_id: uuid.UUID,
    admin: AdminActual = Depends(requiere_gestor_de_formularios),
    pool=Depends(obtener_pool),
):
    with pool.connection() as conn:
        _cargar_formulario_de_mi_organismo(conn, admin, formulario_id)
        quien = admin_repository.obtener_admin_por_id(conn, admin.id)
        if not formularios_repository.borrar_respuesta(conn, str(formulario_id), str(respuesta_id), quien["email"]):
            raise HTTPException(status_code=404, detail="Respuesta no encontrada")
        conn.commit()
    return {"ok": True}


# --- Documentos por organismo ---------------------------------------------------------------

_LOTE_DE_EMBEDDINGS = 100


def _cargar_documento_de_mi_organismo(conn, admin: AdminActual, documento_id: uuid.UUID) -> dict:
    documento = documentos_repository.obtener_documento(conn, str(documento_id))
    if documento is None or (admin.rol == "admin_organismo" and documento["organismo_id"] != admin.organismo_id):
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    return documento


def _leer_archivo_de_documento(archivo: UploadFile) -> bytes:
    contenido = archivo.file.read(DOCUMENTO_MAX_BYTES + 1)
    if len(contenido) > DOCUMENTO_MAX_BYTES:
        raise HTTPException(status_code=413, detail="El archivo supera el máximo de 10 MB.")
    if not contenido:
        raise HTTPException(status_code=400, detail="El archivo está vacío.")
    return contenido


def _procesar_documento(nombre_archivo: str, contenido: bytes, openai_client) -> tuple[list[str], list[list[float]]]:
    """Extrae, fragmenta y vectoriza antes de tocar la base: si algo falla, no se pierde nada."""
    try:
        fragmentos = fragmentar(extraer_texto(nombre_archivo, contenido))
    except DocumentoInvalido as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    embeddings: list[list[float]] = []
    for inicio in range(0, len(fragmentos), _LOTE_DE_EMBEDDINGS):
        embeddings.extend(openai_client.generate_embeddings(fragmentos[inicio : inicio + _LOTE_DE_EMBEDDINGS]))
    return fragmentos, embeddings


def _titulo_de_documento(titulo: str | None, nombre_archivo: str | None = None) -> str | None:
    titulo = (titulo or "").strip()
    if not titulo and nombre_archivo:
        titulo = os.path.splitext(os.path.basename(nombre_archivo))[0].strip()
    if len(titulo) > 150:
        raise HTTPException(status_code=400, detail="El título no puede superar los 150 caracteres.")
    return titulo or None


@app.get("/admin/documentos")
def admin_listar_documentos(
    organismo_id: int | None = None, admin: AdminActual = Depends(requiere_admin), pool=Depends(obtener_pool)
):
    if admin.rol == "admin_organismo":
        organismo_id = admin.organismo_id
    with pool.connection() as conn:
        return documentos_repository.listar_documentos(conn, organismo_id)


@app.post("/admin/documentos", status_code=201)
def admin_subir_documento(
    archivo: UploadFile = File(...),
    titulo: str | None = Form(None),
    organismo_id: int | None = Form(None),
    admin: AdminActual = Depends(requiere_admin),
    pool=Depends(obtener_pool),
    openai_client=Depends(obtener_openai_client),
):
    if admin.rol == "admin_organismo":
        organismo_id = admin.organismo_id
    elif organismo_id is None:
        raise HTTPException(status_code=400, detail="Elegí el organismo del documento")
    nombre_archivo = archivo.filename or "documento"
    titulo = _titulo_de_documento(titulo, nombre_archivo) or nombre_archivo
    contenido = _leer_archivo_de_documento(archivo)
    fragmentos, embeddings = _procesar_documento(nombre_archivo, contenido, openai_client)
    with pool.connection() as conn:
        if admin_tramites_repository.obtener_nombre_organismo(conn, organismo_id) is None:
            raise HTTPException(status_code=400, detail="El organismo no existe")
        quien = admin_repository.obtener_admin_por_id(conn, admin.id)
        try:
            documento = documentos_repository.crear_documento(
                conn, organismo_id, titulo, nombre_archivo, quien["email"], fragmentos, embeddings
            )
        except documentos_repository.TopeDeDocumentos:
            conn.rollback()
            raise HTTPException(
                status_code=409,
                detail=f"Ya hay {documentos_repository.MAX_DOCUMENTOS_POR_ORGANISMO} documentos en el organismo. Reemplazá o borrá uno.",
            )
        conn.commit()
    return documento


@app.put("/admin/documentos/{documento_id}")
def admin_reemplazar_documento(
    documento_id: uuid.UUID,
    archivo: UploadFile | None = File(None),
    titulo: str | None = Form(None),
    admin: AdminActual = Depends(requiere_admin),
    pool=Depends(obtener_pool),
    openai_client=Depends(obtener_openai_client),
):
    nombre_archivo = archivo.filename if archivo is not None else None
    titulo = _titulo_de_documento(titulo)
    if archivo is None and titulo is None:
        raise HTTPException(status_code=400, detail="Indicá un archivo nuevo, un título nuevo, o ambos.")
    with pool.connection() as conn:
        _cargar_documento_de_mi_organismo(conn, admin, documento_id)
    if archivo is None:
        with pool.connection() as conn:
            documento = documentos_repository.renombrar_documento(conn, str(documento_id), titulo)
            conn.commit()
        return documento
    contenido = _leer_archivo_de_documento(archivo)
    fragmentos, embeddings = _procesar_documento(nombre_archivo or "documento", contenido, openai_client)
    with pool.connection() as conn:
        quien = admin_repository.obtener_admin_por_id(conn, admin.id)
        documento = documentos_repository.reemplazar_contenido(
            conn, str(documento_id), nombre_archivo or "documento", quien["email"], fragmentos, embeddings, titulo
        )
        conn.commit()
    return documento


@app.delete("/admin/documentos/{documento_id}", status_code=204)
def admin_borrar_documento(
    documento_id: uuid.UUID, admin: AdminActual = Depends(requiere_admin), pool=Depends(obtener_pool)
):
    with pool.connection() as conn:
        _cargar_documento_de_mi_organismo(conn, admin, documento_id)
        documentos_repository.borrar_documento(conn, str(documento_id))
        conn.commit()
    return Response(status_code=204)
