"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { obtenerSesion, type MensajeAdmin } from "../../../../lib/admin-api";
import { ConversacionChat } from "../../../../components/ConversacionChat";

export default function SesionDetallePage() {
  const params = useParams<{ id: string }>();
  const [mensajes, setMensajes] = useState<MensajeAdmin[] | null | undefined>(undefined);
  const [error, setError] = useState(false);

  useEffect(() => {
    cargar();
  }, [params.id]);

  async function cargar() {
    setError(false);
    setMensajes(undefined);
    try {
      const resultado = await obtenerSesion(params.id);
      setMensajes(resultado);
    } catch {
      setError(true);
    }
  }

  if (error) {
    return (
      <div className="p-4">
        <p className="text-sm texto-error">No se pudo cargar la sesión</p>
        <button onClick={cargar} className="enlace-accion mt-2">
          Reintentar
        </button>
      </div>
    );
  }

  if (mensajes === undefined) {
    return <p className="p-4 text-sm texto-secundario">Cargando…</p>;
  }

  if (mensajes === null) {
    return (
      <div className="p-4">
        <p className="text-sm texto-secundario">Sesión no encontrada</p>
        <Link href="/admin/chats" className="enlace-accion">
          Volver a la lista
        </Link>
      </div>
    );
  }

  return (
    <div className="p-4">
      <ConversacionChat mensajes={mensajes} />
    </div>
  );
}
