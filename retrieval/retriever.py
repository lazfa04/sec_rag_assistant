import psycopg2
from pgvector.psycopg2 import register_vector
from psycopg2.extras import RealDictCursor

from processing.embedder import _model
from storage.vector_store import _dsn


def retrieve(query: str, top_k: int = 5) -> list[dict]:
    """Return the top_k filing chunks closest to the query in cosine space."""
    vector = _model().encode([query], convert_to_numpy=True)[0]
    conn = psycopg2.connect(_dsn())
    register_vector(conn)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    ticker,
                    filing_date,
                    item_number,
                    item_title,
                    text,
                    1 - (embedding <=> %s) AS similarity
                FROM filing_chunks
                ORDER BY embedding <=> %s
                LIMIT %s
                """,
                (vector, vector, top_k),
            )
            return [
                {
                    "ticker": row["ticker"],
                    "filing_date": row["filing_date"],
                    "item_number": row["item_number"],
                    "item_title": row["item_title"],
                    "text": row["text"],
                    "similarity": float(row["similarity"]),
                }
                for row in cur.fetchall()
            ]
    finally:
        conn.close()
