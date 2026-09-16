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
