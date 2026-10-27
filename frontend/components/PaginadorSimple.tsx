export function PaginadorSimple({
  pagina,
  totalPaginas,
  onCambiar,
}: {
  pagina: number;
  totalPaginas: number;
  onCambiar: (pagina: number) => void;
}) {
  return (
    <div className="mt-4 flex items-center gap-4 text-sm">
      <button onClick={() => onCambiar(pagina - 1)} disabled={pagina <= 1} className="boton-secundario">
        Anterior
      </button>
      <span>
        Página {pagina} de {totalPaginas}
      </span>
      <button onClick={() => onCambiar(pagina + 1)} disabled={pagina >= totalPaginas} className="boton-secundario">
        Siguiente
      </button>
    </div>
  );
}
