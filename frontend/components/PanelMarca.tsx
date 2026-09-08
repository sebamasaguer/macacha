export function PanelMarca() {
  return (
    <aside className="hidden min-[1351px]:flex min-[1351px]:w-[300px] min-[1351px]:flex-none min-[1351px]:flex-col min-[1351px]:justify-between min-[1351px]:border-r min-[1351px]:border-white/10 min-[1351px]:bg-gradient-to-br min-[1351px]:from-white/[0.06] min-[1351px]:to-white/[0.015] min-[1351px]:p-10 min-[1351px]:text-white">
      <div>
        <img
          src="/branding/macacha-icon.png"
          alt="Símbolo de Macacha"
          className="h-[110px] w-[86px] object-contain drop-shadow-lg"
        />
        <div className="mt-7">
          <p className="mb-3 text-xs font-bold uppercase tracking-widest text-white/65">
            Gobierno de la Provincia de Salta
          </p>
          <h1 className="max-w-[240px] text-4xl font-medium leading-none tracking-tight text-white">
            Hola,
            <br />
            soy Macacha.
          </h1>
          <p className="mt-5 text-sm leading-relaxed text-white/75">
            Estoy para ayudarte a acceder a información, conocer trámites y encontrar los
            servicios que necesitás.
          </p>
          <div className="mt-8 flex items-center gap-2" aria-hidden="true">
            <span className="h-1.5 w-7 rounded-full bg-macacha-pink" />
            <span className="h-1.5 w-7 rounded-full bg-macacha-blue" />
            <span className="h-1.5 w-7 rounded-full bg-macacha-blueDark" />
            <span className="h-1.5 w-7 rounded-full border border-white/25 bg-macacha-navy" />
          </div>
        </div>
      </div>
      <p className="text-xs leading-relaxed text-white/50">
        Asistente virtual institucional · Información respaldada por fuentes documentales.
      </p>
    </aside>
  );
}
