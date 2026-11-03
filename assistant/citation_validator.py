"""2.4 Citation checks.

llm.py tells the model to cite like:   [Constitution of Nigeria 1999, section 35]
This file checks that every citation in the answer points to a passage that
was REALLY retrieved, and that figures like "72 hours" appear in the sources.

A retrieved chunk looks like (same as llm.py uses):
    {"text": "...", "metadata": {"source": "Police Act 2020", "section": "66"}, "similarity": 0.8}
"""
import re

# [Source name, section 35]   also accepts "sec 35", "s. 35", "Section 35(1)"
CITATION_PATTERN = re.compile(
    r"\[(?P<source>[^\[\]]+?),\s*(?:sections?|sec\.?|s\.)\s*(?P<section>[^\[\]]+?)\s*\]",
    re.IGNORECASE,
)

_STOP_WORDS = {"the", "of", "and", "for", "a", "an", "in", "to"}


def _words(text):
    return {w for w in re.findall(r"[a-z0-9]+", str(text or "").lower()) if w not in _STOP_WORDS}


def _section_number(section):
    """'35(1)' -> '35'   (so 35 and 35(1) count as the same section)"""
    m = re.match(r"\s*(\d+[A-Za-z]?)", str(section or ""))
    return m.group(1).lower() if m else ""


def chunk_info(chunk):
    """Source name and section of a chunk (keys as in llm.py: source, section)."""
    meta = chunk.get("metadata", {}) or {}
    source = meta.get("source") or meta.get("doc_title") or meta.get("document_id") or ""
    return str(source), str(meta.get("section", ""))


def _same_source(cited, real):
    a, b = _words(cited), _words(real)
    if not a or not b:
        return False
    return len(a & b) / min(len(a), len(b)) >= 0.75


def _find_chunk(source, section, retrieved_chunks):
    """Index of the retrieved chunk this citation points to, or None."""
    for i, chunk in enumerate(retrieved_chunks):
        real_source, real_section = chunk_info(chunk)
        if _same_source(source, real_source) and \
                _section_number(section) == _section_number(real_section):
            return i
    return None


def validate_citations(answer, retrieved_chunks):

    matches = list(CITATION_PATTERN.finditer(answer))

    valid = []
    invalid = []
    used_chunks = []

    for match in matches:

        index = _find_chunk(match.group("source"), match.group("section"), retrieved_chunks)

        if index is not None:
            valid.append(match.group())
            if index not in used_chunks:
                used_chunks.append(index)

        else:
            invalid.append(match.group())

    return {
        "has_citations": bool(matches),
        "is_valid": bool(matches) and not invalid,
        "citation_count": len(matches),
        "valid_citations": valid,
        "invalid_citations": invalid,
        "used_chunks": used_chunks,
    }


def remove_invalid_citations(answer, validation):

    for citation in validation["invalid_citations"]:

        answer = answer.replace(
            citation,
            "[UNVERIFIED CITATION]"
        )

    return answer


def citations_for_ui(validation, retrieved_chunks):
    """The list the Streamlit 'Sources' box expects (see ui/app.py)."""
    items = []
    for i in validation["used_chunks"]:
        chunk = retrieved_chunks[i]
        source, section = chunk_info(chunk)
        text = (chunk.get("text") or "").strip()
        meta = chunk.get("metadata", {}) or {}
        items.append({
            "chunk_id": meta.get("chunk_id") or chunk.get("id") or f"chunk-{i}",
            "doc_title": source,
            "section": section,
            "excerpt": text[:300] + ("…" if len(text) > 300 else ""),
        })
    return items


# ---------------------------------------------------------------------------
# Figures: time limits, amounts and percentages must come from the sources
# ---------------------------------------------------------------------------
_ONES = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen "
    "fifteen sixteen seventeen eighteen nineteen".split())}
_TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
         "eighty": 80, "ninety": 90}
_NUMBER_WORD = re.compile(
    r"\b(?:(" + "|".join(_TENS) + r")(?:[-\s]+(one|two|three|four|five|six|seven|eight|nine))?"
    r"|(" + "|".join(_ONES) + r"))\b", re.IGNORECASE)

# "72 hours", "14 days", "N5,000", "10%"
FIGURE_PATTERN = re.compile(
    r"(?:₦\s?|\bNGN\s?|\bN\s?(?=\d))(?P<money>\d[\d,]*(?:\.\d+)?)"
    r"|(?P<number>\d[\d,]*(?:\.\d+)?)\s*(?:(?:hours?|hrs?|days?|weeks?|months?|years?|"
    r"per\s?cent|percent|naira|kobo)\b|%)", re.IGNORECASE)


def _words_to_digits(text):
    """'forty-eight hours' -> '48 hours'"""
    def convert(m):
        if m.group(1):
            extra = _ONES[m.group(2).lower()] if m.group(2) else 0
            return str(_TENS[m.group(1).lower()] + extra)
        return str(_ONES[m.group(3).lower()])
    return _NUMBER_WORD.sub(convert, text)


def _numbers_in(text):
    text = _words_to_digits(text or "")
    return {n.replace(",", "") for n in re.findall(r"\d[\d,]*(?:\.\d+)?", text)}


def find_unsupported_figures(answer, retrieved_chunks, question=""):
    """Figures in the answer that are in neither the sources nor the user's question."""
    allowed = _numbers_in(question)
    for chunk in retrieved_chunks:
        allowed |= _numbers_in(chunk.get("text"))

    body = CITATION_PATTERN.sub(" ", answer)          # ignore numbers inside citations
    unsupported = []
    for m in FIGURE_PATTERN.finditer(_words_to_digits(body)):
        number = (m.group("money") or m.group("number")).replace(",", "")
        text = m.group(0).strip()
        if number not in allowed and text not in unsupported:
            unsupported.append(text)
    return unsupported
