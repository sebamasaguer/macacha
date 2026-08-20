# Identidad visual: marca Macacha + institucional Gobierno de Salta

## Contexto y motivación

Macacha no tiene hoy ninguna identidad visual aplicada: el frontend usa
Tailwind sin personalizar (grises y azul genérico de utilidades), sin
tipografía propia, sin logo, sin favicon. El proyecto tiene desde ahora dos
fuentes de identidad que hay que combinar sin mezclarlas:

- **Brandbook de Macacha** (`Macacha identidad Brandbook.pdf`, aportado por
  el usuario): logo de perfil de cabeza con degradado azul→rosa, paleta de 4
  colores, tipografía Montserrat, y mockups de producto con estética oscura
  vibrante (gradiente tipo aurora, glassmorphism, glow).
- **Identidad institucional del Gobierno de Salta** (`salta.gob.ar`):
  escudo + wordmark "SALTA GOBIERNO" en bordó, portal sobrio (blanco, gris,
  acento rojo/bordó), muy distinto en tono al brandbook de producto.

Ambas identidades conviven sin fusionarse: el sello institucional identifica
al organismo dueño del servicio, la marca Macacha identifica el producto en
sí. Este spec cubre cómo se combinan en el chat público y en el panel admin.

## Objetivo

Aplicar la identidad de marca (paleta, tipografía, logo) y el sello
institucional del Gobierno de Salta a todo el frontend (chat público +
panel admin), con soporte de modo claro/oscuro. Es un cambio
fundamentalmente visual — no toca copys ni lógica funcional de ningún flujo
existente.

## Assets de marca

Extraídos y preparados durante el brainstorming (ver
`.superpowers/brainstorm/` de esta sesión para los mockups de referencia):

- **Logo oficial del Gobierno de Salta**: SVG bajado directo de
  `https://www.salta.gob.ar/public/images/logo-gobierno-salta-2023.svg`
  (escudo ovalado verde/celeste + wordmark "SALTA GOBIERNO" en bordó).
  Vector limpio, sin modificar.
- **Logo de Macacha**: el PDF del brandbook no tiene el vector fuente
  (AI/Figma/SVG) — solo páginas rasterizadas a JPEG dentro del PDF. Se
  recortó y se le quitó el fondo blanco (chroma-key) desde la página de
  máxima resolución disponible (2400×1080 por página), quedando tres
  variantes PNG con transparencia:
  - Ícono solo (perfil con degradado azul→rosa) — funciona igual sobre
    fondo claro u oscuro, no necesita variante por tema.
  - Logotipo horizontal (ícono + wordmark "Macacha") en dos variantes de
    color de texto, siguiendo el propio brandbook (sección "02. Logotipo
    Aplicaciones"): texto gris oscuro (`#1a2732`) para fondo claro, texto
    blanco para fondo oscuro. **Pendiente de implementación:** solo se
    extrajo la variante de texto oscuro durante el brainstorming: falta
    recortar del brandbook la variante de texto blanco (existe en el PDF,
    página 3, panel derecho) antes o durante la implementación.
  - Logotipo apilado (ícono arriba, wordmark debajo) — mismo criterio de
    variante de texto por tema.

  Al no ser vector puro, estos PNG tienen algo de ruido de compresión JPEG
  heredado del PDF en los bordes del degradado — aceptable a los tamaños de
  uso previstos (header, favicon, hero del chat), decisión tomada
  explícitamente con el usuario en vez de invertir en trazado vectorial
  (no había forma de instalar `potrace` en el entorno de esta sesión).

- **Favicon**: derivado del ícono solo (sin wordmark).

Ruta de destino en el repo: `frontend/public/branding/`:
  `logo-salta.svg`, `macacha-icon.png`, `macacha-logo-horizontal-light.png`,
  `macacha-logo-horizontal-dark.png`, `macacha-logo-stacked-light.png`,
  `macacha-logo-stacked-dark.png`, y el favicon derivado en
  `frontend/app/favicon.ico` (o `icon.png` vía las convenciones de Next.js
  App Router).

## Sistema de diseño

### Paleta de colores

Tokens Tailwind (`tailwind.config.ts` → `theme.extend.colors.macacha`),
valores exactos del brandbook:

| Token | Hex | Uso |
|---|---|---|
| `macacha.pink` | `#f1446f` | Acento secundario: glow en modo oscuro, badges ("Fuente: ...") |
| `macacha.blue` | `#0078c9` | Acento primario: bordes, links, botones, burbujas de usuario (claro) |
| `macacha.blueDark` | `#005aba` | Extremo oscuro del degradado de botones/burbujas |
| `macacha.navy` | `#1a2732` | Texto oscuro sobre fondo claro / fondo base del modo oscuro |

El bordó/verde/celeste del logo de Salta **no** se extraen como tokens —
el logo se usa tal cual, intocado, como cualquier logo institucional.

### Tipografía

Montserrat vía `next/font/google`, reemplaza la fuente por defecto de
Tailwind (`font-sans`) en todo el sitio (`app/layout.tsx`).

### Modo claro/oscuro

Toggle explícito (no solo `prefers-color-scheme`), con esta mecánica:

- **Persistencia:** `localStorage` (clave `macacha-theme`, valores
  `"light" | "dark"`).
- **Default la primera visita:** `window.matchMedia("(prefers-color-scheme: dark)")`.
- **Aplicación:** clase `dark` en `<html>` (convención de Tailwind
  `darkMode: "class"`), togglable desde un botón en la franja de marca del
  header.
- La función que decide el tema inicial (localStorage → matchMedia →
  fallback `"light"`) se extrae como función pura testeable (p. ej.
  `lib/theme.ts` → `resolverTemaInicial(...)`), siguiendo la convención del
  repo de testear solo funciones puras.
- El toggle se implementa una sola vez (hook/componente compartido) y se
  reutiliza en el header del chat público y en el header del admin — no se
  duplica la lógica.

## Header de dos franjas

Validado visualmente durante el brainstorming (mockups
`header-layout.html`, `header-layout-dark.html`, `chat-completo-toggle.html`
en `.superpowers/brainstorm/`). Mismo patrón en `/` (chat público, dentro de
`app/page.tsx`) y en `/admin/layout.tsx`.

**Franja institucional** (arriba):
- Claro: fondo blanco, borde inferior `1px solid` gris claro, logo de Salta
  a la altura natural (sin recolorear).
- Oscuro: fondo `macacha.navy`, el logo de Salta va dentro de una placa
  blanca (`bg-white rounded-md px-2.5 py-1`) porque el logo institucional no
  tiene variante para fondo oscuro y no se debe recolorear.

**Franja de marca** (debajo, la franja institucional queda siempre por
encima):
- Ícono + wordmark de Macacha, subtítulo ("Asistente virtual de trámites —
  Gobierno de Salta" en el chat; "Admin" en el panel admin), botón de
  toggle de tema, y en el chat público el link "¿Hablar con una persona?"
  que ya existe hoy (se conserva la funcionalidad, cambia solo el estilo).
- Claro: fondo blanco, borde inferior `2px solid macacha.blue`.
- Oscuro (solo en el chat público — ver siguiente sección para el admin):
  fondo transparente sobre el gradiente del contenedor, borde inferior
  `1px solid` blanco al 12% de opacidad.

## Área de chat (`app/page.tsx`, `ChatMessage.tsx`, `ChatInput.tsx`, `ContactoHumanoModal.tsx`)

- **Claro:** fondo `#fafbfc`, burbujas de usuario con degradado
  `macacha.blue` → `macacha.blueDark`, burbujas del asistente blancas con
  borde gris claro.
- **Oscuro:** fondo del contenedor con gradiente radial tipo "aurora"
  (rosa-púrpura-azul-navy, como en el mockup `chat-completo-toggle.html`),
  burbujas de usuario igual que en claro pero con `box-shadow` de glow en
  `macacha.blue`, burbujas del asistente en blanco al 8% de opacidad con
  `backdrop-filter: blur` (glassmorphism), ícono de Macacha del header con
  `drop-shadow` en `macacha.pink`.
- El modal de contacto (`ContactoHumanoModal.tsx`) hereda la paleta clara/
  oscura del contenedor donde se monta, sin gradiente propio — es un
  formulario, prioriza legibilidad.
- Estados existentes que ya maneja el chat (mensaje de error con
  "Reintentar", "escribiendo…", paneles de trámite/ambiguos/frecuentes en el
  aside) se re-estilizan con los mismos tokens, sin cambiar su lógica ni
  contenido.

## Panel admin (`admin/layout.tsx` y pantallas existentes)

Mismo header de dos franjas, misma paleta de tokens, **pero sobrio en
ambos modos** — sin gradiente de fondo, sin glow, sin glassmorphism, porque
es una herramienta de trabajo (tablas, formularios), no la conversación:

- **Claro:** igual al chat en claro (fondo blanco/gris muy claro, acentos
  puntuales de `macacha.blue`).
- **Oscuro:** fondo `macacha.navy` liso (no gradiente), tarjetas/filas con
  fondo blanco al 8% de opacidad y borde blanco al 15% (sin blur), acentos
  en `macacha.pink`/`macacha.blue` para estados (ej. "pendiente" en azul
  claro, "resuelto" en gris).
- Se actualizan las clases Tailwind de las pantallas admin existentes
  (`admin/chats`, `admin/tramites`, `admin/contacto`, `admin/usuarios`,
  `admin/login`) para heredar la paleta — **sin rediseñar su estructura**
  (tablas, listados, formularios siguen igual), solo su piel visual.

## Componentes afectados (archivos a tocar)

- `frontend/tailwind.config.ts` — tokens de color, `darkMode: "class"`.
- `frontend/app/layout.tsx` — Montserrat vía `next/font/google`, favicon.
- `frontend/app/globals.css` — si hace falta CSS base adicional (gradiente
  de fondo del chat oscuro, si no es practicable solo con utilidades).
- `frontend/lib/theme.ts` (nuevo) — función pura `resolverTemaInicial`.
- `frontend/hooks/useTema.ts` (nuevo) — hook compartido de toggle +
  persistencia, usado por ambos headers.
- `frontend/components/HeaderInstitucional.tsx` (nuevo) — franja
  institucional + franja de marca, parametrizable (variante chat vs admin,
  subtítulo, y si muestra el link de contacto).
- `frontend/app/page.tsx` — usa el nuevo header, re-estiliza el layout del
  chat.
- `frontend/components/ChatMessage.tsx`, `ChatInput.tsx`,
  `ContactoHumanoModal.tsx` — re-estilizado con los tokens.
- `frontend/app/admin/layout.tsx` — usa el nuevo header (variante admin) +
  sidebar re-estilizado.
- `frontend/app/admin/login/page.tsx`, `admin/chats/**`, `admin/tramites/**`,
  `admin/contacto/**`, `admin/usuarios/**` — clases Tailwind actualizadas a
  los tokens nuevos, sin cambios estructurales.
- `frontend/public/branding/*`, `frontend/app/favicon.ico` (o
  `icon.png`) — assets nuevos.

## Testing

Cambio mayormente visual (CSS/Tailwind/JSX), fuera del alcance del
pure-function testing que usa este repo, con una excepción: `resolverTemaInicial`
en `lib/theme.ts` es lógica pura (localStorage → matchMedia → default) y se
testea igual que el resto de `lib/*.ts` en este proyecto.

## Fuera de alcance

- No se cambia ningún copy ni la lógica funcional de ningún flujo existente
  (chat, contacto, admin).
- No se rediseña la estructura/IA de las pantallas del admin (siguen siendo
  tablas y formularios) — solo su piel visual.
- No se genera un vector puro (SVG) del logo de Macacha — se usa PNG de alta
  resolución con fondo transparente, extraído del brandbook.
- No se toca la identidad del logo de Salta (colores, proporciones) — se usa
  tal cual viene del sitio oficial.
