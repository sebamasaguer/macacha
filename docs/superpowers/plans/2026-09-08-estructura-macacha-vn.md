# Reestructurar interfaz de macacha (estructura 1:1 con macacha-vn) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reestructurar el chat público (3 columnas, sin header, fondo oscuro fijo) y el panel
admin (sidebar reestilizado, sin header, sin dark mode) de `macacha` para que su estructura
coincida con la de `macacha-vn`, con la paleta de marca de `macacha`, sin tocar lógica funcional.

**Architecture:** El chat pasa a ser oscuro de forma fija y el admin claro de forma fija — ya no
hay un tema alternable por el usuario. Tailwind ya resuelve sus variantes `dark:` mirando si un
**ancestro en el DOM** tiene la clase `.dark` (no depende de dónde se aplique esa clase). En vez
de eliminar `darkMode: "class"` y reescribir cada componente (lo que el spec sugería), este plan
aplica `className="dark"` de forma **estática** solo en el contenedor raíz del chat — así los
componentes de chat (`BurbujaMensaje`, `ChatMessage`, `TramiteInfoPanel`, etc.) seguirán viendo
activadas sus variantes `dark:` ya implementadas (glow, glassmorphism) sin tocarlos, mientras que
el admin, que nunca tiene ese ancestro, nunca las activa. Esto es una desviación deliberada del
detalle técnico del spec (que pedía borrar `darkMode`) porque logra el mismo resultado visual con
mucho menos riesgo, reutilizando estilos ya construidos y probados. Lo único que se elimina de
verdad es el **mecanismo de toggle** (hook, persistencia, botón, script anti-flash), porque ya no
hay nada que alternar.

**Tech Stack:** Next.js 15 / React 19 / Tailwind CSS 3 (arbitrary breakpoints `min-[Npx]:`, sin
plugins nuevos).

**Spec:** `docs/superpowers/specs/2026-09-08-estructura-macacha-vn-design.md`

## Global Constraints

- Paleta de marca (ya en `tailwind.config.ts`, sin cambios): `macacha.pink #f1446f`,
  `macacha.blue #0078c9`, `macacha.blueDark #005aba`, `macacha.navy #1a2732`.
- `darkMode: "class"` de `tailwind.config.ts` **se mantiene** (ver nota de Architecture arriba)
  — no se toca ese archivo en este plan.
- El chat público es oscuro siempre: su contenedor raíz lleva `className="dark ..."` fijo, sin
  condicional ni toggle.
- El admin es claro siempre: ningún nodo bajo `/admin/*` lleva la clase `dark`.
- No se cambia ningún `href`, `onClick`, prop, ni lógica de ningún hook o componente existente
  (`useChatStream`, `usePanelTramite`, `useSession`, `useChecklist`, `useAdminActual`,
  `tramitesCitadosEnConversacion`, `enviarSolicitudContacto`, `extraerDetalleToolCalls`) — solo
  `className` y la estructura JSX mínima para el nuevo layout.
- Breakpoints tomados de `macacha-vn`: panel de marca visible desde 1351px
  (`min-[1351px]:flex`, oculto por defecto); panel contextual es drawer fixed por debajo de
  1051px, parte del layout normal desde 1051px (`min-[1051px]:static` y variantes).
- Este repo solo escribe tests para funciones puras (`lib/*.ts`) — no se agrega testing de
  componentes en este plan. Al eliminar `lib/theme.ts` se elimina también su test.
- No se construye un dashboard `/admin` con KPIs ni las secciones de "Base RAG" — fuera de
  alcance (ver spec).

---

### Task 1: CSS del fondo del chat + quitar el script anti-flash de tema

**Files:**
- Modify: `frontend/app/globals.css`
- Modify: `frontend/app/layout.tsx`

**Interfaces:**
- Produces: clase de componente `.fondo-aurora-chat` (fondo del chat público), consumida por
  Task 4.

- [ ] **Step 1: Reemplazar `.fondo-degrade-chat` por `.fondo-aurora-chat` en `globals.css`**

En `frontend/app/globals.css`, dentro de `@layer components`, reemplazar:

```css
  .fondo-degrade-chat {
    background-color: #fafbfc;
  }
  .dark .fondo-degrade-chat {
    background: radial-gradient(ellipse at top right, #3a1a4a 0%, #1a1a3a 35%, #121b23 70%);
  }
```

por:

```css
  .fondo-aurora-chat {
    background:
      radial-gradient(circle at 12% 10%, rgba(241, 68, 111, 0.35) 0%, transparent 32%),
      radial-gradient(circle at 86% 82%, rgba(62, 35, 220, 0.42) 0%, transparent 38%),
      linear-gradient(135deg, #070b2a 0%, #26104f 48%, #10184a 100%);
  }
```

(Sin condicional `.dark` — esta clase se usa una sola vez, Task 4, en un contenedor que ya lleva
la clase `dark` de forma fija.)

- [ ] **Step 2: Quitar el script anti-flash de `app/layout.tsx`**

En `frontend/app/layout.tsx`, quitar la constante `SCRIPT_TEMA_INICIAL` y el `<head>` que la
inyecta. El archivo completo queda:

```tsx
import type { Metadata } from "next";
import { Montserrat } from "next/font/google";
import "./globals.css";

const montserrat = Montserrat({ subsets: ["latin"], variable: "--font-montserrat" });

export const metadata: Metadata = {
  title: "Macacha",
  description: "Asistente virtual de trámites de la Provincia de Salta",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="es" className={montserrat.variable} suppressHydrationWarning>
      <body>{children}</body>
    </html>
  );
}
```

(`suppressHydrationWarning` se conserva sin costo — ya no hace falta pero no molesta.)

- [ ] **Step 3: Verificar que el build de Tailwind no falla**

Run: `cd frontend && npx tailwindcss -i app/globals.css -o /tmp/tw-check.css && rm /tmp/tw-check.css`
Expected: termina sin error (código de salida 0).

- [ ] **Step 4: Commit**

```bash
git add frontend/app/globals.css frontend/app/layout.tsx
git commit -m "refactor: fondo aurora del chat como clase fija, quita script anti-flash de tema"
```

---

### Task 2: Componente `PanelMarca` (columna izquierda del chat)

**Files:**
- Create: `frontend/components/PanelMarca.tsx`

**Interfaces:**
- Produces: `PanelMarca()` — componente sin props, usado por Task 4.

- [ ] **Step 1: Crear el componente**

```tsx
export function PanelMarca() {
  return (
    <aside className="hidden min-[1351px]:flex min-[1351px]:w-[300px] min-[1351px]:flex-none min-[1351px]:flex-col min-[1351px]:justify-between min-[1351px]:border-r min-[1351px]:border-white/12 min-[1351px]:bg-gradient-to-br min-[1351px]:from-white/[0.06] min-[1351px]:to-white/[0.015] min-[1351px]:p-10 min-[1351px]:text-white">
      <div>
        <img
          src="/branding/macacha-icon.png"
          alt="Símbolo de Macacha"
          className="h-[110px] w-[86px] object-contain drop-shadow-lg"
        />
        <div className="mt-7">
          <p className="mb-3 text-xs font-bold uppercase tracking-widest text-white/65">
            Gobierno de la Provincia de Salta
          </p>
          <h1 className="max-w-[240px] text-4xl font-medium leading-none tracking-tight text-white">
            Hola,
            <br />
            soy Macacha.
          </h1>
          <p className="mt-5 text-sm leading-relaxed text-white/75">
            Estoy para ayudarte a acceder a información, conocer trámites y encontrar los
            servicios que necesitás.
          </p>
          <div className="mt-8 flex items-center gap-2" aria-hidden="true">
            <span className="h-1.5 w-7 rounded-full bg-macacha-pink" />
            <span className="h-1.5 w-7 rounded-full bg-macacha-blue" />
            <span className="h-1.5 w-7 rounded-full bg-macacha-blueDark" />
            <span className="h-1.5 w-7 rounded-full border border-white/25 bg-macacha-navy" />
          </div>
        </div>
      </div>
      <p className="text-xs leading-relaxed text-white/50">
        Asistente virtual institucional · Información respaldada por fuentes documentales.
      </p>
    </aside>
  );
}
```

- [ ] **Step 2: Verificar que compila**

Run: `cd frontend && npx tsc --noEmit`
Expected: sin errores (el componente no se usa todavía, pero debe tipar bien de forma aislada —
si el proyecto reporta "declared but never read" para el archivo entero, ignorarlo: TypeScript no
emite ese error para exports, solo para variables locales).

- [ ] **Step 3: Commit**

```bash
git add frontend/components/PanelMarca.tsx
git commit -m "feat: agrega PanelMarca (columna izquierda del chat)"
```

---

### Task 3: Componente `PanelContextual` (columna derecha del chat, con drawer mobile)

**Files:**
- Create: `frontend/components/PanelContextual.tsx`

**Interfaces:**
- Produces: `PanelContextual({ abierto, onCerrar, onAbrirContacto, children })` — envuelve
  cualquier contenido (los paneles de trámite existentes) con el título fijo, scroll interno y
  el footer de contacto; en mobile es un drawer que se desliza desde la derecha. Usado por
  Task 4.
- Consumes: nada de tareas anteriores (es un wrapper visual puro).

- [ ] **Step 1: Crear el componente**

```tsx
import type { ReactNode } from "react";

export function PanelContextual({
  abierto,
  onCerrar,
  onAbrirContacto,
  children,
}: {
  abierto: boolean;
  onCerrar: () => void;
  onAbrirContacto: () => void;
  children: ReactNode;
}) {
  return (
    <>
      {abierto && (
        <button
          type="button"
          onClick={onCerrar}
          aria-label="Cerrar ficha contextual"
          className="fixed inset-0 z-[89] bg-black/60 min-[1051px]:hidden"
        />
      )}
      <aside
        className={`fixed inset-y-0 right-0 z-[90] flex w-full max-w-[390px] flex-col overflow-hidden border-l border-white/11 bg-macacha-navy shadow-2xl transition-transform duration-200 min-[1051px]:static min-[1051px]:z-auto min-[1051px]:w-[370px] min-[1051px]:max-w-none min-[1051px]:flex-none min-[1051px]:translate-x-0 min-[1051px]:bg-transparent min-[1051px]:shadow-none ${
          abierto ? "translate-x-0" : "translate-x-full"
        }`}
        aria-label="Información contextual del trámite"
      >
        <div className="flex-1 overflow-y-auto p-5">
          <div className="mb-4 flex items-start justify-between gap-3">
            <div>
              <p className="mb-1 text-xs font-extrabold uppercase tracking-widest text-sky-300">
                Panel contextual inteligente
              </p>
              <h2 className="text-lg font-semibold text-white">
                Información útil para resolver tu consulta
              </h2>
            </div>
            <button
              type="button"
              onClick={onCerrar}
              aria-label="Cerrar ficha"
              className="flex h-9 w-9 flex-none items-center justify-center rounded-xl border border-white/16 bg-white/10 text-lg text-white min-[1051px]:hidden"
            >
              ×
            </button>
          </div>
          {children}
        </div>
        <div className="flex-none border-t border-white/11 bg-black/20 p-4">
          <button type="button" onClick={onAbrirContacto} className="boton-primario w-full">
            Hablar con una persona
          </button>
        </div>
      </aside>
    </>
  );
}
```

- [ ] **Step 2: Verificar que compila**

Run: `cd frontend && npx tsc --noEmit`
Expected: sin errores.

- [ ] **Step 3: Commit**

```bash
git add frontend/components/PanelContextual.tsx
git commit -m "feat: agrega PanelContextual (columna derecha del chat, drawer en mobile)"
```

---

### Task 4: Reescribir `app/page.tsx` con la estructura de 3 columnas

**Files:**
- Modify: `frontend/app/page.tsx`

**Interfaces:**
- Consumes: `PanelMarca()` (Task 2), `PanelContextual({abierto, onCerrar, onAbrirContacto,
  children})` (Task 3), clase `.fondo-aurora-chat` (Task 1). `TramiteInfoPanel`,
  `TramitesAmbiguosPanel`, `TramitesFrecuentesPanel`, `ChatMessage`, `ChatInput`,
  `ContactoHumanoModal`, `useChatStream`, `usePanelTramite`, `useSession` sin cambios de firma.
- Produces: nada (es la página raíz).

- [ ] **Step 1: Reescribir el archivo completo**

```tsx
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
              <span className="inline-flex flex-none items-center gap-2 rounded-full border border-white/16 bg-white/10 px-3 py-1.5 text-xs font-bold text-white/85">
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
```

Nota: `vista.tipo === "tramite"` / `"ambiguo"` / `"top3"` / `"cargando"` son los mismos
discriminantes que ya devuelve `usePanelTramite` hoy (sin cambios en ese hook).

- [ ] **Step 2: Verificar que compila y tipa**

Run: `cd frontend && npx tsc --noEmit`
Expected: sin errores.

- [ ] **Step 3: Verificar el build de producción**

Run: `cd frontend && npm run build`
Expected: `✓ Compiled successfully`, sin errores de tipos ni de lint.

- [ ] **Step 4: Commit**

```bash
git add frontend/app/page.tsx
git commit -m "feat: reestructura el chat público en 3 columnas (marca / conversación / contextual)"
```

---

### Task 5: Reestilizar el sidebar del admin y quitar el header

**Files:**
- Modify: `frontend/app/admin/layout.tsx`

**Interfaces:**
- Consumes: `logout()` de `lib/admin-api`, `AdminAuthProvider`/`useAdminActual` de
  `hooks/useAdminActual` — sin cambios de firma. Deja de consumir `HeaderInstitucional`.

- [ ] **Step 1: Reescribir el archivo completo**

```tsx
"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { logout } from "../../lib/admin-api";
import { AdminAuthProvider, useAdminActual } from "../../hooks/useAdminActual";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <AdminAuthProvider>
      <AdminLayoutInner>{children}</AdminLayoutInner>
    </AdminAuthProvider>
  );
}

function AdminLayoutInner({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const admin = useAdminActual();

  if (pathname === "/admin/login") {
    return <>{children}</>;
  }

  async function handleLogout() {
    await logout();
    router.push("/admin/login");
  }

  return (
    <div className="flex h-screen bg-gray-50 text-gray-900">
      <nav className="flex w-60 flex-none flex-col border-r border-gray-200 bg-white">
        <div className="flex items-center gap-3 border-b border-gray-200 px-4 py-4">
          <img
            src="/branding/macacha-icon.png"
            alt=""
            className="h-10 w-8 flex-none object-contain"
          />
          <div className="min-w-0">
            <p className="text-sm font-extrabold leading-tight">Macacha Admin</p>
            <p className="text-xs leading-tight text-gray-500">
              Gobierno de la Provincia de Salta
            </p>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-3 py-4">
          <p className="mb-2 px-2 text-xs font-extrabold uppercase tracking-widest text-gray-400">
            Operación
          </p>
          <ul className="space-y-1 text-sm">
            <li>
              <ItemNav href="/admin/chats" pathname={pathname} icono="◌">
                Chats
              </ItemNav>
            </li>
            <li>
              <ItemNav href="/admin/tramites" pathname={pathname} icono="✓">
                Trámites
              </ItemNav>
            </li>
            <li>
              <ItemNav href="/admin/contacto" pathname={pathname} icono="✦">
                Contacto
              </ItemNav>
            </li>
            {admin?.rol === "super_admin" && (
              <li>
                <ItemNav href="/admin/usuarios" pathname={pathname} icono="⚇">
                  Usuarios
                </ItemNav>
              </li>
            )}
          </ul>
        </div>

        <div className="grid gap-1 border-t border-gray-200 p-3">
          <Link
            href="/"
            className="flex min-h-[38px] items-center rounded-lg px-2.5 text-sm font-medium text-gray-500 hover:bg-gray-100 hover:text-gray-900"
          >
            Abrir chat
          </Link>
          <button
            onClick={handleLogout}
            className="flex min-h-[38px] items-center rounded-lg px-2.5 text-left text-sm font-medium text-gray-500 hover:bg-gray-100 hover:text-gray-900"
          >
            Cerrar sesión
          </button>
        </div>
      </nav>
      <main className="flex-1 overflow-y-auto">{children}</main>
    </div>
  );
}

function ItemNav({
  href,
  pathname,
  icono,
  children,
}: {
  href: string;
  pathname: string;
  icono: string;
  children: React.ReactNode;
}) {
  const activo = pathname.startsWith(href);
  return (
    <Link
      href={href}
      className={
        activo
          ? "flex min-h-[40px] items-center gap-2.5 rounded-lg bg-blue-50 px-2.5 font-semibold text-macacha-blueDark"
          : "flex min-h-[40px] items-center gap-2.5 rounded-lg px-2.5 text-gray-600 hover:bg-gray-50 hover:text-gray-900"
      }
    >
      <span className="w-5 text-center" aria-hidden="true">
        {icono}
      </span>
      {children}
    </Link>
  );
}
```

(El botón "Cerrar sesión" deja de usar la clase `boton-neutro` — en `macacha-vn` el pie del
sidebar es texto plano con hover sutil, no un botón con fondo. Es un cambio de piel visual, la
función `handleLogout` no cambia.)

- [ ] **Step 2: Verificar que compila y tipa**

Run: `cd frontend && npx tsc --noEmit`
Expected: sin errores.

- [ ] **Step 3: Commit**

```bash
git add frontend/app/admin/layout.tsx
git commit -m "refactor: sidebar admin reestilizado (agrupado, con logo), quita el header"
```

---

### Task 6: Cabecera con gradiente en el login del admin

**Files:**
- Modify: `frontend/app/admin/login/page.tsx`

**Interfaces:** ninguna — solo cambia el JSX de presentación; `handleSubmit`, `email`,
`password`, `error`, `enviando` no cambian.

- [ ] **Step 1: Reemplazar el `return` del componente**

En `frontend/app/admin/login/page.tsx`, reemplazar el bloque `return (...)` (desde
`<div className="flex h-screen items-center justify-center...`) por:

```tsx
  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 p-4">
      <div className="w-full max-w-sm overflow-hidden rounded-3xl border border-gray-200 bg-white shadow-xl">
        <div className="bg-gradient-to-br from-macacha-blueDark to-macacha-blue p-6 text-center text-white">
          <img src="/branding/macacha-icon.png" alt="Macacha" className="mx-auto h-12 w-12" />
          <h1 className="mt-3 text-lg font-semibold">Ingresar</h1>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4 p-6">
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="campo-input w-full"
            required
          />
          <input
            type="password"
            placeholder="Contraseña"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="campo-input w-full"
            required
          />
          {error && <p className="text-sm texto-error">Credenciales inválidas</p>}
          <button type="submit" disabled={enviando} className="boton-primario w-full">
            {enviando ? "Ingresando…" : "Ingresar"}
          </button>
        </form>
      </div>
    </div>
  );
```

- [ ] **Step 2: Verificar que compila y tipa**

Run: `cd frontend && npx tsc --noEmit`
Expected: sin errores.

- [ ] **Step 3: Commit**

```bash
git add frontend/app/admin/login/page.tsx
git commit -m "refactor: cabecera con gradiente en el login del admin"
```

---

### Task 7: Limpiar clases `dark:` residuales que ya no se activan nunca

**Files:**
- Modify: `frontend/components/ConversacionChat.tsx`
- Modify: `frontend/app/admin/chats/page.tsx`
- Modify: `frontend/app/admin/tramites/[id]/page.tsx`
- Modify: `frontend/app/admin/usuarios/page.tsx`

Estos cuatro archivos solo se renderizan dentro de `/admin/*`, que después de la Task 5 nunca
tiene un ancestro con la clase `dark`. Sus variantes `dark:` quedan inertes — se limpian para que
el código no sugiera un dark mode que ya no existe ahí.

- [ ] **Step 1: `ConversacionChat.tsx`**

En `frontend/components/ConversacionChat.tsx`, línea 17, cambiar:

```tsx
            <span className="mt-1 inline-block rounded bg-gray-200 px-1.5 py-0.5 text-xs text-gray-600 dark:bg-white/15 dark:text-gray-300">
```

por:

```tsx
            <span className="mt-1 inline-block rounded bg-gray-200 px-1.5 py-0.5 text-xs text-gray-600">
```

Línea 41, cambiar:

```tsx
    <div className="mt-2 border-t border-gray-300 pt-2 text-sm dark:border-white/20">
```

por:

```tsx
    <div className="mt-2 border-t border-gray-300 pt-2 text-sm">
```

Línea 48, cambiar:

```tsx
            <li key={item.id} className="rounded bg-white p-2 dark:bg-black/20">
```

por:

```tsx
            <li key={item.id} className="rounded bg-white p-2">
```

- [ ] **Step 2: `admin/chats/page.tsx`**

En `frontend/app/admin/chats/page.tsx`, línea 79, quitar ` dark:bg-white/10` de la clase (dejar
`"mr-1 rounded bg-gray-100 px-2 py-0.5 text-xs"`).

- [ ] **Step 3: `admin/tramites/[id]/page.tsx`**

En `frontend/app/admin/tramites/[id]/page.tsx`, línea 84, quitar ` dark:text-green-400` de la
clase (dejar `"p-4 pb-0 text-sm text-green-700"`).

- [ ] **Step 4: `admin/usuarios/page.tsx`**

En `frontend/app/admin/usuarios/page.tsx`, línea 131, quitar ` dark:bg-white/10
dark:hover:bg-white/20` de la clase (dejar `"rounded bg-gray-200 px-3 py-1.5 text-sm
hover:bg-gray-300"`).

- [ ] **Step 5: Verificar que no queda ningún `dark:` fuera del chat**

Run: `cd frontend && grep -rn "dark:" app/admin components/ConversacionChat.tsx`
Expected: sin resultados (el chat público — `app/page.tsx`, `components/ChatMessage.tsx`, etc. —
sí puede seguir teniendo `dark:`, ese grep no los incluye).

- [ ] **Step 6: Commit**

```bash
git add frontend/components/ConversacionChat.tsx frontend/app/admin/chats/page.tsx frontend/app/admin/tramites/\[id\]/page.tsx frontend/app/admin/usuarios/page.tsx
git commit -m "chore: limpia clases dark: inertes en el admin"
```

---

### Task 8: Eliminar el mecanismo de toggle de tema

**Files:**
- Delete: `frontend/components/HeaderInstitucional.tsx`
- Delete: `frontend/hooks/useTema.ts`
- Delete: `frontend/lib/theme.ts`
- Delete: `frontend/lib/theme.test.ts`

Ningún archivo del repo importa ya estos cuatro (Tasks 4, 5 y 6 reescribieron los tres
consumidores: `app/page.tsx`, `app/admin/layout.tsx`, `app/admin/login/page.tsx` no usaba
`HeaderInstitucional` directamente pero tampoco `useTema`).

- [ ] **Step 1: Confirmar que no queda ningún import**

Run: `cd frontend && grep -rn "HeaderInstitucional\|useTema\|lib/theme" app components hooks`
Expected: sin resultados.

- [ ] **Step 2: Eliminar los archivos**

```bash
cd frontend
git rm components/HeaderInstitucional.tsx hooks/useTema.ts lib/theme.ts lib/theme.test.ts
```

- [ ] **Step 3: Correr los tests de funciones puras**

Run: `cd frontend && npx vitest run`
Expected: todos los test files restantes pasan (ya no aparece `lib/theme.test.ts` en la lista).

- [ ] **Step 4: Commit**

```bash
git commit -m "chore: elimina el mecanismo de toggle de tema (ya no hay tema alternable)"
```

---

### Task 9: Verificación final — build, tests y comparación visual

**Files:** ninguno (solo verificación).

- [ ] **Step 1: Typecheck limpio**

Run: `cd frontend && npx tsc --noEmit`
Expected: sin errores.

- [ ] **Step 2: Build de producción limpio**

Run: `cd frontend && npm run build`
Expected: `✓ Compiled successfully`, todas las rutas listadas sin error.

- [ ] **Step 3: Tests de funciones puras**

Run: `cd frontend && npx vitest run`
Expected: todos pasan (mismo conteo que antes de este plan, menos los 3 tests de
`lib/theme.test.ts` que se eliminaron con ese archivo).

- [ ] **Step 4: Levantar la app y capturar el chat público**

Con el backend y el frontend corriendo (`cd backend && .venv/bin/uvicorn agent.api:app --port
8000` y `cd frontend && npm run dev`), usar el driver del skill `run-macacha`:

```bash
cd frontend
node ../.claude/skills/run-macacha/driver.mjs <<'EOF'
launch
nav http://localhost:3000
wait textarea
ss chat-3-columnas
console --errors
quit
EOF
```

Expected: captura en `/tmp/shots/chat-3-columnas.png` muestra fondo oscuro con gradiente aurora,
sin header separado arriba, panel contextual a la derecha con "Panel contextual inteligente" y
botón "Hablar con una persona" en el pie. Sin errores nuevos en consola (el 404 de favicon, si
aparece, es preexistente y no es de este plan).

- [ ] **Step 5: Capturar el admin y el login**

```bash
cd frontend
node ../.claude/skills/run-macacha/driver.mjs <<'EOF'
launch
nav http://localhost:3000/admin/login
wait input[type=email]
ss admin-login-gradiente
quit
EOF
```

Expected: card centrada con cabecera en gradiente azul, sin franja institucional arriba.

Para el sidebar del admin, como no hay credenciales de prueba conocidas, seguir el flujo de
"Testing the admin login flow" del skill `run-macacha` (crear un admin descartable, capturar,
borrarlo de la base inmediatamente):

```bash
cd backend
echo "<password-descartable>" | .venv/bin/python -m agent.admin.create_admin plan-verify@macacha.local
```

```bash
cd frontend
node ../.claude/skills/run-macacha/driver.mjs <<'EOF'
launch
nav http://localhost:3000/admin/login
wait input[type=email]
fill input[type=email] plan-verify@macacha.local
fill input[type=password] <password-descartable>
click-text Ingresar
wait-text Fecha
ss admin-sidebar-nuevo
quit
EOF
```

```bash
psql "$DATABASE_URL" -c "DELETE FROM admins WHERE email='plan-verify@macacha.local';"
```

Expected: sidebar izquierdo blanco con logo, "Macacha Admin", ítems agrupados bajo "Operación",
sin header arriba. El admin creado se borra de inmediato — no debe quedar en la base real.

- [ ] **Step 6: Reportar resultado**

No hay commit en este task (es solo verificación) — si algún paso falla, volver a la task
correspondiente y corregir antes de dar el plan por terminado.
