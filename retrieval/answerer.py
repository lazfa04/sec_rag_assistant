import os
import re

from anthropic import Anthropic
from dotenv import load_dotenv

from retrieval.retriever import retrieve

load_dotenv()

MODEL = "claude-sonnet-4-5"
INSUFFICIENT = "I don't have enough information in the retrieved filings"
KNOWN_TICKERS = ["AAPL", "NVDA", "TSLA", "MSFT"]
COMPANY_NAMES = {
    "apple": "AAPL",
    "microsoft": "MSFT",
    "nvidia": "NVDA",
    "tesla": "TSLA",
}

SYSTEM_PROMPT = """You are answering questions about SEC filings using only the numbered context excerpts provided in the user message.

Citation rules:
- Treat the excerpts as the sole source of truth. Do not use outside knowledge, prior training, or speculation.
- After every factual claim, add inline citations like [1] or [1][3].
- A citation is valid ONLY if that numbered excerpt explicitly contains the SPECIFIC fact you just stated (the same number, rate, date, entity, or assertion). Being from the correct company, the correct Item (e.g. MD&A), or a loosely related topic is not enough.
- Example of an invalid citation: stating Apple's tax rate and citing an AAPL chunk that discusses SG&A expenses but never mentions the tax rate.
- Before writing a claim, verify you can quote or closely paraphrase the supporting sentence from the cited excerpt. If you cannot, do not make the claim and do not cite that excerpt for it.
- If no retrieved excerpt actually contains the specific fact needed to answer the question, reply with exactly this sentence and nothing else:
  I don't have enough information in the retrieved filings

Company-matching rules:
- Each excerpt is labeled with the company ticker at the start of the block, e.g. "[1] AAPL - Item 1A Risk Factors:".
- If the question names a specific company, or a ticker filter is provided, you may use ONLY excerpts whose ticker matches that company.
- Do not use facts from a different company's filing even if the excerpt is topically similar (same Item, similar risk language, similar numbers).
- Ignore mismatched excerpts entirely. If, after ignoring them, nothing remains that answers the question about the requested company, reply with exactly this sentence and nothing else:
  I don't have enough information in the retrieved filings
- You may mention that retrieved context included an unrelated company's filing if that is why you cannot answer.
"""


def _context_blocks(chunks: list[dict]) -> str:
    blocks = []
    for i, chunk in enumerate(chunks, start=1):
        item = chunk.get("item_number", "")
        title = chunk.get("item_title", "")
        ticker = chunk.get("ticker", "") or "UNKNOWN"
        header = f"[{i}] {ticker} - Item {item} {title}"
        blocks.append(f"{header}: {chunk.get('text', '')}")
    return "\n\n".join(blocks)


def _user_prompt(query: str, chunks: list[dict], ticker: str | None = None) -> str:
    filter_line = (
        f"Ticker filter: {ticker.strip().upper()} (use only excerpts labeled with this ticker)\n\n"
        if ticker
        else ""
    )
    return (
        f"{filter_line}"
        f"Question:\n{query}\n\n"
        "Context excerpts (answer only from these; each block starts with its company ticker):\n"
        f"{_context_blocks(chunks)}\n\n"
        "Write the answer with inline [n] citations. "
        "Cite a source only when that excerpt contains the specific fact you stated, "
        "not merely because it is the same company or a related topic. "
        "Use only excerpts from the company being asked about. "
        "If no excerpt contains the specific fact needed, use the exact fallback sentence from your instructions."
    )


def detect_ticker(query: str, known_tickers: list[str]) -> str | None:
    """Return a ticker if the query names a known ticker or company, else None."""
    known = {ticker.upper() for ticker in known_tickers}
    matches: list[tuple[int, str]] = []

    for name, ticker in COMPANY_NAMES.items():
        if ticker not in known:
            continue
        match = re.search(rf"\b{re.escape(name)}\b", query, re.IGNORECASE)
        if match:
            matches.append((match.start(), ticker))

    for ticker in known:
        match = re.search(rf"\b{re.escape(ticker)}\b", query, re.IGNORECASE)
        if match:
            matches.append((match.start(), ticker))

    if not matches:
        return None
    matches.sort(key=lambda item: item[0])
    return matches[0][1]


def answer_question(
    query: str, top_k: int = 5, ticker: str | None = None
) -> dict:
    """Retrieve filing chunks and ask Claude to answer with numbered citations."""
    resolved = ticker.strip().upper() if ticker else detect_ticker(query, KNOWN_TICKERS)
    sources = retrieve(query, top_k, resolved)
    if not sources:
        return {"answer": INSUFFICIENT, "sources": []}

    client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    message = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": _user_prompt(query, sources, resolved)}],
    )
    answer = "".join(
        block.text for block in message.content if getattr(block, "type", None) == "text"
    )
    return {"answer": answer, "sources": sources}
