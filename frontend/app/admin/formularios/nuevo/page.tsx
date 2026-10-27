"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { FormularioEditor } from "../../../../components/FormularioEditor";
import { useAdminActual } from "../../../../hooks/useAdminActual";
import { crearFormulario, type FormularioEntrada } from "../../../../lib/admin-formularios-api";
import {
  listarOrganismos,
  listarTramites,
  type Organismo,
  type TramiteResumen,
} from "../../../../lib/admin-tramites-api";
import { campoNuevo } from "../../../../lib/formularios-ui";

const INICIAL: FormularioEntrada = {
  organismo_id: null,
  nombre: "",
  descripcion_uso: "",
  aviso_finalidad: "",
  tramite_id: null,
  estado: "borrador",
  fecha_cierre: null,
  cupo: null,
  campos: [campoNuevo()],
};

export default function NuevoFormularioPage() {
  const router = useRouter();
  const admin = useAdminActual();
  const [organismos, setOrganismos] = useState<Organismo[]>([]);
  const [tramites, setTramites] = useState<TramiteResumen[]>([]);
  const [cargado, setCargado] = useState(false);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!admin) return;
    const tareas: Promise<unknown>[] = [listarTramites().then(setTramites).catch(() => setTramites([]))];
    if (admin.rol === "super_admin") tareas.push(listarOrganismos().then(setOrganismos).catch(() => setOrganismos([])));
    Promise.all(tareas).finally(() => setCargado(true));
  }, [admin]);

  async function handleGuardar(datos: FormularioEntrada) {
    setGuardando(true);
    setError(null);
    try {
      const { id } = await crearFormulario(datos);
      router.push(`/admin/formularios/${id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo crear el formulario");
      setGuardando(false);
    }
  }

  if (!admin || !cargado) return <p className="p-4 text-sm texto-secundario">Cargando…</p>;

  if (!admin.puede_crear_formularios) {
    return <p className="p-4 text-sm texto-secundario">No tenés permiso para crear formularios.</p>;
  }

  return (
    <div className="p-4">
      <h1 className="mb-4 text-lg font-semibold">Nuevo formulario</h1>
      <FormularioEditor
        valoresIniciales={INICIAL}
        organismos={admin.rol === "super_admin" ? organismos : null}
        nombreOrganismo={admin.organismo}
        tramites={tramites}
        hayRespuestas={false}
        soloLectura={false}
        guardando={guardando}
        error={error}
        onGuardar={handleGuardar}
        onCancelar={() => router.push("/admin/formularios")}
      />
    </div>
  );
}
