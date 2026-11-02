"""Backend prompt for the local LLM.

Used in two ways (see PROMPT_MODE in settings.py):
  "group2_then_backup" (default): Group 2's prompt (assistant/llm.py) answers first; this prompt is used only
                                  when that one says "not found" although retrieval matched strongly.
  "backend"                     : this prompt answers every question (use it to compare the two prompts).

It answers only from the passages and still declines when nothing matches."""
import re

from . import settings as config

NOT_COVERED = "NOT_COVERED"

SYSTEM = f"""You are a legal information assistant for Nigeria. You explain the law in simple words.

RULES
1. Use ONLY the PASSAGES. Never use outside knowledge. Never invent numbers, deadlines, penalties or section numbers.
2. Read ALL the passages before you answer. If one passage defines a term that another passage uses (for example what "a reasonable time" means), use that definition in your answer.
3. Copy conditions exactly. If a rule applies only to some cases (for example "other than an offence punishable with death"), repeat that condition. Never reverse it or drop it.
4. Keep different time limits apart. Say exactly what each limit applies to (the time to bring an arrested person to court is not the same as the time allowed before a trial must take place).
5. Every point must end with its source in square brackets, copied from a passage label, for example [Police Act 2020, section 42]. Never cite a document or section that is not shown in a passage label.
6. If NONE of the passages is about the question, reply with exactly: {NOT_COVERED}

ANSWER LAYOUT (use these headings; at most 4 bullet points):
Short answer: <one or two sentences>
What the law says:
- <point> [Source, section N]
Not covered: <write this line ONLY if the question asks about something the passages do not mention; otherwise leave it out>
Next steps: <one short, practical line>
Then end with this sentence, word for word: This is general legal information, not legal advice. Please consult a qualified lawyer."""


def build_user(question: str, hits: list[dict]) -> str:
    blocks = []
    for i, h in enumerate(hits, 1):
        m = h["metadata"]
        blocks.append(f'PASSAGE {i} [{m.get("source", "Unknown")}, section {m.get("section", "?")}]\n{h["text"]}')
    return ("\n\n".join(blocks)
            + f"\n\nQUESTION: {question}\n\nAnswer using only the passages above, in the format given.")


def fallback_answer(question: str, hits: list[dict], no_source_message: str) -> str:
    import ollama
    resp = ollama.chat(
        model=config.OLLAMA_MODEL,
        messages=[{"role": "system", "content": SYSTEM},
                  {"role": "user", "content": build_user(question, hits)}],
        options={"temperature": 0.1, "num_ctx": 4096, "num_predict": 450},
    )
    text = resp["message"]["content"].strip()
    text = re.sub(r"(?i)\bfinish with:\s*", "", text)      # small models sometimes echo the instruction
    return no_source_message if (NOT_COVERED in text or not text) else text
