"""Backup prompt used ONLY when Group 2's prompt (assistant/llm.py) answers "not found" although retrieval
found strongly matching passages. Small local models are sometimes over-cautious; this one is shorter
and clearer, but it still answers only from the passages and still declines when nothing matches."""
from . import settings as config

NOT_COVERED = "NOT_COVERED"

SYSTEM = f"""You are a legal information assistant for Nigeria.
Use ONLY the PASSAGES given. Explain in simple words what the passages say that answers the question.
After each legal point, name its source in square brackets exactly like [Police Act 2020, section 42],
using only the document names and section numbers shown in the passage labels.
Do not add numbers, deadlines or penalties that are not written in the passages.
If the passages answer only part of the question, say clearly which part is not covered.
Only if NONE of the passages is about the topic of the question, reply with exactly: {NOT_COVERED}
Finish with: This is general legal information, not legal advice. Please consult a qualified lawyer."""


def build_user(question: str, hits: list[dict]) -> str:
    blocks = []
    for h in hits:
        m = h["metadata"]
        blocks.append(f'[{m.get("source", "Unknown")}, section {m.get("section", "?")}]\n{h["text"]}')
    return "PASSAGES:\n" + "\n\n".join(blocks) + f"\n\nQUESTION:\n{question}"


def fallback_answer(question: str, hits: list[dict], no_source_message: str) -> str:
    import ollama
    resp = ollama.chat(
        model=config.OLLAMA_MODEL,
        messages=[{"role": "system", "content": SYSTEM},
                  {"role": "user", "content": build_user(question, hits)}],
        options={"temperature": 0.2, "num_ctx": 4096, "num_predict": 512},
    )
    text = resp["message"]["content"].strip()
    return no_source_message if (NOT_COVERED in text or not text) else text
