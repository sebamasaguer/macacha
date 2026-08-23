# Sistema de botones unificado (sin enlaces de texto)

## Contexto y motivación

La identidad visual ya aplicada (`docs/superpowers/specs/2026-08-20-identidad-visual-design.md`,
rama `identidad-visual`, sin mergear todavía) dejó una mezcla de dos lenguajes visuales para
elementos accionables: botones sólidos (`boton-primario`/`boton-secundario`) y enlaces de texto
subrayado (`enlace-accion`, más los `<Link>` de navegación de tabla con
`text-macacha-blue hover:underline`). Este spec unifica todo en un solo lenguaje — botón — con
una jerarquía de dos niveles de peso visual, y le da al botón primario una animación de gradiente
en vez de un color plano.

## Objetivo

Eliminar todo enlace de texto del sitio (chat público + admin). Cada elemento accionable —
incluida la navegación dentro de tablas — se ve y se comporta como un botón. El botón primario
tiene un gradiente animado azul→rosa→azul que se desliza al hover, con elevación y sombra.

## Regla general

**Cero enlaces de texto en todo el sitio.** Esto incluye casos que hoy son `<Link>` de
navegación real (ir al detalle de un chat, de un trámite, de una solicitud de contacto) — siguen
siendo técnicamente un `<Link>` de Next.js (la navegación real no cambia), pero su `className`
pasa del estilo "texto azul subrayado" al estilo botón secundario. No se toca ningún href ni
comportamiento de navegación — es un cambio de piel visual, igual que el resto de esta identidad
de marca.

## Jerarquía de dos niveles

Ambos niveles son botones reales (fondo sólido, bordes redondeados, transición). La diferencia
es de peso visual, para que los CTAs principales no compitan con acciones secundarias repetidas
(ej. una tabla de 10 filas con 10 botones "primarios" gritando sería peor que el problema que
esto resuelve).

### Botón primario (`boton-primario`)

Para la acción principal de una pantalla: Enviar, Guardar, Nuevo trámite/usuario, Ingresar.

- Fondo: gradiente `macacha.blue → macacha.pink → macacha.blue` (`background-size: 200% auto`),
  que se desliza (`background-position: right center`) al hover.
- Al hover: eleva (`translateY(-2px)`) y agrega sombra (`box-shadow` en tono `macacha.blue`).
- Transición suave en `background-position`, `transform` y `box-shadow` (no instantánea).
- Estado `disabled`: sin gradiente ni animación, opacidad reducida (como hoy).
- Estado `focus-visible`: anillo de foco visible (accesibilidad de teclado) — no existía en el
  botón anterior, se agrega ahora.

### Botón secundario — dos variantes, dos clases

Para todo lo demás, con dos matices según si la acción es "afirmativa" o "neutra":

**`boton-secundario`** (redefinida — reemplaza `enlace-accion` y todos los `<Link>`/`<a>` con
estilo texto): navegación de tabla, "Reintentar", "Editar", "Ver/Ocultar detalle técnico",
"+ Agregar", "Volver a la lista", enlaces a fuentes citadas, el link "¿Hablar con una persona?"
del header, el botón dentro de una burbuja de chat que sugiere el formulario de contacto.

- Fondo sólido `macacha.blue`, texto blanco.
- Transición suave de color al hover (se oscurece a `macacha.blueDark`), sin elevación — para no
  repetir el efecto del primario y mantener la jerarquía.
- Mismo `focus-visible` que el primario.

**`boton-neutro`** (nueva clase — antes era el estilo gris que ya tenía `boton-secundario`):
únicamente para "Cancelar" (formularios de contacto y de usuario) — la única acción que
explícitamente no debe leerse como una acción afirmativa/azul.

- Fondo gris claro (`gray-100` en claro, `white/10` en oscuro), texto gris — exactamente el
  estilo que hoy tiene `boton-secundario`, solo renombrado para no chocar con la redefinición de
  arriba.

## Casos especiales

- **El botón "¿Querés que te ayude una persona? Completá este formulario" dentro de una burbuja
  de chat** (mensaje del asistente): sigue viviendo dentro de la burbuja, pero pasa de texto
  subrayado a un botón secundario chico — no se agranda la burbuja ni se cambia su lógica.
- **El sidebar del admin** (`ItemNav` en `admin/layout.tsx`, los links "Chats"/"Trámites"/
  "Contacto"/"Usuarios"): **fuera de alcance** — ya no es un enlace de texto subrayado, ya usa un
  estilo de bloque de navegación con fondo resaltado cuando está activo. No se toca.
- **Enlaces a URLs externas** (fuentes citadas en el chat, enlaces oficiales de un trámite): se
  ven como botón secundario igual que el resto — siguen abriendo en pestaña nueva
  (`target="_blank"`), solo cambia el estilo.

## Componentes y archivos afectados

Mismo inventario que tocó la identidad visual original, porque son los mismos consumidores de
`enlace-accion` y de los `<Link>` de navegación con estilo texto:

- `frontend/app/globals.css` — clases `boton-primario` (reescrita), `boton-secundario`
  (reescrita, absorbe lo que hacía `enlace-accion`); se elimina la clase `enlace-accion`.
- `frontend/components/ChatMessage.tsx`, `ContactoHumanoModal.tsx`, `TramiteInfoPanel.tsx`,
  `TramitesAmbiguosPanel.tsx` (sin cambio real — no usa `enlace-accion`, no se toca),
  `TramitesFrecuentesPanel.tsx` (sin cambio real, no se toca), `CopyButton.tsx`,
  `ConversacionChat.tsx`.
- `frontend/components/HeaderInstitucional.tsx` (el link "¿Hablar con una persona?").
- `frontend/app/admin/chats/page.tsx`, `admin/chats/[id]/page.tsx`, `admin/tramites/page.tsx`,
  `admin/tramites/[id]/page.tsx`, `admin/contacto/page.tsx`, `admin/contacto/[id]/page.tsx`,
  `admin/usuarios/page.tsx`, `admin/login/page.tsx`.
- `frontend/components/TramiteForm.tsx`, `UsuarioForm.tsx`, `ListaTextos.tsx`, `ListaFAQ.tsx`.

Se revisa cada uno de estos archivos buscando literalmente la clase `enlace-accion` y los
`<Link>`/`<a>` con `text-macacha-blue hover:underline`, reemplazando por `boton-secundario`.

## Testing

Sin cambios de lógica funcional ni de función pura nueva — sigue siendo un cambio de piel
visual, fuera del alcance del pure-function testing de este repo (igual que el spec de
identidad visual original).

## Fuera de alcance

- No se toca el sidebar del admin (`ItemNav`) — ya cumple la regla.
- No se cambia ningún `href`, comportamiento de navegación, ni lógica funcional de ningún flujo.
- No se agregan variantes de botón adicionales (ej. "peligro"/rojo) — los mensajes de error
  siguen usando `texto-error` como texto plano, no como botón.
