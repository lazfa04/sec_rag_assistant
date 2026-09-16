import os
from urllib.parse import quote, urlparse, urlunparse

import psycopg2
from dotenv import load_dotenv
from pgvector.psycopg2 import register_vector
from psycopg2.extras import execute_values

load_dotenv()


def _dsn() -> str:
    raw = os.environ["DATABASE_URL"]
    parsed = urlparse(raw)
    user = quote(parsed.username or "", safe="")
    password = quote(parsed.password or "", safe="")
    host = parsed.hostname or "localhost"
    netloc = f"{user}:{password}@{host}"
    if parsed.port:
        netloc += f":{parsed.port}"
    return urlunparse(
        (parsed.scheme, netloc, parsed.path, parsed.params, parsed.query, parsed.fragment)
    )


def _connect():
    conn = psycopg2.connect(_dsn())
    register_vector(conn)
    return conn


def create_table() -> None:
    """Create the pgvector extension and filing_chunks table if needed."""
    conn = psycopg2.connect(_dsn())
    try:
        with conn, conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS filing_chunks (
                    id SERIAL PRIMARY KEY,
                    ticker TEXT,
                    filing_date TEXT,
                    item_number TEXT,
                    item_title TEXT,
                    text TEXT,
                    embedding VECTOR(384)
                )
                """
            )
    finally:
        conn.close()


def insert_chunks(chunks: list[dict]) -> None:
    """Insert embedded chunk dicts into filing_chunks."""
    if not chunks:
        return

    rows = [
        (
            chunk["ticker"],
            chunk["filing_date"],
            chunk["item_number"],
            chunk["item_title"],
            chunk["text"],
            chunk["embedding"],
        )
        for chunk in chunks
    ]
    conn = _connect()
    try:
        with conn, conn.cursor() as cur:
            execute_values(
                cur,
                """
                INSERT INTO filing_chunks
                    (ticker, filing_date, item_number, item_title, text, embedding)
                VALUES %s
                """,
                rows,
            )
    finally:
        conn.close()
