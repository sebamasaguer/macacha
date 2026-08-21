# Avatar 3D de Macacha en el chat público

## Contexto y motivación

El chat público ya tiene aplicada la identidad visual de marca (header institucional, paleta,
modo claro/oscuro — ver `docs/superpowers/specs/2026-08-20-identidad-visual-design.md`). Este
spec agrega una pieza de personalidad adicional: un avatar 3D del logo de Macacha, fijo a la
izquierda del área de chat, que se anima mientras el asistente está generando una respuesta —
dando sensación de "vida" al producto más allá de la burbuja de texto.

## Objetivo

Agregar un avatar 3D (Three.js real, no un efecto CSS pseudo-3D) a la izquierda del chat
público, en desktop, que rota suavemente en reposo y se anima más intensamente (rotación más
rápida, glow más fuerte) mientras Macacha está generando una respuesta.

## Resolución del modelo 3D

No existe un modelo 3D del logo (el brandbook solo tiene el logo 2D rasterizado — ver el spec de
identidad visual). En vez de intentar extruir/esculpir la silueta exacta de la cabeza de perfil
en 3D, la geometría es abstracta pero fiel a la paleta y a la composición del logo: **dos
esferas superpuestas**, replicando los dos círculos que ya forman parte del logotipo 2D:

- Esfera trasera (más grande): material en degradado `macacha.blue` (`#0078c9`) →
  `macacha.blueDark` (`#005aba`).
- Esfera delantera (más chica, desplazada): material en `macacha.pink` (`#f1446f`).

No hay intento de replicar la silueta facial del logo — es una decisión explícita para mantener
el alcance manejable sin depender de un artista 3D o de un trazado vectorial que hoy no existe.

## Arquitectura

### Dependencias nuevas

- `three` (motor 3D/WebGL).
- `@react-three/fiber` (bindings de React para Three.js, compatible con React 19).

Deliberadamente **sin** `@react-three/drei` — no hace falta para una escena tan simple (dos
esferas, una luz, rotación), y sumar un paquete de helpers sin usarlos es sobre-ingeniería
(YAGNI). Peso aproximado de lo que sí se suma: ~150-180KB gzip de Three.js core más un overhead
menor de `@react-three/fiber` — la primera dependencia de peso real que suma este proyecto,
documentado explícitamente porque hasta ahora el frontend no tenía ninguna.

### Componente: `components/AvatarMacacha3D.tsx`

- Client component (`"use client"`), pero **no se importa directamente** desde `app/page.tsx` —
  se carga vía `next/dynamic(() => import("./AvatarMacacha3D"), { ssr: false })`, porque Three.js
  depende de `window`/WebGL, que no existen durante el renderizado en servidor de Next.js.
- Props: `{ hablando: boolean }`.
- Escena: un `<Canvas>` de `@react-three/fiber` conteniendo las dos esferas (mismo grupo,
  rotando junto), una `ambientLight` tenue y una `pointLight` cuyo color e intensidad varían
  según `hablando`.
- Animación vía `useFrame`: en cada frame, incrementa la rotación del grupo a una velocidad que
  depende de `hablando` (más rápida y de mayor amplitud si es `true`).
- Los parámetros numéricos de la animación (velocidad de rotación, intensidad de la luz) **no**
  se hardcodean inline en el componente — se calculan con una función pura importada, ver abajo.

### Función pura: `lib/avatar3d.ts`

```ts
export function parametrosAnimacion(hablando: boolean): {
  velocidadRotacion: number; // radianes por frame
  intensidadLuz: number; // 0-1+
} {
  return hablando
    ? { velocidadRotacion: 0.04, intensidadLuz: 1.4 }
    : { velocidadRotacion: 0.008, intensidadLuz: 0.5 };
}
```

Esta es la única pieza testeable de esta feature, siguiendo la convención del repo de testear
solo funciones puras (`lib/*.ts`) — el componente Three.js en sí no tiene test (no hay contexto
WebGL real en el entorno de test `jsdom`/vitest de este proyecto).

### Integración en `app/page.tsx`

- Nueva columna fija a la izquierda del layout existente (dentro del contenedor
  `mx-auto flex w-full max-w-6xl flex-1...` que ya organiza chat + aside), de ~200px de ancho.
- Visible solo desde el breakpoint `md:` hacia arriba (`hidden md:flex`) — en mobile el layout ya
  usa tabs para alternar entre chat e info del trámite porque no hay espacio horizontal para más
  columnas; el avatar no se muestra ahí.
- Recibe `hablando={enviando}` — el mismo estado booleano que ya expone `useChatStream` y que
  hoy dispara el texto "escribiendo…".

### Robustez

Si el navegador no soporta WebGL (poco común, pero posible en entornos muy restringidos), el
avatar simplemente no debe romper el resto del chat: `@react-three/fiber` lanza un error de
contexto WebGL en ese caso, así que el componente se envuelve en un error boundary local que,
ante cualquier error de renderizado 3D, no muestra nada en esa columna en vez de tirar abajo
toda la página. React no tiene error boundaries funcionales — este boundary es un class
component chico (`components/AvatarErrorBoundary.tsx`), el único class component nuevo de esta
feature, dedicado exclusivamente a envolver el `<Canvas>`.

## Testing

- `lib/avatar3d.ts` → `parametrosAnimacion`: test unitario cubriendo ambos casos
  (`hablando: true` / `hablando: false`), siguiendo el patrón de
  `lib/contacto-tramites.test.ts`.
- Sin test de componente para `AvatarMacacha3D.tsx` (fuera de la convención del repo, y sin
  valor real sin un contexto WebGL).
- Verificación manual (no automatizada) de que el avatar rota más rápido y brilla más mientras
  `enviando` es `true`, y que no aparece en mobile.

## Fuera de alcance

- No se modela la silueta facial exacta del logo en 3D.
- No se agrega interactividad al avatar (click, arrastre, `OrbitControls`) — solo animación
  automática.
- No se agrega el avatar al panel admin ni a ninguna otra pantalla — solo el chat público, solo
  desktop.
- No se sincroniza la animación con el contenido/longitud del texto que llega (no hay "lip
  sync") — es un único estado binario (`hablando` sí/no), no una animación palabra por palabra.
