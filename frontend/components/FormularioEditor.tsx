"use client";

import { useState, type FormEvent } from "react";
import type { CampoFormulario, EstadoFormulario, FormularioEntrada, TipoCampo } from "../lib/admin-formularios-api";
import type { Organismo, TramiteResumen } from "../lib/admin-tramites-api";
import {
  ETIQUETAS_TIPO,
  TIPOS_CAMPO,
  campoNuevo,
  inputFechaAIso,
  isoAInputFecha,
  opcionesDeTexto,
  puedeCambiarTipo,
  puedeQuitarCampo,
  puedeSerObligatorio,
  textoDeOpciones,
  validarEntrada,
} from "../lib/formularios-ui";

// El texto de las opciones se edita como texto libre (una por línea) y se convierte al guardar.
type CampoEditable = CampoFormulario & { textoOpciones: string };

const ESTADOS: { valor: EstadoFormulario; etiqueta: string }[] = [
  { valor: "borrador", etiqueta: "Borrador (no se ofrece)" },
  { valor: "activo", etiqueta: "Activo (el asistente lo ofrece)" },
  { valor: "cerrado", etiqueta: "Cerrado" },
];

function aEditable(campo: CampoFormulario): CampoEditable {
  return { ...campo, textoOpciones: textoDeOpciones(campo.opciones) };
}

function aCampo({ textoOpciones, ...campo }: CampoEditable): CampoFormulario {
  return { ...campo, opciones: campo.tipo === "opcion" ? opcionesDeTexto(textoOpciones) : null };
}

export function FormularioEditor({
  valoresIniciales,
  organismos,
  nombreOrganismo,
  tramites,
  hayRespuestas,
  soloLectura,
  guardando,
  error,
  onGuardar,
  onCancelar,
}: {
  valoresIniciales: FormularioEntrada;
  organismos: Organismo[] | null;
  nombreOrganismo: string | null;
  tramites: TramiteResumen[];
  hayRespuestas: boolean;
  soloLectura: boolean;
  guardando: boolean;
  error: string | null;
  onGuardar: (datos: FormularioEntrada) => void;
  onCancelar: () => void;
}) {
  const { campos: camposIniciales, ...resto } = valoresIniciales;
  const [datos, setDatos] = useState(resto);
  const [campos, setCampos] = useState<CampoEditable[]>(camposIniciales.map(aEditable));
  const [errorLocal, setErrorLocal] = useState<string | null>(null);

  function actualizar<K extends keyof typeof datos>(clave: K, valor: (typeof datos)[K]) {
    setDatos((anterior) => ({ ...anterior, [clave]: valor }));
  }

  function actualizarCampo(indice: number, cambios: Partial<CampoEditable>) {
    setCampos((anteriores) => anteriores.map((c, i) => (i === indice ? { ...c, ...cambios } : c)));
  }

  function mover(indice: number, delta: number) {
    setCampos((anteriores) => {
      const destino = indice + delta;
      if (destino < 0 || destino >= anteriores.length) return anteriores;
      const copia = [...anteriores];
      [copia[indice], copia[destino]] = [copia[destino], copia[indice]];
      return copia;
    });
  }

  const nombreActual = organismos
    ? (organismos.find((o) => o.id === datos.organismo_id)?.nombre ?? null)
    : nombreOrganismo;
  const tramitesDelOrganismo = tramites.filter((t) => t.organismo === nombreActual);

  function handleSubmit(evento: FormEvent) {
    evento.preventDefault();
    const entrada: FormularioEntrada = { ...datos, campos: campos.map(aCampo) };
    const problema =
      organismos && entrada.organismo_id === null ? "Elegí el organismo." : validarEntrada(entrada, hayRespuestas);
    setErrorLocal(problema);
    if (!problema) onGuardar(entrada);
  }

  return (
    <form onSubmit={handleSubmit} className="max-w-3xl space-y-4">
      <fieldset disabled={soloLectura} className="tarjeta space-y-3">
        {organismos ? (
          <div>
            <label className="campo-label">Organismo</label>
            <select
              aria-label="Organismo del formulario"
              value={datos.organismo_id ?? ""}
              onChange={(e) => {
                actualizar("organismo_id", e.target.value ? Number(e.target.value) : null);
                actualizar("tramite_id", null);
              }}
              className="campo-input w-full"
            >
              <option value="">Elegir…</option>
              {organismos.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.nombre}
                </option>
              ))}
            </select>
          </div>
        ) : (
          nombreOrganismo && (
            <p className="text-sm texto-secundario">
              Organismo: <span className="font-semibold">{nombreOrganismo}</span>
            </p>
          )
        )}

        <div>
          <label className="campo-label">Nombre del formulario</label>
          <input
            aria-label="Nombre del formulario"
            value={datos.nombre}
            onChange={(e) => actualizar("nombre", e.target.value)}
            className="campo-input w-full"
          />
        </div>

        <div>
          <label className="campo-label">¿Cuándo tiene que ofrecerlo el asistente?</label>
          <textarea
            aria-label="Cuándo ofrecerlo"
            value={datos.descripcion_uso}
            onChange={(e) => actualizar("descripcion_uso", e.target.value)}
            rows={2}
            maxLength={500}
            placeholder="Ej.: Cuando la persona quiera inscribirse a la capacitación de la Subsecretaría de Trabajo"
            className="campo-input w-full"
          />
        </div>

        <div>
          <label className="campo-label">¿Para qué se usan los datos? (el asistente lo dice antes de pedirlos)</label>
          <textarea
            aria-label="Finalidad de los datos"
            value={datos.aviso_finalidad}
            onChange={(e) => actualizar("aviso_finalidad", e.target.value)}
            rows={2}
            maxLength={500}
            placeholder="Ej.: La Subsecretaría de Trabajo usa tus datos para inscribirte a la capacitación."
            className="campo-input w-full"
          />
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <label className="campo-label">Trámite vinculado (opcional)</label>
            <select
              aria-label="Trámite vinculado"
              value={datos.tramite_id ?? ""}
              onChange={(e) => actualizar("tramite_id", e.target.value || null)}
              className="campo-input w-full"
            >
              <option value="">Ninguno</option>
              {tramitesDelOrganismo.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.id} · {t.nombre_oficial}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="campo-label">Estado</label>
            <select
              aria-label="Estado del formulario"
              value={datos.estado}
              onChange={(e) => actualizar("estado", e.target.value as EstadoFormulario)}
              className="campo-input w-full"
            >
              {ESTADOS.map((e) => (
                <option key={e.valor} value={e.valor}>
                  {e.etiqueta}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="campo-label">Fecha límite (opcional)</label>
            <input
              type="datetime-local"
              aria-label="Fecha límite"
              value={isoAInputFecha(datos.fecha_cierre)}
              onChange={(e) => actualizar("fecha_cierre", inputFechaAIso(e.target.value))}
              className="campo-input w-full"
            />
          </div>
          <div>
            <label className="campo-label">Cupo máximo de respuestas (opcional)</label>
            <input
              type="number"
              min={1}
              aria-label="Cupo máximo"
              value={datos.cupo ?? ""}
              onChange={(e) => actualizar("cupo", e.target.value === "" ? null : Number(e.target.value))}
              className="campo-input w-full"
            />
          </div>
        </div>
      </fieldset>

      <fieldset disabled={soloLectura} className="space-y-3">
        <h2 className="text-sm font-semibold">Campos que pide el asistente</h2>
        {hayRespuestas && (
          <p className="text-xs texto-secundario">
            Este formulario ya tiene respuestas: no se pueden quitar ni cambiar de tipo los campos existentes, y los
            campos nuevos tienen que ser opcionales.
          </p>
        )}
        {campos.map((campo, i) => (
          <div key={campo.clave ?? `nuevo-${i}`} className="tarjeta space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <input
                aria-label={`Etiqueta del campo ${i + 1}`}
                value={campo.etiqueta}
                onChange={(e) => actualizarCampo(i, { etiqueta: e.target.value })}
                placeholder="Pregunta o etiqueta"
                className="campo-input min-w-[200px] flex-1"
              />
              <select
                aria-label={`Tipo del campo ${i + 1}`}
                value={campo.tipo}
                disabled={!puedeCambiarTipo(campo, hayRespuestas)}
                onChange={(e) => actualizarCampo(i, { tipo: e.target.value as TipoCampo })}
                className="campo-input"
              >
                {TIPOS_CAMPO.map((tipo) => (
                  <option key={tipo} value={tipo}>
                    {ETIQUETAS_TIPO[tipo]}
                  </option>
                ))}
              </select>
              <label className="flex items-center gap-1 text-sm">
                <input
                  type="checkbox"
                  aria-label={`Campo ${i + 1} obligatorio`}
                  checked={campo.obligatorio}
                  disabled={!puedeSerObligatorio(campo, hayRespuestas)}
                  onChange={(e) => actualizarCampo(i, { obligatorio: e.target.checked })}
                />
                Obligatorio
              </label>
              <button type="button" aria-label={`Subir campo ${i + 1}`} onClick={() => mover(i, -1)} className="boton-neutro">
                ↑
              </button>
              <button type="button" aria-label={`Bajar campo ${i + 1}`} onClick={() => mover(i, 1)} className="boton-neutro">
                ↓
              </button>
              <button
                type="button"
                aria-label={`Quitar campo ${i + 1}`}
                disabled={!puedeQuitarCampo(campo, hayRespuestas)}
                onClick={() => setCampos((anteriores) => anteriores.filter((_, k) => k !== i))}
                className="boton-neutro"
              >
                Quitar
              </button>
            </div>
            {campo.tipo === "opcion" && (
              <textarea
                aria-label={`Opciones del campo ${i + 1}`}
                value={campo.textoOpciones}
                onChange={(e) => actualizarCampo(i, { textoOpciones: e.target.value })}
                rows={3}
                placeholder="Una opción por línea"
                className="campo-input w-full"
              />
            )}
          </div>
        ))}
        <button
          type="button"
          onClick={() => setCampos((anteriores) => [...anteriores, aEditable({ ...campoNuevo(), obligatorio: !hayRespuestas })])}
          disabled={campos.length >= 30}
          className="boton-secundario"
        >
          Agregar campo
        </button>
      </fieldset>

      {(errorLocal || error) && <p className="text-sm texto-error">{errorLocal ?? error}</p>}

      <div className="flex gap-2">
        {!soloLectura && (
          <button type="submit" disabled={guardando} className="boton-primario">
            {guardando ? "Guardando…" : "Guardar"}
          </button>
        )}
        <button type="button" onClick={onCancelar} className="boton-neutro">
          {soloLectura ? "Volver" : "Cancelar"}
        </button>
      </div>
    </form>
  );
}
