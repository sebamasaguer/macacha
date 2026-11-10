# Documentos por organismo para alimentar al agente

## Intención y por qué

Cada organismo tiene información propia que hoy el agente no conoce: reglamentos internos, datos de las delegaciones del interior, etc. Se quiere que el administrador de cada organismo suba hasta 3 documentos con esa información, que el sistema los vectorice y que el agente los use para responder. Los documentos se pueden reemplazar por una versión nueva cuando cambian.

## Objetivos

- El administrador de un organismo sube, reemplaza y borra hasta **3 documentos** de su organismo desde el panel admin.
- Formatos: **PDF y Word (.docx)** con texto. Sin OCR de escaneos.
- Al subir o reemplazar, el texto se extrae, se parte en fragmentos y se vectoriza (mismo modelo que los trámites: `text-embedding-3-small`).
- El agente consulta los documentos **ante cualquier pregunta de la persona**, buscando en los documentos de **todos** los organismos (no solo el del trámite en juego).
- Cuando una respuesta usa contenido de un documento, el agente **lo dice**, indicando de qué documento sale (nombre del documento y organismo).
- Reemplazar un documento deja solo los fragmentos de la versión nueva.

- **Precedencia (decisión del usuario):** si un documento del organismo contradice los datos del trámite oficial (costo, requisito, etc.), el agente **prioriza el documento** y lo cita. El prompt del agente debe reflejarlo.

## No objetivos

- No hay editor de texto en línea: "modificar" significa reemplazar el archivo por una versión nueva.
- No hay OCR ni lectura de imágenes escaneadas.
- No hay historial de versiones anteriores de un documento.
- No hay permiso aparte por administrador: pueden subir **todos** los admin de organismo (decisión del usuario).

## Anti-objetivos

- Un admin de organismo nunca ve, reemplaza ni borra documentos de otro organismo.
- El agente no debe usar un documento sin citarlo.
- No se debe perder el documento anterior si falla la extracción o la vectorización de la versión nueva.

## Restricciones y contexto del proyecto

- Backend FastAPI (`backend/agent/api.py`), Postgres con pgvector, esquema en `backend/db/schema.sql` (bloques idempotentes; se aplica a mano en producción, solo con autorización del usuario).
- Alcance por rol: super_admin elige el organismo; admin_organismo queda fijo en el suyo (patrón `admin.organismo_id` ya usado en formularios).
- La búsqueda existente (`backend/retrieval/hybrid_search.py`) es híbrida (vectores + texto, RRF, rerank LLM) y solo cubre `tramite_chunks`.
- Hoy no hay subida de archivos con multipart ni dependencias para leer PDF/Word.
- El `DATABASE_URL` del `.env` es la base real: las verificaciones van a la base local de pruebas.

## Cómo se decidió (por el usuario)

- Quién sube: todos los administradores de organismo.
- Reemplazo por versión nueva, no edición de texto.
- PDF y Word, casi siempre de texto.
- El agente consulta en toda pregunta y cita el documento de origen.

## Decisiones mías (a revisar)

- **Tablas nuevas**, separadas de los trámites: una de documentos (organismo, nombre, archivo, fecha) y otra de fragmentos con `embedding vector(1536)` y `tsv`, ambas con `organismo_id` accesible. Los fragmentos se borran en cascada con el documento.
- **Tope de 3** validado en el backend (error claro al intentar subir un cuarto), no solo en la pantalla.
- **Tamaño máximo por archivo: 10 MB** (mi propuesta).
- **Extracción:** `pypdf` para PDF y `python-docx` para Word; subida por `multipart/form-data` (agrega `python-multipart`).
- **Fragmentado:** por párrafos/secciones, de unos 800–1000 caracteres con algo de solapamiento (mi propuesta).
- **Búsqueda:** reutilizar el esquema híbrido (vectores + texto + RRF) sobre la tabla nueva, con una **herramienta nueva del agente** (por ejemplo `buscar_documentos`) cuyos resultados incluyen nombre del documento y organismo. El prompt del agente le indica usarla ante cualquier consulta y citar la fuente.
- **Reemplazo seguro:** se procesa el archivo nuevo completo (extraer, fragmentar, vectorizar) y recién entonces se reemplazan los fragmentos en una transacción.
- **Pantalla nueva** en el panel (`/admin/documentos`): lista de los 3 cupos con nombre, fecha, subir, reemplazar y borrar. El super_admin ve un selector de organismo.
- **No se guarda el archivo original ni hay descarga**: solo el texto extraído y los fragmentos (mi decisión; simplifica el esquema y evita depender del disco del despliegue). Se puede agregar después.
- **Tope de 3 por organismo**, no por administrador. Cualquier admin del organismo puede reemplazar o borrar cualquiera de sus documentos. Se registra qué admin subió cada uno. El tope se verifica dentro de una transacción con bloqueo, para que dos subidas simultáneas no pasen el límite.
- **Título editable**: el formulario de subida pide un título para el documento, con el nombre del archivo como valor inicial. La cita del agente usa el título. Al reemplazar se conserva el título salvo que se cambie.
- **Cuándo busca el agente**: el prompt le indica consultar `buscar_documentos` ante toda consulta informativa (no en saludos ni agradecimientos). La herramienta es opcional para el modelo, no forzada por código. Se mantiene la fusión híbrida pero **sin rerank por LLM** en esta herramienta (costo por turno) y con un **puntaje mínimo de relevancia**: lo que no lo alcanza se descarta, para no citar fragmentos irrelevantes. El umbral exacto se calibra al construir.
- **Contenido como dato, no como instrucción**: los fragmentos se entregan al modelo delimitados y marcados como texto citado, con la indicación de ignorar instrucciones que contengan (protección básica contra inyección de prompts, porque el contenido de un organismo llega a las conversaciones de todos).
- **Texto vacío o muy corto**: si la extracción da menos de unos 200 caracteres (por ejemplo un PDF escaneado), la subida se rechaza con un mensaje claro y no se toca la versión anterior.
- **Procesamiento síncrono** con indicador de carga en la pantalla, límite de 10 MB y tope de páginas/fragmentos razonable (se define al construir). Sin estado en segundo plano.
- **Alcance del plan**: llega hasta entregar el bloque SQL en `schema.sql`; aplicarlo en producción lo decide y autoriza el usuario. Las pruebas usan la base local de pruebas. El nombre del organismo en la cita sale de `organismos.nombre`.

## Lo que queda al constructor

- Nombres exactos de tablas, endpoints y componentes.
- Dónde guardar el archivo original (columna `bytea` o disco).
- Detalles de chunking y de prompt del agente.
- Pruebas: extracción de PDF/Word, tope de 3, aislamiento entre organismos, reemplazo transaccional, citación en el agente.
