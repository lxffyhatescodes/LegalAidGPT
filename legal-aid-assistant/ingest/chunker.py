"""Task 1.3: split cleaned legal texts into labelled chunks."""
import csv
import json
import re

from assistant import config

MAX_WORDS = 180
OVERLAP = 30

SECTION_RE = re.compile(r"^(\d{1,3}[A-Z]?)\.\s+(\S.*)$")
HEADING_RE = re.compile(r"^(PART|CHAPTER|SCHEDULE|FIRST SCHEDULE|SECOND SCHEDULE)\b")


def load_register():
    with open(config.SOURCE_REGISTER, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def skip_arrangement(lines):
    """Drop the 'Arrangement of Sections' list: the real text starts at the
    second line beginning with '1.'. If that pattern is not found, keep everything."""
    start = next((i for i, l in enumerate(lines)
                  if "arrangement of sections" in l.lower()), None)
    if start is None:
        return lines
    firsts = [i for i in range(start + 1, len(lines)) if lines[i].startswith("1.")]
    if len(firsts) >= 2:
        return lines[:start] + lines[firsts[1]:]
    return lines


def parse_sections(text):
    lines = skip_arrangement([l.strip() for l in text.splitlines()])
    sections = []
    heading = ""
    current = {"section": "intro", "heading": "", "lines": []}
    for line in lines:
        if not line:
            continue
        if HEADING_RE.match(line) and len(line) <= 120:
            heading = line
            continue
        m = SECTION_RE.match(line)
        if m:
            sections.append(current)
            current = {"section": m.group(1), "heading": heading, "lines": [line]}
        else:
            current["lines"].append(line)
    sections.append(current)
    return [s for s in sections if s["lines"]]


def windows(text):
    """Cut long provisions into ~180-word windows with a 30-word overlap."""
    words = text.split()
    if len(words) <= MAX_WORDS:
        return [text]
    step = MAX_WORDS - OVERLAP
    out = []
    for i in range(0, len(words), step):
        out.append(" ".join(words[i:i + MAX_WORDS]))
        if i + MAX_WORDS >= len(words):
            break
    return out


def build_chunks():
    chunks = []
    for row in load_register():
        path = config.CLEAN_DIR / f"{row['doc_id']}.txt"
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        k = 0
        for sec in parse_sections(text):
            parts = windows(" ".join(sec["lines"]))
            for n, part in enumerate(parts, 1):
                k += 1
                chunks.append({
                    "chunk_id": f"{row['doc_id']}-{k:04d}",
                    "text": part,
                    "label": {
                        "doc_id": row["doc_id"],
                        "doc_title": row["title"],
                        "section": sec["section"],
                        "heading": sec["heading"],
                        "problem_area": row["problem_area"],
                        "doc_type": row["doc_type"],
                        "status": row["status"],
                        "part": n,
                    },
                })
    return chunks


def save_chunks(chunks):
    config.CHUNKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(config.CHUNKS_FILE, "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    chunks = build_chunks()
    save_chunks(chunks)
    counts = {}
    for c in chunks:
        d = c["label"]["doc_id"]
        counts[d] = counts.get(d, 0) + 1
    for d, n in counts.items():
        print(f"{n:5d}  {d}")
    print("TOTAL", len(chunks))
    sample = next((c for c in chunks if c["label"]["doc_id"] == "labour_act_cap_l1"
                   and c["label"]["section"] not in ("intro", "1")), chunks[0])
    print(json.dumps(sample, indent=2, ensure_ascii=False))