"use client";

import { useEffect, useState } from "react";
import { resolverTemaInicial, type Tema } from "../lib/theme";

const CLAVE_STORAGE = "macacha-theme";

export function useTema() {
  const [tema, setTema] = useState<Tema>("light");
  const [listo, setListo] = useState(false);

  useEffect(() => {
    const guardado = window.localStorage.getItem(CLAVE_STORAGE);
    const prefiereOscuro = window.matchMedia("(prefers-color-scheme: dark)").matches;
    setTema(resolverTemaInicial(guardado, prefiereOscuro));
    setListo(true);
  }, []);

  useEffect(() => {
    if (!listo) return;
    document.documentElement.classList.toggle("dark", tema === "dark");
    window.localStorage.setItem(CLAVE_STORAGE, tema);
  }, [tema, listo]);

  function alternar() {
    setTema((actual) => (actual === "dark" ? "light" : "dark"));
  }

  return { tema, alternar };
}
