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


def test_existen_tablas_de_documentos_por_organismo(db_conn):
    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
        )
        tablas = {row[0] for row in cur.fetchall()}
    assert {"organismo_documentos", "organismo_documento_chunks"} <= tablas


def test_borrar_documento_borra_sus_chunks(db_conn, clean_db):
    with db_conn.cursor() as cur:
        cur.execute("INSERT INTO organismos (nombre) VALUES ('Org doc') RETURNING id")
        organismo_id = cur.fetchone()[0]
        cur.execute(
            """
            INSERT INTO organismo_documentos (organismo_id, titulo, nombre_archivo, subido_por_email)
            VALUES (%s, 'Reglamento', 'reglamento.pdf', 'a@b.c') RETURNING id
            """,
            (organismo_id,),
        )
        documento_id = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO organismo_documento_chunks (documento_id, orden, texto) VALUES (%s, 0, 'hola')",
            (documento_id,),
        )
        cur.execute("DELETE FROM organismo_documentos WHERE id = %s", (documento_id,))
        cur.execute(
            "SELECT count(*) FROM organismo_documento_chunks WHERE documento_id = %s", (documento_id,)
        )
        assert cur.fetchone()[0] == 0
