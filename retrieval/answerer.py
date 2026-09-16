import os

from anthropic import Anthropic
from dotenv import load_dotenv

from retrieval.retriever import retrieve

load_dotenv()

MODEL = "claude-sonnet-4-5"
INSUFFICIENT = "I don't have enough information in the retrieved filings"

SYSTEM_PROMPT = """You are answering questions about SEC filings using only the numbered context excerpts provided in the user message.

Citation rules:
- Treat the excerpts as the sole source of truth. Do not use outside knowledge, prior training, or speculation.
- After every factual claim, add inline citations like [1] or [1][3] that point to the numbered excerpt(s) that support that claim.
- If a statement cannot be tied to at least one numbered excerpt, do not write it.
- If the excerpts do not contain enough information to answer the question, reply with exactly this sentence and nothing else:
  I don't have enough information in the retrieved filings
"""


def _context_blocks(chunks: list[dict]) -> str:
    blocks = []
    for i, chunk in enumerate(chunks, start=1):
        item = chunk.get("item_number", "")
        title = chunk.get("item_title", "")
        ticker = chunk.get("ticker", "")
        filing_date = chunk.get("filing_date", "")
        header = f"[{i}] Item {item} {title} ({ticker}, {filing_date})"
        blocks.append(f"{header}:\n{chunk.get('text', '')}")
    return "\n\n".join(blocks)


def _user_prompt(query: str, chunks: list[dict]) -> str:
    return (
        f"Question:\n{query}\n\n"
        "Context excerpts (answer only from these):\n"
        f"{_context_blocks(chunks)}\n\n"
        "Write the answer with inline [n] citations. "
        "If the context is insufficient, use the exact fallback sentence from your instructions."
    )


def answer_question(query: str, top_k: int = 5) -> dict:
    """Retrieve filing chunks and ask Claude to answer with numbered citations."""
    sources = retrieve(query, top_k)
    if not sources:
        return {"answer": INSUFFICIENT, "sources": []}

    client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    message = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": _user_prompt(query, sources)}],
    )
    answer = "".join(
        block.text for block in message.content if getattr(block, "type", None) == "text"
    )
    return {"answer": answer, "sources": sources}
