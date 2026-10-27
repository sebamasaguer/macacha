import type { MensajeAdmin } from "./admin-api";

export type TipoCampo =
  | "texto"
  | "texto_largo"
  | "dni"
  | "telefono"
  | "email"
  | "numero"
  | "fecha"
  | "si_no"
  | "opcion";
export type EstadoFormulario = "borrador" | "activo" | "cerrado";
export type EstadoEfectivo = "borrador" | "cerrado" | "vencido" | "cupo_completo" | "abierto";

export type CampoFormulario = {
  clave?: string;
  etiqueta: string;
  tipo: TipoCampo;
  obligatorio: boolean;
  opciones: string[] | null;
};

export type FormularioResumen = {
  id: string;
  organismo_id: number;
  organismo: string;
  nombre: string;
  descripcion_uso: string;
  aviso_finalidad: string;
  tramite_id: string | null;
  estado: EstadoFormulario;
  estado_efectivo: EstadoEfectivo;
  fecha_cierre: string | null;
  cupo: number | null;
  respuestas: number;
  hay_respuestas: boolean;
  creado_por_email: string;
  creado_en: string;
  actualizado_en: string;
};

export type FormularioDetalle = FormularioResumen & { campos: CampoFormulario[] };

export type FormularioEntrada = {
  organismo_id: number | null;
  nombre: string;
  descripcion_uso: string;
  aviso_finalidad: string;
  tramite_id: string | null;
  estado: EstadoFormulario;
  fecha_cierre: string | null;
  cupo: number | null;
  campos: CampoFormulario[];
};

export type PaginaFormularios = {
  formularios: FormularioResumen[];
  total: number;
  page: number;
  page_size: number;
};

export type RespuestaFila = { id: string; creado_en: string; valores: Record<string, unknown> };

export type PaginaRespuestas = {
  respuestas: RespuestaFila[];
  campos: CampoFormulario[];
  total: number;
  page: number;
  page_size: number;
};

export type RespuestaDetalle = RespuestaFila & {
  session_id: string;
  formulario: { id: string; nombre: string };
  campos: CampoFormulario[];
  mensajes: MensajeAdmin[];
};

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function parsearOLanzar<T>(respuesta: Response, mensajePorDefecto: string): Promise<T> {
  if (!respuesta.ok) {
    const cuerpo = await respuesta.json().catch(() => null);
    const detalle = typeof cuerpo?.detail === "string" ? cuerpo.detail : null;
    throw new Error(detalle ?? mensajePorDefecto);
  }
  return respuesta.json();
}

export async function listarFormularios(page: number, pageSize: number): Promise<PaginaFormularios> {
  const respuesta = await fetch(`${BASE_URL}/admin/formularios?page=${page}&page_size=${pageSize}`, {
    credentials: "include",
  });
  return parsearOLanzar(respuesta, "No se pudo cargar la lista de formularios");
}

export async function obtenerFormulario(id: string): Promise<FormularioDetalle | null> {
  const respuesta = await fetch(`${BASE_URL}/admin/formularios/${id}`, { credentials: "include" });
  if (respuesta.status === 404) return null;
  return parsearOLanzar(respuesta, "No se pudo cargar el formulario");
}

export async function crearFormulario(entrada: FormularioEntrada): Promise<{ id: string }> {
  const respuesta = await fetch(`${BASE_URL}/admin/formularios`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(entrada),
  });
  return parsearOLanzar(respuesta, "No se pudo crear el formulario");
}

export async function editarFormulario(id: string, entrada: FormularioEntrada): Promise<void> {
  const respuesta = await fetch(`${BASE_URL}/admin/formularios/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(entrada),
  });
  await parsearOLanzar(respuesta, "No se pudo guardar el formulario");
}

export async function listarRespuestas(id: string, page: number, pageSize: number): Promise<PaginaRespuestas> {
  const respuesta = await fetch(
    `${BASE_URL}/admin/formularios/${id}/respuestas?page=${page}&page_size=${pageSize}`,
    { credentials: "include" }
  );
  return parsearOLanzar(respuesta, "No se pudieron cargar las respuestas");
}

export async function obtenerRespuesta(id: string, respuestaId: string): Promise<RespuestaDetalle | null> {
  const respuesta = await fetch(`${BASE_URL}/admin/formularios/${id}/respuestas/${respuestaId}`, {
    credentials: "include",
  });
  if (respuesta.status === 404) return null;
  return parsearOLanzar(respuesta, "No se pudo cargar la respuesta");
}

export async function borrarRespuesta(id: string, respuestaId: string): Promise<void> {
  const respuesta = await fetch(`${BASE_URL}/admin/formularios/${id}/respuestas/${respuestaId}`, {
    method: "DELETE",
    credentials: "include",
  });
  await parsearOLanzar(respuesta, "No se pudo borrar la respuesta");
}

export async function descargarCsv(id: string, nombreArchivo: string): Promise<void> {
  const respuesta = await fetch(`${BASE_URL}/admin/formularios/${id}/respuestas.csv`, {
    credentials: "include",
  });
  if (!respuesta.ok) throw new Error("No se pudo exportar el CSV");
  const url = URL.createObjectURL(await respuesta.blob());
  const enlace = document.createElement("a");
  enlace.href = url;
  enlace.download = nombreArchivo;
  document.body.appendChild(enlace);
  enlace.click();
  enlace.remove();
  URL.revokeObjectURL(url);
}
