def test_extension_and_tables_exist(db_conn):
    with db_conn.cursor() as cur:
        cur.execute("SELECT extname FROM pg_extension WHERE extname = 'vector'")
        assert cur.fetchone() is not None

        cur.execute(
            """
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
            """
        )
        tables = {row[0] for row in cur.fetchall()}
        assert {
            "organismos",
            "tramites",
            "tramite_versiones",
            "tramite_chunks",
            "sesiones",
            "mensajes",
            "admins",
            "solicitudes_contacto",
            "formularios",
            "formulario_campos",
            "formulario_respuestas",
            "feedback_respuestas",
        } <= tables


def test_admins_tiene_columnas_de_rol_y_organismo(db_conn):
    with db_conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'admins'
            """
        )
        columnas = {row[0] for row in cur.fetchall()}
        assert {"rol", "organismo_id", "activo"} <= columnas


def test_organismos_tiene_columna_email_contacto(db_conn):
    with db_conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'organismos' AND column_name = 'email_contacto'
            """
        )
        assert cur.fetchone() is not None


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
