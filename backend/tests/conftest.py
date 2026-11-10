import os

import psycopg
import pytest
from pgvector.psycopg import register_vector


def _test_database_url() -> str:
    return os.environ.get(
        "TEST_DATABASE_URL",
        "postgresql://macacha:macacha@localhost:5432/macacha_test",
    )


@pytest.fixture
def db_conn():
    conn = psycopg.connect(_test_database_url())
    register_vector(conn)
    yield conn
    conn.rollback()
    conn.close()


@pytest.fixture
def clean_db(db_conn):
    conn = psycopg.connect(_test_database_url(), autocommit=True)

    def _clean() -> None:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM feedback_respuestas")
            cur.execute("DELETE FROM mensajes")
            cur.execute("DELETE FROM solicitudes_contacto")
            cur.execute("DELETE FROM formulario_respuestas")
            cur.execute("DELETE FROM formulario_campos")
            cur.execute("DELETE FROM formularios")
            cur.execute("DELETE FROM sesiones")
            cur.execute("DELETE FROM tramite_chunks")
            cur.execute("DELETE FROM tramite_versiones")
            cur.execute("DELETE FROM organismo_documento_chunks")
            cur.execute("DELETE FROM organismo_documentos")
            cur.execute("DELETE FROM admins")
            cur.execute("DELETE FROM tramites")
            cur.execute("DELETE FROM organismos")

    _clean()
    yield
    # db_conn puede dejar abierta una transacción con locks (p. ej. el FOR UPDATE de un formulario) y el DELETE esperaría.
    db_conn.rollback()
    _clean()
    conn.close()
