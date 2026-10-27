import { describe, expect, it } from "vitest";
import type { CampoFormulario, FormularioEntrada } from "./admin-formularios-api";
import {
  campoNuevo,
  inputFechaAIso,
  isoAInputFecha,
  nombreArchivoCsv,
  opcionesDeTexto,
  puedeCambiarTipo,
  puedeQuitarCampo,
  puedeSerObligatorio,
  textoCupo,
  textoDeOpciones,
  textoEstado,
  validarEntrada,
  valorLegible,
} from "./formularios-ui";

const campo = (cambios: Partial<CampoFormulario> = {}): CampoFormulario => ({
  etiqueta: "Nombre",
  tipo: "texto",
  obligatorio: true,
  opciones: null,
  ...cambios,
});

const entrada = (cambios: Partial<FormularioEntrada> = {}): FormularioEntrada => ({
  organismo_id: 1,
  nombre: "Inscripción a la capacitación",
  descripcion_uso: "",
  aviso_finalidad: "",
  tramite_id: null,
  estado: "activo",
  fecha_cierre: null,
  cupo: null,
  campos: [campo()],
  ...cambios,
});

describe("textos de estado y cupo", () => {
  it("traduce el estado efectivo", () => {
    expect(textoEstado("abierto")).toBe("Abierto");
    expect(textoEstado("borrador")).toBe("Borrador");
    expect(textoEstado("cerrado")).toBe("Cerrado");
    expect(textoEstado("vencido")).toBe("Cerrado por fecha");
    expect(textoEstado("cupo_completo")).toBe("Cupo completo");
  });

  it("muestra las respuestas sobre el cupo cuando hay cupo", () => {
    expect(textoCupo(12, 40)).toBe("12 de 40");
    expect(textoCupo(12, null)).toBe("12");
  });
});

describe("reglas de edición según haya respuestas", () => {
  const existente = campo({ clave: "dni" });
  const nuevo = campo();

  it("sin respuestas todo se puede cambiar", () => {
    expect(puedeQuitarCampo(existente, false)).toBe(true);
    expect(puedeCambiarTipo(existente, false)).toBe(true);
    expect(puedeSerObligatorio(nuevo, false)).toBe(true);
  });

  it("con respuestas los campos existentes no se quitan ni cambian de tipo", () => {
    expect(puedeQuitarCampo(existente, true)).toBe(false);
    expect(puedeCambiarTipo(existente, true)).toBe(false);
  });

  it("con respuestas un campo nuevo se puede quitar pero tiene que ser opcional", () => {
    expect(puedeQuitarCampo(nuevo, true)).toBe(true);
    expect(puedeSerObligatorio(nuevo, true)).toBe(false);
    expect(puedeSerObligatorio(existente, true)).toBe(true);
  });

  it("un campo nuevo arranca como texto obligatorio y sin clave", () => {
    expect(campoNuevo()).toEqual({ etiqueta: "", tipo: "texto", obligatorio: true, opciones: null });
  });
});

describe("opciones de una lista", () => {
  it("separa por línea, recorta y descarta las vacías", () => {
    expect(opcionesDeTexto(" Mañana \n\nTarde\n  ")).toEqual(["Mañana", "Tarde"]);
  });

  it("vuelve a armar el texto", () => {
    expect(textoDeOpciones(["Mañana", "Tarde"])).toBe("Mañana\nTarde");
    expect(textoDeOpciones(null)).toBe("");
  });
});

describe("validarEntrada", () => {
  it("acepta un formulario correcto", () => {
    expect(validarEntrada(entrada())).toBeNull();
  });

  it("pide un nombre", () => {
    expect(validarEntrada(entrada({ nombre: "   " }))).toMatch(/nombre/i);
  });

  it("pide al menos un campo y una etiqueta en cada uno", () => {
    expect(validarEntrada(entrada({ campos: [] }))).toMatch(/campo/i);
    expect(validarEntrada(entrada({ campos: [campo({ etiqueta: " " })] }))).toMatch(/etiqueta|pregunta/i);
  });

  it("admite como máximo 30 campos y un solo DNI", () => {
    expect(validarEntrada(entrada({ campos: Array.from({ length: 31 }, () => campo()) }))).toMatch(/30/);
    expect(validarEntrada(entrada({ campos: [campo({ tipo: "dni" }), campo({ tipo: "dni", etiqueta: "Otro" })] }))).toMatch(/DNI/);
  });

  it("una lista necesita entre 2 y 20 opciones distintas", () => {
    const lista = (opciones: string[]) => entrada({ campos: [campo({ tipo: "opcion", opciones })] });
    expect(validarEntrada(lista(["Una"]))).toMatch(/opciones/i);
    expect(validarEntrada(lista(["A", "a"]))).toMatch(/opciones/i);
    expect(validarEntrada(lista(Array.from({ length: 21 }, (_, i) => `o${i}`)))).toMatch(/opciones/i);
    expect(validarEntrada(lista(["Mañana", "Tarde"]))).toBeNull();
  });

  it("el cupo tiene que ser un entero positivo", () => {
    expect(validarEntrada(entrada({ cupo: 0 }))).toMatch(/cupo/i);
    expect(validarEntrada(entrada({ cupo: 2.5 }))).toMatch(/cupo/i);
    expect(validarEntrada(entrada({ cupo: 40 }))).toBeNull();
  });

  it("con respuestas, un campo nuevo obligatorio se rechaza", () => {
    const f = entrada({ campos: [campo({ clave: "nombre" }), campo({ etiqueta: "Nuevo", obligatorio: true })] });
    expect(validarEntrada(f, true)).toMatch(/opcional/i);
    expect(validarEntrada(f, false)).toBeNull();
  });
});

describe("valorLegible", () => {
  it("formatea sí/no, fecha y vacíos", () => {
    expect(valorLegible(campo({ tipo: "si_no" }), true)).toBe("Sí");
    expect(valorLegible(campo({ tipo: "si_no" }), false)).toBe("No");
    expect(valorLegible(campo({ tipo: "fecha" }), "1990-12-25")).toBe("25/12/1990");
    expect(valorLegible(campo(), undefined)).toBe("");
    expect(valorLegible(campo({ tipo: "numero" }), 12)).toBe("12");
  });
});

describe("nombreArchivoCsv", () => {
  it("arma un nombre sin acentos ni símbolos", () => {
    expect(nombreArchivoCsv("Inscripción a la capacitación")).toBe("inscripcion-a-la-capacitacion-respuestas.csv");
    expect(nombreArchivoCsv("???")).toBe("formulario-respuestas.csv");
  });
});

describe("fechas del campo datetime-local", () => {
  it("convierte ida y vuelta sin cambiar la hora local", () => {
    const iso = inputFechaAIso("2026-10-30T18:00");
    expect(iso).not.toBeNull();
    expect(isoAInputFecha(iso)).toBe("2026-10-30T18:00");
  });

  it("maneja vacío", () => {
    expect(inputFechaAIso("")).toBeNull();
    expect(isoAInputFecha(null)).toBe("");
  });
});
