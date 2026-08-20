# Identidad visual: marca Macacha + institucional Gobierno de Salta — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Aplicar la identidad de marca de Macacha (paleta, tipografía, logo) y el sello institucional del Gobierno de Salta a todo el frontend (chat público + panel admin), con soporte de modo claro/oscuro.

**Architecture:** Tokens de color en `tailwind.config.ts` (`darkMode: "class"`), tipografía Montserrat vía `next/font/google`, un componente `HeaderInstitucional` compartido entre el chat público y el admin, un hook `useTema` (persistido en `localStorage`) que aplica la clase `dark` a `<html>`, y un vocabulario de clases de componente reutilizables en `globals.css` (`@layer components`) para no repetir `dark:` variants en cada uno de los ~15 archivos que solo cambian su piel visual.

**Tech Stack:** Next.js 15 / React 19 / Tailwind CSS 3, sin dependencias nuevas.

## Global Constraints

- Paleta de marca (`tailwind.config.ts` → `theme.extend.colors.macacha`): `pink` `#f1446f`, `blue` `#0078c9`, `blueDark` `#005aba`, `navy` `#1a2732`. Valores exactos, no aproximar.
- `darkMode: "class"` — la clase `dark` se aplica a `<html>`, nunca a `<body>` ni a un wrapper interno.
- Tema persistido en `localStorage` bajo la clave `macacha-theme` (valores `"light"` o `"dark"`), con `prefers-color-scheme` como default solo la primera visita (sin valor guardado).
- El logo del Gobierno de Salta (`frontend/public/branding/logo-salta.svg`) no se recolorea ni se modifica — en modo oscuro va dentro de una placa blanca (`bg-white rounded-md`), nunca directamente sobre fondo oscuro.
- El header de dos franjas (institucional arriba, marca Macacha abajo) es el mismo componente (`HeaderInstitucional`) en el chat público y en el admin — no se duplica su implementación.
- El modo oscuro del **chat público** usa el gradiente tipo "aurora" (rosa-púrpura-azul-navy) con glow en burbujas de usuario e ícono. El modo oscuro del **admin** es sobrio: fondo `macacha.navy` liso, sin gradiente, sin glow, sin `backdrop-filter`.
- No se cambia ningún copy ni la lógica funcional de ningún flujo existente (chat, contacto, admin) — solo `className` y la estructura mínima de JSX necesaria para insertar el nuevo header.
- No se rediseña la estructura de las pantallas admin (tablas y formularios siguen siendo tablas y formularios).
- Este repo solo escribe tests para funciones puras (`lib/*.ts`), nunca para componentes React ni para clases CSS — convención existente, no se introduce testing de componentes en este plan.
- Assets de marca ya preparados (recortados y con fondo transparente) en
  `/tmp/claude-1000/-home-seba-Escritorio-workspace-macacha/6a4861a8-5010-4643-96e8-d4e72308675b/scratchpad/salta-assets/final/`:
  `logo-salta.svg`, `macacha-icon.png`, `macacha-logo-horizontal-light.png`,
  `macacha-logo-horizontal-dark.png`. Task 1 los copia al repo — si ese directorio no existe en el entorno del implementador (p. ej. worktree distinto), pedir los archivos al humano antes de continuar; no regenerarlos con supuestos distintos a los del spec.

---

### Task 1: Assets de marca en el repo

**Files:**
- Create: `frontend/public/branding/logo-salta.svg`
- Create: `frontend/public/branding/macacha-icon.png`
- Create: `frontend/public/branding/macacha-logo-horizontal-light.png`
- Create: `frontend/public/branding/macacha-logo-horizontal-dark.png`
- Create: `frontend/app/icon.png`

**Interfaces:**
- Produces: rutas públicas `/branding/logo-salta.svg`, `/branding/macacha-icon.png`,
  `/branding/macacha-logo-horizontal-light.png`, `/branding/macacha-logo-horizontal-dark.png`
  (servidas por Next.js desde `public/`), consumidas por `HeaderInstitucional` (Task 6) y
  `admin/login/page.tsx` (Task 13). `frontend/app/icon.png` es la convención de Next.js App
  Router para el favicon — no requiere código, Next.js lo sirve automáticamente.

- [ ] **Step 1: Copiar los assets preparados**

```bash
SRC="/tmp/claude-1000/-home-seba-Escritorio-workspace-macacha/6a4861a8-5010-4643-96e8-d4e72308675b/scratchpad/salta-assets/final"
mkdir -p frontend/public/branding
cp "$SRC/logo-salta.svg" frontend/public/branding/logo-salta.svg
cp "$SRC/macacha-icon.png" frontend/public/branding/macacha-icon.png
cp "$SRC/macacha-logo-horizontal-light.png" frontend/public/branding/macacha-logo-horizontal-light.png
cp "$SRC/macacha-logo-horizontal-dark.png" frontend/public/branding/macacha-logo-horizontal-dark.png
cp "$SRC/macacha-icon.png" frontend/app/icon.png
```

- [ ] **Step 2: Verificar que los 5 archivos existen y no están vacíos**

Run: `ls -la frontend/public/branding/ frontend/app/icon.png`
Expected: los 5 archivos listados, ninguno con tamaño 0.

- [ ] **Step 3: Commit**

```bash
git add frontend/public/branding frontend/app/icon.png
git commit -m "feat: agrega assets de marca (logo Salta + logo Macacha)"
```

---

### Task 2: Tokens de color, dark mode y clases de componente reutilizables

**Files:**
- Modify: `frontend/tailwind.config.ts`
- Modify: `frontend/app/globals.css`

**Interfaces:**
- Produces: token de colores `macacha.pink` / `macacha.blue` / `macacha.blueDark` / `macacha.navy`
  (clases Tailwind `bg-macacha-blue`, `text-macacha-blue`, `border-macacha-blue`, etc.);
  `darkMode: "class"`; clases de componente en `globals.css`: `.campo-label`, `.campo-input`,
  `.enlace-accion`, `.boton-primario`, `.boton-secundario`, `.tarjeta`, `.tabla-cabecera`,
  `.tabla-fila`, `.texto-secundario`, `.texto-error`, `.fondo-degrade-chat`. Todas las tareas
  siguientes las consumen.

- [ ] **Step 1: Reescribir `tailwind.config.ts`**

```ts
import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        macacha: {
          pink: "#f1446f",
          blue: "#0078c9",
          blueDark: "#005aba",
          navy: "#1a2732",
        },
      },
      fontFamily: {
        sans: ["var(--font-montserrat)", "ui-sans-serif", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
```

- [ ] **Step 2: Reescribir `app/globals.css`**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer components {
  .campo-label {
    @apply mb-1 block text-sm font-medium text-gray-700 dark:text-gray-200;
  }
  .campo-input {
    @apply rounded border border-gray-300 px-2 py-1 text-sm text-gray-900 disabled:bg-gray-100 disabled:text-gray-500 dark:border-white/20 dark:bg-white/5 dark:text-gray-100 dark:disabled:bg-white/10;
  }
  .enlace-accion {
    @apply text-sm text-macacha-blue underline dark:text-sky-300;
  }
  .boton-primario {
    @apply rounded bg-macacha-blue px-4 py-2 text-sm text-white hover:bg-macacha-blueDark disabled:opacity-50;
  }
  .boton-secundario {
    @apply rounded px-4 py-2 text-sm text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-white/10;
  }
  .tarjeta {
    @apply rounded border border-gray-200 bg-white p-4 dark:border-white/15 dark:bg-white/5;
  }
  .tabla-cabecera {
    @apply border-b border-gray-200 text-left dark:border-white/15;
  }
  .tabla-fila {
    @apply border-b border-gray-100 dark:border-white/10;
  }
  .texto-secundario {
    @apply text-gray-500 dark:text-gray-400;
  }
  .texto-error {
    @apply text-red-600 dark:text-red-400;
  }
  .fondo-degrade-chat {
    background-color: #fafbfc;
  }
  .dark .fondo-degrade-chat {
    background: radial-gradient(ellipse at top right, #3a1a4a 0%, #1a1a3a 35%, #121b23 70%);
  }
}
```

- [ ] **Step 3: Verificar que el build de Tailwind no falla**

Run: `cd frontend && npx tailwindcss -i app/globals.css -o /tmp/tw-check.css && rm /tmp/tw-check.css`
Expected: termina sin error (código de salida 0).

- [ ] **Step 4: Commit**

```bash
git add frontend/tailwind.config.ts frontend/app/globals.css
git commit -m "feat: agrega tokens de color de marca, dark mode y clases de componente"
```

---

### Task 3: Tipografía Montserrat + script anti-flash de tema

**Files:**
- Modify: `frontend/app/layout.tsx`

**Interfaces:**
- Consumes: token `macacha` (Task 2, ya en Tailwind config, no requiere import).
- Produces: variable CSS `--font-montserrat` aplicada en `<html>`, consumida por
  `fontFamily.sans` (Task 2). El script inline aplica la clase `dark` antes de la hidratación
  de React usando la misma lógica que `resolverTemaInicial` (Task 4), duplicada
  deliberadamente en JS plano porque corre antes de que cualquier módulo de la app esté
  disponible — patrón estándar para evitar flash de tema incorrecto (usado por librerías como
  `next-themes`).

- [ ] **Step 1: Reescribir `app/layout.tsx`**

```tsx
import type { Metadata } from "next";
import { Montserrat } from "next/font/google";
import "./globals.css";

const montserrat = Montserrat({ subsets: ["latin"], variable: "--font-montserrat" });

export const metadata: Metadata = {
  title: "Macacha",
  description: "Asistente virtual de trámites de la Provincia de Salta",
};

const SCRIPT_TEMA_INICIAL = `(function(){try{var t=localStorage.getItem('macacha-theme');var d=t==='dark'||(t!=='light'&&window.matchMedia('(prefers-color-scheme: dark)').matches);if(d)document.documentElement.classList.add('dark');}catch(e){}})();`;

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="es" className={montserrat.variable}>
      <head>
        <script dangerouslySetInnerHTML={{ __html: SCRIPT_TEMA_INICIAL }} />
      </head>
      <body>{children}</body>
    </html>
  );
}
```

- [ ] **Step 2: Verificar que compila**

Run: `cd frontend && npx tsc --noEmit`
Expected: sin errores.

- [ ] **Step 3: Commit**

```bash
git add frontend/app/layout.tsx
git commit -m "feat: agrega tipografía Montserrat y script anti-flash de tema"
```

---

### Task 4: `lib/theme.ts` — función pura de resolución de tema

**Files:**
- Create: `frontend/lib/theme.ts`
- Test: `frontend/lib/theme.test.ts`

**Interfaces:**
- Produces: `resolverTemaInicial(temaGuardado: string | null, prefiereOscuroDelSistema: boolean): Tema`
  y el tipo `Tema = "light" | "dark"`, consumidos por `hooks/useTema.ts` (Task 5).

- [ ] **Step 1: Escribir el test que falla**

```ts
import { describe, expect, it } from "vitest";
import { resolverTemaInicial } from "./theme";

describe("resolverTemaInicial", () => {
  it("usa el tema guardado si es válido", () => {
    expect(resolverTemaInicial("dark", false)).toBe("dark");
    expect(resolverTemaInicial("light", true)).toBe("light");
  });

  it("ignora un valor guardado inválido y usa la preferencia del sistema", () => {
    expect(resolverTemaInicial("cualquier-cosa", true)).toBe("dark");
    expect(resolverTemaInicial(null, true)).toBe("dark");
  });

  it("usa light por defecto si no hay tema guardado ni preferencia del sistema", () => {
    expect(resolverTemaInicial(null, false)).toBe("light");
  });
});
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `cd frontend && npx vitest run lib/theme.test.ts`
Expected: FAIL con "Cannot find module './theme'" (o similar, el archivo no existe todavía).

- [ ] **Step 3: Implementar `lib/theme.ts`**

```ts
export type Tema = "light" | "dark";

export function resolverTemaInicial(
  temaGuardado: string | null,
  prefiereOscuroDelSistema: boolean
): Tema {
  if (temaGuardado === "light" || temaGuardado === "dark") {
    return temaGuardado;
  }
  return prefiereOscuroDelSistema ? "dark" : "light";
}
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `cd frontend && npx vitest run lib/theme.test.ts`
Expected: PASS, 3 tests.

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/theme.ts frontend/lib/theme.test.ts
git commit -m "feat: agrega resolverTemaInicial (lógica pura de tema claro/oscuro)"
```

---

### Task 5: `hooks/useTema.ts` — hook compartido de toggle + persistencia

**Files:**
- Create: `frontend/hooks/useTema.ts`

**Interfaces:**
- Consumes: `resolverTemaInicial`, `type Tema` desde `../lib/theme` (Task 4).
- Produces: `useTema(): { tema: Tema; alternar: () => void }`, consumido por
  `HeaderInstitucional` (Task 6).

- [ ] **Step 1: Implementar `hooks/useTema.ts`**

```tsx
"use client";

import { useEffect, useState } from "react";
import { resolverTemaInicial, type Tema } from "../lib/theme";

const CLAVE_STORAGE = "macacha-theme";

export function useTema() {
  const [tema, setTema] = useState<Tema>("light");
  const [listo, setListo] = useState(false);

  useEffect(() => {
    const guardado = window.localStorage.getItem(CLAVE_STORAGE);
    const prefiereOscuro = window.matchMedia("(prefers-color-scheme: dark)").matches;
    setTema(resolverTemaInicial(guardado, prefiereOscuro));
    setListo(true);
  }, []);

  useEffect(() => {
    if (!listo) return;
    document.documentElement.classList.toggle("dark", tema === "dark");
    window.localStorage.setItem(CLAVE_STORAGE, tema);
  }, [tema, listo]);

  function alternar() {
    setTema((actual) => (actual === "dark" ? "light" : "dark"));
  }

  return { tema, alternar };
}
```

Nota: este hook no tiene test propio — es un wrapper de efectos secundarios (DOM,
`localStorage`) sobre la función pura ya testeada en Task 4, siguiendo la convención del repo
de testear solo funciones puras.

- [ ] **Step 2: Verificar que compila**

Run: `cd frontend && npx tsc --noEmit`
Expected: sin errores.

- [ ] **Step 3: Commit**

```bash
git add frontend/hooks/useTema.ts
git commit -m "feat: agrega hook useTema (toggle + persistencia de tema)"
```

---

### Task 6: `components/HeaderInstitucional.tsx`

**Files:**
- Create: `frontend/components/HeaderInstitucional.tsx`

**Interfaces:**
- Consumes: `useTema` desde `../hooks/useTema` (Task 5); assets `/branding/logo-salta.svg` y
  `/branding/macacha-icon.png` (Task 1).
- Produces: `HeaderInstitucional({ subtitulo: string; linkContacto?: { texto: string; onClick: () => void } })`,
  consumido por `app/page.tsx` (Task 7) y `app/admin/layout.tsx` (Task 12).

- [ ] **Step 1: Implementar `components/HeaderInstitucional.tsx`**

```tsx
"use client";

import { useTema } from "../hooks/useTema";

export function HeaderInstitucional({
  subtitulo,
  linkContacto,
}: {
  subtitulo: string;
  linkContacto?: { texto: string; onClick: () => void };
}) {
  const { tema, alternar } = useTema();

  return (
    <header>
      <div className="flex items-center border-b border-gray-200 bg-white px-4 py-2 dark:border-white/10 dark:bg-transparent sm:px-6">
        <img
          src="/branding/logo-salta.svg"
          alt="Gobierno de Salta"
          className="h-8 w-auto dark:hidden"
        />
        <span className="hidden items-center rounded-md bg-white px-2.5 py-1 dark:inline-flex">
          <img src="/branding/logo-salta.svg" alt="Gobierno de Salta" className="h-6 w-auto" />
        </span>
      </div>
      <div className="flex items-center justify-between border-b-2 border-macacha-blue bg-white px-4 py-3 dark:border-white/10 dark:bg-transparent sm:px-6">
        <div className="flex items-center gap-3">
          <img
            src="/branding/macacha-icon.png"
            alt="Macacha"
            className="h-10 w-10 dark:drop-shadow-[0_0_12px_rgba(241,68,111,0.6)]"
          />
          <div>
            <p className="text-lg font-bold text-macacha-navy dark:text-white">Macacha</p>
            <p className="text-sm text-gray-600 dark:text-[#9fb3c0]">{subtitulo}</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          {linkContacto && (
            <button onClick={linkContacto.onClick} className="enlace-accion">
              {linkContacto.texto}
            </button>
          )}
          <button
            onClick={alternar}
            aria-label={tema === "dark" ? "Cambiar a modo claro" : "Cambiar a modo oscuro"}
            className="rounded-full border border-gray-300 p-1.5 text-sm hover:bg-gray-100 dark:border-white/20 dark:hover:bg-white/10"
          >
            {tema === "dark" ? "☀️" : "🌙"}
          </button>
        </div>
      </div>
    </header>
  );
}
```

Nota de diseño (de la sesión de brainstorming, mockups `header-layout.html` /
`header-layout-dark.html` / `chat-completo-toggle.html` en `.superpowers/brainstorm/`): ambas
franjas son `bg-white` en claro y `bg-transparent` en oscuro — en oscuro dejan ver el fondo del
contenedor padre (el gradiente "aurora" en el chat, el `macacha.navy` liso en el admin), que es
lo que las Tasks 7 y 12 deben proveer.

- [ ] **Step 2: Verificar que compila**

Run: `cd frontend && npx tsc --noEmit`
Expected: sin errores.

- [ ] **Step 3: Commit**

```bash
git add frontend/components/HeaderInstitucional.tsx
git commit -m "feat: agrega HeaderInstitucional (franja Salta + franja Macacha + toggle tema)"
```

---

### Task 7: `app/page.tsx` — chat público, header + layout general

**Files:**
- Modify: `frontend/app/page.tsx`

**Interfaces:**
- Consumes: `HeaderInstitucional` (Task 6), `.fondo-degrade-chat` y `.texto-secundario` (Task 2).
- No cambia la interfaz de ningún hook ni componente hijo (`ChatInput`, `ChatMessage`,
  `ContactoHumanoModal`, los paneles del `aside`) — esos se re-estilizan en Tasks 8-11 sin
  cambiar sus props.

- [ ] **Step 1: Reescribir `app/page.tsx`**

```tsx
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
```

- [ ] **Step 2: Correr el test suite existente (no debe romper nada)**

Run: `cd frontend && npx vitest run && npx tsc --noEmit`
Expected: mismos tests en verde que antes de este cambio (25 passed), `tsc` sin errores.

- [ ] **Step 3: Commit**

```bash
git add frontend/app/page.tsx
git commit -m "feat: header institucional + layout del chat con paleta de marca"
```

---

### Task 8: `components/BurbujaMensaje.tsx` + `components/ChatMessage.tsx`

**Files:**
- Modify: `frontend/components/BurbujaMensaje.tsx`
- Modify: `frontend/components/ChatMessage.tsx`

**Interfaces:**
- No cambian: `BurbujaMensaje({ esUsuario, className?, children })`,
  `ChatMessage({ mensaje, onReintentar?, onPedirContacto? })` — mismas props, solo cambia el
  `className` interno.

- [ ] **Step 1: Reescribir `components/BurbujaMensaje.tsx`**

```tsx
export function BurbujaMensaje({
  esUsuario,
  className = "",
  children,
}: {
  esUsuario: boolean;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <div className={`flex ${esUsuario ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] rounded-lg px-4 py-2 ${
          esUsuario
            ? "bg-gradient-to-br from-macacha-blue to-macacha-blueDark text-white dark:shadow-[0_0_20px_rgba(0,120,201,0.5)]"
            : "bg-gray-100 text-gray-900 dark:bg-white/10 dark:text-gray-100 dark:backdrop-blur-sm"
        } ${className}`}
      >
        {children}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Reescribir `components/ChatMessage.tsx`**

```tsx
import type { Mensaje } from "../hooks/useChatStream";
import { BurbujaMensaje } from "./BurbujaMensaje";

export function ChatMessage({
  mensaje,
  onReintentar,
  onPedirContacto,
}: {
  mensaje: Mensaje;
  onReintentar?: () => void;
  onPedirContacto?: () => void;
}) {
  const esUsuario = mensaje.rol === "user";

  return (
    <BurbujaMensaje
      esUsuario={esUsuario}
      className={mensaje.error ? "border border-red-500 dark:border-red-400" : ""}
    >
      <p className="whitespace-pre-wrap">{mensaje.contenido}</p>
      {mensaje.fuentes && mensaje.fuentes.length > 0 && (
        <ul className="mt-2 border-t border-gray-300 pt-2 text-sm dark:border-white/20">
          {mensaje.fuentes.map((fuente) => (
            <li key={fuente.tramite_id}>
              {fuente.fuente_url ? (
                <a
                  href={fuente.fuente_url}
                  target="_blank"
                  rel="noreferrer"
                  className="enlace-accion"
                >
                  {fuente.nombre_oficial}
                </a>
              ) : (
                fuente.nombre_oficial
              )}
            </li>
          ))}
        </ul>
      )}
      {mensaje.sugerirContacto && onPedirContacto && (
        <button onClick={onPedirContacto} className="enlace-accion mt-2 block">
          ¿Querés que te ayude una persona? Completá este formulario
        </button>
      )}
      {mensaje.error && onReintentar && (
        <button onClick={onReintentar} className="texto-error mt-2 text-sm underline">
          Reintentar
        </button>
      )}
    </BurbujaMensaje>
  );
}
```

- [ ] **Step 3: Correr el test suite existente**

Run: `cd frontend && npx vitest run && npx tsc --noEmit`
Expected: 25 passed, `tsc` sin errores.

- [ ] **Step 4: Commit**

```bash
git add frontend/components/BurbujaMensaje.tsx frontend/components/ChatMessage.tsx
git commit -m "feat: paleta de marca en burbujas de chat (glow + glassmorphism en oscuro)"
```

---

### Task 9: `components/ChatInput.tsx`

**Files:**
- Modify: `frontend/components/ChatInput.tsx`

**Interfaces:**
- No cambia: `ChatInput({ disabled, onEnviar })`.

- [ ] **Step 1: Reescribir `components/ChatInput.tsx`**

```tsx
"use client";

import { useState } from "react";

export function ChatInput({
  disabled,
  onEnviar,
}: {
  disabled: boolean;
  onEnviar: (texto: string) => void;
}) {
  const [texto, setTexto] = useState("");

  function enviar() {
    const limpio = texto.trim();
    if (!limpio || disabled) return;
    onEnviar(limpio);
    setTexto("");
  }

  return (
    <div className="flex gap-2 border-t border-gray-200 p-4 dark:border-white/10">
      <textarea
        className="campo-input flex-1 resize-none"
        rows={2}
        value={texto}
        disabled={disabled}
        onChange={(e) => setTexto(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            enviar();
          }
        }}
        placeholder="Escribí tu consulta sobre un trámite..."
      />
      <button className="boton-primario" disabled={disabled || !texto.trim()} onClick={enviar}>
        Enviar
      </button>
    </div>
  );
}
```

- [ ] **Step 2: Correr el test suite existente**

Run: `cd frontend && npx vitest run && npx tsc --noEmit`
Expected: 25 passed, `tsc` sin errores.

- [ ] **Step 3: Commit**

```bash
git add frontend/components/ChatInput.tsx
git commit -m "feat: paleta de marca en ChatInput"
```

---

### Task 10: `components/ContactoHumanoModal.tsx`

**Files:**
- Modify: `frontend/components/ContactoHumanoModal.tsx`

**Interfaces:**
- No cambia: `ContactoHumanoModal({ sessionId, mensajes, onCerrar })`.

- [ ] **Step 1: Reescribir `components/ContactoHumanoModal.tsx`**

```tsx
"use client";

import { useState } from "react";
import { enviarSolicitudContacto } from "../lib/contacto-api";
import { tramitesCitadosEnConversacion } from "../lib/contacto-tramites";
import type { Mensaje } from "../hooks/useChatStream";

export function ContactoHumanoModal({
  sessionId,
  mensajes,
  onCerrar,
}: {
  sessionId: string;
  mensajes: Mensaje[];
  onCerrar: () => void;
}) {
  const tramites = tramitesCitadosEnConversacion(mensajes);
  const [tramiteId, setTramiteId] = useState<string | null>(
    tramites.length === 1 ? tramites[0].tramite_id : null
  );
  const [nombre, setNombre] = useState("");
  const [email, setEmail] = useState("");
  const [telefono, setTelefono] = useState("");
  const [consulta, setConsulta] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [enviado, setEnviado] = useState(false);

  const puedeEnviar =
    nombre.trim() !== "" &&
    email.trim() !== "" &&
    telefono.trim() !== "" &&
    consulta.trim() !== "";

  async function handleSubmit(evento: React.FormEvent) {
    evento.preventDefault();
    setEnviando(true);
    setError(null);
    try {
      await enviarSolicitudContacto({
        session_id: sessionId,
        tramite_id: tramiteId,
        nombre,
        email,
        telefono,
        consulta,
      });
      setEnviado(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo enviar la consulta");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-md rounded-lg bg-white p-6 dark:border dark:border-white/15 dark:bg-macacha-navy">
        {enviado ? (
          <div>
            <p className="text-sm text-gray-800 dark:text-gray-100">
              Recibimos tu consulta. Alguien del área correspondiente se va a poner en
              contacto con vos.
            </p>
            <button onClick={onCerrar} className="boton-primario mt-4">
              Cerrar
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-3">
            <h2 className="text-lg font-semibold text-macacha-navy dark:text-white">
              Hablar con una persona
            </h2>

            {tramites.length > 1 && (
              <div>
                <label className="campo-label">¿Sobre qué trámite?</label>
                <select
                  value={tramiteId ?? ""}
                  onChange={(e) => setTramiteId(e.target.value || null)}
                  className="campo-input w-full"
                >
                  <option value="">Elegir…</option>
                  {tramites.map((t) => (
                    <option key={t.tramite_id} value={t.tramite_id}>
                      {t.nombre_oficial}
                    </option>
                  ))}
                </select>
              </div>
            )}
            {tramites.length === 1 && (
              <p className="text-sm texto-secundario">Trámite: {tramites[0].nombre_oficial}</p>
            )}
            {tramites.length === 0 && (
              <p className="text-sm texto-secundario">
                No identificamos un trámite en esta conversación — tu consulta la recibe el
                equipo general.
              </p>
            )}

            <div>
              <label className="campo-label">Nombre</label>
              <input
                type="text"
                value={nombre}
                onChange={(e) => setNombre(e.target.value)}
                className="campo-input w-full"
              />
            </div>
            <div>
              <label className="campo-label">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="campo-input w-full"
              />
            </div>
            <div>
              <label className="campo-label">Teléfono / WhatsApp</label>
              <input
                type="text"
                value={telefono}
                onChange={(e) => setTelefono(e.target.value)}
                className="campo-input w-full"
              />
            </div>
            <div>
              <label className="campo-label">Tu consulta</label>
              <textarea
                value={consulta}
                onChange={(e) => setConsulta(e.target.value)}
                className="campo-input w-full"
                rows={3}
              />
            </div>

            {error && <p className="text-sm texto-error">{error}</p>}

            <div className="flex gap-2">
              <button type="submit" disabled={!puedeEnviar || enviando} className="boton-primario">
                {enviando ? "Enviando…" : "Enviar"}
              </button>
              <button type="button" onClick={onCerrar} className="boton-secundario">
                Cancelar
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Correr el test suite existente**

Run: `cd frontend && npx vitest run && npx tsc --noEmit`
Expected: 25 passed, `tsc` sin errores.

- [ ] **Step 3: Commit**

```bash
git add frontend/components/ContactoHumanoModal.tsx
git commit -m "feat: paleta de marca en ContactoHumanoModal"
```

---

### Task 11: Paneles laterales del chat (`TramiteInfoPanel`, `TramitesAmbiguosPanel`, `TramitesFrecuentesPanel`, `CopyButton`)

**Files:**
- Modify: `frontend/components/TramiteInfoPanel.tsx`
- Modify: `frontend/components/TramitesAmbiguosPanel.tsx`
- Modify: `frontend/components/TramitesFrecuentesPanel.tsx`
- Modify: `frontend/components/CopyButton.tsx`

**Interfaces:**
- No cambia ninguna prop de estos 4 componentes.

- [ ] **Step 1: Reescribir `components/TramiteInfoPanel.tsx`**

```tsx
"use client";

import type { TramiteDetalle } from "../lib/api";
import { CopyButton } from "./CopyButton";
import { useChecklist } from "../hooks/useChecklist";

export function TramiteInfoPanel({
  tramite,
  onPreguntar,
  preguntarDeshabilitado,
}: {
  tramite: TramiteDetalle;
  onPreguntar: (mensaje: string) => void;
  preguntarDeshabilitado: boolean;
}) {
  const { estaTildado, toggle } = useChecklist(tramite.tramite_id);

  return (
    <div className="text-gray-900 dark:text-gray-100">
      <h2 className="font-semibold">{tramite.nombre_oficial}</h2>
      <p className="text-sm texto-secundario">{tramite.organismo}</p>

      {tramite.requisitos.length > 0 && (
        <div className="mt-4">
          <h3 className="text-sm font-medium">Requisitos</h3>
          <ul className="mt-1 space-y-1 text-sm">
            {tramite.requisitos.map((requisito, indice) => (
              <li key={requisito} className="flex items-start gap-2">
                <input
                  type="checkbox"
                  className="mt-1"
                  checked={estaTildado("requisito", indice)}
                  onChange={() => toggle("requisito", indice)}
                  aria-label={`Marcar requisito: ${requisito}`}
                />
                <span
                  className={
                    estaTildado("requisito", indice)
                      ? "flex-1 text-gray-400 line-through dark:text-gray-500"
                      : "flex-1"
                  }
                >
                  {requisito}
                </span>
                <CopyButton texto={requisito} />
              </li>
            ))}
          </ul>
          <BotonDuda
            texto={`Tengo una duda sobre los requisitos de ${tramite.nombre_oficial}.`}
            onPreguntar={onPreguntar}
            disabled={preguntarDeshabilitado}
          />
        </div>
      )}

      {(tramite.costo || tramite.modalidad || tramite.duracion) && (
        <div className="mt-4 text-sm">
          <h3 className="font-medium">Costo, modalidad y duración</h3>
          {tramite.costo && <p>Costo: {tramite.costo}</p>}
          {tramite.modalidad && <p>Modalidad: {tramite.modalidad}</p>}
          {tramite.duracion && <p>Duración: {tramite.duracion}</p>}
          <BotonDuda
            texto={`Tengo una duda sobre el costo, la modalidad o la duración de ${tramite.nombre_oficial}.`}
            onPreguntar={onPreguntar}
            disabled={preguntarDeshabilitado}
          />
        </div>
      )}

      {tramite.pasos.length > 0 && (
        <div className="mt-4">
          <h3 className="text-sm font-medium">Pasos</h3>
          <ol className="mt-1 space-y-1 text-sm">
            {tramite.pasos.map((paso, indice) => (
              <li key={paso} className="flex items-start gap-2">
                <input
                  type="checkbox"
                  className="mt-1"
                  checked={estaTildado("paso", indice)}
                  onChange={() => toggle("paso", indice)}
                  aria-label={`Marcar paso: ${paso}`}
                />
                <span
                  className={
                    estaTildado("paso", indice)
                      ? "flex-1 text-gray-400 line-through dark:text-gray-500"
                      : "flex-1"
                  }
                >
                  {paso}
                </span>
                <CopyButton texto={paso} />
              </li>
            ))}
          </ol>
          <BotonDuda
            texto={`Tengo una duda sobre los pasos de ${tramite.nombre_oficial}.`}
            onPreguntar={onPreguntar}
            disabled={preguntarDeshabilitado}
          />
        </div>
      )}

      {tramite.enlaces_oficiales.length > 0 && (
        <div className="mt-4">
          <h3 className="text-sm font-medium">Enlaces oficiales</h3>
          <div className="mt-1 flex flex-col gap-2">
            {tramite.enlaces_oficiales.map((enlace) => (
              <a
                key={enlace}
                href={enlace}
                target="_blank"
                rel="noreferrer"
                className="rounded border border-macacha-blue px-3 py-1.5 text-center text-sm text-macacha-blue hover:bg-blue-50 dark:hover:bg-white/10"
              >
                {enlace}
              </a>
            ))}
          </div>
        </div>
      )}

      <div className="mt-4 text-sm">
        <h3 className="font-medium">Contacto</h3>
        {tramite.telefono_contacto && (
          <p>
            Tel: {tramite.telefono_contacto}
            <CopyButton texto={tramite.telefono_contacto} />
          </p>
        )}
        {tramite.email_contacto && (
          <p>
            Mail: {tramite.email_contacto}
            <CopyButton texto={tramite.email_contacto} />
          </p>
        )}
        {!tramite.telefono_contacto && !tramite.email_contacto && (
          <p className="texto-secundario">Sin datos de contacto.</p>
        )}
      </div>
    </div>
  );
}

function BotonDuda({
  texto,
  onPreguntar,
  disabled,
}: {
  texto: string;
  onPreguntar: (mensaje: string) => void;
  disabled: boolean;
}) {
  return (
    <button
      type="button"
      onClick={() => onPreguntar(texto)}
      disabled={disabled}
      className="enlace-accion mt-2 text-xs disabled:opacity-50"
    >
      ¿Tenés dudas sobre esto?
    </button>
  );
}
```

- [ ] **Step 2: Reescribir `components/TramitesAmbiguosPanel.tsx`**

```tsx
"use client";

import type { CandidatoAmbiguo } from "../hooks/useChatStream";

export function TramitesAmbiguosPanel({
  candidatos,
  onPreguntar,
  preguntarDeshabilitado,
}: {
  candidatos: CandidatoAmbiguo[];
  onPreguntar: (mensaje: string) => void;
  preguntarDeshabilitado: boolean;
}) {
  return (
    <div className="text-gray-900 dark:text-gray-100">
      <h2 className="font-semibold">¿Cuál de estos trámites te interesa?</h2>
      <ul className="mt-2 space-y-3">
        {candidatos.map((candidato) => (
          <li key={candidato.tramite_id}>
            <button
              type="button"
              onClick={() => onPreguntar(`Quiero información sobre ${candidato.nombre_oficial}.`)}
              disabled={preguntarDeshabilitado}
              className="w-full rounded border border-gray-200 p-2 text-left text-sm hover:bg-gray-50 disabled:opacity-50 dark:border-white/15 dark:hover:bg-white/5"
            >
              <span className="font-medium">{candidato.nombre_oficial}</span>
              <p className="mt-1 texto-secundario">{candidato.descripcion}</p>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
```

- [ ] **Step 3: Reescribir `components/TramitesFrecuentesPanel.tsx`**

```tsx
import type { TramiteFrecuente } from "../lib/api";

export function TramitesFrecuentesPanel({
  tramites,
  onPreguntar,
  preguntarDeshabilitado,
}: {
  tramites: TramiteFrecuente[];
  onPreguntar: (mensaje: string) => void;
  preguntarDeshabilitado: boolean;
}) {
  if (tramites.length === 0) {
    return (
      <p className="text-sm texto-secundario">
        Los trámites más consultados van a aparecer acá.
      </p>
    );
  }

  return (
    <div className="text-gray-900 dark:text-gray-100">
      <h2 className="font-semibold">Más consultados</h2>
      <ol className="mt-2 space-y-2 text-sm">
        {tramites.map((tramite, indice) => (
          <li key={tramite.tramite_id}>
            <button
              type="button"
              onClick={() => onPreguntar(`Quiero información sobre ${tramite.nombre_oficial}.`)}
              disabled={preguntarDeshabilitado}
              className="flex w-full justify-between gap-2 rounded p-1 text-left hover:bg-gray-50 disabled:opacity-50 dark:hover:bg-white/5"
            >
              <span>
                {indice + 1}. {tramite.nombre_oficial}
              </span>
              <span className="texto-secundario">{tramite.veces_consultado}</span>
            </button>
          </li>
        ))}
      </ol>
    </div>
  );
}
```

- [ ] **Step 4: Reescribir `components/CopyButton.tsx`**

```tsx
"use client";

import { useState } from "react";

export function CopyButton({ texto }: { texto: string }) {
  const [estado, setEstado] = useState<"idle" | "copiado" | "error">("idle");

  async function copiar() {
    try {
      await navigator.clipboard.writeText(texto);
      setEstado("copiado");
    } catch {
      setEstado("error");
    }
    setTimeout(() => setEstado("idle"), 1500);
  }

  return (
    <button
      type="button"
      onClick={copiar}
      className="enlace-accion ml-2 text-xs"
      aria-label={`Copiar ${texto}`}
    >
      {estado === "idle" && "Copiar"}
      {estado === "copiado" && "Copiado ✓"}
      {estado === "error" && "No se pudo copiar"}
    </button>
  );
}
```

- [ ] **Step 5: Correr el test suite existente**

Run: `cd frontend && npx vitest run && npx tsc --noEmit`
Expected: 25 passed (incluye `hooks/useChecklist.test.ts`, que no debe romperse), `tsc` sin errores.

- [ ] **Step 6: Commit**

```bash
git add frontend/components/TramiteInfoPanel.tsx frontend/components/TramitesAmbiguosPanel.tsx frontend/components/TramitesFrecuentesPanel.tsx frontend/components/CopyButton.tsx
git commit -m "feat: paleta de marca en los paneles laterales del chat"
```

---

### Task 12: `app/admin/layout.tsx` — header institucional + sidebar

**Files:**
- Modify: `frontend/app/admin/layout.tsx`

**Interfaces:**
- Consumes: `HeaderInstitucional` con `subtitulo="Panel de administración"` y sin
  `linkContacto` (Task 6).
- No cambia: sigue usando `AdminAuthProvider` / `useAdminActual` / `logout` sin tocar su
  comportamiento — el `if (pathname === "/admin/login") return <>{children}</>` se mantiene
  igual (el login no lleva este header, ver Task 13).

- [ ] **Step 1: Reescribir `app/admin/layout.tsx`**

```tsx
"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { logout } from "../../lib/admin-api";
import { AdminAuthProvider, useAdminActual } from "../../hooks/useAdminActual";
import { HeaderInstitucional } from "../../components/HeaderInstitucional";

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
    <div className="flex h-screen flex-col bg-white text-gray-900 dark:bg-macacha-navy dark:text-gray-100">
      <HeaderInstitucional subtitulo="Panel de administración" />
      <div className="flex flex-1 overflow-hidden">
        <nav className="flex w-48 flex-col justify-between border-r border-gray-200 p-4 dark:border-white/10">
          <ul className="space-y-1 text-sm">
            <li>
              <ItemNav href="/admin/chats" pathname={pathname}>
                Chats
              </ItemNav>
            </li>
            <li>
              <ItemNav href="/admin/tramites" pathname={pathname}>
                Trámites
              </ItemNav>
            </li>
            <li>
              <ItemNav href="/admin/contacto" pathname={pathname}>
                Contacto
              </ItemNav>
            </li>
            {admin?.rol === "super_admin" && (
              <li>
                <ItemNav href="/admin/usuarios" pathname={pathname}>
                  Usuarios
                </ItemNav>
              </li>
            )}
          </ul>
          <button onClick={handleLogout} className="boton-secundario text-left">
            Cerrar sesión
          </button>
        </nav>
        <main className="flex-1 overflow-y-auto">{children}</main>
      </div>
    </div>
  );
}

function ItemNav({
  href,
  pathname,
  children,
}: {
  href: string;
  pathname: string;
  children: React.ReactNode;
}) {
  const activo = pathname.startsWith(href);
  return (
    <Link
      href={href}
      className={
        activo
          ? "block rounded-md bg-blue-50 px-2 py-1.5 font-semibold text-macacha-blue dark:bg-macacha-blue/15 dark:text-sky-300"
          : "block rounded-md px-2 py-1.5 text-gray-700 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-white/5"
      }
    >
      {children}
    </Link>
  );
}
```

Nota: se quita el `<p>Macacha Admin</p>` estático del sidebar — ese rol ya lo cumple el ícono +
wordmark del `HeaderInstitucional` arriba, evitando duplicar el nombre de marca dos veces en la
misma pantalla (decisión tomada al escribir esta tarea, coherente con el mockup
`admin-style.html` aprobado, que no repetía "Macacha" en el sidebar).

- [ ] **Step 2: Correr el test suite existente**

Run: `cd frontend && npx vitest run && npx tsc --noEmit`
Expected: 25 passed, `tsc` sin errores.

- [ ] **Step 3: Commit**

```bash
git add frontend/app/admin/layout.tsx
git commit -m "feat: header institucional + sidebar recoloreado en el admin"
```

---

### Task 13: `app/admin/login/page.tsx`

**Files:**
- Modify: `frontend/app/admin/login/page.tsx`

**Interfaces:**
- No cambia: `LoginPage` sigue llamando a `login(email, password)` de `../../../lib/admin-api`
  igual que antes.

- [ ] **Step 1: Reescribir `app/admin/login/page.tsx`**

```tsx
"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { login } from "../../../lib/admin-api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(false);
  const [enviando, setEnviando] = useState(false);

  async function handleSubmit(evento: FormEvent) {
    evento.preventDefault();
    setEnviando(true);
    setError(false);
    const resultado = await login(email, password);
    setEnviando(false);
    if (!resultado.ok) {
      setError(true);
      return;
    }
    router.push("/admin/chats");
  }

  return (
    <div className="flex h-screen items-center justify-center bg-white dark:bg-macacha-navy">
      <form onSubmit={handleSubmit} className="w-full max-w-sm space-y-4 p-4">
        <div className="mb-2 flex flex-col items-center gap-2">
          <img src="/branding/macacha-icon.png" alt="Macacha" className="h-12 w-12" />
          <h1 className="text-lg font-semibold text-macacha-navy dark:text-white">Ingresar</h1>
        </div>
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
  );
}
```

- [ ] **Step 2: Correr el test suite existente**

Run: `cd frontend && npx vitest run && npx tsc --noEmit`
Expected: 25 passed, `tsc` sin errores.

- [ ] **Step 3: Commit**

```bash
git add frontend/app/admin/login/page.tsx
git commit -m "feat: paleta de marca en el login del admin"
```

---

### Task 14: Admin — Chats (`admin/chats/page.tsx`, `admin/chats/[id]/page.tsx`, `components/ConversacionChat.tsx`)

**Files:**
- Modify: `frontend/app/admin/chats/page.tsx`
- Modify: `frontend/app/admin/chats/[id]/page.tsx`
- Modify: `frontend/components/ConversacionChat.tsx`

**Interfaces:**
- No cambia ninguna prop ni firma de función.

- [ ] **Step 1: Reescribir `app/admin/chats/page.tsx`**

```tsx
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
```

- [ ] **Step 2: Reescribir `app/admin/chats/[id]/page.tsx`**

```tsx
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
```

- [ ] **Step 3: Reescribir `components/ConversacionChat.tsx`**

```tsx
"use client";

import { useState } from "react";
import type { MensajeAdmin } from "../lib/admin-api";
import { extraerDetalleToolCalls } from "../lib/admin-chats";
import { BurbujaMensaje } from "./BurbujaMensaje";

export function ConversacionChat({ mensajes }: { mensajes: MensajeAdmin[] }) {
  const visibles = mensajes.filter((m) => m.rol === "user" || m.rol === "assistant");

  return (
    <div className="mx-auto max-w-2xl space-y-3">
      {visibles.map((mensaje, indice) => (
        <BurbujaMensaje key={indice} esUsuario={mensaje.rol === "user"}>
          <p className="whitespace-pre-wrap">{mensaje.contenido}</p>
          {mensaje.rol === "assistant" && mensaje.proveedor && (
            <span className="mt-1 inline-block rounded bg-gray-200 px-1.5 py-0.5 text-xs text-gray-600 dark:bg-white/15 dark:text-gray-300">
              {mensaje.proveedor === "gemini" ? "Gemini" : "OpenAI"}
            </span>
          )}
          {mensaje.rol === "assistant" && mensaje.tool_calls && mensaje.tool_calls.length > 0 && (
            <DetalleTecnico mensaje={mensaje} todosLosMensajes={mensajes} />
          )}
        </BurbujaMensaje>
      ))}
    </div>
  );
}

function DetalleTecnico({
  mensaje,
  todosLosMensajes,
}: {
  mensaje: MensajeAdmin;
  todosLosMensajes: MensajeAdmin[];
}) {
  const [abierto, setAbierto] = useState(false);
  const detalle = extraerDetalleToolCalls(mensaje, todosLosMensajes);

  return (
    <div className="mt-2 border-t border-gray-300 pt-2 text-sm dark:border-white/20">
      <button onClick={() => setAbierto(!abierto)} className="enlace-accion">
        {abierto ? "Ocultar detalle técnico" : "Ver detalle técnico"}
      </button>
      {abierto && (
        <ul className="mt-2 space-y-2">
          {detalle.map((item) => (
            <li key={item.id} className="rounded bg-white p-2 dark:bg-black/20">
              <p className="font-mono text-xs font-semibold">{item.nombre}</p>
              <pre className="whitespace-pre-wrap break-all text-xs">{item.argumentos}</pre>
              <pre className="whitespace-pre-wrap break-all text-xs texto-secundario">
                {item.resultado ?? "(sin resultado)"}
              </pre>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Correr el test suite existente**

Run: `cd frontend && npx vitest run && npx tsc --noEmit`
Expected: 25 passed (incluye `lib/admin-chats.test.ts`, que no debe romperse), `tsc` sin errores.

- [ ] **Step 5: Commit**

```bash
git add frontend/app/admin/chats frontend/components/ConversacionChat.tsx
git commit -m "feat: paleta de marca en Chats admin"
```

---

### Task 15: Admin — Trámites (`admin/tramites/page.tsx`, `admin/tramites/[id]/page.tsx`, `components/TramiteForm.tsx`, `components/ListaTextos.tsx`, `components/ListaFAQ.tsx`)

**Files:**
- Modify: `frontend/app/admin/tramites/page.tsx`
- Modify: `frontend/app/admin/tramites/[id]/page.tsx`
- Modify: `frontend/components/TramiteForm.tsx`
- Modify: `frontend/components/ListaTextos.tsx`
- Modify: `frontend/components/ListaFAQ.tsx`
- No modifica: `frontend/app/admin/tramites/nuevo/page.tsx` (no tiene ningún `className` propio
  — delega todo el JSX a `TramiteForm` — no requiere cambios).

**Interfaces:**
- No cambia ninguna prop ni firma de función.

- [ ] **Step 1: Reescribir `app/admin/tramites/page.tsx`**

```tsx
"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { listarTramites, type TramiteResumen } from "../../../lib/admin-tramites-api";

export default function TramitesPage() {
  const [tramites, setTramites] = useState<TramiteResumen[] | null>(null);
  const [error, setError] = useState(false);
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    cargar();
  }, []);

  async function cargar() {
    setCargando(true);
    setError(false);
    try {
      const resultado = await listarTramites();
      setTramites(resultado);
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
        <p className="text-sm texto-error">No se pudo cargar la lista de trámites</p>
        <button onClick={cargar} className="enlace-accion mt-2">
          Reintentar
        </button>
      </div>
    );
  }

  return (
    <div className="p-4">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-lg font-semibold">Trámites</h1>
        <Link href="/admin/tramites/nuevo" className="boton-primario">
          Nuevo trámite
        </Link>
      </div>
      {tramites && tramites.length === 0 ? (
        <p className="text-sm texto-secundario">Todavía no hay trámites cargados</p>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="tabla-cabecera">
              <th className="p-2">ID</th>
              <th className="p-2">Nombre</th>
              <th className="p-2">Organismo</th>
              <th className="p-2">Categoría</th>
              <th className="p-2">Consultas</th>
              <th className="p-2">Versión</th>
            </tr>
          </thead>
          <tbody>
            {tramites!.map((tramite) => (
              <tr key={tramite.id} className="tabla-fila">
                <td className="p-2">
                  <Link
                    href={`/admin/tramites/${tramite.id}`}
                    className="text-macacha-blue hover:underline dark:text-sky-300"
                  >
                    {tramite.id}
                  </Link>
                </td>
                <td className="p-2">{tramite.nombre_oficial}</td>
                <td className="p-2">{tramite.organismo}</td>
                <td className="p-2">{tramite.categoria}</td>
                <td className="p-2">{tramite.veces_consultado}</td>
                <td className="p-2">{tramite.numero_version ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Reescribir `app/admin/tramites/[id]/page.tsx`**

```tsx
"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { useAdminActual } from "../../../../hooks/useAdminActual";
import { TramiteForm } from "../../../../components/TramiteForm";
import {
  Organismo,
  editarTramite,
  listarOrganismos,
  obtenerTramiteAdmin,
  type TramiteDetalleAdmin,
} from "../../../../lib/admin-tramites-api";

export default function EditarTramitePage() {
  const params = useParams<{ id: string }>();
  const admin = useAdminActual();
  const [organismos, setOrganismos] = useState<Organismo[]>([]);
  const [tramite, setTramite] = useState<TramiteDetalleAdmin | null | undefined>(undefined);
  const [cargandoError, setCargandoError] = useState(false);
  const [guardando, setGuardando] = useState(false);
  const [errorGuardado, setErrorGuardado] = useState<string | null>(null);
  const [confirmacion, setConfirmacion] = useState<string | null>(null);

  useEffect(() => {
    cargar();
  }, [params.id]);

  async function cargar() {
    setCargandoError(false);
    setTramite(undefined);
    try {
      const [detalle, listaOrganismos] = await Promise.all([
        obtenerTramiteAdmin(params.id),
        listarOrganismos(),
      ]);
      setTramite(detalle);
      setOrganismos(listaOrganismos);
    } catch {
      setCargandoError(true);
    }
  }

  async function handleGuardar(datos: TramiteDetalleAdmin) {
    setGuardando(true);
    setErrorGuardado(null);
    setConfirmacion(null);
    try {
      const resultado = await editarTramite(params.id, datos);
      setConfirmacion(
        resultado.cambios
          ? `Guardado como versión ${resultado.numero_version}.`
          : "No había cambios para guardar."
      );
    } catch (err) {
      setErrorGuardado(err instanceof Error ? err.message : "No se pudo guardar el trámite");
    } finally {
      setGuardando(false);
    }
  }

  if (cargandoError) {
    return (
      <div className="p-4">
        <p className="text-sm texto-error">No se pudo cargar el trámite</p>
        <button onClick={cargar} className="enlace-accion mt-2">
          Reintentar
        </button>
      </div>
    );
  }

  if (tramite === undefined) {
    return <p className="p-4 text-sm texto-secundario">Cargando…</p>;
  }

  if (tramite === null) {
    return <p className="p-4 text-sm texto-secundario">Trámite no encontrado</p>;
  }

  return (
    <div>
      {confirmacion && (
        <p className="p-4 pb-0 text-sm text-green-700 dark:text-green-400">{confirmacion}</p>
      )}
      <TramiteForm
        valoresIniciales={tramite}
        organismosExistentes={organismos}
        organismoFijo={admin?.rol === "admin_organismo" ? admin.organismo ?? undefined : undefined}
        guardando={guardando}
        error={errorGuardado}
        onGuardar={handleGuardar}
      />
    </div>
  );
}
```

- [ ] **Step 3: Reescribir `components/TramiteForm.tsx`**

```tsx
"use client";

import { useState, type FormEvent } from "react";
import { ListaFAQ } from "./ListaFAQ";
import { ListaTextos } from "./ListaTextos";
import type { Organismo, TramiteDetalleAdmin } from "../lib/admin-tramites-api";

export function TramiteForm({
  valoresIniciales,
  organismosExistentes,
  organismoFijo,
  guardando,
  error,
  onGuardar,
}: {
  valoresIniciales: TramiteDetalleAdmin;
  organismosExistentes: Organismo[];
  organismoFijo?: string;
  guardando: boolean;
  error: string | null;
  onGuardar: (datos: TramiteDetalleAdmin) => void;
}) {
  const [datos, setDatos] = useState<TramiteDetalleAdmin>(valoresIniciales);
  const [organismoEsNuevo, setOrganismoEsNuevo] = useState(
    !organismosExistentes.some((o) => o.nombre === valoresIniciales.organismo)
  );

  function actualizar<K extends keyof TramiteDetalleAdmin>(campo: K, valor: TramiteDetalleAdmin[K]) {
    setDatos((anterior) => ({ ...anterior, [campo]: valor }));
  }

  function handleSubmit(evento: FormEvent) {
    evento.preventDefault();
    onGuardar(organismoFijo ? { ...datos, organismo: organismoFijo } : datos);
  }

  const organismoEfectivo = organismoFijo ?? datos.organismo;
  const puedeGuardar = organismoEfectivo.trim() !== "" && datos.nombre_oficial.trim() !== "";

  return (
    <form onSubmit={handleSubmit} className="max-w-2xl space-y-4 p-4">
      <div>
        <label className="campo-label">Organismo</label>
        {organismoFijo ? (
          <input type="text" value={organismoFijo} disabled className="campo-input w-full" />
        ) : organismoEsNuevo ? (
          <input
            type="text"
            value={datos.organismo}
            onChange={(e) => actualizar("organismo", e.target.value)}
            className="campo-input w-full"
          />
        ) : (
          <select
            value={datos.organismo}
            onChange={(e) => actualizar("organismo", e.target.value)}
            className="campo-input w-full"
          >
            {organismosExistentes.map((organismo) => (
              <option key={organismo.id} value={organismo.nombre}>
                {organismo.nombre}
              </option>
            ))}
          </select>
        )}
        {!organismoFijo && (
          <button
            type="button"
            onClick={() => setOrganismoEsNuevo(!organismoEsNuevo)}
            className="enlace-accion mt-1"
          >
            {organismoEsNuevo ? "Elegir uno existente" : "Otro… (crear nuevo)"}
          </button>
        )}
      </div>

      <div>
        <label className="campo-label">Categoría</label>
        <input
          type="text"
          value={datos.categoria}
          onChange={(e) => actualizar("categoria", e.target.value)}
          className="campo-input w-full"
        />
      </div>

      <div>
        <label className="campo-label">Nombre oficial</label>
        <input
          type="text"
          value={datos.nombre_oficial}
          onChange={(e) => actualizar("nombre_oficial", e.target.value)}
          className="campo-input w-full"
        />
      </div>

      <div>
        <label className="campo-label">Descripción</label>
        <textarea
          value={datos.descripcion}
          onChange={(e) => actualizar("descripcion", e.target.value)}
          className="campo-input w-full"
        />
      </div>

      <div>
        <label className="campo-label">Objetivo</label>
        <textarea
          value={datos.objetivo}
          onChange={(e) => actualizar("objetivo", e.target.value)}
          className="campo-input w-full"
        />
      </div>

      <ListaTextos
        etiqueta="Requisitos"
        valores={datos.requisitos}
        onChange={(v) => actualizar("requisitos", v)}
      />
      <ListaTextos etiqueta="Pasos" valores={datos.pasos} onChange={(v) => actualizar("pasos", v)} />

      <div className="grid grid-cols-3 gap-2">
        <div>
          <label className="campo-label">Costo</label>
          <input
            type="text"
            value={datos.costo}
            onChange={(e) => actualizar("costo", e.target.value)}
            className="campo-input w-full"
          />
        </div>
        <div>
          <label className="campo-label">Modalidad</label>
          <input
            type="text"
            value={datos.modalidad}
            onChange={(e) => actualizar("modalidad", e.target.value)}
            className="campo-input w-full"
          />
        </div>
        <div>
          <label className="campo-label">Duración</label>
          <input
            type="text"
            value={datos.duracion}
            onChange={(e) => actualizar("duracion", e.target.value)}
            className="campo-input w-full"
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className="campo-label">Teléfono de contacto</label>
          <input
            type="text"
            value={datos.telefono_contacto}
            onChange={(e) => actualizar("telefono_contacto", e.target.value)}
            className="campo-input w-full"
          />
        </div>
        <div>
          <label className="campo-label">Email de contacto</label>
          <input
            type="text"
            value={datos.email_contacto}
            onChange={(e) => actualizar("email_contacto", e.target.value)}
            className="campo-input w-full"
          />
        </div>
      </div>

      <ListaTextos
        etiqueta="Problemas frecuentes"
        valores={datos.problemas_frecuentes}
        onChange={(v) => actualizar("problemas_frecuentes", v)}
      />
      <ListaTextos
        etiqueta="Sinónimos"
        valores={datos.sinonimos}
        onChange={(v) => actualizar("sinonimos", v)}
      />
      <ListaTextos
        etiqueta="Keywords"
        valores={datos.keywords}
        onChange={(v) => actualizar("keywords", v)}
      />
      <ListaTextos
        etiqueta="Enlaces oficiales"
        valores={datos.enlaces_oficiales}
        onChange={(v) => actualizar("enlaces_oficiales", v)}
      />
      <ListaFAQ
        valores={datos.preguntas_frecuentes}
        onChange={(v) => actualizar("preguntas_frecuentes", v)}
      />

      {error && <p className="text-sm texto-error">{error}</p>}

      <button type="submit" disabled={!puedeGuardar || guardando} className="boton-primario">
        {guardando ? "Guardando…" : "Guardar"}
      </button>
    </form>
  );
}
```

- [ ] **Step 4: Reescribir `components/ListaTextos.tsx`**

```tsx
"use client";

export function ListaTextos({
  etiqueta,
  valores,
  onChange,
}: {
  etiqueta: string;
  valores: string[];
  onChange: (valores: string[]) => void;
}) {
  function actualizar(indice: number, valor: string) {
    const nuevos = [...valores];
    nuevos[indice] = valor;
    onChange(nuevos);
  }

  function agregar() {
    onChange([...valores, ""]);
  }

  function quitar(indice: number) {
    onChange(valores.filter((_, i) => i !== indice));
  }

  return (
    <div>
      <label className="campo-label">{etiqueta}</label>
      <div className="space-y-2">
        {valores.map((valor, indice) => (
          <div key={indice} className="flex gap-2">
            <input
              type="text"
              value={valor}
              onChange={(e) => actualizar(indice, e.target.value)}
              className="campo-input flex-1"
            />
            <button type="button" onClick={() => quitar(indice)} className="text-sm texto-error">
              Quitar
            </button>
          </div>
        ))}
      </div>
      <button type="button" onClick={agregar} className="enlace-accion mt-2">
        + Agregar
      </button>
    </div>
  );
}
```

- [ ] **Step 5: Reescribir `components/ListaFAQ.tsx`**

```tsx
"use client";

import type { Faq } from "../lib/admin-tramites-api";

export function ListaFAQ({
  valores,
  onChange,
}: {
  valores: Faq[];
  onChange: (valores: Faq[]) => void;
}) {
  function actualizar(indice: number, campo: keyof Faq, valor: string) {
    const nuevos = [...valores];
    nuevos[indice] = { ...nuevos[indice], [campo]: valor };
    onChange(nuevos);
  }

  function agregar() {
    onChange([...valores, { pregunta: "", respuesta: "" }]);
  }

  function quitar(indice: number) {
    onChange(valores.filter((_, i) => i !== indice));
  }

  return (
    <div>
      <label className="campo-label">Preguntas frecuentes</label>
      <div className="space-y-3">
        {valores.map((faq, indice) => (
          <div key={indice} className="tarjeta space-y-1 p-2">
            <input
              type="text"
              placeholder="Pregunta"
              value={faq.pregunta}
              onChange={(e) => actualizar(indice, "pregunta", e.target.value)}
              className="campo-input w-full"
            />
            <input
              type="text"
              placeholder="Respuesta"
              value={faq.respuesta}
              onChange={(e) => actualizar(indice, "respuesta", e.target.value)}
              className="campo-input w-full"
            />
            <button type="button" onClick={() => quitar(indice)} className="text-sm texto-error">
              Quitar
            </button>
          </div>
        ))}
      </div>
      <button type="button" onClick={agregar} className="enlace-accion mt-2">
        + Agregar pregunta
      </button>
    </div>
  );
}
```

- [ ] **Step 6: Correr el test suite existente**

Run: `cd frontend && npx vitest run && npx tsc --noEmit`
Expected: 25 passed, `tsc` sin errores.

- [ ] **Step 7: Commit**

```bash
git add frontend/app/admin/tramites frontend/components/TramiteForm.tsx frontend/components/ListaTextos.tsx frontend/components/ListaFAQ.tsx
git commit -m "feat: paleta de marca en Trámites admin"
```

---

### Task 16: Admin — Contacto (`admin/contacto/page.tsx`, `admin/contacto/[id]/page.tsx`)

**Files:**
- Modify: `frontend/app/admin/contacto/page.tsx`
- Modify: `frontend/app/admin/contacto/[id]/page.tsx`

**Interfaces:**
- No cambia ninguna prop ni firma de función.

- [ ] **Step 1: Reescribir `app/admin/contacto/page.tsx`**

```tsx
"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { listarSolicitudesContacto, type SolicitudContacto } from "../../../lib/admin-contacto-api";

export default function ContactoPage() {
  const [solicitudes, setSolicitudes] = useState<SolicitudContacto[] | null>(null);
  const [error, setError] = useState(false);
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    cargar();
  }, []);

  async function cargar() {
    setCargando(true);
    setError(false);
    try {
      const resultado = await listarSolicitudesContacto();
      setSolicitudes(resultado);
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
        <p className="text-sm texto-error">No se pudo cargar la lista de contacto</p>
        <button onClick={cargar} className="enlace-accion mt-2">
          Reintentar
        </button>
      </div>
    );
  }

  return (
    <div className="p-4">
      <h1 className="mb-4 text-lg font-semibold">Contacto</h1>
      {solicitudes && solicitudes.length === 0 ? (
        <p className="text-sm texto-secundario">Todavía no hay solicitudes de contacto</p>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="tabla-cabecera">
              <th className="p-2">Fecha</th>
              <th className="p-2">Nombre</th>
              <th className="p-2">Trámite</th>
              <th className="p-2">Organismo</th>
              <th className="p-2">Estado</th>
            </tr>
          </thead>
          <tbody>
            {solicitudes!.map((solicitud) => (
              <tr key={solicitud.id} className="tabla-fila">
                <td className="p-2">{new Date(solicitud.creado_en).toLocaleString()}</td>
                <td className="p-2">
                  <Link
                    href={`/admin/contacto/${solicitud.id}`}
                    className="text-macacha-blue hover:underline dark:text-sky-300"
                  >
                    {solicitud.nombre}
                  </Link>
                </td>
                <td className="p-2">{solicitud.tramite_nombre ?? "—"}</td>
                <td className="p-2">{solicitud.organismo ?? "—"}</td>
                <td className="p-2">
                  {solicitud.estado === "resuelto" ? "Resuelto" : "Pendiente"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Reescribir `app/admin/contacto/[id]/page.tsx`**

```tsx
"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import {
  editarEstadoContacto,
  obtenerSolicitudContacto,
  type SolicitudContactoDetalle,
} from "../../../../lib/admin-contacto-api";
import { ConversacionChat } from "../../../../components/ConversacionChat";

export default function ContactoDetallePage() {
  const params = useParams<{ id: string }>();
  const [solicitud, setSolicitud] = useState<SolicitudContactoDetalle | null | undefined>(undefined);
  const [error, setError] = useState(false);
  const [actualizandoEstado, setActualizandoEstado] = useState(false);

  useEffect(() => {
    cargar();
  }, [params.id]);

  async function cargar() {
    setError(false);
    setSolicitud(undefined);
    try {
      const resultado = await obtenerSolicitudContacto(params.id);
      setSolicitud(resultado);
    } catch {
      setError(true);
    }
  }

  async function handleCambiarEstado() {
    if (!solicitud) return;
    const nuevoEstado = solicitud.estado === "pendiente" ? "resuelto" : "pendiente";
    setActualizandoEstado(true);
    try {
      await editarEstadoContacto(solicitud.id, nuevoEstado);
      setSolicitud({ ...solicitud, estado: nuevoEstado });
    } catch {
      setError(true);
    } finally {
      setActualizandoEstado(false);
    }
  }

  if (error) {
    return (
      <div className="p-4">
        <p className="text-sm texto-error">No se pudo cargar la solicitud</p>
        <button onClick={cargar} className="enlace-accion mt-2">
          Reintentar
        </button>
      </div>
    );
  }

  if (solicitud === undefined) {
    return <p className="p-4 text-sm texto-secundario">Cargando…</p>;
  }

  if (solicitud === null) {
    return (
      <div className="p-4">
        <p className="text-sm texto-secundario">Solicitud no encontrada</p>
        <Link href="/admin/contacto" className="enlace-accion">
          Volver a la lista
        </Link>
      </div>
    );
  }

  return (
    <div className="p-4">
      <div className="tarjeta mb-4 max-w-2xl">
        <p><span className="font-semibold">Nombre:</span> {solicitud.nombre}</p>
        <p><span className="font-semibold">Email:</span> {solicitud.email}</p>
        <p><span className="font-semibold">Teléfono:</span> {solicitud.telefono}</p>
        <p><span className="font-semibold">Trámite:</span> {solicitud.tramite_nombre ?? "—"}</p>
        <p className="mt-2"><span className="font-semibold">Consulta:</span></p>
        <p className="whitespace-pre-wrap text-sm">{solicitud.consulta}</p>
        <button
          onClick={handleCambiarEstado}
          disabled={actualizandoEstado}
          className="boton-primario mt-3"
        >
          {solicitud.estado === "pendiente" ? "Marcar como resuelto" : "Marcar como pendiente"}
        </button>
      </div>

      <h2 className="mb-2 text-sm font-semibold texto-secundario">Conversación completa</h2>
      <ConversacionChat mensajes={solicitud.mensajes} />
    </div>
  );
}
```

- [ ] **Step 3: Correr el test suite existente**

Run: `cd frontend && npx vitest run && npx tsc --noEmit`
Expected: 25 passed, `tsc` sin errores.

- [ ] **Step 4: Commit**

```bash
git add frontend/app/admin/contacto
git commit -m "feat: paleta de marca en Contacto admin"
```

---

### Task 17: Admin — Usuarios (`admin/usuarios/page.tsx`, `components/UsuarioForm.tsx`)

**Files:**
- Modify: `frontend/app/admin/usuarios/page.tsx`
- Modify: `frontend/components/UsuarioForm.tsx`

**Interfaces:**
- No cambia ninguna prop ni firma de función.

- [ ] **Step 1: Reescribir `app/admin/usuarios/page.tsx`**

```tsx
"use client";

import { useEffect, useState } from "react";
import { UsuarioForm } from "../../../components/UsuarioForm";
import { listarOrganismos, type Organismo } from "../../../lib/admin-tramites-api";
import {
  crearOrganismo,
  crearUsuario,
  editarUsuario,
  obtenerUsuarios,
  type AdminUsuario,
  type UsuarioFormValores,
} from "../../../lib/admin-usuarios-api";

const VALORES_VACIOS: UsuarioFormValores = {
  email: "",
  password: "",
  rol: "admin_organismo",
  organismo_id: null,
  activo: true,
};

export default function UsuariosPage() {
  const [usuarios, setUsuarios] = useState<AdminUsuario[] | null>(null);
  const [organismos, setOrganismos] = useState<Organismo[]>([]);
  const [error, setError] = useState(false);
  const [cargando, setCargando] = useState(true);
  const [editando, setEditando] = useState<AdminUsuario | "nuevo" | null>(null);
  const [guardando, setGuardando] = useState(false);
  const [errorGuardado, setErrorGuardado] = useState<string | null>(null);
  const [nombreOrganismoNuevo, setNombreOrganismoNuevo] = useState("");
  const [errorOrganismo, setErrorOrganismo] = useState<string | null>(null);

  useEffect(() => {
    cargar();
  }, []);

  async function cargar() {
    setCargando(true);
    setError(false);
    try {
      const [listaUsuarios, listaOrganismos] = await Promise.all([
        obtenerUsuarios(),
        listarOrganismos(),
      ]);
      setUsuarios(listaUsuarios);
      setOrganismos(listaOrganismos);
    } catch {
      setError(true);
    } finally {
      setCargando(false);
    }
  }

  async function handleCrearOrganismo() {
    if (!nombreOrganismoNuevo.trim()) return;
    setErrorOrganismo(null);
    try {
      await crearOrganismo(nombreOrganismoNuevo.trim());
      setNombreOrganismoNuevo("");
      setOrganismos(await listarOrganismos());
    } catch (err) {
      setErrorOrganismo(err instanceof Error ? err.message : "No se pudo crear el organismo");
    }
  }

  async function handleGuardar(datos: UsuarioFormValores) {
    setGuardando(true);
    setErrorGuardado(null);
    try {
      if (editando === "nuevo") {
        await crearUsuario(datos);
      } else if (editando) {
        await editarUsuario(editando.id, datos);
      }
      setEditando(null);
      await cargar();
    } catch (err) {
      setErrorGuardado(err instanceof Error ? err.message : "No se pudo guardar el usuario");
    } finally {
      setGuardando(false);
    }
  }

  function valoresParaEditar(usuario: AdminUsuario): UsuarioFormValores {
    return {
      email: usuario.email,
      password: "",
      rol: usuario.rol,
      organismo_id: organismos.find((o) => o.nombre === usuario.organismo)?.id ?? null,
      activo: usuario.activo,
    };
  }

  if (cargando) {
    return <p className="p-4 text-sm texto-secundario">Cargando…</p>;
  }

  if (error) {
    return (
      <div className="p-4">
        <p className="text-sm texto-error">No se pudo cargar la lista de usuarios</p>
        <button onClick={cargar} className="enlace-accion mt-2">
          Reintentar
        </button>
      </div>
    );
  }

  return (
    <div className="p-4">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-lg font-semibold">Usuarios</h1>
        <button onClick={() => setEditando("nuevo")} className="boton-primario">
          Nuevo usuario
        </button>
      </div>

      <div className="mb-4 flex items-end gap-2">
        <div>
          <label className="campo-label">Nuevo organismo</label>
          <input
            type="text"
            value={nombreOrganismoNuevo}
            onChange={(e) => setNombreOrganismoNuevo(e.target.value)}
            className="campo-input"
          />
        </div>
        <button
          onClick={handleCrearOrganismo}
          className="rounded bg-gray-200 px-3 py-1.5 text-sm hover:bg-gray-300 dark:bg-white/10 dark:hover:bg-white/20"
        >
          Crear organismo
        </button>
        {errorOrganismo && <p className="text-sm texto-error">{errorOrganismo}</p>}
      </div>

      {editando && (
        <div className="mb-4">
          <UsuarioForm
            key={editando === "nuevo" ? "nuevo" : editando.id}
            valoresIniciales={editando === "nuevo" ? VALORES_VACIOS : valoresParaEditar(editando)}
            organismos={organismos}
            esEdicion={editando !== "nuevo"}
            guardando={guardando}
            error={errorGuardado}
            onGuardar={handleGuardar}
            onCancelar={() => setEditando(null)}
          />
        </div>
      )}

      {usuarios && usuarios.length === 0 ? (
        <p className="text-sm texto-secundario">Todavía no hay usuarios cargados</p>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="tabla-cabecera">
              <th className="p-2">Email</th>
              <th className="p-2">Rol</th>
              <th className="p-2">Organismo</th>
              <th className="p-2">Activo</th>
              <th className="p-2"></th>
            </tr>
          </thead>
          <tbody>
            {usuarios!.map((usuario) => (
              <tr key={usuario.id} className="tabla-fila">
                <td className="p-2">{usuario.email}</td>
                <td className="p-2">
                  {usuario.rol === "super_admin" ? "Super admin" : "Admin de organismo"}
                </td>
                <td className="p-2">{usuario.organismo ?? "—"}</td>
                <td className="p-2">{usuario.activo ? "Sí" : "No"}</td>
                <td className="p-2">
                  <button onClick={() => setEditando(usuario)} className="enlace-accion">
                    Editar
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Reescribir `components/UsuarioForm.tsx`**

```tsx
"use client";

import { useState, type FormEvent } from "react";
import type { Organismo } from "../lib/admin-tramites-api";
import type { UsuarioFormValores } from "../lib/admin-usuarios-api";

export function UsuarioForm({
  valoresIniciales,
  organismos,
  esEdicion,
  guardando,
  error,
  onGuardar,
  onCancelar,
}: {
  valoresIniciales: UsuarioFormValores;
  organismos: Organismo[];
  esEdicion: boolean;
  guardando: boolean;
  error: string | null;
  onGuardar: (datos: UsuarioFormValores) => void;
  onCancelar: () => void;
}) {
  const [datos, setDatos] = useState<UsuarioFormValores>(valoresIniciales);

  function actualizar<K extends keyof UsuarioFormValores>(campo: K, valor: UsuarioFormValores[K]) {
    setDatos((anterior) => ({ ...anterior, [campo]: valor }));
  }

  function handleSubmit(evento: FormEvent) {
    evento.preventDefault();
    onGuardar(datos);
  }

  const puedeGuardar =
    datos.email.trim() !== "" &&
    (esEdicion || datos.password.trim().length >= 8) &&
    (datos.rol === "super_admin" || datos.organismo_id !== null);

  return (
    <form onSubmit={handleSubmit} className="tarjeta max-w-md space-y-3">
      <div>
        <label className="campo-label">Email</label>
        <input
          type="email"
          value={datos.email}
          disabled={esEdicion}
          onChange={(e) => actualizar("email", e.target.value)}
          className="campo-input w-full"
        />
      </div>

      <div>
        <label className="campo-label">
          {esEdicion ? "Nueva contraseña (dejar en blanco para no cambiar)" : "Contraseña"}
        </label>
        <input
          type="password"
          value={datos.password}
          onChange={(e) => actualizar("password", e.target.value)}
          className="campo-input w-full"
        />
      </div>

      <div>
        <label className="campo-label">Rol</label>
        <select
          value={datos.rol}
          onChange={(e) => actualizar("rol", e.target.value as UsuarioFormValores["rol"])}
          className="campo-input w-full"
        >
          <option value="admin_organismo">Admin de organismo</option>
          <option value="super_admin">Super admin</option>
        </select>
      </div>

      {datos.rol === "admin_organismo" && (
        <div>
          <label className="campo-label">Organismo</label>
          <select
            value={datos.organismo_id ?? ""}
            onChange={(e) => actualizar("organismo_id", e.target.value ? Number(e.target.value) : null)}
            className="campo-input w-full"
          >
            <option value="">Elegir…</option>
            {organismos.map((organismo) => (
              <option key={organismo.id} value={organismo.id}>
                {organismo.nombre}
              </option>
            ))}
          </select>
        </div>
      )}

      {esEdicion && (
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={datos.activo}
            onChange={(e) => actualizar("activo", e.target.checked)}
          />
          Activo
        </label>
      )}

      {error && <p className="text-sm texto-error">{error}</p>}

      <div className="flex gap-2">
        <button type="submit" disabled={!puedeGuardar || guardando} className="boton-primario">
          {guardando ? "Guardando…" : "Guardar"}
        </button>
        <button type="button" onClick={onCancelar} className="boton-secundario">
          Cancelar
        </button>
      </div>
    </form>
  );
}
```

- [ ] **Step 3: Correr el test suite existente**

Run: `cd frontend && npx vitest run && npx tsc --noEmit`
Expected: 25 passed, `tsc` sin errores.

- [ ] **Step 4: Commit**

```bash
git add frontend/app/admin/usuarios frontend/components/UsuarioForm.tsx
git commit -m "feat: paleta de marca en Usuarios admin"
```

---

### Task 18: Verificación end-to-end (claro/oscuro, chat + admin)

**Files:** ninguno (verificación manual, sin cambios de código salvo fixes puntuales que surjan).

- [ ] **Step 1: Levantar backend + frontend**

Seguir el runbook de la skill `run-macacha` (`.claude/skills/run-macacha/SKILL.md`) para
levantar `backend` (puerto 8000) y `frontend` (puerto 3000) contra la base de datos que
corresponda en el entorno de ejecución.

- [ ] **Step 2: Capturas del chat público — modo claro**

Usando el driver de `run-macacha` (`node ../.claude/skills/run-macacha/driver.mjs`, cwd
`frontend/`): navegar a `http://localhost:3000`, tomar screenshot (`ss chat-claro`), confirmar
visualmente:
- Header de dos franjas: logo de Salta arriba, ícono + "Macacha" + subtítulo abajo, borde
  inferior azul.
- Burbujas y botones con la paleta `macacha.blue`/`macacha.blueDark`.
- Botón de toggle de tema visible en el header.

- [ ] **Step 3: Capturas del chat público — modo oscuro**

`click` en el botón de toggle de tema, `ss chat-oscuro`, confirmar visualmente:
- Fondo con gradiente "aurora" (rosa-púrpura-azul-navy) detrás del header (que debe verse
  transparente, dejando ver el gradiente).
- Logo de Salta dentro de la placa blanca.
- Ícono de Macacha con glow rosa, burbujas de usuario con glow azul, burbujas del asistente con
  aspecto glassmorphism (fondo blanco translúcido).
- Recargar la página (`nav http://localhost:3000`) y confirmar que el modo oscuro persiste
  (sin flash del modo claro antes de aplicarse).

- [ ] **Step 4: Capturas del admin — modo claro y oscuro**

Login con credenciales de prueba (ver "Testing the admin login flow" en el `SKILL.md` de
`run-macacha` — crear un admin descartable, verificar, borrarlo después). Navegar a
`/admin/chats`, `/admin/tramites`, `/admin/contacto`, `/admin/usuarios` (si el rol es
`super_admin`), tomar capturas en claro y oscuro (toggle en el header), confirmar visualmente:
- Header institucional igual que en el chat, pero sin el link "¿Hablar con una persona?".
- Sidebar con el item de la sección activa resaltado.
- En oscuro: fondo `macacha.navy` liso (sin gradiente ni glow), tablas y tarjetas legibles.

- [ ] **Step 5: Revisar la consola del navegador**

`console --errors` en cada pantalla visitada — no debe haber errores nuevos (favicon 404 es
ruido conocido y se ignora, según el `SKILL.md`).

- [ ] **Step 6: Test suite completo + build de producción**

Run: `cd frontend && npx vitest run && npx tsc --noEmit && npm run build`
Expected: 25 tests passed, `tsc` sin errores, `next build` termina sin errores (confirma que
el gradiente CSS, las fuentes y las imágenes en `public/branding/` no rompen el build de
producción).

- [ ] **Step 7: Arreglar lo que surja**

Si alguna captura revela un problema real (contraste insuficiente, header roto en mobile,
imagen no carga), corregirlo directamente en el archivo correspondiente de las tareas 1-17 y
volver a verificar. No es una tarea nueva — es cierre de las tareas anteriores.

- [ ] **Step 8: Commit final si hubo fixes**

```bash
git add -A
git commit -m "fix: ajustes de verificación E2E de la identidad visual"
```

Si no hubo fixes, no hay nada que commitear en este paso.
