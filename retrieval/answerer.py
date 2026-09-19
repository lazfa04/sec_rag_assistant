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
- If the question names a specific company, or a ticker filter is provided, you may use ONLY excerpts whose ticker matches that company (or those companies, if several are named).
- Do not use facts from a different company's filing even if the excerpt is topically similar (same Item, similar risk language, similar numbers).
- Ignore mismatched excerpts entirely. If, after ignoring them, nothing remains that answers the question about the requested company, reply with exactly this sentence and nothing else:
  I don't have enough information in the retrieved filings
- You may mention that retrieved context included an unrelated company's filing if that is why you cannot answer.
- When multiple companies are provided as context, you may compare and contrast across them. Attribute every claim to the correct company using that excerpt's ticker label. Do not mix one company's facts into another's.
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


def _normalized_tickers(ticker: str | list[str] | None) -> list[str]:
    if ticker is None:
        return []
    if isinstance(ticker, str):
        value = ticker.strip().upper()
        return [value] if value else []
    return [t.strip().upper() for t in ticker if isinstance(t, str) and t.strip()]


def _user_prompt(
    query: str, chunks: list[dict], ticker: str | list[str] | None = None
) -> str:
    tickers = _normalized_tickers(ticker)
    if len(tickers) == 1:
        filter_line = (
            f"Ticker filter: {tickers[0]} (use only excerpts labeled with this ticker)\n\n"
        )
    elif len(tickers) > 1:
        joined = ", ".join(tickers)
        filter_line = (
            f"Ticker filter: {joined} (use only excerpts labeled with these tickers; "
            "you may compare and contrast across them, attributing each claim "
            "to the correct ticker)\n\n"
        )
    else:
        filter_line = ""
    return (
        f"{filter_line}"
        f"Question:\n{query}\n\n"
        "Context excerpts (answer only from these; each block starts with its company ticker):\n"
        f"{_context_blocks(chunks)}\n\n"
        "Write the answer with inline [n] citations. "
        "Cite a source only when that excerpt contains the specific fact you stated, "
        "not merely because it is the same company or a related topic. "
        "Use only excerpts from the company or companies being asked about. "
        "When multiple companies appear in the context, compare and contrast using "
        "each excerpt's ticker label so claims stay attributed to the right company. "
        "If no excerpt contains the specific fact needed, use the exact fallback sentence from your instructions."
    )


def detect_tickers(query: str, known_tickers: list[str]) -> list[str]:
    """Return every known ticker named in the query, in order of appearance."""
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

    matches.sort(key=lambda item: item[0])
    seen: set[str] = set()
    ordered: list[str] = []
    for _, ticker in matches:
        if ticker not in seen:
            seen.add(ticker)
            ordered.append(ticker)
    return ordered


def answer_question(
    query: str, top_k: int = 5, ticker: str | None = None
) -> dict:
    """Retrieve filing chunks and ask Claude to answer with numbered citations."""
    if ticker:
        resolved: str | list[str] | None = ticker.strip().upper()
        k = top_k
    else:
        detected = detect_tickers(query, KNOWN_TICKERS)
        if len(detected) >= 2:
            resolved = detected
            k = top_k * len(detected)
        elif len(detected) == 1:
            resolved = detected[0]
            k = top_k
        else:
            resolved = None
            k = top_k
    sources = retrieve(query, k, resolved)
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
