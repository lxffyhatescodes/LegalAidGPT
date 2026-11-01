"""See what the search returns for a question (no LLM needed).
Run:  python -m backend.try_retrieval "I was arrested yesterday. How long can police hold me?"
"""
import sys

from .retriever import expand_query, get_retriever, retrieve

q = " ".join(sys.argv[1:]) or "I was arrested yesterday. How long can police hold me?"
print("retriever:", get_retriever().name)
print("search text:", expand_query(q)[:200], "...\n")
for i, h in enumerate(retrieve(q, 8), 1):
    m = h["metadata"]
    print(f'{i}. {h["score"]:.3f} | {m["source"][:45]} | s.{m["section"]} | {h["text"][:90]!r}')
