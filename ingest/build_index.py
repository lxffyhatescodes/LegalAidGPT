"""Chunk data/clean/*.txt, embed with Ollama, store in Chroma.

    python ingest/build_index.py --areas arrest all_areas   # quick index for testing
    python ingest/build_index.py                            # everything
"""
import argparse
import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from assistant import config
from retrieval import add_chunks, collection

NUMBERED = re.compile(r"^(\d{1,3}[A-Z]?)\.(\s|\u2014|-|\()")
SENT = re.compile(r"(?<=[.;:])\s+")
HEADER_JUNK = re.compile(
    r"(\d+\s+)?The Constitution of the Federal Republic of Nigeria Updated with the "
    r"First, Second, Third, Fourth and Fifth Alterations(\s+\d+)?"
)
MAX_CHARS = 1500
MIN_CHARS = 80   # drops table-of-contents lines like "35. Right to liberty"
SKIP_STATUS = {"needs_ocr", "draft_not_in_force", "bill_text_verify"}
SKIP_AREAS = {"support"}


def shrink(line):
    """Break a very long line into pieces of at most MAX_CHARS, at sentence ends."""
    if len(line) <= MAX_CHARS:
        return [line]
    out, cur = [], ""
    for s in SENT.split(line):
        while len(s) > MAX_CHARS:          # a single huge sentence: hard cut
            if cur:
                out.append(cur)
                cur = ""
            out.append(s[:MAX_CHARS])
            s = s[MAX_CHARS:]
        if cur and len(cur) + len(s) + 1 > MAX_CHARS:
            out.append(cur)
            cur = ""
        cur = f"{cur} {s}".strip()
    if cur:
        out.append(cur)
    return out


def split_long(lines):
    pieces, current = [], ""
    for raw in lines:
        for ln in shrink(raw):
            if current and len(current) + len(ln) + 1 > MAX_CHARS:
                pieces.append(current)
                current = ""
            current = f"{current}\n{ln}".strip()
    if current:
        pieces.append(current)
    return pieces


def chunk_document(doc_id, lines):
    sections, label, buf = [], "intro", []
    for ln in lines:
        m = NUMBERED.match(ln)
        if m:
            if buf:
                sections.append((label, buf))
            label, buf = m.group(1), [ln]
        else:
            buf.append(ln)
    if buf:
        sections.append((label, buf))

        chunks, n = [], 0
    for label, buf in sections:
        for k, piece in enumerate(split_long(buf)):
            if k > 0 and label != "intro":
                piece = f"{buf[0][:120]}\n{piece}"   # repeat the section heading
            if len(piece) < MIN_CHARS:
                continue
            n += 1
            section = label if label != "intro" else f"excerpt {n}"
            chunks.append({"id": f"{doc_id}-{n}", "text": piece, "section": section})
    return chunks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--areas", nargs="*", help="only these problem_area values")
    args = ap.parse_args()

    with open(config.SOURCE_REGISTER, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    total = 0
    for row in rows:
        if row["status"].startswith("excluded") or row["status"] in SKIP_STATUS:
            continue
        if row["problem_area"] in SKIP_AREAS:
            continue
        if args.areas and row["problem_area"] not in args.areas:
            continue
        path = config.CLEAN_DIR / f"{row['doc_id']}.txt"
        if not path.exists():
            print(f"!! missing {path.name}, run extract.py first")
            continue

        lines = [l.strip() for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
        chunks = chunk_document(row["doc_id"], lines)
        records = [{
            "id": c["id"],
            "text": HEADER_JUNK.sub(" ", c["text"]),
            "metadata": {
                "case_area": row["problem_area"],
                "source_type": row["doc_type"],
                "source": row["title"],
                "section": c["section"],
                "doc_id": row["doc_id"],
            },
        } for c in chunks]

        existing = len(collection.get(where={"doc_id": row["doc_id"]})["ids"])
        if existing == len(records):
            print(f"skip {row['doc_id']:42} already indexed")
            continue
        
        for i in range(0, len(records), 32):
            add_chunks(records[i:i + 32])
        total += len(records)
        print(f"ok  {row['doc_id']:42} {len(records):5} chunks")

    print(f"\nDone: {total} chunks stored in {config.INDEX_DIR / 'chroma'}")


if __name__ == "__main__":
    main()