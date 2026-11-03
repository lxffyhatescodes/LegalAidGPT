import ollama

from assistant import config

SYSTEM_PROMPT = """You are a legal aid assistant for Nigeria.

Answer using ONLY the passages provided under CONTEXT. Rules:

1. If none of the passages is relevant to the QUESTION's topic, reply with ONLY
   this and nothing else:
   "I could not find this in the available legal documents. Please consult a
   qualified lawyer or the Legal Aid Council."
2. Read ALL the passages before answering. Use the passage that most directly
   answers the question. If a passage defines a term the question depends on
   (for example what "a reasonable time" means), use that definition. Ignore
   passages that do not help.
3. If the passages only partly answer the question, say what they state and
   which part is not covered by the available documents. Never fill gaps from
   your own knowledge.
4. Cite every legal claim by copying the label printed above the passage, in
   square brackets, exactly as written, for example
   [Constitution of the Federal Republic of Nigeria 1999, section 35].
   Never cite a source or section number that is not in a label.
5. Never state numbers, time limits, deadlines or penalties unless they are
   written in the passages.
6. Keep the answer short: at most 80 words, in plain language. Then give one
   or two general next steps (such as asking for a lawyer or contacting the
   Legal Aid Council) and end with the line:
   "This is general legal information, not legal advice. Please consult a
   qualified lawyer."
7. Never use the word "CONTEXT" or "passage" in your answer. Say "the
   available legal documents".
8. Never accept sensitive personal information. If the user provides it,
   politely decline to continue and suggest consulting a lawyer."""
   
NO_SOURCE_MESSAGE = (
    "I could not find this in the available legal documents. "
    "Please consult a qualified lawyer or the Legal Aid Council."
)


def build_prompt(question: str, hits: list[dict]) -> str:
    blocks = []
    for h in hits:
        m = h["metadata"]
        label = f'{m.get("source", "Unknown source")}, section {m.get("section", "?")}'
        blocks.append(f"[{label}]\n{h['text']}")
    return f"CONTEXT:\n{chr(10).join(blocks)}\n\nQUESTION:\n{question}"


def _messages(question: str, hits: list[dict]) -> list[dict]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_prompt(question, hits)},
    ]


def _options() -> dict:
    return {
        "temperature": config.LLM_TEMPERATURE,
        "num_ctx": config.LLM_CONTEXT_TOKENS,
        "num_predict": config.LLM_MAX_NEW_TOKENS,
        "num_thread": 4,
    }


def answer(question: str, hits: list[dict], model: str = config.OLLAMA_MODEL) -> str:
    if not hits:
        return NO_SOURCE_MESSAGE
    resp = ollama.chat(
        model=model,
        messages=_messages(question, hits),
        options=_options(),
        keep_alive="30m",
    )
    text = resp["message"]["content"].strip()
    if text.lower().startswith(("i could not find", "i couldn't find", "i cannot find", "i can't find")):
        return NO_SOURCE_MESSAGE
    return text


def answer_stream(question: str, hits: list[dict], model: str = config.OLLAMA_MODEL):
    if not hits:
        yield NO_SOURCE_MESSAGE
        return
    stream = ollama.chat(
        model=model,
        messages=_messages(question, hits),
        options=_options(),
        stream=True,
        keep_alive="30m",
    )
    for part in stream:
        yield part["message"]["content"]