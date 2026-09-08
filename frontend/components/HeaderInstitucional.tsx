"use client";

import { useTema } from "../hooks/useTema";

export function HeaderInstitucional({
  subtitulo,
  linkContacto,
}: {
  subtitulo: string;
  linkContacto?: { texto: string; onClick: () => void };
}) {
  const { tema, alternar } = useTema();

  return (
    <header>
      <div className="flex items-center border-b border-gray-200 bg-white px-4 py-2 dark:border-white/10 dark:bg-transparent sm:px-6">
        <img
          src="/branding/logo-salta.svg"
          alt="Gobierno de Salta"
          className="h-8 w-auto dark:hidden"
        />
        <span className="hidden items-center rounded-md bg-white px-2.5 py-1 dark:inline-flex">
          <img src="/branding/logo-salta.svg" alt="Gobierno de Salta" className="h-6 w-auto" />
        </span>
      </div>
      <div className="flex items-center justify-between border-b-2 border-macacha-blue bg-white px-4 py-3 dark:border-white/10 dark:bg-transparent sm:px-6">
        <div className="flex items-center gap-3">
          <img
            src="/branding/macacha-icon.png"
            alt="Macacha"
            className="h-10 w-10 dark:drop-shadow-[0_0_12px_rgba(241,68,111,0.6)]"
          />
          <div>
            <p className="text-lg font-bold text-macacha-navy dark:text-white">Macacha</p>
            <p className="text-sm text-gray-600 dark:text-[#9fb3c0]">{subtitulo}</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          {linkContacto && (
            <button
              onClick={linkContacto.onClick}
              className="boton-secundario dark:shadow-[0_0_10px_rgba(0,120,201,0.6)]"
            >
              {linkContacto.texto}
            </button>
          )}
          <button
            onClick={alternar}
            aria-label={tema === "dark" ? "Cambiar a modo claro" : "Cambiar a modo oscuro"}
            className="rounded-full border border-gray-300 p-1.5 text-sm hover:bg-gray-100 dark:border-white/20 dark:hover:bg-white/10"
          >
            {tema === "dark" ? "☀️" : "🌙"}
          </button>
        </div>
      </div>
    </header>
  );
}
