# Formularios por organismo, completados por el asistente — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que un usuario de organismo habilitado por el super admin cree formularios en el panel, y que el asistente los complete conversando con la persona y guarde las respuestas en una tabla nueva.

**Architecture:** Tres tablas nuevas (`formularios`, `formulario_campos`, `formulario_respuestas` con los valores en JSON) y una columna `admins.puede_crear_formularios`. La validación por tipo y el CSV son módulos puros; el acceso a datos va en un repositorio con bloqueo de fila para el cupo. El panel suma endpoints bajo `/admin/formularios` con el patrón de aislamiento por organismo de Contacto, y el asistente suma dos herramientas (`buscar_formularios`, `guardar_respuesta_formulario`) que validan todo en el servidor. El frontend suma la sección "Formularios" y un interruptor en Usuarios.

**Tech Stack:** FastAPI + psycopg (sin ORM) + PostgreSQL, pytest; Next.js 15 + React 19 + Tailwind, vitest (entorno `node`, solo lógica pura en `lib/`), Puppeteer/Chromium para verificar pantallas.

**Spec:** `docs/superpowers/specs/2026-10-23-formularios-organismo-design.md` (rama `feat/formularios-organismo`).

## Global Constraints

Cada tarea hereda estas reglas. Los valores son los del spec.

- **Rama y árbol:** trabajar en `feat/formularios-organismo`. No commitear ni modificar `frontend/package.json`, `frontend/package-lock.json` ni `.claude/` (cambios ajenos). Commits solo de los archivos de cada tarea. **No hacer push** a ningún remoto.
- **Base de datos:** los tests usan `TEST_DATABASE_URL` (`postgresql://macacha:macacha@localhost:5432/macacha_test`, local). **Nunca tocar la base remota** (`DATABASE_URL` del `.env`) ni aplicarle el esquema: eso lo decide la persona al final. Cada vez que `backend/db/schema.sql` cambie, aplicarlo a la base local de tests con `psql postgresql://macacha:macacha@localhost:5432/macacha_test -f backend/db/schema.sql`.
- **Esquema idempotente** (`IF NOT EXISTS`), como el resto de `schema.sql`. Sin variables de entorno nuevas.
- **Nueve tipos de campo:** `texto`, `texto_largo`, `dni`, `telefono`, `email`, `numero`, `fecha`, `si_no`, `opcion`.
- **Límites:** hasta 30 campos por formulario, 20 opciones por lista (cada una de hasta 80 caracteres), etiqueta de hasta 120, **un solo campo DNI por formulario**; texto hasta 200 caracteres y texto largo hasta 1000.
- **Validación:** DNI = 7 u 8 dígitos (se quitan puntos y espacios); teléfono = 8 a 15 dígitos (acepta `+`, espacios, guiones y paréntesis); email con la validación de `normalizar_email_contacto`; número entero o decimal (coma o punto); fecha guardada como `AAAA-MM-DD` (acepta `DD/MM/AAAA`); sí/no booleano (acepta "sí", "si", "no"); lista = una de las opciones.
- **Estados:** `borrador`, `activo`, `cerrado`. Estado **efectivo**: `borrador`, `cerrado`, `vencido` (pasó `fecha_cierre`), `cupo_completo` (respuestas vigentes ≥ cupo) o `abierto`. Solo un formulario `abierto` se ofrece y se guarda.
- **Permisos:** super admin todo; usuario de organismo **habilitado** crea/edita/cierra formularios y borra respuestas de su organismo; **no habilitado** ve formularios y respuestas de su organismo y exporta CSV, sin editar. Lo ajeno devuelve **404**; sin sesión **401**; sin permiso de edición **403**. El permiso se lee **de la base en cada pedido**, no del token.
- **Edición con respuestas:** se pueden cambiar textos, estado, fecha límite y cupo, agregar opciones a una lista y agregar campos nuevos **opcionales**. No se quitan ni cambian de tipo los campos existentes (→ `ReglaDeEdicion`, HTTP 409).
- **Asistente:** `buscar_formularios` devuelve hasta 5 formularios abiertos; `guardar_respuesta_formulario` exige `confirmado` verdadero, un `formulario_id` consultado antes en la sesión, máximo 1 envío por formulario y sesión y 3 formularios distintos por sesión. Motivos de rechazo: `no_confirmado`, `formulario_no_consultado`, `cerrado`, `cupo`, `duplicado`, `limite_sesion`, `ya_registrada`, `datos_invalidos`.
- **CSV:** las celdas de texto que empiezan con `=`, `+`, `-` o `@` se prefijan con una comilla simple (excepto los campos de tipo número).
- **Mail:** aviso a `resolver_destinatarios(organismo_id)` en cada respuesta; un fallo del envío se registra y **no** deshace la respuesta.
- **Idioma:** textos de pantalla, mensajes de error y prompt en español rioplatense (voseo); identificadores en español como el resto del código.
- **Orden de despliegue** (documentarlo, no ejecutarlo): esquema a mano en la base remota → backend → frontend.

## Review Focus

Condiciones que el spec implica pero que ninguna tarea cubriría por defecto. Cada una tiene su test en la tarea indicada.

1. Dos personas que envían a la vez el **último lugar del cupo**: se guarda una sola y la otra recibe `cupo` (Task 3, con dos conexiones reales).
2. El **mismo DNI escrito de formas distintas** (`30.123.456`, `30 123 456`, `30123456`) cuenta como duplicado, y borrar la respuesta libera el DNI y el lugar del cupo (Task 3).
3. Un usuario habilitado del organismo A que pide por ID un formulario, respuesta, CSV o borrado del organismo B recibe 404 y no ve ni cambia nada (Task 4).
4. Un CSV con celdas que empiezan con `=`, `+`, `-`, `@`, con comas, comillas y saltos de línea queda bien formado y sin fórmulas ejecutables (Task 2).
5. Retirar el permiso a un usuario **con la sesión ya iniciada** le quita la edición en el siguiente pedido, y vincular un formulario a un trámite de **otro organismo** se rechaza (Task 1 y Task 4).
6. El asistente **no guarda** sin confirmación ni con un formulario que no consultó, y no cuenta como guardado algo que el servidor rechazó (Task 5).

## Estructura de archivos

| Archivo | Responsabilidad |
|---|---|
| `backend/db/schema.sql` | Columna `admins.puede_crear_formularios` y las tres tablas nuevas |
| `backend/agent/formularios_validacion.py` (nuevo) | Tipos, límites, claves, normalización y validación por tipo (puro) |
| `backend/agent/formularios_csv.py` (nuevo) | Valores legibles y CSV con protección contra fórmulas (puro) |
| `backend/agent/admin/formularios_repository.py` (nuevo) | CRUD, estado efectivo, edición con reglas, guardado con cupo y DNI único, consultas del asistente |
| `backend/agent/formularios_tools.py` (nuevo) | Herramientas del asistente y aviso por mail |
| `backend/agent/admin/repository.py` | El permiso en altas, ediciones y listados de admins |
| `backend/agent/api.py` | Dependencia de permiso, `/admin/me`, usuarios y endpoints `/admin/formularios` |
| `backend/agent/tools.py`, `backend/agent/orchestrator.py` | Registro de las herramientas, `session_id` en `ejecutar_tool` y reglas del prompt |
| `backend/tests/` | Tests nuevos por módulo y `formularios_helpers.py` compartido |
| `frontend/lib/admin-formularios-api.ts`, `frontend/lib/formularios-ui.ts` (+ test) | Cliente de la API y lógica pura de las pantallas |
| `frontend/components/FormularioEditor.tsx` | Editor de formulario y campos |
| `frontend/app/admin/formularios/**` | Lista, alta, edición, respuestas y detalle de respuesta |
| `frontend/app/admin/layout.tsx`, `frontend/lib/admin-api.ts`, `frontend/lib/admin-usuarios-api.ts`, `frontend/components/UsuarioForm.tsx`, `frontend/app/admin/usuarios/page.tsx` | Navegación, tipo de sesión e interruptor en Usuarios |
| `docs/deploy-dokploy.md` | Nota de despliegue |

---

### Task 1: Esquema y permiso "puede crear formularios"

**Files:**
- Modify: `backend/db/schema.sql`
- Modify: `backend/tests/conftest.py` (limpieza de las tablas nuevas)
- Modify: `backend/tests/test_schema_smoke.py` (tablas nuevas en la lista)
- Modify: `backend/agent/admin/repository.py`
- Modify: `backend/agent/api.py` (`/admin/me`, usuarios y dependencia de permiso)
- Test: `backend/tests/test_admin_formularios_permiso.py` (nuevo)

**Interfaces:**
- Produces: `admin_repository.crear_admin(conn, email, password_hash, rol="admin_organismo", organismo_id=None, puede_crear_formularios=False)`; `admin_repository.editar_admin(conn, admin_id, rol, organismo_id, activo, password_hash=None, puede_crear_formularios=None)` (`None` = no cambiar); `obtener_admin_por_id` y `listar_admins` devuelven la clave `puede_crear_formularios` (bool); `GET /admin/me` devuelve `puede_crear_formularios` **efectivo** (siempre `true` para super admin); dependencia `requiere_gestor_de_formularios` en `agent/api.py` (403 si no tiene permiso; devuelve `AdminActual`).

- [ ] **Step 1: Escribir los tests que fallan**

Crear `backend/tests/test_admin_formularios_permiso.py`:

```python
import pytest
from fastapi.testclient import TestClient

from agent import api
from agent.admin import repository as admin_repository
from agent.admin import security as admin_security
from agent.api import obtener_pool
from ingest import repository as repo


class _FakeConnCtx:
    def __init__(self, conn):
        self._conn = conn

    def __enter__(self):
        return self._conn

    def __exit__(self, *args):
        pass


class _FakePool:
    def __init__(self, conn):
        self._conn = conn

    def connection(self):
        return _FakeConnCtx(self._conn)


def _loguear(client, conn, rol="super_admin", organismo_id=None, email="admin@macacha.gob.ar", puede=False):
    password = "secreta123"
    admin_repository.crear_admin(
        conn, email, admin_security.hash_password(password), rol, organismo_id, puede_crear_formularios=puede
    )
    conn.commit()
    client.post("/admin/login", json={"email": email, "password": password})


@pytest.fixture
def cliente(db_conn, clean_db, monkeypatch):
    monkeypatch.setenv("ADMIN_JWT_SECRET", "secreto-de-test")
    api.app.dependency_overrides[obtener_pool] = lambda: _FakePool(db_conn)
    yield TestClient(api.app, base_url="https://testserver")
    api.app.dependency_overrides.clear()


def _admin(conn, email):
    return admin_repository.obtener_admin_por_email(conn, email)


def test_crear_admin_no_puede_crear_formularios_por_defecto(db_conn, clean_db):
    organismo_id = repo.upsert_organismo(db_conn, "Trabajo")
    admin_repository.crear_admin(db_conn, "a@x.com", "hash", "admin_organismo", organismo_id)

    assert admin_repository.obtener_admin_por_id(db_conn, _admin(db_conn, "a@x.com")["id"])["puede_crear_formularios"] is False


def test_crear_admin_con_permiso(db_conn, clean_db):
    organismo_id = repo.upsert_organismo(db_conn, "Trabajo")
    admin_repository.crear_admin(db_conn, "a@x.com", "hash", "admin_organismo", organismo_id, puede_crear_formularios=True)

    assert admin_repository.obtener_admin_por_id(db_conn, _admin(db_conn, "a@x.com")["id"])["puede_crear_formularios"] is True


def test_volver_a_crear_el_admin_no_pisa_el_permiso(db_conn, clean_db):
    # El comando create_admin se puede volver a correr para cambiar la contraseña.
    organismo_id = repo.upsert_organismo(db_conn, "Trabajo")
    admin_repository.crear_admin(db_conn, "a@x.com", "hash", "admin_organismo", organismo_id, puede_crear_formularios=True)
    admin_repository.crear_admin(db_conn, "a@x.com", "hash2", "admin_organismo", organismo_id)

    assert admin_repository.obtener_admin_por_id(db_conn, _admin(db_conn, "a@x.com")["id"])["puede_crear_formularios"] is True


def test_editar_admin_cambia_el_permiso_y_none_lo_deja_igual(db_conn, clean_db):
    organismo_id = repo.upsert_organismo(db_conn, "Trabajo")
    admin_repository.crear_admin(db_conn, "a@x.com", "hash", "admin_organismo", organismo_id)
    admin_id = _admin(db_conn, "a@x.com")["id"]

    admin_repository.editar_admin(db_conn, admin_id, "admin_organismo", organismo_id, True, puede_crear_formularios=True)
    assert admin_repository.obtener_admin_por_id(db_conn, admin_id)["puede_crear_formularios"] is True

    admin_repository.editar_admin(db_conn, admin_id, "admin_organismo", organismo_id, True)
    assert admin_repository.obtener_admin_por_id(db_conn, admin_id)["puede_crear_formularios"] is True


def test_listar_admins_incluye_el_permiso(db_conn, clean_db):
    organismo_id = repo.upsert_organismo(db_conn, "Trabajo")
    admin_repository.crear_admin(db_conn, "a@x.com", "hash", "admin_organismo", organismo_id, puede_crear_formularios=True)

    assert admin_repository.listar_admins(db_conn)[0]["puede_crear_formularios"] is True


def test_admin_me_super_admin_siempre_puede(cliente, db_conn):
    _loguear(cliente, db_conn)

    assert cliente.get("/admin/me").json()["puede_crear_formularios"] is True


@pytest.mark.parametrize("puede", [False, True])
def test_admin_me_organismo_refleja_el_permiso(cliente, db_conn, puede):
    organismo_id = repo.upsert_organismo(db_conn, "Trabajo")
    _loguear(cliente, db_conn, rol="admin_organismo", organismo_id=organismo_id, puede=puede)

    assert cliente.get("/admin/me").json()["puede_crear_formularios"] is puede


def test_super_admin_habilita_y_deshabilita_desde_usuarios(cliente, db_conn):
    organismo_id = repo.upsert_organismo(db_conn, "Trabajo")
    admin_repository.crear_admin(db_conn, "org@x.com", "hash", "admin_organismo", organismo_id)
    db_conn.commit()
    _loguear(cliente, db_conn)
    admin_id = _admin(db_conn, "org@x.com")["id"]
    cuerpo = {"rol": "admin_organismo", "organismo_id": organismo_id, "activo": True, "puede_crear_formularios": True}

    assert cliente.put(f"/admin/usuarios/{admin_id}", json=cuerpo).status_code == 200
    assert next(u for u in cliente.get("/admin/usuarios").json() if u["email"] == "org@x.com")["puede_crear_formularios"] is True

    cuerpo["puede_crear_formularios"] = False
    cliente.put(f"/admin/usuarios/{admin_id}", json=cuerpo)
    assert next(u for u in cliente.get("/admin/usuarios").json() if u["email"] == "org@x.com")["puede_crear_formularios"] is False


def test_el_permiso_no_se_guarda_en_un_super_admin(cliente, db_conn):
    admin_repository.crear_admin(db_conn, "otro@x.com", "hash", "super_admin", None)
    db_conn.commit()
    _loguear(cliente, db_conn)
    admin_id = _admin(db_conn, "otro@x.com")["id"]

    cliente.put(
        f"/admin/usuarios/{admin_id}",
        json={"rol": "super_admin", "organismo_id": None, "activo": True, "puede_crear_formularios": True},
    )

    assert admin_repository.obtener_admin_por_id(db_conn, admin_id)["puede_crear_formularios"] is False


def test_crear_usuario_de_organismo_con_permiso(cliente, db_conn):
    organismo_id = repo.upsert_organismo(db_conn, "Trabajo")
    _loguear(cliente, db_conn)

    respuesta = cliente.post(
        "/admin/usuarios",
        json={
            "email": "nuevo@x.com",
            "password": "secreta123",
            "rol": "admin_organismo",
            "organismo_id": organismo_id,
            "puede_crear_formularios": True,
        },
    )

    assert respuesta.status_code == 200
    assert admin_repository.obtener_admin_por_id(db_conn, _admin(db_conn, "nuevo@x.com")["id"])["puede_crear_formularios"] is True


def test_retirar_el_permiso_se_nota_sin_volver_a_iniciar_sesion(cliente, db_conn):
    organismo_id = repo.upsert_organismo(db_conn, "Trabajo")
    _loguear(cliente, db_conn, rol="admin_organismo", organismo_id=organismo_id, puede=True)
    assert cliente.get("/admin/me").json()["puede_crear_formularios"] is True

    admin_id = _admin(db_conn, "admin@macacha.gob.ar")["id"]
    admin_repository.editar_admin(db_conn, admin_id, "admin_organismo", organismo_id, True, puede_crear_formularios=False)
    db_conn.commit()

    assert cliente.get("/admin/me").json()["puede_crear_formularios"] is False
```

En `backend/tests/test_schema_smoke.py`, agregar a la lista de tablas esperadas (después de `"solicitudes_contacto",`):

```python
            "formularios",
            "formulario_campos",
            "formulario_respuestas",
```

y agregar al final del archivo:

```python


def test_admins_tiene_la_columna_puede_crear_formularios(db_conn):
    with db_conn.cursor() as cur:
        cur.execute(
            """
            SELECT data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = 'admins' AND column_name = 'puede_crear_formularios'
            """
        )
        fila = cur.fetchone()
    assert fila is not None
    assert fila[0] == "boolean" and fila[1] == "NO" and "false" in fila[2]
```

- [ ] **Step 2: Correr los tests para ver que fallan**

Run (desde `backend/`): `timeout 120 .venv/bin/pytest -q -p no:cacheprovider tests/test_admin_formularios_permiso.py tests/test_schema_smoke.py 2>&1 | tail -6`
Expected: FAIL (`TypeError: crear_admin() got an unexpected keyword argument 'puede_crear_formularios'` y el smoke test sin las tablas).

- [ ] **Step 3: Agregar el esquema y aplicarlo a la base local de tests**

Agregar al final de `backend/db/schema.sql`:

```sql

ALTER TABLE admins ADD COLUMN IF NOT EXISTS puede_crear_formularios BOOLEAN NOT NULL DEFAULT false;

CREATE TABLE IF NOT EXISTS formularios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organismo_id INTEGER NOT NULL REFERENCES organismos(id),
    nombre TEXT NOT NULL,
    descripcion_uso TEXT NOT NULL DEFAULT '',
    aviso_finalidad TEXT NOT NULL DEFAULT '',
    tramite_id TEXT REFERENCES tramites(id),
    estado TEXT NOT NULL DEFAULT 'borrador',
    fecha_cierre TIMESTAMPTZ,
    cupo INTEGER,
    creado_por_email TEXT NOT NULL,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    actualizado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT formularios_estado_valido CHECK (estado IN ('borrador', 'activo', 'cerrado')),
    CONSTRAINT formularios_cupo_positivo CHECK (cupo IS NULL OR cupo > 0)
);

CREATE INDEX IF NOT EXISTS formularios_organismo_idx ON formularios (organismo_id, creado_en DESC);

CREATE TABLE IF NOT EXISTS formulario_campos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    formulario_id UUID NOT NULL REFERENCES formularios(id),
    clave TEXT NOT NULL,
    etiqueta TEXT NOT NULL,
    tipo TEXT NOT NULL,
    obligatorio BOOLEAN NOT NULL DEFAULT true,
    opciones JSONB,
    orden INTEGER NOT NULL,
    UNIQUE (formulario_id, clave),
    CONSTRAINT formulario_campos_tipo_valido CHECK (
        tipo IN ('texto', 'texto_largo', 'dni', 'telefono', 'email', 'numero', 'fecha', 'si_no', 'opcion')
    )
);

CREATE TABLE IF NOT EXISTS formulario_respuestas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    formulario_id UUID NOT NULL REFERENCES formularios(id),
    session_id UUID NOT NULL REFERENCES sesiones(id),
    valores JSONB NOT NULL,
    dni TEXT,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    eliminada_en TIMESTAMPTZ,
    eliminada_por_email TEXT
);

CREATE INDEX IF NOT EXISTS formulario_respuestas_formulario_idx ON formulario_respuestas (formulario_id, creado_en DESC);
CREATE INDEX IF NOT EXISTS formulario_respuestas_session_idx ON formulario_respuestas (session_id);
CREATE UNIQUE INDEX IF NOT EXISTS formulario_respuestas_dni_unico
    ON formulario_respuestas (formulario_id, dni) WHERE dni IS NOT NULL AND eliminada_en IS NULL;
```

Run (desde la raíz del repo): `psql postgresql://macacha:macacha@localhost:5432/macacha_test -f backend/db/schema.sql 2>&1 | grep -iE "^psql:.*error" | head -3; echo "esquema aplicado en macacha_test"`
Expected: sin líneas de error antes del mensaje final.

En `backend/tests/conftest.py`, dentro de `_clean()`, agregar **antes** de `cur.execute("DELETE FROM sesiones")`:

```python
            cur.execute("DELETE FROM formulario_respuestas")
            cur.execute("DELETE FROM formulario_campos")
            cur.execute("DELETE FROM formularios")
```

- [ ] **Step 4: Implementar el permiso en el repositorio de admins**

En `backend/agent/admin/repository.py` reemplazar `crear_admin`:

```python
def crear_admin(
    conn,
    email: str,
    password_hash: str,
    rol: str = "admin_organismo",
    organismo_id: int | None = None,
    puede_crear_formularios: bool = False,
) -> None:
    # Si el admin ya existe, no se toca el permiso: volver a correr create_admin solo cambia la contraseña.
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO admins (email, password_hash, rol, organismo_id, puede_crear_formularios)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (email) DO UPDATE SET
                password_hash = EXCLUDED.password_hash,
                rol = EXCLUDED.rol,
                organismo_id = EXCLUDED.organismo_id
            """,
            (email, password_hash, rol, organismo_id, puede_crear_formularios),
        )
```

Reemplazar `obtener_admin_por_id`:

```python
def obtener_admin_por_id(conn, admin_id: str) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, email, rol, organismo_id, activo, puede_crear_formularios FROM admins WHERE id = %s",
            (admin_id,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        return {
            "id": str(row[0]),
            "email": row[1],
            "rol": row[2],
            "organismo_id": row[3],
            "activo": row[4],
            "puede_crear_formularios": row[5],
        }
```

Reemplazar `listar_admins` y `editar_admin` por:

```python
def listar_admins(conn) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT a.id, a.email, a.rol, o.nombre, a.activo, a.puede_crear_formularios
            FROM admins a
            LEFT JOIN organismos o ON o.id = a.organismo_id
            ORDER BY a.email
            """
        )
        return [
            {
                "id": str(id_),
                "email": email,
                "rol": rol,
                "organismo": organismo,
                "activo": activo,
                "puede_crear_formularios": puede,
            }
            for id_, email, rol, organismo, activo, puede in cur.fetchall()
        ]


def editar_admin(
    conn,
    admin_id: str,
    rol: str,
    organismo_id: int | None,
    activo: bool,
    password_hash: str | None = None,
    puede_crear_formularios: bool | None = None,
) -> None:
    asignaciones = ["rol = %s", "organismo_id = %s", "activo = %s"]
    parametros: list = [rol, organismo_id, activo]
    if password_hash is not None:
        asignaciones.append("password_hash = %s")
        parametros.append(password_hash)
    if puede_crear_formularios is not None:
        asignaciones.append("puede_crear_formularios = %s")
        parametros.append(puede_crear_formularios)
    parametros.append(admin_id)
    with conn.cursor() as cur:
        cur.execute(f"UPDATE admins SET {', '.join(asignaciones)} WHERE id = %s", parametros)
```

(Reemplazar las funciones `listar_admins` y `editar_admin` actuales por estas dos; el resto del archivo no cambia.)

- [ ] **Step 5: Implementar `/admin/me`, usuarios y la dependencia en `api.py`**

En `backend/agent/api.py`:

1. En `admin_me`, cambiar el `return` por:

```python
    puede = admin_db["rol"] == "super_admin" or admin_db["puede_crear_formularios"]
    return {
        "email": admin_db["email"],
        "rol": admin_db["rol"],
        "organismo": organismo,
        "puede_crear_formularios": puede,
    }
```

2. En `UsuarioPayload` agregar el campo `puede_crear_formularios: bool = False`, y en `UsuarioEdicionPayload` agregar `puede_crear_formularios: bool | None = None`.

3. En `admin_crear_usuario`, reemplazar la llamada a `crear_admin` por:

```python
        admin_repository.crear_admin(
            conn,
            request.email,
            password_hash,
            request.rol,
            request.organismo_id,
            puede_crear_formularios=request.puede_crear_formularios and request.rol == "admin_organismo",
        )
```

4. En `admin_editar_usuario`, reemplazar la llamada a `editar_admin` por:

```python
        puede = (
            None
            if request.puede_crear_formularios is None
            else request.puede_crear_formularios and request.rol == "admin_organismo"
        )
        admin_repository.editar_admin(
            conn,
            str(admin_id),
            request.rol,
            request.organismo_id,
            request.activo,
            password_hash,
            puede_crear_formularios=puede,
        )
```

5. Agregar la dependencia junto a las otras funciones auxiliares de admin (antes de los endpoints de formularios que se crean en la Task 4; por ejemplo justo después de `admin_me`):

```python
def requiere_gestor_de_formularios(
    admin: AdminActual = Depends(requiere_admin), pool=Depends(obtener_pool)
) -> AdminActual:
    """El permiso se lee de la base en cada pedido: activarlo o retirarlo tiene efecto inmediato."""
    if admin.rol == "super_admin":
        return admin
    with pool.connection() as conn:
        admin_db = admin_repository.obtener_admin_por_id(conn, admin.id)
    if admin_db is None or not admin_db["activo"] or not admin_db["puede_crear_formularios"]:
        raise HTTPException(status_code=403, detail="No tenés permiso para gestionar formularios")
    return admin
```

- [ ] **Step 6: Correr los tests y la suite del backend**

Run: `timeout 120 .venv/bin/pytest -q -p no:cacheprovider tests/test_admin_formularios_permiso.py tests/test_schema_smoke.py 2>&1 | tail -3`
Expected: PASS (todos).

Run: `timeout 280 .venv/bin/pytest -q -p no:cacheprovider 2>&1 | tail -1`
Expected: toda la suite PASS (los tests de usuarios existentes siguen verdes: los campos nuevos son opcionales).

- [ ] **Step 7: Commit**

```bash
git add backend/db/schema.sql backend/tests/conftest.py backend/tests/test_schema_smoke.py backend/tests/test_admin_formularios_permiso.py backend/agent/admin/repository.py backend/agent/api.py
git commit -m "feat: permiso para crear formularios por usuario y tablas de formularios"
```

---

### Task 2: Validación por tipo y CSV (módulos puros)

**Files:**
- Create: `backend/agent/formularios_validacion.py`
- Create: `backend/agent/formularios_csv.py`
- Test: `backend/tests/test_formularios_validacion.py`
- Test: `backend/tests/test_formularios_csv.py`

**Interfaces:**
- Consumes: `agent.admin.email_contacto.normalizar_email_contacto(valor) -> str | None` (lanza `ValueError`).
- Produces (`formularios_validacion`): `TIPOS` (tupla de 9), `ErrorDeCampo(ValueError)`, `generar_clave(etiqueta: str, existentes: set[str]) -> str`, `normalizar_valor(campo: dict, valor) -> object`, `validar_valores(campos: list[dict], valores: dict) -> tuple[dict, dict]` (valores normalizados, errores por clave), `validar_definicion(campos: list[dict]) -> None` (lanza `ValueError`). Un campo es `{"clave", "etiqueta", "tipo", "obligatorio", "opciones"}`.
- Produces (`formularios_csv`): `valor_legible(campo: dict, valor) -> str`, `a_csv(campos: list[dict], respuestas: list[dict]) -> str` (cada respuesta con `creado_en` y `valores`).

- [ ] **Step 1: Escribir los tests de validación que fallan**

Crear `backend/tests/test_formularios_validacion.py`:

```python
import pytest

from agent.formularios_validacion import (
    ErrorDeCampo,
    generar_clave,
    normalizar_valor,
    validar_definicion,
    validar_valores,
)


def _campo(tipo, obligatorio=True, opciones=None, clave="c"):
    return {"clave": clave, "etiqueta": "Campo", "tipo": tipo, "obligatorio": obligatorio, "opciones": opciones}


@pytest.mark.parametrize("entrada", ["30123456", "30.123.456", "30 123 456", " 30123456 ", 30123456])
def test_dni_acepta_puntos_y_espacios_y_queda_solo_con_numeros(entrada):
    assert normalizar_valor(_campo("dni"), entrada) == "30123456"


@pytest.mark.parametrize("entrada", ["123456", "123456789", "12a45678", "abc", ""])
def test_dni_rechaza_lo_que_no_tiene_7_u_8_numeros(entrada):
    with pytest.raises(ErrorDeCampo):
        normalizar_valor(_campo("dni"), entrada)


@pytest.mark.parametrize(
    "entrada, esperado",
    [("387 456-7890", "3874567890"), ("(387) 4567890", "3874567890"), ("+54 9 387 456 7890", "+5493874567890")],
)
def test_telefono_acepta_formatos_comunes(entrada, esperado):
    assert normalizar_valor(_campo("telefono"), entrada) == esperado


@pytest.mark.parametrize("entrada", ["1234567", "1" * 16, "387-abc-4567", "387#4567890"])
def test_telefono_rechaza_largos_y_caracteres_invalidos(entrada):
    with pytest.raises(ErrorDeCampo):
        normalizar_valor(_campo("telefono"), entrada)


def test_email_se_valida_y_se_recorta():
    assert normalizar_valor(_campo("email"), "  ana@correo.com ") == "ana@correo.com"
    with pytest.raises(ErrorDeCampo):
        normalizar_valor(_campo("email"), "no-es-un-mail")


@pytest.mark.parametrize("entrada, esperado", [("12", 12), ("12,5", 12.5), ("12.5", 12.5), (7, 7), (3.0, 3), ("-4", -4)])
def test_numero_acepta_coma_y_punto(entrada, esperado):
    assert normalizar_valor(_campo("numero"), entrada) == esperado


@pytest.mark.parametrize("entrada", ["abc", "", "nan", "inf", True])
def test_numero_rechaza_lo_que_no_es_numero(entrada):
    with pytest.raises(ErrorDeCampo):
        normalizar_valor(_campo("numero"), entrada)


@pytest.mark.parametrize("entrada, esperado", [("1990-12-25", "1990-12-25"), ("25/12/1990", "1990-12-25"), ("5/3/2001", "2001-03-05")])
def test_fecha_acepta_iso_y_dia_mes_anio(entrada, esperado):
    assert normalizar_valor(_campo("fecha"), entrada) == esperado


@pytest.mark.parametrize("entrada", ["31/02/2020", "2020-13-01", "mañana", "25-12-1990"])
def test_fecha_rechaza_fechas_que_no_existen_o_con_otro_formato(entrada):
    with pytest.raises(ErrorDeCampo):
        normalizar_valor(_campo("fecha"), entrada)


@pytest.mark.parametrize("entrada, esperado", [("sí", True), ("Si", True), (True, True), ("no", False), ("NO", False), (False, False)])
def test_si_no_acepta_variantes(entrada, esperado):
    assert normalizar_valor(_campo("si_no"), entrada) is esperado


def test_si_no_rechaza_otras_respuestas():
    with pytest.raises(ErrorDeCampo):
        normalizar_valor(_campo("si_no"), "quizás")


def test_opcion_acepta_sin_distinguir_mayusculas_y_devuelve_la_opcion_original():
    campo = _campo("opcion", opciones=["Mañana", "Tarde"])
    assert normalizar_valor(campo, "tarde") == "Tarde"
    with pytest.raises(ErrorDeCampo) as error:
        normalizar_valor(campo, "noche")
    assert "Mañana" in str(error.value) and "Tarde" in str(error.value)


def test_texto_y_texto_largo_respetan_su_largo_maximo():
    assert normalizar_valor(_campo("texto"), "  hola   mundo ") == "hola mundo"
    with pytest.raises(ErrorDeCampo):
        normalizar_valor(_campo("texto"), "x" * 201)
    assert normalizar_valor(_campo("texto_largo"), "x" * 1000) == "x" * 1000
    with pytest.raises(ErrorDeCampo):
        normalizar_valor(_campo("texto_largo"), "x" * 1001)


def test_validar_valores_junta_los_errores_por_clave_y_omite_los_opcionales_vacios():
    campos = [
        _campo("texto", clave="nombre"),
        _campo("dni", clave="dni"),
        _campo("telefono", obligatorio=False, clave="telefono"),
    ]

    normalizados, errores = validar_valores(campos, {"nombre": "Ana", "dni": "12", "telefono": "  "})

    assert normalizados == {"nombre": "Ana"}
    assert set(errores) == {"dni"}


def test_validar_valores_marca_los_obligatorios_faltantes_e_ignora_claves_desconocidas():
    campos = [_campo("texto", clave="nombre")]

    normalizados, errores = validar_valores(campos, {"otro": "x"})

    assert normalizados == {}
    assert errores == {"nombre": "Este dato es obligatorio."}


def test_validar_valores_acepta_el_valor_falso_de_un_si_no_obligatorio():
    campos = [_campo("si_no", clave="participa")]

    normalizados, errores = validar_valores(campos, {"participa": False})

    assert normalizados == {"participa": False} and errores == {}


def test_generar_clave_saca_acentos_y_evita_repetidas():
    assert generar_clave("¿Participaría de la capacitación?", set()) == "participaria_de_la_capacitacion"
    assert generar_clave("DNI", {"dni"}) == "dni_2"
    assert generar_clave("DNI", {"dni", "dni_2"}) == "dni_3"
    assert generar_clave("???", set()) == "campo"


def test_validar_definicion_acepta_el_ejemplo_de_trabajo():
    validar_definicion([_campo("texto"), _campo("dni"), _campo("telefono"), _campo("si_no")])


@pytest.mark.parametrize(
    "campos",
    [
        [],
        [_campo("dni"), _campo("dni")],
        [_campo("inventado")],
        [{**_campo("texto"), "etiqueta": "  "}],
        [{**_campo("texto"), "etiqueta": "x" * 121}],
        [_campo("opcion", opciones=["Una sola"])],
        [_campo("opcion", opciones=["A", "a"])],
        [_campo("opcion", opciones=[f"o{i}" for i in range(21)])],
        [_campo("texto") for _ in range(31)],
    ],
)
def test_validar_definicion_rechaza_definiciones_invalidas(campos):
    with pytest.raises(ValueError):
        validar_definicion(campos)
```

- [ ] **Step 2: Correr los tests para ver que fallan**

Run: `timeout 60 .venv/bin/pytest -q -p no:cacheprovider tests/test_formularios_validacion.py 2>&1 | tail -3`
Expected: FAIL (`ModuleNotFoundError: No module named 'agent.formularios_validacion'`).

- [ ] **Step 3: Implementar `formularios_validacion.py`**

Crear `backend/agent/formularios_validacion.py`:

```python
import math
import re
import unicodedata
from datetime import date

from agent.admin.email_contacto import normalizar_email_contacto

TIPOS = ("texto", "texto_largo", "dni", "telefono", "email", "numero", "fecha", "si_no", "opcion")
MAX_CAMPOS = 30
MAX_OPCIONES = 20
MAX_OPCION = 80
MAX_ETIQUETA = 120
MAX_TEXTO = 200
MAX_TEXTO_LARGO = 1000

_SI = {"si", "sí", "s", "true", "verdadero"}
_NO = {"no", "n", "false", "falso"}


class ErrorDeCampo(ValueError):
    """El valor no cumple las reglas de su tipo; el mensaje se le puede mostrar a la persona."""


def _sin_acentos(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


def generar_clave(etiqueta: str, existentes: set[str]) -> str:
    base = re.sub(r"[^a-z0-9]+", "_", _sin_acentos(etiqueta).lower()).strip("_")[:40] or "campo"
    clave, n = base, 2
    while clave in existentes:
        clave = f"{base}_{n}"
        n += 1
    return clave


def _normalizar_texto(valor, maximo: int, una_linea: bool) -> str:
    texto = " ".join(str(valor).split()) if una_linea else str(valor).strip()
    if len(texto) > maximo:
        raise ErrorDeCampo(f"Es demasiado largo (máximo {maximo} caracteres).")
    return texto


def _normalizar_dni(valor) -> str:
    digitos = re.sub(r"[.\s]", "", str(valor))
    if not re.fullmatch(r"\d{7,8}", digitos):
        raise ErrorDeCampo("El DNI debe tener 7 u 8 números.")
    return digitos


def _normalizar_telefono(valor) -> str:
    limpio = str(valor).strip()
    if not re.fullmatch(r"\+?[\d\s\-()]+", limpio):
        raise ErrorDeCampo("El teléfono solo puede tener números, espacios, guiones y paréntesis.")
    digitos = re.sub(r"\D", "", limpio)
    if not 8 <= len(digitos) <= 15:
        raise ErrorDeCampo("El teléfono debe tener entre 8 y 15 números.")
    return ("+" if limpio.startswith("+") else "") + digitos


def _normalizar_email(valor) -> str:
    try:
        email = normalizar_email_contacto(str(valor))
    except ValueError as error:
        raise ErrorDeCampo(str(error)) from None
    if email is None:
        raise ErrorDeCampo("Ingresá un email.")
    return email


def _normalizar_numero(valor):
    if isinstance(valor, bool):
        raise ErrorDeCampo("Ingresá un número.")
    if isinstance(valor, (int, float)):
        numero = float(valor)
    else:
        try:
            numero = float(str(valor).strip().replace(",", "."))
        except ValueError:
            raise ErrorDeCampo("Ingresá un número.") from None
    if math.isnan(numero) or math.isinf(numero):
        raise ErrorDeCampo("Ingresá un número.")
    return int(numero) if numero == int(numero) else numero


def _normalizar_fecha(valor) -> str:
    texto = str(valor).strip()
    iso = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", texto)
    if iso:
        anio, mes, dia = (int(x) for x in iso.groups())
    else:
        local = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", texto)
        if not local:
            raise ErrorDeCampo("Ingresá la fecha como día/mes/año, por ejemplo 25/12/1990.")
        dia, mes, anio = (int(x) for x in local.groups())
    try:
        return date(anio, mes, dia).isoformat()
    except ValueError:
        raise ErrorDeCampo("Esa fecha no existe.") from None


def _normalizar_si_no(valor) -> bool:
    if isinstance(valor, bool):
        return valor
    texto = str(valor).strip().lower()
    if texto in _SI:
        return True
    if texto in _NO:
        return False
    raise ErrorDeCampo("Respondé sí o no.")


def _normalizar_opcion(valor, opciones) -> str:
    texto = str(valor).strip().lower()
    for opcion in opciones or []:
        if opcion.strip().lower() == texto:
            return opcion
    raise ErrorDeCampo("Elegí una de estas opciones: " + ", ".join(opciones or []) + ".")


def normalizar_valor(campo: dict, valor):
    tipo = campo["tipo"]
    if tipo == "texto":
        return _normalizar_texto(valor, MAX_TEXTO, una_linea=True)
    if tipo == "texto_largo":
        return _normalizar_texto(valor, MAX_TEXTO_LARGO, una_linea=False)
    if tipo == "dni":
        return _normalizar_dni(valor)
    if tipo == "telefono":
        return _normalizar_telefono(valor)
    if tipo == "email":
        return _normalizar_email(valor)
    if tipo == "numero":
        return _normalizar_numero(valor)
    if tipo == "fecha":
        return _normalizar_fecha(valor)
    if tipo == "si_no":
        return _normalizar_si_no(valor)
    if tipo == "opcion":
        return _normalizar_opcion(valor, campo.get("opciones"))
    raise ValueError(f"Tipo de campo desconocido: {tipo}")


def validar_valores(campos: list[dict], valores: dict) -> tuple[dict, dict]:
    normalizados: dict = {}
    errores: dict = {}
    for campo in campos:
        clave = campo["clave"]
        crudo = valores.get(clave) if isinstance(valores, dict) else None
        vacio = crudo is None or (isinstance(crudo, str) and not crudo.strip())
        if vacio:
            if campo["obligatorio"]:
                errores[clave] = "Este dato es obligatorio."
            continue
        try:
            normalizados[clave] = normalizar_valor(campo, crudo)
        except ErrorDeCampo as error:
            errores[clave] = str(error)
    return normalizados, errores


def validar_definicion(campos: list[dict]) -> None:
    if not campos:
        raise ValueError("El formulario necesita al menos un campo.")
    if len(campos) > MAX_CAMPOS:
        raise ValueError(f"Un formulario admite hasta {MAX_CAMPOS} campos.")
    if sum(1 for c in campos if c["tipo"] == "dni") > 1:
        raise ValueError("Un formulario admite un solo campo DNI.")
    for campo in campos:
        if campo["tipo"] not in TIPOS:
            raise ValueError(f"Tipo de campo desconocido: {campo['tipo']}.")
        etiqueta = (campo.get("etiqueta") or "").strip()
        if not etiqueta or len(etiqueta) > MAX_ETIQUETA:
            raise ValueError(f"Cada campo necesita una etiqueta de hasta {MAX_ETIQUETA} caracteres.")
        if campo["tipo"] == "opcion":
            opciones = [o.strip() for o in (campo.get("opciones") or [])]
            repetidas = len({o.lower() for o in opciones}) != len(opciones)
            if not 2 <= len(opciones) <= MAX_OPCIONES or repetidas or any(not o or len(o) > MAX_OPCION for o in opciones):
                raise ValueError(
                    f"La lista «{etiqueta}» necesita entre 2 y {MAX_OPCIONES} opciones distintas, de hasta {MAX_OPCION} caracteres."
                )
```

- [ ] **Step 4: Correr los tests de validación**

Run: `timeout 60 .venv/bin/pytest -q -p no:cacheprovider tests/test_formularios_validacion.py 2>&1 | tail -3`
Expected: PASS.

- [ ] **Step 5: Escribir los tests del CSV que fallan**

Crear `backend/tests/test_formularios_csv.py`:

```python
import csv
import io

from agent.formularios_csv import a_csv, valor_legible

CAMPOS = [
    {"clave": "nombre", "etiqueta": "Nombre", "tipo": "texto", "obligatorio": True, "opciones": None},
    {"clave": "edad", "etiqueta": "Edad", "tipo": "numero", "obligatorio": True, "opciones": None},
    {"clave": "participa", "etiqueta": "¿Participa?", "tipo": "si_no", "obligatorio": True, "opciones": None},
    {"clave": "nacimiento", "etiqueta": "Nacimiento", "tipo": "fecha", "obligatorio": False, "opciones": None},
]


def _leer(texto):
    return list(csv.reader(io.StringIO(texto)))


def test_valor_legible_por_tipo():
    assert valor_legible(CAMPOS[2], True) == "Sí"
    assert valor_legible(CAMPOS[2], False) == "No"
    assert valor_legible(CAMPOS[3], "1990-12-25") == "25/12/1990"
    assert valor_legible(CAMPOS[1], 12) == "12"
    assert valor_legible(CAMPOS[0], None) == ""


def test_el_csv_tiene_encabezado_y_una_fila_por_respuesta():
    respuestas = [
        {"creado_en": "2026-10-23T10:00:00", "valores": {"nombre": "Ana", "edad": 30, "participa": True, "nacimiento": "1990-12-25"}},
        {"creado_en": "2026-10-23T11:00:00", "valores": {"nombre": "Luis", "edad": 41, "participa": False}},
    ]

    filas = _leer(a_csv(CAMPOS, respuestas))

    assert filas[0] == ["Fecha", "Nombre", "Edad", "¿Participa?", "Nacimiento"]
    assert filas[1] == ["2026-10-23T10:00:00", "Ana", "30", "Sí", "25/12/1990"]
    assert filas[2] == ["2026-10-23T11:00:00", "Luis", "41", "No", ""]


def test_las_celdas_que_empiezan_como_formula_se_prefijan_con_comilla():
    respuestas = [{"creado_en": "x", "valores": {"nombre": "=HYPERLINK(\"http://malo\")", "edad": 1, "participa": True}}]

    celda = _leer(a_csv(CAMPOS, respuestas))[1][1]

    assert celda.startswith("'=")


def test_las_otras_marcas_de_formula_tambien_se_neutralizan():
    for texto in ("+54 9 387", "-cmd", "@usuario"):
        respuestas = [{"creado_en": "x", "valores": {"nombre": texto, "edad": 1, "participa": True}}]
        assert _leer(a_csv(CAMPOS, respuestas))[1][1] == "'" + texto


def test_los_numeros_negativos_no_se_prefijan():
    respuestas = [{"creado_en": "x", "valores": {"nombre": "Ana", "edad": -4, "participa": True}}]

    assert _leer(a_csv(CAMPOS, respuestas))[1][2] == "-4"


def test_el_encabezado_tambien_se_neutraliza():
    campos = [{"clave": "a", "etiqueta": "=1+1", "tipo": "texto", "obligatorio": True, "opciones": None}]

    assert _leer(a_csv(campos, []))[0][1] == "'=1+1"


def test_comas_comillas_y_saltos_de_linea_quedan_bien_formados():
    respuestas = [{"creado_en": "x", "valores": {"nombre": 'Ana, "la" mejor\nsegunda línea', "edad": 1, "participa": True}}]

    filas = _leer(a_csv(CAMPOS, respuestas))

    assert filas[1][1] == 'Ana, "la" mejor\nsegunda línea'
    assert len(filas[1]) == 5
```

- [ ] **Step 6: Correr los tests del CSV para ver que fallan**

Run: `timeout 60 .venv/bin/pytest -q -p no:cacheprovider tests/test_formularios_csv.py 2>&1 | tail -3`
Expected: FAIL (`ModuleNotFoundError: No module named 'agent.formularios_csv'`).

- [ ] **Step 7: Implementar `formularios_csv.py`**

Crear `backend/agent/formularios_csv.py`:

```python
import csv
import io

_INICIOS_DE_FORMULA = ("=", "+", "-", "@", "\t", "\r")


def neutralizar_formula(texto: str) -> str:
    """Excel interpreta como fórmula lo que empieza con = + - @; una comilla simple lo vuelve texto."""
    return "'" + texto if texto[:1] in _INICIOS_DE_FORMULA else texto


def valor_legible(campo: dict, valor) -> str:
    if valor is None:
        return ""
    if campo["tipo"] == "si_no":
        return "Sí" if valor else "No"
    if campo["tipo"] == "fecha":
        partes = str(valor).split("-")
        return f"{partes[2]}/{partes[1]}/{partes[0]}" if len(partes) == 3 else str(valor)
    return str(valor)


def a_csv(campos: list[dict], respuestas: list[dict]) -> str:
    salida = io.StringIO()
    escritor = csv.writer(salida, lineterminator="\r\n")
    escritor.writerow(["Fecha"] + [neutralizar_formula(c["etiqueta"]) for c in campos])
    for respuesta in respuestas:
        fila = [str(respuesta["creado_en"])]
        for campo in campos:
            texto = valor_legible(campo, respuesta["valores"].get(campo["clave"]))
            fila.append(texto if campo["tipo"] == "numero" else neutralizar_formula(texto))
        escritor.writerow(fila)
    return salida.getvalue()
```

- [ ] **Step 8: Correr los tests y la suite**

Run: `timeout 60 .venv/bin/pytest -q -p no:cacheprovider tests/test_formularios_validacion.py tests/test_formularios_csv.py 2>&1 | tail -3`
Expected: PASS.

Run: `timeout 280 .venv/bin/pytest -q -p no:cacheprovider 2>&1 | tail -1`
Expected: toda la suite PASS.

- [ ] **Step 9: Commit**

```bash
git add backend/agent/formularios_validacion.py backend/agent/formularios_csv.py backend/tests/test_formularios_validacion.py backend/tests/test_formularios_csv.py
git commit -m "feat: validación por tipo de campo y exportación CSV de formularios"
```

---

### Task 3: Repositorio de formularios (CRUD, estado efectivo, edición con reglas, guardado con cupo y DNI único)

**Files:**
- Create: `backend/agent/admin/formularios_repository.py`
- Create: `backend/tests/formularios_helpers.py`
- Test: `backend/tests/test_formularios_repository.py`

**Interfaces:**
- Consumes: `formularios_validacion.generar_clave`, `validar_definicion`, `validar_valores` (Task 2); tablas de la Task 1.
- Produces (todas reciben `conn` como primer parámetro):
  - Excepciones: `ReglaDeEdicion(ValueError)`, `FormularioNoDisponible(Exception)` con `.motivo` (`"cerrado"` o `"cupo"`), `DatosInvalidos(Exception)` con `.errores` (clave → mensaje), `RespuestaDuplicada`, `YaRespondio`.
  - `calcular_estado_efectivo(estado, fecha_cierre, cupo, respuestas, ahora=None) -> str` (`borrador | cerrado | vencido | cupo_completo | abierto`).
  - `crear_formulario(conn, organismo_id, datos, campos, creado_por_email) -> str` (id). `datos`: `nombre`, `descripcion_uso`, `aviso_finalidad`, `tramite_id`, `estado`, `fecha_cierre` (datetime o `None`), `cupo`. Un campo: `{"etiqueta", "tipo", "obligatorio", "opciones", "clave"?}`.
  - `obtener_formulario(conn, formulario_id) -> dict | None` con `id, organismo_id, organismo, nombre, descripcion_uso, aviso_finalidad, tramite_id, estado, estado_efectivo, fecha_cierre (ISO o None), cupo, respuestas (vigentes), hay_respuestas (incluye borradas), creado_por_email, creado_en, actualizado_en, campos` (cada campo con `clave, etiqueta, tipo, obligatorio, opciones`).
  - `listar_formularios(conn, organismo_id: int | None, page, page_size) -> (list[dict], int)` (mismas claves que `obtener_formulario` salvo `campos`).
  - `actualizar_formulario(conn, formulario_id, datos, campos) -> None`.
  - `guardar_respuesta(conn, formulario_id, session_id, valores) -> dict` con `id, formulario, organismo_id, valores, campos`.
  - `listar_respuestas(conn, formulario_id, page, page_size) -> (list[dict], int)`, `todas_las_respuestas(conn, formulario_id) -> list[dict]`, `obtener_respuesta(conn, formulario_id, respuesta_id) -> dict | None` (`id, session_id, creado_en, valores`), `borrar_respuesta(conn, formulario_id, respuesta_id, email) -> bool`. Cada respuesta de las listas: `{"id", "creado_en" (ISO), "valores"}`.
  - `formularios_abiertos(conn, tramite_id=None, consulta=None, limite=5) -> list[dict]` (con `campos`), `formularios_consultados_en_sesion(conn, session_id) -> set[str]`, `formularios_respondidos_en_sesion(conn, session_id) -> int`.

- [ ] **Step 1: Escribir los helpers de tests**

Crear `backend/tests/formularios_helpers.py`:

```python
import uuid

from agent import sessions
from agent.admin import formularios_repository as formularios
from ingest import repository as repo

CAMPOS_TRABAJO = [
    {"etiqueta": "Nombre y apellido", "tipo": "texto", "obligatorio": True, "opciones": None},
    {"etiqueta": "DNI", "tipo": "dni", "obligatorio": True, "opciones": None},
    {"etiqueta": "Teléfono", "tipo": "telefono", "obligatorio": True, "opciones": None},
    {"etiqueta": "¿Participaría de la capacitación?", "tipo": "si_no", "obligatorio": True, "opciones": None},
]


def crear_organismo(conn, nombre: str = "Subsecretaría de Trabajo") -> int:
    return repo.upsert_organismo(conn, nombre)


def crear_tramite(conn, organismo_id: int, tramite_id: str = "TR-0001", nombre: str = "Denuncia laboral") -> str:
    repo.upsert_tramite(conn, tramite_id, organismo_id, "Trabajo", nombre)
    return tramite_id


def datos_formulario(**cambios) -> dict:
    datos = {
        "nombre": "Inscripción a la capacitación",
        "descripcion_uso": "Inscripción a la capacitación de la Subsecretaría de Trabajo",
        "aviso_finalidad": "La Subsecretaría de Trabajo usa tus datos para inscribirte a la capacitación.",
        "tramite_id": None,
        "estado": "activo",
        "fecha_cierre": None,
        "cupo": None,
    }
    datos.update(cambios)
    return datos


def crear_formulario(conn, organismo_id: int, campos: list[dict] | None = None, **cambios) -> str:
    return formularios.crear_formulario(
        conn, organismo_id, datos_formulario(**cambios), campos or CAMPOS_TRABAJO, "creador@organismo.gob.ar"
    )


def crear_sesion(conn) -> str:
    session_id = str(uuid.uuid4())
    sessions.crear_sesion_si_no_existe(conn, session_id)
    return session_id


def valores_validos(dni: str = "30123456", nombre: str = "Ana Pérez", participa: bool = True) -> dict:
    return {
        "nombre_y_apellido": nombre,
        "dni": dni,
        "telefono": "387 456-7890",
        "participaria_de_la_capacitacion": participa,
    }
```

- [ ] **Step 2: Escribir los tests que fallan**

Crear `backend/tests/test_formularios_repository.py`:

```python
import json
import os
import threading
from datetime import datetime, timedelta, timezone

import psycopg
import pytest

from agent import sessions
from agent.admin import formularios_repository as formularios
from agent.admin.formularios_repository import (
    DatosInvalidos,
    FormularioNoDisponible,
    ReglaDeEdicion,
    RespuestaDuplicada,
    YaRespondio,
    calcular_estado_efectivo,
)
from tests.formularios_helpers import (
    CAMPOS_TRABAJO,
    crear_formulario,
    crear_organismo,
    crear_sesion,
    crear_tramite,
    datos_formulario,
    valores_validos,
)

AHORA = datetime(2026, 10, 23, 12, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    "estado, fecha_cierre, cupo, respuestas, esperado",
    [
        ("borrador", None, None, 0, "borrador"),
        ("cerrado", None, None, 0, "cerrado"),
        ("activo", None, None, 0, "abierto"),
        ("activo", AHORA + timedelta(minutes=1), None, 0, "abierto"),
        ("activo", AHORA, None, 0, "vencido"),
        ("activo", AHORA - timedelta(days=1), None, 0, "vencido"),
        ("activo", None, 5, 4, "abierto"),
        ("activo", None, 5, 5, "cupo_completo"),
        ("activo", AHORA - timedelta(days=1), 5, 5, "vencido"),
    ],
)
def test_calcular_estado_efectivo(estado, fecha_cierre, cupo, respuestas, esperado):
    assert calcular_estado_efectivo(estado, fecha_cierre, cupo, respuestas, ahora=AHORA) == esperado


def test_crear_y_obtener_formulario_con_campos_y_claves(db_conn, clean_db):
    organismo_id = crear_organismo(db_conn)

    formulario_id = crear_formulario(db_conn, organismo_id, cupo=40)
    formulario = formularios.obtener_formulario(db_conn, formulario_id)

    assert formulario["nombre"] == "Inscripción a la capacitación"
    assert formulario["organismo"] == "Subsecretaría de Trabajo"
    assert formulario["estado_efectivo"] == "abierto"
    assert formulario["cupo"] == 40 and formulario["respuestas"] == 0 and formulario["hay_respuestas"] is False
    assert [c["clave"] for c in formulario["campos"]] == [
        "nombre_y_apellido", "dni", "telefono", "participaria_de_la_capacitacion",
    ]
    assert [c["tipo"] for c in formulario["campos"]] == ["texto", "dni", "telefono", "si_no"]


def test_obtener_un_formulario_inexistente_devuelve_none(db_conn, clean_db):
    assert formularios.obtener_formulario(db_conn, "00000000-0000-0000-0000-000000000000") is None


def test_crear_rechaza_una_definicion_invalida(db_conn, clean_db):
    organismo_id = crear_organismo(db_conn)
    dos_dni = CAMPOS_TRABAJO + [{"etiqueta": "Otro DNI", "tipo": "dni", "obligatorio": False, "opciones": None}]

    with pytest.raises(ValueError):
        crear_formulario(db_conn, organismo_id, campos=dos_dni)


def test_un_campo_de_lista_guarda_sus_opciones(db_conn, clean_db):
    organismo_id = crear_organismo(db_conn)
    campos = [{"etiqueta": "Turno", "tipo": "opcion", "obligatorio": True, "opciones": [" Mañana ", "Tarde"]}]

    formulario_id = crear_formulario(db_conn, organismo_id, campos=campos)

    assert formularios.obtener_formulario(db_conn, formulario_id)["campos"][0]["opciones"] == ["Mañana", "Tarde"]


def test_listar_formularios_filtra_por_organismo_y_pagina(db_conn, clean_db):
    trabajo = crear_organismo(db_conn)
    registro = crear_organismo(db_conn, "Registro Civil")
    crear_formulario(db_conn, trabajo, nombre="A")
    crear_formulario(db_conn, trabajo, nombre="B")
    crear_formulario(db_conn, registro, nombre="C")

    de_trabajo, total_trabajo = formularios.listar_formularios(db_conn, trabajo, 1, 10)
    todos, total = formularios.listar_formularios(db_conn, None, 1, 10)
    primera, _ = formularios.listar_formularios(db_conn, None, 1, 2)
    segunda, _ = formularios.listar_formularios(db_conn, None, 2, 2)

    assert {f["nombre"] for f in de_trabajo} == {"A", "B"} and total_trabajo == 2
    assert total == 3 and len(todos) == 3
    assert len(primera) == 2 and len(segunda) == 1
    assert "campos" not in de_trabajo[0]


def test_guardar_una_respuesta_normaliza_los_valores(db_conn, clean_db):
    organismo_id = crear_organismo(db_conn)
    formulario_id = crear_formulario(db_conn, organismo_id)
    sesion = crear_sesion(db_conn)

    resultado = formularios.guardar_respuesta(
        db_conn, formulario_id, sesion, valores_validos(dni="30.123.456", participa="sí")
    )

    assert resultado["valores"] == {
        "nombre_y_apellido": "Ana Pérez",
        "dni": "30123456",
        "telefono": "3874567890",
        "participaria_de_la_capacitacion": True,
    }
    assert resultado["formulario"] == "Inscripción a la capacitación"
    respuestas, total = formularios.listar_respuestas(db_conn, formulario_id, 1, 10)
    assert total == 1 and respuestas[0]["valores"]["dni"] == "30123456"
    assert formularios.obtener_formulario(db_conn, formulario_id)["respuestas"] == 1


def test_guardar_con_datos_invalidos_no_guarda_nada(db_conn, clean_db):
    organismo_id = crear_organismo(db_conn)
    formulario_id = crear_formulario(db_conn, organismo_id)
    sesion = crear_sesion(db_conn)

    with pytest.raises(DatosInvalidos) as error:
        formularios.guardar_respuesta(db_conn, formulario_id, sesion, valores_validos(dni="123"))

    assert set(error.value.errores) == {"dni"}
    assert formularios.listar_respuestas(db_conn, formulario_id, 1, 10)[1] == 0


@pytest.mark.parametrize(
    "cambios",
    [
        {"estado": "borrador"},
        {"estado": "cerrado"},
        {"fecha_cierre": datetime.now(timezone.utc) - timedelta(hours=1)},
    ],
)
def test_un_formulario_no_abierto_no_recibe_respuestas(db_conn, clean_db, cambios):
    organismo_id = crear_organismo(db_conn)
    formulario_id = crear_formulario(db_conn, organismo_id, **cambios)
    sesion = crear_sesion(db_conn)

    with pytest.raises(FormularioNoDisponible) as error:
        formularios.guardar_respuesta(db_conn, formulario_id, sesion, valores_validos())

    assert error.value.motivo == "cerrado"


def test_con_el_cupo_completo_no_se_aceptan_mas_respuestas(db_conn, clean_db):
    organismo_id = crear_organismo(db_conn)
    formulario_id = crear_formulario(db_conn, organismo_id, cupo=1)
    formularios.guardar_respuesta(db_conn, formulario_id, crear_sesion(db_conn), valores_validos())

    with pytest.raises(FormularioNoDisponible) as error:
        formularios.guardar_respuesta(db_conn, formulario_id, crear_sesion(db_conn), valores_validos(dni="40123456"))

    assert error.value.motivo == "cupo"
    assert formularios.obtener_formulario(db_conn, formulario_id)["estado_efectivo"] == "cupo_completo"


@pytest.mark.parametrize("segundo_dni", ["30123456", "30.123.456", "30 123 456", " 30123456 "])
def test_el_mismo_dni_escrito_de_otra_forma_es_duplicado(db_conn, clean_db, segundo_dni):
    organismo_id = crear_organismo(db_conn)
    formulario_id = crear_formulario(db_conn, organismo_id)
    formularios.guardar_respuesta(db_conn, formulario_id, crear_sesion(db_conn), valores_validos(dni="30123456"))

    with pytest.raises(RespuestaDuplicada):
        formularios.guardar_respuesta(db_conn, formulario_id, crear_sesion(db_conn), valores_validos(dni=segundo_dni))

    assert formularios.listar_respuestas(db_conn, formulario_id, 1, 10)[1] == 1


def test_el_mismo_dni_se_puede_usar_en_otro_formulario(db_conn, clean_db):
    organismo_id = crear_organismo(db_conn)
    uno = crear_formulario(db_conn, organismo_id, nombre="Uno")
    otro = crear_formulario(db_conn, organismo_id, nombre="Otro")

    formularios.guardar_respuesta(db_conn, uno, crear_sesion(db_conn), valores_validos())
    formularios.guardar_respuesta(db_conn, otro, crear_sesion(db_conn), valores_validos())


def test_una_sesion_no_puede_enviar_dos_veces_el_mismo_formulario(db_conn, clean_db):
    organismo_id = crear_organismo(db_conn)
    formulario_id = crear_formulario(db_conn, organismo_id)
    sesion = crear_sesion(db_conn)
    formularios.guardar_respuesta(db_conn, formulario_id, sesion, valores_validos(dni="30123456"))

    with pytest.raises(YaRespondio):
        formularios.guardar_respuesta(db_conn, formulario_id, sesion, valores_validos(dni="40123456"))


def test_borrar_una_respuesta_libera_el_dni_y_el_lugar_del_cupo(db_conn, clean_db):
    organismo_id = crear_organismo(db_conn)
    formulario_id = crear_formulario(db_conn, organismo_id, cupo=1)
    resultado = formularios.guardar_respuesta(db_conn, formulario_id, crear_sesion(db_conn), valores_validos())

    assert formularios.borrar_respuesta(db_conn, formulario_id, resultado["id"], "admin@x.com") is True

    assert formularios.listar_respuestas(db_conn, formulario_id, 1, 10)[1] == 0
    assert formularios.obtener_respuesta(db_conn, formulario_id, resultado["id"]) is None
    assert formularios.obtener_formulario(db_conn, formulario_id)["hay_respuestas"] is True
    formularios.guardar_respuesta(db_conn, formulario_id, crear_sesion(db_conn), valores_validos())


def test_borrar_registra_quien_y_cuando(db_conn, clean_db):
    organismo_id = crear_organismo(db_conn)
    formulario_id = crear_formulario(db_conn, organismo_id)
    resultado = formularios.guardar_respuesta(db_conn, formulario_id, crear_sesion(db_conn), valores_validos())

    formularios.borrar_respuesta(db_conn, formulario_id, resultado["id"], "admin@x.com")

    with db_conn.cursor() as cur:
        cur.execute("SELECT eliminada_por_email, eliminada_en FROM formulario_respuestas WHERE id = %s", (resultado["id"],))
        quien, cuando = cur.fetchone()
    assert quien == "admin@x.com" and cuando is not None


def test_borrar_una_respuesta_de_otro_formulario_o_ya_borrada_devuelve_false(db_conn, clean_db):
    organismo_id = crear_organismo(db_conn)
    uno = crear_formulario(db_conn, organismo_id, nombre="Uno")
    otro = crear_formulario(db_conn, organismo_id, nombre="Otro")
    resultado = formularios.guardar_respuesta(db_conn, uno, crear_sesion(db_conn), valores_validos())

    assert formularios.borrar_respuesta(db_conn, otro, resultado["id"], "a@x.com") is False
    assert formularios.borrar_respuesta(db_conn, uno, resultado["id"], "a@x.com") is True
    assert formularios.borrar_respuesta(db_conn, uno, resultado["id"], "a@x.com") is False


def test_dos_envios_simultaneos_por_el_ultimo_lugar_guardan_solo_uno(db_conn, clean_db):
    organismo_id = crear_organismo(db_conn)
    formulario_id = crear_formulario(db_conn, organismo_id, cupo=1)
    sesiones_ids = [crear_sesion(db_conn), crear_sesion(db_conn)]
    db_conn.commit()
    url = os.environ.get("TEST_DATABASE_URL", "postgresql://macacha:macacha@localhost:5432/macacha_test")
    resultados: list[str] = []
    barrera = threading.Barrier(2)

    def enviar(indice: int):
        with psycopg.connect(url) as conn:
            barrera.wait()
            try:
                formularios.guardar_respuesta(
                    conn, formulario_id, sesiones_ids[indice], valores_validos(dni=f"3012345{indice}")
                )
                conn.commit()
                resultados.append("ok")
            except FormularioNoDisponible as error:
                conn.rollback()
                resultados.append(error.motivo)

    hilos = [threading.Thread(target=enviar, args=(i,)) for i in range(2)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join(timeout=30)

    assert sorted(resultados) == ["cupo", "ok"]


def test_actualizar_sin_respuestas_permite_reemplazar_los_campos(db_conn, clean_db):
    organismo_id = crear_organismo(db_conn)
    formulario_id = crear_formulario(db_conn, organismo_id)
    actuales = formularios.obtener_formulario(db_conn, formulario_id)["campos"]
    nuevos = [actuales[0], {"etiqueta": "Comentario", "tipo": "texto_largo", "obligatorio": False, "opciones": None}]

    formularios.actualizar_formulario(db_conn, formulario_id, datos_formulario(nombre="Nuevo nombre", cupo=10), nuevos)

    formulario = formularios.obtener_formulario(db_conn, formulario_id)
    assert formulario["nombre"] == "Nuevo nombre" and formulario["cupo"] == 10
    assert [c["clave"] for c in formulario["campos"]] == ["nombre_y_apellido", "comentario"]


def _formulario_con_una_respuesta(db_conn):
    organismo_id = crear_organismo(db_conn)
    campos = CAMPOS_TRABAJO + [{"etiqueta": "Turno", "tipo": "opcion", "obligatorio": False, "opciones": ["Mañana", "Tarde"]}]
    formulario_id = crear_formulario(db_conn, organismo_id, campos=campos)
    formularios.guardar_respuesta(db_conn, formulario_id, crear_sesion(db_conn), valores_validos())
    return formulario_id, formularios.obtener_formulario(db_conn, formulario_id)["campos"]


def test_con_respuestas_se_pueden_cambiar_textos_y_agregar_un_campo_opcional(db_conn, clean_db):
    formulario_id, campos = _formulario_con_una_respuesta(db_conn)
    campos[0] = {**campos[0], "etiqueta": "Nombre completo"}
    campos.append({"etiqueta": "Comentario", "tipo": "texto", "obligatorio": False, "opciones": None})

    formularios.actualizar_formulario(db_conn, formulario_id, datos_formulario(nombre="Otro nombre", cupo=99), campos)

    formulario = formularios.obtener_formulario(db_conn, formulario_id)
    assert formulario["nombre"] == "Otro nombre" and formulario["cupo"] == 99
    assert formulario["campos"][0]["etiqueta"] == "Nombre completo"
    assert formulario["campos"][0]["clave"] == "nombre_y_apellido"
    assert formulario["campos"][-1]["clave"] == "comentario"
    assert formularios.listar_respuestas(db_conn, formulario_id, 1, 10)[0][0]["valores"]["nombre_y_apellido"] == "Ana Pérez"


def test_con_respuestas_se_puede_agregar_una_opcion_a_una_lista(db_conn, clean_db):
    formulario_id, campos = _formulario_con_una_respuesta(db_conn)
    campos[-1] = {**campos[-1], "opciones": ["Mañana", "Tarde", "Noche"]}

    formularios.actualizar_formulario(db_conn, formulario_id, datos_formulario(), campos)

    assert formularios.obtener_formulario(db_conn, formulario_id)["campos"][-1]["opciones"] == ["Mañana", "Tarde", "Noche"]


def test_con_respuestas_no_se_puede_quitar_un_campo(db_conn, clean_db):
    formulario_id, campos = _formulario_con_una_respuesta(db_conn)

    with pytest.raises(ReglaDeEdicion):
        formularios.actualizar_formulario(db_conn, formulario_id, datos_formulario(), campos[1:])


def test_con_respuestas_no_se_puede_cambiar_el_tipo_de_un_campo(db_conn, clean_db):
    formulario_id, campos = _formulario_con_una_respuesta(db_conn)
    campos[0] = {**campos[0], "tipo": "texto_largo"}
    campos[3] = {**campos[3], "tipo": "texto"}

    with pytest.raises(ReglaDeEdicion):
        formularios.actualizar_formulario(db_conn, formulario_id, datos_formulario(), campos)


def test_con_respuestas_un_campo_nuevo_tiene_que_ser_opcional(db_conn, clean_db):
    formulario_id, campos = _formulario_con_una_respuesta(db_conn)
    campos.append({"etiqueta": "Obligatorio nuevo", "tipo": "texto", "obligatorio": True, "opciones": None})

    with pytest.raises(ReglaDeEdicion):
        formularios.actualizar_formulario(db_conn, formulario_id, datos_formulario(), campos)


def test_con_respuestas_no_se_puede_quitar_una_opcion(db_conn, clean_db):
    formulario_id, campos = _formulario_con_una_respuesta(db_conn)
    campos[-1] = {**campos[-1], "opciones": ["Mañana", "Noche"]}

    with pytest.raises(ReglaDeEdicion):
        formularios.actualizar_formulario(db_conn, formulario_id, datos_formulario(), campos)


def test_con_respuestas_una_clave_inexistente_se_rechaza(db_conn, clean_db):
    formulario_id, campos = _formulario_con_una_respuesta(db_conn)
    campos.append({"clave": "inventada", "etiqueta": "X", "tipo": "texto", "obligatorio": False, "opciones": None})

    with pytest.raises(ReglaDeEdicion):
        formularios.actualizar_formulario(db_conn, formulario_id, datos_formulario(), campos)


def _id_por_nombre(conn, nombre):
    return next(f["id"] for f in formularios.listar_formularios(conn, None, 1, 100)[0] if f["nombre"] == nombre)


def test_formularios_abiertos_solo_trae_los_activos_con_lugar_y_prioriza_el_vinculado(db_conn, clean_db):
    organismo_id = crear_organismo(db_conn)
    tramite_id = crear_tramite(db_conn, organismo_id)
    crear_formulario(db_conn, organismo_id, nombre="Borrador", estado="borrador")
    crear_formulario(db_conn, organismo_id, nombre="Cerrado", estado="cerrado")
    crear_formulario(db_conn, organismo_id, nombre="Vencido", fecha_cierre=datetime.now(timezone.utc) - timedelta(days=1))
    crear_formulario(db_conn, organismo_id, nombre="Sin cupo", cupo=1)
    formularios.guardar_respuesta(db_conn, _id_por_nombre(db_conn, "Sin cupo"), crear_sesion(db_conn), valores_validos())
    crear_formulario(db_conn, organismo_id, nombre="Aaa común")
    crear_formulario(db_conn, organismo_id, nombre="Zzz vinculado", tramite_id=tramite_id)

    resultado = formularios.formularios_abiertos(db_conn, tramite_id=tramite_id)

    assert [f["nombre"] for f in resultado] == ["Zzz vinculado", "Aaa común"]
    assert [c["clave"] for c in resultado[0]["campos"]] == ["nombre_y_apellido", "dni", "telefono", "participaria_de_la_capacitacion"]


def test_formularios_abiertos_prioriza_por_coincidencia_con_la_consulta_y_respeta_el_limite(db_conn, clean_db):
    organismo_id = crear_organismo(db_conn)
    for nombre in ["Alfa", "Beta", "Gamma", "Delta", "Epsilon", "Zeta"]:
        crear_formulario(db_conn, organismo_id, nombre=nombre, descripcion_uso="Otro tema")
    crear_formulario(
        db_conn, organismo_id, nombre="Zzz Capacitación", descripcion_uso="Inscripción a la capacitación laboral"
    )

    resultado = formularios.formularios_abiertos(db_conn, consulta="quiero anotarme a la capacitación", limite=5)

    assert len(resultado) == 5
    assert resultado[0]["nombre"] == "Zzz Capacitación"


def test_formularios_consultados_en_sesion_lee_las_herramientas_del_historial(db_conn, clean_db):
    organismo_id = crear_organismo(db_conn)
    formulario_id = crear_formulario(db_conn, organismo_id)
    sesion = crear_sesion(db_conn)
    assert formularios.formularios_consultados_en_sesion(db_conn, sesion) == set()

    llamada = [{"id": "call_1", "type": "function", "function": {"name": "buscar_formularios", "arguments": "{}"}}]
    sessions.guardar_mensaje(db_conn, sesion, "assistant", None, tool_calls=llamada)
    sessions.guardar_mensaje(db_conn, sesion, "tool", json.dumps([{"id": formulario_id, "nombre": "X"}]), tool_call_id="call_1")

    assert formularios.formularios_consultados_en_sesion(db_conn, sesion) == {formulario_id}


def test_otras_herramientas_no_cuentan_como_consulta_de_formularios(db_conn, clean_db):
    sesion = crear_sesion(db_conn)
    llamada = [{"id": "call_1", "type": "function", "function": {"name": "buscar_tramite", "arguments": "{}"}}]
    sessions.guardar_mensaje(db_conn, sesion, "assistant", None, tool_calls=llamada)
    sessions.guardar_mensaje(db_conn, sesion, "tool", json.dumps([{"id": "RC-0001"}]), tool_call_id="call_1")

    assert formularios.formularios_consultados_en_sesion(db_conn, sesion) == set()


def test_formularios_respondidos_en_sesion_cuenta_los_distintos_vigentes(db_conn, clean_db):
    organismo_id = crear_organismo(db_conn)
    uno = crear_formulario(db_conn, organismo_id, nombre="Uno")
    otro = crear_formulario(db_conn, organismo_id, nombre="Otro")
    sesion = crear_sesion(db_conn)
    assert formularios.formularios_respondidos_en_sesion(db_conn, sesion) == 0

    formularios.guardar_respuesta(db_conn, uno, sesion, valores_validos(dni="30123456"))
    formularios.guardar_respuesta(db_conn, otro, sesion, valores_validos(dni="30123456"))

    assert formularios.formularios_respondidos_en_sesion(db_conn, sesion) == 2
```

- [ ] **Step 3: Correr los tests para ver que fallan**

Run: `timeout 120 .venv/bin/pytest -q -p no:cacheprovider tests/test_formularios_repository.py 2>&1 | tail -4`
Expected: FAIL (`ModuleNotFoundError: No module named 'agent.admin.formularios_repository'`).

- [ ] **Step 4: Implementar el repositorio**

Crear `backend/agent/admin/formularios_repository.py`:

```python
import json
import re
import unicodedata
from datetime import datetime, timezone

import psycopg

from agent.formularios_validacion import generar_clave, validar_definicion, validar_valores


class ReglaDeEdicion(ValueError):
    """Un cambio que no se permite en un formulario que ya tiene respuestas."""


class FormularioNoDisponible(Exception):
    def __init__(self, motivo: str):
        super().__init__(motivo)
        self.motivo = motivo


class DatosInvalidos(Exception):
    def __init__(self, errores: dict):
        super().__init__("datos inválidos")
        self.errores = errores


class RespuestaDuplicada(Exception):
    """Ya hay una respuesta vigente con ese DNI en el formulario."""


class YaRespondio(Exception):
    """Esta sesión ya envió una respuesta vigente a este formulario."""


def calcular_estado_efectivo(estado, fecha_cierre, cupo, respuestas, ahora=None) -> str:
    ahora = ahora or datetime.now(timezone.utc)
    if estado == "borrador":
        return "borrador"
    if estado == "cerrado":
        return "cerrado"
    if fecha_cierre is not None and ahora >= fecha_cierre:
        return "vencido"
    if cupo is not None and respuestas >= cupo:
        return "cupo_completo"
    return "abierto"


_SELECT = """
    SELECT f.id, f.organismo_id, o.nombre, f.nombre, f.descripcion_uso, f.aviso_finalidad, f.tramite_id,
           f.estado, f.fecha_cierre, f.cupo, f.creado_por_email, f.creado_en, f.actualizado_en,
           (SELECT COUNT(*) FROM formulario_respuestas r WHERE r.formulario_id = f.id AND r.eliminada_en IS NULL),
           EXISTS (SELECT 1 FROM formulario_respuestas r WHERE r.formulario_id = f.id)
    FROM formularios f
    JOIN organismos o ON o.id = f.organismo_id
"""


def _fila_a_formulario(fila) -> dict:
    (id_, organismo_id, organismo, nombre, descripcion_uso, aviso_finalidad, tramite_id, estado,
     fecha_cierre, cupo, creado_por_email, creado_en, actualizado_en, respuestas, hay_respuestas) = fila
    return {
        "id": str(id_),
        "organismo_id": organismo_id,
        "organismo": organismo,
        "nombre": nombre,
        "descripcion_uso": descripcion_uso,
        "aviso_finalidad": aviso_finalidad,
        "tramite_id": tramite_id,
        "estado": estado,
        "estado_efectivo": calcular_estado_efectivo(estado, fecha_cierre, cupo, respuestas),
        "fecha_cierre": fecha_cierre.isoformat() if fecha_cierre else None,
        "cupo": cupo,
        "respuestas": respuestas,
        "hay_respuestas": hay_respuestas,
        "creado_por_email": creado_por_email,
        "creado_en": creado_en.isoformat(),
        "actualizado_en": actualizado_en.isoformat(),
    }


def _campos(conn, formulario_id: str) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT clave, etiqueta, tipo, obligatorio, opciones
            FROM formulario_campos WHERE formulario_id = %s ORDER BY orden
            """,
            (formulario_id,),
        )
        return [
            {"clave": clave, "etiqueta": etiqueta, "tipo": tipo, "obligatorio": obligatorio, "opciones": opciones}
            for clave, etiqueta, tipo, obligatorio, opciones in cur.fetchall()
        ]


def _opciones_limpias(campo: dict):
    return [o.strip() for o in campo["opciones"]] if campo["tipo"] == "opcion" else None


def _insertar_campo(conn, formulario_id: str, campo: dict, clave: str, orden: int) -> None:
    opciones = _opciones_limpias(campo)
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO formulario_campos (formulario_id, clave, etiqueta, tipo, obligatorio, opciones, orden)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                formulario_id,
                clave,
                campo["etiqueta"].strip(),
                campo["tipo"],
                campo.get("obligatorio", True),
                json.dumps(opciones) if opciones is not None else None,
                orden,
            ),
        )


def crear_formulario(conn, organismo_id: int, datos: dict, campos: list[dict], creado_por_email: str) -> str:
    validar_definicion(campos)
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO formularios
                (organismo_id, nombre, descripcion_uso, aviso_finalidad, tramite_id, estado, fecha_cierre, cupo,
                 creado_por_email)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                organismo_id,
                datos["nombre"].strip(),
                datos.get("descripcion_uso", ""),
                datos.get("aviso_finalidad", ""),
                datos.get("tramite_id"),
                datos.get("estado", "borrador"),
                datos.get("fecha_cierre"),
                datos.get("cupo"),
                creado_por_email,
            ),
        )
        formulario_id = str(cur.fetchone()[0])
    usadas = {c["clave"] for c in campos if c.get("clave")}
    for orden, campo in enumerate(campos):
        clave = campo.get("clave")
        if not clave:
            clave = generar_clave(campo["etiqueta"], usadas)
            usadas.add(clave)
        _insertar_campo(conn, formulario_id, campo, clave, orden)
    return formulario_id


def obtener_formulario(conn, formulario_id: str) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(_SELECT + " WHERE f.id = %s", (formulario_id,))
        fila = cur.fetchone()
    if fila is None:
        return None
    formulario = _fila_a_formulario(fila)
    formulario["campos"] = _campos(conn, formulario_id)
    return formulario


def listar_formularios(conn, organismo_id: int | None, page: int, page_size: int) -> tuple[list[dict], int]:
    donde = ""
    parametros: tuple = ()
    if organismo_id is not None:
        donde = " WHERE f.organismo_id = %s"
        parametros = (organismo_id,)
    with conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM formularios f{donde}", parametros)
        total = cur.fetchone()[0]
        cur.execute(
            _SELECT + donde + " ORDER BY f.creado_en DESC, f.id LIMIT %s OFFSET %s",
            parametros + (page_size, (page - 1) * page_size),
        )
        return [_fila_a_formulario(f) for f in cur.fetchall()], total


def actualizar_formulario(conn, formulario_id: str, datos: dict, campos: list[dict]) -> None:
    validar_definicion(campos)
    actuales = {c["clave"]: c for c in _campos(conn, formulario_id)}
    with conn.cursor() as cur:
        cur.execute("SELECT EXISTS (SELECT 1 FROM formulario_respuestas WHERE formulario_id = %s)", (formulario_id,))
        con_respuestas = cur.fetchone()[0]

    if con_respuestas:
        enviadas = {c["clave"] for c in campos if c.get("clave")}
        for clave, actual in actuales.items():
            if clave not in enviadas:
                raise ReglaDeEdicion(f"No se puede quitar el campo «{actual['etiqueta']}» porque ya tiene respuestas.")
        for campo in campos:
            clave = campo.get("clave")
            if clave is None:
                if campo.get("obligatorio", True):
                    raise ReglaDeEdicion("Los campos nuevos tienen que ser opcionales porque el formulario ya tiene respuestas.")
                continue
            actual = actuales.get(clave)
            if actual is None:
                raise ReglaDeEdicion(f"El campo «{clave}» no existe en el formulario.")
            if campo["tipo"] != actual["tipo"]:
                raise ReglaDeEdicion(f"No se puede cambiar el tipo del campo «{actual['etiqueta']}» porque ya tiene respuestas.")
            if actual["tipo"] == "opcion":
                nuevas = {o.strip().lower() for o in campo["opciones"]}
                if not {o.strip().lower() for o in actual["opciones"]} <= nuevas:
                    raise ReglaDeEdicion(f"No se pueden quitar opciones de «{actual['etiqueta']}» porque ya tiene respuestas.")

    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE formularios
            SET nombre = %s, descripcion_uso = %s, aviso_finalidad = %s, tramite_id = %s, estado = %s,
                fecha_cierre = %s, cupo = %s, actualizado_en = now()
            WHERE id = %s
            """,
            (
                datos["nombre"].strip(),
                datos.get("descripcion_uso", ""),
                datos.get("aviso_finalidad", ""),
                datos.get("tramite_id"),
                datos.get("estado", "borrador"),
                datos.get("fecha_cierre"),
                datos.get("cupo"),
                formulario_id,
            ),
        )
        if not con_respuestas:
            conservadas = [c["clave"] for c in campos if c.get("clave") in actuales]
            cur.execute(
                "DELETE FROM formulario_campos WHERE formulario_id = %s AND clave <> ALL(%s)",
                (formulario_id, conservadas),
            )
    usadas = set(actuales) | {c["clave"] for c in campos if c.get("clave")}
    for orden, campo in enumerate(campos):
        clave = campo.get("clave")
        if clave in actuales:
            opciones = _opciones_limpias(campo)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE formulario_campos SET etiqueta = %s, obligatorio = %s, opciones = %s, orden = %s
                    WHERE formulario_id = %s AND clave = %s
                    """,
                    (
                        campo["etiqueta"].strip(),
                        campo.get("obligatorio", True),
                        json.dumps(opciones) if opciones is not None else None,
                        orden,
                        formulario_id,
                        clave,
                    ),
                )
        else:
            nueva = clave or generar_clave(campo["etiqueta"], usadas)
            usadas.add(nueva)
            _insertar_campo(conn, formulario_id, campo, nueva, orden)


def guardar_respuesta(conn, formulario_id: str, session_id: str, valores: dict) -> dict:
    with conn.cursor() as cur:
        # Se bloquea el formulario hasta el final de la transacción: dos envíos simultáneos no superan el cupo.
        cur.execute(
            "SELECT estado, fecha_cierre, cupo, organismo_id, nombre FROM formularios WHERE id = %s FOR UPDATE",
            (formulario_id,),
        )
        fila = cur.fetchone()
        if fila is None:
            raise FormularioNoDisponible("cerrado")
        estado, fecha_cierre, cupo, organismo_id, nombre = fila
        cur.execute(
            "SELECT COUNT(*) FROM formulario_respuestas WHERE formulario_id = %s AND eliminada_en IS NULL",
            (formulario_id,),
        )
        vigentes = cur.fetchone()[0]
        efectivo = calcular_estado_efectivo(estado, fecha_cierre, cupo, vigentes)
        if efectivo == "cupo_completo":
            raise FormularioNoDisponible("cupo")
        if efectivo != "abierto":
            raise FormularioNoDisponible("cerrado")
        cur.execute(
            """
            SELECT 1 FROM formulario_respuestas
            WHERE formulario_id = %s AND session_id = %s AND eliminada_en IS NULL
            """,
            (formulario_id, session_id),
        )
        if cur.fetchone() is not None:
            raise YaRespondio()

    campos = _campos(conn, formulario_id)
    normalizados, errores = validar_valores(campos, valores)
    if errores:
        raise DatosInvalidos(errores)
    dni = next((normalizados[c["clave"]] for c in campos if c["tipo"] == "dni" and c["clave"] in normalizados), None)
    try:
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO formulario_respuestas (formulario_id, session_id, valores, dni)
                    VALUES (%s, %s, %s, %s) RETURNING id
                    """,
                    (formulario_id, session_id, json.dumps(normalizados), dni),
                )
                respuesta_id = str(cur.fetchone()[0])
    except psycopg.errors.UniqueViolation:
        raise RespuestaDuplicada() from None
    return {
        "id": respuesta_id,
        "formulario": nombre,
        "organismo_id": organismo_id,
        "valores": normalizados,
        "campos": campos,
    }


def _fila_a_respuesta(fila) -> dict:
    id_, session_id, creado_en, valores = fila
    return {"id": str(id_), "session_id": str(session_id), "creado_en": creado_en.isoformat(), "valores": valores}


def listar_respuestas(conn, formulario_id: str, page: int, page_size: int) -> tuple[list[dict], int]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM formulario_respuestas WHERE formulario_id = %s AND eliminada_en IS NULL",
            (formulario_id,),
        )
        total = cur.fetchone()[0]
        cur.execute(
            """
            SELECT id, session_id, creado_en, valores FROM formulario_respuestas
            WHERE formulario_id = %s AND eliminada_en IS NULL
            ORDER BY creado_en DESC, id LIMIT %s OFFSET %s
            """,
            (formulario_id, page_size, (page - 1) * page_size),
        )
        return [_fila_a_respuesta(f) for f in cur.fetchall()], total


def todas_las_respuestas(conn, formulario_id: str) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, session_id, creado_en, valores FROM formulario_respuestas
            WHERE formulario_id = %s AND eliminada_en IS NULL ORDER BY creado_en, id
            """,
            (formulario_id,),
        )
        return [_fila_a_respuesta(f) for f in cur.fetchall()]


def obtener_respuesta(conn, formulario_id: str, respuesta_id: str) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, session_id, creado_en, valores FROM formulario_respuestas
            WHERE formulario_id = %s AND id = %s AND eliminada_en IS NULL
            """,
            (formulario_id, respuesta_id),
        )
        fila = cur.fetchone()
    return _fila_a_respuesta(fila) if fila else None


def borrar_respuesta(conn, formulario_id: str, respuesta_id: str, email: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE formulario_respuestas SET eliminada_en = now(), eliminada_por_email = %s
            WHERE formulario_id = %s AND id = %s AND eliminada_en IS NULL
            """,
            (email, formulario_id, respuesta_id),
        )
        return cur.rowcount == 1


def _sin_acentos(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


def _palabras(texto: str) -> set[str]:
    return {p for p in re.findall(r"[a-z0-9]+", _sin_acentos(texto.lower())) if len(p) >= 4}


def formularios_abiertos(conn, tramite_id: str | None = None, consulta: str | None = None, limite: int = 5) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(_SELECT + " WHERE f.estado = 'activo' ORDER BY f.nombre")
        todos = [_fila_a_formulario(f) for f in cur.fetchall()]
    abiertos = [f for f in todos if f["estado_efectivo"] == "abierto"]
    palabras_consulta = _palabras(consulta or "")

    def puntaje(formulario: dict) -> int:
        vinculado = 100 if tramite_id and formulario["tramite_id"] == tramite_id else 0
        coincidencias = len(palabras_consulta & _palabras(formulario["nombre"] + " " + formulario["descripcion_uso"]))
        return vinculado + coincidencias

    abiertos.sort(key=lambda f: (-puntaje(f), f["nombre"]))
    elegidos = abiertos[:limite]
    for formulario in elegidos:
        formulario["campos"] = _campos(conn, formulario["id"])
    return elegidos


def formularios_consultados_en_sesion(conn, session_id: str) -> set[str]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT DISTINCT t.contenido
            FROM mensajes t
            JOIN mensajes a ON a.session_id = t.session_id AND a.rol = 'assistant' AND a.tool_calls IS NOT NULL
            WHERE t.session_id = %s AND t.rol = 'tool'
              AND EXISTS (
                  SELECT 1 FROM jsonb_array_elements(a.tool_calls) llamada
                  WHERE llamada->>'id' = t.tool_call_id AND llamada->'function'->>'name' = 'buscar_formularios'
              )
            """,
            (session_id,),
        )
        contenidos = [fila[0] for fila in cur.fetchall()]
    ids: set[str] = set()
    for contenido in contenidos:
        try:
            lista = json.loads(contenido)
        except (TypeError, ValueError):
            continue
        if isinstance(lista, list):
            ids.update(str(item["id"]) for item in lista if isinstance(item, dict) and "id" in item)
    return ids


def formularios_respondidos_en_sesion(conn, session_id: str) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(DISTINCT formulario_id) FROM formulario_respuestas WHERE session_id = %s AND eliminada_en IS NULL",
            (session_id,),
        )
        return cur.fetchone()[0]
```

- [ ] **Step 5: Correr los tests del repositorio**

Run: `timeout 180 .venv/bin/pytest -q -p no:cacheprovider tests/test_formularios_repository.py 2>&1 | tail -4`
Expected: PASS (todos, incluido el de concurrencia).

Run: `timeout 280 .venv/bin/pytest -q -p no:cacheprovider 2>&1 | tail -1`
Expected: toda la suite PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/agent/admin/formularios_repository.py backend/tests/formularios_helpers.py backend/tests/test_formularios_repository.py
git commit -m "feat: repositorio de formularios con cupo, DNI único y reglas de edición"
```

---

### Task 4: Endpoints `/admin/formularios` (permisos, aislamiento por organismo, CSV)

**Files:**
- Modify: `backend/agent/api.py`
- Modify: `backend/tests/formularios_helpers.py` (helpers de API)
- Test: `backend/tests/test_admin_formularios_api.py`

**Interfaces:**
- Consumes: `formularios_repository` (Task 3), `requiere_gestor_de_formularios` (Task 1), `formularios_csv.a_csv` (Task 2), `admin_tramites_repository.obtener_organismo_id_de_tramite` y `obtener_nombre_organismo`, `admin_chats_repository.obtener_mensajes_completos`.
- Produces (todas bajo `/admin/formularios`; "cualquier admin" = `requiere_admin`, "gestor" = `requiere_gestor_de_formularios`):
  - `GET /admin/formularios?page&page_size` → `{formularios, total, page, page_size}` (cualquier admin; el de organismo ve solo los suyos).
  - `POST /admin/formularios` (gestor) → `{id}`. Cuerpo: `organismo_id?` (solo lo usa el super admin y es obligatorio para él; el de organismo usa el suyo), `nombre`, `descripcion_uso`, `aviso_finalidad`, `tramite_id?`, `estado`, `fecha_cierre?` (ISO), `cupo?`, `campos` (`clave?`, `etiqueta`, `tipo`, `obligatorio`, `opciones?`).
  - `GET /admin/formularios/{id}` → el dict de `obtener_formulario`; `PUT /admin/formularios/{id}` (gestor) → `{ok: true}`.
  - `GET /admin/formularios/{id}/respuestas?page&page_size` → `{respuestas: [{id, creado_en, valores}], campos, total, page, page_size}`.
  - `GET /admin/formularios/{id}/respuestas.csv` → archivo `text/csv` (con BOM para Excel).
  - `GET /admin/formularios/{id}/respuestas/{rid}` → `{id, session_id, creado_en, valores, formulario: {id, nombre}, campos, mensajes}`.
  - `DELETE /admin/formularios/{id}/respuestas/{rid}` (gestor) → `{ok: true}`.
  - Errores: 401 sin sesión, 403 sin permiso de edición, 404 formulario/respuesta ajenos o inexistentes, 400 definición o vínculo inválidos, 409 regla de edición, 422 parámetros inválidos.

- [ ] **Step 1: Agregar helpers de API y escribir los tests que fallan**

Agregar al final de `backend/tests/formularios_helpers.py`:

```python


# ---- helpers para los tests de la API del panel ----
from agent.admin import repository as admin_repository  # noqa: E402
from agent.admin import security as admin_security  # noqa: E402


class FakeConnCtx:
    def __init__(self, conn):
        self._conn = conn

    def __enter__(self):
        return self._conn

    def __exit__(self, *args):
        pass


class FakePool:
    def __init__(self, conn):
        self._conn = conn

    def connection(self):
        return FakeConnCtx(self._conn)


def loguear(client, conn, rol="admin_organismo", organismo_id=None, email="admin@organismo.gob.ar", puede=True):
    password = "secreta123"
    admin_repository.crear_admin(
        conn, email, admin_security.hash_password(password), rol, organismo_id, puede_crear_formularios=puede
    )
    conn.commit()
    client.post("/admin/login", json={"email": email, "password": password})


def cuerpo_formulario(**cambios) -> dict:
    cuerpo = {
        "nombre": "Inscripción a la capacitación",
        "descripcion_uso": "Inscripción a la capacitación de la Subsecretaría de Trabajo",
        "aviso_finalidad": "La Subsecretaría de Trabajo usa tus datos para inscribirte.",
        "estado": "activo",
        "cupo": 40,
        "campos": [
            {"etiqueta": "Nombre y apellido", "tipo": "texto", "obligatorio": True},
            {"etiqueta": "DNI", "tipo": "dni", "obligatorio": True},
            {"etiqueta": "Teléfono", "tipo": "telefono", "obligatorio": True},
            {"etiqueta": "¿Participaría de la capacitación?", "tipo": "si_no", "obligatorio": True},
        ],
    }
    cuerpo.update(cambios)
    return cuerpo
```

Crear `backend/tests/test_admin_formularios_api.py`:

```python
import pytest
from fastapi.testclient import TestClient

from agent import api, sessions
from agent.admin import formularios_repository as formularios
from agent.api import obtener_pool
from tests.formularios_helpers import (
    FakePool,
    crear_formulario,
    crear_organismo,
    crear_sesion,
    crear_tramite,
    cuerpo_formulario,
    loguear,
    valores_validos,
)


@pytest.fixture
def cliente(db_conn, clean_db, monkeypatch):
    monkeypatch.setenv("ADMIN_JWT_SECRET", "secreto-de-test")
    api.app.dependency_overrides[obtener_pool] = lambda: FakePool(db_conn)
    yield TestClient(api.app, base_url="https://testserver")
    api.app.dependency_overrides.clear()


def _con_respuesta(db_conn, organismo_id, **valores):
    formulario_id = crear_formulario(db_conn, organismo_id)
    sesion = crear_sesion(db_conn)
    respuesta = formularios.guardar_respuesta(db_conn, formulario_id, sesion, valores_validos(**valores))
    db_conn.commit()
    return formulario_id, respuesta["id"], sesion


def test_sin_sesion_todo_devuelve_401(cliente):
    assert cliente.get("/admin/formularios").status_code == 401
    assert cliente.post("/admin/formularios", json=cuerpo_formulario()).status_code == 401
    assert cliente.get("/admin/formularios/00000000-0000-0000-0000-000000000000/respuestas.csv").status_code == 401


def test_un_usuario_no_habilitado_ve_pero_no_edita(cliente, db_conn):
    organismo_id = crear_organismo(db_conn)
    formulario_id, respuesta_id, _ = _con_respuesta(db_conn, organismo_id)
    loguear(cliente, db_conn, organismo_id=organismo_id, puede=False)

    assert cliente.get("/admin/formularios").status_code == 200
    assert cliente.get(f"/admin/formularios/{formulario_id}").status_code == 200
    assert cliente.get(f"/admin/formularios/{formulario_id}/respuestas").status_code == 200
    assert cliente.get(f"/admin/formularios/{formulario_id}/respuestas.csv").status_code == 200
    assert cliente.get(f"/admin/formularios/{formulario_id}/respuestas/{respuesta_id}").status_code == 200
    assert cliente.post("/admin/formularios", json=cuerpo_formulario()).status_code == 403
    assert cliente.put(f"/admin/formularios/{formulario_id}", json=cuerpo_formulario()).status_code == 403
    assert cliente.delete(f"/admin/formularios/{formulario_id}/respuestas/{respuesta_id}").status_code == 403
    assert formularios.listar_respuestas(db_conn, formulario_id, 1, 10)[1] == 1


def test_un_usuario_habilitado_crea_un_formulario_en_su_organismo(cliente, db_conn):
    organismo_id = crear_organismo(db_conn)
    otro = crear_organismo(db_conn, "Registro Civil")
    loguear(cliente, db_conn, organismo_id=organismo_id)

    respuesta = cliente.post("/admin/formularios", json=cuerpo_formulario(organismo_id=otro))

    assert respuesta.status_code == 200
    formulario = formularios.obtener_formulario(db_conn, respuesta.json()["id"])
    assert formulario["organismo_id"] == organismo_id
    assert formulario["creado_por_email"] == "admin@organismo.gob.ar"
    assert [c["clave"] for c in formulario["campos"]][:2] == ["nombre_y_apellido", "dni"]


def test_el_super_admin_elige_el_organismo(cliente, db_conn):
    organismo_id = crear_organismo(db_conn)
    loguear(cliente, db_conn, rol="super_admin", puede=False)

    sin_organismo = cliente.post("/admin/formularios", json=cuerpo_formulario())
    inexistente = cliente.post("/admin/formularios", json=cuerpo_formulario(organismo_id=99999))
    bien = cliente.post("/admin/formularios", json=cuerpo_formulario(organismo_id=organismo_id))

    assert sin_organismo.status_code == 400 and inexistente.status_code == 400
    assert bien.status_code == 200
    assert formularios.obtener_formulario(db_conn, bien.json()["id"])["organismo_id"] == organismo_id


def test_una_definicion_invalida_devuelve_400(cliente, db_conn):
    organismo_id = crear_organismo(db_conn)
    loguear(cliente, db_conn, organismo_id=organismo_id)
    dos_dni = cuerpo_formulario()
    dos_dni["campos"].append({"etiqueta": "Otro DNI", "tipo": "dni", "obligatorio": False})

    respuesta = cliente.post("/admin/formularios", json=dos_dni)

    assert respuesta.status_code == 400 and "DNI" in respuesta.json()["detail"]
    assert formularios.listar_formularios(db_conn, None, 1, 10)[1] == 0


@pytest.mark.parametrize("cambios", [{"nombre": ""}, {"cupo": 0}, {"campos": []}, {"estado": "inventado"}])
def test_el_cuerpo_invalido_devuelve_422(cliente, db_conn, cambios):
    organismo_id = crear_organismo(db_conn)
    loguear(cliente, db_conn, organismo_id=organismo_id)

    assert cliente.post("/admin/formularios", json=cuerpo_formulario(**cambios)).status_code == 422


def test_vincular_un_tramite_de_otro_organismo_se_rechaza(cliente, db_conn):
    trabajo = crear_organismo(db_conn)
    registro = crear_organismo(db_conn, "Registro Civil")
    ajeno = crear_tramite(db_conn, registro, "RC-0001", "Actas")
    propio = crear_tramite(db_conn, trabajo, "TR-0001", "Denuncia laboral")
    loguear(cliente, db_conn, organismo_id=trabajo)

    rechazado = cliente.post("/admin/formularios", json=cuerpo_formulario(tramite_id=ajeno))
    inexistente = cliente.post("/admin/formularios", json=cuerpo_formulario(tramite_id="NO-0000"))
    aceptado = cliente.post("/admin/formularios", json=cuerpo_formulario(tramite_id=propio))

    assert rechazado.status_code == 400 and inexistente.status_code == 400
    assert aceptado.status_code == 200
    assert formularios.obtener_formulario(db_conn, aceptado.json()["id"])["tramite_id"] == propio


def test_la_lista_se_limita_al_organismo_y_se_pagina(cliente, db_conn):
    trabajo = crear_organismo(db_conn)
    registro = crear_organismo(db_conn, "Registro Civil")
    for nombre in ("A", "B", "C"):
        crear_formulario(db_conn, trabajo, nombre=nombre)
    crear_formulario(db_conn, registro, nombre="Ajeno")
    db_conn.commit()
    loguear(cliente, db_conn, organismo_id=trabajo, puede=False)

    pagina = cliente.get("/admin/formularios", params={"page": 1, "page_size": 2}).json()

    assert pagina["total"] == 3 and len(pagina["formularios"]) == 2
    assert pagina["page"] == 1 and pagina["page_size"] == 2
    assert "Ajeno" not in {f["nombre"] for f in pagina["formularios"]}


def test_el_super_admin_ve_los_formularios_de_todos(cliente, db_conn):
    crear_formulario(db_conn, crear_organismo(db_conn), nombre="A")
    crear_formulario(db_conn, crear_organismo(db_conn, "Registro Civil"), nombre="B")
    db_conn.commit()
    loguear(cliente, db_conn, rol="super_admin", puede=False)

    assert cliente.get("/admin/formularios").json()["total"] == 2


@pytest.mark.parametrize("params", [{"page": 0}, {"page_size": 0}, {"page_size": 101}])
def test_la_lista_rechaza_paginacion_invalida(cliente, db_conn, params):
    loguear(cliente, db_conn, rol="super_admin", puede=False)

    assert cliente.get("/admin/formularios", params=params).status_code == 422


def test_lo_de_otro_organismo_devuelve_404_en_todos_los_endpoints(cliente, db_conn):
    trabajo = crear_organismo(db_conn)
    registro = crear_organismo(db_conn, "Registro Civil")
    formulario_id, respuesta_id, _ = _con_respuesta(db_conn, registro)
    loguear(cliente, db_conn, organismo_id=trabajo, puede=True)
    base = f"/admin/formularios/{formulario_id}"

    assert cliente.get(base).status_code == 404
    assert cliente.put(base, json=cuerpo_formulario()).status_code == 404
    assert cliente.get(f"{base}/respuestas").status_code == 404
    assert cliente.get(f"{base}/respuestas.csv").status_code == 404
    assert cliente.get(f"{base}/respuestas/{respuesta_id}").status_code == 404
    assert cliente.delete(f"{base}/respuestas/{respuesta_id}").status_code == 404
    assert formularios.listar_respuestas(db_conn, formulario_id, 1, 10)[1] == 1
    assert formularios.obtener_formulario(db_conn, formulario_id)["nombre"] == "Inscripción a la capacitación"


def test_formulario_inexistente_404_y_id_mal_formado_422(cliente, db_conn):
    loguear(cliente, db_conn, rol="super_admin", puede=False)

    assert cliente.get("/admin/formularios/00000000-0000-0000-0000-000000000000").status_code == 404
    assert cliente.get("/admin/formularios/no-es-uuid").status_code == 422


def test_editar_un_formulario_propio(cliente, db_conn):
    organismo_id = crear_organismo(db_conn)
    formulario_id = crear_formulario(db_conn, organismo_id)
    db_conn.commit()
    loguear(cliente, db_conn, organismo_id=organismo_id)
    cuerpo = cuerpo_formulario(nombre="Nuevo nombre", cupo=10)
    cuerpo["campos"] = formularios.obtener_formulario(db_conn, formulario_id)["campos"]

    respuesta = cliente.put(f"/admin/formularios/{formulario_id}", json=cuerpo)

    assert respuesta.status_code == 200
    formulario = formularios.obtener_formulario(db_conn, formulario_id)
    assert formulario["nombre"] == "Nuevo nombre" and formulario["cupo"] == 10


def test_una_regla_de_edicion_devuelve_409(cliente, db_conn):
    organismo_id = crear_organismo(db_conn)
    formulario_id, _, _ = _con_respuesta(db_conn, organismo_id)
    loguear(cliente, db_conn, organismo_id=organismo_id)
    cuerpo = cuerpo_formulario()
    cuerpo["campos"] = formularios.obtener_formulario(db_conn, formulario_id)["campos"][:2]

    respuesta = cliente.put(f"/admin/formularios/{formulario_id}", json=cuerpo)

    assert respuesta.status_code == 409 and "respuestas" in respuesta.json()["detail"]
    assert len(formularios.obtener_formulario(db_conn, formulario_id)["campos"]) == 4


def test_listar_respuestas_incluye_los_campos_para_armar_la_tabla(cliente, db_conn):
    organismo_id = crear_organismo(db_conn)
    formulario_id, respuesta_id, _ = _con_respuesta(db_conn, organismo_id)
    loguear(cliente, db_conn, organismo_id=organismo_id, puede=False)

    cuerpo = cliente.get(f"/admin/formularios/{formulario_id}/respuestas").json()

    assert cuerpo["total"] == 1
    assert cuerpo["respuestas"][0]["id"] == respuesta_id
    assert cuerpo["respuestas"][0]["valores"]["dni"] == "30123456"
    assert [c["clave"] for c in cuerpo["campos"]][1] == "dni"


def test_el_csv_se_descarga_con_bom_y_sin_formulas(cliente, db_conn):
    organismo_id = crear_organismo(db_conn)
    formulario_id, _, _ = _con_respuesta(db_conn, organismo_id, nombre="=1+1")
    loguear(cliente, db_conn, organismo_id=organismo_id, puede=False)

    respuesta = cliente.get(f"/admin/formularios/{formulario_id}/respuestas.csv")

    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"].startswith("text/csv")
    assert "attachment" in respuesta.headers["content-disposition"]
    assert respuesta.headers["content-disposition"].endswith('-respuestas.csv"')
    assert respuesta.content.startswith(b"\xef\xbb\xbf")
    texto = respuesta.content.decode("utf-8-sig")
    assert texto.splitlines()[0].startswith("Fecha,Nombre y apellido,DNI")
    assert "'=1+1" in texto


def test_el_detalle_de_una_respuesta_trae_la_conversacion_de_origen(cliente, db_conn):
    organismo_id = crear_organismo(db_conn)
    formulario_id, respuesta_id, sesion = _con_respuesta(db_conn, organismo_id)
    sessions.guardar_mensaje(db_conn, sesion, "user", "Quiero anotarme a la capacitación")
    db_conn.commit()
    loguear(cliente, db_conn, organismo_id=organismo_id, puede=False)

    cuerpo = cliente.get(f"/admin/formularios/{formulario_id}/respuestas/{respuesta_id}").json()

    assert cuerpo["session_id"] == sesion
    assert cuerpo["formulario"]["nombre"] == "Inscripción a la capacitación"
    assert any(m["contenido"] == "Quiero anotarme a la capacitación" for m in cuerpo["mensajes"])


def test_pedir_una_respuesta_con_el_id_de_otro_formulario_devuelve_404(cliente, db_conn):
    organismo_id = crear_organismo(db_conn)
    _, respuesta_id, _ = _con_respuesta(db_conn, organismo_id)
    otro = crear_formulario(db_conn, organismo_id, nombre="Otro")
    db_conn.commit()
    loguear(cliente, db_conn, organismo_id=organismo_id)

    assert cliente.get(f"/admin/formularios/{otro}/respuestas/{respuesta_id}").status_code == 404
    assert cliente.delete(f"/admin/formularios/{otro}/respuestas/{respuesta_id}").status_code == 404


def test_borrar_una_respuesta_la_saca_de_la_lista_y_registra_quien(cliente, db_conn):
    organismo_id = crear_organismo(db_conn)
    formulario_id, respuesta_id, _ = _con_respuesta(db_conn, organismo_id)
    loguear(cliente, db_conn, organismo_id=organismo_id)

    assert cliente.delete(f"/admin/formularios/{formulario_id}/respuestas/{respuesta_id}").status_code == 200

    assert cliente.get(f"/admin/formularios/{formulario_id}/respuestas").json()["total"] == 0
    assert cliente.delete(f"/admin/formularios/{formulario_id}/respuestas/{respuesta_id}").status_code == 404
    with db_conn.cursor() as cur:
        cur.execute("SELECT eliminada_por_email FROM formulario_respuestas WHERE id = %s", (respuesta_id,))
        assert cur.fetchone()[0] == "admin@organismo.gob.ar"


def test_retirar_el_permiso_a_un_usuario_con_sesion_iniciada_le_quita_la_edicion(cliente, db_conn):
    organismo_id = crear_organismo(db_conn)
    loguear(cliente, db_conn, organismo_id=organismo_id, puede=True)
    assert cliente.post("/admin/formularios", json=cuerpo_formulario()).status_code == 200

    with db_conn.cursor() as cur:
        cur.execute("UPDATE admins SET puede_crear_formularios = false WHERE email = 'admin@organismo.gob.ar'")
    db_conn.commit()

    assert cliente.post("/admin/formularios", json=cuerpo_formulario()).status_code == 403
    assert cliente.get("/admin/formularios").status_code == 200


def test_un_usuario_inactivo_no_gestiona_aunque_tenga_el_permiso(cliente, db_conn):
    organismo_id = crear_organismo(db_conn)
    loguear(cliente, db_conn, organismo_id=organismo_id, puede=True)
    with db_conn.cursor() as cur:
        cur.execute("UPDATE admins SET activo = false WHERE email = 'admin@organismo.gob.ar'")
    db_conn.commit()

    assert cliente.post("/admin/formularios", json=cuerpo_formulario()).status_code == 403


def test_el_super_admin_gestiona_formularios_de_cualquier_organismo(cliente, db_conn):
    organismo_id = crear_organismo(db_conn)
    formulario_id, respuesta_id, _ = _con_respuesta(db_conn, organismo_id)
    loguear(cliente, db_conn, rol="super_admin", puede=False)
    cuerpo = cuerpo_formulario(nombre="Editado por el super admin")
    cuerpo["campos"] = formularios.obtener_formulario(db_conn, formulario_id)["campos"]

    assert cliente.put(f"/admin/formularios/{formulario_id}", json=cuerpo).status_code == 200
    assert cliente.delete(f"/admin/formularios/{formulario_id}/respuestas/{respuesta_id}").status_code == 200
```

- [ ] **Step 2: Correr los tests para ver que fallan**

Run (desde `backend/`): `timeout 120 .venv/bin/pytest -q -p no:cacheprovider tests/test_admin_formularios_api.py 2>&1 | tail -4`
Expected: FAIL (la mayoría con 404 en lugar del código esperado: los endpoints no existen).

- [ ] **Step 3: Implementar los endpoints**

En `backend/agent/api.py`, asegurar estos imports arriba (agregar los que falten): `from datetime import datetime, timezone`, `from agent import formularios_csv` (junto a los otros `from agent import ...`), `from agent.admin import formularios_repository` y `from agent.formularios_validacion import generar_clave`.

Agregar al final del archivo, después de los endpoints de contacto:

```python
# ---------- Formularios por organismo ----------


class CampoFormularioPayload(BaseModel):
    clave: str | None = None
    etiqueta: str = Field(min_length=1, max_length=120)
    tipo: Literal["texto", "texto_largo", "dni", "telefono", "email", "numero", "fecha", "si_no", "opcion"]
    obligatorio: bool = True
    opciones: list[str] | None = None


class FormularioPayload(BaseModel):
    organismo_id: int | None = None
    nombre: str = Field(min_length=1, max_length=150)
    descripcion_uso: str = Field(default="", max_length=500)
    aviso_finalidad: str = Field(default="", max_length=500)
    tramite_id: str | None = None
    estado: Literal["borrador", "activo", "cerrado"] = "borrador"
    fecha_cierre: datetime | None = None
    cupo: int | None = Field(default=None, gt=0)
    campos: list[CampoFormularioPayload] = Field(min_length=1, max_length=30)


def _cargar_formulario_de_mi_organismo(conn, admin: AdminActual, formulario_id: uuid.UUID) -> dict:
    formulario = formularios_repository.obtener_formulario(conn, str(formulario_id))
    if formulario is None or (admin.rol == "admin_organismo" and formulario["organismo_id"] != admin.organismo_id):
        raise HTTPException(status_code=404, detail="Formulario no encontrado")
    return formulario


def _datos_de_formulario(conn, request: FormularioPayload, organismo_id: int) -> dict:
    if request.tramite_id is not None:
        if admin_tramites_repository.obtener_organismo_id_de_tramite(conn, request.tramite_id) != organismo_id:
            raise HTTPException(status_code=400, detail="El trámite no pertenece al organismo del formulario")
    fecha_cierre = request.fecha_cierre
    if fecha_cierre is not None and fecha_cierre.tzinfo is None:
        fecha_cierre = fecha_cierre.replace(tzinfo=timezone.utc)
    return {
        "nombre": request.nombre,
        "descripcion_uso": request.descripcion_uso,
        "aviso_finalidad": request.aviso_finalidad,
        "tramite_id": request.tramite_id,
        "estado": request.estado,
        "fecha_cierre": fecha_cierre,
        "cupo": request.cupo,
    }


@app.get("/admin/formularios")
def admin_listar_formularios(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin: AdminActual = Depends(requiere_admin),
    pool=Depends(obtener_pool),
):
    with pool.connection() as conn:
        organismo_id = admin.organismo_id if admin.rol == "admin_organismo" else None
        lista, total = formularios_repository.listar_formularios(conn, organismo_id, page, page_size)
    return {"formularios": lista, "total": total, "page": page, "page_size": page_size}


@app.post("/admin/formularios")
def admin_crear_formulario(
    request: FormularioPayload,
    admin: AdminActual = Depends(requiere_gestor_de_formularios),
    pool=Depends(obtener_pool),
):
    if admin.rol == "admin_organismo":
        organismo_id = admin.organismo_id
    elif request.organismo_id is None:
        raise HTTPException(status_code=400, detail="Elegí el organismo del formulario")
    else:
        organismo_id = request.organismo_id
    with pool.connection() as conn:
        if admin_tramites_repository.obtener_nombre_organismo(conn, organismo_id) is None:
            raise HTTPException(status_code=400, detail="El organismo no existe")
        datos = _datos_de_formulario(conn, request, organismo_id)
        creador = admin_repository.obtener_admin_por_id(conn, admin.id)
        try:
            formulario_id = formularios_repository.crear_formulario(
                conn, organismo_id, datos, [c.model_dump() for c in request.campos], creador["email"]
            )
        except ValueError as error:
            conn.rollback()
            raise HTTPException(status_code=400, detail=str(error)) from error
        conn.commit()
    return {"id": formulario_id}


@app.get("/admin/formularios/{formulario_id}")
def admin_obtener_formulario(
    formulario_id: uuid.UUID, admin: AdminActual = Depends(requiere_admin), pool=Depends(obtener_pool)
):
    with pool.connection() as conn:
        return _cargar_formulario_de_mi_organismo(conn, admin, formulario_id)


@app.put("/admin/formularios/{formulario_id}")
def admin_editar_formulario(
    formulario_id: uuid.UUID,
    request: FormularioPayload,
    admin: AdminActual = Depends(requiere_gestor_de_formularios),
    pool=Depends(obtener_pool),
):
    with pool.connection() as conn:
        formulario = _cargar_formulario_de_mi_organismo(conn, admin, formulario_id)
        datos = _datos_de_formulario(conn, request, formulario["organismo_id"])
        try:
            formularios_repository.actualizar_formulario(
                conn, str(formulario_id), datos, [c.model_dump() for c in request.campos]
            )
        except formularios_repository.ReglaDeEdicion as error:
            conn.rollback()
            raise HTTPException(status_code=409, detail=str(error)) from error
        except ValueError as error:
            conn.rollback()
            raise HTTPException(status_code=400, detail=str(error)) from error
        conn.commit()
    return {"ok": True}


@app.get("/admin/formularios/{formulario_id}/respuestas")
def admin_listar_respuestas_formulario(
    formulario_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin: AdminActual = Depends(requiere_admin),
    pool=Depends(obtener_pool),
):
    with pool.connection() as conn:
        formulario = _cargar_formulario_de_mi_organismo(conn, admin, formulario_id)
        respuestas, total = formularios_repository.listar_respuestas(conn, str(formulario_id), page, page_size)
    return {
        "respuestas": [{"id": r["id"], "creado_en": r["creado_en"], "valores": r["valores"]} for r in respuestas],
        "campos": formulario["campos"],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@app.get("/admin/formularios/{formulario_id}/respuestas.csv")
def admin_exportar_respuestas_formulario(
    formulario_id: uuid.UUID, admin: AdminActual = Depends(requiere_admin), pool=Depends(obtener_pool)
):
    with pool.connection() as conn:
        formulario = _cargar_formulario_de_mi_organismo(conn, admin, formulario_id)
        respuestas = formularios_repository.todas_las_respuestas(conn, str(formulario_id))
    contenido = "﻿" + formularios_csv.a_csv(formulario["campos"], respuestas)
    archivo = generar_clave(formulario["nombre"], set())
    return Response(
        content=contenido.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{archivo}-respuestas.csv"'},
    )


@app.get("/admin/formularios/{formulario_id}/respuestas/{respuesta_id}")
def admin_obtener_respuesta_formulario(
    formulario_id: uuid.UUID,
    respuesta_id: uuid.UUID,
    admin: AdminActual = Depends(requiere_admin),
    pool=Depends(obtener_pool),
):
    with pool.connection() as conn:
        formulario = _cargar_formulario_de_mi_organismo(conn, admin, formulario_id)
        respuesta = formularios_repository.obtener_respuesta(conn, str(formulario_id), str(respuesta_id))
        if respuesta is None:
            raise HTTPException(status_code=404, detail="Respuesta no encontrada")
        mensajes = admin_chats_repository.obtener_mensajes_completos(conn, respuesta["session_id"])
    return {
        **respuesta,
        "formulario": {"id": formulario["id"], "nombre": formulario["nombre"]},
        "campos": formulario["campos"],
        "mensajes": mensajes,
    }


@app.delete("/admin/formularios/{formulario_id}/respuestas/{respuesta_id}")
def admin_borrar_respuesta_formulario(
    formulario_id: uuid.UUID,
    respuesta_id: uuid.UUID,
    admin: AdminActual = Depends(requiere_gestor_de_formularios),
    pool=Depends(obtener_pool),
):
    with pool.connection() as conn:
        _cargar_formulario_de_mi_organismo(conn, admin, formulario_id)
        quien = admin_repository.obtener_admin_por_id(conn, admin.id)
        if not formularios_repository.borrar_respuesta(conn, str(formulario_id), str(respuesta_id), quien["email"]):
            raise HTTPException(status_code=404, detail="Respuesta no encontrada")
        conn.commit()
    return {"ok": True}
```

- [ ] **Step 4: Correr los tests y la suite**

Run: `timeout 120 .venv/bin/pytest -q -p no:cacheprovider tests/test_admin_formularios_api.py 2>&1 | tail -4`
Expected: PASS (todos).

Run: `timeout 280 .venv/bin/pytest -q -p no:cacheprovider 2>&1 | tail -1`
Expected: toda la suite PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/agent/api.py backend/tests/formularios_helpers.py backend/tests/test_admin_formularios_api.py
git commit -m "feat: endpoints del panel para formularios, respuestas y exportación CSV"
```

---

### Task 5: Herramientas del asistente, prompt y aviso por mail

**Files:**
- Create: `backend/agent/formularios_tools.py`
- Modify: `backend/agent/tools.py` (esquemas, despacho y `session_id`)
- Modify: `backend/agent/orchestrator.py` (pasar `session_id` y reglas del prompt)
- Modify: `docs/superpowers/specs/2026-10-23-formularios-organismo-design.md` (agregar el motivo `ya_registrada`)
- Test: `backend/tests/test_formularios_tools.py`
- Test: `backend/tests/test_orchestrator.py` (dos tests nuevos al final)
- Test: `backend/tests/test_system_prompt.py` (tests nuevos al final)

**Interfaces:**
- Consumes: `formularios_repository` (Task 3), `formularios_csv.valor_legible` (Task 2), `contacto_repository.resolver_destinatarios(conn, organismo_id)`, `mail.enviar_mail(destinatarios, asunto, cuerpo_texto)`.
- Produces: `formularios_tools.buscar_formularios(conn, argumentos) -> list[dict]` (cada uno con `id, nombre, organismo, descripcion_uso, aviso_finalidad, campos`); `formularios_tools.guardar_respuesta_formulario(conn, session_id, argumentos) -> dict` (`{"ok": True, "formulario": nombre}` o `{"ok": False, "motivo": ..., ...}`); `tools.ejecutar_tool(nombre, argumentos, conn, embed_fn, rerank_fn, session_id=None)`; herramientas `buscar_formularios` y `guardar_respuesta_formulario` en `TOOL_SCHEMAS`.

- [ ] **Step 1: Escribir los tests de las herramientas que fallan**

Crear `backend/tests/test_formularios_tools.py`:

```python
import json
from datetime import datetime, timedelta, timezone

import pytest

from agent import formularios_tools, sessions, tools
from agent.admin import formularios_repository as formularios
from tests.formularios_helpers import (
    crear_formulario,
    crear_organismo,
    crear_sesion,
    crear_tramite,
    valores_validos,
)


@pytest.fixture
def mails(monkeypatch):
    enviados = []
    monkeypatch.setattr(
        formularios_tools.mail,
        "enviar_mail",
        lambda destinatarios, asunto, cuerpo_texto: enviados.append((destinatarios, asunto, cuerpo_texto)),
    )
    return enviados


def _consultar(conn, sesion, formulario_id, llamada="call_1"):
    """Reproduce en el historial lo que deja buscar_formularios: la llamada y su resultado."""
    sessions.guardar_mensaje(
        conn,
        sesion,
        "assistant",
        None,
        tool_calls=[{"id": llamada, "type": "function", "function": {"name": "buscar_formularios", "arguments": "{}"}}],
    )
    sessions.guardar_mensaje(conn, sesion, "tool", json.dumps([{"id": formulario_id}]), tool_call_id=llamada)


def _guardar(conn, sesion, formulario_id, **cambios):
    argumentos = {"formulario_id": formulario_id, "valores": valores_validos(), "confirmado": True}
    argumentos.update(cambios)
    return formularios_tools.guardar_respuesta_formulario(conn, sesion, argumentos)


def _cantidad(conn, formulario_id):
    return formularios.listar_respuestas(conn, formulario_id, 1, 10)[1]


def test_buscar_formularios_devuelve_los_abiertos_con_campos_y_aviso(db_conn, clean_db):
    organismo_id = crear_organismo(db_conn)
    crear_formulario(db_conn, organismo_id, nombre="Abierto")
    crear_formulario(db_conn, organismo_id, nombre="Cerrado", estado="cerrado")

    resultado = formularios_tools.buscar_formularios(db_conn, {"consulta": "capacitación"})

    assert [f["nombre"] for f in resultado] == ["Abierto"]
    formulario = resultado[0]
    assert set(formulario) == {"id", "nombre", "organismo", "descripcion_uso", "aviso_finalidad", "campos"}
    assert formulario["organismo"] == "Subsecretaría de Trabajo"
    assert "inscribirte" in formulario["aviso_finalidad"]
    assert {c["tipo"] for c in formulario["campos"]} == {"texto", "dni", "telefono", "si_no"}
    json.dumps(resultado)  # tiene que ser serializable: el orquestador lo guarda como JSON


def test_buscar_formularios_prioriza_el_vinculado_al_tramite(db_conn, clean_db):
    organismo_id = crear_organismo(db_conn)
    tramite_id = crear_tramite(db_conn, organismo_id)
    crear_formulario(db_conn, organismo_id, nombre="Aaa común")
    crear_formulario(db_conn, organismo_id, nombre="Zzz vinculado", tramite_id=tramite_id)

    resultado = formularios_tools.buscar_formularios(db_conn, {"tramite_id": tramite_id})

    assert resultado[0]["nombre"] == "Zzz vinculado"


@pytest.mark.parametrize("confirmado", [False, None, "true", "sí", 1])
def test_no_guarda_si_la_persona_no_confirmo(db_conn, clean_db, mails, confirmado):
    organismo_id = crear_organismo(db_conn)
    formulario_id = crear_formulario(db_conn, organismo_id)
    sesion = crear_sesion(db_conn)
    _consultar(db_conn, sesion, formulario_id)

    resultado = _guardar(db_conn, sesion, formulario_id, confirmado=confirmado)

    assert resultado["ok"] is False and resultado["motivo"] == "no_confirmado"
    assert _cantidad(db_conn, formulario_id) == 0 and mails == []


def test_no_guarda_si_falta_el_campo_confirmado(db_conn, clean_db, mails):
    organismo_id = crear_organismo(db_conn)
    formulario_id = crear_formulario(db_conn, organismo_id)
    sesion = crear_sesion(db_conn)
    _consultar(db_conn, sesion, formulario_id)

    resultado = formularios_tools.guardar_respuesta_formulario(
        db_conn, sesion, {"formulario_id": formulario_id, "valores": valores_validos()}
    )

    assert resultado["motivo"] == "no_confirmado" and _cantidad(db_conn, formulario_id) == 0


@pytest.mark.parametrize("identificador", ["abc", "00000000-0000-0000-0000-000000000000", ""])
def test_no_guarda_un_formulario_que_no_se_consulto_en_la_sesion(db_conn, clean_db, mails, identificador):
    sesion = crear_sesion(db_conn)

    resultado = _guardar(db_conn, sesion, identificador)

    assert resultado["ok"] is False and resultado["motivo"] == "formulario_no_consultado"


def test_un_formulario_consultado_en_otra_sesion_no_sirve(db_conn, clean_db, mails):
    organismo_id = crear_organismo(db_conn)
    formulario_id = crear_formulario(db_conn, organismo_id)
    otra = crear_sesion(db_conn)
    _consultar(db_conn, otra, formulario_id)

    resultado = _guardar(db_conn, crear_sesion(db_conn), formulario_id)

    assert resultado["motivo"] == "formulario_no_consultado" and _cantidad(db_conn, formulario_id) == 0


def test_guardar_una_respuesta_confirmada_la_registra_y_avisa_al_organismo(db_conn, clean_db, mails):
    organismo_id = crear_organismo(db_conn)
    with db_conn.cursor() as cur:
        cur.execute("UPDATE organismos SET email_contacto = 'trabajo@gob.ar' WHERE id = %s", (organismo_id,))
    formulario_id = crear_formulario(db_conn, organismo_id)
    sesion = crear_sesion(db_conn)
    _consultar(db_conn, sesion, formulario_id)

    resultado = _guardar(db_conn, sesion, formulario_id)

    assert resultado == {"ok": True, "formulario": "Inscripción a la capacitación"}
    respuestas, total = formularios.listar_respuestas(db_conn, formulario_id, 1, 10)
    assert total == 1 and respuestas[0]["valores"]["dni"] == "30123456"
    destinatarios, asunto, cuerpo = mails[0]
    assert destinatarios == ["trabajo@gob.ar"]
    assert "Inscripción a la capacitación" in asunto
    assert "DNI: 30123456" in cuerpo
    assert "Nombre y apellido: Ana Pérez" in cuerpo
    assert "¿Participaría de la capacitación?: Sí" in cuerpo


def test_la_respuesta_queda_confirmada_en_la_base_sin_esperar_al_final_del_turno(db_conn, clean_db, mails):
    organismo_id = crear_organismo(db_conn)
    formulario_id = crear_formulario(db_conn, organismo_id)
    sesion = crear_sesion(db_conn)
    _consultar(db_conn, sesion, formulario_id)
    db_conn.commit()

    _guardar(db_conn, sesion, formulario_id)
    db_conn.rollback()  # si el turno falla después, lo guardado no se pierde

    assert _cantidad(db_conn, formulario_id) == 1


def test_datos_invalidos_devuelve_el_error_de_cada_campo_y_no_guarda(db_conn, clean_db, mails):
    organismo_id = crear_organismo(db_conn)
    formulario_id = crear_formulario(db_conn, organismo_id)
    sesion = crear_sesion(db_conn)
    _consultar(db_conn, sesion, formulario_id)

    resultado = _guardar(db_conn, sesion, formulario_id, valores=valores_validos(dni="123"))

    assert resultado["ok"] is False and resultado["motivo"] == "datos_invalidos"
    assert set(resultado["errores"]) == {"dni"} and "DNI" in resultado["errores"]["dni"]
    assert _cantidad(db_conn, formulario_id) == 0 and mails == []


@pytest.mark.parametrize("valores", [None, "texto", ["lista"], 5])
def test_valores_que_no_son_un_objeto_se_rechazan(db_conn, clean_db, mails, valores):
    organismo_id = crear_organismo(db_conn)
    formulario_id = crear_formulario(db_conn, organismo_id)
    sesion = crear_sesion(db_conn)
    _consultar(db_conn, sesion, formulario_id)

    resultado = _guardar(db_conn, sesion, formulario_id, valores=valores)

    assert resultado["ok"] is False and resultado["motivo"] == "datos_invalidos"


def test_un_dni_repetido_devuelve_duplicado(db_conn, clean_db, mails):
    organismo_id = crear_organismo(db_conn)
    formulario_id = crear_formulario(db_conn, organismo_id)
    primera, segunda = crear_sesion(db_conn), crear_sesion(db_conn)
    _consultar(db_conn, primera, formulario_id)
    _consultar(db_conn, segunda, formulario_id)
    _guardar(db_conn, primera, formulario_id)

    resultado = _guardar(db_conn, segunda, formulario_id, valores=valores_validos(dni="30.123.456"))

    assert resultado["ok"] is False and resultado["motivo"] == "duplicado"
    assert _cantidad(db_conn, formulario_id) == 1 and len(mails) == 1


def test_un_segundo_envio_de_la_misma_sesion_devuelve_ya_registrada(db_conn, clean_db, mails):
    organismo_id = crear_organismo(db_conn)
    formulario_id = crear_formulario(db_conn, organismo_id)
    sesion = crear_sesion(db_conn)
    _consultar(db_conn, sesion, formulario_id)
    _guardar(db_conn, sesion, formulario_id)

    resultado = _guardar(db_conn, sesion, formulario_id, valores=valores_validos(dni="40123456"))

    assert resultado["motivo"] == "ya_registrada" and _cantidad(db_conn, formulario_id) == 1


@pytest.mark.parametrize(
    "cambios, motivo",
    [
        ({"estado": "cerrado"}, "cerrado"),
        ({"fecha_cierre": datetime.now(timezone.utc) - timedelta(hours=1)}, "cerrado"),
    ],
)
def test_un_formulario_que_ya_no_esta_abierto_se_rechaza(db_conn, clean_db, mails, cambios, motivo):
    organismo_id = crear_organismo(db_conn)
    formulario_id = crear_formulario(db_conn, organismo_id, **cambios)
    sesion = crear_sesion(db_conn)
    _consultar(db_conn, sesion, formulario_id)

    resultado = _guardar(db_conn, sesion, formulario_id)

    assert resultado == {"ok": False, "motivo": motivo}


def test_el_cupo_completo_devuelve_cupo(db_conn, clean_db, mails):
    organismo_id = crear_organismo(db_conn)
    formulario_id = crear_formulario(db_conn, organismo_id, cupo=1)
    primera, segunda = crear_sesion(db_conn), crear_sesion(db_conn)
    _consultar(db_conn, primera, formulario_id)
    _consultar(db_conn, segunda, formulario_id)
    _guardar(db_conn, primera, formulario_id)

    resultado = _guardar(db_conn, segunda, formulario_id, valores=valores_validos(dni="40123456"))

    assert resultado == {"ok": False, "motivo": "cupo"}


def test_una_sesion_no_puede_completar_mas_de_tres_formularios(db_conn, clean_db, mails):
    organismo_id = crear_organismo(db_conn)
    sesion = crear_sesion(db_conn)
    ids = [crear_formulario(db_conn, organismo_id, nombre=f"Formulario {i}") for i in range(4)]
    for numero, formulario_id in enumerate(ids, start=1):
        _consultar(db_conn, sesion, formulario_id, llamada=f"call_{numero}")

    resultados = [_guardar(db_conn, sesion, formulario_id) for formulario_id in ids]

    assert [r["ok"] for r in resultados] == [True, True, True, False]
    assert resultados[3]["motivo"] == "limite_sesion"
    assert _cantidad(db_conn, ids[3]) == 0


def test_un_fallo_del_mail_no_deshace_la_respuesta(db_conn, clean_db, monkeypatch):
    def fallar(*args, **kwargs):
        raise RuntimeError("smtp caído")

    monkeypatch.setattr(formularios_tools.mail, "enviar_mail", fallar)
    organismo_id = crear_organismo(db_conn)
    formulario_id = crear_formulario(db_conn, organismo_id)
    sesion = crear_sesion(db_conn)
    _consultar(db_conn, sesion, formulario_id)

    resultado = _guardar(db_conn, sesion, formulario_id)

    assert resultado["ok"] is True and _cantidad(db_conn, formulario_id) == 1


def test_las_herramientas_estan_registradas_y_se_despachan(db_conn, clean_db, mails):
    nombres = [t["function"]["name"] for t in tools.TOOL_SCHEMAS]
    assert "buscar_formularios" in nombres and "guardar_respuesta_formulario" in nombres
    guardar = next(t for t in tools.TOOL_SCHEMAS if t["function"]["name"] == "guardar_respuesta_formulario")
    assert set(guardar["function"]["parameters"]["required"]) == {"formulario_id", "valores", "confirmado"}

    organismo_id = crear_organismo(db_conn)
    formulario_id = crear_formulario(db_conn, organismo_id)
    sesion = crear_sesion(db_conn)
    _consultar(db_conn, sesion, formulario_id)

    encontrados = tools.ejecutar_tool("buscar_formularios", {}, db_conn, None, None, session_id=sesion)
    guardado = tools.ejecutar_tool(
        "guardar_respuesta_formulario",
        {"formulario_id": formulario_id, "valores": valores_validos(), "confirmado": True},
        db_conn,
        None,
        None,
        session_id=sesion,
    )

    assert encontrados[0]["id"] == formulario_id and guardado["ok"] is True
```

- [ ] **Step 2: Escribir los tests de orquestador y de prompt que fallan**

Agregar al final de `backend/tests/test_orchestrator.py` (usa `_FakeChatClient`, `_fake_embed_fn` y `_fake_rerank_fn` que ya están en ese archivo):

```python


def _llamada(nombre, argumentos, id_):
    return {
        "role": "assistant",
        "content": None,
        "tool_calls": [{"id": id_, "type": "function", "function": {"name": nombre, "arguments": json.dumps(argumentos)}}],
    }


def test_el_asistente_busca_el_formulario_y_guarda_la_respuesta_confirmada(db_conn, clean_db, monkeypatch):
    from agent import formularios_tools
    from agent.admin import formularios_repository
    from tests.formularios_helpers import crear_formulario, crear_organismo, valores_validos

    monkeypatch.setattr(formularios_tools.mail, "enviar_mail", lambda *a, **k: None)
    organismo_id = crear_organismo(db_conn)
    formulario_id = crear_formulario(db_conn, organismo_id)
    session_id = str(uuid.uuid4())
    chat_client = _FakeChatClient(
        [
            _llamada("buscar_formularios", {"consulta": "capacitación"}, "call_1"),
            _llamada(
                "guardar_respuesta_formulario",
                {"formulario_id": formulario_id, "valores": valores_validos(), "confirmado": True},
                "call_2",
            ),
            {"role": "assistant", "content": "Listo, quedaste inscripto.", "tool_calls": None},
        ]
    )

    eventos = list(
        procesar_turno(db_conn, chat_client, _fake_embed_fn, _fake_rerank_fn, session_id, "quiero anotarme a la capacitación")
    )

    assert eventos[-1]["tipo"] == "fin"
    respuestas, total = formularios_repository.listar_respuestas(db_conn, formulario_id, 1, 10)
    assert total == 1 and respuestas[0]["valores"]["dni"] == "30123456"
    with db_conn.cursor() as cur:
        cur.execute("SELECT contenido FROM mensajes WHERE session_id = %s AND tool_call_id = 'call_2'", (session_id,))
        assert json.loads(cur.fetchone()[0]) == {"ok": True, "formulario": "Inscripción a la capacitación"}


def test_el_asistente_no_puede_guardar_un_formulario_que_no_consulto(db_conn, clean_db, monkeypatch):
    from agent import formularios_tools
    from agent.admin import formularios_repository
    from tests.formularios_helpers import crear_formulario, crear_organismo, valores_validos

    monkeypatch.setattr(formularios_tools.mail, "enviar_mail", lambda *a, **k: None)
    organismo_id = crear_organismo(db_conn)
    formulario_id = crear_formulario(db_conn, organismo_id)
    session_id = str(uuid.uuid4())
    chat_client = _FakeChatClient(
        [
            _llamada(
                "guardar_respuesta_formulario",
                {"formulario_id": formulario_id, "valores": valores_validos(), "confirmado": True},
                "call_1",
            ),
            {"role": "assistant", "content": "No pude guardarlo.", "tool_calls": None},
        ]
    )

    list(procesar_turno(db_conn, chat_client, _fake_embed_fn, _fake_rerank_fn, session_id, "anotame"))

    assert formularios_repository.listar_respuestas(db_conn, formulario_id, 1, 10)[1] == 0
    with db_conn.cursor() as cur:
        cur.execute("SELECT contenido FROM mensajes WHERE session_id = %s AND tool_call_id = 'call_1'", (session_id,))
        assert json.loads(cur.fetchone()[0])["motivo"] == "formulario_no_consultado"
```

(Si `json` no estuviera importado en la cabecera de `test_orchestrator.py`, agregar `import json` arriba.)

Agregar al final de `backend/tests/test_system_prompt.py`:

```python


def test_ordena_buscar_formularios_cuando_la_persona_quiere_anotarse():
    prompt = _normalizado()

    assert "llamá a buscar_formularios" in prompt
    assert "anotarse, inscribirse o completar un formulario" in prompt


def test_exige_avisar_la_finalidad_antes_de_pedir_datos():
    prompt = _normalizado()

    assert "qué organismo los recibe y para qué" in prompt
    assert "dejá que decida si sigue" in prompt


def test_exige_resumir_y_confirmar_antes_de_guardar_y_permite_cancelar():
    prompt = _normalizado()

    assert "resumilos y preguntale si son correctos" in prompt
    assert "guardar_respuesta_formulario con confirmado en verdadero" in prompt
    assert "no guardes nada" in prompt


def test_prohibe_decir_que_se_guardo_sin_que_la_herramienta_lo_confirme():
    prompt = _normalizado()

    assert "Nunca digas que quedó registrado" in prompt
    assert "nunca inventes datos" in prompt
```

- [ ] **Step 3: Correr los tests para ver que fallan**

Run: `timeout 120 .venv/bin/pytest -q -p no:cacheprovider tests/test_formularios_tools.py tests/test_system_prompt.py tests/test_orchestrator.py 2>&1 | tail -5`
Expected: FAIL (`ImportError: cannot import name 'formularios_tools'`, y los tests de prompt sin las frases).

- [ ] **Step 4: Implementar `formularios_tools.py`**

Crear `backend/agent/formularios_tools.py`:

```python
import logging

from agent import mail
from agent.admin import contacto_repository
from agent.admin import formularios_repository as formularios
from agent.formularios_csv import valor_legible

logger = logging.getLogger(__name__)

MAX_FORMULARIOS_POR_SESION = 3


def buscar_formularios(conn, argumentos: dict) -> list[dict]:
    abiertos = formularios.formularios_abiertos(
        conn, tramite_id=argumentos.get("tramite_id"), consulta=argumentos.get("consulta"), limite=5
    )
    return [
        {
            "id": f["id"],
            "nombre": f["nombre"],
            "organismo": f["organismo"],
            "descripcion_uso": f["descripcion_uso"],
            "aviso_finalidad": f["aviso_finalidad"],
            "campos": [
                {
                    "clave": c["clave"],
                    "etiqueta": c["etiqueta"],
                    "tipo": c["tipo"],
                    "obligatorio": c["obligatorio"],
                    "opciones": c["opciones"],
                }
                for c in f["campos"]
            ],
        }
        for f in abiertos
    ]


def guardar_respuesta_formulario(conn, session_id: str, argumentos: dict) -> dict:
    # El servidor no confía en el modelo: cada defensa se comprueba acá, antes de tocar los datos.
    if argumentos.get("confirmado") is not True:
        return {
            "ok": False,
            "motivo": "no_confirmado",
            "detalle": "Resumí los datos y pedile a la persona que confirme antes de guardar.",
        }
    formulario_id = str(argumentos.get("formulario_id", ""))
    if formulario_id not in formularios.formularios_consultados_en_sesion(conn, session_id):
        return {
            "ok": False,
            "motivo": "formulario_no_consultado",
            "detalle": "Primero consultá el formulario con buscar_formularios.",
        }
    valores = argumentos.get("valores")
    if not isinstance(valores, dict):
        return {"ok": False, "motivo": "datos_invalidos", "errores": {}, "detalle": "Faltan los valores del formulario."}
    if formularios.formularios_respondidos_en_sesion(conn, session_id) >= MAX_FORMULARIOS_POR_SESION:
        return {"ok": False, "motivo": "limite_sesion"}

    try:
        resultado = formularios.guardar_respuesta(conn, formulario_id, session_id, valores)
    except formularios.FormularioNoDisponible as error:
        return {"ok": False, "motivo": error.motivo}
    except formularios.DatosInvalidos as error:
        return {"ok": False, "motivo": "datos_invalidos", "errores": error.errores}
    except formularios.RespuestaDuplicada:
        return {"ok": False, "motivo": "duplicado"}
    except formularios.YaRespondio:
        return {"ok": False, "motivo": "ya_registrada"}

    # Se confirma ahora y no al final del turno: si algo falla después, la persona no pierde lo que ya se le confirmó.
    conn.commit()
    _avisar_por_mail(conn, resultado)
    return {"ok": True, "formulario": resultado["formulario"]}


def _avisar_por_mail(conn, resultado: dict) -> None:
    try:
        destinatarios = contacto_repository.resolver_destinatarios(conn, resultado["organismo_id"])
        lineas = [f"Nueva respuesta al formulario «{resultado['formulario']}»", ""]
        for campo in resultado["campos"]:
            lineas.append(f"{campo['etiqueta']}: {valor_legible(campo, resultado['valores'].get(campo['clave']))}")
        mail.enviar_mail(
            destinatarios,
            asunto=f"Nueva respuesta: {resultado['formulario']}",
            cuerpo_texto="\n".join(lineas),
        )
    except Exception:
        logger.exception("Falló el aviso por mail de la respuesta %s", resultado["id"])
```

- [ ] **Step 5: Registrar las herramientas en `tools.py` y pasar `session_id` desde el orquestador**

En `backend/agent/tools.py`: agregar arriba `from agent import formularios_tools`; agregar al final de la lista `TOOL_SCHEMAS` (antes del `]` de cierre), después del esquema de `ofrecer_contacto_humano`:

```python
    {
        "type": "function",
        "function": {
            "name": "buscar_formularios",
            "description": (
                "Busca los formularios de inscripción o registro que algún organismo tiene abiertos (por ejemplo, "
                "inscripción a una capacitación). Usala cuando la persona quiera anotarse, inscribirse o completar "
                "un formulario, o cuando lo que cuenta coincida con uno. Devuelve, por cada formulario, para qué se "
                "usan los datos (aviso_finalidad) y los campos que hay que pedir."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "consulta": {
                        "type": "string",
                        "description": "Lo que la persona quiere hacer, con sus palabras.",
                    },
                    "tramite_id": {
                        "type": "string",
                        "description": "El ID del trámite de la conversación, si ya está identificado (ej. 'TR-0001').",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "guardar_respuesta_formulario",
            "description": (
                "Guarda los datos que la persona dio para un formulario. Llamala solo después de haber consultado el "
                "formulario con buscar_formularios, de haber resumido los datos y de que la persona confirmó que son "
                "correctos. Si devuelve errores por campo, repreguntá solo esos datos."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "formulario_id": {"type": "string", "description": "El id del formulario devuelto por buscar_formularios."},
                    "valores": {
                        "type": "object",
                        "description": "Un valor por cada campo, usando la clave del campo (ej. {\"dni\": \"30123456\"}).",
                    },
                    "confirmado": {
                        "type": "boolean",
                        "description": "Verdadero solo si la persona confirmó explícitamente que los datos resumidos son correctos.",
                    },
                },
                "required": ["formulario_id", "valores", "confirmado"],
            },
        },
    },
```

Cambiar la firma y el final de `ejecutar_tool`:

```python
def ejecutar_tool(nombre: str, argumentos: dict, conn, embed_fn, rerank_fn, session_id: str | None = None):
```

y agregar antes de `raise ValueError(f"Tool desconocida: {nombre}")`:

```python
    if nombre == "buscar_formularios":
        return formularios_tools.buscar_formularios(conn, argumentos)
    if nombre == "guardar_respuesta_formulario":
        return formularios_tools.guardar_respuesta_formulario(conn, session_id, argumentos)
```

En `backend/agent/orchestrator.py`, cambiar la llamada (dentro del bucle de `tool_calls`) a:

```python
            resultado = ejecutar_tool(nombre, argumentos, conn, embed_fn, rerank_fn, session_id=session_id)
```

- [ ] **Step 6: Agregar las reglas al prompt**

En `backend/agent/orchestrator.py`, el `SYSTEM_PROMPT` termina hoy con:

```python
    "ese trámite y usá ofrecer_contacto_humano."
)
```

Reemplazar esas dos líneas por:

```python
    "ese trámite y usá ofrecer_contacto_humano. "
    "Si la persona quiere anotarse, inscribirse o completar un formulario de un "
    "organismo, o lo que cuenta coincide con alguno, llamá a buscar_formularios. "
    "Antes de pedirle datos, decile qué organismo los recibe y para qué (el aviso "
    "de finalidad del formulario) y dejá que decida si sigue. Pedile los datos del "
    "formulario, resumilos y preguntale si son correctos; solo cuando confirme "
    "llamá a guardar_respuesta_formulario con confirmado en verdadero. Si la "
    "persona cancela, no guardes nada. Nunca digas que quedó registrado si "
    "guardar_respuesta_formulario no devolvió ok, y nunca inventes datos que la "
    "persona no te dio."
)
```

- [ ] **Step 7: Corregir el spec (motivo `ya_registrada`) y correr los tests**

En `docs/superpowers/specs/2026-10-23-formularios-organismo-design.md`, en la lista de motivos de `guardar_respuesta_formulario`, reemplazar `` `duplicado`, `limite_sesion` o `datos_invalidos` `` por `` `duplicado`, `limite_sesion`, `ya_registrada` (la sesión ya envió ese formulario) o `datos_invalidos` ``.

Run: `timeout 120 .venv/bin/pytest -q -p no:cacheprovider tests/test_formularios_tools.py tests/test_system_prompt.py tests/test_orchestrator.py tests/test_tools.py 2>&1 | tail -4`
Expected: PASS (todos).

Run: `timeout 280 .venv/bin/pytest -q -p no:cacheprovider 2>&1 | tail -1`
Expected: toda la suite PASS.

- [ ] **Step 8: Commit**

```bash
git add backend/agent/formularios_tools.py backend/agent/tools.py backend/agent/orchestrator.py backend/tests/test_formularios_tools.py backend/tests/test_orchestrator.py backend/tests/test_system_prompt.py docs/superpowers/specs/2026-10-23-formularios-organismo-design.md
git commit -m "feat: el asistente busca formularios y guarda respuestas confirmadas"
```

---

### Task 6: Cliente de la API y lógica pura del frontend

**Files:**
- Create: `frontend/lib/admin-formularios-api.ts`
- Create: `frontend/lib/formularios-ui.ts`
- Test: `frontend/lib/formularios-ui.test.ts`
- Modify: `frontend/lib/admin-api.ts` (`puede_crear_formularios` en `AdminSesionInfo`)
- Modify: `frontend/lib/admin-usuarios-api.ts` (el permiso en `AdminUsuario` y `UsuarioFormValores`)

**Interfaces:**
- Consumes: los endpoints de la Task 4 y `MensajeAdmin` de `lib/admin-api.ts`.
- Produces (`admin-formularios-api.ts`): tipos `TipoCampo`, `EstadoFormulario`, `EstadoEfectivo`, `CampoFormulario` (`clave?, etiqueta, tipo, obligatorio, opciones`), `FormularioResumen`, `FormularioDetalle`, `FormularioEntrada`, `PaginaFormularios`, `RespuestaFila`, `PaginaRespuestas`, `RespuestaDetalle`; funciones `listarFormularios(page, pageSize)`, `obtenerFormulario(id)` (`null` si 404), `crearFormulario(entrada) -> {id}`, `editarFormulario(id, entrada)`, `listarRespuestas(id, page, pageSize)`, `obtenerRespuesta(id, rid)` (`null` si 404), `borrarRespuesta(id, rid)`, `descargarCsv(id, nombreArchivo)`.
- Produces (`formularios-ui.ts`): `ETIQUETAS_TIPO`, `TIPOS_CAMPO`, `textoEstado`, `textoCupo`, `campoNuevo`, `puedeQuitarCampo`, `puedeCambiarTipo`, `puedeSerObligatorio`, `opcionesDeTexto`, `textoDeOpciones`, `validarEntrada`, `valorLegible`, `nombreArchivoCsv`, `isoAInputFecha`, `inputFechaAIso`.

- [ ] **Step 1: Escribir los tests que fallan**

Crear `frontend/lib/formularios-ui.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import type { CampoFormulario, FormularioEntrada } from "./admin-formularios-api";
import {
  campoNuevo,
  inputFechaAIso,
  isoAInputFecha,
  nombreArchivoCsv,
  opcionesDeTexto,
  puedeCambiarTipo,
  puedeQuitarCampo,
  puedeSerObligatorio,
  textoCupo,
  textoDeOpciones,
  textoEstado,
  validarEntrada,
  valorLegible,
} from "./formularios-ui";

const campo = (cambios: Partial<CampoFormulario> = {}): CampoFormulario => ({
  etiqueta: "Nombre",
  tipo: "texto",
  obligatorio: true,
  opciones: null,
  ...cambios,
});

const entrada = (cambios: Partial<FormularioEntrada> = {}): FormularioEntrada => ({
  organismo_id: 1,
  nombre: "Inscripción a la capacitación",
  descripcion_uso: "",
  aviso_finalidad: "",
  tramite_id: null,
  estado: "activo",
  fecha_cierre: null,
  cupo: null,
  campos: [campo()],
  ...cambios,
});

describe("textos de estado y cupo", () => {
  it("traduce el estado efectivo", () => {
    expect(textoEstado("abierto")).toBe("Abierto");
    expect(textoEstado("borrador")).toBe("Borrador");
    expect(textoEstado("cerrado")).toBe("Cerrado");
    expect(textoEstado("vencido")).toBe("Cerrado por fecha");
    expect(textoEstado("cupo_completo")).toBe("Cupo completo");
  });

  it("muestra las respuestas sobre el cupo cuando hay cupo", () => {
    expect(textoCupo(12, 40)).toBe("12 de 40");
    expect(textoCupo(12, null)).toBe("12");
  });
});

describe("reglas de edición según haya respuestas", () => {
  const existente = campo({ clave: "dni" });
  const nuevo = campo();

  it("sin respuestas todo se puede cambiar", () => {
    expect(puedeQuitarCampo(existente, false)).toBe(true);
    expect(puedeCambiarTipo(existente, false)).toBe(true);
    expect(puedeSerObligatorio(nuevo, false)).toBe(true);
  });

  it("con respuestas los campos existentes no se quitan ni cambian de tipo", () => {
    expect(puedeQuitarCampo(existente, true)).toBe(false);
    expect(puedeCambiarTipo(existente, true)).toBe(false);
  });

  it("con respuestas un campo nuevo se puede quitar pero tiene que ser opcional", () => {
    expect(puedeQuitarCampo(nuevo, true)).toBe(true);
    expect(puedeSerObligatorio(nuevo, true)).toBe(false);
    expect(puedeSerObligatorio(existente, true)).toBe(true);
  });

  it("un campo nuevo arranca como texto obligatorio y sin clave", () => {
    expect(campoNuevo()).toEqual({ etiqueta: "", tipo: "texto", obligatorio: true, opciones: null });
  });
});

describe("opciones de una lista", () => {
  it("separa por línea, recorta y descarta las vacías", () => {
    expect(opcionesDeTexto(" Mañana \n\nTarde\n  ")).toEqual(["Mañana", "Tarde"]);
  });

  it("vuelve a armar el texto", () => {
    expect(textoDeOpciones(["Mañana", "Tarde"])).toBe("Mañana\nTarde");
    expect(textoDeOpciones(null)).toBe("");
  });
});

describe("validarEntrada", () => {
  it("acepta un formulario correcto", () => {
    expect(validarEntrada(entrada())).toBeNull();
  });

  it("pide un nombre", () => {
    expect(validarEntrada(entrada({ nombre: "   " }))).toMatch(/nombre/i);
  });

  it("pide al menos un campo y una etiqueta en cada uno", () => {
    expect(validarEntrada(entrada({ campos: [] }))).toMatch(/campo/i);
    expect(validarEntrada(entrada({ campos: [campo({ etiqueta: " " })] }))).toMatch(/etiqueta|pregunta/i);
  });

  it("admite como máximo 30 campos y un solo DNI", () => {
    expect(validarEntrada(entrada({ campos: Array.from({ length: 31 }, () => campo()) }))).toMatch(/30/);
    expect(validarEntrada(entrada({ campos: [campo({ tipo: "dni" }), campo({ tipo: "dni", etiqueta: "Otro" })] }))).toMatch(/DNI/);
  });

  it("una lista necesita entre 2 y 20 opciones distintas", () => {
    const lista = (opciones: string[]) => entrada({ campos: [campo({ tipo: "opcion", opciones })] });
    expect(validarEntrada(lista(["Una"]))).toMatch(/opciones/i);
    expect(validarEntrada(lista(["A", "a"]))).toMatch(/opciones/i);
    expect(validarEntrada(lista(Array.from({ length: 21 }, (_, i) => `o${i}`)))).toMatch(/opciones/i);
    expect(validarEntrada(lista(["Mañana", "Tarde"]))).toBeNull();
  });

  it("el cupo tiene que ser un entero positivo", () => {
    expect(validarEntrada(entrada({ cupo: 0 }))).toMatch(/cupo/i);
    expect(validarEntrada(entrada({ cupo: 2.5 }))).toMatch(/cupo/i);
    expect(validarEntrada(entrada({ cupo: 40 }))).toBeNull();
  });

  it("con respuestas, un campo nuevo obligatorio se rechaza", () => {
    const f = entrada({ campos: [campo({ clave: "nombre" }), campo({ etiqueta: "Nuevo", obligatorio: true })] });
    expect(validarEntrada(f, true)).toMatch(/opcional/i);
    expect(validarEntrada(f, false)).toBeNull();
  });
});

describe("valorLegible", () => {
  it("formatea sí/no, fecha y vacíos", () => {
    expect(valorLegible(campo({ tipo: "si_no" }), true)).toBe("Sí");
    expect(valorLegible(campo({ tipo: "si_no" }), false)).toBe("No");
    expect(valorLegible(campo({ tipo: "fecha" }), "1990-12-25")).toBe("25/12/1990");
    expect(valorLegible(campo(), undefined)).toBe("");
    expect(valorLegible(campo({ tipo: "numero" }), 12)).toBe("12");
  });
});

describe("nombreArchivoCsv", () => {
  it("arma un nombre sin acentos ni símbolos", () => {
    expect(nombreArchivoCsv("Inscripción a la capacitación")).toBe("inscripcion-a-la-capacitacion-respuestas.csv");
    expect(nombreArchivoCsv("???")).toBe("formulario-respuestas.csv");
  });
});

describe("fechas del campo datetime-local", () => {
  it("convierte ida y vuelta sin cambiar la hora local", () => {
    const iso = inputFechaAIso("2026-10-30T18:00");
    expect(iso).not.toBeNull();
    expect(isoAInputFecha(iso)).toBe("2026-10-30T18:00");
  });

  it("maneja vacío", () => {
    expect(inputFechaAIso("")).toBeNull();
    expect(isoAInputFecha(null)).toBe("");
  });
});
```

- [ ] **Step 2: Correr los tests para ver que fallan**

Run (desde `frontend/`): `timeout 100 npx vitest run lib/formularios-ui.test.ts 2>&1 | grep -E "Failed|Error|Cannot find" | head -3`
Expected: FAIL (`Failed to load url ./formularios-ui`).

- [ ] **Step 3: Implementar el cliente de la API**

Crear `frontend/lib/admin-formularios-api.ts`:

```ts
import type { MensajeAdmin } from "./admin-api";

export type TipoCampo =
  | "texto"
  | "texto_largo"
  | "dni"
  | "telefono"
  | "email"
  | "numero"
  | "fecha"
  | "si_no"
  | "opcion";
export type EstadoFormulario = "borrador" | "activo" | "cerrado";
export type EstadoEfectivo = "borrador" | "cerrado" | "vencido" | "cupo_completo" | "abierto";

export type CampoFormulario = {
  clave?: string;
  etiqueta: string;
  tipo: TipoCampo;
  obligatorio: boolean;
  opciones: string[] | null;
};

export type FormularioResumen = {
  id: string;
  organismo_id: number;
  organismo: string;
  nombre: string;
  descripcion_uso: string;
  aviso_finalidad: string;
  tramite_id: string | null;
  estado: EstadoFormulario;
  estado_efectivo: EstadoEfectivo;
  fecha_cierre: string | null;
  cupo: number | null;
  respuestas: number;
  hay_respuestas: boolean;
  creado_por_email: string;
  creado_en: string;
  actualizado_en: string;
};

export type FormularioDetalle = FormularioResumen & { campos: CampoFormulario[] };

export type FormularioEntrada = {
  organismo_id: number | null;
  nombre: string;
  descripcion_uso: string;
  aviso_finalidad: string;
  tramite_id: string | null;
  estado: EstadoFormulario;
  fecha_cierre: string | null;
  cupo: number | null;
  campos: CampoFormulario[];
};

export type PaginaFormularios = {
  formularios: FormularioResumen[];
  total: number;
  page: number;
  page_size: number;
};

export type RespuestaFila = { id: string; creado_en: string; valores: Record<string, unknown> };

export type PaginaRespuestas = {
  respuestas: RespuestaFila[];
  campos: CampoFormulario[];
  total: number;
  page: number;
  page_size: number;
};

export type RespuestaDetalle = RespuestaFila & {
  session_id: string;
  formulario: { id: string; nombre: string };
  campos: CampoFormulario[];
  mensajes: MensajeAdmin[];
};

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function parsearOLanzar<T>(respuesta: Response, mensajePorDefecto: string): Promise<T> {
  if (!respuesta.ok) {
    const cuerpo = await respuesta.json().catch(() => null);
    const detalle = typeof cuerpo?.detail === "string" ? cuerpo.detail : null;
    throw new Error(detalle ?? mensajePorDefecto);
  }
  return respuesta.json();
}

export async function listarFormularios(page: number, pageSize: number): Promise<PaginaFormularios> {
  const respuesta = await fetch(`${BASE_URL}/admin/formularios?page=${page}&page_size=${pageSize}`, {
    credentials: "include",
  });
  return parsearOLanzar(respuesta, "No se pudo cargar la lista de formularios");
}

export async function obtenerFormulario(id: string): Promise<FormularioDetalle | null> {
  const respuesta = await fetch(`${BASE_URL}/admin/formularios/${id}`, { credentials: "include" });
  if (respuesta.status === 404) return null;
  return parsearOLanzar(respuesta, "No se pudo cargar el formulario");
}

export async function crearFormulario(entrada: FormularioEntrada): Promise<{ id: string }> {
  const respuesta = await fetch(`${BASE_URL}/admin/formularios`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(entrada),
  });
  return parsearOLanzar(respuesta, "No se pudo crear el formulario");
}

export async function editarFormulario(id: string, entrada: FormularioEntrada): Promise<void> {
  const respuesta = await fetch(`${BASE_URL}/admin/formularios/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(entrada),
  });
  await parsearOLanzar(respuesta, "No se pudo guardar el formulario");
}

export async function listarRespuestas(id: string, page: number, pageSize: number): Promise<PaginaRespuestas> {
  const respuesta = await fetch(
    `${BASE_URL}/admin/formularios/${id}/respuestas?page=${page}&page_size=${pageSize}`,
    { credentials: "include" }
  );
  return parsearOLanzar(respuesta, "No se pudieron cargar las respuestas");
}

export async function obtenerRespuesta(id: string, respuestaId: string): Promise<RespuestaDetalle | null> {
  const respuesta = await fetch(`${BASE_URL}/admin/formularios/${id}/respuestas/${respuestaId}`, {
    credentials: "include",
  });
  if (respuesta.status === 404) return null;
  return parsearOLanzar(respuesta, "No se pudo cargar la respuesta");
}

export async function borrarRespuesta(id: string, respuestaId: string): Promise<void> {
  const respuesta = await fetch(`${BASE_URL}/admin/formularios/${id}/respuestas/${respuestaId}`, {
    method: "DELETE",
    credentials: "include",
  });
  await parsearOLanzar(respuesta, "No se pudo borrar la respuesta");
}

export async function descargarCsv(id: string, nombreArchivo: string): Promise<void> {
  const respuesta = await fetch(`${BASE_URL}/admin/formularios/${id}/respuestas.csv`, {
    credentials: "include",
  });
  if (!respuesta.ok) throw new Error("No se pudo exportar el CSV");
  const url = URL.createObjectURL(await respuesta.blob());
  const enlace = document.createElement("a");
  enlace.href = url;
  enlace.download = nombreArchivo;
  document.body.appendChild(enlace);
  enlace.click();
  enlace.remove();
  URL.revokeObjectURL(url);
}
```

- [ ] **Step 4: Implementar la lógica pura**

Crear `frontend/lib/formularios-ui.ts`:

```ts
import type {
  CampoFormulario,
  EstadoEfectivo,
  FormularioEntrada,
  TipoCampo,
} from "./admin-formularios-api";

export const ETIQUETAS_TIPO: Record<TipoCampo, string> = {
  texto: "Texto corto",
  texto_largo: "Texto largo",
  dni: "DNI",
  telefono: "Teléfono",
  email: "Email",
  numero: "Número",
  fecha: "Fecha",
  si_no: "Sí / No",
  opcion: "Lista de opciones",
};

export const TIPOS_CAMPO = Object.keys(ETIQUETAS_TIPO) as TipoCampo[];

const MAX_CAMPOS = 30;
const MAX_OPCIONES = 20;

export function textoEstado(estado: EstadoEfectivo): string {
  switch (estado) {
    case "abierto":
      return "Abierto";
    case "borrador":
      return "Borrador";
    case "cerrado":
      return "Cerrado";
    case "vencido":
      return "Cerrado por fecha";
    case "cupo_completo":
      return "Cupo completo";
  }
}

export function textoCupo(respuestas: number, cupo: number | null): string {
  return cupo === null ? `${respuestas}` : `${respuestas} de ${cupo}`;
}

export function campoNuevo(): CampoFormulario {
  return { etiqueta: "", tipo: "texto", obligatorio: true, opciones: null };
}

// Un campo "existente" es el que ya tiene clave (viene del servidor); uno nuevo todavía no la tiene.
export function puedeQuitarCampo(campo: CampoFormulario, hayRespuestas: boolean): boolean {
  return !(hayRespuestas && campo.clave);
}

export function puedeCambiarTipo(campo: CampoFormulario, hayRespuestas: boolean): boolean {
  return !(hayRespuestas && campo.clave);
}

export function puedeSerObligatorio(campo: CampoFormulario, hayRespuestas: boolean): boolean {
  return !(hayRespuestas && !campo.clave);
}

export function opcionesDeTexto(texto: string): string[] {
  return texto
    .split("\n")
    .map((linea) => linea.trim())
    .filter((linea) => linea !== "");
}

export function textoDeOpciones(opciones: string[] | null): string {
  return (opciones ?? []).join("\n");
}

export function validarEntrada(entrada: FormularioEntrada, hayRespuestas = false): string | null {
  if (entrada.nombre.trim() === "") return "Poné un nombre al formulario.";
  if (entrada.campos.length === 0) return "El formulario necesita al menos un campo.";
  if (entrada.campos.length > MAX_CAMPOS) return `Un formulario admite hasta ${MAX_CAMPOS} campos.`;
  if (entrada.campos.filter((c) => c.tipo === "dni").length > 1) return "Un formulario admite un solo campo DNI.";
  for (const campo of entrada.campos) {
    if (campo.etiqueta.trim() === "") return "Cada campo necesita una pregunta o etiqueta.";
    if (campo.tipo === "opcion") {
      const opciones = (campo.opciones ?? []).map((o) => o.trim());
      const distintas = new Set(opciones.map((o) => o.toLowerCase()));
      if (opciones.length < 2 || opciones.length > MAX_OPCIONES || distintas.size !== opciones.length) {
        return `La lista «${campo.etiqueta}» necesita entre 2 y ${MAX_OPCIONES} opciones distintas.`;
      }
    }
    if (hayRespuestas && !campo.clave && campo.obligatorio) {
      return `El campo nuevo «${campo.etiqueta}» tiene que ser opcional porque el formulario ya tiene respuestas.`;
    }
  }
  if (entrada.cupo !== null && (!Number.isInteger(entrada.cupo) || entrada.cupo <= 0)) {
    return "El cupo tiene que ser un número entero mayor que cero.";
  }
  return null;
}

export function valorLegible(campo: CampoFormulario, valor: unknown): string {
  if (valor === undefined || valor === null) return "";
  if (campo.tipo === "si_no") return valor ? "Sí" : "No";
  if (campo.tipo === "fecha") {
    const partes = String(valor).split("-");
    return partes.length === 3 ? `${partes[2]}/${partes[1]}/${partes[0]}` : String(valor);
  }
  return String(valor);
}

export function nombreArchivoCsv(nombre: string): string {
  const base = nombre
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return `${base || "formulario"}-respuestas.csv`;
}

function dosDigitos(n: number): string {
  return String(n).padStart(2, "0");
}

// El input datetime-local trabaja en hora local sin zona; el servidor guarda un instante con zona.
export function isoAInputFecha(iso: string | null): string {
  if (!iso) return "";
  const f = new Date(iso);
  return `${f.getFullYear()}-${dosDigitos(f.getMonth() + 1)}-${dosDigitos(f.getDate())}T${dosDigitos(f.getHours())}:${dosDigitos(f.getMinutes())}`;
}

export function inputFechaAIso(valor: string): string | null {
  if (!valor) return null;
  const fecha = new Date(valor);
  return Number.isNaN(fecha.getTime()) ? null : fecha.toISOString();
}
```

- [ ] **Step 5: Agregar el permiso a los tipos de sesión y de usuarios**

En `frontend/lib/admin-api.ts`, el tipo `AdminSesionInfo` queda:

```ts
export type AdminSesionInfo = {
  email: string;
  rol: "super_admin" | "admin_organismo";
  organismo: string | null;
  puede_crear_formularios: boolean;
};
```

En `frontend/lib/admin-usuarios-api.ts`:
- `AdminUsuario` suma `puede_crear_formularios: boolean;` (después de `activo`).
- `UsuarioFormValores` suma `puede_crear_formularios: boolean;` (después de `activo`).
- En `editarUsuario`, el cuerpo del `JSON.stringify` suma `puede_crear_formularios: datos.puede_crear_formularios,` (después de `activo: datos.activo,`).

- [ ] **Step 6: Correr los tests, `tsc` y la suite**

Run: `timeout 100 npx vitest run lib/formularios-ui.test.ts 2>&1 | grep -E "Tests |FAIL" | head -3`
Expected: todos PASS.

Run: `timeout 100 npx tsc --noEmit 2>&1 | head -10`
Expected: errores **solo** en `app/admin/usuarios/page.tsx` (los valores iniciales no incluyen el campo nuevo obligatorio; se arregla en la Task 7); ningún otro. Si aparece otro error, corregirlo antes de seguir.

- [ ] **Step 7: Commit**

(Los dos archivos con error de tipos se corrigen en la Task 7; para no dejar un commit que no compile, **no commitear todavía** `admin-usuarios-api.ts` ni `admin-api.ts`: commitearlos junto con la Task 7.)

```bash
git add frontend/lib/admin-formularios-api.ts frontend/lib/formularios-ui.ts frontend/lib/formularios-ui.test.ts
git commit -m "feat: cliente de la API y lógica de las pantallas de formularios"
```

---

### Task 7: Pantallas del panel (lista, editor, respuestas) e interruptor en Usuarios

**Files:**
- Create: `frontend/components/PaginadorSimple.tsx`
- Create: `frontend/components/FormularioEditor.tsx`
- Create: `frontend/app/admin/formularios/page.tsx`
- Create: `frontend/app/admin/formularios/nuevo/page.tsx`
- Create: `frontend/app/admin/formularios/[id]/page.tsx`
- Create: `frontend/app/admin/formularios/[id]/respuestas/page.tsx`
- Create: `frontend/app/admin/formularios/[id]/respuestas/[rid]/page.tsx`
- Modify: `frontend/app/admin/layout.tsx` (ítem "Formularios" en la barra)
- Modify: `frontend/components/UsuarioForm.tsx`, `frontend/app/admin/usuarios/page.tsx` (interruptor)
- Modify (ya editados en la Task 6, se commitean acá): `frontend/lib/admin-api.ts`, `frontend/lib/admin-usuarios-api.ts`

**Interfaces:**
- Consumes: todo lo de la Task 6; `useAdminActual()` (devuelve `AdminSesionInfo | null`, ahora con `puede_crear_formularios`); `listarTramites()` y `listarOrganismos()` de `lib/admin-tramites-api.ts`; `ConversacionChat` (`components/ConversacionChat.tsx`).
- Produces: `FormularioEditor` con props `valoresIniciales: FormularioEntrada`, `organismos: Organismo[] | null` (solo el super admin al crear), `nombreOrganismo: string | null`, `tramites: TramiteResumen[]`, `hayRespuestas: boolean`, `soloLectura: boolean`, `guardando: boolean`, `error: string | null`, `onGuardar(datos)`, `onCancelar()`. Las pantallas viven en `/admin/formularios`, `/admin/formularios/nuevo`, `/admin/formularios/{id}`, `/admin/formularios/{id}/respuestas` y `/admin/formularios/{id}/respuestas/{rid}`.

(Las pantallas no tienen tests unitarios: el entorno de vitest es `node`. Su lógica está en `lib/formularios-ui.ts` (Task 6) y se verifica en el navegador en el Step 8.)

- [ ] **Step 1: Paginador reutilizable**

Crear `frontend/components/PaginadorSimple.tsx`:

```tsx
export function PaginadorSimple({
  pagina,
  totalPaginas,
  onCambiar,
}: {
  pagina: number;
  totalPaginas: number;
  onCambiar: (pagina: number) => void;
}) {
  return (
    <div className="mt-4 flex items-center gap-4 text-sm">
      <button onClick={() => onCambiar(pagina - 1)} disabled={pagina <= 1} className="boton-secundario">
        Anterior
      </button>
      <span>
        Página {pagina} de {totalPaginas}
      </span>
      <button onClick={() => onCambiar(pagina + 1)} disabled={pagina >= totalPaginas} className="boton-secundario">
        Siguiente
      </button>
    </div>
  );
}
```

- [ ] **Step 2: Editor de formulario**

Crear `frontend/components/FormularioEditor.tsx`:

```tsx
"use client";

import { useState, type FormEvent } from "react";
import type { CampoFormulario, EstadoFormulario, FormularioEntrada, TipoCampo } from "../lib/admin-formularios-api";
import type { Organismo, TramiteResumen } from "../lib/admin-tramites-api";
import {
  ETIQUETAS_TIPO,
  TIPOS_CAMPO,
  campoNuevo,
  inputFechaAIso,
  isoAInputFecha,
  opcionesDeTexto,
  puedeCambiarTipo,
  puedeQuitarCampo,
  puedeSerObligatorio,
  textoDeOpciones,
  validarEntrada,
} from "../lib/formularios-ui";

// El texto de las opciones se edita como texto libre (una por línea) y se convierte al guardar.
type CampoEditable = CampoFormulario & { textoOpciones: string };

const ESTADOS: { valor: EstadoFormulario; etiqueta: string }[] = [
  { valor: "borrador", etiqueta: "Borrador (no se ofrece)" },
  { valor: "activo", etiqueta: "Activo (el asistente lo ofrece)" },
  { valor: "cerrado", etiqueta: "Cerrado" },
];

function aEditable(campo: CampoFormulario): CampoEditable {
  return { ...campo, textoOpciones: textoDeOpciones(campo.opciones) };
}

function aCampo({ textoOpciones, ...campo }: CampoEditable): CampoFormulario {
  return { ...campo, opciones: campo.tipo === "opcion" ? opcionesDeTexto(textoOpciones) : null };
}

export function FormularioEditor({
  valoresIniciales,
  organismos,
  nombreOrganismo,
  tramites,
  hayRespuestas,
  soloLectura,
  guardando,
  error,
  onGuardar,
  onCancelar,
}: {
  valoresIniciales: FormularioEntrada;
  organismos: Organismo[] | null;
  nombreOrganismo: string | null;
  tramites: TramiteResumen[];
  hayRespuestas: boolean;
  soloLectura: boolean;
  guardando: boolean;
  error: string | null;
  onGuardar: (datos: FormularioEntrada) => void;
  onCancelar: () => void;
}) {
  const { campos: camposIniciales, ...resto } = valoresIniciales;
  const [datos, setDatos] = useState(resto);
  const [campos, setCampos] = useState<CampoEditable[]>(camposIniciales.map(aEditable));
  const [errorLocal, setErrorLocal] = useState<string | null>(null);

  function actualizar<K extends keyof typeof datos>(clave: K, valor: (typeof datos)[K]) {
    setDatos((anterior) => ({ ...anterior, [clave]: valor }));
  }

  function actualizarCampo(indice: number, cambios: Partial<CampoEditable>) {
    setCampos((anteriores) => anteriores.map((c, i) => (i === indice ? { ...c, ...cambios } : c)));
  }

  function mover(indice: number, delta: number) {
    setCampos((anteriores) => {
      const destino = indice + delta;
      if (destino < 0 || destino >= anteriores.length) return anteriores;
      const copia = [...anteriores];
      [copia[indice], copia[destino]] = [copia[destino], copia[indice]];
      return copia;
    });
  }

  const nombreActual = organismos
    ? (organismos.find((o) => o.id === datos.organismo_id)?.nombre ?? null)
    : nombreOrganismo;
  const tramitesDelOrganismo = tramites.filter((t) => t.organismo === nombreActual);

  function handleSubmit(evento: FormEvent) {
    evento.preventDefault();
    const entrada: FormularioEntrada = { ...datos, campos: campos.map(aCampo) };
    const problema =
      organismos && entrada.organismo_id === null ? "Elegí el organismo." : validarEntrada(entrada, hayRespuestas);
    setErrorLocal(problema);
    if (!problema) onGuardar(entrada);
  }

  return (
    <form onSubmit={handleSubmit} className="max-w-3xl space-y-4">
      <fieldset disabled={soloLectura} className="tarjeta space-y-3">
        {organismos ? (
          <div>
            <label className="campo-label">Organismo</label>
            <select
              aria-label="Organismo del formulario"
              value={datos.organismo_id ?? ""}
              onChange={(e) => {
                actualizar("organismo_id", e.target.value ? Number(e.target.value) : null);
                actualizar("tramite_id", null);
              }}
              className="campo-input w-full"
            >
              <option value="">Elegir…</option>
              {organismos.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.nombre}
                </option>
              ))}
            </select>
          </div>
        ) : (
          nombreOrganismo && (
            <p className="text-sm texto-secundario">
              Organismo: <span className="font-semibold">{nombreOrganismo}</span>
            </p>
          )
        )}

        <div>
          <label className="campo-label">Nombre del formulario</label>
          <input
            aria-label="Nombre del formulario"
            value={datos.nombre}
            onChange={(e) => actualizar("nombre", e.target.value)}
            className="campo-input w-full"
          />
        </div>

        <div>
          <label className="campo-label">¿Cuándo tiene que ofrecerlo el asistente?</label>
          <textarea
            aria-label="Cuándo ofrecerlo"
            value={datos.descripcion_uso}
            onChange={(e) => actualizar("descripcion_uso", e.target.value)}
            rows={2}
            maxLength={500}
            placeholder="Ej.: Cuando la persona quiera inscribirse a la capacitación de la Subsecretaría de Trabajo"
            className="campo-input w-full"
          />
        </div>

        <div>
          <label className="campo-label">¿Para qué se usan los datos? (el asistente lo dice antes de pedirlos)</label>
          <textarea
            aria-label="Finalidad de los datos"
            value={datos.aviso_finalidad}
            onChange={(e) => actualizar("aviso_finalidad", e.target.value)}
            rows={2}
            maxLength={500}
            placeholder="Ej.: La Subsecretaría de Trabajo usa tus datos para inscribirte a la capacitación."
            className="campo-input w-full"
          />
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <label className="campo-label">Trámite vinculado (opcional)</label>
            <select
              aria-label="Trámite vinculado"
              value={datos.tramite_id ?? ""}
              onChange={(e) => actualizar("tramite_id", e.target.value || null)}
              className="campo-input w-full"
            >
              <option value="">Ninguno</option>
              {tramitesDelOrganismo.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.id} · {t.nombre_oficial}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="campo-label">Estado</label>
            <select
              aria-label="Estado del formulario"
              value={datos.estado}
              onChange={(e) => actualizar("estado", e.target.value as EstadoFormulario)}
              className="campo-input w-full"
            >
              {ESTADOS.map((e) => (
                <option key={e.valor} value={e.valor}>
                  {e.etiqueta}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="campo-label">Fecha límite (opcional)</label>
            <input
              type="datetime-local"
              aria-label="Fecha límite"
              value={isoAInputFecha(datos.fecha_cierre)}
              onChange={(e) => actualizar("fecha_cierre", inputFechaAIso(e.target.value))}
              className="campo-input w-full"
            />
          </div>
          <div>
            <label className="campo-label">Cupo máximo de respuestas (opcional)</label>
            <input
              type="number"
              min={1}
              aria-label="Cupo máximo"
              value={datos.cupo ?? ""}
              onChange={(e) => actualizar("cupo", e.target.value === "" ? null : Number(e.target.value))}
              className="campo-input w-full"
            />
          </div>
        </div>
      </fieldset>

      <fieldset disabled={soloLectura} className="space-y-3">
        <h2 className="text-sm font-semibold">Campos que pide el asistente</h2>
        {hayRespuestas && (
          <p className="text-xs texto-secundario">
            Este formulario ya tiene respuestas: no se pueden quitar ni cambiar de tipo los campos existentes, y los
            campos nuevos tienen que ser opcionales.
          </p>
        )}
        {campos.map((campo, i) => (
          <div key={campo.clave ?? `nuevo-${i}`} className="tarjeta space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <input
                aria-label={`Etiqueta del campo ${i + 1}`}
                value={campo.etiqueta}
                onChange={(e) => actualizarCampo(i, { etiqueta: e.target.value })}
                placeholder="Pregunta o etiqueta"
                className="campo-input min-w-[200px] flex-1"
              />
              <select
                aria-label={`Tipo del campo ${i + 1}`}
                value={campo.tipo}
                disabled={!puedeCambiarTipo(campo, hayRespuestas)}
                onChange={(e) => actualizarCampo(i, { tipo: e.target.value as TipoCampo })}
                className="campo-input"
              >
                {TIPOS_CAMPO.map((tipo) => (
                  <option key={tipo} value={tipo}>
                    {ETIQUETAS_TIPO[tipo]}
                  </option>
                ))}
              </select>
              <label className="flex items-center gap-1 text-sm">
                <input
                  type="checkbox"
                  aria-label={`Campo ${i + 1} obligatorio`}
                  checked={campo.obligatorio}
                  disabled={!puedeSerObligatorio(campo, hayRespuestas)}
                  onChange={(e) => actualizarCampo(i, { obligatorio: e.target.checked })}
                />
                Obligatorio
              </label>
              <button type="button" aria-label={`Subir campo ${i + 1}`} onClick={() => mover(i, -1)} className="boton-neutro">
                ↑
              </button>
              <button type="button" aria-label={`Bajar campo ${i + 1}`} onClick={() => mover(i, 1)} className="boton-neutro">
                ↓
              </button>
              <button
                type="button"
                aria-label={`Quitar campo ${i + 1}`}
                disabled={!puedeQuitarCampo(campo, hayRespuestas)}
                onClick={() => setCampos((anteriores) => anteriores.filter((_, k) => k !== i))}
                className="boton-neutro"
              >
                Quitar
              </button>
            </div>
            {campo.tipo === "opcion" && (
              <textarea
                aria-label={`Opciones del campo ${i + 1}`}
                value={campo.textoOpciones}
                onChange={(e) => actualizarCampo(i, { textoOpciones: e.target.value })}
                rows={3}
                placeholder="Una opción por línea"
                className="campo-input w-full"
              />
            )}
          </div>
        ))}
        <button
          type="button"
          onClick={() => setCampos((anteriores) => [...anteriores, aEditable({ ...campoNuevo(), obligatorio: !hayRespuestas })])}
          disabled={campos.length >= 30}
          className="boton-secundario"
        >
          Agregar campo
        </button>
      </fieldset>

      {(errorLocal || error) && <p className="text-sm texto-error">{errorLocal ?? error}</p>}

      <div className="flex gap-2">
        {!soloLectura && (
          <button type="submit" disabled={guardando} className="boton-primario">
            {guardando ? "Guardando…" : "Guardar"}
          </button>
        )}
        <button type="button" onClick={onCancelar} className="boton-neutro">
          {soloLectura ? "Volver" : "Cancelar"}
        </button>
      </div>
    </form>
  );
}
```

- [ ] **Step 3: Lista, alta y edición**

Crear `frontend/app/admin/formularios/page.tsx`:

```tsx
"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { PaginadorSimple } from "../../../components/PaginadorSimple";
import { useAdminActual } from "../../../hooks/useAdminActual";
import { listarFormularios, type PaginaFormularios } from "../../../lib/admin-formularios-api";
import { textoCupo, textoEstado } from "../../../lib/formularios-ui";

const POR_PAGINA = 10;

export default function FormulariosPage() {
  const admin = useAdminActual();
  const [datos, setDatos] = useState<PaginaFormularios | null>(null);
  const [pagina, setPagina] = useState(1);
  const [error, setError] = useState(false);
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    cargar();
  }, [pagina]);

  async function cargar() {
    setCargando(true);
    setError(false);
    try {
      setDatos(await listarFormularios(pagina, POR_PAGINA));
    } catch {
      setError(true);
    } finally {
      setCargando(false);
    }
  }

  if (cargando) return <p className="p-4 text-sm texto-secundario">Cargando…</p>;

  if (error) {
    return (
      <div className="p-4">
        <p className="text-sm texto-error">No se pudo cargar la lista de formularios</p>
        <button onClick={cargar} className="boton-secundario mt-2">
          Reintentar
        </button>
      </div>
    );
  }

  const totalPaginas = Math.max(1, Math.ceil((datos?.total ?? 0) / POR_PAGINA));

  return (
    <div className="p-4">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-lg font-semibold">Formularios</h1>
        {admin?.puede_crear_formularios && (
          <Link href="/admin/formularios/nuevo" className="boton-primario">
            Nuevo formulario
          </Link>
        )}
      </div>

      {datos?.total === 0 ? (
        <p className="text-sm texto-secundario">Todavía no hay formularios</p>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="tabla-cabecera">
              <th className="p-2">Nombre</th>
              <th className="p-2">Organismo</th>
              <th className="p-2">Estado</th>
              <th className="p-2">Respuestas</th>
              <th className="p-2">Fecha límite</th>
              <th className="p-2"></th>
            </tr>
          </thead>
          <tbody>
            {datos!.formularios.map((f) => (
              <tr key={f.id} className="tabla-fila">
                <td className="p-2">
                  <Link href={`/admin/formularios/${f.id}`} className="boton-secundario">
                    {f.nombre}
                  </Link>
                </td>
                <td className="p-2">{f.organismo}</td>
                <td className="p-2">{textoEstado(f.estado_efectivo)}</td>
                <td className="p-2">{textoCupo(f.respuestas, f.cupo)}</td>
                <td className="p-2">{f.fecha_cierre ? new Date(f.fecha_cierre).toLocaleString() : "—"}</td>
                <td className="p-2">
                  <Link href={`/admin/formularios/${f.id}/respuestas`} className="underline">
                    Ver respuestas
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {datos && datos.total > 0 && (
        <PaginadorSimple pagina={pagina} totalPaginas={totalPaginas} onCambiar={setPagina} />
      )}
    </div>
  );
}
```

Crear `frontend/app/admin/formularios/nuevo/page.tsx`:

```tsx
"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { FormularioEditor } from "../../../../components/FormularioEditor";
import { useAdminActual } from "../../../../hooks/useAdminActual";
import { crearFormulario, type FormularioEntrada } from "../../../../lib/admin-formularios-api";
import {
  listarOrganismos,
  listarTramites,
  type Organismo,
  type TramiteResumen,
} from "../../../../lib/admin-tramites-api";
import { campoNuevo } from "../../../../lib/formularios-ui";

const INICIAL: FormularioEntrada = {
  organismo_id: null,
  nombre: "",
  descripcion_uso: "",
  aviso_finalidad: "",
  tramite_id: null,
  estado: "borrador",
  fecha_cierre: null,
  cupo: null,
  campos: [campoNuevo()],
};

export default function NuevoFormularioPage() {
  const router = useRouter();
  const admin = useAdminActual();
  const [organismos, setOrganismos] = useState<Organismo[]>([]);
  const [tramites, setTramites] = useState<TramiteResumen[]>([]);
  const [cargado, setCargado] = useState(false);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!admin) return;
    const tareas: Promise<unknown>[] = [listarTramites().then(setTramites).catch(() => setTramites([]))];
    if (admin.rol === "super_admin") tareas.push(listarOrganismos().then(setOrganismos).catch(() => setOrganismos([])));
    Promise.all(tareas).finally(() => setCargado(true));
  }, [admin]);

  async function handleGuardar(datos: FormularioEntrada) {
    setGuardando(true);
    setError(null);
    try {
      const { id } = await crearFormulario(datos);
      router.push(`/admin/formularios/${id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo crear el formulario");
      setGuardando(false);
    }
  }

  if (!admin || !cargado) return <p className="p-4 text-sm texto-secundario">Cargando…</p>;

  if (!admin.puede_crear_formularios) {
    return <p className="p-4 text-sm texto-secundario">No tenés permiso para crear formularios.</p>;
  }

  return (
    <div className="p-4">
      <h1 className="mb-4 text-lg font-semibold">Nuevo formulario</h1>
      <FormularioEditor
        valoresIniciales={INICIAL}
        organismos={admin.rol === "super_admin" ? organismos : null}
        nombreOrganismo={admin.organismo}
        tramites={tramites}
        hayRespuestas={false}
        soloLectura={false}
        guardando={guardando}
        error={error}
        onGuardar={handleGuardar}
        onCancelar={() => router.push("/admin/formularios")}
      />
    </div>
  );
}
```

Crear `frontend/app/admin/formularios/[id]/page.tsx`:

```tsx
"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { FormularioEditor } from "../../../../components/FormularioEditor";
import { useAdminActual } from "../../../../hooks/useAdminActual";
import {
  editarFormulario,
  obtenerFormulario,
  type FormularioDetalle,
  type FormularioEntrada,
} from "../../../../lib/admin-formularios-api";
import { listarTramites, type TramiteResumen } from "../../../../lib/admin-tramites-api";
import { textoCupo, textoEstado } from "../../../../lib/formularios-ui";

function aEntrada(f: FormularioDetalle): FormularioEntrada {
  return {
    organismo_id: f.organismo_id,
    nombre: f.nombre,
    descripcion_uso: f.descripcion_uso,
    aviso_finalidad: f.aviso_finalidad,
    tramite_id: f.tramite_id,
    estado: f.estado,
    fecha_cierre: f.fecha_cierre,
    cupo: f.cupo,
    campos: f.campos,
  };
}

export default function FormularioDetallePage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const admin = useAdminActual();
  const [formulario, setFormulario] = useState<FormularioDetalle | null | undefined>(undefined);
  const [tramites, setTramites] = useState<TramiteResumen[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [errorCarga, setErrorCarga] = useState(false);
  const [guardando, setGuardando] = useState(false);
  const [guardado, setGuardado] = useState(false);

  useEffect(() => {
    cargar();
  }, [params.id]);

  async function cargar() {
    setErrorCarga(false);
    try {
      const [detalle, lista] = await Promise.all([
        obtenerFormulario(params.id),
        listarTramites().catch(() => [] as TramiteResumen[]),
      ]);
      setFormulario(detalle);
      setTramites(lista);
    } catch {
      setErrorCarga(true);
    }
  }

  async function handleGuardar(datos: FormularioEntrada) {
    setGuardando(true);
    setError(null);
    setGuardado(false);
    try {
      await editarFormulario(params.id, datos);
      setFormulario(await obtenerFormulario(params.id));
      setGuardado(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo guardar el formulario");
    } finally {
      setGuardando(false);
    }
  }

  if (errorCarga) {
    return (
      <div className="p-4">
        <p className="text-sm texto-error">No se pudo cargar el formulario</p>
        <button onClick={cargar} className="boton-secundario mt-2">
          Reintentar
        </button>
      </div>
    );
  }

  if (formulario === undefined || !admin) return <p className="p-4 text-sm texto-secundario">Cargando…</p>;

  if (formulario === null) {
    return (
      <div className="p-4">
        <p className="text-sm texto-secundario">Formulario no encontrado</p>
        <Link href="/admin/formularios" className="boton-secundario">
          Volver a la lista
        </Link>
      </div>
    );
  }

  return (
    <div className="p-4">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-lg font-semibold">{formulario.nombre}</h1>
          <p className="text-sm texto-secundario">
            {textoEstado(formulario.estado_efectivo)} · Respuestas: {textoCupo(formulario.respuestas, formulario.cupo)}
          </p>
        </div>
        <Link href={`/admin/formularios/${formulario.id}/respuestas`} className="boton-secundario">
          Ver respuestas ({formulario.respuestas})
        </Link>
      </div>
      {guardado && <p className="mb-2 text-sm text-emerald-600">Cambios guardados.</p>}
      <FormularioEditor
        key={formulario.actualizado_en}
        valoresIniciales={aEntrada(formulario)}
        organismos={null}
        nombreOrganismo={formulario.organismo}
        tramites={tramites}
        hayRespuestas={formulario.hay_respuestas}
        soloLectura={!admin.puede_crear_formularios}
        guardando={guardando}
        error={error}
        onGuardar={handleGuardar}
        onCancelar={() => router.push("/admin/formularios")}
      />
    </div>
  );
}
```

- [ ] **Step 4: Respuestas y detalle de una respuesta**

Crear `frontend/app/admin/formularios/[id]/respuestas/page.tsx`:

```tsx
"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { PaginadorSimple } from "../../../../../components/PaginadorSimple";
import {
  descargarCsv,
  listarRespuestas,
  obtenerFormulario,
  type PaginaRespuestas,
} from "../../../../../lib/admin-formularios-api";
import { nombreArchivoCsv, valorLegible } from "../../../../../lib/formularios-ui";

const POR_PAGINA = 20;

export default function RespuestasPage() {
  const params = useParams<{ id: string }>();
  const [nombre, setNombre] = useState("");
  const [datos, setDatos] = useState<PaginaRespuestas | null>(null);
  const [pagina, setPagina] = useState(1);
  const [error, setError] = useState(false);
  const [cargando, setCargando] = useState(true);
  const [errorCsv, setErrorCsv] = useState<string | null>(null);

  useEffect(() => {
    obtenerFormulario(params.id).then((f) => setNombre(f?.nombre ?? ""));
  }, [params.id]);

  useEffect(() => {
    cargar();
  }, [pagina, params.id]);

  async function cargar() {
    setCargando(true);
    setError(false);
    try {
      setDatos(await listarRespuestas(params.id, pagina, POR_PAGINA));
    } catch {
      setError(true);
    } finally {
      setCargando(false);
    }
  }

  async function handleExportar() {
    setErrorCsv(null);
    try {
      await descargarCsv(params.id, nombreArchivoCsv(nombre));
    } catch (err) {
      setErrorCsv(err instanceof Error ? err.message : "No se pudo exportar el CSV");
    }
  }

  if (cargando) return <p className="p-4 text-sm texto-secundario">Cargando…</p>;

  if (error || !datos) {
    return (
      <div className="p-4">
        <p className="text-sm texto-error">No se pudieron cargar las respuestas</p>
        <button onClick={cargar} className="boton-secundario mt-2">
          Reintentar
        </button>
      </div>
    );
  }

  const totalPaginas = Math.max(1, Math.ceil(datos.total / POR_PAGINA));

  return (
    <div className="p-4">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <div>
          <Link href={`/admin/formularios/${params.id}`} className="text-sm underline">
            ← {nombre || "Formulario"}
          </Link>
          <h1 className="text-lg font-semibold">Respuestas ({datos.total})</h1>
        </div>
        <button onClick={handleExportar} className="boton-primario">
          Exportar CSV
        </button>
      </div>
      {errorCsv && <p className="mb-2 text-sm texto-error">{errorCsv}</p>}

      {datos.total === 0 ? (
        <p className="text-sm texto-secundario">Todavía no hay respuestas</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="tabla-cabecera">
                <th className="p-2">Fecha</th>
                {datos.campos.map((c) => (
                  <th key={c.clave} className="p-2">
                    {c.etiqueta}
                  </th>
                ))}
                <th className="p-2"></th>
              </tr>
            </thead>
            <tbody>
              {datos.respuestas.map((r) => (
                <tr key={r.id} className="tabla-fila">
                  <td className="p-2">{new Date(r.creado_en).toLocaleString()}</td>
                  {datos.campos.map((c) => (
                    <td key={c.clave} className="p-2">
                      {valorLegible(c, r.valores[c.clave ?? ""])}
                    </td>
                  ))}
                  <td className="p-2">
                    <Link href={`/admin/formularios/${params.id}/respuestas/${r.id}`} className="underline">
                      Ver
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {datos.total > 0 && <PaginadorSimple pagina={pagina} totalPaginas={totalPaginas} onCambiar={setPagina} />}
    </div>
  );
}
```

Crear `frontend/app/admin/formularios/[id]/respuestas/[rid]/page.tsx`:

```tsx
"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ConversacionChat } from "../../../../../../components/ConversacionChat";
import { useAdminActual } from "../../../../../../hooks/useAdminActual";
import {
  borrarRespuesta,
  obtenerRespuesta,
  type RespuestaDetalle,
} from "../../../../../../lib/admin-formularios-api";
import { valorLegible } from "../../../../../../lib/formularios-ui";

export default function RespuestaDetallePage() {
  const params = useParams<{ id: string; rid: string }>();
  const router = useRouter();
  const admin = useAdminActual();
  const [respuesta, setRespuesta] = useState<RespuestaDetalle | null | undefined>(undefined);
  const [error, setError] = useState<string | null>(null);
  const [errorCarga, setErrorCarga] = useState(false);
  const [borrando, setBorrando] = useState(false);

  useEffect(() => {
    cargar();
  }, [params.id, params.rid]);

  async function cargar() {
    setErrorCarga(false);
    try {
      setRespuesta(await obtenerRespuesta(params.id, params.rid));
    } catch {
      setErrorCarga(true);
    }
  }

  async function handleBorrar() {
    if (!window.confirm("¿Borrar esta respuesta? Deja de contarse en el cupo y libera el DNI.")) return;
    setBorrando(true);
    setError(null);
    try {
      await borrarRespuesta(params.id, params.rid);
      router.push(`/admin/formularios/${params.id}/respuestas`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo borrar la respuesta");
      setBorrando(false);
    }
  }

  if (errorCarga) {
    return (
      <div className="p-4">
        <p className="text-sm texto-error">No se pudo cargar la respuesta</p>
        <button onClick={cargar} className="boton-secundario mt-2">
          Reintentar
        </button>
      </div>
    );
  }

  if (respuesta === undefined || !admin) return <p className="p-4 text-sm texto-secundario">Cargando…</p>;

  if (respuesta === null) {
    return (
      <div className="p-4">
        <p className="text-sm texto-secundario">Respuesta no encontrada</p>
        <Link href={`/admin/formularios/${params.id}/respuestas`} className="boton-secundario">
          Volver a las respuestas
        </Link>
      </div>
    );
  }

  return (
    <div className="p-4">
      <Link href={`/admin/formularios/${params.id}/respuestas`} className="text-sm underline">
        ← Respuestas de {respuesta.formulario.nombre}
      </Link>
      <div className="tarjeta mb-4 mt-2 max-w-2xl">
        <p className="mb-2 text-xs texto-secundario">{new Date(respuesta.creado_en).toLocaleString()}</p>
        {respuesta.campos.map((c) => (
          <p key={c.clave}>
            <span className="font-semibold">{c.etiqueta}:</span> {valorLegible(c, respuesta.valores[c.clave ?? ""]) || "—"}
          </p>
        ))}
        {admin.puede_crear_formularios && (
          <button onClick={handleBorrar} disabled={borrando} className="boton-neutro mt-3">
            Borrar respuesta
          </button>
        )}
        {error && <p className="mt-2 text-sm texto-error">{error}</p>}
      </div>

      <h2 className="mb-2 text-sm font-semibold texto-secundario">Conversación de origen</h2>
      <ConversacionChat mensajes={respuesta.mensajes} />
    </div>
  );
}
```

- [ ] **Step 5: Navegación e interruptor en Usuarios**

En `frontend/app/admin/layout.tsx`, agregar el ítem **después** del de Contacto y antes del de Feedback:

```tsx
            <li>
              <ItemNav href="/admin/formularios" pathname={pathname} icono="▤">
                Formularios
              </ItemNav>
            </li>
```

En `frontend/components/UsuarioForm.tsx`, agregar **después** del bloque `{datos.rol === "admin_organismo" && ( ... Organismo ... )}` y antes del `{esEdicion && (` de "Activo":

```tsx
      {datos.rol === "admin_organismo" && (
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={datos.puede_crear_formularios}
            onChange={(e) => actualizar("puede_crear_formularios", e.target.checked)}
          />
          Puede crear formularios
        </label>
      )}
```

En `frontend/app/admin/usuarios/page.tsx`:
- En `VALORES_VACIOS` agregar `puede_crear_formularios: false,` (después de `activo: true,`).
- En `valoresParaEditar` agregar `puede_crear_formularios: usuario.puede_crear_formularios,` (después de `activo: usuario.activo,`).
- En la tabla: agregar `<th className="p-2">Formularios</th>` después de `<th className="p-2">Activo</th>`, y la celda correspondiente después de la de "Activo":

```tsx
                <td className="p-2">
                  {usuario.rol === "super_admin" ? "Todos" : usuario.puede_crear_formularios ? "Puede crear" : "Solo ver"}
                </td>
```

- [ ] **Step 6: `tsc` y suite del frontend**

Run (desde `frontend/`): `timeout 100 npx tsc --noEmit && echo tsc-ok`
Expected: `tsc-ok` (sin errores).

Run: `timeout 100 npx vitest run 2>&1 | grep -E "Test Files|Tests "`
Expected: todos PASS.

- [ ] **Step 7: Preparar la verificación en navegador (datos de prueba y servidores)**

Todo contra la base **local de tests**, nunca la remota. Crear en el scratchpad de la sesión (`$SCRATCH`) el archivo `seed_formularios.py`:

```python
import os
import sys

import psycopg

from agent.admin import repository as admin_repository
from agent.admin import security
from agent import sessions
from ingest import repository as repo

URL = os.environ.get("TEST_DATABASE_URL", "postgresql://macacha:macacha@localhost:5432/macacha_test")
with psycopg.connect(URL) as c:
    for tabla in ("formulario_respuestas", "formulario_campos", "formularios", "solicitudes_contacto", "admins"):
        c.execute(f"DELETE FROM {tabla}")
    trabajo = repo.upsert_organismo(c, "Subsecretaría de Trabajo")
    repo.upsert_organismo(c, "Registro Civil")
    repo.upsert_tramite(c, "TR-0001", trabajo, "Trabajo", "Denuncia laboral")
    clave = security.hash_password("visual-pass-123")
    admin_repository.crear_admin(c, "super@x.com", clave, "super_admin", None)
    admin_repository.crear_admin(c, "trabajo@x.com", clave, "admin_organismo", trabajo)
    admin_repository.crear_admin(c, "lector@x.com", clave, "admin_organismo", trabajo)
    c.commit()
    print("sembrado")
```

y `seed_respuesta.py` (recibe el id del formulario):

```python
import os
import sys
import uuid

import psycopg

from agent import sessions
from agent.admin import formularios_repository as formularios

URL = os.environ.get("TEST_DATABASE_URL", "postgresql://macacha:macacha@localhost:5432/macacha_test")
with psycopg.connect(URL) as c:
    sesion = str(uuid.uuid4())
    sessions.crear_sesion_si_no_existe(c, sesion)
    sessions.guardar_mensaje(c, sesion, "user", "Quiero anotarme a la capacitación")
    sessions.guardar_mensaje(c, sesion, "assistant", "Perfecto, ¿me pasás tu nombre y tu DNI?")
    formularios.guardar_respuesta(
        c, sys.argv[1], sesion,
        {"nombre_y_apellido": "Ana Pérez", "dni": "30.123.456", "telefono": "387 456-7890", "participaria_de_la_capacitacion": "sí"},
    )
    c.commit()
    print("respuesta cargada")
```

Run (desde `backend/`, con la base de tests ya con el esquema aplicado): `PYTHONPATH=. .venv/bin/python "$SCRATCH/seed_formularios.py" 2>&1 | tail -1`
Expected: `sembrado`.

Levantar los servidores auxiliares (puertos 8001 y 3001, como en las verificaciones anteriores):

```bash
cd backend && TDB=$(grep -E "^TEST_DATABASE_URL=" ../.env | cut -d= -f2-)
DATABASE_URL="$TDB" ADMIN_JWT_SECRET=visual-secret FRONTEND_ORIGIN=http://localhost:3001 nohup .venv/bin/uvicorn agent.api:app --port 8001 &> "$SCRATCH/back-aux.log" &
cd ../frontend && NEXT_PUBLIC_API_URL=http://localhost:8001 nohup npx next dev -p 3001 &> "$SCRATCH/front-aux.log" &
timeout 60 bash -c 'until curl -sf http://localhost:8001/tramites-frecuentes >/dev/null; do sleep 1; done'
timeout 90 bash -c 'until curl -sf http://localhost:3001 >/dev/null; do sleep 1; done'
```

- [ ] **Step 8: Verificar las pantallas en Chromium**

Crear `$SCRATCH/formularios-visual.cjs`:

```js
const { createRequire } = require("module");
const { execFileSync } = require("child_process");
const path = require("path");
const puppeteer = createRequire(path.join(process.cwd(), "package.json"))("puppeteer-core");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const BACKEND = process.env.BACKEND_DIR; // .../backend
const SCRATCH = __dirname;
let fallas = 0;
const check = (nombre, ok, detalle = "") => {
  if (!ok) fallas++;
  console.log(`${ok ? "OK  " : "FAIL"} ${nombre}${detalle ? " — " + detalle : ""}`);
};

async function login(page, email) {
  await page.goto("http://localhost:3001/admin/login", { waitUntil: "networkidle0" });
  await page.type("input[type=email]", email);
  await page.type("input[type=password]", "visual-pass-123");
  await page.evaluate(() => [...document.querySelectorAll("button")].find((b) => /Ingresar/.test(b.textContent)).click());
  await page.waitForFunction(() => !location.pathname.includes("login"), { timeout: 15000 });
}
const clic = (page, texto, selector = "button") =>
  page.evaluate((t, s) => { const e = [...document.querySelectorAll(s)].find((x) => x.textContent.trim() === t); if (e) e.click(); return !!e; }, texto, selector);
const logout = async (page) => { await clic(page, "Cerrar sesión"); await sleep(800); };
const texto = (page) => page.evaluate(() => document.body.innerText);

(async () => {
  const browser = await puppeteer.launch({ executablePath: "/snap/bin/chromium", headless: "new", args: ["--no-sandbox"] });
  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 1000 });
  page.on("dialog", (d) => d.accept());

  // 1) El super admin habilita al usuario "trabajo" desde Usuarios
  await login(page, "super@x.com");
  await page.goto("http://localhost:3001/admin/usuarios", { waitUntil: "networkidle0" });
  await page.evaluate(() => [...document.querySelectorAll("tr")].find((r) => r.textContent.includes("trabajo@x.com")).querySelector("button").click());
  await sleep(300);
  await page.evaluate(() => [...document.querySelectorAll("label")].find((l) => l.textContent.includes("Puede crear formularios")).querySelector("input").click());
  await clic(page, "Guardar");
  await sleep(1200);
  const fila = await page.evaluate(() => [...document.querySelectorAll("tr")].find((r) => r.textContent.includes("trabajo@x.com")).innerText);
  const filaLector = await page.evaluate(() => [...document.querySelectorAll("tr")].find((r) => r.textContent.includes("lector@x.com")).innerText);
  check("1a Usuarios: 'trabajo' queda con 'Puede crear'", fila.includes("Puede crear"), fila.replace(/\s+/g, " "));
  check("1b Usuarios: 'lector' sigue en 'Solo ver'", filaLector.includes("Solo ver"));
  await page.screenshot({ path: path.join(SCRATCH, "form-1-usuarios.png") });
  await logout(page);

  // 2) El usuario habilitado crea un formulario desde la pantalla
  await login(page, "trabajo@x.com");
  await page.goto("http://localhost:3001/admin/formularios", { waitUntil: "networkidle0" });
  check("2a Lista: aparece 'Nuevo formulario' para el habilitado", (await texto(page)).includes("Nuevo formulario"));
  await page.goto("http://localhost:3001/admin/formularios/nuevo", { waitUntil: "networkidle0" });
  await page.waitForSelector('input[aria-label="Nombre del formulario"]');
  await page.type('input[aria-label="Nombre del formulario"]', "Inscripción a la capacitación");
  await page.type('textarea[aria-label="Cuándo ofrecerlo"]', "Inscripción a la capacitación de Trabajo");
  await page.type('textarea[aria-label="Finalidad de los datos"]', "Trabajo usa tus datos para inscribirte.");
  const campos = [["Nombre y apellido", "texto"], ["DNI", "dni"], ["Teléfono", "telefono"], ["¿Participaría de la capacitación?", "si_no"]];
  for (let i = 0; i < campos.length; i++) {
    if (i > 0) await clic(page, "Agregar campo");
    await page.type(`input[aria-label="Etiqueta del campo ${i + 1}"]`, campos[i][0]);
    await page.select(`select[aria-label="Tipo del campo ${i + 1}"]`, campos[i][1]);
  }
  await page.select('select[aria-label="Estado del formulario"]', "activo");
  await page.type('input[aria-label="Cupo máximo"]', "40");
  await page.screenshot({ path: path.join(SCRATCH, "form-2-editor.png"), fullPage: true });
  await clic(page, "Guardar");
  await page.waitForFunction(() => /\/admin\/formularios\/[0-9a-f-]{36}$/.test(location.pathname), { timeout: 15000 });
  const formularioId = page.url().split("/").pop();
  check("2b Alta: redirige al detalle del formulario nuevo", /^[0-9a-f-]{36}$/.test(formularioId));
  await sleep(800);
  const detalle = await texto(page);
  check("2c Detalle: muestra nombre, estado y cupo", detalle.includes("Inscripción a la capacitación") && detalle.includes("Abierto") && detalle.includes("0 de 40"));

  // 3) Con respuestas cargadas solo se pueden agregar campos opcionales
  execFileSync(path.join(BACKEND, ".venv/bin/python"), [path.join(SCRATCH, "seed_respuesta.py"), formularioId], { cwd: BACKEND, env: { ...process.env, PYTHONPATH: "." } });
  await page.reload({ waitUntil: "networkidle0" });
  await clic(page, "Agregar campo");
  await page.type('input[aria-label="Etiqueta del campo 5"]', "Comentario");
  const nuevoObligatorio = await page.$eval('input[aria-label="Campo 5 obligatorio"]', (e) => ({ marcado: e.checked, deshabilitado: e.disabled }));
  check("3a Edición con respuestas: el campo nuevo nace opcional y no se puede volver obligatorio", !nuevoObligatorio.marcado && nuevoObligatorio.deshabilitado);
  const quitarDeshabilitado = await page.$eval('button[aria-label="Quitar campo 1"]', (e) => e.disabled);
  const tipoDeshabilitado = await page.$eval('select[aria-label="Tipo del campo 2"]', (e) => e.disabled);
  check("3b Edición con respuestas: los campos existentes no se quitan ni cambian de tipo", quitarDeshabilitado && tipoDeshabilitado);
  await clic(page, "Guardar");
  await page.waitForFunction(() => document.body.innerText.includes("Cambios guardados"), { timeout: 10000 });
  await page.reload({ waitUntil: "networkidle0" });
  check("3c Guardar agrega el campo nuevo y conserva las respuestas", (await page.$('input[aria-label="Etiqueta del campo 5"]')) !== null);

  // 4) Respuestas: tabla, CSV, detalle y borrado
  await page.goto(`http://localhost:3001/admin/formularios/${formularioId}/respuestas`, { waitUntil: "networkidle0" });
  const tabla = await texto(page);
  check("4a Respuestas: la tabla muestra el DNI normalizado y 'Sí'", tabla.includes("30123456") && tabla.includes("Ana Pérez") && tabla.includes("Sí"));
  const csv = page.waitForResponse((r) => r.url().includes("respuestas.csv"));
  await clic(page, "Exportar CSV");
  const respuestaCsv = await csv;
  check("4b Exportar CSV: el servidor responde 200 con un archivo CSV", respuestaCsv.status() === 200 && (respuestaCsv.headers()["content-type"] || "").startsWith("text/csv"));
  await page.screenshot({ path: path.join(SCRATCH, "form-3-respuestas.png"), fullPage: true });
  await page.evaluate(() => [...document.querySelectorAll("a")].find((a) => a.textContent.trim() === "Ver").click());
  await page.waitForFunction(() => document.body.innerText.includes("Conversación de origen"));
  await sleep(500);
  const respuestaDetalle = await texto(page);
  check("4c Detalle de respuesta: valores y conversación de origen", respuestaDetalle.includes("DNI") && respuestaDetalle.includes("Quiero anotarme a la capacitación"));
  await page.screenshot({ path: path.join(SCRATCH, "form-4-detalle-respuesta.png"), fullPage: true });
  await clic(page, "Borrar respuesta");
  await page.waitForFunction(() => location.pathname.endsWith("/respuestas"), { timeout: 10000 });
  await sleep(600);
  check("4d Borrar: la respuesta desaparece de la tabla", (await texto(page)).includes("Todavía no hay respuestas"));
  await logout(page);

  // 5) Un usuario sin permiso de edición ve el formulario, pero no lo puede cambiar
  await login(page, "lector@x.com");
  await page.goto("http://localhost:3001/admin/formularios", { waitUntil: "networkidle0" });
  const lista = await texto(page);
  check("5a Sin permiso: ve la lista pero no el botón 'Nuevo formulario'", lista.includes("Inscripción a la capacitación") && !lista.includes("Nuevo formulario"));
  await page.goto(`http://localhost:3001/admin/formularios/${formularioId}`, { waitUntil: "networkidle0" });
  await sleep(500);
  const soloLectura = await page.$$eval("fieldset", (fs) => fs.every((f) => f.disabled));
  const hayGuardar = await page.evaluate(() => [...document.querySelectorAll("button")].some((b) => b.textContent.trim() === "Guardar"));
  check("5b Sin permiso: el editor está en solo lectura y sin botón Guardar", soloLectura && !hayGuardar);
  await page.screenshot({ path: path.join(SCRATCH, "form-5-solo-lectura.png"), fullPage: true });

  await browser.close();
  console.log(fallas ? `${fallas} FALLAS` : "todo OK");
  process.exit(fallas ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(2); });
```

Run (desde `frontend/`, con los servidores del Step 7 levantados): `BACKEND_DIR="$(cd ../backend && pwd)" timeout 240 node "$SCRATCH/formularios-visual.cjs"`
Expected: todas las líneas `OK` y `todo OK`. Mirar las capturas `form-*.png` del scratchpad y confirmar que se vean bien (editor, tabla de respuestas, detalle y solo lectura).

Si una verificación falla, corregir la pantalla (no el script) salvo que el selector del script esté mal; repetir hasta que pase.

- [ ] **Step 9: Apagar los servidores, limpiar los datos de prueba y commit**

```bash
for p in 8001 3001; do ss -ltnp | grep ":$p " | grep -o 'pid=[0-9]*' | cut -d= -f2 | xargs -r kill; done
cd backend && PYTHONPATH=. .venv/bin/python - <<'EOF'
import os, psycopg
url = os.environ.get("TEST_DATABASE_URL", "postgresql://macacha:macacha@localhost:5432/macacha_test")
with psycopg.connect(url) as c:
    for tabla in ("formulario_respuestas", "formulario_campos", "formularios", "mensajes", "sesiones", "admins"):
        c.execute(f"DELETE FROM {tabla}")
    c.commit()
print("base de test limpia")
EOF
cd .. && git add frontend/components/PaginadorSimple.tsx frontend/components/FormularioEditor.tsx "frontend/app/admin/formularios" frontend/app/admin/layout.tsx frontend/components/UsuarioForm.tsx frontend/app/admin/usuarios/page.tsx frontend/lib/admin-api.ts frontend/lib/admin-usuarios-api.ts
git commit -m "feat: pantallas de formularios en el panel e interruptor de permiso en Usuarios"
```

Verificar con `git status --short` que solo quedan sin commitear `frontend/package.json`, `frontend/package-lock.json` y `.claude/`.

---

### Task 8: Despliegue documentado, conversaciones reales y verificación final

**Files:**
- Modify: `docs/deploy-dokploy.md`
- (Sin cambios de código salvo que las conversaciones reales muestren un defecto crítico; ver Step 4.)

**Interfaces:**
- Consumes: todo lo anterior. La base local `macacha_chat_eval` (copia del catálogo, ya usada en evaluaciones previas) y el chat real (`build_real_chat_client`, `build_real_client`, `OPENAI_API_KEY` del `.env`).
- Produces: la nota de despliegue y la evidencia de las 10 conversaciones (resultado en el ledger y en el informe final; no se commitea el script).

- [ ] **Step 1: Nota de despliegue**

En `docs/deploy-dokploy.md`, en el paso 6, a continuación del párrafo de la consulta por voz (el que termina en "…el navegador bloqueará el micrófono.") y antes de `## 3. Push a GitHub`, agregar:

```markdown

   Los formularios por organismo agregan la columna `admins.puede_crear_formularios` y las tablas `formularios`,
   `formulario_campos` y `formulario_respuestas`. Mismo orden obligatorio: **primero** correr el esquema,
   **después** el backend y por último el frontend. Si el backend sale antes que el esquema, `GET /admin/me`,
   `/admin/usuarios` y `/admin/formularios*` devuelven 500 y el asistente falla al consultar formularios. Ningún
   usuario de organismo puede crear formularios hasta que el super admin lo habilite desde Usuarios. Las respuestas
   guardan el DNI y el teléfono de la ciudadanía: antes de usarlo en producción conviene definir la política de
   privacidad y de retención de esos datos.
```

- [ ] **Step 2: Suites completas**

Run (desde `backend/`): `timeout 280 .venv/bin/pytest -q -p no:cacheprovider 2>&1 | tail -1`
Expected: toda la suite PASS.

Run (desde `frontend/`): `timeout 100 npx vitest run 2>&1 | grep -E "Test Files|Tests "; timeout 100 npx tsc --noEmit && echo tsc-ok`
Expected: todos PASS y `tsc-ok`.

- [ ] **Step 3: Conversaciones reales contra la base local de evaluación**

**Reglas de seguridad de este paso:** usa SOLO `macacha_chat_eval` (local). No toca la base remota. Reemplaza el envío de mail por un registro en memoria (no sale ningún correo real). Gasta llamadas a OpenAI (unas 40 en total).

Aplicar el esquema a la base de evaluación: `psql postgresql://macacha:macacha@localhost:5432/macacha_chat_eval -f backend/db/schema.sql 2>&1 | grep -iE "^psql:.*error" | head -3; echo listo`
Expected: sin líneas de error.

Crear `$SCRATCH/formularios_chat.py`:

```python
import os
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv

load_dotenv("/home/seba/Escritorio/workspace/macacha/.env")
sys.path.insert(0, "/home/seba/Escritorio/workspace/macacha/backend")
import psycopg
from pgvector.psycopg import register_vector

from agent import formularios_tools
from agent.admin import formularios_repository as formularios
from agent.chat_client import build_real_chat_client
from agent.orchestrator import procesar_turno
from ingest.openai_client import build_real_client

DESTINO = "postgresql://macacha:macacha@localhost:5432/macacha_chat_eval"
assert "macacha_chat_eval" in DESTINO  # nunca la base remota
AVISOS: list = []
# Nunca se manda un mail real durante la evaluación: solo se registra.
formularios_tools.mail.enviar_mail = lambda destinatarios, asunto, cuerpo_texto: AVISOS.append((destinatarios, asunto))

N, D, T, SN = "texto", "dni", "telefono", "si_no"
CAMPOS_F1 = [
    {"etiqueta": "Nombre y apellido", "tipo": N, "obligatorio": True, "opciones": None},
    {"etiqueta": "DNI", "tipo": D, "obligatorio": True, "opciones": None},
    {"etiqueta": "Teléfono", "tipo": T, "obligatorio": True, "opciones": None},
    {"etiqueta": "¿Participaría de la capacitación?", "tipo": SN, "obligatorio": True, "opciones": None},
]
CAMPOS_F2 = [
    {"etiqueta": "Nombre y apellido", "tipo": N, "obligatorio": True, "opciones": None},
    {"etiqueta": "Email", "tipo": "email", "obligatorio": True, "opciones": None},
    {"etiqueta": "Turno preferido", "tipo": "opcion", "obligatorio": True, "opciones": ["Mañana", "Tarde"]},
]
NOMBRES = {"Inscripción a la capacitación": "f1", "Interés en el programa de primer empleo": "f2"}


def preparar(c):
    for tabla in ("formulario_respuestas", "formulario_campos", "formularios"):
        c.execute(f"DELETE FROM {tabla}")
    trabajo = c.execute("SELECT id FROM organismos WHERE nombre = 'Subsecretaría de Trabajo'").fetchone()[0]

    def base(nombre, uso, aviso, **extra):
        datos = {"nombre": nombre, "descripcion_uso": uso, "aviso_finalidad": aviso, "tramite_id": None,
                 "estado": "activo", "fecha_cierre": None, "cupo": None}
        datos.update(extra)
        return datos

    formularios.crear_formulario(c, trabajo, base(
        "Inscripción a la capacitación",
        "Cuando la persona quiere inscribirse o anotarse a la capacitación de la Subsecretaría de Trabajo",
        "La Subsecretaría de Trabajo usa tus datos solamente para inscribirte a la capacitación y avisarte las fechas.",
        cupo=50), CAMPOS_F1, "evaluacion@local")
    formularios.crear_formulario(c, trabajo, base(
        "Interés en el programa de primer empleo",
        "Cuando la persona quiere dejar sus datos para el programa de primer empleo",
        "La Subsecretaría de Trabajo usa tus datos para contactarte por el programa de primer empleo.",
        tramite_id="TR-0019"), CAMPOS_F2, "evaluacion@local")
    formularios.crear_formulario(c, trabajo, base(
        "Inscripción vencida", "Curso con la inscripción vencida", "No se usa.",
        fecha_cierre=datetime.now(timezone.utc) - timedelta(days=2)), CAMPOS_F1, "evaluacion@local")
    formularios.crear_formulario(c, trabajo, base(
        "Inscripción cerrada", "Curso con la inscripción cerrada", "No se usa.", estado="cerrado"), CAMPOS_F1, "evaluacion@local")
    c.commit()


CASOS = [
    ("01 pedido directo, flujo completo", {"f1": 1}, [
        "Quiero anotarme a la capacitación",
        "Sí, quiero seguir. Me llamo Lucía Fernández, mi DNI es 30.456.789, mi teléfono es 387 4001122 y sí participaría.",
        "Sí, es correcto."]),
    ("02 consulta ambigua, no corresponde guardar", {}, [
        "Quiero información sobre capacitaciones para trabajadores"]),
    ("03 cancela a mitad", {}, [
        "Quiero inscribirme a la capacitación",
        "Sí, seguí. Me llamo Pedro Gómez",
        "Mejor no, cancelá todo por favor."]),
    ("04 DNI inválido y se corrige", {"f1": 1}, [
        "Quiero anotarme a la capacitación",
        "Sí. Soy Raúl Sosa, mi DNI es 123, mi teléfono 387 4555666 y sí participo.",
        "Perdón, mi DNI es 25.888.777",
        "Sí, es correcto."]),
    ("05 DNI duplicado (el del caso 01)", {}, [
        "Quiero anotarme a la capacitación",
        "Sí. Soy Lucía F., mi DNI es 30.456.789, mi teléfono 387 4001122 y sí participo.",
        "Sí, es correcto."]),
    ("06 formularios vencido y cerrado no se ofrecen", {}, [
        "Quiero inscribirme al curso con la inscripción vencida"]),
    ("07 corrige un dato al confirmar", {"f1": 1}, [
        "Quiero anotarme a la capacitación",
        "Sí. Soy Ana Díaz, DNI 28.111.222, teléfono 387 4111111 y sí participo.",
        "No, el teléfono es 387 4222222",
        "Sí, ahora está bien."]),
    ("08 formulario vinculado a un trámite", {"f2": 1}, [
        "¿Cómo accedo al programa de Primera Oportunidad Laboral?",
        "Quiero dejar mis datos de interés",
        "Sí, quiero seguir. Soy Leo Paz, mi email es leo@correo.com y prefiero el turno mañana.",
        "Sí, es correcto."]),
    ("09 dos formularios en la misma sesión", {"f1": 1, "f2": 1}, [
        "Quiero anotarme a la capacitación",
        "Sí. Soy Marta Ruiz, DNI 27.999.888, teléfono 387 4333444 y sí participo.",
        "Sí, es correcto.",
        "Ahora quiero dejar mis datos para el programa de primer empleo",
        "Sí. Mi email es marta@correo.com y prefiero el turno tarde.",
        "Sí, es correcto."]),
    ("10 control: consulta de un trámite, no ofrece formulario", {}, [
        "Perdí el DNI, ¿qué tengo que hacer?"]),
]


def herramientas(c, sid):
    nombres = []
    for (llamadas,) in c.execute(
        "SELECT tool_calls FROM mensajes WHERE session_id = %s AND rol = 'assistant' AND tool_calls IS NOT NULL ORDER BY orden", (sid,)
    ):
        nombres += [t["function"]["name"] for t in llamadas]
    return nombres


def correr(chat, oc, titulo, esperado, mensajes):
    sid = str(uuid.uuid4())
    with psycopg.connect(DESTINO) as c:
        register_vector(c)
        turnos = []
        for pregunta in mensajes:
            texto, error = "", None
            for intento in range(4):
                texto, error = "", None
                try:
                    for ev in procesar_turno(c, chat, oc.generate_embeddings, oc.rerank, sid, pregunta):
                        if ev["tipo"] == "texto":
                            texto += ev["delta"]
                    c.commit()
                    break
                except Exception as e:  # noqa: BLE001
                    c.rollback()
                    error = f"{type(e).__name__}: {e}"[:160]
                    if "429" in str(e) or "RateLimit" in type(e).__name__:
                        time.sleep(15 * (intento + 1))
                        continue
                    break
            turnos.append((pregunta, texto, error))
        guardadas = {}
        for nombre, n in c.execute(
            """SELECT f.nombre, count(*) FROM formulario_respuestas r JOIN formularios f ON f.id = r.formulario_id
               WHERE r.session_id = %s AND r.eliminada_en IS NULL GROUP BY 1""", (sid,)):
            guardadas[NOMBRES[nombre]] = n
        datos = [r[0] for r in c.execute("SELECT valores FROM formulario_respuestas WHERE session_id = %s", (sid,))]
        usadas = herramientas(c, sid)
        ofrecidos = [
            r[0] for r in c.execute(
                "SELECT contenido FROM mensajes WHERE session_id = %s AND rol = 'tool' AND contenido LIKE '%%aviso_finalidad%%'", (sid,))
        ]
    ok = guardadas == esperado
    print(f"\n{'OK  ' if ok else 'MAL '} {titulo} | esperado {esperado} | guardadas {guardadas} | herramientas {usadas}")
    print("     datos guardados:", datos)
    if any(("vencida" in o or "cerrada" in o) for o in ofrecidos):
        print("     MAL: se ofreció un formulario vencido o cerrado")
        ok = False
    for pregunta, texto, error in turnos:
        print(f"     > {pregunta[:90]}\n       {(texto or '(sin texto)').replace(chr(10), ' ')[:300]}" + (f"\n       ERROR {error}" if error else ""))
    return ok


if __name__ == "__main__":
    chat, oc = build_real_chat_client(), build_real_client()
    with psycopg.connect(DESTINO) as c:
        preparar(c)
    resultados = [correr(chat, oc, titulo, esperado, mensajes) for titulo, esperado, mensajes in CASOS]
    print(f"\n== {sum(resultados)}/{len(resultados)} conversaciones como se esperaba | avisos por mail simulados: {len(AVISOS)}")
```

Run (desde `backend/`): `PYTHONPATH=. timeout 580 .venv/bin/python "$SCRATCH/formularios_chat.py" 2>&1 | tee "$SCRATCH/formularios_chat.log" | tail -80`
Expected: la salida lista las 10 conversaciones con `OK`/`MAL`, los datos guardados y las respuestas del asistente. (Si el comando excede el tiempo, correrlo en segundo plano y leer el log.)

- [ ] **Step 4: Leer el resultado y decidir**

Leer la salida completa (no solo el resumen) y clasificar cada `MAL`:

- **Crítico (corregir):** se guardó una respuesta **sin que la persona confirmara**; se guardaron **datos distintos** de los que dio (DNI o teléfono equivocados); el asistente dijo que quedó registrado y **no se guardó** (o al revés); se ofreció un formulario cerrado o vencido; se guardó algo en el caso de cancelación.
- **Menor (registrar):** el asistente repregunta de más, no ofrece el formulario a la primera, redacta raro, o el control 10 menciona el formulario sin guardar nada.

Si hay algún defecto crítico: escribir primero un test que lo reproduzca (en `test_orchestrator.py` con el cliente falso si es de lógica del servidor, o en `test_system_prompt.py` si es una regla del prompt), verlo fallar, corregir y repetir el Step 3 **una sola vez** para confirmar. Registrar en el ledger `Ruling:` con lo que se cambió y por qué. Si después de esa pasada siguen apareciendo defectos críticos, **no seguir intentando**: dejarlos asentados con el detalle y avisar a la persona (es el límite de lo que se resuelve solo con el prompt).

Los defectos menores se anotan en el ledger como `minor (deferred)` y se informan al final.

- [ ] **Step 5: Limpiar y revisar el estado de la rama**

Limpiar la base de evaluación (los formularios de la prueba no deben quedar):

```bash
psql postgresql://macacha:macacha@localhost:5432/macacha_chat_eval -c "DELETE FROM formulario_respuestas; DELETE FROM formulario_campos; DELETE FROM formularios;" 2>&1 | tail -1
```

Run: `git status --short && git log --oneline -10 | cat`
Expected: solo `frontend/package.json`, `frontend/package-lock.json` y `.claude/` sin commitear; los commits de las Tasks 1 a 7 presentes. No hacer push.

- [ ] **Step 6: Commit**

```bash
git add docs/deploy-dokploy.md
git commit -m "docs: despliegue de los formularios por organismo"
```

---
