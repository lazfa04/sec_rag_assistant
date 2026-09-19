# SEC Filing RAG Assistant

A retrieval-augmented generation (RAG) system that answers natural-language questions about public companies' SEC filings (10-K/10-Q), grounded in the actual filing text with source citations — not model guesses.

Built to explore production RAG engineering: multi-source ingestion, section-aware chunking, vector retrieval, grounded answer generation, and evaluation — rather than a thin wrapper around an LLM API.

## What it does

Ask a question like "What antitrust issues is Apple facing?" and the system:

1. Embeds the question
2. Retrieves the most relevant chunks from real SEC filings via vector similarity search
3. Generates an answer using Claude, strictly grounded in those retrieved chunks, with inline citations back to source sections
4. Refuses to answer when the retrieved context doesn't actually support a response, rather than hallucinating

Supports multiple companies (currently **AAPL**, **NVDA**, **TSLA**, **MSFT**), with optional per-company filtering.

## Architecture

```text
Ticker -> CIK lookup (EDGAR) -> Filing list -> Raw 10-K/10-Q document
-> Clean (strip iXBRL metadata) -> Section-aware chunking (by SEC Item)
-> Sub-chunking (paragraph-boundary, size-bounded) -> Embed (MiniLM)
-> Store (Postgres + pgvector) -> Retrieve (cosine similarity, optional
ticker filter) -> Generate grounded answer with citations (Claude)
```

Section-aware chunking was chosen over fixed-size chunking because SEC filings have a standard structure (**Item 1: Business**, **Item 1A: Risk Factors**, **Item 7: MD&A**, etc.). Splitting along those real section boundaries keeps each chunk's meaning intact and lets retrieval reason about which kind of disclosure a question needs, not just which words are similar.

## Tech stack

- **Ingestion:** SEC EDGAR public API (`data.sec.gov`, `www.sec.gov`)
- **Cleaning:** BeautifulSoup (`lxml-xml` parser, for iXBRL-tagged documents)
- **Embeddings:** sentence-transformers (`all-MiniLM-L6-v2`, 384-dim)
- **Vector store:** PostgreSQL + pgvector
- **Answer generation:** Anthropic Claude API
- **Language:** Python

## Setup

```bash
git clone <repo-url>
cd sec-rag-assistant
python -m venv venv
venv\Scripts\Activate.ps1   # Windows PowerShell
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```env
ANTHROPIC_API_KEY=your_key_here
DATABASE_URL=postgresql://postgres:password@localhost:5432/sec_rag
```

Postgres setup:

```sql
CREATE DATABASE sec_rag;
\c sec_rag
CREATE EXTENSION vector;
```

Ingest a company:

```python
from pipeline.ingest import ingest_company

ingest_company("AAPL")
```

Ask a question:

```python
from retrieval.answerer import answer_question

result = answer_question("What are Apple's main risk factors?", ticker="AAPL")
print(result["answer"])
```

## Evaluation

Ran an 18-question hand-written eval set against Apple's Q3 2026 10-Q, covering factual/numeric lookups, risk-factor reasoning, near-empty-section edge cases, and deliberately out-of-scope questions designed to test whether the system correctly refuses rather than hallucinates.

**Results: 15/18 correct** (up from 11/18 after a chunking fix, described below).

- 11/11 risk-factor and MD&A questions answered accurately with correct citations
- 3/3 out-of-scope questions (e.g. "What is Apple's projected revenue for fiscal year 2028?") correctly triggered a refusal instead of a hallucinated answer
- 2 failures: near-empty sections ("Defaults Upon Senior Securities" — just "None.") don't retrieve reliably, since a 1-2 word chunk produces a weak, non-distinctive embedding. This is a known limitation of dense embedding retrieval on sparse content, not a bug — a production system would likely need a keyword/hybrid fallback for very short sections.

### Bug found during eval: cover-page data was missing entirely

Initial chunking only started capturing text from the first Item header, silently dropping everything before it — including the filing's cover page (company name, state of incorporation, Commission File Number). Questions like "What state is Apple incorporated in?" were wrongly refused, not because retrieval ranked poorly, but because the answer was never in the corpus at all. Fixed by adding a dedicated cover-page chunk before the first section boundary. **Result: 11/18 -> 15/18.**

### Bug found during multi-company testing: HTML tag-boundary text corruption

Extending to Microsoft's 10-K, several section titles came back mangled (e.g. `"RIS"` instead of `"Risk Factors"`). Root cause: Microsoft's filing wraps section titles across multiple inline HTML tags, and the text-extraction step was concatenating them with a stray line break mid-word instead of reassembling them correctly. This was initially mistaken for a table-of-contents matching issue, but line-by-line inspection of the raw cleaned text revealed the real cause. Fixed by reassembling tag-split text before pattern-matching, plus adding a proper TOC-row filter (title immediately followed by a standalone page number, rather than real section prose). Verified across all 4 ingested companies afterward — Nvidia's apparently "missing" sections turned out to be a real, legitimate difference in what the company discloses, not a bug.

## Known limitations

- Sparse/near-empty filing sections don't retrieve reliably with dense embeddings alone (see eval results above)
- Only the most recent 10-K/10-Q per company is ingested; historical filings are not yet supported
- No deduplication guard on re-ingesting the same company — re-running `ingest_company` on an already-ingested ticker creates duplicate rows (manual cleanup required for now)
- Single-document retrieval only — no cross-filing comparison (e.g. "how did Apple's risk factors change quarter over quarter") yet
- Multi-company questions search across all named companies (via `detect_tickers`), but retrieval ranking is shared across a single pool, not quota'd per company. If one company's language ranks more semantically similar to the query, its chunks can dominate the retrieved set even when the other named company has relevant content that never gets retrieved. The system correctly reports this limitation rather than fabricating comparison content it doesn't have, but a hard per-company retrieval quota would be a more robust fix.

## Possible extensions

- Hybrid retrieval (keyword + vector) for sparse-content sections
- Historical filing ingestion for trend analysis across quarters
- Agent layer: a tool that can fetch and compare across multiple filings/companies for a single query
- Simple web UI (Streamlit) instead of REPL-only interaction

### Bug found in production UI testing: cross-entity fact attribution

Asking about Apple's tax rate with "All companies" selected returned a 
confident, cited answer — but the citation pointed to an NVIDIA chunk that 
mentioned the same generic 21% U.S. statutory rate in passing. Initial fix 
(explicit prompt instructions against cross-company citation) reduced but 
didn't eliminate the issue — the model would still cite a same-company chunk 
that didn't actually contain the claimed fact, just to satisfy the instruction. 
This revealed a broader lesson: prompt-level grounding rules are necessary but 
not sufficient, since an LLM can still rationalize a technically-compliant but 
substantively wrong citation. The reliable fix was moving enforcement to the 
retrieval layer — auto-detecting a company mention in the question and 
filtering retrieval to that company's chunks before the LLM ever sees mismatched 
data, rather than relying on the model to self-police after the fact.

### Bug found in production UI testing: multi-company question handling

Asking "Compare Apple's and Microsoft's risk factors" with "All companies" 
selected only ever detected and searched for Apple, because the original 
`detect_ticker()` returned just the first company mentioned in the query. 
The resulting refusal implied no Microsoft data existed, when Microsoft's 
filings were simply never searched. Diagnosis: retrieval was filtered to a 
single ticker before ranking, so the second named company never entered the 
candidate set. Fix: renamed to `detect_tickers()`, returning every company 
named in the query; updated `retrieve()` to accept a list of tickers via 
`WHERE ticker = ANY(%s)`; and scaled `top_k` by the number of detected 
companies (`top_k * n`) so each company has a better chance of appearing in 
the retrieved set rather than a fixed `top_k` being dominated by one company. 
After the fix, retrieval genuinely searches all named companies, and the 
system's behavior became honestly self-reporting rather than misleading — 
when Apple's chunks dominated the retrieved set in testing (9 of 10 sources), 
the model correctly said "I can only provide information about Apple's 
antitrust risks; the Microsoft excerpts provided do not contain any discussion 
of antitrust risk factors" instead of either hallucinating a Microsoft 
comparison or giving a misleading blanket refusal. Remaining limitation 
(see Known limitations): ranking is still shared across companies, not 
quota'd per company.
