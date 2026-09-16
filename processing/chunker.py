import re

# Same-line title only. \s would also match a newline, which joins TOC rows
# ("Item 1.\nBusiness") into a fake header. [^\S\n] is horizontal whitespace.
ITEM_HEADER = re.compile(
    r"^Item[^\S\n]+(\d{1,2}[A-Za-z]?)\.[^\S\n]+(\S.*)$",
    re.IGNORECASE | re.MULTILINE,
)


def chunk_by_section(clean_text: str) -> list[dict]:
    """Split cleaned 10-K/10-Q text into Item-level section chunks."""
    matches = list(ITEM_HEADER.finditer(clean_text))
    chunks: list[dict] = []
    if matches:
        cover = clean_text[: matches[0].start()].strip()
        if cover:
            chunks.append(
                {
                    "item_number": "0",
                    "item_title": "Cover Page",
                    "text": cover,
                }
            )
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(clean_text)
        chunks.append(
            {
                "item_number": match.group(1).upper(),
                "item_title": re.sub(r"\s+", " ", match.group(2)).strip(),
                "text": clean_text[match.end() : end].strip(),
            }
        )
    return chunks


_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _word_count(text: str) -> int:
    return len(text.split())


def _paragraphs(text: str) -> list[str]:
    if "\n\n" in text:
        parts = re.split(r"\n\s*\n", text)
    else:
        parts = text.split("\n")
    return [part.strip() for part in parts if part.strip()]


def _sentences(text: str) -> list[str]:
    parts = _SENTENCE_SPLIT.split(text.strip())
    return [part.strip() for part in parts if part.strip()]


def _split_oversized(text: str, max_words: int) -> list[str]:
    """Split one paragraph by sentences when it already exceeds max_words."""
    packed: list[str] = []
    current: list[str] = []
    current_words = 0
    for sentence in _sentences(text):
        n = _word_count(sentence)
        if current and current_words + n > max_words:
            packed.append(" ".join(current))
            current = [sentence]
            current_words = n
        else:
            current.append(sentence)
            current_words += n
    if current:
        packed.append(" ".join(current))
    return packed or [text]


def _rebalance_tail(groups: list[list[str]], max_words: int) -> None:
    """Fold a tiny last group into the previous one, or steal paragraphs to pad it."""
    min_words = max(1, max_words // 4)
    while len(groups) >= 2 and _word_count(" ".join(groups[-1])) < min_words:
        last = groups[-1]
        prev = groups[-2]
        combined_words = _word_count(" ".join(prev + last))
        if combined_words <= max_words:
            groups[-2] = prev + last
            groups.pop()
            continue
        if len(prev) >= 2:
            stolen = prev.pop()
            groups[-1] = [stolen] + last
            continue
        break


def _split_text(text: str, max_words: int) -> list[str]:
    units: list[str] = []
    for paragraph in _paragraphs(text):
        if _word_count(paragraph) <= max_words:
            units.append(paragraph)
        else:
            units.extend(_split_oversized(paragraph, max_words))

    groups: list[list[str]] = []
    current: list[str] = []
    current_words = 0
    for unit in units:
        n = _word_count(unit)
        if current and current_words + n > max_words:
            groups.append(current)
            current = [unit]
            current_words = n
        else:
            current.append(unit)
            current_words += n
    if current:
        groups.append(current)

    _rebalance_tail(groups, max_words)
    return ["\n".join(group) for group in groups]


def split_long_chunks(
    chunks: list[dict],
    ticker: str,
    filing_date: str,
    max_words: int = 400,
) -> list[dict]:
    """Split oversize Item chunks on paragraph boundaries, preserving section metadata."""
    output: list[dict] = []
    for chunk in chunks:
        text = chunk.get("text", "")
        if _word_count(text) <= max_words:
            pieces = [text]
        else:
            pieces = _split_text(text, max_words)

        for index, piece in enumerate(pieces):
            output.append(
                {
                    "item_number": chunk.get("item_number"),
                    "item_title": chunk.get("item_title"),
                    "text": piece,
                    "chunk_index": index,
                    "ticker": ticker,
                    "filing_date": filing_date,
                }
            )
    return output
