"use client";

export function ListaTextos({
  etiqueta,
  valores,
  onChange,
}: {
  etiqueta: string;
  valores: string[];
  onChange: (valores: string[]) => void;
}) {
  function actualizar(indice: number, valor: string) {
    const nuevos = [...valores];
    nuevos[indice] = valor;
    onChange(nuevos);
  }

  function agregar() {
    onChange([...valores, ""]);
  }

  function quitar(indice: number) {
    onChange(valores.filter((_, i) => i !== indice));
  }

  return (
    <div>
      <label className="campo-label">{etiqueta}</label>
      <div className="space-y-2">
        {valores.map((valor, indice) => (
          <div key={indice} className="flex gap-2">
            <input
              type="text"
              value={valor}
              onChange={(e) => actualizar(indice, e.target.value)}
              className="campo-input flex-1"
            />
            <button type="button" onClick={() => quitar(indice)} className="text-sm texto-error">
              Quitar
            </button>
          </div>
        ))}
      </div>
      <button type="button" onClick={agregar} className="enlace-accion mt-2">
        + Agregar
      </button>
    </div>
  );
}
