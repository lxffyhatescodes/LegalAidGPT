"""Step 6: extract text from each PDF in data/raw and clean it into data/clean.

Run from the legal-aid-assistant folder:
    python ingest/extract.py                  # process every eligible document
    python ingest/extract.py --preview acja_2015   # look at a sample of one result

Outputs:
    data/clean/<doc_id>.txt    one clean text file per document
    data/clean/_report.csv     quality report (check the 'flags' column)

Documents are taken from data/source_register.csv. Rows whose status starts with
"excluded" or equals "needs_ocr" are skipped. Raw files are never changed.
"""
import csv
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

import pymupdf

RAW = Path("data/raw")
CLEAN = Path("data/clean")
REGISTER = Path("data/source_register.csv")
REPORT = CLEAN / "_report.csv"

ZONE = 3             # how many lines at the top/bottom of a page count as header/footer
REPEAT_SHARE = 0.35  # a header/footer line must appear on this share of pages

PAGE_NUMBER = re.compile(
    r"^(page\s*\d+(\s*of\s*\d+)?|\d+\s*\|\s*p\s*a\s*g\s*e|-\s*\d+\s*-|\d{1,4}|[ivxlc]{1,6})$",
    re.I,
)
NUMBERED = re.compile(r"^\d{1,3}[A-Z]?\.(\s|\u2014|-|\()")
SUBITEM = re.compile(r"^\(\s*([0-9]{1,3}|[a-z]{1,3}|[ivx]{1,5})\s*\)")
DIVISION = re.compile(
    r"^(PART|CHAPTER|SCHEDULE|FIRST SCHEDULE|SECOND SCHEDULE|ARTICLE|SECTION|ARRANGEMENT)\b"
    r"|^(Part|Chapter|Schedule|Section|Article)\s+[IVXLC\d]+\b"
)


def normalise_chars(text):
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\u00ad", "").replace("\u200b", "").replace("\x0c", " ")
    text = text.replace("\u2010", "-").replace("\u2011", "-").replace("\u2012", "-")
    text = re.sub(r"\(\s+([0-9A-Za-z]{1,4})\s*\)", r"(\1)", text)   # '( 4)' -> '(4)'
    text = re.sub(r"\(([0-9A-Za-z]{1,4})\s+\)", r"(\1)", text)      # '(4 )' -> '(4)'
    text = text.replace("(I)", "(1)")                                 # OCR often reads (1) as (I)
    text = text.replace("\u2019", "'").replace("\u2018", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = re.sub(r"\.{3,}", " ", text)           # table-of-contents dot leaders
    text = re.sub(r"[ \t]+", " ", text)
    return text


def shape(line):
    """Line with digits masked, so 'Page 4' and 'Page 5' count as the same line."""
    return re.sub(r"\d+", "#", line.strip().lower())


def page_lines(doc):
    pages = []
    for page in doc:
        raw = normalise_chars(page.get_text("text", sort=True))
        pages.append([ln.strip() for ln in raw.split("\n") if ln.strip()])
    return pages


def strip_headers_footers(pages):
    """Remove repeated header/footer lines and bare page numbers. Returns (pages, count)."""
    n = len(pages)
    counts = Counter()
    for lines in pages:
        zone = lines[:ZONE] + lines[-ZONE:]
        for s in {shape(ln) for ln in zone}:
            counts[s] += 1
    repeated = {s for s, c in counts.items() if n >= 5 and c / n >= REPEAT_SHARE and len(s) < 90}
    removed, out, kept_first = 0, [], set()
    for lines in pages:
        keep = []
        for i, ln in enumerate(lines):
            in_zone = i < ZONE or i >= len(lines) - ZONE
            protected = bool(NUMBERED.match(ln) or SUBITEM.match(ln)) or len(ln) >= 45
            if in_zone and PAGE_NUMBER.match(ln):
                removed += 1
                continue
            if in_zone and shape(ln) in repeated and not protected:
                if DIVISION.match(ln) and shape(ln) not in kept_first:
                    kept_first.add(shape(ln))   # a real PART/CHAPTER heading: keep the first copy
                    keep.append(ln)
                    continue
                removed += 1
                continue
            keep.append(ln)
        out.append(keep)
    return out, removed


def is_heading(line):
    letters = [c for c in line if c.isalpha()]
    return len(letters) >= 3 and line.isupper() and len(line) < 100


def starts_block(line):
    return bool(NUMBERED.match(line) or SUBITEM.match(line) or DIVISION.match(line) or is_heading(line))


def join_lines(lines):
    """Rejoin wrapped lines into blocks; keep headings and numbered provisions on their own lines."""
    blocks = []
    for ln in lines:
        if not blocks:
            blocks.append(ln)
            continue
        prev = blocks[-1]
        if starts_block(ln) or is_heading(prev):
            blocks.append(ln)
        elif re.search(r"[A-Za-z]-$", prev) and ln[:1].islower():
            blocks[-1] = prev[:-1] + ln          # word split by a hyphen at the line end
        else:
            blocks[-1] = prev + " " + ln
    return [re.sub(r"\s+", " ", b).strip() for b in blocks if b.strip()]


def clean_document(path):
    doc = pymupdf.open(path)
    pages = page_lines(doc)
    pages, removed = strip_headers_footers(pages)
    blocks = join_lines([ln for lines in pages for ln in lines])
    return blocks, len(doc), removed


def flags_for(blocks, n_pages, text):
    flags = []
    if n_pages and len(text) / n_pages < 600:
        flags.append("low_text_per_page")
    letters = sum(c.isalpha() for c in text)
    if text and letters / len(text) < 0.65:
        flags.append("many_symbols")
    if not any(NUMBERED.match(b) for b in blocks):
        flags.append("no_numbered_sections")
    return ";".join(flags)


def eligible_rows():
    if not REGISTER.exists():
        print("No register found; processing every PDF in data/raw.")
        return [{"doc_id": p.stem, "file": p.name} for p in sorted(RAW.glob("*.pdf"))]
    with open(REGISTER, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    keep = [r for r in rows if not r["status"].startswith("excluded") and r["status"] != "needs_ocr"]
    skipped = [r["doc_id"] for r in rows if r not in keep]
    if skipped:
        print("Skipped (excluded / needs OCR):", ", ".join(skipped))
    return keep


def preview(doc_id):
    path = CLEAN / f"{doc_id}.txt"
    if not path.exists():
        print("Not found:", path)
        return
    lines = path.read_text(encoding="utf-8").split("\n")
    start = int(len(lines) * 0.4)
    print(f"--- {doc_id}: lines {start} to {min(start + 30, len(lines))} of {len(lines)} ---")
    for ln in lines[start:start + 30]:
        print(ln[:160])


def main():
    if "--preview" in sys.argv:
        preview(sys.argv[sys.argv.index("--preview") + 1])
        return
    CLEAN.mkdir(parents=True, exist_ok=True)
    report = []
    for row in eligible_rows():
        src = RAW / row["file"]
        if not src.exists():
            print(f"!! missing file: {row['file']}")
            continue
        try:
            blocks, n_pages, removed = clean_document(src)
        except Exception as exc:   # keep going if one file is broken
            print(f"!! failed: {row['file']} ({exc})")
            report.append({"doc_id": row["doc_id"], "pages": "", "chars": 0,
                           "removed_lines": 0, "numbered_sections": 0, "flags": "failed"})
            continue
        text = "\n".join(blocks)
        (CLEAN / f"{row['doc_id']}.txt").write_text(text, encoding="utf-8")
        report.append({
            "doc_id": row["doc_id"], "pages": n_pages, "chars": len(text),
            "removed_lines": removed,
            "numbered_sections": sum(bool(NUMBERED.match(b)) for b in blocks),
            "flags": flags_for(blocks, n_pages, text),
        })
        print(f"ok  {row['doc_id']:42} {n_pages:4}p {len(text):8} chars  {report[-1]['flags']}")
    with open(REPORT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(report[0].keys()))
        w.writeheader()
        w.writerows(report)
    print(f"\nDone. {len(report)} documents. Report: {REPORT}")


if __name__ == "__main__":
    main()
