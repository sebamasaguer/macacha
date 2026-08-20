"use client";

import { useState } from "react";
import { ChatInput } from "../components/ChatInput";
import { ChatMessage } from "../components/ChatMessage";
import { ContactoHumanoModal } from "../components/ContactoHumanoModal";
import { HeaderInstitucional } from "../components/HeaderInstitucional";
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

type Tab = "chat" | "info";

function Chat({ sessionId }: { sessionId: string }) {
  const { mensajes, enviando, enviarMensaje } = useChatStream(sessionId);
  const vista = usePanelTramite(mensajes);
  const [tab, setTab] = useState<Tab>("chat");
  const [modalContactoAbierto, setModalContactoAbierto] = useState(false);

  function preguntarSobre(mensaje: string) {
    enviarMensaje(mensaje);
    setTab("chat");
  }

  return (
    <div className="fondo-degrade-chat flex h-screen flex-col">
      <HeaderInstitucional
        subtitulo="Asistente virtual de trámites — Gobierno de Salta"
        linkContacto={{
          texto: "¿Hablar con una persona?",
          onClick: () => setModalContactoAbierto(true),
        }}
      />
      <div className="mx-auto flex w-full max-w-6xl flex-1 flex-col overflow-hidden md:flex-row">
        <nav className="flex border-b border-gray-200 dark:border-white/10 md:hidden">
          <TabButton activo={tab === "chat"} onClick={() => setTab("chat")}>
            Chat
          </TabButton>
          <TabButton activo={tab === "info"} onClick={() => setTab("info")}>
            Info del trámite
          </TabButton>
        </nav>

        <main
          className={`min-w-0 flex-1 flex-col ${tab === "chat" ? "flex" : "hidden"} md:flex`}
        >
          <div className="flex-1 space-y-3 overflow-y-auto p-4">
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
        </main>

        <aside
          className={`w-full flex-1 overflow-y-auto border-gray-200 p-4 dark:border-white/10 md:block md:flex-none md:w-72 md:border-l ${
            tab === "info" ? "block" : "hidden"
          }`}
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
        </aside>

        {modalContactoAbierto && (
          <ContactoHumanoModal
            sessionId={sessionId}
            mensajes={mensajes}
            onCerrar={() => setModalContactoAbierto(false)}
          />
        )}
      </div>
    </div>
  );
}

function TabButton({
  activo,
  onClick,
  children,
}: {
  activo: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      className={`flex-1 p-3 text-sm font-medium ${
        activo
          ? "border-b-2 border-macacha-blue text-macacha-blue"
          : "text-gray-500 dark:text-gray-400"
      }`}
      onClick={onClick}
    >
      {children}
    </button>
  );
}
