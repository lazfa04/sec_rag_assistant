from ingestion.edgar_client import (
    get_cik,
    get_filing_document,
    get_filing_list,
)
from processing.chunker import chunk_by_section, split_long_chunks
from processing.cleaner import clean_filing_html
from processing.embedder import embed_chunks
from storage.vector_store import insert_chunks


def ingest_company(ticker: str) -> int:
    """Run the full ingest pipeline for one ticker's most recent 10-K/10-Q."""
    ticker = ticker.strip().upper()
    cik = get_cik(ticker)
    if cik is None:
        print(f"Warning: unknown ticker {ticker}, skipping")
        return 0

    print(f"Resolved {ticker} -> CIK {cik}")
    filings = get_filing_list(cik)
    print(f"Fetched {len(filings)} filings for {ticker}")
    if not filings:
        print(f"Warning: no 10-K/10-Q filings for {ticker}, skipping")
        return 0

    filing = max(filings, key=lambda row: row["filingDate"])
    print(
        f"Downloading most recent {filing['form']} "
        f"({filing['filingDate']}) for {ticker}"
    )
    raw_html = get_filing_document(cik, filing)

    clean_text = clean_filing_html(raw_html)
    print(f"Cleaned filing text for {ticker} ({len(clean_text)} chars)")

    sections = chunk_by_section(clean_text)
    print(f"Split into {len(sections)} sections for {ticker}")

    chunks = split_long_chunks(sections, ticker, filing["filingDate"])
    print(f"Prepared {len(chunks)} chunks for {ticker}")

    embedded = embed_chunks(chunks)
    insert_chunks(embedded)
    print(f"Inserted {len(embedded)} chunks for {ticker}")
    return len(embedded)
