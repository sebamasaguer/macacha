"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { PaginadorSimple } from "../../../../../components/PaginadorSimple";
import {
  descargarCsv,
  listarRespuestas,
  obtenerFormulario,
  type PaginaRespuestas,
} from "../../../../../lib/admin-formularios-api";
import { nombreArchivoCsv, valorLegible } from "../../../../../lib/formularios-ui";

const POR_PAGINA = 20;

export default function RespuestasPage() {
  const params = useParams<{ id: string }>();
  const [nombre, setNombre] = useState("");
  const [datos, setDatos] = useState<PaginaRespuestas | null>(null);
  const [pagina, setPagina] = useState(1);
  const [error, setError] = useState(false);
  const [cargando, setCargando] = useState(true);
  const [errorCsv, setErrorCsv] = useState<string | null>(null);

  useEffect(() => {
    obtenerFormulario(params.id).then((f) => setNombre(f?.nombre ?? ""));
  }, [params.id]);

  useEffect(() => {
    cargar();
  }, [pagina, params.id]);

  async function cargar() {
    setCargando(true);
    setError(false);
    try {
      setDatos(await listarRespuestas(params.id, pagina, POR_PAGINA));
    } catch {
      setError(true);
    } finally {
      setCargando(false);
    }
  }

  async function handleExportar() {
    setErrorCsv(null);
    try {
      await descargarCsv(params.id, nombreArchivoCsv(nombre));
    } catch (err) {
      setErrorCsv(err instanceof Error ? err.message : "No se pudo exportar el CSV");
    }
  }

  if (cargando) return <p className="p-4 text-sm texto-secundario">Cargando…</p>;

  if (error || !datos) {
    return (
      <div className="p-4">
        <p className="text-sm texto-error">No se pudieron cargar las respuestas</p>
        <button onClick={cargar} className="boton-secundario mt-2">
          Reintentar
        </button>
      </div>
    );
  }

  const totalPaginas = Math.max(1, Math.ceil(datos.total / POR_PAGINA));

  return (
    <div className="p-4">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <div>
          <Link href={`/admin/formularios/${params.id}`} className="text-sm underline">
            ← {nombre || "Formulario"}
          </Link>
          <h1 className="text-lg font-semibold">Respuestas ({datos.total})</h1>
        </div>
        <button onClick={handleExportar} className="boton-primario">
          Exportar CSV
        </button>
      </div>
      {errorCsv && <p className="mb-2 text-sm texto-error">{errorCsv}</p>}

      {datos.total === 0 ? (
        <p className="text-sm texto-secundario">Todavía no hay respuestas</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="tabla-cabecera">
                <th className="p-2">Fecha</th>
                {datos.campos.map((c) => (
                  <th key={c.clave} className="p-2">
                    {c.etiqueta}
                  </th>
                ))}
                <th className="p-2"></th>
              </tr>
            </thead>
            <tbody>
              {datos.respuestas.map((r) => (
                <tr key={r.id} className="tabla-fila">
                  <td className="p-2">{new Date(r.creado_en).toLocaleString()}</td>
                  {datos.campos.map((c) => (
                    <td key={c.clave} className="p-2">
                      {valorLegible(c, r.valores[c.clave ?? ""])}
                    </td>
                  ))}
                  <td className="p-2">
                    <Link href={`/admin/formularios/${params.id}/respuestas/${r.id}`} className="underline">
                      Ver
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {datos.total > 0 && <PaginadorSimple pagina={pagina} totalPaginas={totalPaginas} onCambiar={setPagina} />}
    </div>
  );
}
