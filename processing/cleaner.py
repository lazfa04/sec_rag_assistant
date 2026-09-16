import re

from bs4 import BeautifulSoup

IXBRL_NS = "http://www.xbrl.org/2013/inlineXBRL"
IXBRL_META_LOCAL_NAMES = frozenset({"header", "hidden", "references", "resources"})
STRIP_LOCAL_NAMES = frozenset({"script", "style", "noscript"})


def _local_name(tag_name: str) -> str:
    name = tag_name.lower()
    if name.startswith("{") and "}" in name:
        return name.rsplit("}", 1)[-1]
    if ":" in name:
        return name.rsplit(":", 1)[-1]
    return name


def _is_ixbrl_meta_tag(tag) -> bool:
    """True for ix:header / ix:hidden / ix:references / ix:resources."""
    local = _local_name(tag.name or "")
    if local not in IXBRL_META_LOCAL_NAMES:
        return False
    prefix = (getattr(tag, "prefix", None) or "").lower()
    namespace = getattr(tag, "namespace", None) or ""
    name = (tag.name or "").lower()
    return (
        prefix == "ix"
        or namespace == IXBRL_NS
        or name.startswith("ix:")
        or name.startswith(f"{{{IXBRL_NS.lower()}}}")
    )


def _should_remove(tag) -> bool:
    local = _local_name(tag.name or "")
    return local in STRIP_LOCAL_NAMES or _is_ixbrl_meta_tag(tag)


def clean_filing_html(raw_html: str) -> str:
    """Strip HTML/XML tags and iXBRL hidden metadata, returning plain text."""
    soup = BeautifulSoup(raw_html, "lxml-xml")

    for tag in soup.find_all(_should_remove):
        tag.decompose()

    text = soup.get_text(separator="\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())
