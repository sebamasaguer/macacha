# Avatar 3D de Macacha en el chat público — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Agregar un avatar 3D (Three.js real) del logo de Macacha a la izquierda del chat público, en desktop, que rota suavemente en reposo y se anima más intensamente mientras el asistente genera una respuesta.

**Architecture:** Un componente `AvatarMacacha3D` (dos esferas Three.js en degradado azul/rosa, animadas vía `@react-three/fiber`'s `useFrame`), cargado con `next/dynamic({ ssr: false })` desde `app/page.tsx` y envuelto en un error boundary local, con los parámetros de animación calculados por una función pura testeable.

**Tech Stack:** `three` + `@react-three/fiber` (sin `@react-three/drei`), Next.js 15 / React 19.

## Global Constraints

- Dependencias exactas a instalar: `three@^0.185.0`, `@react-three/fiber@^9.7.0` (dependencies);
  `@types/three@^0.185.0` (devDependency). No agregar `@react-three/drei` — no hace falta para
  esta escena (dos esferas, una luz, rotación).
- Geometría: dos esferas superpuestas, sin intentar replicar la silueta facial del logo.
  - Esfera trasera, más grande: color `#0078c9` (`macacha.blue`), emissive `#005aba`
    (`macacha.blueDark`).
  - Esfera delantera, más chica y desplazada: color `#f1446f` (`macacha.pink`).
- El componente Three.js **debe** cargarse vía `next/dynamic(() => import(...), { ssr: false })`
  — Three.js usa `window`/WebGL, no puede renderizarse en el servidor.
- El avatar se muestra **solo** en el chat público (`app/page.tsx`), **solo** desde el
  breakpoint `md:` hacia arriba — no en mobile, no en el admin.
- El disparador de la animación "hablando" es el estado `enviando` que ya expone
  `useChatStream(sessionId)` — no se agrega ningún estado nuevo para esto.
- El componente se envuelve en un error boundary local (class component,
  `components/AvatarErrorBoundary.tsx`) para que un fallo de WebGL no rompa el resto del chat.
- No se agrega interactividad (`OrbitControls`, click, arrastre) ni sincronización con el
  contenido/longitud del texto — un único estado binario `hablando`.
- Los parámetros numéricos de la animación (velocidad de rotación, intensidad de luz) viven en
  una función pura (`lib/avatar3d.ts`), no hardcodeados inline en el componente — es la única
  pieza de esta feature testeable, siguiendo la convención del repo de testear solo funciones
  puras.

---

### Task 1: Instalar dependencias de Three.js

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`

**Interfaces:**
- Produces: los paquetes `three`, `@react-three/fiber` (runtime) y `@types/three` (tipos)
  disponibles para las tareas siguientes.

- [ ] **Step 1: Instalar los paquetes exactos**

```bash
cd frontend
npm install three@^0.185.0 @react-three/fiber@^9.7.0
npm install --save-dev @types/three@^0.185.0
```

- [ ] **Step 2: Verificar que quedaron en `package.json` y que el proyecto sigue compilando**

Run: `cd frontend && npx tsc --noEmit`
Expected: sin errores (todavía no hay código nuevo que los use, pero la instalación no debe
romper nada existente).

- [ ] **Step 3: Commit**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "feat: agrega three y @react-three/fiber como dependencias"
```

---

### Task 2: `lib/avatar3d.ts` — función pura de parámetros de animación

**Files:**
- Create: `frontend/lib/avatar3d.ts`
- Test: `frontend/lib/avatar3d.test.ts`

**Interfaces:**
- Produces: `parametrosAnimacion(hablando: boolean): { velocidadRotacion: number; intensidadLuz: number }`,
  consumido por `components/AvatarMacacha3D.tsx` (Task 4).

- [ ] **Step 1: Escribir el test que falla**

```ts
import { describe, expect, it } from "vitest";
import { parametrosAnimacion } from "./avatar3d";

describe("parametrosAnimacion", () => {
  it("devuelve rotación rápida y luz intensa cuando está hablando", () => {
    expect(parametrosAnimacion(true)).toEqual({ velocidadRotacion: 0.04, intensidadLuz: 1.4 });
  });

  it("devuelve rotación lenta y luz tenue en reposo", () => {
    expect(parametrosAnimacion(false)).toEqual({ velocidadRotacion: 0.008, intensidadLuz: 0.5 });
  });
});
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `cd frontend && npx vitest run lib/avatar3d.test.ts`
Expected: FAIL con "Cannot find module './avatar3d'" (el archivo no existe todavía).

- [ ] **Step 3: Implementar `lib/avatar3d.ts`**

```ts
export type ParametrosAnimacion = {
  velocidadRotacion: number;
  intensidadLuz: number;
};

export function parametrosAnimacion(hablando: boolean): ParametrosAnimacion {
  return hablando
    ? { velocidadRotacion: 0.04, intensidadLuz: 1.4 }
    : { velocidadRotacion: 0.008, intensidadLuz: 0.5 };
}
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `cd frontend && npx vitest run lib/avatar3d.test.ts`
Expected: PASS, 2 tests.

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/avatar3d.ts frontend/lib/avatar3d.test.ts
git commit -m "feat: agrega parametrosAnimacion (lógica pura del avatar 3D)"
```

---

### Task 3: `components/AvatarErrorBoundary.tsx`

**Files:**
- Create: `frontend/components/AvatarErrorBoundary.tsx`

**Interfaces:**
- Produces: `<AvatarErrorBoundary>{children}</AvatarErrorBoundary>` — si `children` lanza un
  error de renderizado, no muestra nada (en vez de tirar abajo la página). Consumido por
  `app/page.tsx` (Task 5), envolviendo al `AvatarMacacha3D` cargado dinámicamente.

- [ ] **Step 1: Implementar `components/AvatarErrorBoundary.tsx`**

```tsx
"use client";

import { Component, type ReactNode } from "react";

export class AvatarErrorBoundary extends Component<
  { children: ReactNode },
  { tieneError: boolean }
> {
  constructor(props: { children: ReactNode }) {
    super(props);
    this.state = { tieneError: false };
  }

  static getDerivedStateFromError() {
    return { tieneError: true };
  }

  render() {
    if (this.state.tieneError) {
      return null;
    }
    return this.props.children;
  }
}
```

Nota: React no tiene error boundaries funcionales — esto requiere ser un class component. Es
el único class component de todo este plan, dedicado exclusivamente a este propósito. Sin test
propio (un error boundary sin lógica de negocio no es una función pura, y el repo no testea
componentes React).

- [ ] **Step 2: Verificar que compila**

Run: `cd frontend && npx tsc --noEmit`
Expected: sin errores.

- [ ] **Step 3: Commit**

```bash
git add frontend/components/AvatarErrorBoundary.tsx
git commit -m "feat: agrega AvatarErrorBoundary"
```

---

### Task 4: `components/AvatarMacacha3D.tsx`

**Files:**
- Create: `frontend/components/AvatarMacacha3D.tsx`

**Interfaces:**
- Consumes: `parametrosAnimacion` desde `../lib/avatar3d` (Task 2); `Canvas`, `useFrame` desde
  `@react-three/fiber` (Task 1).
- Produces: `AvatarMacacha3D({ hablando: boolean })` (named export), consumido por
  `app/page.tsx` (Task 5) vía `next/dynamic`.

- [ ] **Step 1: Implementar `components/AvatarMacacha3D.tsx`**

```tsx
"use client";

import { Canvas, useFrame } from "@react-three/fiber";
import { useRef } from "react";
import type { Group } from "three";
import { parametrosAnimacion } from "../lib/avatar3d";

const AZUL = "#0078c9";
const AZUL_OSCURO = "#005aba";
const ROSA = "#f1446f";

function Esferas({ hablando }: { hablando: boolean }) {
  const grupoRef = useRef<Group>(null);
  const { velocidadRotacion, intensidadLuz } = parametrosAnimacion(hablando);

  useFrame(() => {
    if (grupoRef.current) {
      grupoRef.current.rotation.y += velocidadRotacion;
    }
  });

  return (
    <>
      <ambientLight intensity={0.4} />
      <pointLight
        position={[2, 2, 3]}
        intensity={intensidadLuz}
        color={hablando ? ROSA : AZUL}
      />
      <group ref={grupoRef}>
        <mesh position={[0, 0.3, 0]}>
          <sphereGeometry args={[1, 32, 32]} />
          <meshStandardMaterial color={AZUL} emissive={AZUL_OSCURO} emissiveIntensity={0.3} />
        </mesh>
        <mesh position={[0.3, -0.5, 0.4]}>
          <sphereGeometry args={[0.65, 32, 32]} />
          <meshStandardMaterial color={ROSA} emissive={ROSA} emissiveIntensity={0.2} />
        </mesh>
      </group>
    </>
  );
}

export function AvatarMacacha3D({ hablando }: { hablando: boolean }) {
  return (
    <Canvas camera={{ position: [0, 0, 4] }}>
      <Esferas hablando={hablando} />
    </Canvas>
  );
}
```

Sin test propio: es un componente Three.js/WebGL, y este repo no tiene contexto WebGL real en
su entorno de test (`vitest` + `jsdom`) — la única lógica extraíble como función pura
(`parametrosAnimacion`) ya está testeada en Task 2.

- [ ] **Step 2: Verificar que compila**

Run: `cd frontend && npx tsc --noEmit`
Expected: sin errores. Si TypeScript se queja de que no reconoce las etiquetas JSX intrínsecas
de Three.js (`<mesh>`, `<sphereGeometry>`, etc.), confirmar que `@react-three/fiber` está
importado en este archivo (su sola importación registra esos tipos JSX globalmente vía
declaración de módulo) — no hace falta ninguna configuración adicional en `tsconfig.json`.

- [ ] **Step 3: Commit**

```bash
git add frontend/components/AvatarMacacha3D.tsx
git commit -m "feat: agrega AvatarMacacha3D (dos esferas Three.js animadas)"
```

---

### Task 5: Integrar el avatar en `app/page.tsx`

**Files:**
- Modify: `frontend/app/page.tsx`

**Interfaces:**
- Consumes: `AvatarMacacha3D` desde `../components/AvatarMacacha3D` (Task 4, vía
  `next/dynamic`), `AvatarErrorBoundary` desde `../components/AvatarErrorBoundary` (Task 3).
- No cambia ninguna otra interfaz: `ChatInput`, `ChatMessage`, `ContactoHumanoModal`,
  `HeaderInstitucional`, los paneles del `aside`, y `useChatStream`/`usePanelTramite`/
  `useSession` se usan exactamente igual que antes — la única adición es la nueva columna del
  avatar y el import dinámico.

- [ ] **Step 1: Reescribir `app/page.tsx`**

```tsx
"use client";

import dynamic from "next/dynamic";
import { useState } from "react";
import { AvatarErrorBoundary } from "../components/AvatarErrorBoundary";
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

const AvatarMacacha3D = dynamic(
  () => import("../components/AvatarMacacha3D").then((mod) => mod.AvatarMacacha3D),
  { ssr: false }
);

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
        <div className="hidden w-[200px] flex-shrink-0 items-center justify-center border-r border-gray-200 dark:border-white/10 md:flex">
          <AvatarErrorBoundary>
            <AvatarMacacha3D hablando={enviando} />
          </AvatarErrorBoundary>
        </div>

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

- [ ] **Step 2: Correr el test suite existente + tsc**

Run: `cd frontend && npx vitest run && npx tsc --noEmit`
Expected: todos los tests existentes en verde (sin cambios de comportamiento fuera del avatar),
`tsc` sin errores.

- [ ] **Step 3: Commit**

```bash
git add frontend/app/page.tsx
git commit -m "feat: integra el avatar 3D en el chat público"
```

---

### Task 6: Verificación end-to-end (desktop, mobile, transición hablando/idle)

**Files:** ninguno (verificación manual, sin cambios de código salvo fixes puntuales que surjan).

- [ ] **Step 1: Levantar backend + frontend**

Seguir el runbook de la skill `run-macacha` (`.claude/skills/run-macacha/SKILL.md`).

- [ ] **Step 2: Captura en desktop, estado idle**

Vía el driver de `run-macacha`: navegar a `http://localhost:3000` con un viewport de ancho
`md:` o mayor (1440px, el default del driver), esperar a que cargue, tomar screenshot.
Confirmar visualmente que la columna izquierda (~200px) muestra dos esferas 3D en degradado
azul/rosa, con volumen real (sombreado, no un ícono plano).

- [ ] **Step 3: Captura en desktop, estado "hablando"**

Enviar un mensaje de chat real (`fill textarea` + `press Enter`), y mientras el mensaje está en
vuelo (antes de que `wait-gone escribiendo` se cumpla), tomar un screenshot. Comparar contra la
captura de idle: la rotación debe verse más marcada entre dos capturas consecutivas tomadas con
1-2 segundos de diferencia, y el glow debe ser visiblemente rosa/más intenso en vez de azul
tenue.

- [ ] **Step 4: Confirmar que no aparece en mobile**

`eval` para achicar el viewport por debajo de 768px (o relanzar el driver con un viewport
mobile), recargar, tomar screenshot. Confirmar que la columna del avatar no se renderiza (el
layout vuelve al de antes de esta feature: tabs Chat/Info del trámite, sin columna extra a la
izquierda).

- [ ] **Step 5: Revisar la consola del navegador**

`console --errors` en cada pantalla visitada — no debe haber errores nuevos relacionados a
WebGL/Three.js (favicon 404 es ruido conocido, se ignora).

- [ ] **Step 6: Test suite completo + build de producción**

Run: `cd frontend && npx vitest run && npx tsc --noEmit && npm run build`
Expected: todos los tests passing, `tsc` sin errores, `next build` termina sin errores
(confirma que el `next/dynamic({ ssr: false })` no rompe el build de producción — es un punto
real de riesgo, ya que un mal uso de `ssr: false` en un Server Component puede fallar el build).

- [ ] **Step 7: Arreglar lo que surja**

Si alguna captura revela un problema real (el avatar no rota, el glow no cambia, aparece en
mobile, rompe el build), corregirlo directamente en el archivo correspondiente de las tareas
1-5 y volver a verificar.

- [ ] **Step 8: Commit final si hubo fixes**

```bash
git add -A
git commit -m "fix: ajustes de verificación E2E del avatar 3D"
```

Si no hubo fixes, no hay nada que commitear en este paso.
