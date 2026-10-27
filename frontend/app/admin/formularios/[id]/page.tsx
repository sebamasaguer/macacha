"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { FormularioEditor } from "../../../../components/FormularioEditor";
import { useAdminActual } from "../../../../hooks/useAdminActual";
import {
  editarFormulario,
  obtenerFormulario,
  type FormularioDetalle,
  type FormularioEntrada,
} from "../../../../lib/admin-formularios-api";
import { listarTramites, type TramiteResumen } from "../../../../lib/admin-tramites-api";
import { textoCupo, textoEstado } from "../../../../lib/formularios-ui";

function aEntrada(f: FormularioDetalle): FormularioEntrada {
  return {
    organismo_id: f.organismo_id,
    nombre: f.nombre,
    descripcion_uso: f.descripcion_uso,
    aviso_finalidad: f.aviso_finalidad,
    tramite_id: f.tramite_id,
    estado: f.estado,
    fecha_cierre: f.fecha_cierre,
    cupo: f.cupo,
    campos: f.campos,
  };
}

export default function FormularioDetallePage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const admin = useAdminActual();
  const [formulario, setFormulario] = useState<FormularioDetalle | null | undefined>(undefined);
  const [tramites, setTramites] = useState<TramiteResumen[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [errorCarga, setErrorCarga] = useState(false);
  const [guardando, setGuardando] = useState(false);
  const [guardado, setGuardado] = useState(false);

  useEffect(() => {
    cargar();
  }, [params.id]);

  async function cargar() {
    setErrorCarga(false);
    try {
      const [detalle, lista] = await Promise.all([
        obtenerFormulario(params.id),
        listarTramites().catch(() => [] as TramiteResumen[]),
      ]);
      setFormulario(detalle);
      setTramites(lista);
    } catch {
      setErrorCarga(true);
    }
  }

  async function handleGuardar(datos: FormularioEntrada) {
    setGuardando(true);
    setError(null);
    setGuardado(false);
    try {
      await editarFormulario(params.id, datos);
      setFormulario(await obtenerFormulario(params.id));
      setGuardado(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo guardar el formulario");
    } finally {
      setGuardando(false);
    }
  }

  if (errorCarga) {
    return (
      <div className="p-4">
        <p className="text-sm texto-error">No se pudo cargar el formulario</p>
        <button onClick={cargar} className="boton-secundario mt-2">
          Reintentar
        </button>
      </div>
    );
  }

  if (formulario === undefined || !admin) return <p className="p-4 text-sm texto-secundario">Cargando…</p>;

  if (formulario === null) {
    return (
      <div className="p-4">
        <p className="text-sm texto-secundario">Formulario no encontrado</p>
        <Link href="/admin/formularios" className="boton-secundario">
          Volver a la lista
        </Link>
      </div>
    );
  }

  return (
    <div className="p-4">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-lg font-semibold">{formulario.nombre}</h1>
          <p className="text-sm texto-secundario">
            {textoEstado(formulario.estado_efectivo)} · Respuestas: {textoCupo(formulario.respuestas, formulario.cupo)}
          </p>
        </div>
        <Link href={`/admin/formularios/${formulario.id}/respuestas`} className="boton-secundario">
          Ver respuestas ({formulario.respuestas})
        </Link>
      </div>
      {guardado && <p className="mb-2 text-sm text-emerald-600">Cambios guardados.</p>}
      <FormularioEditor
        key={formulario.actualizado_en}
        valoresIniciales={aEntrada(formulario)}
        organismos={null}
        nombreOrganismo={formulario.organismo}
        tramites={tramites}
        hayRespuestas={formulario.hay_respuestas}
        soloLectura={!admin.puede_crear_formularios}
        guardando={guardando}
        error={error}
        onGuardar={handleGuardar}
        onCancelar={() => router.push("/admin/formularios")}
      />
    </div>
  );
}
