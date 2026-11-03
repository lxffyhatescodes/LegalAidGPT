"""Profile every PDF in data/raw and suggest which target problem each belongs to.

Run from the legal-aid-assistant folder:
    python ingest/profile_docs.py
Writes data/doc_profile.csv and prints a short table.
"""
import csv
import re
from pathlib import Path

import fitz  # PyMuPDF

RAW = Path("data/raw")
OUT = Path("data/doc_profile.csv")
PAGES_TO_READ = 15  # enough to identify a document without reading all of it

CLASSES = {
    "arrest": ["arrest", "police", "detention", "bail", "suspect", "custody",
               "criminal justice", "remand", "fundamental rights enforcement"],
    "land": ["land use", "certificate of occupancy", "right of occupancy",
             "land", "title", "tenure", "governor"],
    "tenant": ["tenant", "landlord", "tenancy", "rent", "premises",
               "eviction", "lease", "quit notice"],
    "consumer": ["consumer", "competition", "lending", "loan", "borrower",
                 "goods", "central bank", "cbn", "fccpc"],
    "legal_assistance": ["legal aid", "legal practitioner", "legal aid council",
                         "indigent", "pro bono"],
    "marriage": ["marriage", "matrimonial", "divorce", "spouse", "wife",
                 "husband", "dissolution", "child rights", "domestic violence",
                 "customary law marriage"],
    "employment": ["employee", "employer", "labour", "wages", "workers",
                   "trade union", "redundancy", "pension"],
}

TYPE_HINTS = [
    ("judgment", ["in the high court", "in the court of appeal", "judgment",
                  "plaintiff", "defendant", "appellant", "respondent"]),
    ("regulation", ["regulations", "guidelines", "rules"]),
    ("statute", ["an act to", "be it enacted", "laws of the federation", "cap."]),
    ("article", ["abstract", "keywords", "journal", "introduction"]),
]


def score(text, words):
    return sum(text.count(w) for w in words)


def profile(path):
    doc = fitz.open(path)
    n_pages = len(doc)
    chunks = [doc[i].get_text() for i in range(min(PAGES_TO_READ, n_pages))]
    text = "\n".join(chunks)
    low = re.sub(r"\s+", " ", text.lower())
    first = re.sub(r"\s+", " ", chunks[0]).strip()[:120] if chunks else ""
    has_text = len(low) > 200 * min(3, n_pages)
    scores = {c: score(low, w) for c, w in CLASSES.items()}
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    top, top2 = ranked[0], ranked[1]
    if not has_text:
        guess = "NEEDS OCR"
    elif top[1] < 5:
        guess = "unclear"
    else:
        guess = top[0]
    kind = "unknown"
    best = 0
    for name, words in TYPE_HINTS:
        s = score(low, words)
        if s > best:
            kind, best = name, s
    return {
        "file": path.name, "pages": n_pages, "has_text": has_text,
        "suggested_class": guess, "score": top[1],
        "second_class": top2[0] if top2[1] >= 5 else "",
        "doc_type_guess": kind, "starts_with": first,
    }


def main():
    rows = [profile(p) for p in sorted(RAW.glob("*.pdf"))]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    for r in rows:
        print(f"{r['file'][:45]:45} | {r['suggested_class']:16} | "
              f"{r['doc_type_guess']:10} | {r['pages']}p | {r['starts_with'][:60]}")
    print(f"\nSaved {len(rows)} rows to {OUT}")


if __name__ == "__main__":
    main()
