"""Split data/clean/*.txt into one chunk per section -> data/chunks.jsonl.

Chunk schema (the contract the backend relies on):
  chunk_id, doc_id, doc_title, section, text

Run:  python -m backend.chunker
Writes backend/data/chunks.jsonl (its own copy; Group 1 files are not touched).
"""
import csv
import json
import re
from pathlib import Path

from . import settings as config

SECTION_START = re.compile(r"^(\d{1,3}[A-Z]?)\.\s+\S")
MIN_CHARS = 120      # drops table-of-contents lines (short one-line "N. Title" entries)
MAX_CHARS = 950      # ~230 tokens: fits the embedding model window (256 tokens) and a small LLM prompt


_PAGE_NOISE = re.compile(
    r"(?:\s\d{1,3})?\s*The Constitution of the Federal Republic of Nigeria\s+Updated with the First, Second, "
    r"Third, Fourth and Fifth Alterations(?:[ \t]+\d{1,3})?(?=\s|$)")


def clean_text(text: str) -> str:
    """Remove running page headers/footers that the PDF extraction left in the middle of sentences."""
    return _PAGE_NOISE.sub(" ", text)


def _register():
    """titles + the set of doc_ids that must NOT be searched (drafts, excluded scans)."""
    titles, skip = {}, set()
    if config.SOURCE_REGISTER.exists():
        with open(config.SOURCE_REGISTER, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                titles[row["doc_id"]] = row["title"]
                st = (row.get("status") or "").strip()
                if st.startswith("excluded") or st == "draft_not_in_force":
                    skip.add(row["doc_id"])
    return titles, skip


def _pieces(text: str):
    """Yield lines; a single over-long line (flat judgments) is cut at sentence ends."""
    for line in text.split("\n"):
        while len(line) > MAX_CHARS:
            cut = line.rfind(". ", 0, MAX_CHARS)
            cut = cut + 1 if cut > MAX_CHARS // 2 else MAX_CHARS
            yield line[:cut]
            line = line[cut:].lstrip()
        yield line


def _split_long(text: str):
    """Split a long section on line boundaries. Every part after the first repeats the
    section heading, so the embedding (and the LLM) always know which section it belongs to."""
    if len(text) <= MAX_CHARS:
        yield text
        return
    heading = text.split("\n", 1)[0][:120]
    buf = ""
    first = True
    for line in _pieces(text):
        if buf and len(buf) + len(line) > MAX_CHARS:
            yield buf.strip()
            buf, first = f"{heading} (continued)\n", False
        buf += line + "\n"
    if buf.strip() and buf.strip() != f"{heading} (continued)":
        yield buf.strip()


def chunk_document(doc_id: str, title: str, text: str):
    sections, current_no, current = [], "General", []
    for line in text.split("\n"):
        m = SECTION_START.match(line)
        if m:
            if current:
                sections.append((current_no, "\n".join(current)))
            current_no, current = m.group(1), [line]
        else:
            current.append(line)
    if current:
        sections.append((current_no, "\n".join(current)))

    n = 0
    for sec_no, body in sections:
        body = body.strip()
        if len(body) < MIN_CHARS:
            continue
        for part in _split_long(body):
            n += 1
            yield {
                "chunk_id": f"{doc_id}::{sec_no}::{n}",
                "doc_id": doc_id,
                "doc_title": title,
                "section": sec_no,
                "text": part,
            }


def build(out_file: Path = config.CHUNKS_FILE) -> int:
    titles, skip = _register()
    count = 0
    with open(out_file, "w", encoding="utf-8") as out:
        for f in sorted(config.CLEAN_DIR.glob("*.txt")):
            doc_id = f.stem
            if doc_id in skip:      # e.g. exposure draft that is not law yet
                continue
            title = titles.get(doc_id, doc_id.replace("_", " ").title())
            for ch in chunk_document(doc_id, title, clean_text(f.read_text(encoding="utf-8", errors="ignore"))):
                out.write(json.dumps(ch, ensure_ascii=False) + "\n")
                count += 1
    return count


if __name__ == "__main__":
    print(f"Wrote {build()} chunks to {config.CHUNKS_FILE}")
