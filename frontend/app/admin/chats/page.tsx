"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { obtenerSesiones, type ListaSesiones } from "../../../lib/admin-api";

export default function ChatsPage() {
  const [pagina, setPagina] = useState(1);
  const [datos, setDatos] = useState<ListaSesiones | null>(null);
  const [error, setError] = useState(false);
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    cargar();
  }, [pagina]);

  async function cargar() {
    setCargando(true);
    setError(false);
    try {
      const resultado = await obtenerSesiones(pagina, 20);
      setDatos(resultado);
    } catch {
      setError(true);
    } finally {
      setCargando(false);
    }
  }

  if (cargando) {
    return <p className="p-4 text-sm texto-secundario">Cargando…</p>;
  }

  if (error) {
    return (
      <div className="p-4">
        <p className="text-sm texto-error">No se pudo cargar la lista de chats</p>
        <button onClick={cargar} className="enlace-accion mt-2">
          Reintentar
        </button>
      </div>
    );
  }

  if (!datos || datos.total === 0) {
    return <p className="p-4 text-sm texto-secundario">Todavía no hay chats registrados</p>;
  }

  const totalPaginas = Math.ceil(datos.total / datos.page_size);

  return (
    <div className="p-4">
      <table className="w-full text-sm">
        <thead>
          <tr className="tabla-cabecera">
            <th className="p-2">Fecha</th>
            <th className="p-2">Mensajes</th>
            <th className="p-2">Último mensaje</th>
            <th className="p-2">Trámites citados</th>
          </tr>
        </thead>
        <tbody>
          {datos.sesiones.map((sesion) => (
            <tr key={sesion.id} className="tabla-fila">
              <td className="p-2">
                <Link
                  href={`/admin/chats/${sesion.id}`}
                  className="text-macacha-blue hover:underline dark:text-sky-300"
                >
                  {new Date(sesion.creado_en).toLocaleString("es-AR")}
                </Link>
              </td>
              <td className="p-2">{sesion.cantidad_mensajes}</td>
              <td className="p-2">{sesion.ultimo_mensaje ?? "—"}</td>
              <td className="p-2">
                {sesion.tramites_citados.map((id) => (
                  <span
                    key={id}
                    className="mr-1 rounded bg-gray-100 px-2 py-0.5 text-xs dark:bg-white/10"
                  >
                    {id}
                  </span>
                ))}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="mt-4 flex items-center gap-4 text-sm">
        <button
          onClick={() => setPagina((p) => p - 1)}
          disabled={pagina <= 1}
          className="text-macacha-blue underline disabled:text-gray-400 disabled:no-underline dark:text-sky-300 dark:disabled:text-gray-500"
        >
          Anterior
        </button>
        <span>
          Página {pagina} de {totalPaginas}
        </span>
        <button
          onClick={() => setPagina((p) => p + 1)}
          disabled={pagina >= totalPaginas}
          className="text-macacha-blue underline disabled:text-gray-400 disabled:no-underline dark:text-sky-300 dark:disabled:text-gray-500"
        >
          Siguiente
        </button>
      </div>
    </div>
  );
}
