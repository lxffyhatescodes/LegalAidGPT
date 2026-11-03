import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from assistant import config
from assistant.pipeline import __search_areas

q = " ".join(sys.argv[1:]) or "How long can police hold me before taking me to court?"
hits = _search_areas(q, ["arrest", "all_areas"], config.TOP_K)
for i, h in enumerate(hits, 1):
    m = h["metadata"]
    flag = "   <-- has the 'reasonable time' definition" if "forty kilometres" in h["text"] else ""
    print(f"{i}. {m['source'][:42]} s.{m['section']}  (similarity {1 - h['distance']:.3f}){flag}")