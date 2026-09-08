import { describe, expect, it } from "vitest";
import { resolverTemaInicial } from "./theme";

describe("resolverTemaInicial", () => {
  it("usa el tema guardado si es válido", () => {
    expect(resolverTemaInicial("dark", false)).toBe("dark");
    expect(resolverTemaInicial("light", true)).toBe("light");
  });

  it("ignora un valor guardado inválido y usa la preferencia del sistema", () => {
    expect(resolverTemaInicial("cualquier-cosa", true)).toBe("dark");
    expect(resolverTemaInicial(null, true)).toBe("dark");
  });

  it("usa light por defecto si no hay tema guardado ni preferencia del sistema", () => {
    expect(resolverTemaInicial(null, false)).toBe("light");
  });
});
