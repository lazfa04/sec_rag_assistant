import psycopg2
from pgvector.psycopg2 import register_vector
from psycopg2.extras import RealDictCursor

from processing.embedder import _model
from storage.vector_store import _dsn

SEARCH_SQL = """
    SELECT
        ticker,
        filing_date,
        item_number,
        item_title,
        text,
        1 - (embedding <=> %s) AS similarity
    FROM filing_chunks
"""


def _ticker_list(ticker: str | list[str] | None) -> list[str]:
    """Normalize a ticker argument to an ordered, de-duplicated list of tickers."""
    if ticker is None:
        return []
    values = [ticker] if isinstance(ticker, str) else ticker
    ordered: list[str] = []
    for value in values:
        if not isinstance(value, str):
            continue
        code = value.strip().upper()
        if code and code not in ordered:
            ordered.append(code)
    return ordered


def _search(cur, vector, top_k: int, ticker: str | None) -> list[dict]:
    """Run one similarity search, optionally scoped to a single ticker."""
    sql = SEARCH_SQL
    params: list = [vector]
    if ticker:
        sql += " WHERE ticker = %s"
        params.append(ticker)
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


def retrieve(
    query: str, top_k: int = 5, ticker: str | list[str] | None = None
) -> list[dict]:
    """Return filing chunks closest to the query in cosine space.

    A single ticker (or None) runs one search for the top_k closest chunks.
    Several tickers run one search per company, each getting a full top_k, so
    every named company is represented regardless of how it ranks against the
    others. Results stay grouped by company in the order the tickers were given.
    """
    tickers = _ticker_list(ticker)
    vector = _model().encode([query], convert_to_numpy=True)[0]
    conn = psycopg2.connect(_dsn())
    register_vector(conn)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if len(tickers) > 1:
                chunks: list[dict] = []
                for code in tickers:
                    chunks.extend(_search(cur, vector, top_k, code))
                return chunks
            return _search(cur, vector, top_k, tickers[0] if tickers else None)
    finally:
        conn.close()
