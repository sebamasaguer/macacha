export function BurbujaMensaje({
  esUsuario,
  className = "",
  children,
}: {
  esUsuario: boolean;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <div className={`flex ${esUsuario ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] rounded-lg px-4 py-2 ${
          esUsuario
            ? "bg-gradient-to-br from-macacha-blue to-macacha-blueDark text-white dark:shadow-[0_0_20px_rgba(0,120,201,0.5)]"
            : "bg-gray-100 text-gray-900 dark:bg-white/10 dark:text-gray-100 dark:backdrop-blur-sm"
        } ${className}`}
      >
        {children}
      </div>
    </div>
  );
}
