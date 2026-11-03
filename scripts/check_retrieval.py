import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from retrieval import search

q = " ".join(sys.argv[1:]) or "How long can police hold me before taking me to court?"
for area in (["arrest"], ["all_areas"], None):
    print(f"\n== area filter: {area}")
    for h in search(q, case_area=area, k=5):
        m = h["metadata"]
        print(f"{1 - h['distance']:.3f}  {m['source'][:35]:35} s.{m['section']:6} {h['text'][:70]!r}")