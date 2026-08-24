# Sistema de botones unificado (sin enlaces de texto) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminar todo enlace de texto del sitio (chat público + admin) — cada elemento accionable, incluida la navegación dentro de tablas, se ve y se comporta como un botón. El botón primario gana un gradiente animado azul→rosa→azul.

**Architecture:** Tres clases de componente en `globals.css` (`boton-primario` con gradiente animado, `boton-secundario` en azul sólido que absorbe lo que hacía `enlace-accion`, `boton-neutro` en gris para las pocas acciones que no deben leerse como afirmativas). El resto del trabajo es renombrar `className` en los ~24 sitios que hoy usan `enlace-accion`, el viejo `boton-secundario`, o un `<Link>`/`<a>` con estilo de texto subrayado — sin tocar ningún `href`, `onClick` ni lógica.

**Tech Stack:** Tailwind CSS 3 (arbitrary values + variants existentes, sin plugins nuevos).

## Global Constraints

- `boton-primario`: gradiente `macacha.blue → macacha.pink → macacha.blue`
  (`bg-gradient-to-r from-macacha-blue via-macacha-pink to-macacha-blue`,
  `bg-[length:200%_auto]`), posición inicial `bg-left`, se desliza a `bg-right` en hover;
  eleva (`hover:-translate-y-0.5`) y agrega sombra (`hover:shadow-lg hover:shadow-macacha-blue/40`)
  en hover; sin gradiente ni elevación cuando `disabled`.
- `boton-secundario`: fondo sólido `macacha.blue`, se oscurece a `macacha.blueDark` en hover, sin
  elevación. Reemplaza tanto `enlace-accion` como todo `<Link>`/`<a>` con
  `text-macacha-blue hover:underline` (o variantes).
- `boton-neutro`: fondo gris (`gray-100` claro / `white/10` oscuro) — solo para "Cancelar"
  (`ContactoHumanoModal`, `UsuarioForm`) y "Cerrar sesión" (`admin/layout.tsx`). Es el mismo
  estilo que hoy tiene `boton-secundario` antes de este plan, solo renombrado.
- Todas las clases de botón llevan `focus-visible:ring-2` (accesibilidad de teclado — no existía
  antes de este plan).
- No se toca `app/admin/layout.tsx`'s `ItemNav` (el sidebar) ni `TabButton` en `app/page.tsx` —
  explícitamente fuera de alcance (ya no son enlaces de texto subrayado).
- No se cambia ningún `href`, `onClick`, comportamiento de navegación, ni copy — solo `className`.
- La clase `enlace-accion` se elimina de `globals.css` una vez que ningún archivo la referencia
  (Task 1 la quita del CSS; Tasks 3-7 quitan sus usos — el orden de ejecución del plan garantiza
  que para cuando se borra del CSS, ya no queda ningún consumidor. Si se ejecutaran fuera de
  orden, Tailwind simplemente no generaría la clase para los usos que quedaran huérfanos,
  produciendo una card sin estilo visible — por eso el orden de tasks importa, ver dependencias
  en cada task).

---

### Task 1: `globals.css` — redefinir clases de botón

**Files:**
- Modify: `frontend/app/globals.css`

**Interfaces:**
- Produces: `.boton-primario` (redefinida, gradiente animado), `.boton-secundario` (redefinida,
  azul sólido), `.boton-neutro` (nueva, gris). Elimina `.enlace-accion`. Consumido por Tasks 2-7.
- No cambia: `.campo-label`, `.campo-input`, `.tarjeta`, `.tabla-cabecera`, `.tabla-fila`,
  `.texto-secundario`, `.texto-error`, `.fondo-degrade-chat`.

- [ ] **Step 1: Reescribir `app/globals.css`**

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
  .boton-primario {
    @apply relative rounded bg-gradient-to-r from-macacha-blue via-macacha-pink to-macacha-blue bg-[length:200%_auto] bg-left px-4 py-2 text-sm font-medium text-white transition-all duration-300 ease-out hover:-translate-y-0.5 hover:bg-right hover:shadow-lg hover:shadow-macacha-blue/40 disabled:translate-y-0 disabled:bg-macacha-blue disabled:bg-none disabled:opacity-50 disabled:shadow-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-macacha-blue focus-visible:ring-offset-2 dark:focus-visible:ring-offset-macacha-navy;
  }
  .boton-secundario {
    @apply rounded bg-macacha-blue px-3 py-1.5 text-sm text-white transition-colors duration-150 hover:bg-macacha-blueDark disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-macacha-blue focus-visible:ring-offset-2 dark:focus-visible:ring-offset-macacha-navy;
  }
  .boton-neutro {
    @apply rounded bg-gray-100 px-3 py-1.5 text-sm text-gray-700 transition-colors duration-150 hover:bg-gray-200 disabled:opacity-50 dark:bg-white/10 dark:text-gray-300 dark:hover:bg-white/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-400 focus-visible:ring-offset-2 dark:focus-visible:ring-offset-macacha-navy;
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

Nota: `bg-left`/`bg-right` son utilidades estándar de Tailwind para `background-position`
(no arbitrary values) — no requieren configuración adicional.

- [ ] **Step 2: Verificar que el build de Tailwind no falla**

Run: `cd frontend && npx tailwindcss -i app/globals.css -o /tmp/tw-check.css && rm /tmp/tw-check.css`
Expected: termina sin error (código de salida 0).

- [ ] **Step 3: Commit**

```bash
git add frontend/app/globals.css
git commit -m "feat: redefine boton-primario (gradiente animado) y boton-secundario, agrega boton-neutro"
```

---

### Task 2: Renombrar el `boton-secundario` existente a `boton-neutro`

**Files:**
- Modify: `frontend/components/ContactoHumanoModal.tsx`
- Modify: `frontend/components/UsuarioForm.tsx`
- Modify: `frontend/app/admin/layout.tsx`

**Interfaces:**
- Consumes: `.boton-neutro` (Task 1).
- No cambia ninguna prop ni comportamiento — solo `className`.

Estos 3 usos son exactamente los que antes de este plan usaban la clase `boton-secundario` (que
Task 1 redefinió como azul sólido) — deben pasar a `boton-neutro` para conservar su aspecto gris
actual, porque el nombre `boton-secundario` ahora significa otra cosa.

- [ ] **Step 1: `components/ContactoHumanoModal.tsx` — botón "Cancelar"**

Find:
```tsx
              <button type="button" onClick={onCerrar} className="boton-secundario">
                Cancelar
              </button>
```

Replace:
```tsx
              <button type="button" onClick={onCerrar} className="boton-neutro">
                Cancelar
              </button>
```

- [ ] **Step 2: `components/UsuarioForm.tsx` — botón "Cancelar"**

Find:
```tsx
        <button type="button" onClick={onCancelar} className="boton-secundario">
          Cancelar
        </button>
```

Replace:
```tsx
        <button type="button" onClick={onCancelar} className="boton-neutro">
          Cancelar
        </button>
```

- [ ] **Step 3: `app/admin/layout.tsx` — botón "Cerrar sesión"**

Find:
```tsx
          <button onClick={handleLogout} className="boton-secundario text-left">
            Cerrar sesión
          </button>
```

Replace:
```tsx
          <button onClick={handleLogout} className="boton-neutro text-left">
            Cerrar sesión
          </button>
```

- [ ] **Step 4: Correr el test suite + tsc**

Run: `cd frontend && npx vitest run && npx tsc --noEmit`
Expected: 28 tests passed, `tsc` sin errores.

- [ ] **Step 5: Commit**

```bash
git add frontend/components/ContactoHumanoModal.tsx frontend/components/UsuarioForm.tsx frontend/app/admin/layout.tsx
git commit -m "refactor: renombra boton-secundario (Cancelar/Cerrar sesión) a boton-neutro"
```

---

### Task 3: Chat público y componentes compartidos — `enlace-accion` → `boton-secundario`

**Files:**
- Modify: `frontend/components/HeaderInstitucional.tsx`
- Modify: `frontend/app/page.tsx`
- Modify: `frontend/components/ChatMessage.tsx`
- Modify: `frontend/components/CopyButton.tsx`
- Modify: `frontend/components/TramiteInfoPanel.tsx`
- Modify: `frontend/components/ConversacionChat.tsx`

**Interfaces:**
- Consumes: `.boton-secundario` (Task 1, ya redefinida en azul sólido).
- No cambia ninguna prop ni comportamiento — solo `className`, salvo el Step 2 (cambio de copy
  explícitamente pedido por el usuario).

- [ ] **Step 1: `components/HeaderInstitucional.tsx` — botón "¿Hablar con una persona?" (con
  ajuste de contraste en modo oscuro)**

Feedback real del usuario tras ver Task 1/2 corriendo: en modo oscuro este botón vive sobre el
gradiente "aurora" (rosa-púrpura-azul) del header transparente — un `boton-secundario` azul
sólido sin más se funde visualmente con ese fondo. Se agrega un glow sutil en dark, coherente
con el mismo lenguaje visual que ya usan la burbuja de usuario y el ícono del header
(`dark:shadow-[...]`).

Find:
```tsx
            <button onClick={linkContacto.onClick} className="enlace-accion">
```

Replace:
```tsx
            <button
              onClick={linkContacto.onClick}
              className="boton-secundario dark:shadow-[0_0_10px_rgba(0,120,201,0.6)]"
            >
```

- [ ] **Step 2: `app/page.tsx` — cambiar el texto del botón a "Comunicarme con el organismo"**

Pedido explícito del usuario: el texto "¿Hablar con una persona?" pasa a
"Comunicarme con el organismo". Es el único cambio de copy de todo este plan — el resto del
plan no toca texto, solo estilo.

Find:
```tsx
          texto: "¿Hablar con una persona?",
```

Replace:
```tsx
          texto: "Comunicarme con el organismo",
```

- [ ] **Step 3: `components/ChatMessage.tsx` — link de fuente citada**

Find:
```tsx
                  className="enlace-accion"
```

Replace:
```tsx
                  className="boton-secundario"
```

- [ ] **Step 4: `components/ChatMessage.tsx` — botón "¿Querés que te ayude una persona?"**

Find:
```tsx
        <button onClick={onPedirContacto} className="enlace-accion mt-2 block">
```

Replace:
```tsx
        <button onClick={onPedirContacto} className="boton-secundario mt-2 block">
```

- [ ] **Step 5: `components/CopyButton.tsx`**

Find:
```tsx
      className="enlace-accion ml-2 text-xs"
```

Replace:
```tsx
      className="boton-secundario ml-2 text-xs"
```

- [ ] **Step 6: `components/TramiteInfoPanel.tsx` — botón "¿Tenés dudas sobre esto?" (`BotonDuda`)**

Find:
```tsx
      className="enlace-accion mt-2 text-xs disabled:opacity-50"
```

Replace:
```tsx
      className="boton-secundario mt-2 text-xs"
```

(Se quita `disabled:opacity-50` explícito porque `.boton-secundario` ya lo incluye.)

- [ ] **Step 7: `components/TramiteInfoPanel.tsx` — enlaces oficiales (caso especial: hoy usan un estilo outline propio, no `enlace-accion`)**

Find:
```tsx
                className="rounded border border-macacha-blue px-3 py-1.5 text-center text-sm text-macacha-blue hover:bg-blue-50 dark:hover:bg-white/10"
```

Replace:
```tsx
                className="boton-secundario text-center"
```

- [ ] **Step 8: `components/ConversacionChat.tsx` — botón "Ver/Ocultar detalle técnico"**

Find:
```tsx
      <button onClick={() => setAbierto(!abierto)} className="enlace-accion">
```

Replace:
```tsx
      <button onClick={() => setAbierto(!abierto)} className="boton-secundario">
```

- [ ] **Step 9: Correr el test suite + tsc**

Run: `cd frontend && npx vitest run && npx tsc --noEmit`
Expected: 28 tests passed, `tsc` sin errores.

- [ ] **Step 10: Commit**

```bash
git add frontend/components/HeaderInstitucional.tsx frontend/app/page.tsx frontend/components/ChatMessage.tsx frontend/components/CopyButton.tsx frontend/components/TramiteInfoPanel.tsx frontend/components/ConversacionChat.tsx
git commit -m "refactor: convierte enlaces de texto en botones + ajusta contraste y copy del botón de contacto (chat público y componentes compartidos)"
```

---

### Task 4: Admin — Chats

**Files:**
- Modify: `frontend/app/admin/chats/page.tsx`
- Modify: `frontend/app/admin/chats/[id]/page.tsx`

**Interfaces:**
- Consumes: `.boton-secundario` (Task 1).
- No cambia ninguna prop ni comportamiento — solo `className`.

- [ ] **Step 1: `app/admin/chats/page.tsx` — botón "Reintentar" (error de carga)**

Find:
```tsx
        <button onClick={cargar} className="enlace-accion mt-2">
```

Replace:
```tsx
        <button onClick={cargar} className="boton-secundario mt-2">
```

- [ ] **Step 2: `app/admin/chats/page.tsx` — link de fecha (navegación al detalle)**

Find:
```tsx
                <Link href={`/admin/chats/${sesion.id}`} className="text-macacha-blue hover:underline dark:text-sky-300">
```

Replace:
```tsx
                <Link href={`/admin/chats/${sesion.id}`} className="boton-secundario">
```

- [ ] **Step 3: `app/admin/chats/page.tsx` — paginación "Anterior" y "Siguiente" (misma clase, dos botones)**

Find (aparece 2 veces, en los botones "Anterior" y "Siguiente" — reemplazar ambas apariciones):
```tsx
          className="text-macacha-blue underline disabled:text-gray-400 disabled:no-underline dark:text-sky-300 dark:disabled:text-gray-500"
```

Replace (ambas apariciones):
```tsx
          className="boton-secundario"
```

- [ ] **Step 4: `app/admin/chats/[id]/page.tsx` — botón "Reintentar"**

Find:
```tsx
        <button onClick={cargar} className="enlace-accion mt-2">
```

Replace:
```tsx
        <button onClick={cargar} className="boton-secundario mt-2">
```

- [ ] **Step 5: `app/admin/chats/[id]/page.tsx` — link "Volver a la lista"**

Find:
```tsx
        <Link href="/admin/chats" className="enlace-accion">
```

Replace:
```tsx
        <Link href="/admin/chats" className="boton-secundario">
```

- [ ] **Step 6: Correr el test suite + tsc**

Run: `cd frontend && npx vitest run && npx tsc --noEmit`
Expected: 28 tests passed (incluye `lib/admin-chats.test.ts`), `tsc` sin errores.

- [ ] **Step 7: Commit**

```bash
git add frontend/app/admin/chats
git commit -m "refactor: convierte enlaces de texto en botones (Chats admin)"
```

---

### Task 5: Admin — Trámites

**Files:**
- Modify: `frontend/app/admin/tramites/page.tsx`
- Modify: `frontend/app/admin/tramites/[id]/page.tsx`
- Modify: `frontend/components/TramiteForm.tsx`
- Modify: `frontend/components/ListaTextos.tsx`
- Modify: `frontend/components/ListaFAQ.tsx`

**Interfaces:**
- Consumes: `.boton-secundario` (Task 1).
- No cambia ninguna prop ni comportamiento — solo `className`.

- [ ] **Step 1: `app/admin/tramites/page.tsx` — botón "Reintentar"**

Find:
```tsx
        <button onClick={cargar} className="enlace-accion mt-2">
```

Replace:
```tsx
        <button onClick={cargar} className="boton-secundario mt-2">
```

- [ ] **Step 2: `app/admin/tramites/page.tsx` — link de ID (navegación al detalle)**

Find:
```tsx
                  <Link href={`/admin/tramites/${tramite.id}`} className="text-macacha-blue hover:underline dark:text-sky-300">
```

Replace:
```tsx
                  <Link href={`/admin/tramites/${tramite.id}`} className="boton-secundario">
```

- [ ] **Step 3: `app/admin/tramites/[id]/page.tsx` — botón "Reintentar"**

Find:
```tsx
        <button onClick={cargar} className="enlace-accion mt-2">
```

Replace:
```tsx
        <button onClick={cargar} className="boton-secundario mt-2">
```

- [ ] **Step 4: `components/TramiteForm.tsx` — botón "Elegir uno existente" / "Otro… (crear nuevo)"**

Find:
```tsx
            className="enlace-accion mt-1"
```

Replace:
```tsx
            className="boton-secundario mt-1"
```

- [ ] **Step 5: `components/ListaTextos.tsx` — botón "+ Agregar"**

Find:
```tsx
      <button type="button" onClick={agregar} className="enlace-accion mt-2">
```

Replace:
```tsx
      <button type="button" onClick={agregar} className="boton-secundario mt-2">
```

- [ ] **Step 6: `components/ListaFAQ.tsx` — botón "+ Agregar pregunta"**

Find:
```tsx
      <button type="button" onClick={agregar} className="enlace-accion mt-2">
```

Replace:
```tsx
      <button type="button" onClick={agregar} className="boton-secundario mt-2">
```

- [ ] **Step 7: Correr el test suite + tsc**

Run: `cd frontend && npx vitest run && npx tsc --noEmit`
Expected: 28 tests passed, `tsc` sin errores.

- [ ] **Step 8: Commit**

```bash
git add frontend/app/admin/tramites frontend/components/TramiteForm.tsx frontend/components/ListaTextos.tsx frontend/components/ListaFAQ.tsx
git commit -m "refactor: convierte enlaces de texto en botones (Trámites admin)"
```

---

### Task 6: Admin — Contacto

**Files:**
- Modify: `frontend/app/admin/contacto/page.tsx`
- Modify: `frontend/app/admin/contacto/[id]/page.tsx`

**Interfaces:**
- Consumes: `.boton-secundario` (Task 1).
- No cambia ninguna prop ni comportamiento — solo `className`.

- [ ] **Step 1: `app/admin/contacto/page.tsx` — botón "Reintentar"**

Find:
```tsx
        <button onClick={cargar} className="enlace-accion mt-2">
```

Replace:
```tsx
        <button onClick={cargar} className="boton-secundario mt-2">
```

- [ ] **Step 2: `app/admin/contacto/page.tsx` — link de nombre (navegación al detalle)**

Find:
```tsx
                    className="text-macacha-blue hover:underline dark:text-sky-300"
```

Replace:
```tsx
                    className="boton-secundario"
```

- [ ] **Step 3: `app/admin/contacto/[id]/page.tsx` — botón "Reintentar"**

Find:
```tsx
        <button onClick={cargar} className="enlace-accion mt-2">
```

Replace:
```tsx
        <button onClick={cargar} className="boton-secundario mt-2">
```

- [ ] **Step 4: `app/admin/contacto/[id]/page.tsx` — link "Volver a la lista"**

Find:
```tsx
        <Link href="/admin/contacto" className="enlace-accion">
```

Replace:
```tsx
        <Link href="/admin/contacto" className="boton-secundario">
```

- [ ] **Step 5: Correr el test suite + tsc**

Run: `cd frontend && npx vitest run && npx tsc --noEmit`
Expected: 28 tests passed, `tsc` sin errores.

- [ ] **Step 6: Commit**

```bash
git add frontend/app/admin/contacto
git commit -m "refactor: convierte enlaces de texto en botones (Contacto admin)"
```

---

### Task 7: Admin — Usuarios

**Files:**
- Modify: `frontend/app/admin/usuarios/page.tsx`

**Interfaces:**
- Consumes: `.boton-secundario` (Task 1).
- No cambia ninguna prop ni comportamiento — solo `className`. (`UsuarioForm.tsx` ya se cubrió
  en Task 2 — su único enlace era el "Cancelar" que pasó a `boton-neutro`.)

- [ ] **Step 1: `app/admin/usuarios/page.tsx` — botón "Reintentar"**

Find:
```tsx
        <button onClick={cargar} className="enlace-accion mt-2">
```

Replace:
```tsx
        <button onClick={cargar} className="boton-secundario mt-2">
```

- [ ] **Step 2: `app/admin/usuarios/page.tsx` — botón "Editar" (fila de tabla)**

Find:
```tsx
                  <button onClick={() => setEditando(usuario)} className="enlace-accion">
```

Replace:
```tsx
                  <button onClick={() => setEditando(usuario)} className="boton-secundario">
```

- [ ] **Step 3: Correr el test suite + tsc**

Run: `cd frontend && npx vitest run && npx tsc --noEmit`
Expected: 28 tests passed, `tsc` sin errores.

- [ ] **Step 4: Commit**

```bash
git add frontend/app/admin/usuarios/page.tsx
git commit -m "refactor: convierte enlaces de texto en botones (Usuarios admin)"
```

---

### Task 8: Verificación end-to-end (gradiente animado, hover/focus, consistencia)

**Files:** ninguno (verificación manual, sin cambios de código salvo fixes puntuales que surjan).

- [ ] **Step 1: Confirmar que no queda ningún uso de `enlace-accion` en el código**

Run: `cd frontend && grep -rn "enlace-accion" --include="*.tsx" . | grep -v node_modules`
Expected: sin resultados (si aparece alguno, es un sitio que este plan no cubrió — agregar el
fix directamente y volver a correr este grep antes de continuar).

- [ ] **Step 2: Levantar backend + frontend**

Seguir el runbook de la skill `run-macacha` (`.claude/skills/run-macacha/SKILL.md`).

- [ ] **Step 3: Captura del botón primario — estado normal y hover**

Vía el driver de `run-macacha`: navegar a `http://localhost:3000`, tomar screenshot del botón
"Enviar" en reposo, luego usar `eval` para simular `:hover` (o mover el mouse sobre el elemento
si el driver lo soporta) y tomar otra captura. Confirmar visualmente el gradiente
azul→rosa desplazado y la elevación/sombra en el estado hover.

- [ ] **Step 4: Recorrido visual del resto de las pantallas**

Navegar por el chat público y las 5 secciones del admin (Chats, Trámites, Contacto, Usuarios,
detalle de cada una), en claro y oscuro. Confirmar que no queda ningún texto subrayado azul
suelto — todo elemento accionable se ve como botón (azul sólido para acciones/navegación, gris
para "Cancelar"/"Cerrar sesión", gradiente para las acciones principales).

- [ ] **Step 5: Revisar la consola del navegador**

`console --errors` en cada pantalla visitada — no debe haber errores nuevos (favicon 404 es
ruido conocido, se ignora).

- [ ] **Step 6: Test suite completo + build de producción**

Run: `cd frontend && npx vitest run && npx tsc --noEmit && npm run build`
Expected: todos los tests passing, `tsc` sin errores, `next build` termina sin errores.

- [ ] **Step 7: Arreglar lo que surja**

Si alguna captura revela un problema real (un enlace de texto que quedó sin convertir, un
botón que se ve roto, contraste insuficiente en `boton-neutro`), corregirlo directamente en el
archivo correspondiente de las tareas 1-7 y volver a verificar.

- [ ] **Step 8: Commit final si hubo fixes**

```bash
git add -A
git commit -m "fix: ajustes de verificación E2E del sistema de botones"
```

Si no hubo fixes, no hay nada que commitear en este paso.
