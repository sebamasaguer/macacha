"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { PaginadorSimple } from "../../../components/PaginadorSimple";
import { useAdminActual } from "../../../hooks/useAdminActual";
import { listarFormularios, type PaginaFormularios } from "../../../lib/admin-formularios-api";
import { textoCupo, textoEstado } from "../../../lib/formularios-ui";

const POR_PAGINA = 10;

export default function FormulariosPage() {
  const admin = useAdminActual();
  const [datos, setDatos] = useState<PaginaFormularios | null>(null);
  const [pagina, setPagina] = useState(1);
  const [error, setError] = useState(false);
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    cargar();
  }, [pagina]);

  async function cargar() {
    setCargando(true);
    setError(false);
    try {
      setDatos(await listarFormularios(pagina, POR_PAGINA));
    } catch {
      setError(true);
    } finally {
      setCargando(false);
    }
  }

  if (cargando) return <p className="p-4 text-sm texto-secundario">Cargando…</p>;

  if (error) {
    return (
      <div className="p-4">
        <p className="text-sm texto-error">No se pudo cargar la lista de formularios</p>
        <button onClick={cargar} className="boton-secundario mt-2">
          Reintentar
        </button>
      </div>
    );
  }

  const totalPaginas = Math.max(1, Math.ceil((datos?.total ?? 0) / POR_PAGINA));

  return (
    <div className="p-4">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-lg font-semibold">Formularios</h1>
        {admin?.puede_crear_formularios && (
          <Link href="/admin/formularios/nuevo" className="boton-primario">
            Nuevo formulario
          </Link>
        )}
      </div>

      {datos?.total === 0 ? (
        <p className="text-sm texto-secundario">Todavía no hay formularios</p>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="tabla-cabecera">
              <th className="p-2">Nombre</th>
              <th className="p-2">Organismo</th>
              <th className="p-2">Estado</th>
              <th className="p-2">Respuestas</th>
              <th className="p-2">Fecha límite</th>
              <th className="p-2"></th>
            </tr>
          </thead>
          <tbody>
            {datos!.formularios.map((f) => (
              <tr key={f.id} className="tabla-fila">
                <td className="p-2">
                  <Link href={`/admin/formularios/${f.id}`} className="boton-secundario">
                    {f.nombre}
                  </Link>
                </td>
                <td className="p-2">{f.organismo}</td>
                <td className="p-2">{textoEstado(f.estado_efectivo)}</td>
                <td className="p-2">{textoCupo(f.respuestas, f.cupo)}</td>
                <td className="p-2">{f.fecha_cierre ? new Date(f.fecha_cierre).toLocaleString() : "—"}</td>
                <td className="p-2">
                  <Link href={`/admin/formularios/${f.id}/respuestas`} className="underline">
                    Ver respuestas
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {datos && datos.total > 0 && (
        <PaginadorSimple pagina={pagina} totalPaginas={totalPaginas} onCambiar={setPagina} />
      )}
    </div>
  );
}
