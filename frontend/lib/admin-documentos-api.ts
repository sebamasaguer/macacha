export type DocumentoOrganismo = {
  id: string;
  organismo_id: number;
  organismo: string;
  titulo: string;
  nombre_archivo: string;
  subido_por_email: string;
  creado_en: string;
  actualizado_en: string;
  fragmentos: number;
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

export async function listarDocumentos(organismoId?: number): Promise<DocumentoOrganismo[]> {
  const consulta = organismoId !== undefined ? `?organismo_id=${organismoId}` : "";
  const respuesta = await fetch(`${BASE_URL}/admin/documentos${consulta}`, { credentials: "include" });
  return parsearOLanzar(respuesta, "No se pudieron cargar los documentos");
}

export async function subirDocumento(datos: {
  archivo: File;
  titulo?: string;
  organismoId?: number;
}): Promise<DocumentoOrganismo> {
  const formulario = new FormData();
  formulario.append("archivo", datos.archivo);
  if (datos.titulo) formulario.append("titulo", datos.titulo);
  if (datos.organismoId !== undefined) formulario.append("organismo_id", String(datos.organismoId));
  const respuesta = await fetch(`${BASE_URL}/admin/documentos`, {
    method: "POST",
    credentials: "include",
    body: formulario,
  });
  return parsearOLanzar(respuesta, "No se pudo subir el documento");
}

export async function reemplazarDocumento(
  id: string,
  datos: { archivo?: File; titulo?: string },
): Promise<DocumentoOrganismo> {
  const formulario = new FormData();
  if (datos.archivo) formulario.append("archivo", datos.archivo);
  if (datos.titulo) formulario.append("titulo", datos.titulo);
  const respuesta = await fetch(`${BASE_URL}/admin/documentos/${id}`, {
    method: "PUT",
    credentials: "include",
    body: formulario,
  });
  return parsearOLanzar(respuesta, "No se pudo actualizar el documento");
}

export async function borrarDocumento(id: string): Promise<void> {
  const respuesta = await fetch(`${BASE_URL}/admin/documentos/${id}`, {
    method: "DELETE",
    credentials: "include",
  });
  if (!respuesta.ok) {
    const cuerpo = await respuesta.json().catch(() => null);
    throw new Error(typeof cuerpo?.detail === "string" ? cuerpo.detail : "No se pudo borrar el documento");
  }
}
