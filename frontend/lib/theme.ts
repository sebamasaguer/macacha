export type Tema = "light" | "dark";

export function resolverTemaInicial(
  temaGuardado: string | null,
  prefiereOscuroDelSistema: boolean
): Tema {
  if (temaGuardado === "light" || temaGuardado === "dark") {
    return temaGuardado;
  }
  return prefiereOscuroDelSistema ? "dark" : "light";
}
