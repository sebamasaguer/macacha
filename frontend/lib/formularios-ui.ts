import type {
  CampoFormulario,
  EstadoEfectivo,
  FormularioEntrada,
  TipoCampo,
} from "./admin-formularios-api";

export const ETIQUETAS_TIPO: Record<TipoCampo, string> = {
  texto: "Texto corto",
  texto_largo: "Texto largo",
  dni: "DNI",
  telefono: "Teléfono",
  email: "Email",
  numero: "Número",
  fecha: "Fecha",
  si_no: "Sí / No",
  opcion: "Lista de opciones",
};

export const TIPOS_CAMPO = Object.keys(ETIQUETAS_TIPO) as TipoCampo[];

const MAX_CAMPOS = 30;
const MAX_OPCIONES = 20;

export function textoEstado(estado: EstadoEfectivo): string {
  switch (estado) {
    case "abierto":
      return "Abierto";
    case "borrador":
      return "Borrador";
    case "cerrado":
      return "Cerrado";
    case "vencido":
      return "Cerrado por fecha";
    case "cupo_completo":
      return "Cupo completo";
  }
}

export function textoCupo(respuestas: number, cupo: number | null): string {
  return cupo === null ? `${respuestas}` : `${respuestas} de ${cupo}`;
}

export function campoNuevo(): CampoFormulario {
  return { etiqueta: "", tipo: "texto", obligatorio: true, opciones: null };
}

// Un campo "existente" es el que ya tiene clave (viene del servidor); uno nuevo todavía no la tiene.
export function puedeQuitarCampo(campo: CampoFormulario, hayRespuestas: boolean): boolean {
  return !(hayRespuestas && campo.clave);
}

export function puedeCambiarTipo(campo: CampoFormulario, hayRespuestas: boolean): boolean {
  return !(hayRespuestas && campo.clave);
}

export function puedeSerObligatorio(campo: CampoFormulario, hayRespuestas: boolean): boolean {
  return !(hayRespuestas && !campo.clave);
}

export function opcionesDeTexto(texto: string): string[] {
  return texto
    .split("\n")
    .map((linea) => linea.trim())
    .filter((linea) => linea !== "");
}

export function textoDeOpciones(opciones: string[] | null): string {
  return (opciones ?? []).join("\n");
}

export function validarEntrada(entrada: FormularioEntrada, hayRespuestas = false): string | null {
  if (entrada.nombre.trim() === "") return "Poné un nombre al formulario.";
  if (entrada.campos.length === 0) return "El formulario necesita al menos un campo.";
  if (entrada.campos.length > MAX_CAMPOS) return `Un formulario admite hasta ${MAX_CAMPOS} campos.`;
  if (entrada.campos.filter((c) => c.tipo === "dni").length > 1) return "Un formulario admite un solo campo DNI.";
  for (const campo of entrada.campos) {
    if (campo.etiqueta.trim() === "") return "Cada campo necesita una pregunta o etiqueta.";
    if (campo.tipo === "opcion") {
      const opciones = (campo.opciones ?? []).map((o) => o.trim());
      const distintas = new Set(opciones.map((o) => o.toLowerCase()));
      if (opciones.length < 2 || opciones.length > MAX_OPCIONES || distintas.size !== opciones.length) {
        return `La lista «${campo.etiqueta}» necesita entre 2 y ${MAX_OPCIONES} opciones distintas.`;
      }
    }
    if (hayRespuestas && !campo.clave && campo.obligatorio) {
      return `El campo nuevo «${campo.etiqueta}» tiene que ser opcional porque el formulario ya tiene respuestas.`;
    }
  }
  if (entrada.cupo !== null && (!Number.isInteger(entrada.cupo) || entrada.cupo <= 0)) {
    return "El cupo tiene que ser un número entero mayor que cero.";
  }
  return null;
}

export function valorLegible(campo: CampoFormulario, valor: unknown): string {
  if (valor === undefined || valor === null) return "";
  if (campo.tipo === "si_no") return valor ? "Sí" : "No";
  if (campo.tipo === "fecha") {
    const partes = String(valor).split("-");
    return partes.length === 3 ? `${partes[2]}/${partes[1]}/${partes[0]}` : String(valor);
  }
  return String(valor);
}

export function nombreArchivoCsv(nombre: string): string {
  const base = nombre
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return `${base || "formulario"}-respuestas.csv`;
}

function dosDigitos(n: number): string {
  return String(n).padStart(2, "0");
}

// El input datetime-local trabaja en hora local sin zona; el servidor guarda un instante con zona.
export function isoAInputFecha(iso: string | null): string {
  if (!iso) return "";
  const f = new Date(iso);
  return `${f.getFullYear()}-${dosDigitos(f.getMonth() + 1)}-${dosDigitos(f.getDate())}T${dosDigitos(f.getHours())}:${dosDigitos(f.getMinutes())}`;
}

export function inputFechaAIso(valor: string): string | null {
  if (!valor) return null;
  const fecha = new Date(valor);
  return Number.isNaN(fecha.getTime()) ? null : fecha.toISOString();
}
