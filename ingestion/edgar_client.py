import json
import os
from functools import lru_cache
from urllib.error import URLError
from urllib.request import Request, urlopen

COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
ARCHIVE_URL = (
    "https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{document}"
)
DEFAULT_USER_AGENT = "sec-rag-assistant contact@example.com"


def _user_agent() -> str:
    return os.getenv("SEC_USER_AGENT", DEFAULT_USER_AGENT)


def _fetch_bytes(url: str, timeout: int = 30) -> bytes:
    request = Request(url, headers={"User-Agent": _user_agent()})
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.read()
    except URLError as exc:
        raise RuntimeError(f"Failed to fetch {url}: {exc}") from exc


def _fetch_json(url: str) -> dict:
    return json.loads(_fetch_bytes(url))


@lru_cache(maxsize=1)
def _ticker_to_cik() -> dict[str, str]:
    """Fetch company_tickers.json once and invert it into ticker -> 10-digit CIK."""
    payload = _fetch_json(COMPANY_TICKERS_URL)

    mapping: dict[str, str] = {}
    for entry in payload.values():
        ticker = str(entry["ticker"]).strip().upper()
        mapping[ticker] = str(entry["cik_str"]).zfill(10)
    return mapping


def get_cik(ticker: str) -> str | None:
    """Return the 10-digit CIK for a ticker, or None if the ticker is unknown."""
    key = ticker.strip().upper()
    return _ticker_to_cik().get(key)


def get_filing_list(
    cik: str, form_types: set[str] = {"10-K", "10-Q"}
) -> list[dict]:
    """Return recent filings for a CIK, filtered to the requested form types."""
    cik = str(cik).strip().zfill(10)
    payload = _fetch_json(SUBMISSIONS_URL.format(cik=cik))
    recent = payload.get("filings", {}).get("recent", {})

    rows = zip(
        recent.get("form", []),
        recent.get("filingDate", []),
        recent.get("reportDate", []),
        recent.get("accessionNumber", []),
        recent.get("primaryDocument", []),
    )
    return [
        {
            "form": form,
            "filingDate": filing_date,
            "reportDate": report_date,
            "accessionNumber": accession,
            "primaryDocument": primary_document,
        }
        for form, filing_date, report_date, accession, primary_document in rows
        if form in form_types
    ]


def get_filing_document(cik: str, filing: dict) -> str:
    """Return the raw HTML of a filing's primary document from the EDGAR archive."""
    cik_path = str(int(str(cik).strip()))
    accession = str(filing["accessionNumber"]).replace("-", "")
    document = filing["primaryDocument"]
    url = ARCHIVE_URL.format(cik=cik_path, accession=accession, document=document)
    return _fetch_bytes(url, timeout=60).decode("utf-8", errors="replace")
