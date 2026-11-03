import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from retrieval import search

COVERED = [
    "What must police tell me when they arrest me?",
    "How long can police hold me before taking me to court?",
    "My boss has refused to pay my salary for three months. What should I do?",
    "Can my employer dismiss me without notice?",
    "My landlord wants to evict me. What are my rights?",
    "What are my rights as a borrower of a digital loan?",
    "A shop sold me a faulty phone and refuses to refund me.",
]
NOT_COVERED = [
    "What is the penalty for tax evasion?",
    "How do I register a company?",
    "How do I get a passport?",
    "What is the speed limit on highways?",
]

for label, qs in [("COVERED", COVERED), ("NOT COVERED", NOT_COVERED)]:
    print(label)
    for q in qs:
        hits = search(q, k=1)
        sim = 1 - hits[0]["distance"] if hits else None
        src = hits[0]["metadata"]["source"][:30] if hits else ""
        print(f"  {sim:.3f}  {src:30}  {q}" if sim is not None else f"  none  {q}")