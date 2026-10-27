"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ConversacionChat } from "../../../../../../components/ConversacionChat";
import { useAdminActual } from "../../../../../../hooks/useAdminActual";
import {
  borrarRespuesta,
  obtenerRespuesta,
  type RespuestaDetalle,
} from "../../../../../../lib/admin-formularios-api";
import { valorLegible } from "../../../../../../lib/formularios-ui";

export default function RespuestaDetallePage() {
  const params = useParams<{ id: string; rid: string }>();
  const router = useRouter();
  const admin = useAdminActual();
  const [respuesta, setRespuesta] = useState<RespuestaDetalle | null | undefined>(undefined);
  const [error, setError] = useState<string | null>(null);
  const [errorCarga, setErrorCarga] = useState(false);
  const [borrando, setBorrando] = useState(false);

  useEffect(() => {
    cargar();
  }, [params.id, params.rid]);

  async function cargar() {
    setErrorCarga(false);
    try {
      setRespuesta(await obtenerRespuesta(params.id, params.rid));
    } catch {
      setErrorCarga(true);
    }
  }

  async function handleBorrar() {
    if (!window.confirm("¿Borrar esta respuesta? Deja de contarse en el cupo y libera el DNI.")) return;
    setBorrando(true);
    setError(null);
    try {
      await borrarRespuesta(params.id, params.rid);
      router.push(`/admin/formularios/${params.id}/respuestas`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo borrar la respuesta");
      setBorrando(false);
    }
  }

  if (errorCarga) {
    return (
      <div className="p-4">
        <p className="text-sm texto-error">No se pudo cargar la respuesta</p>
        <button onClick={cargar} className="boton-secundario mt-2">
          Reintentar
        </button>
      </div>
    );
  }

  if (respuesta === undefined || !admin) return <p className="p-4 text-sm texto-secundario">Cargando…</p>;

  if (respuesta === null) {
    return (
      <div className="p-4">
        <p className="text-sm texto-secundario">Respuesta no encontrada</p>
        <Link href={`/admin/formularios/${params.id}/respuestas`} className="boton-secundario">
          Volver a las respuestas
        </Link>
      </div>
    );
  }

  return (
    <div className="p-4">
      <Link href={`/admin/formularios/${params.id}/respuestas`} className="text-sm underline">
        ← Respuestas de {respuesta.formulario.nombre}
      </Link>
      <div className="tarjeta mb-4 mt-2 max-w-2xl">
        <p className="mb-2 text-xs texto-secundario">{new Date(respuesta.creado_en).toLocaleString()}</p>
        {respuesta.campos.map((c) => (
          <p key={c.clave}>
            <span className="font-semibold">{c.etiqueta}:</span> {valorLegible(c, respuesta.valores[c.clave ?? ""]) || "—"}
          </p>
        ))}
        {admin.puede_crear_formularios && (
          <button onClick={handleBorrar} disabled={borrando} className="boton-neutro mt-3">
            Borrar respuesta
          </button>
        )}
        {error && <p className="mt-2 text-sm texto-error">{error}</p>}
      </div>

      <h2 className="mb-2 text-sm font-semibold texto-secundario">Conversación de origen</h2>
      <ConversacionChat mensajes={respuesta.mensajes} />
    </div>
  );
}
