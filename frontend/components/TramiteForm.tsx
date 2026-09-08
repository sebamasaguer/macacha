"use client";

import { useState, type FormEvent } from "react";
import { ListaFAQ } from "./ListaFAQ";
import { ListaTextos } from "./ListaTextos";
import type { Organismo, TramiteDetalleAdmin } from "../lib/admin-tramites-api";

export function TramiteForm({
  valoresIniciales,
  organismosExistentes,
  organismoFijo,
  guardando,
  error,
  onGuardar,
}: {
  valoresIniciales: TramiteDetalleAdmin;
  organismosExistentes: Organismo[];
  organismoFijo?: string;
  guardando: boolean;
  error: string | null;
  onGuardar: (datos: TramiteDetalleAdmin) => void;
}) {
  const [datos, setDatos] = useState<TramiteDetalleAdmin>(valoresIniciales);
  const [organismoEsNuevo, setOrganismoEsNuevo] = useState(
    !organismosExistentes.some((o) => o.nombre === valoresIniciales.organismo)
  );

  function actualizar<K extends keyof TramiteDetalleAdmin>(campo: K, valor: TramiteDetalleAdmin[K]) {
    setDatos((anterior) => ({ ...anterior, [campo]: valor }));
  }

  function handleSubmit(evento: FormEvent) {
    evento.preventDefault();
    onGuardar(organismoFijo ? { ...datos, organismo: organismoFijo } : datos);
  }

  const organismoEfectivo = organismoFijo ?? datos.organismo;
  const puedeGuardar = organismoEfectivo.trim() !== "" && datos.nombre_oficial.trim() !== "";

  return (
    <form onSubmit={handleSubmit} className="max-w-2xl space-y-4 p-4">
      <div>
        <label className="campo-label">Organismo</label>
        {organismoFijo ? (
          <input type="text" value={organismoFijo} disabled className="campo-input w-full" />
        ) : organismoEsNuevo ? (
          <input
            type="text"
            value={datos.organismo}
            onChange={(e) => actualizar("organismo", e.target.value)}
            className="campo-input w-full"
          />
        ) : (
          <select
            value={datos.organismo}
            onChange={(e) => actualizar("organismo", e.target.value)}
            className="campo-input w-full"
          >
            {organismosExistentes.map((organismo) => (
              <option key={organismo.id} value={organismo.nombre}>
                {organismo.nombre}
              </option>
            ))}
          </select>
        )}
        {!organismoFijo && (
          <button
            type="button"
            onClick={() => setOrganismoEsNuevo(!organismoEsNuevo)}
            className="boton-secundario mt-1"
          >
            {organismoEsNuevo ? "Elegir uno existente" : "Otro… (crear nuevo)"}
          </button>
        )}
      </div>

      <div>
        <label className="campo-label">Categoría</label>
        <input
          type="text"
          value={datos.categoria}
          onChange={(e) => actualizar("categoria", e.target.value)}
          className="campo-input w-full"
        />
      </div>

      <div>
        <label className="campo-label">Nombre oficial</label>
        <input
          type="text"
          value={datos.nombre_oficial}
          onChange={(e) => actualizar("nombre_oficial", e.target.value)}
          className="campo-input w-full"
        />
      </div>

      <div>
        <label className="campo-label">Descripción</label>
        <textarea
          value={datos.descripcion}
          onChange={(e) => actualizar("descripcion", e.target.value)}
          className="campo-input w-full"
        />
      </div>

      <div>
        <label className="campo-label">Objetivo</label>
        <textarea
          value={datos.objetivo}
          onChange={(e) => actualizar("objetivo", e.target.value)}
          className="campo-input w-full"
        />
      </div>

      <ListaTextos
        etiqueta="Requisitos"
        valores={datos.requisitos}
        onChange={(v) => actualizar("requisitos", v)}
      />
      <ListaTextos etiqueta="Pasos" valores={datos.pasos} onChange={(v) => actualizar("pasos", v)} />

      <div className="grid grid-cols-3 gap-2">
        <div>
          <label className="campo-label">Costo</label>
          <input
            type="text"
            value={datos.costo}
            onChange={(e) => actualizar("costo", e.target.value)}
            className="campo-input w-full"
          />
        </div>
        <div>
          <label className="campo-label">Modalidad</label>
          <input
            type="text"
            value={datos.modalidad}
            onChange={(e) => actualizar("modalidad", e.target.value)}
            className="campo-input w-full"
          />
        </div>
        <div>
          <label className="campo-label">Duración</label>
          <input
            type="text"
            value={datos.duracion}
            onChange={(e) => actualizar("duracion", e.target.value)}
            className="campo-input w-full"
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className="campo-label">Teléfono de contacto</label>
          <input
            type="text"
            value={datos.telefono_contacto}
            onChange={(e) => actualizar("telefono_contacto", e.target.value)}
            className="campo-input w-full"
          />
        </div>
        <div>
          <label className="campo-label">Email de contacto</label>
          <input
            type="text"
            value={datos.email_contacto}
            onChange={(e) => actualizar("email_contacto", e.target.value)}
            className="campo-input w-full"
          />
        </div>
      </div>

      <ListaTextos
        etiqueta="Problemas frecuentes"
        valores={datos.problemas_frecuentes}
        onChange={(v) => actualizar("problemas_frecuentes", v)}
      />
      <ListaTextos
        etiqueta="Sinónimos"
        valores={datos.sinonimos}
        onChange={(v) => actualizar("sinonimos", v)}
      />
      <ListaTextos
        etiqueta="Keywords"
        valores={datos.keywords}
        onChange={(v) => actualizar("keywords", v)}
      />
      <ListaTextos
        etiqueta="Enlaces oficiales"
        valores={datos.enlaces_oficiales}
        onChange={(v) => actualizar("enlaces_oficiales", v)}
      />
      <ListaFAQ
        valores={datos.preguntas_frecuentes}
        onChange={(v) => actualizar("preguntas_frecuentes", v)}
      />

      {error && <p className="text-sm texto-error">{error}</p>}

      <button type="submit" disabled={!puedeGuardar || guardando} className="boton-primario">
        {guardando ? "Guardando…" : "Guardar"}
      </button>
    </form>
  );
}
