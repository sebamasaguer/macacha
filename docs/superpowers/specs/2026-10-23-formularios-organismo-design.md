# Formularios por organismo, completados por el asistente — Diseño

Fecha: 2026-10-23

## Objetivo

Permitir que un usuario de un organismo (por ejemplo, de la Subsecretaría de Trabajo) **cree formularios** desde
el panel de administración y que el **asistente los complete conversando con la persona**: le pide los datos, los
confirma con ella y los guarda automáticamente en una tabla nueva. El **super admin** decide qué usuarios de
organismo pueden crear formularios.

Ejemplo guía: la Subsecretaría de Trabajo crea el formulario "Inscripción a la capacitación" con los campos
nombre, DNI, teléfono y "¿participaría de la capacitación?" (sí/no). Una persona dice que quiere anotarse, el
asistente le pide esos datos y la inscripción queda registrada y visible en el panel.

## Decisiones tomadas

1. **El formulario es independiente del catálogo** y puede vincularse a un trámite de forma opcional. Al crearlo se
   escribe una descripción de **cuándo ofrecerlo**; el asistente lo ofrece cuando la consulta coincide, cuando la
   persona lo pide o cuando aparece el trámite vinculado en la conversación.
2. **Tipos de campo (nueve):** texto, texto largo, DNI, teléfono, email, número, fecha, sí/no y lista de opciones.
3. **Controles de cada formulario:** estado manual (borrador, activo, cerrado), **fecha límite** de cierre opcional,
   **cupo** máximo de respuestas opcional y **un solo envío por persona** (por DNI, si el formulario tiene un campo
   DNI).
4. **Respuestas:** tabla por formulario con una columna por campo, exportación a CSV, aviso por mail a la casilla
   del organismo en cada respuesta, enlace a la conversación de origen y borrado de respuestas (lógico).
5. **Edición con respuestas cargadas:** se pueden cambiar textos, estado, fecha límite y cupo, y **agregar campos
   nuevos opcionales**. No se borran ni se cambian de tipo los campos existentes.
6. **Permisos:** el super admin puede todo; un usuario de organismo **habilitado** crea y gestiona los formularios y
   respuestas de su organismo; uno **no habilitado** los ve y exporta las respuestas, sin editar.
7. **Conversación:** el asistente avisa para qué son los datos y quién los recibe, los pide como le resulte natural,
   **resume y pide confirmación antes de guardar** y permite **cancelar** en cualquier momento.
8. **Una tabla de respuestas genérica** con los valores en JSON, en lugar de una tabla real por formulario: crear
   tablas desde la aplicación obligaría a modificar el esquema en producción cada vez que alguien arma un formulario.

## Fuera de alcance (primera versión)

Campos condicionales, archivos adjuntos, que la persona edite o consulte su respuesta, gráficos y estadísticas,
notificaciones por WhatsApp, borrado de formularios (se cierran) y retención automática de datos.

## Datos

Todos los cambios van en `backend/db/schema.sql`, idempotentes (`IF NOT EXISTS`), como el resto del esquema.

### `admins` (columna nueva)

`puede_crear_formularios BOOLEAN NOT NULL DEFAULT false`. Para `super_admin` el valor guardado es irrelevante: su
permiso efectivo siempre es verdadero.

### `formularios`

| Columna | Detalle |
|---|---|
| `id` | UUID, clave primaria |
| `organismo_id` | `NOT NULL`, referencia a `organismos` |
| `nombre` | texto, obligatorio |
| `descripcion_uso` | texto: cuándo ofrecerlo (lo lee el asistente) |
| `aviso_finalidad` | texto: para qué se usan los datos (el asistente lo dice antes de pedirlos) |
| `tramite_id` | opcional, referencia a `tramites` |
| `estado` | `borrador`, `activo` o `cerrado` |
| `fecha_cierre` | `TIMESTAMPTZ`, opcional |
| `cupo` | entero positivo, opcional |
| `creado_por_email`, `creado_en`, `actualizado_en` | auditoría |

**Formulario abierto** (el único que el asistente puede ofrecer y guardar): `estado = 'activo'` y (`fecha_cierre`
vacía o futura) y (`cupo` vacío o con menos respuestas válidas que el cupo). Se calcula en cada consulta; no hay
tareas programadas.

### `formulario_campos`

`id` (UUID), `formulario_id`, `clave` (identificador estable generado de la etiqueta, único por formulario y que
nunca cambia), `etiqueta`, `tipo`, `obligatorio`, `opciones` (JSON, solo para listas), `orden`.
Límites: hasta 30 campos por formulario, 20 opciones por lista y **un solo campo DNI por formulario** (es el que se usa para la unicidad).

### `formulario_respuestas` (la tabla nueva)

`id` (UUID), `formulario_id`, `session_id` (referencia a `sesiones`), `valores` (JSON: clave del campo → valor ya
normalizado), `dni` (texto normalizado, vacío si el formulario no tiene campo DNI), `creado_en`, `eliminada_en` y
`eliminada_por_email` (borrado lógico).

- **Unicidad:** índice único parcial sobre (`formulario_id`, `dni`) donde `dni` no es nulo y `eliminada_en` es nulo.
  Una respuesta borrada deja libre el DNI y el lugar del cupo.
- **Cupo:** al guardar, se bloquea la fila del formulario (`SELECT … FOR UPDATE`) dentro de la transacción, se cuenta
  y se inserta; así dos personas simultáneas no superan el cupo.

## Permisos

| Quién | Qué puede hacer |
|---|---|
| Super admin | Todo, en todos los organismos; es el único que activa el permiso en otros usuarios |
| Usuario de organismo habilitado | Crear, editar, activar, cerrar formularios y borrar respuestas **de su organismo** |
| Usuario de organismo no habilitado | Ver los formularios de su organismo, ver y exportar sus respuestas; sin editar |

- El permiso se **lee de la base en cada pedido** (dependencia nueva `requiere_puede_gestionar_formularios`), no del
  token: activarlo o retirarlo tiene efecto inmediato.
- Lo que pertenece a otro organismo devuelve **404**, igual que Contacto hoy. Sin sesión, 401; sin permiso de
  edición, 403.
- Un usuario de organismo solo crea formularios para su propio organismo; el super admin elige el organismo.

## Backend

### Endpoints del panel (todos bajo `/admin/formularios`)

| Método y ruta | Permiso | Función |
|---|---|---|
| `GET /admin/formularios` | cualquier admin | Lista paginada (`page`, `page_size`) con estado, respuestas y cupo |
| `POST /admin/formularios` | habilitado | Crea formulario con sus campos |
| `GET /admin/formularios/{id}` | cualquier admin | Detalle con campos |
| `PUT /admin/formularios/{id}` | habilitado | Edita (con las reglas de edición de arriba) |
| `GET /admin/formularios/{id}/respuestas` | cualquier admin | Tabla paginada de respuestas |
| `GET /admin/formularios/{id}/respuestas.csv` | cualquier admin | Exporta todas las respuestas vigentes |
| `GET /admin/formularios/{id}/respuestas/{rid}` | cualquier admin | Una respuesta con la conversación de origen |
| `DELETE /admin/formularios/{id}/respuestas/{rid}` | habilitado | Borrado lógico |

La conversación de origen se devuelve dentro del detalle de la respuesta (como hace Contacto), porque el endpoint
de chats de un usuario de organismo solo muestra conversaciones que citan trámites de su organismo.

Además: `GET /admin/me`, `GET /admin/usuarios`, `POST /admin/usuarios` y `PUT /admin/usuarios/{id}` incluyen
`puede_crear_formularios`; solo el super admin puede modificarlo y solo en usuarios de organismo.

### Validación por tipo (se aplica en el servidor)

| Tipo | Regla |
|---|---|
| texto / texto largo | no vacío si es obligatorio; hasta 200 y 1000 caracteres |
| DNI | se quitan puntos y espacios; 7 u 8 dígitos |
| teléfono | se aceptan `+`, espacios, guiones y paréntesis; 8 a 15 dígitos |
| email | formato válido (se reutiliza la validación de las casillas de contacto) |
| número | entero o decimal; acepta coma o punto |
| fecha | se guarda como `AAAA-MM-DD`; acepta `DD/MM/AAAA` |
| sí/no | verdadero o falso (acepta "sí", "si", "no") |
| lista | debe ser una de las opciones |

### CSV

Una fila por respuesta y una columna por campo, más fecha. Las celdas de texto que empiezan con `=`, `+`, `-` o
`@` se prefijan con una comilla simple para evitar que Excel las interprete como fórmulas.

### Aviso por mail

Al guardar una respuesta se envía un mail a los destinatarios de `resolver_destinatarios(organismo_id)` (la casilla
del organismo) con el nombre del formulario y los datos cargados. Un fallo del envío se registra en el log y **no**
deshace la respuesta, igual que en Contacto.

## El asistente

### Herramientas nuevas (se suman a `TOOL_SCHEMAS`)

- **`buscar_formularios(consulta?, tramite_id?)`**: devuelve hasta 5 formularios **abiertos** con id, nombre,
  organismo, descripción de uso, aviso de finalidad y campos (clave, etiqueta, tipo, obligatorio, opciones).
  Prioriza el vinculado a `tramite_id` y los que coinciden con la consulta por texto. Registra en la sesión qué
  formularios se consultaron.
- **`guardar_respuesta_formulario(formulario_id, valores, confirmado)`**: valida y guarda. Devuelve `{ok: true}` o
  `{ok: false, motivo, errores}` con `motivo` en `no_confirmado`, `formulario_no_consultado`, `cerrado`, `cupo`,
  `duplicado`, `limite_sesion`, `ya_registrada` (la sesión ya envió ese formulario) o `datos_invalidos` (con el error de cada campo para que el asistente repregunte).

### Defensas del servidor

- Rechaza guardar si `confirmado` no es verdadero.
- Solo acepta un `formulario_id` que se haya devuelto antes en esa misma sesión por `buscar_formularios`.
- Máximo **1 envío por formulario y sesión** (un segundo intento devuelve que ya está registrada) y **3 formularios
  distintos por sesión**.
- Vuelve a comprobar que el formulario esté abierto, el cupo y la unicidad dentro de la transacción de guardado.

### Reglas del prompt (se suman a `SYSTEM_PROMPT`)

Cuando la persona pida anotarse, inscribirse o completar algo, o su consulta coincida con un formulario, usar
`buscar_formularios`. Antes de pedir datos, decir qué organismo los recibe y para qué (el aviso de finalidad) y
dejar que decida si sigue. Pedir los campos obligatorios, **resumir lo cargado y pedir confirmación explícita**
antes de guardar, y solo entonces llamar a `guardar_respuesta_formulario` con `confirmado: true`. Si la persona
cancela, no guardar nada. Nunca decir que se guardó algo si la herramienta no devolvió `ok`. No inventar valores.

### Interacción con lo existente

No hay cambios en la pantalla del chat. El asistente puede combinar el formulario con la derivación a una persona
si no puede resolver la consulta. El dictado por voz funciona igual: el DNI dictado pasa por la misma confirmación.

## Panel de administración (frontend)

- **Sección nueva "Formularios"** en la barra lateral, visible para todos los admins.
  - **Lista:** paginada, con nombre, organismo, estado (incluyendo "cerrado por fecha" o "cupo completo"),
    respuestas sobre cupo y fecha límite.
  - **Editor:** nombre, descripción de cuándo ofrecerlo, aviso de finalidad, trámite vinculado (opcional),
    estado, fecha límite, cupo y campos (agregar, ordenar, tipo, obligatorio y opciones), con las reglas de
    edición. Para quien no está habilitado, todo es de solo lectura.
  - **Respuestas:** tabla con una columna por campo, paginada, botón "Exportar CSV", borrar y detalle con la
    conversación de origen.
- **Pantalla de Usuarios:** casilla "Puede crear formularios", visible y editable solo por el super admin y solo
  para usuarios de organismo.
- La lógica pura (reglas de edición, armado de filas) va en `lib/` con vitest, como el resto del frontend.

## Pruebas

- **pytest:** repositorios; permisos (super admin, habilitado, no habilitado, otro organismo, sin sesión); validación
  de cada tipo; DNI duplicado y borrado que libera el lugar; cupo con envíos simultáneos; fecha límite; reglas de
  edición con respuestas; herramientas del asistente (cada `motivo` de rechazo); orquestador con un cliente falso;
  CSV con protección contra fórmulas; mail con fallo.
- **vitest:** lógica de `lib/` del editor y de la tabla.
- **Navegador (Chromium):** crear un formulario, editarlo, ver y exportar respuestas, y el interruptor en Usuarios,
  con un administrador temporal sobre la base local de pruebas.
- **Chat real:** 10 conversaciones contra la base local (pedido directo, consulta ambigua, cancelar a mitad, DNI
  inválido, DNI duplicado, formulario cerrado o con cupo completo, corrección en la confirmación, formulario
  vinculado a un trámite, dos formularios en la misma sesión, y un control en que no corresponde ofrecer nada).
- Suites completas de backend y frontend y `tsc`.

## Despliegue

Cambia el esquema, así que el orden es: **esquema (a mano en la base remota), después backend y por último
frontend**. Si el backend sale antes que el esquema, los endpoints de usuarios y de formularios devuelven 500 (leen
columnas y tablas nuevas). Se documenta en `docs/deploy-dokploy.md`. No hay variables de entorno nuevas.

## Riesgos y decisiones abiertas

- **Datos personales:** el DNI y el teléfono son datos sensibles. El aviso en pantalla es un mínimo y no reemplaza
  una política de privacidad ni el consentimiento que exija la normativa (Ley 25.326); es una decisión
  institucional a confirmar. No hay retención automática: las respuestas se conservan hasta que alguien las borre.
- **Los datos también quedan en el historial del chat:** lo que la persona escribe (incluido el DNI) se guarda en la
  conversación y es visible para quienes pueden ver esos chats (el super admin y los usuarios del organismo cuyo
  trámite se cite). Es el comportamiento actual de todo lo que se escribe en el chat.
- **El modelo puede decir que guardó sin haber guardado.** Pasó con el formulario de contacto. Se mitiga con la regla
  del prompt y se verifica en las conversaciones reales; si aparece, el paso siguiente es un control en el servidor
  como el que ya existe para el formulario de contacto.
- **El modelo puede equivocarse al pasar los datos** (por ejemplo, un dígito del DNI). Por eso la confirmación es
  obligatoria y la validación está en el servidor.
- **Abuso:** el chat es público. El límite por sesión acota los envíos repetidos, pero no impide que alguien abra
  muchas sesiones; si hace falta, el paso siguiente es un límite por IP como el del audio.
- **Cupo y fecha límite sin tareas programadas:** el formulario "se cierra" en cada consulta; no hay un trabajo que
  cambie el estado guardado, por lo que el estado guardado seguirá en "activo" aunque ya esté cerrado de hecho. La
  pantalla y el asistente usan siempre el estado calculado.
