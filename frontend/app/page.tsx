"use client";

import { useState } from "react";
import { ChatInput } from "../components/ChatInput";
import { ChatMessage } from "../components/ChatMessage";
import { ContactoHumanoModal } from "../components/ContactoHumanoModal";
import { PanelContextual } from "../components/PanelContextual";
import { PanelMarca } from "../components/PanelMarca";
import { TramiteInfoPanel } from "../components/TramiteInfoPanel";
import { TramitesAmbiguosPanel } from "../components/TramitesAmbiguosPanel";
import { TramitesFrecuentesPanel } from "../components/TramitesFrecuentesPanel";
import { useChatStream } from "../hooks/useChatStream";
import { usePanelTramite } from "../hooks/usePanelTramite";
import { useSession } from "../hooks/useSession";

export default function Home() {
  const { sessionId } = useSession();

  if (!sessionId) {
    return null;
  }

  return <Chat sessionId={sessionId} />;
}

function Chat({ sessionId }: { sessionId: string }) {
  const { mensajes, enviando, enviarMensaje } = useChatStream(sessionId);
  const vista = usePanelTramite(mensajes);
  const [panelAbierto, setPanelAbierto] = useState(false);
  const [modalContactoAbierto, setModalContactoAbierto] = useState(false);

  function preguntarSobre(mensaje: string) {
    enviarMensaje(mensaje);
    setPanelAbierto(false);
  }

  return (
    <div className="dark fondo-aurora-chat flex min-h-screen items-center justify-center p-3 md:p-6">
      <section className="flex h-[calc(100vh-24px)] w-full max-w-[1760px] overflow-hidden rounded-[30px] border border-white/15 bg-[rgba(13,18,54,0.68)] shadow-2xl backdrop-blur-2xl md:h-[calc(100vh-48px)]">
        <PanelMarca />

        <div className="flex min-w-0 flex-1 flex-col bg-black/20">
          <header className="flex min-h-[86px] flex-none items-center justify-between gap-4 border-b border-white/10 bg-white/[0.035] px-4 py-3 md:px-6">
            <div className="flex min-w-0 items-center gap-3">
              <img
                src="/branding/macacha-icon.png"
                alt=""
                className="h-10 w-10 flex-none object-contain"
              />
              <div className="min-w-0">
                <p className="text-base font-extrabold text-white">Macacha</p>
                <p className="truncate text-sm text-white/60">
                  Asistente virtual del Gobierno de Salta
                </p>
              </div>
            </div>
            <div className="flex flex-none items-center gap-2">
              <button
                type="button"
                onClick={() => setPanelAbierto(true)}
                className="boton-neutro min-[1051px]:hidden"
              >
                Ficha del trámite
              </button>
              <span className="inline-flex flex-none items-center gap-2 rounded-full border border-white/15 bg-white/10 px-3 py-1.5 text-xs font-bold text-white/85">
                <span className="h-2 w-2 rounded-full bg-emerald-400" />
                Activa
              </span>
            </div>
          </header>

          <div className="flex-1 space-y-3 overflow-y-auto p-5">
            {mensajes.map((mensaje, indice) => (
              <ChatMessage
                key={indice}
                mensaje={mensaje}
                onReintentar={
                  mensaje.error && !enviando
                    ? () => {
                        const anterior = mensajes[indice - 1];
                        if (anterior) enviarMensaje(anterior.contenido);
                      }
                    : undefined
                }
                onPedirContacto={() => setModalContactoAbierto(true)}
              />
            ))}
            {enviando && <p className="text-sm texto-secundario">escribiendo…</p>}
          </div>
          <ChatInput disabled={enviando} onEnviar={enviarMensaje} />
        </div>

        <PanelContextual
          abierto={panelAbierto}
          onCerrar={() => setPanelAbierto(false)}
          onAbrirContacto={() => setModalContactoAbierto(true)}
        >
          {vista.tipo === "tramite" && (
            <TramiteInfoPanel
              tramite={vista.tramite}
              onPreguntar={preguntarSobre}
              preguntarDeshabilitado={enviando}
            />
          )}
          {vista.tipo === "ambiguo" && (
            <TramitesAmbiguosPanel
              candidatos={vista.candidatos}
              onPreguntar={preguntarSobre}
              preguntarDeshabilitado={enviando}
            />
          )}
          {vista.tipo === "top3" && (
            <TramitesFrecuentesPanel
              tramites={vista.tramites}
              onPreguntar={preguntarSobre}
              preguntarDeshabilitado={enviando}
            />
          )}
          {vista.tipo === "cargando" && (
            <p className="text-sm texto-secundario">La info del trámite va a aparecer acá.</p>
          )}
        </PanelContextual>

        {modalContactoAbierto && (
          <ContactoHumanoModal
            sessionId={sessionId}
            mensajes={mensajes}
            onCerrar={() => setModalContactoAbierto(false)}
          />
        )}
      </section>
    </div>
  );
}
