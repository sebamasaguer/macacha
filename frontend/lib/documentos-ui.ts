export const MAX_DOCUMENTOS = 3;
export const MAX_BYTES = 10 * 1024 * 1024;

export function validarArchivo(nombre: string, bytes: number): string | null {
  const minuscula = nombre.toLowerCase();
  if (!minuscula.endsWith(".pdf") && !minuscula.endsWith(".docx")) {
    return "Solo se admiten archivos PDF o Word (.docx).";
  }
  if (bytes === 0) return "El archivo está vacío.";
  if (bytes > MAX_BYTES) return "El archivo supera el máximo de 10 MB.";
  return null;
}

export function tituloPorDefecto(nombreArchivo: string): string {
  return nombreArchivo.replace(/\.(pdf|docx)$/i, "").trim();
}

export function cuposLibres(cantidad: number): number {
  return Math.max(0, MAX_DOCUMENTOS - cantidad);
}
