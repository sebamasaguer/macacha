from retrieval.fusion import fusionar_rrf

# Calibrado con embeddings reales (2026-11-10): consultas relevantes 0.53-0.77, ajenas 0.20-0.36.
UMBRAL_SIMILITUD = 0.45
# La rama textual también exige algo de cercanía semántica: una palabra común ("DNI", "trámite") no alcanza.
UMBRAL_SIMILITUD_TEXTUAL = 0.30

_COLUMNAS = """
    c.id, d.id, d.titulo, o.nombre, c.texto
    FROM organismo_documento_chunks c
    JOIN organismo_documentos d ON d.id = c.documento_id
    JOIN organismos o ON o.id = d.organismo_id
"""


def _chunk(fila) -> dict:
    return {
        "chunk_id": str(fila[0]),
        "documento_id": str(fila[1]),
        "titulo": fila[2],
        "organismo": fila[3],
        "texto": fila[4],
    }


def _por_similitud(conn, query_embedding: list[float], top_n: int) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT {_COLUMNAS}
            WHERE 1 - (c.embedding <=> %s::vector) >= %s
            ORDER BY c.embedding <=> %s::vector
            LIMIT %s
            """,
            (query_embedding, UMBRAL_SIMILITUD, query_embedding, top_n),
        )
        return [_chunk(fila) for fila in cur.fetchall()]


def _por_texto(conn, query: str, query_embedding: list[float], top_n: int) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT {_COLUMNAS}
            WHERE c.tsv @@ websearch_to_tsquery('spanish', %s)
              AND 1 - (c.embedding <=> %s::vector) >= %s
            ORDER BY ts_rank(c.tsv, websearch_to_tsquery('spanish', %s)) DESC
            LIMIT %s
            """,
            (query, query_embedding, UMBRAL_SIMILITUD_TEXTUAL, query, top_n),
        )
        return [_chunk(fila) for fila in cur.fetchall()]


def buscar_documentos_chunks(conn, embed_fn, query: str, top_k: int = 5) -> list[dict]:
    query_embedding = embed_fn([query])[0]
    vectorial = _por_similitud(conn, query_embedding, top_n=20)
    textual = _por_texto(conn, query, query_embedding, top_n=20)
    return fusionar_rrf(vectorial, textual)[:top_k]
