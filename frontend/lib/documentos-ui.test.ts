import { describe, expect, it } from "vitest";
import { MAX_BYTES, MAX_DOCUMENTOS, cuposLibres, tituloPorDefecto, validarArchivo } from "./documentos-ui";

describe("validarArchivo", () => {
  it("acepta pdf y docx en mayúsculas o minúsculas", () => {
    expect(validarArchivo("reglamento.pdf", 1000)).toBeNull();
    expect(validarArchivo("Reglamento.DOCX", 1000)).toBeNull();
  });

  it("rechaza txt y doc", () => {
    expect(validarArchivo("notas.txt", 1000)).toMatch(/PDF o Word/);
    expect(validarArchivo("viejo.doc", 1000)).toMatch(/PDF o Word/);
  });

  it("rechaza más de 10 MB", () => {
    expect(MAX_BYTES).toBe(10 * 1024 * 1024);
    expect(validarArchivo("grande.pdf", MAX_BYTES + 1)).toMatch(/10 MB/);
    expect(validarArchivo("justo.pdf", MAX_BYTES)).toBeNull();
  });

  it("rechaza un archivo vacío", () => {
    expect(validarArchivo("vacio.pdf", 0)).toMatch(/vacío/);
  });
});

describe("tituloPorDefecto", () => {
  it("quita la extensión y conserva tildes", () => {
    expect(tituloPorDefecto("Delegaciones del interior.docx")).toBe("Delegaciones del interior");
    expect(tituloPorDefecto("Reglamento Orán.v2.PDF")).toBe("Reglamento Orán.v2");
  });
});

describe("cuposLibres", () => {
  it("nunca devuelve negativos", () => {
    expect(MAX_DOCUMENTOS).toBe(3);
    expect(cuposLibres(0)).toBe(3);
    expect(cuposLibres(2)).toBe(1);
    expect(cuposLibres(5)).toBe(0);
  });
});
