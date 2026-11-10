# Documentos por organismo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que cada administrador de organismo suba hasta 3 documentos (PDF/Word) que se vectorizan y el agente consulta y cita, con reemplazo por versión nueva.

**Architecture:** Dos tablas nuevas (`organismo_documentos`, `organismo_documento_chunks`) independientes de los trámites. Un módulo extrae texto y fragmenta; un repositorio maneja el tope y el reemplazo transaccional; una búsqueda híbrida propia alimenta una herramienta nueva del agente (`buscar_documentos`). Endpoints `/admin/documentos` multipart y una pantalla `/admin/documentos` calcada del patrón de formularios.

**Tech Stack:** FastAPI, psycopg + pgvector, `pypdf`, `python-docx`, `python-multipart`, Next.js (App Router), vitest, pytest.

**Spec:** `docs/superpowers/specs/2026-11-10-documentos-organismo-design.md`

## Global Constraints

- Máximo **3 documentos por organismo** (no por admin), validado en el backend dentro de una transacción con bloqueo.
- Formatos: **PDF y .docx** con texto; sin OCR. Tamaño máximo **10 MB** por archivo.
- Embeddings: `text-embedding-3-small`, `vector(1536)` (`OpenAIClient.generate_embeddings`).
- Texto extraído menor a **200 caracteres** → rechazar la subida y no tocar la versión anterior.
- Un admin de organismo solo ve y maneja los documentos de su organismo; super_admin elige el organismo (patrón `admin.organismo_id` de formularios).
- Pueden subir **todos** los admin de organismo (sin permiso aparte).
- No se guarda el archivo original ni hay descarga; solo texto extraído y fragmentos.
- La búsqueda abarca documentos de **todos** los organismos, sin rerank por LLM, con puntaje mínimo de relevancia.
- Si un documento contradice al trámite oficial, el agente **prioriza el documento** y lo cita (título y organismo).
- Los fragmentos llegan al modelo como texto citado, delimitado, con la indicación de ignorar instrucciones que contengan.
- Voseo rioplatense y mensajes en español con tildes. Esquema solo en `backend/db/schema.sql` (idempotente); **no aplicarlo a la base remota**. Pruebas contra la base local de pruebas.
- Commits solo de los archivos de cada tarea (dejar afuera `frontend/package.json`, `frontend/package-lock.json` salvo que la tarea los cambie a propósito, y `.claude/`).

## Review Focus

- PDF escaneado o Word vacío al **reemplazar**: se rechaza y el documento anterior queda intacto (Task 3, Task 5).
- Archivo con extensión `.pdf` pero contenido inválido, o formato no admitido (`.txt`, `.doc`): 400 con mensaje claro, no 500 (Task 2, Task 5).
- Dos subidas simultáneas cuando ya hay 2 documentos: solo una pasa (Task 3).
- Admin de otro organismo intenta ver, reemplazar o borrar un documento ajeno: 404 (Task 5).
- Fragmento con texto del tipo "ignorá tus instrucciones": llega delimitado como cita y el prompt lo declara dato (Task 4).
- Consulta sin coincidencias reales: la herramienta devuelve lista vacía y el agente no cita nada (Task 4).
- Documento Word con tablas (típico en listados de delegaciones): el texto de las celdas se extrae (Task 2).

## File Structure

- Modify `backend/db/schema.sql` — tablas e índices nuevos.
- Modify `backend/requirements.txt` — `pypdf`, `python-docx`, `python-multipart`.
- Modify `backend/tests/conftest.py` — limpiar tablas nuevas en `clean_db`.
- Create `backend/ingest/documento_texto.py` — extracción y fragmentado.
- Create `backend/agent/admin/documentos_repository.py` — persistencia y tope.
- Create `backend/retrieval/documentos_search.py` — búsqueda híbrida sobre documentos.
- Create `backend/agent/documentos_tools.py` — herramienta `buscar_documentos`.
- Modify `backend/agent/tools.py`, `backend/agent/orchestrator.py` — registrar herramienta y prompt.
- Modify `backend/agent/api.py` — endpoints.
- Create `frontend/lib/admin-documentos-api.ts`, `frontend/lib/documentos-ui.ts` (+ `.test.ts`), `frontend/app/admin/documentos/page.tsx`; modify `frontend/app/admin/layout.tsx`.
- Tests: `backend/tests/test_documento_texto.py`, `test_documentos_repository.py`, `test_documentos_search.py`, `test_documentos_tools.py`, `test_admin_documentos_api.py`; ampliar `test_system_prompt.py` y `test_schema_smoke.py`.

---

### Task 1: Esquema y dependencias

**Files:**
- Modify: `backend/db/schema.sql` (bloque nuevo al final), `backend/requirements.txt`, `backend/tests/conftest.py` (`clean_db`)
- Test: `backend/tests/test_schema_smoke.py`

**Interfaces:**
- Produces: tabla `organismo_documentos(id UUID PK, organismo_id INT FK organismos, titulo TEXT, nombre_archivo TEXT, subido_por_email TEXT, creado_en TIMESTAMPTZ, actualizado_en TIMESTAMPTZ)` y `organismo_documento_chunks(id UUID PK, documento_id UUID FK ON DELETE CASCADE, orden INT, texto TEXT, embedding vector(1536), tsv tsvector GENERATED 'spanish')` con índices hnsw (coseno), GIN en `tsv` y btree en `documento_id` y `organismo_id`.

- [ ] **Step 1: Test** en `test_schema_smoke.py`: `test_existen_tablas_de_documentos_por_organismo` consulta `information_schema.tables` y espera ambas tablas; `test_borrar_documento_borra_sus_chunks` inserta un documento con un chunk, lo borra y espera 0 chunks.
- [ ] **Step 2:** Correr `cd backend && .venv/bin/pytest tests/test_schema_smoke.py -q` → FALLA (tablas inexistentes).
- [ ] **Step 3:** Agregar el bloque idempotente (`CREATE TABLE IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`) y las tres dependencias a `requirements.txt` (versiones fijadas, `pip install -r`). Agregar `DELETE FROM organismo_documento_chunks` y `DELETE FROM organismo_documentos` a `clean_db`, antes de borrar `admins`. Reaplicar el esquema a la base **de pruebas** local (`psql` contra `TEST_DATABASE_URL`).
- [ ] **Step 4:** Mismo comando → PASA.
- [ ] **Step 5: Commit** — `feat: tablas de documentos por organismo y dependencias de lectura de PDF y Word`.

### Task 2: Extracción de texto y fragmentado

**Files:**
- Create: `backend/ingest/documento_texto.py`
- Test: `backend/tests/test_documento_texto.py`

**Interfaces:**
- Produces:
  - `class DocumentoInvalido(ValueError)` — mensaje en español apto para mostrar.
  - `MINIMO_CARACTERES = 200`, `MAX_FRAGMENTOS = 400`, `MAX_BYTES = 10 * 1024 * 1024`.
  - `extraer_texto(nombre_archivo: str, contenido: bytes) -> str` — decide por extensión (`.pdf`, `.docx`, en minúsculas); extrae párrafos y celdas de tablas en Word; lanza `DocumentoInvalido` por formato no admitido, archivo ilegible, o texto menor a `MINIMO_CARACTERES`.
  - `fragmentar(texto: str, objetivo: int = 900, solapamiento: int = 150) -> list[str]` — parte por párrafos y agrupa hasta ~`objetivo` caracteres; lanza `DocumentoInvalido` si superaría `MAX_FRAGMENTOS`.

- [ ] **Step 1: Tests** (generar los archivos en el test con `reportlab`-free: PDF mínimo armado con `pypdf.PdfWriter` y texto vía una fixture de bytes; docx con `docx.Document()`): `test_extrae_texto_de_docx`, `test_extrae_texto_de_celdas_de_tabla_en_docx`, `test_extrae_texto_de_pdf_con_texto`, `test_rechaza_extension_no_admitida` (`.txt`, `.doc`), `test_rechaza_pdf_con_contenido_invalido`, `test_rechaza_texto_menor_al_minimo` (mensaje menciona que podría ser un escaneo), `test_fragmenta_en_trozos_cercanos_al_objetivo`, `test_fragmentos_consecutivos_comparten_solapamiento`, `test_rechaza_documento_que_excede_el_maximo_de_fragmentos`.
- [ ] **Step 2:** `pytest tests/test_documento_texto.py -q` → FALLA.
- [ ] **Step 3:** Implementar con `pypdf.PdfReader` y `docx.Document`; capturar excepciones de las librerías y relanzar como `DocumentoInvalido`.
- [ ] **Step 4:** Mismo comando → PASA.
- [ ] **Step 5: Commit** — `feat: extracción de texto y fragmentado de documentos`.

### Task 3: Repositorio de documentos (tope y reemplazo transaccional)

**Files:**
- Create: `backend/agent/admin/documentos_repository.py`
- Test: `backend/tests/test_documentos_repository.py`

**Interfaces:**
- Consumes: tablas de Task 1; `fragmentar` de Task 2 (el repositorio recibe fragmentos ya calculados).
- Produces:
  - `MAX_DOCUMENTOS_POR_ORGANISMO = 3`
  - `class TopeDeDocumentos(Exception)`
  - `listar_documentos(conn, organismo_id: int | None) -> list[dict]` — claves `id, organismo_id, organismo, titulo, nombre_archivo, subido_por_email, creado_en, actualizado_en, fragmentos`; `None` lista todos.
  - `obtener_documento(conn, documento_id: str) -> dict | None` (mismas claves).
  - `crear_documento(conn, organismo_id: int, titulo: str, nombre_archivo: str, subido_por_email: str, fragmentos: list[str], embeddings: list[list[float]]) -> dict` — bloquea la fila del organismo (`SELECT ... FOR UPDATE`), cuenta, lanza `TopeDeDocumentos` si ya hay 3, inserta documento y chunks (`orden` desde 0).
  - `reemplazar_contenido(conn, documento_id: str, nombre_archivo: str, subido_por_email: str, fragmentos: list[str], embeddings: list[list[float]], titulo: str | None = None) -> dict | None` — en una transacción borra chunks viejos, inserta nuevos y actualiza `actualizado_en`; `None` si no existe.
  - `renombrar_documento(conn, documento_id: str, titulo: str) -> dict | None`
  - `borrar_documento(conn, documento_id: str) -> bool`

- [ ] **Step 1: Tests** (usan `db_conn`/`clean_db` y los helpers de organismos de los tests existentes): `test_crea_documento_con_sus_fragmentos_en_orden`, `test_rechaza_el_cuarto_documento_del_organismo`, `test_el_tope_es_por_organismo` (otro organismo puede tener sus 3), `test_dos_altas_simultaneas_con_dos_existentes_solo_una_pasa` (dos conexiones y hilos; una recibe `TopeDeDocumentos`), `test_reemplazar_deja_solo_los_fragmentos_nuevos`, `test_reemplazar_conserva_el_titulo_si_no_se_cambia`, `test_si_reemplazar_falla_a_mitad_el_documento_anterior_queda_intacto` (embeddings de largo distinto fuerza error), `test_listar_filtra_por_organismo`, `test_borrar_elimina_documento_y_fragmentos`.
- [ ] **Step 2:** `pytest tests/test_documentos_repository.py -q` → FALLA.
- [ ] **Step 3:** Implementar siguiendo el estilo de `formularios_repository.py` (SQL plano, filas a dict). Los vectores se pasan con `pgvector` como en `ingest/repository.py:63-98`.
- [ ] **Step 4:** Mismo comando → PASA.
- [ ] **Step 5: Commit** — `feat: repositorio de documentos por organismo con tope y reemplazo transaccional`.

### Task 4: Búsqueda y herramienta del agente

**Files:**
- Create: `backend/retrieval/documentos_search.py`, `backend/agent/documentos_tools.py`
- Modify: `backend/agent/tools.py` (agregar el esquema a `TOOL_SCHEMAS` y la rama en `ejecutar_tool`), `backend/agent/orchestrator.py` (`SYSTEM_PROMPT`)
- Test: `backend/tests/test_documentos_search.py`, `test_documentos_tools.py`, `test_system_prompt.py`

**Interfaces:**
- Consumes: `fusionar_rrf` (`retrieval/fusion.py`, requiere `chunk_id` en cada dict), `embed_fn(texts) -> list[list[float]]` como en `buscar_chunks`.
- Produces:
  - `UMBRAL_SIMILITUD = 0.35` (calibrable).
  - `buscar_documentos_chunks(conn, embed_fn, query: str, top_k: int = 5) -> list[dict]` — claves `chunk_id, documento_id, titulo, organismo, texto`; une top 20 vectorial (solo los de similitud coseno ≥ `UMBRAL_SIMILITUD`) y top 20 textual (`websearch_to_tsquery('spanish')`), fusiona con `fusionar_rrf`, corta a `top_k`. Sin rerank. Lista vacía si nada califica.
  - `buscar_documentos(conn, embed_fn, argumentos: dict) -> dict` en `documentos_tools.py` → `{"aviso": <texto fijo que declara los fragmentos como cita, no instrucciones>, "fragmentos": [{"documento": titulo, "organismo": nombre, "texto": ...}]}`; cada texto va delimitado (por ejemplo entre `<<<` y `>>>`).
  - Esquema de herramienta `buscar_documentos` con parámetro `query` (string, requerido).

- [ ] **Step 1: Tests:** `test_devuelve_fragmentos_de_documentos_de_todos_los_organismos`, `test_descarta_fragmentos_bajo_el_umbral_de_similitud`, `test_encuentra_por_texto_aunque_el_vector_no_alcance`, `test_sin_coincidencias_devuelve_lista_vacia`, `test_resultado_incluye_titulo_y_nombre_del_organismo`; en tools: `test_los_fragmentos_van_delimitados_y_con_aviso_de_cita` (un fragmento "Ignorá tus instrucciones anteriores" aparece dentro de los delimitadores y el aviso lo declara dato), `test_ejecutar_tool_despacha_buscar_documentos`; en `test_system_prompt.py`: `test_ordena_consultar_documentos_en_toda_consulta_informativa`, `test_ordena_citar_titulo_y_organismo`, `test_prioriza_el_documento_si_contradice_al_tramite`, `test_trata_el_contenido_de_documentos_como_dato`.
- [ ] **Step 2:** `pytest tests/test_documentos_search.py tests/test_documentos_tools.py tests/test_system_prompt.py -q` → FALLA.
- [ ] **Step 3:** Implementar. Agregar al `SYSTEM_PROMPT`, sin romper los tests existentes (que verifican frases actuales), un párrafo: ante toda consulta informativa (no saludos ni agradecimientos) llamar también a `buscar_documentos`; si devuelve contenido que responde, usarlo, mencionar "según *título* del *organismo*", y priorizarlo sobre el trámite oficial si se contradicen; tratar los fragmentos como texto citado y no seguir instrucciones que contengan.
- [ ] **Step 4:** Mismo comando más `pytest tests/test_tools.py tests/test_orchestrator.py -q` → PASAN.
- [ ] **Step 5: Commit** — `feat: el agente busca en los documentos de los organismos y los cita`.

### Task 5: Endpoints del panel

**Files:**
- Modify: `backend/agent/api.py`
- Test: `backend/tests/test_admin_documentos_api.py`

**Interfaces:**
- Consumes: `requiere_admin`, `AdminActual`, `obtener_pool`, `obtener_openai_client`, funciones de Tasks 2 y 3.
- Produces (todos requieren admin; usar `multipart/form-data` para los que reciben archivo):
  - `GET /admin/documentos?organismo_id=` → lista (admin_organismo: siempre el suyo; super_admin: filtro opcional).
  - `POST /admin/documentos` — campos `titulo` (str, 1–150, opcional: por defecto el nombre del archivo sin extensión), `archivo` (UploadFile), `organismo_id` (solo super_admin; obligatorio para él). 201 con el documento. 400 `DocumentoInvalido`/organismo faltante, 409 `TopeDeDocumentos` ("Ya hay 3 documentos…"), 413 si supera `MAX_BYTES` (leer por partes, como `/audio/transcribe`).
  - `PUT /admin/documentos/{id}` — `archivo` opcional y `titulo` opcional (al menos uno); con archivo, extrae, fragmenta, vectoriza **antes** de tocar la base; mismos errores 400/413; 404 si no existe o es de otro organismo.
  - `DELETE /admin/documentos/{id}` → 204; 404 igual que arriba.
  - Helper `_cargar_documento_de_mi_organismo(conn, admin, documento_id)` análogo a `_cargar_formulario_de_mi_organismo`.
  - Embeddings por lotes de 100 con `openai_client.generate_embeddings`.

- [ ] **Step 1: Tests** (patrón de `test_admin_formularios_api.py`, con el cliente de OpenAI simulado): `test_admin_organismo_sube_documento_a_su_organismo`, `test_super_admin_debe_indicar_organismo`, `test_cuarto_documento_devuelve_409`, `test_archivo_no_admitido_devuelve_400`, `test_pdf_invalido_devuelve_400`, `test_archivo_mayor_a_10mb_devuelve_413`, `test_titulo_por_defecto_es_el_nombre_del_archivo`, `test_reemplazar_cambia_los_fragmentos`, `test_reemplazar_con_escaneo_devuelve_400_y_deja_el_original`, `test_solo_cambiar_titulo`, `test_admin_de_otro_organismo_recibe_404_al_reemplazar_y_borrar`, `test_listar_solo_muestra_los_del_propio_organismo`, `test_sin_sesion_devuelve_401`.
- [ ] **Step 2:** `pytest tests/test_admin_documentos_api.py -q` → FALLA.
- [ ] **Step 3:** Implementar los endpoints junto a los de formularios. Correr extracción y embeddings en hilo (como `audio/transcribe`) para no bloquear el loop.
- [ ] **Step 4:** Mismo comando, luego la suite completa `pytest -q` → PASA.
- [ ] **Step 5: Commit** — `feat: endpoints de documentos por organismo en el panel`.

### Task 6: Pantalla del panel

**Files:**
- Create: `frontend/lib/admin-documentos-api.ts`, `frontend/lib/documentos-ui.ts`, `frontend/lib/documentos-ui.test.ts`, `frontend/app/admin/documentos/page.tsx`
- Modify: `frontend/app/admin/layout.tsx` (ítem de navegación junto a "Formularios", visible para ambos roles)

**Interfaces:**
- Consumes: endpoints de Task 5; tipo `Organismo` de `admin-tramites-api.ts`; `useAdminActual` para rol y organismo.
- Produces:
  - `documentos-ui.ts`: `MAX_DOCUMENTOS = 3`, `MAX_BYTES = 10 * 1024 * 1024`, `validarArchivo(nombre: string, bytes: number): string | null` (null si es válido; mensaje en español si no es `.pdf`/`.docx` o supera el tamaño), `tituloPorDefecto(nombreArchivo: string): string`, `cuposLibres(cantidad: number): number`.
  - `admin-documentos-api.ts`: tipo `DocumentoOrganismo`, `listarDocumentos(organismoId?)`, `subirDocumento(datos: {archivo: File; titulo?: string; organismoId?: number})`, `reemplazarDocumento(id, datos: {archivo?: File; titulo?: string})`, `borrarDocumento(id)`; mismo patrón de `fetch` con `credentials: "include"` y `parsearOLanzar`; sin `Content-Type` manual en los `FormData`.

- [ ] **Step 1: Tests (vitest)** en `documentos-ui.test.ts`: `validarArchivo acepta pdf y docx en mayúsculas o minúsculas`, `validarArchivo rechaza txt y doc`, `validarArchivo rechaza más de 10 MB`, `tituloPorDefecto quita la extensión y conserva tildes`, `cuposLibres nunca devuelve negativos`.
- [ ] **Step 2:** `cd frontend && npx vitest run lib/documentos-ui.test.ts` → FALLA.
- [ ] **Step 3:** Implementar los helpers y el cliente. Página: lista de los 3 cupos (título, archivo, fecha, cantidad de fragmentos, botones Reemplazar y Borrar con confirmación), formulario de subida con título editable (se completa con `tituloPorDefecto`), indicador de carga mientras procesa, errores del backend visibles, botón de subir deshabilitado sin cupos; super_admin con selector de organismo. Reutilizar `PestanaFicha`/estilos de formularios solo si encajan.
- [ ] **Step 4:** `npx vitest run` y `npm run build` → PASAN.
- [ ] **Step 5: Verificación visual** con el skill `run-macacha` contra la base local de pruebas (no la remota): subir un docx, reemplazarlo, borrarlo; captura de la pantalla.
- [ ] **Step 6: Commit** — `feat: pantalla de documentos por organismo en el panel`.

### Task 7: Documentación de despliegue

**Files:**
- Modify: `docs/deploy-dokploy.md`

- [ ] **Step 1:** Agregar la sección del bloque SQL nuevo (aplicarlo a mano antes de desplegar el backend, orden esquema → backend → frontend) y las dependencias nuevas. Dejar dicho que la aplicación a producción la autoriza el usuario.
- [ ] **Step 2: Commit** — `docs: despliegue de los documentos por organismo`.

---

## Self-Review

- **Cobertura del spec:** tope 3 por organismo y transacción (T3), formatos y mínimo de texto (T2/T5), vectorización (T3/T5), consulta en toda pregunta, cita y prioridad del documento (T4), reemplazo seguro (T3/T5), título editable (T5/T6), alcance por rol (T5), contenido como dato (T4), sin archivo original (T1: no hay columna), pantalla (T6), SQL sin aplicar a producción (T7).
- **Consistencia de tipos:** `fragmentos`/`embeddings` son listas paralelas en T3 y T5; `DocumentoInvalido` de T2 se mapea a 400 en T5; `TopeDeDocumentos` de T3 a 409; claves del documento iguales en T3, T5 y `DocumentoOrganismo` de T6.
- **Decisiones del plan a vigilar:** `UMBRAL_SIMILITUD = 0.35`, `MAX_FRAGMENTOS = 400` y fragmentos de ~900 caracteres con 150 de solapamiento son valores iniciales a calibrar con documentos reales.
