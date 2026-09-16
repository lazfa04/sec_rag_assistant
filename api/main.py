from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from retrieval.answerer import answer_question
from storage.vector_store import _connect

app = FastAPI(title="SEC Filing RAG Assistant")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    question: str = Field(min_length=1)
    ticker: str | None = None


class AskResponse(BaseModel):
    answer: str
    sources: list


@app.post("/ask", response_model=AskResponse)
def ask(body: AskRequest) -> dict:
    ticker = body.ticker.strip().upper() if body.ticker else None
    return answer_question(body.question, ticker=ticker)


@app.get("/companies")
def companies() -> list[str]:
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT ticker
                FROM filing_chunks
                WHERE ticker IS NOT NULL
                ORDER BY ticker
                """
            )
            return [row[0] for row in cur.fetchall()]
    finally:
        conn.close()
