import re

# Item number on its own line or followed by a (possibly wrapped) title.
ITEM_LINE = re.compile(r"^Item[^\S\n]+(\d{1,2}[A-Za-z]?)\.(.*)$", re.IGNORECASE)
PAGE_NUMBER = re.compile(r"^\d{1,4}$")
PART_LINE = re.compile(r"^PART\s+[IVX]+\b", re.IGNORECASE)
# Small complete words that should not be glued to the next wrapped token.
_COMPLETE_SMALL_WORDS = frozenset({"A", "AN", "AND", "FOR", "IN", "OF", "ON", "OR", "THE", "TO"})
_TITLE_ENDINGS = (
    "BUSINESS",
    "FACTORS",
    "COMMENTS",
    "CYBERSECURITY",
    "PROPERTIES",
    "PROCEEDINGS",
    "DISCLOSURES",
    "SECURITIES",
    "OPERATIONS",
    "RISK",
    "DATA",
    "PROCEDURES",
    "INFORMATION",
    "INSPECTIONS",
    "GOVERNANCE",
    "COMPENSATION",
    "MATTERS",
    "INDEPENDENCE",
    "SERVICES",
    "SCHEDULES",
    "SUMMARY",
    "RESERVED]",
    "RESERVED",
)


def _is_body_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped or PAGE_NUMBER.match(stripped) or ITEM_LINE.match(stripped) or PART_LINE.match(stripped):
        return False
    words = stripped.split()
    letters = re.sub(r"[^A-Za-z]", "", stripped)
    if letters and letters.isupper():
        return False
    if len(words) >= 8:
        return True
    if re.match(
        r"^(The|This|We|Our|In |For |On |To |None\.|Not applicable|Microsoft|Apple|Refer |Under )",
        stripped,
        re.I,
    ):
        return True
    return bool(stripped.endswith(".") and len(words) >= 3)


def _looks_truncated(text: str) -> bool:
    if not text:
        return True
    if text[-1] in ".:;]!?":
        return False
    last_word = re.sub(r"[^A-Za-z]", "", text.split()[-1])
    return bool(last_word and last_word.isupper() and len(last_word) <= 8)


def _title_looks_complete(title: str) -> bool:
    norm = re.sub(r"[^A-Za-z0-9\]]+$", "", title.upper())
    return any(norm.endswith(end) for end in _TITLE_ENDINGS)


def _is_title_continuation(prev_title: str, line: str) -> bool:
    stripped = line.strip()
    if not stripped or PAGE_NUMBER.match(stripped) or ITEM_LINE.match(stripped) or PART_LINE.match(stripped):
        return False
    if _title_looks_complete(prev_title):
        return False
    if _is_body_line(stripped):
        return False
    if _looks_truncated(prev_title):
        return True
    first_letters = re.sub(r"[^A-Za-z]", "", stripped.split()[0])
    return bool(first_letters.isupper() and 1 <= len(first_letters) <= 2)


def _join_title_fragment(left: str, right: str) -> str:
    if not left:
        return right
    if not right:
        return left
    last_word = re.sub(r"[^A-Za-z]", "", left.split()[-1]).upper()
    first_word = re.sub(r"[^A-Za-z]", "", right.split()[0]).upper()
    if first_word in _COMPLETE_SMALL_WORDS:
        return left + " " + right
    if left[-1].isalnum() and right[0].isalnum() and last_word not in _COMPLETE_SMALL_WORDS:
        if right[0].islower() or len(last_word) <= 3 or len(first_word) <= 7:
            return left + right
    return left + " " + right


def _join_title(parts: list[str]) -> str:
    title = ""
    for part in parts:
        title = _join_title_fragment(title, part)
    return re.sub(r"\s+", " ", title).strip()


def _read_header(lines: list[str], index: int) -> dict | None:
    match = ITEM_LINE.match(lines[index])
    if not match:
        return None

    item_number = match.group(1).upper()
    same_line = re.sub(r"\s+", " ", match.group(2)).strip()
    title_parts: list[str] = []
    cursor = index + 1

    if same_line:
        title_parts.append(same_line)
    elif cursor < len(lines):
        nxt = lines[cursor].strip()
        # TOC and some real headers put the full title on the next line, even if long.
        if nxt and not PAGE_NUMBER.match(nxt) and not ITEM_LINE.match(nxt) and not PART_LINE.match(nxt):
            title_parts.append(nxt)
            cursor += 1

    while cursor < len(lines) and title_parts and _is_title_continuation(_join_title(title_parts), lines[cursor]):
        title_parts.append(lines[cursor].strip())
        cursor += 1
        if len(title_parts) >= 5:
            break

    lookahead = lines[cursor].strip() if cursor < len(lines) else ""
    return {
        "line": index,
        "end_line": cursor,
        "item_number": item_number,
        "item_title": _join_title(title_parts),
        "is_toc": bool(PAGE_NUMBER.match(lookahead)),
    }


def chunk_by_section(clean_text: str) -> list[dict]:
    """Split cleaned 10-K/10-Q text into Item-level section chunks."""
    lines = clean_text.splitlines()
    headers: list[dict] = []
    i = 0
    while i < len(lines):
        parsed = _read_header(lines, i)
        if parsed and not parsed["is_toc"]:
            headers.append(parsed)
            i = max(parsed["end_line"], i + 1)
        else:
            i += 1

    chunks: list[dict] = []
    if headers:
        cover = "\n".join(lines[: headers[0]["line"]]).strip()
        if cover:
            chunks.append(
                {
                    "item_number": "0",
                    "item_title": "Cover Page",
                    "text": cover,
                }
            )
    for idx, header in enumerate(headers):
        end = headers[idx + 1]["line"] if idx + 1 < len(headers) else len(lines)
        chunks.append(
            {
                "item_number": header["item_number"],
                "item_title": header["item_title"],
                "text": "\n".join(lines[header["end_line"] : end]).strip(),
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
