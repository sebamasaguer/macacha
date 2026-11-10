MAX_DOCUMENTOS_POR_ORGANISMO = 3


class TopeDeDocumentos(Exception):
    """El organismo ya tiene el máximo de documentos."""


_SELECT = """
    SELECT d.id::text, d.organismo_id, o.nombre, d.titulo, d.nombre_archivo, d.subido_por_email,
           d.creado_en, d.actualizado_en,
           (SELECT COUNT(*) FROM organismo_documento_chunks c WHERE c.documento_id = d.id)
    FROM organismo_documentos d
    JOIN organismos o ON o.id = d.organismo_id
"""


def _fila_a_documento(fila) -> dict:
    return {
        "id": fila[0],
        "organismo_id": fila[1],
        "organismo": fila[2],
        "titulo": fila[3],
        "nombre_archivo": fila[4],
        "subido_por_email": fila[5],
        "creado_en": fila[6],
        "actualizado_en": fila[7],
        "fragmentos": fila[8],
    }


def listar_documentos(conn, organismo_id: int | None) -> list[dict]:
    with conn.cursor() as cur:
        if organismo_id is None:
            cur.execute(_SELECT + " ORDER BY o.nombre, d.creado_en")
        else:
            cur.execute(_SELECT + " WHERE d.organismo_id = %s ORDER BY d.creado_en", (organismo_id,))
        return [_fila_a_documento(fila) for fila in cur.fetchall()]


def obtener_documento(conn, documento_id: str) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(_SELECT + " WHERE d.id = %s", (documento_id,))
        fila = cur.fetchone()
    return _fila_a_documento(fila) if fila else None


def _insertar_fragmentos(cur, documento_id: str, fragmentos: list[str], embeddings: list[list[float]]) -> None:
    if len(fragmentos) != len(embeddings):
        raise ValueError("Cada fragmento necesita su embedding")
    for orden, (texto, embedding) in enumerate(zip(fragmentos, embeddings)):
        cur.execute(
            "INSERT INTO organismo_documento_chunks (documento_id, orden, texto, embedding) VALUES (%s, %s, %s, %s)",
            (documento_id, orden, texto, embedding),
        )


def crear_documento(
    conn,
    organismo_id: int,
    titulo: str,
    nombre_archivo: str,
    subido_por_email: str,
    fragmentos: list[str],
    embeddings: list[list[float]],
) -> dict:
    with conn.cursor() as cur:
        # Bloquea la fila del organismo: dos altas simultáneas se ordenan y la segunda ve el conteo real.
        cur.execute("SELECT id FROM organismos WHERE id = %s FOR UPDATE", (organismo_id,))
        cur.execute("SELECT COUNT(*) FROM organismo_documentos WHERE organismo_id = %s", (organismo_id,))
        if cur.fetchone()[0] >= MAX_DOCUMENTOS_POR_ORGANISMO:
            raise TopeDeDocumentos()
        cur.execute(
            """
            INSERT INTO organismo_documentos (organismo_id, titulo, nombre_archivo, subido_por_email)
            VALUES (%s, %s, %s, %s) RETURNING id::text
            """,
            (organismo_id, titulo, nombre_archivo, subido_por_email),
        )
        documento_id = cur.fetchone()[0]
        _insertar_fragmentos(cur, documento_id, fragmentos, embeddings)
    return obtener_documento(conn, documento_id)


def reemplazar_contenido(
    conn,
    documento_id: str,
    nombre_archivo: str,
    subido_por_email: str,
    fragmentos: list[str],
    embeddings: list[list[float]],
    titulo: str | None = None,
) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE organismo_documentos
            SET nombre_archivo = %s, subido_por_email = %s, titulo = COALESCE(%s, titulo), actualizado_en = now()
            WHERE id = %s
            """,
            (nombre_archivo, subido_por_email, titulo, documento_id),
        )
        if cur.rowcount == 0:
            return None
        cur.execute("DELETE FROM organismo_documento_chunks WHERE documento_id = %s", (documento_id,))
        _insertar_fragmentos(cur, documento_id, fragmentos, embeddings)
    return obtener_documento(conn, documento_id)


def renombrar_documento(conn, documento_id: str, titulo: str) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE organismo_documentos SET titulo = %s, actualizado_en = now() WHERE id = %s",
            (titulo, documento_id),
        )
        if cur.rowcount == 0:
            return None
    return obtener_documento(conn, documento_id)


def borrar_documento(conn, documento_id: str) -> bool:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM organismo_documentos WHERE id = %s", (documento_id,))
        return cur.rowcount > 0
