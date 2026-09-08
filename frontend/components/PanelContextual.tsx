import type { ReactNode } from "react";

export function PanelContextual({
  abierto,
  onCerrar,
  onAbrirContacto,
  children,
}: {
  abierto: boolean;
  onCerrar: () => void;
  onAbrirContacto: () => void;
  children: ReactNode;
}) {
  return (
    <>
      {abierto && (
        <button
          type="button"
          onClick={onCerrar}
          aria-label="Cerrar ficha contextual"
          className="fixed inset-0 z-[89] bg-black/60 min-[1051px]:hidden"
        />
      )}
      <aside
        className={`fixed inset-y-0 right-0 z-[90] flex w-full max-w-[390px] flex-col overflow-hidden border-l border-white/10 bg-macacha-navy shadow-2xl transition-transform duration-200 min-[1051px]:static min-[1051px]:z-auto min-[1051px]:w-[370px] min-[1051px]:max-w-none min-[1051px]:flex-none min-[1051px]:translate-x-0 min-[1051px]:visible min-[1051px]:bg-transparent min-[1051px]:shadow-none ${
          abierto ? "translate-x-0" : "invisible translate-x-full"
        }`}
        aria-label="Información contextual del trámite"
      >
        <div className="flex-1 overflow-y-auto p-5">
          <div className="mb-4 flex items-start justify-between gap-3">
            <div>
              <p className="mb-1 text-xs font-extrabold uppercase tracking-widest text-sky-300">
                Panel contextual inteligente
              </p>
              <h2 className="text-lg font-semibold text-white">
                Información útil para resolver tu consulta
              </h2>
            </div>
            <button
              type="button"
              onClick={onCerrar}
              aria-label="Cerrar ficha"
              className="flex h-9 w-9 flex-none items-center justify-center rounded-xl border border-white/15 bg-white/10 text-lg text-white min-[1051px]:hidden"
            >
              ×
            </button>
          </div>
          {children}
        </div>
        <div className="flex-none border-t border-white/10 bg-black/20 p-4">
          <button type="button" onClick={onAbrirContacto} className="boton-primario w-full">
            Hablar con una persona
          </button>
        </div>
      </aside>
    </>
  );
}
