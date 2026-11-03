import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from assistant.pipeline import ask

q = " ".join(sys.argv[1:]) or "What must police tell me when they arrest me?"
a = ask(q)
print(a.answer)
for w in a.warnings:
    print("WARNING:", w)
for c in a.citations:
    print("SOURCE:", c["doc_title"], c["section"])