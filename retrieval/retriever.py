import psycopg2
from pgvector.psycopg2 import register_vector
from psycopg2.extras import RealDictCursor

from processing.embedder import _model
from storage.vector_store import _dsn


def retrieve(
    query: str, top_k: int = 5, ticker: str | list[str] | None = None
) -> list[dict]:
    """Return the top_k filing chunks closest to the query in cosine space."""
    vector = _model().encode([query], convert_to_numpy=True)[0]
    conn = psycopg2.connect(_dsn())
    register_vector(conn)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            sql = """
                SELECT
                    ticker,
                    filing_date,
                    item_number,
                    item_title,
                    text,
                    1 - (embedding <=> %s) AS similarity
                FROM filing_chunks
            """
            params: list = [vector]
            if isinstance(ticker, list):
                tickers = [
                    t.strip().upper()
                    for t in ticker
                    if isinstance(t, str) and t.strip()
                ]
                if tickers:
                    sql += " WHERE ticker = ANY(%s)"
                    params.append(tickers)
            elif ticker:
                sql += " WHERE ticker = %s"
                params.append(ticker.strip().upper())
            sql += """
                ORDER BY embedding <=> %s
                LIMIT %s
            """
            params.extend([vector, top_k])
            cur.execute(sql, params)
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
