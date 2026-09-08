# Reestructurar la interfaz de macacha para igualar la estructura de macacha-vn

## Contexto y motivación

`macacha` (este repo) ya tiene aplicada la identidad de marca (paleta, tipografía, dark mode
tipo "aurora" en el chat) mergeada en `main` — ver
`docs/superpowers/specs/2026-08-20-identidad-visual-design.md`. Esa implementación usa un
**header de dos franjas** compartido entre chat y admin, con toggle de tema claro/oscuro.

`macacha-vn` es una implementación previa y más madura del mismo producto (FastAPI + Jinja2,
sin frontend separado). Al inspeccionar su HTML/CSS servidos realmente (no solo los archivos CSS
sueltos, que incluyen capas legacy) se confirmó que su estructura real es otra:

- **Chat público** (`app/templates/chat.html`, estilos inline en el propio template): sin
  header separado, layout de **3 columnas fijas** (panel de marca / conversación / panel
  contextual), fondo oscuro único con gradiente "aurora" (radial rosa + púrpura sobre
  linear-gradient navy) y glassmorphism — sin toggle de tema, el chat es oscuro siempre.
- **Admin** (`app/templates/base.html` + `admin-v735.css`): **sidebar izquierdo fijo**, sin
  header arriba, agrupado por secciones, con azul genérico de acento y una franja de gradiente
  de marca decorativa en las KPI-cards. Sin dark mode.
- **Login admin**: card centrada con una cabecera en gradiente diagonal, formulario debajo.

Se decidió adoptar esta estructura 1:1 en `macacha`, con la paleta de marca de `macacha`
(`macacha.blue` / `macacha.pink` / `macacha.blueDark` / `macacha.navy`) en vez del azul genérico
que usa `macacha-vn` en su admin. Como consecuencia, el dark mode "tipo producto" ya
implementado deja de ser un modo alternable: pasa a ser el único modo del chat (el admin sigue
siempre claro), y el toggle de tema desaparece de todo el sitio.

## Objetivo

Reestructurar el chat público y el panel admin de `macacha` para que su estructura visual
coincida con la de `macacha-vn`, manteniendo la paleta de marca de `macacha` y sin tocar ninguna
lógica funcional (streaming de chat, paneles de trámite, autenticación, CRUD de admin). Es un
cambio de estructura y piel visual, no de comportamiento.

## Chat público

Reemplaza `frontend/app/page.tsx` (y elimina el uso de `HeaderInstitucional` ahí).

**Estructura de 3 columnas** (grid `minmax(250px,300px) minmax(520px,1fr) minmax(330px,390px)`),
dentro de un "shell" centrado con bordes redondeados grandes, borde sutil blanco/12% y
`backdrop-filter: blur`, sobre un fondo de página con gradiente radial rosa (arriba-izquierda) +
púrpura (abajo-derecha) sobre un linear-gradient navy — igual al `fondo-degrade-chat` que ya
existe para el dark mode actual, ahora aplicado siempre (sin variante clara).

1. **Panel de marca** (nuevo, izquierda): ícono grande de Macacha, "Hola,<br>soy Macacha.", texto
   descriptivo, franja de 4 puntos de color de la paleta de marca, pie de página institucional.
   Se oculta por debajo de 1350px (`hidden xl:flex` o breakpoint Tailwind equivalente) — a ese
   ancho el layout pasa a 2 columnas (conversación + panel contextual).
2. **Panel de conversación** (centro, ya existe): gana un header propio *dentro* del panel (no
   compartido con el admin): ícono chico + "Macacha" + subtítulo + badge "Activa" con punto
   verde, a la derecha. Debajo, los mensajes (`ChatMessage`, sin cambios de lógica) y el compose
   (`ChatInput`) con el botón "Enviar" en gradiente `macacha.pink → macacha.blueDark →
   macacha.blue` (ya existe como `boton-primario`).
3. **Panel contextual** (derecha, ya existe como `TramiteInfoPanel` /
   `TramitesAmbiguosPanel` / `TramitesFrecuentesPanel`, sin cambios de lógica): se envuelve en el
   nuevo panel visual oscuro con blur. Por debajo de 1050px pasa a ser un drawer que se desliza
   desde la derecha (posición fixed, `transform: translateX`), con overlay y botón de cierre —
   accesible con el mismo patrón de tabs que ya existe hoy en mobile (`TabButton`), adaptado a
   abrir/cerrar el drawer en vez de alternar `hidden`/`block`.
   El botón "Comunicarme con el organismo" (hoy en el header) pasa a vivir en un **pie fijo** del
   panel contextual ("Hablar con una persona" en `macacha-vn`) — incluida la lógica que ya abre
   `ContactoHumanoModal`, sin cambios.

`ContactoHumanoModal` no cambia de estructura (spec de identidad visual ya la resolvió como
formulario centrado, prioriza legibilidad) — solo pierde cualquier referencia al header viejo si
la tuviera.

## Admin

`macacha` ya tiene sidebar (`frontend/app/admin/layout.tsx`) — no hace falta construir uno
nuevo, se reestiliza el existente y se quita el header de arriba.

- Se elimina `<HeaderInstitucional subtitulo="Panel de administración" />` de
  `AdminLayoutInner`.
- El `<nav>` (hoy `w-48`, plano, sin logo) pasa a:
  - Franja superior con logo (`macacha-icon.png`) + "Macacha Admin" + "Gobierno de la Provincia
    de Salta", separada por un borde inferior.
  - Los `ItemNav` existentes (Chats/Trámites/Contacto/Usuarios) se agrupan bajo un label
    "Operación" (mayúsculas, gris, tracking amplio) — con un solo grupo alcanza, `macacha` no
    tiene las secciones de "Base RAG" de `macacha-vn` (documentos/fuentes/candidatos no existen
    acá). Cada `ItemNav` gana un ícono a la izquierda del texto (bloque de 19px, reutilizando
    caracteres Unicode simples como en `macacha-vn`, sin agregar una librería de íconos nueva).
  - Pie del sidebar con "Abrir chat" (`<Link href="/">`) encima del botón "Cerrar sesión"
    existente (`boton-neutro`, sin cambios de lógica).
- El acento de nav activo/hover y los botones usan la paleta de marca de `macacha`
  (`macacha.blue` para el fondo activo suave, `macacha.blueDark` para hover), no el azul
  genérico de `macacha-vn`.
- Sin dark mode: se quitan las clases `dark:` del layout y de las pantallas admin.
- Sin dashboard con KPIs: `macacha` no tiene una pantalla `/admin` propia (`/admin` redirige a
  `/admin/chats`) y `macacha-vn` sí — **fuera de alcance**, no se construye un dashboard nuevo en
  este plan.

## Login admin

`frontend/app/admin/login/page.tsx` gana una cabecera en gradiente diagonal
(`macacha.blueDark → macacha.blue`) envolviendo el ícono + "Ingresar" que hoy están sueltos
sobre fondo blanco, con el formulario debajo sobre fondo blanco — mismo patrón que
`.login-head`/`.login-form` de `macacha-vn`, dentro de una card centrada con sombra. Sin cambios
de lógica (`handleSubmit`, mensaje de error).

## Código que se elimina

Como ningún lugar del sitio conserva el toggle claro/oscuro:

- `frontend/components/HeaderInstitucional.tsx` (reemplazado por el header propio del panel de
  conversación en el chat, y por la franja superior del sidebar en el admin).
- `frontend/hooks/useTema.ts`, `frontend/lib/theme.ts`, `frontend/lib/theme.test.ts`.
- `darkMode: "class"` de `tailwind.config.ts` y todas las clases `dark:` introducidas por el
  spec de identidad visual, en los archivos que se tocan en este plan (chat, admin, login). Los
  archivos admin que no se tocan explícitamente (si quedara alguna clase `dark:` residual) se
  limpian igual si aparecen en el camino, ya que quedarían muertas.
- El script anti-flash de tema en `app/layout.tsx` (ya no hay tema que decidir antes de
  hidratar).

## Componentes y archivos afectados

- `frontend/app/page.tsx` — reescritura completa de la estructura (3 columnas).
- `frontend/components/ChatMessage.tsx`, `ChatInput.tsx` — ajuste de clases al nuevo fondo oscuro
  fijo (hoy tienen variantes `dark:`, pasan a ser solo esas variantes sin condicional).
- `frontend/components/TramiteInfoPanel.tsx`, `TramitesAmbiguosPanel.tsx`,
  `TramitesFrecuentesPanel.tsx` — mismo ajuste de clases, sin cambios de props/lógica.
- `frontend/components/ContactoHumanoModal.tsx` — mismo ajuste de clases.
- Nuevo: `frontend/components/PanelMarca.tsx` (panel izquierdo del chat) y
  `frontend/components/PanelContextual.tsx` (wrapper visual del panel derecho + drawer mobile +
  footer de contacto) — extraídos como componentes propios porque no existían antes.
- `frontend/app/admin/layout.tsx` — reescritura del `<nav>`, elimina `HeaderInstitucional`.
- `frontend/app/admin/login/page.tsx` — agrega cabecera con gradiente.
- `frontend/app/admin/chats/**`, `tramites/**`, `contacto/**`, `usuarios/**` — quitan clases
  `dark:` residuales si las tuvieran.
- Elimina: `frontend/components/HeaderInstitucional.tsx`, `frontend/hooks/useTema.ts`,
  `frontend/lib/theme.ts`, `frontend/lib/theme.test.ts`.
- `frontend/tailwind.config.ts` — quita `darkMode: "class"`.
- `frontend/app/layout.tsx` — quita el script anti-flash de tema.

## Testing

Mismo criterio que el spec de identidad visual: cambio visual/estructural (CSS, Tailwind, JSX),
fuera del alcance del pure-function testing de este repo. Al eliminar `lib/theme.ts` se elimina
también su test (`lib/theme.test.ts`) — no se agrega testing de componentes nuevo.

## Fuera de alcance

- No se construye un dashboard `/admin` con KPIs (no existe hoy en `macacha`, `macacha-vn` sí lo
  tiene pero es una pantalla nueva, no una reestructuración de una existente).
- No se agregan las secciones de "Base RAG" (documentos/fuentes/candidatos/sincronización) al
  sidebar admin — `macacha` no tiene esas pantallas.
- No se portan las funcionalidades de audio (micrófono, texto a voz) del chat de `macacha-vn` —
  son funcionalidad nueva, no estructura visual.
- No se cambia ningún flujo funcional: streaming de chat, autenticación de admin, CRUD de
  trámites/contacto/usuarios, envío de contacto humano.
- No se reintroduce un toggle de tema en ningún lugar del sitio.
