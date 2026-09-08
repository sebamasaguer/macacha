"use client";

import type { Faq } from "../lib/admin-tramites-api";

export function ListaFAQ({
  valores,
  onChange,
}: {
  valores: Faq[];
  onChange: (valores: Faq[]) => void;
}) {
  function actualizar(indice: number, campo: keyof Faq, valor: string) {
    const nuevos = [...valores];
    nuevos[indice] = { ...nuevos[indice], [campo]: valor };
    onChange(nuevos);
  }

  function agregar() {
    onChange([...valores, { pregunta: "", respuesta: "" }]);
  }

  function quitar(indice: number) {
    onChange(valores.filter((_, i) => i !== indice));
  }

  return (
    <div>
      <label className="campo-label">Preguntas frecuentes</label>
      <div className="space-y-3">
        {valores.map((faq, indice) => (
          <div key={indice} className="tarjeta space-y-1 p-2">
            <input
              type="text"
              placeholder="Pregunta"
              value={faq.pregunta}
              onChange={(e) => actualizar(indice, "pregunta", e.target.value)}
              className="campo-input w-full"
            />
            <input
              type="text"
              placeholder="Respuesta"
              value={faq.respuesta}
              onChange={(e) => actualizar(indice, "respuesta", e.target.value)}
              className="campo-input w-full"
            />
            <button type="button" onClick={() => quitar(indice)} className="text-sm texto-error">
              Quitar
            </button>
          </div>
        ))}
      </div>
      <button type="button" onClick={agregar} className="boton-secundario mt-2">
        + Agregar pregunta
      </button>
    </div>
  );
}
